"""Small, self-contained builders for dashboard sub-components.

Kept separate from ``dashboard.callbacks`` so each piece (regression
snippets, performance panels, table theming) has a single responsibility
and can be built, reasoned about, and tested independently of Dash's
callback machinery.
"""

from __future__ import annotations

import logging
from typing import Any

import dash_mantine_components as dmc
import pandas as pd
import plotly.graph_objects as go
from dash import dcc
from sklearn.linear_model import LinearRegression

from dashboard.config import Config
from dashboard.data import DATA
from dashboard.ui.theme import table_theme  # noqa: F401  (re-exported for callers of this module)
from dashboard.viz.charts import Visualizer

logger = logging.getLogger(__name__)

_MIN_POINTS_FOR_REGRESSION = 5
_REGRESSION_AXIS_TITLE_SIZE = 8
_POSITIVE_COLOR = "#81c784"
_NEGATIVE_COLOR = "#e57373"


def build_regression_snippets(
    selected_tickers: list[str], start: pd.Timestamp, end: pd.Timestamp, mode: str
) -> list[Any]:
    """One small mentions-vs-price scatter + linear fit per ticker with enough data."""
    snippets = []
    for ticker in selected_tickers:
        mentions = DATA.mentions.loc[start:end, ticker].values.reshape(-1, 1)
        prices = DATA.quotes_clean.loc[start:end, ticker].values
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
        Visualizer.apply_standard_style(fig, mode, x_label="Ref", y_label="Price %")
        # These snippets are only 150px tall; shrink the axis titles (and their
        # standoff from the axis) so they don't crowd out the plot area.
        fig.update_xaxes(title_font=dict(size=_REGRESSION_AXIS_TITLE_SIZE), title_standoff=2)
        fig.update_yaxes(title_font=dict(size=_REGRESSION_AXIS_TITLE_SIZE), title_standoff=2)
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
        prices = DATA.quotes_clean.loc[start:end, ticker]
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
