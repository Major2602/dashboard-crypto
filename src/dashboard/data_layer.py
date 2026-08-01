"""Loading and preprocessing of the dashboard's source CSV data."""
from __future__ import annotations

import ast
import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
from src.dashboard.config import settings

logger = logging.getLogger(__name__)

class DataLoadError(RuntimeError):
    pass

def _safe_parse_dict(value: Any) -> dict[str, Any]:
    try:
        parsed = ast.literal_eval(value)
    except (ValueError, SyntaxError, TypeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}

def _mention_count(tickers_dict: dict[str, Any], ticker: str) -> float:
    value = tickers_dict.get(ticker.lower())
    if value is None:
        return float("nan")
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")

def _fill_missing_mentions(df_mentions: pd.DataFrame) -> pd.DataFrame:
    df_mentions = df_mentions.sort_index().ffill()
    if df_mentions.isna().any().any():
        df_mentions = df_mentions.fillna(0)
    return df_mentions.astype(int)

@dataclass(frozen=True)
class DataBundle:
    report: pd.DataFrame
    quotes: pd.DataFrame
    mentions: pd.DataFrame
    mentions_diff: pd.DataFrame
    quotes_clean: pd.DataFrame

class DataManager:
    @staticmethod
    async def _read_csv(path: Path, sep: str) -> pd.DataFrame:
        if not path.exists():
            raise DataLoadError(f"Data file not found: {path}")
        return await asyncio.to_thread(pd.read_csv, path, sep=sep)

    @classmethod
    async def load(cls, quotes_path: Path, report_path: Path, sep: str, target_tickers: tuple[str, ...]) -> DataBundle:
        """Dependency Injected Load Function."""
        df_quotes, df_report = await asyncio.gather(
            cls._read_csv(quotes_path, sep),
            cls._read_csv(report_path, sep),
        )

        df_report, df_quotes, df_mentions, df_diff, quotes_clean = await asyncio.to_thread(
            cls._preprocess, df_report, df_quotes, target_tickers
        )

        return DataBundle(
            report=df_report, quotes=df_quotes, mentions=df_mentions,
            mentions_diff=df_diff, quotes_clean=quotes_clean,
        )

    @staticmethod
    def _preprocess(
        df_report: pd.DataFrame, df_quotes: pd.DataFrame, target_tickers: tuple[str, ...]
    ) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        df_report = df_report.copy()
        df_report["tickers_dict"] = df_report["tickers_count"].apply(_safe_parse_dict)
        df_report["date"] = pd.to_datetime(df_report["date"])

        df_quotes = df_quotes.copy()
        aligned_len = min(len(df_quotes), len(df_report))
        df_quotes = df_quotes.iloc[:aligned_len].copy()
        df_quotes.index = pd.to_datetime(df_report["date"].values[:aligned_len])

        mentions_records = [
            {
                "Date": row["date"],
                **{t: _mention_count(row["tickers_dict"], t) for t in target_tickers},
            }
            for _, row in df_report.iterrows()
        ]
        df_mentions = pd.DataFrame(mentions_records).set_index("Date")
        df_mentions = _fill_missing_mentions(df_mentions)
        df_diff = df_mentions.diff().fillna(0)

        quotes_clean = df_quotes.copy()
        quotes_clean.columns = [str(c).split("-")[0] for c in quotes_clean.columns]

        return df_report, df_quotes, df_mentions, df_diff, quotes_clean

def _bootstrap() -> DataBundle:
    return asyncio.run(DataManager.load(
        settings.quotes_path, 
        settings.report_path, 
        settings.csv_separator, 
        settings.target_tickers
    ))

_bundle = _bootstrap()
DF_REPORT, DF_QUOTES, DF_MENTIONS, DF_DIFF, QUOTES_CLEAN = (
    _bundle.report, _bundle.quotes, _bundle.mentions, _bundle.mentions_diff, _bundle.quotes_clean
)
