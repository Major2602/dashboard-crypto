# CONFIGURATION

# CONFIGURATION

import os
from pathlib import Path
import plotly.express as px

class Config:
    BASE_DIR = Path(__file__).resolve().parent
    TARGET_TICKERS = ['BTC', 'ETH', 'XRP', 'SOL', 'ADA']
    QUOTES_PATH = BASE_DIR / 'data' / 'cr_quotes_base_24.csv'
    REPORT_PATH = BASE_DIR / 'data' / 'cr_report_24.csv'
    
    TICKER_COLORS = {
        t: px.colors.qualitative.Plotly[i % len(px.colors.qualitative.Plotly)] 
        for i, t in enumerate(TARGET_TICKERS)
    }
