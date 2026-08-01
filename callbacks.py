# CALLBACKS

from dash import Output, Input, callback_context, dcc, html, dash_table
import dash_mantine_components as dmc
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import timedelta
import re
from sklearn.linear_model import LinearRegression

from layout import app
from config import Config
from data_layer import DF_REPORT, DF_MENTIONS, QUOTES_CLEAN
from vis_helpers import Visualizer


@app.callback(Output("mantine-provider", "forceColorScheme"), Input("theme-toggle", "checked"))
def toggle_theme(checked): return "dark" if checked else "light"

@app.callback(
    [Output('main-price-graph', 'figure'), Output('corr-price', 'figure'), Output('corr-ref', 'figure'),
     Output('radar-graph', 'figure'), Output('regression-container', 'children'), Output('topics-table', 'data'),
     Output('perf-panels-top', 'children'), Output('date-range', 'value'), Output('topics-table', 'style_cell'),
     Output('topics-table', 'style_header'), Output('topics-table', 'style_data'), Output('main-title', 'style')],
    [Input('ticker-select', 'value'), Input('date-range', 'value'), Input('btn-1m', 'n_clicks'),
     Input('btn-3m', 'n_clicks'), Input('btn-6m', 'n_clicks'), Input('btn-9m', 'n_clicks'), Input('btn-12m', 'n_clicks'),
     Input('btn-all', 'n_clicks'), Input('mantine-provider', 'forceColorScheme')]
)
def update_dashboard(selected_tickers, date_range, n1, n3, n6, n9, n12, n_all, mode):
    mode = mode or 'dark'
    trigger = callback_context.triggered[0]['prop_id'].split('.')[0] if callback_context.triggered else None
    max_d, min_d = DF_REPORT['date'].max().date(), DF_REPORT['date'].min().date()

    if trigger == 'btn-1m': date_range = [max_d - timedelta(days=30), max_d]
    elif trigger == 'btn-3m': date_range = [max_d - timedelta(days=90), max_d]
    elif trigger == 'btn-6m': date_range = [max_d - timedelta(days=180), max_d]
    elif trigger == 'btn-9m': date_range = [max_d - timedelta(days=270), max_d]
    elif trigger == 'btn-12m': date_range = [max_d - timedelta(days=360), max_d]
    elif trigger == 'btn-all': date_range = [min_d, max_d]

    start, end = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])

    fig_price = Visualizer.create_main_price_chart(start, end, selected_tickers, mode)
    fig_radar = Visualizer.create_radar_chart(selected_tickers, start, end, mode)
    fig_corr_p = Visualizer.create_correlation_heatmap(QUOTES_CLEAN.loc[start:end, selected_tickers], mode)
    fig_corr_r = Visualizer.create_correlation_heatmap(DF_MENTIONS.loc[start:end, selected_tickers], mode)

    reg_snippets = []
    for t in selected_tickers:
        m_v, p_v = DF_MENTIONS.loc[start:end, t].values.reshape(-1, 1), QUOTES_CLEAN.loc[start:end, t].values
        if len(m_v) > 5:
            model = LinearRegression().fit(m_v, p_v)
            f_reg = go.Figure()
            f_reg.add_trace(go.Scatter(x=m_v.flatten(), y=p_v, mode='markers', marker=dict(color=Config.TICKER_COLORS[t])))
            f_reg.add_trace(go.Scatter(x=m_v.flatten(), y=model.predict(m_v), line=dict(color=Config.TICKER_COLORS[t])))
            Visualizer.apply_standard_style(f_reg, mode); f_reg.update_layout(height=150, showlegend=False, margin=dict(t=5, b=5))
            reg_snippets.append(dmc.Stack([dmc.Text(t, size="xs", fw=700, ta="center"), dmc.Paper([dcc.Graph(figure=f_reg, config={'displayModeBar': False})], withBorder=True, radius="sm", shadow="xs", mb="xs")]))

    table_df = DF_REPORT[(DF_REPORT['date'] >= start) & (DF_REPORT['date'] <= end)].copy()
    table_df = table_df.sort_values('date', ascending=False)
    table_df['date_str'] = table_df['date'].dt.strftime('%Y-%m-%d')
    table_df['clean_topics'] = table_df['top_5_topics'].apply(lambda x: re.sub(r'[^\w\s\d.,!?\-\n*]', '', str(x)))

    theme_colors = {'bg': '#1A1B1E' if mode == 'dark' else '#FFFFFF', 'text': '#C1C2C5' if mode == 'dark' else '#000000', 'border': '#373A40' if mode == 'dark' else '#dee2e6', 'header': '#25262B' if mode == 'dark' else '#f8f9fa'}
    s_cell = {'backgroundColor': theme_colors['bg'], 'color': theme_colors['text'], 'textAlign': 'left', 'border': f'1px solid {theme_colors["border"]}', 'padding': '10px', 'whiteSpace': 'normal', 'font-family': 'sans-serif'}
    s_head = {'backgroundColor': theme_colors['header'], 'color': theme_colors['text'], 'fontWeight': 'bold', 'border': f'1px solid {theme_colors["border"]}', 'font-family': 'sans-serif'}

    perf_items = []
    for t in selected_tickers:
        p_sub = QUOTES_CLEAN.loc[start:end, t]
        val = p_sub.iloc[-1] - p_sub.iloc[0] if not p_sub.empty else 0
        color = "#81c784" if val >= 0 else "#e57373"
        perf_items.append(dmc.Paper([dmc.Text(t, fw=700, size="xs", ta="center", c=color), dmc.Text(f"{val:+.2f}%", size="xs", ta="center", c=color)], withBorder=True, p=5, bg="rgba(0,0,0,0.2)" if mode=='dark' else "#f8f9fa"))

    print(start, end)
    print(QUOTES_CLEAN.loc[start:end].shape)
    
    return (fig_price, fig_corr_p, fig_corr_r, fig_radar, reg_snippets, table_df[['date_str', 'clean_topics']].rename(columns={'date_str':'date'}).to_dict('records'),
            dmc.SimpleGrid(cols=5, children=perf_items), date_range, s_cell, s_head, {'border': f'1px solid {theme_colors["border"]}'}, {'fontWeight': 800, 'color': 'white' if mode == 'dark' else 'black'})
