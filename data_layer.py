# DATA LAYER

import pandas as pd
import ast
from typing import Tuple
from config import Config
import numpy as np


class DataManager:
    
    @staticmethod
    def load_and_preprocess() -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        df_q = pd.read_csv(Config.QUOTES_PATH, sep=';').replace(0, np.nan).ffill()
        df_r = pd.read_csv(Config.REPORT_PATH, sep=';')

        def safe_parse_dict(val):
            try: return ast.literal_eval(val)
            except: return {}

        df_r['tickers_dict'] = df_r['tickers_count'].apply(safe_parse_dict)
        df_r['date'] = pd.to_datetime(df_r['date'])
        df_q.index = pd.to_datetime(df_r['date'].values)

        mentions = []
        for _, row in df_r.iterrows():
            entry = {'Date': row['date']}
            for t in Config.TARGET_TICKERS:
                entry[t] = row['tickers_dict'].get(t.lower(), 0)
            mentions.append(entry)

        df_m = pd.DataFrame(mentions).set_index('Date')
        df_d = df_m.diff().fillna(0)

        quotes_renamed = df_q.copy()
        quotes_renamed.columns = [c.split('-')[0] for c in quotes_renamed.columns]

        return df_r, df_q, df_m, df_d, quotes_renamed

DF_REPORT, DF_QUOTES, DF_MENTIONS, DF_DIFF, QUOTES_CLEAN = DataManager.load_and_preprocess()
