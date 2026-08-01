# DATA LAYER

import pandas as pd
import ast
import logging
from pathlib import Path
from typing import Tuple
from config import Config

logger = logging.getLogger(__name__)

class DataManager:
    
    @staticmethod
    def load_and_preprocess() -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        try:
            quotes_path = Path(Config.QUOTES_PATH)
            report_path = Path(Config.REPORT_PATH)

            if not quotes_path.exists() or not report_path.exists():
                raise FileNotFoundError("Required data files are missing in the data directory.")

            df_q = pd.read_csv(quotes_path, sep=';')
            df_r = pd.read_csv(report_path, sep=';')

            def safe_parse_dict(val: str) -> dict:
                try: 
                    parsed = ast.literal_eval(val)
                    return parsed if isinstance(parsed, dict) else {}
                except Exception: 
                    return {}

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
            quotes_renamed.columns = [str(c).split('-')[0] for c in quotes_renamed.columns]

            return df_r, df_q, df_m, df_d, quotes_renamed
            
        except Exception as e:
            logger.error(f"Failed to load and preprocess data: {e}")
            raise

DF_REPORT, DF_QUOTES, DF_MENTIONS, DF_DIFF, QUOTES_CLEAN = DataManager.load_and_preprocess()
