from __future__ import annotations

import pandas as pd
import pytest


@pytest.fixture
def sample_report_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"]),
            "tickers_count": [
                "{'ada': 1, 'btc': 355, 'eth': 83, 'sol': 13, 'xrp': 18}",
                "{'ada': None, 'btc': 631, 'eth': 128, 'sol': 31, 'xrp': 9}",
                "{'btc': 400, 'eth': 90, 'sol': 20, 'xrp': 12}",
            ],
            "top_5_topics": [
                "1. **Topic A**: something *bold* & <weird> chars!\n2. Topic B",
                "1. Topic C, with punctuation.",
                "1. Topic D?",
            ],
        }
    )


@pytest.fixture
def sample_quotes_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ADA-USD": [0.0, -2.5, -8.1],
            "BTC-USD": [0.0, 1.8, -3.0],
            "ETH-USD": [0.0, 0.1, -6.0],
            "SOL-USD": [0.0, -2.6, -9.9],
            "XRP-USD": [0.0, -0.7, -7.5],
        }
    )
