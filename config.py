# CONFIGURATION


import os
from pathlib import Path
from typing import List, Dict
import plotly.express as px


class Config:
  
    BASE_DIR: Path = Path(__file__).resolve().parent

    QUOTES_PATH: Path = Path(os.getenv("QUOTES_PATH", BASE_DIR / "data" / "cr_quotes_base.csv"))
    REPORT_PATH: Path = Path(os.getenv("REPORT_PATH", BASE_DIR / "data" / "cr_report.csv"))

    TARGET_TICKERS: List[str] = ["BTC", "ETH", "XRP", "SOL", "ADA"]

    TICKER_COLORS: Dict[str, str] = {
        ticker: px.colors.qualitative.Plotly[i % len(px.colors.qualitative.Plotly)]
        for i, ticker in enumerate(TARGET_TICKERS)
    }
