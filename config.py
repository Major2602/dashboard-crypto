# CONFIGURATION

import plotly.express as px

class Config:
  
    TARGET_TICKERS = ['BTC', 'ETH', 'XRP', 'SOL', 'ADA']
  
    QUOTES_PATH = 'data/cr_quotes_base_24.csv'
  
    REPORT_PATH = 'data/cr_report_24.csv'
  
    TICKER_COLORS = {t:  px.colors.qualitative.Plotly[i % len(px.colors.qualitative.Plotly)] for i, t in enumerate(TARGET_TICKERS)}
