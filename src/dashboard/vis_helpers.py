from __future__ import annotations
import logging
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.dashboard.config import settings
from src.dashboard.data_layer import DF_DIFF, DF_MENTIONS, QUOTES_CLEAN

logger = logging.getLogger(__name__)

class Visualizer:
    @staticmethod
    def apply_standard_style(fig: go.Figure, theme: str = "dark", x_label: str | None = None, y_label: str | None = None) -> None:
        is_dark = theme == "dark"
        fig.update_layout(template="plotly_dark" if is_dark else "plotly_white", hovermode="x", margin=dict(t=50, b=40, l=40, r=20))
        grid_color = "rgba(255,255,255,0.1)" if is_dark else "LightGray"
        fig.update_xaxes(title_text=x_label, showgrid=True, gridcolor=grid_color, showspikes=True, spikemode="across")
        fig.update_yaxes(title_text=y_label, showgrid=True, gridcolor=grid_color, showspikes=True, spikemode="across")

    @staticmethod
    def create_main_price_chart(start: pd.Timestamp, end: pd.Timestamp, selected_tickers: list[str], mode: str) -> go.Figure:
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True, subplot_titles=("Price (Base)", "Reference Delta", "Reference Total"), row_heights=[0.6, 0.2, 0.2], vertical_spacing=0.1)
        for ticker in selected_tickers:
            sub_price = QUOTES_CLEAN.loc[start:end, ticker]
            sub_diff = DF_DIFF.loc[start:end, ticker]
            if sub_price.empty:
                continue
            rebased = sub_price - sub_price.iloc[0]
            color = settings.ticker_colors.get(ticker, "#FFFFFF")
            fig.add_trace(go.Scatter(x=sub_price.index, y=rebased, name=ticker, line=dict(color=color), legend="legend1"), row=1, col=1)
            fig.add_trace(go.Bar(x=sub_diff.index, y=sub_diff.values, name=ticker, marker_color=color, legend="legend2"), row=2, col=1)
            fig.add_trace(go.Scatter(x=sub_diff.index, y=sub_diff.values, name=ticker, mode="lines+markers", line=dict(color=color), legend="legend3"), row=3, col=1)
        Visualizer.apply_standard_style(fig, mode, y_label="Percent")
        fig.update_layout(barmode="stack", legend1=dict(y=1), legend2=dict(y=0.25), legend3=dict(y=0), xaxis3=dict(title="Date"))
        return fig

    @staticmethod
    def create_correlation_heatmap(df_sub: pd.DataFrame, mode: str) -> go.Figure:
        if df_sub.empty or df_sub.shape[1] < 1:
            return go.Figure()
        corr = df_sub.corr().sort_index(axis=0, ascending=False).sort_index(axis=1, ascending=True)
        fig = go.Figure(go.Heatmap(z=corr.values, x=corr.columns, y=corr.index, colorscale="Inferno", showscale=False, text=np.round(corr.values, 2), texttemplate="%{text}"))
        Visualizer.apply_standard_style(fig, mode)
        return fig

    @staticmethod
    def _radar_metrics_for_ticker(ticker: str, start: pd.Timestamp, end: pd.Timestamp) -> dict[str, Any] | None:
        mentions = DF_MENTIONS.loc[start:end, ticker]
        prices = QUOTES_CLEAN.loc[start:end, ticker]
        if prices.empty:
            return None
        daily_returns = np.diff(prices.values)
        volatility = prices.std() or 1e-9
        return {
            "Ticker": ticker, "Max Growth": prices.max(), "Volatility": volatility,
            "Consistency": (prices.diff().fillna(0) > 0).mean() * 100,
            "Total References": mentions.sum(),
        }

    @staticmethod
    def create_radar_chart(selected_tickers: list[str], start: pd.Timestamp, end: pd.Timestamp, mode: str) -> go.Figure:
        radar_rows = [row for t in selected_tickers if (row := Visualizer._radar_metrics_for_ticker(t, start, end)) is not None]
        fig = go.Figure()
        if radar_rows:
            df_radar = pd.DataFrame(radar_rows).set_index("Ticker")
            radar_norm = (df_radar - df_radar.min()) / (df_radar.max() - df_radar.min() + 1e-9)
            for ticker in radar_norm.index:
                values = radar_norm.loc[ticker].values.tolist()
                fig.add_trace(go.Scatterpolar(r=values + [values[0]], theta=radar_norm.columns.tolist() + [radar_norm.columns.tolist()[0]], fill="toself", name=ticker, line=dict(color=settings.ticker_colors.get(ticker), width=3)))
        Visualizer.apply_standard_style(fig, mode)
        fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 1])), showlegend=True, margin=dict(t=80, b=80, l=80, r=80))
        return fig
