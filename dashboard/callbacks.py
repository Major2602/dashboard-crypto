"""Dash callbacks.

Callbacks are defined as ``async def`` functions. Dash dispatches async
callbacks through Flask's async view support (enabled by having
``asgiref`` installed, see requirements.txt); each invocation runs inside
its own event loop. Within ``update_dashboard`` the independent pieces of
work -- each Plotly figure, the regression snippets, the performance
panels, the topics table -- are CPU-bound (pandas/plotly), so they're
dispatched to worker threads via ``asyncio.to_thread`` and awaited
together with ``asyncio.gather``. That keeps the event loop free to serve
other requests while a given callback's charts are being computed,
instead of building everything strictly sequentially.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date
from typing import Any

import dash_mantine_components as dmc
import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, callback_context

from dashboard.callback_helpers import clean_topics_table, resolve_date_range
from dashboard.config import Config
from dashboard.data import DATA
from dashboard.ui.components import build_performance_grid, build_regression_snippets
from dashboard.ui.layout import app
from dashboard.ui.theme import table_theme
from dashboard.viz.charts import Visualizer

logger = logging.getLogger(__name__)


@app.callback(Output("mantine-provider", "forceColorScheme"), Input("theme-toggle", "checked"))
def toggle_theme(checked: bool) -> str:
    """Cheap, purely synchronous UI toggle -- no benefit from async here."""
    return "dark" if checked else "light"


def _empty_dashboard_response(date_range: list[date]) -> tuple[Any, ...]:
    """Fallback output tuple used when a dashboard rebuild fails, so the UI
    degrades gracefully instead of crashing the callback."""
    empty_fig = go.Figure()
    return (
        empty_fig, empty_fig, empty_fig, empty_fig, [], [],
        dmc.SimpleGrid(cols=5, children=[]), date_range, {}, {}, {}, {},
    )


@app.callback(
    [
        Output("main-price-graph", "figure"), Output("corr-price", "figure"), Output("corr-ref", "figure"),
        Output("radar-graph", "figure"), Output("regression-container", "children"), Output("topics-table", "data"),
        Output("perf-panels-top", "children"), Output("date-range", "value"), Output("topics-table", "style_cell"),
        Output("topics-table", "style_header"), Output("topics-table", "style_data"), Output("main-title", "style"),
    ],
    [
        Input("ticker-select", "value"), Input("date-range", "value"), Input("btn-1m", "n_clicks"),
        Input("btn-3m", "n_clicks"), Input("btn-6m", "n_clicks"), Input("btn-9m", "n_clicks"), Input("btn-12m", "n_clicks"),
        Input("btn-all", "n_clicks"), Input("mantine-provider", "forceColorScheme"),
    ],
)
async def update_dashboard(
    selected_tickers: list[str] | None,
    date_range: list[date],
    n1: int, n3: int, n6: int, n9: int, n12: int, n_all: int,
    mode: str | None,
) -> tuple[Any, ...]:
    """Rebuild every chart, table and panel for the current filters."""
    mode = mode or Config.DEFAULT_THEME
    # Callback inputs arrive as raw JSON from the browser, so a UI-level
    # MultiSelect allowlist is not a security boundary -- re-validate here
    # against the data we actually loaded (see DataBundle.valid_tickers).
    selected_tickers = DATA.valid_tickers(selected_tickers)

    trigger = callback_context.triggered[0]["prop_id"].split(".")[0] if callback_context.triggered else None
    max_d, min_d = DATA.report["date"].max().date(), DATA.report["date"].min().date()
    date_range = resolve_date_range(trigger, date_range, max_d, min_d)
    start, end = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])

    try:
        (
            fig_price, fig_corr_p, fig_corr_r, fig_radar,
            reg_snippets, table_records, perf_items,
        ) = await asyncio.gather(
            asyncio.to_thread(Visualizer.create_main_price_chart, start, end, selected_tickers, mode),
            asyncio.to_thread(Visualizer.create_correlation_heatmap, DATA.quotes_clean.loc[start:end, selected_tickers], mode),
            asyncio.to_thread(Visualizer.create_correlation_heatmap, DATA.mentions.loc[start:end, selected_tickers], mode),
            asyncio.to_thread(Visualizer.create_radar_chart, selected_tickers, start, end, mode),
            asyncio.to_thread(build_regression_snippets, selected_tickers, start, end, mode),
            asyncio.to_thread(clean_topics_table, DATA.report, start, end),
            asyncio.to_thread(build_performance_grid, selected_tickers, start, end, mode),
        )
    except Exception:
        logger.exception(
            "Failed to rebuild dashboard for tickers=%s range=[%s, %s]", selected_tickers, start, end
        )
        return _empty_dashboard_response(date_range)

    theme = table_theme(mode)
    return (
        fig_price, fig_corr_p, fig_corr_r, fig_radar,
        reg_snippets, table_records,
        dmc.SimpleGrid(cols=5, children=perf_items),
        date_range,
        theme["cell"], theme["header"], theme["data"], theme["title"],
    )
