# CONFIGURATION


class Config:
  
    TARGET_TICKERS = ['BTC', 'ETH', 'XRP', 'SOL', 'ADA']
  
    QUOTES_PATH = 'data/cr_quotes_base.csv'
  
    REPORT_PATH = 'data/cr_report.csv'
  
    TICKER_COLORS = {t:  px.colors.qualitative.Plotly[i % len( px.colors.qualitative.Plotly)] for i, t in enumerate(TARGET_TICKERS)}
