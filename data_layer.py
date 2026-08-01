# DATA LAYER
"""Loading and preprocessing of the dashboard's source CSV data.

The public loading API is asynchronous (`DataManager.load`) so it can be
awaited from async Dash callbacks, or from a future periodic-refresh task,
without blocking the event loop. Blocking work (pandas file I/O and
CPU-bound preprocessing) is offloaded to a worker thread via
``asyncio.to_thread``.

Dash builds ``layout.py`` synchronously at import time and needs the
data frames immediately, so a small bootstrap at the bottom of this
module runs the async loader once via ``asyncio.run`` and exposes the
results as module-level constants (``DF_REPORT``, ``DF_QUOTES``, ...),
preserving the synchronous-import contract relied on elsewhere in the
app.
"""

from __future__ import annotations

import ast
import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from config import Config

logger = logging.getLogger(__name__)


class DataLoadError(RuntimeError):
    """Raised when source CSV files cannot be found, read or parsed."""


def _safe_parse_dict(value: Any) -> dict:
    """Best-effort parse of a stringified dict; never raises."""
    try:
        parsed = ast.literal_eval(value)
    except (ValueError, SyntaxError, TypeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


@dataclass(frozen=True)
class DataBundle:
    """All DataFrames the dashboard needs, pre-processed and aligned."""

    report: pd.DataFrame          # one row per report date, incl. parsed topics
    quotes: pd.DataFrame          # raw quotes, columns like "BTC-USD"
    mentions: pd.DataFrame        # ticker mention counts, indexed by date
    mentions_diff: pd.DataFrame   # day-over-day delta of mentions
    quotes_clean: pd.DataFrame    # quotes with ticker-only columns ("BTC"), date-indexed


class DataManager:
    """Loads and preprocesses the dashboard's source CSV files asynchronously."""

    @staticmethod
    async def _read_csv(path: Path, sep: str) -> pd.DataFrame:
        """Read a CSV in a worker thread (pandas I/O is blocking)."""
        if not path.exists():
            raise DataLoadError(f"Data file not found: {path}")
        try:
            return await asyncio.to_thread(pd.read_csv, path, sep=sep)
        except Exception as exc:  # pragma: no cover - defensive, re-raised as domain error
            raise DataLoadError(f"Failed to read {path}: {exc}") from exc

    @classmethod
    async def load(cls) -> DataBundle:
        """Load, validate and preprocess all source data.

        The two CSV reads run concurrently; the CPU-bound preprocessing
        that depends on both of them runs afterwards, also off the event
        loop.
        """
        logger.info("Loading source data from %s and %s", Config.QUOTES_PATH, Config.REPORT_PATH)

        df_quotes, df_report = await asyncio.gather(
            cls._read_csv(Config.QUOTES_PATH, Config.CSV_SEPARATOR),
            cls._read_csv(Config.REPORT_PATH, Config.CSV_SEPARATOR),
        )

        df_report, df_quotes, df_mentions, df_diff, quotes_clean = await asyncio.to_thread(
            cls._preprocess, df_report, df_quotes
        )

        logger.info(
            "Loaded %d report rows, %d quote rows, tickers=%s",
            len(df_report), len(df_quotes), list(Config.TARGET_TICKERS),
        )
        return DataBundle(
            report=df_report,
            quotes=df_quotes,
            mentions=df_mentions,
            mentions_diff=df_diff,
            quotes_clean=quotes_clean,
        )

    @staticmethod
    def _preprocess(
        df_report: pd.DataFrame, df_quotes: pd.DataFrame
    ) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """CPU-bound preprocessing; kept pure/synchronous and run in a worker thread."""
        required_report_cols = {"date", "tickers_count", "top_5_topics"}
        missing = required_report_cols - set(df_report.columns)
        if missing:
            raise DataLoadError(f"Report CSV is missing required columns: {sorted(missing)}")

        df_report = df_report.copy()
        df_report["tickers_dict"] = df_report["tickers_count"].apply(_safe_parse_dict)
        df_report["date"] = pd.to_datetime(df_report["date"])

        df_quotes = df_quotes.copy()
        if len(df_quotes) != len(df_report):
            logger.warning(
                "Quotes file has %d rows but report file has %d; aligning by "
                "position on the shorter length. Verify the source files are in sync.",
                len(df_quotes), len(df_report),
            )
        aligned_len = min(len(df_quotes), len(df_report))
        df_quotes = df_quotes.iloc[:aligned_len].copy()
        df_quotes.index = pd.to_datetime(df_report["date"].values[:aligned_len])

        mentions_records = [
            {
                "Date": row["date"],
                **{t: row["tickers_dict"].get(t.lower(), 0) for t in Config.TARGET_TICKERS},
            }
            for _, row in df_report.iterrows()
        ]
        df_mentions = pd.DataFrame(mentions_records).set_index("Date")
        df_diff = df_mentions.diff().fillna(0)

        quotes_clean = df_quotes.copy()
        quotes_clean.columns = [c.split("-")[0] for c in quotes_clean.columns]

        return df_report, df_quotes, df_mentions, df_diff, quotes_clean


async def refresh() -> DataBundle:
    """Re-read and reprocess source data on demand (e.g. from a scheduled task).

    Not wired into any callback today (the dashboard's UI has no refresh
    control), but exposed so a future periodic-refresh job or admin route
    can call it without touching the loading logic.
    """
    return await DataManager.load()


def _bootstrap() -> DataBundle:
    """Synchronously run the async loader once, at import time.

    ``layout.py`` needs the data frames immediately and synchronously
    when it is imported to build the Dash layout, so this can't be
    deferred to a running event loop. ``asyncio.run`` is safe here since
    nothing else is running an event loop yet at module-import time.
    """
    try:
        return asyncio.run(DataManager.load())
    except DataLoadError:
        logger.exception("Could not load dashboard data at startup")
        raise


_bundle = _bootstrap()

# Backwards-compatible module-level names relied on by layout.py / callbacks.py
DF_REPORT = _bundle.report
DF_QUOTES = _bundle.quotes
DF_MENTIONS = _bundle.mentions
DF_DIFF = _bundle.mentions_diff
QUOTES_CLEAN = _bundle.quotes_clean
