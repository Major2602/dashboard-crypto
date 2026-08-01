# VISUALIZATION HELPERS

# VISUALIZATION HELPERS

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from config import Config
from data_layer import QUOTES_CLEAN, DF_DIFF, DF_MENTIONS


class Visualizer:
    
    @staticmethod
    def apply_standard_style(fig: go.Figure, theme: str = 'dark', x_label: str = None, y_label: str = None) -> None:
        template = 'plotly_dark' if theme == 'dark' else 'plotly_white'
        grid_color = 'rgba(255,255,255,0.1)' if theme == 'dark' else 'LightGray'
        fig.update_layout(template=template, hovermode='x', margin=dict(t=50, b=40, l=40, r=20))
        fig.update_xaxes(title_text=x_label, showgrid=True, gridcolor=grid_color, showspikes=True, spikemode='across')
        fig.update_yaxes(title_text=y_label, showgrid=True, gridcolor=grid_color, showspikes=True, spikemode='across')

    @staticmethod
    def create_main_price_chart(start: pd.Timestamp, end: pd.Timestamp, selected_tickers: list, mode: str) -> go.Figure:
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True,
                            subplot_titles=("Price (Base)", "Reference Delta", "Reference Total"),
                            row_heights=[0.6, 0.2, 0.2], vertical_spacing=0.1)
        for t in selected_tickers:
            if t not in QUOTES_CLEAN.columns or t not in DF_DIFF.columns:
                continue
            sub_p, sub_d = QUOTES_CLEAN.loc[start:end, t], DF_DIFF.loc[start:end, t]
            if not sub_p.empty:
                rebased, color = sub_p - sub_p.iloc[0], Config.TICKER_COLORS.get(t, '#ffffff')
                fig.add_trace(go.Scatter(x=sub_p.index, y=rebased, name=t, line=dict(color=color), legend='legend1'), row=1, col=1)
                fig.add_trace(go.Bar(x=sub_d.index, y=sub_d.values, name=t, marker_color=color, legend='legend2'), row=2, col=1)
                fig.add_trace(go.Scatter(x=sub_d.index, y=sub_d.values, name=t, mode='lines+markers', line=dict(color=color), legend='legend3'), row=3, col=1)
        Visualizer.apply_standard_style(fig, mode, y_label="Percent")
        fig.update_layout(barmode='stack', legend1=dict(y=1), legend2=dict(y=0.25), legend3=dict(y=0), legend2_traceorder='normal', xaxis=dict(title=None), xaxis2=dict(title=None), xaxis3=dict(title='Date'), yaxis=dict(title='Percent'), yaxis2=dict(title='Ref'), yaxis3=dict(title='Ref'))
        return fig

    @staticmethod
    def create_correlation_heatmap(df_sub: pd.DataFrame, mode: str) -> go.Figure:
        if df_sub.empty or df_sub.shape[1] < 1: 
            return go.Figure()
        corr = df_sub.corr().sort_index(axis=0, ascending=False).sort_index(axis=1, ascending=True)
        fig = go.Figure(go.Heatmap(z=corr.values, x=corr.columns, y=corr.index, colorscale='Inferno',
                                   showscale=False, text=np.round(corr.values, 2), texttemplate="%{text}"))
        Visualizer.apply_standard_style(fig, mode)
        return fig

    @staticmethod
    def create_radar_chart(selected_tickers: list, start: pd.Timestamp, end: pd.Timestamp, mode: str) -> go.Figure:
        radar_data = []
        for t in selected_tickers:
            if t not in DF_MENTIONS.columns or t not in QUOTES_CLEAN.columns:
                continue
            m, p = DF_MENTIONS.loc[start:end, t], QUOTES_CLEAN.loc[start:end, t]
            if p.empty: 
                continue
            prices, daily_returns = p.values, np.diff(p.values)
            total_mentions, max_growth, volatility = m.sum(), p.max(), p.std() or 1e-9
            
            mean_abs_ret = np.mean(np.abs(daily_returns))
            cov = np.std(daily_returns) / mean_abs_ret if mean_abs_ret != 0 else 0
            std_ret = np.std(daily_returns)
            mean_ret = np.mean(daily_returns)
            sharpe = mean_ret / std_ret if std_ret != 0 else 0
            
            neg_ret = daily_returns[daily_returns < 0]
            std_neg = np.std(neg_ret) if len(neg_ret) > 0 else 0
            sortino = mean_ret / std_neg if len(neg_ret) > 0 and std_neg != 0 else 0

            min_idx = p.idxmin()
            rec_slice = p.loc[min_idx:] if min_idx in p.index else p
            recovery_val = (rec_slice.max() - rec_slice.min()) / max(len(rec_slice), 1)

            radar_data.append({
                'Ticker': t, 'Max Growth': max_growth, 'Volatility': volatility, 'Stability': 1/volatility,
                'Consistency': (p.diff().fillna(0) > 0).mean() * 100, 'Recovery': recovery_val,
                'Coef. of Var.': cov, 'Sharpe': sharpe, 'Sortino': sortino,
                'Risk-Adj Return': max_growth/volatility, 'Total References': total_mentions, 
                'Ref. Efficiency': (max_growth/(total_mentions + 1)) * 1000, 
                'Social Impact': m.corr(p.shift(-1).fillna(0)) if len(m) > 1 else 0
            })
            
        fig = go.Figure()
        if radar_data:
            df_radar_sub = pd.DataFrame(radar_data).set_index('Ticker')
            denom = (df_radar_sub.max() - df_radar_sub.min()) + 1e-9
            radar_norm = (df_radar_sub - df_radar_sub.min()) / denom
            cats = radar_norm.columns.tolist()
            for t in radar_norm.index:
                val = radar_norm.loc[t].values.tolist()
                fig.add_trace(go.Scatterpolar(r=val + [val[0]], theta=cats + [cats[0]], fill='tossel', name=t, line=dict(color=Config.TICKER_COLORS.get(t, '#ffffff'), width=3)))
        Visualizer.apply_standard_style(fig, mode)
        fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 1])), showlegend=True, legend=dict(orientation='h'), margin=dict(t=80, b=80, l=80, r=80))
        return fig
