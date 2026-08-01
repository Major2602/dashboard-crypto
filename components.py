# UI COMPONENT BUILDERS
"""Small, self-contained builders for dashboard sub-components.

Extracted out of ``callbacks.py`` so each piece (regression snippets,
performance panels, table theming) has a single responsibility and can be
built, reasoned about, and tested independently of Dash's callback
machinery.
"""

from __future__ import annotations

import logging
from typing import Any

import dash_mantine_components as dmc
import pandas as pd
import plotly.graph_objects as go
from dash import dcc
from sklearn.linear_model import LinearRegression

from config import Config
from data_layer import DF_MENTIONS, QUOTES_CLEAN
from vis_helpers import Visualizer

logger = logging.getLogger(__name__)

_MIN_POINTS_FOR_REGRESSION = 5
_POSITIVE_COLOR = "#81c784"
_NEGATIVE_COLOR = "#e57373"


def build_regression_snippets(
    selected_tickers: list[str], start: pd.Timestamp, end: pd.Timestamp, mode: str
) -> list[Any]:
    """One small mentions-vs-price scatter + linear fit per ticker with enough data."""
    snippets = []
    for ticker in selected_tickers:
        mentions = DF_MENTIONS.loc[start:end, ticker].values.reshape(-1, 1)
        prices = QUOTES_CLEAN.loc[start:end, ticker].values
        if len(mentions) <= _MIN_POINTS_FOR_REGRESSION:
            continue

        try:
            model = LinearRegression().fit(mentions, prices)
        except ValueError:
            logger.warning("Regression fit failed for %s in [%s, %s]; skipping", ticker, start, end)
            continue

        color = Config.TICKER_COLORS[ticker]
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=mentions.flatten(), y=prices, mode="markers", marker=dict(color=color)))
        fig.add_trace(go.Scatter(x=mentions.flatten(), y=model.predict(mentions), line=dict(color=color)))
        Visualizer.apply_standard_style(fig, mode)
        fig.update_layout(height=150, showlegend=False, margin=dict(t=5, b=5))

        snippets.append(
            dmc.Stack(
                [
                    dmc.Text(ticker, size="xs", fw=700, ta="center"),
                    dmc.Paper(
                        [dcc.Graph(figure=fig, config={"displayModeBar": False})],
                        withBorder=True, radius="sm", shadow="xs", mb="xs",
                    ),
                ]
            )
        )
    return snippets


def build_performance_grid(
    selected_tickers: list[str], start: pd.Timestamp, end: pd.Timestamp, mode: str
) -> list[Any]:
    """Small colored panels showing period price performance per ticker."""
    items = []
    for ticker in selected_tickers:
        prices = QUOTES_CLEAN.loc[start:end, ticker]
        change = float(prices.iloc[-1] - prices.iloc[0]) if not prices.empty else 0.0
        color = _POSITIVE_COLOR if change >= 0 else _NEGATIVE_COLOR
        items.append(
            dmc.Paper(
                [
                    dmc.Text(ticker, fw=700, size="xs", ta="center", c=color),
                    dmc.Text(f"{change:+.2f}%", size="xs", ta="center", c=color),
                ],
                withBorder=True, p=5,
                bg="rgba(0,0,0,0.2)" if mode == "dark" else "#f8f9fa",
            )
        )
    return items


def table_theme(mode: str) -> dict[str, dict]:
    """Style dicts for the topics DataTable + section title, per color scheme.

    Returns a dict with keys ``cell``, ``header``, ``data``, ``title`` so
    callers can spread the relevant piece straight into the matching Dash
    Output.
    """
    is_dark = mode == "dark"
    palette = {
        "bg": "#1A1B1E" if is_dark else "#FFFFFF",
        "text": "#C1C2C5" if is_dark else "#000000",
        "border": "#373A40" if is_dark else "#dee2e6",
        "header": "#25262B" if is_dark else "#f8f9fa",
    }
    border = f'1px solid {palette["border"]}'
    return {
        "cell": {
            "backgroundColor": palette["bg"], "color": palette["text"], "textAlign": "left",
            "border": border, "padding": "10px", "whiteSpace": "normal", "font-family": "sans-serif",
        },
        "header": {
            "backgroundColor": palette["header"], "color": palette["text"], "fontWeight": "bold",
            "border": border, "font-family": "sans-serif",
        },
        "data": {"border": border},
        "title": {"fontWeight": 800, "color": "white" if is_dark else "black"},
    }
