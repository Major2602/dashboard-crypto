"""Pure functions/classmethods that turn DataFrames into Plotly figures.

Kept free of any Dash-specific concerns (no callback context, no
component building) so each chart builder can be unit-tested and reused
in isolation. All functions are synchronous/CPU-bound by design; callers
that need to keep an async event loop responsive should run them via
``asyncio.to_thread`` (see ``dashboard.callbacks``).
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from dashboard.config import Config
from dashboard.data import DATA

logger = logging.getLogger(__name__)

_DARK_TEMPLATE = "plotly_dark"
_LIGHT_TEMPLATE = "plotly_white"
_DARK_GRID = "rgba(255,255,255,0.1)"
_LIGHT_GRID = "LightGray"


class Visualizer:
    """Namespace of chart-building helpers used by the dashboard."""

    @staticmethod
    def apply_standard_style(
        fig: go.Figure,
        theme: str = "dark",
        x_label: str | None = None,
        y_label: str | None = None,
    ) -> None:
        """Apply the dashboard's shared look & feel to a figure, in place."""
        is_dark = theme == "dark"
        fig.update_layout(
            template=_DARK_TEMPLATE if is_dark else _LIGHT_TEMPLATE,
            hovermode="x",
            margin=dict(t=50, b=40, l=40, r=20),
        )
        grid_color = _DARK_GRID if is_dark else _LIGHT_GRID
        fig.update_xaxes(title_text=x_label, showgrid=True, gridcolor=grid_color, showspikes=True, spikemode="across")
        fig.update_yaxes(title_text=y_label, showgrid=True, gridcolor=grid_color, showspikes=True, spikemode="across")

    @staticmethod
    def create_main_price_chart(
        start: pd.Timestamp, end: pd.Timestamp, selected_tickers: list[str], mode: str
    ) -> go.Figure:
        """Rebased price + mention-delta + mention-total, one row each, shared x-axis."""
        fig = make_subplots(
            rows=3, cols=1, shared_xaxes=True,
            subplot_titles=("Price (Base)", "Reference Delta", "Reference Total"),
            row_heights=[0.6, 0.2, 0.2], vertical_spacing=0.1,
        )
        for ticker in selected_tickers:
            sub_price = DATA.quotes_clean.loc[start:end, ticker]
            sub_diff = DATA.mentions_diff.loc[start:end, ticker]
            if sub_price.empty:
                continue
            rebased = sub_price - sub_price.iloc[0]
            color = Config.TICKER_COLORS[ticker]
            fig.add_trace(go.Scatter(x=sub_price.index, y=rebased, name=ticker, line=dict(color=color), legend="legend1"), row=1, col=1)
            fig.add_trace(go.Bar(x=sub_diff.index, y=sub_diff.values, name=ticker, marker_color=color, legend="legend2"), row=2, col=1)
            fig.add_trace(go.Scatter(x=sub_diff.index, y=sub_diff.values, name=ticker, mode="lines+markers", line=dict(color=color), legend="legend3"), row=3, col=1)

        Visualizer.apply_standard_style(fig, mode, y_label="Percent")
        fig.update_layout(
            barmode="stack",
            legend1=dict(y=1), legend2=dict(y=0.25), legend3=dict(y=0), legend2_traceorder="normal",
            xaxis=dict(title=None), xaxis2=dict(title=None), xaxis3=dict(title="Date"),
            yaxis=dict(title="Percent"), yaxis2=dict(title="Ref"), yaxis3=dict(title="Ref"),
        )
        return fig

    @staticmethod
    def create_correlation_heatmap(df_sub: pd.DataFrame, mode: str) -> go.Figure:
        """Ticker-vs-ticker correlation heatmap for the given (already sliced) data."""
        if df_sub.empty or df_sub.shape[1] < 1:
            logger.debug("Skipping correlation heatmap: no columns/rows in selection")
            return go.Figure()

        corr = df_sub.corr().sort_index(axis=0, ascending=False).sort_index(axis=1, ascending=True)
        fig = go.Figure(
            go.Heatmap(
                z=corr.values, x=corr.columns, y=corr.index, colorscale="Inferno",
                showscale=False, text=np.round(corr.values, 2), texttemplate="%{text}",
            )
        )
        Visualizer.apply_standard_style(fig, mode)
        return fig

    @staticmethod
    def _radar_metrics_for_ticker(ticker: str, start: pd.Timestamp, end: pd.Timestamp) -> dict | None:
        """Compute the raw (un-normalized) radar metrics for a single ticker, or None if no data."""
        mentions = DATA.mentions.loc[start:end, ticker]
        prices = DATA.quotes_clean.loc[start:end, ticker]
        if prices.empty:
            return None

        daily_returns = np.diff(prices.values)
        volatility = prices.std() or 1e-9
        max_growth = prices.max()
        total_mentions = mentions.sum()
        min_idx = prices.idxmin()
        tail_from_min = prices.loc[min_idx:]
        mean_abs_return = np.mean(np.abs(daily_returns)) if len(daily_returns) else 0.0
        std_return = np.std(daily_returns) if len(daily_returns) else 0.0
        negative_returns = daily_returns[daily_returns < 0]

        return {
            "Ticker": ticker,
            "Max Growth": max_growth,
            "Volatility": volatility,
            "Stability": 1 / volatility,
            "Consistency": (prices.diff().fillna(0) > 0).mean() * 100,
            "Recovery": (tail_from_min.max() - tail_from_min.min()) / max(len(tail_from_min), 1),
            "Coef. of Var.": (std_return / mean_abs_return) if mean_abs_return != 0 else 0,
            "Sharpe": (np.mean(daily_returns) / std_return) if std_return != 0 else 0,
            "Sortino": (
                np.mean(daily_returns) / np.std(negative_returns)
                if len(negative_returns) > 0 and np.std(negative_returns) != 0
                else 0
            ),
            "Risk-Adj Return": max_growth / volatility,
            "Total References": total_mentions,
            "Ref. Efficiency": (max_growth / (total_mentions + 1)) * 1000,
            "Social Impact": mentions.corr(prices.shift(-1).fillna(0)),
        }

    @staticmethod
    def create_radar_chart(selected_tickers: list[str], start: pd.Timestamp, end: pd.Timestamp, mode: str) -> go.Figure:
        """Normalized multi-metric radar comparison across the selected tickers."""
        radar_rows = [
            row for t in selected_tickers
            if (row := Visualizer._radar_metrics_for_ticker(t, start, end)) is not None
        ]

        fig = go.Figure()
        if radar_rows:
            df_radar = pd.DataFrame(radar_rows).set_index("Ticker")
            radar_norm = (df_radar - df_radar.min()) / (df_radar.max() - df_radar.min() + 1e-9)
            categories = radar_norm.columns.tolist()
            for ticker in radar_norm.index:
                values = radar_norm.loc[ticker].values.tolist()
                fig.add_trace(
                    go.Scatterpolar(
                        r=values + [values[0]], theta=categories + [categories[0]],
                        fill="toself", name=ticker,
                        line=dict(color=Config.TICKER_COLORS.get(ticker), width=3),
                    )
                )
        else:
            logger.debug("Skipping radar chart: no data for selected tickers")

        Visualizer.apply_standard_style(fig, mode)
        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
            showlegend=True, legend=dict(orientation="h"), margin=dict(t=80, b=80, l=80, r=80),
        )
        return fig
