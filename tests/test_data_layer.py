import pandas as pd
import numpy as np
from src.dashboard.data_layer import _fill_missing_mentions, _mention_count

def test_mention_count_parsing():
    valid_dict = {"btc": 100, "eth": 50, "ada": None}
    assert _mention_count(valid_dict, "BTC") == 100.0
    assert _mention_count(valid_dict, "XRP") is np.nan

def test_fill_missing_mentions():
    df = pd.DataFrame({
        "BTC": [0, np.nan, 5],
        "ETH": [np.nan, 2, np.nan]
    }, index=pd.date_range("2023-01-01", periods=3))
    
    filled = _fill_missing_mentions(df)
    
    assert filled.iloc[1]["BTC"] == 0  # Forward fill from index 0
    assert filled.iloc[2]["BTC"] == 5
    assert filled.iloc[0]["ETH"] == 0  # Leading gap -> 0
    assert filled.iloc[2]["ETH"] == 2  # Forward fill from index 1
