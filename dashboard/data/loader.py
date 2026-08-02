"""Loading and preprocessing of the dashboard's source CSV data.

The public loading API is asynchronous (`DataManager.load`) so it can be
awaited from async Dash callbacks, or from a future periodic-refresh task,
without blocking the event loop. Blocking work (pandas file I/O and
CPU-bound preprocessing) is offloaded to a worker thread via
``asyncio.to_thread``.

Dash builds the layout synchronously at import time and needs the data
frames immediately, so a small bootstrap at the bottom of this module runs
the async loader once via ``asyncio.run`` and exposes the results as a
module-level ``DATA`` bundle, preserving the synchronous-import contract
relied on elsewhere in the app.
"""

from __future__ import annotations

import ast
import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from dashboard.config import Config

logger = logging.getLogger(__name__)


class DataLoadError(RuntimeError):
    """Raised when source CSV files cannot be found, read, parsed or validated."""


def _safe_parse_dict(value: Any) -> dict:
    """Best-effort parse of a stringified dict; never raises."""
    try:
        parsed = ast.literal_eval(value)
    except (ValueError, SyntaxError, TypeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _mention_count(tickers_dict: dict, ticker: str) -> float:
    """Extract a ticker's raw mention count for one day.

    Returns ``NaN`` when the ticker's key is missing OR explicitly
    ``null`` in the source dict (e.g. ``{"ada": None, "btc": 214, ...}``).
    ``dict.get(key, 0)`` only falls back to a default when the key is
    *absent*, so a plain ``.get(ticker.lower(), 0)`` would let an explicit
    ``None`` straight through. The caller is responsible for filling these
    gaps (see ``_fill_missing_mentions``); we intentionally do NOT zero
    them out here, since a missing count is a data-collection gap, not
    genuinely "zero mentions that day".
    """
    value = tickers_dict.get(ticker.lower())
    if value is None:
        return float("nan")
    try:
        return float(value)
    except (TypeError, ValueError):
        logger.warning("Non-numeric mention count for %s: %r; treating as missing", ticker, value)
        return float("nan")


def _fill_missing_mentions(df_mentions: pd.DataFrame) -> pd.DataFrame:
    """Forward-fill gaps in daily mention counts, without looking ahead.

    A handful of rows in the source data have an explicit ``null`` mention
    count for a ticker (a collection gap), rather than a genuine zero.
    Substituting 0 for those rows created artificial dips/spikes in the
    mentions series and produced ``NaN`` propagation into downstream
    calculations (e.g. the regression fit would fail for any date range
    spanning one of these gaps). Carrying the previous day's value forward
    is the more defensible assumption -- "no new data" rather than
    "activity dropped to zero".

    Deliberately NOT back-filled: a gap at the very start of a series has
    no earlier value to carry forward, and pulling one in from a *later*
    date would mean today's value depends on the future -- look-ahead
    bias, which is exactly what you don't want feeding a regression over
    time. Any such leading gap is left as 0 instead (logged clearly, since
    it's a distinct assumption from the forward-fill case above).
    """
    missing_counts = df_mentions.isna().sum()
    if missing_counts.any():
        logger.info(
            "Forward-filling missing mention counts: %s",
            missing_counts[missing_counts > 0].to_dict(),
        )

    df_mentions = df_mentions.sort_index().ffill()

    if df_mentions.isna().any().any():
        leading_gaps = df_mentions.isna().sum()
        logger.warning(
            "Leading gap(s) with no prior value to forward-fill from (no "
            "history yet): %s. Defaulting to 0 rather than back-filling "
            "from a later date, to avoid look-ahead bias.",
            leading_gaps[leading_gaps > 0].to_dict(),
        )
        df_mentions = df_mentions.fillna(0)

    return df_mentions.astype(int)


@dataclass(frozen=True)
class DataBundle:
    """All DataFrames the dashboard needs, pre-processed and aligned."""

    report: pd.DataFrame          # one row per report date, incl. parsed topics
    quotes: pd.DataFrame          # raw quotes, columns like "BTC-USD"
    mentions: pd.DataFrame        # ticker mention counts, indexed by date
    mentions_diff: pd.DataFrame   # day-over-day delta of mentions
    quotes_clean: pd.DataFrame    # quotes with ticker-only columns ("BTC"), date-indexed

    def valid_tickers(self, requested: list[str] | None) -> list[str]:
        """Filter a client-supplied ticker list down to ones we actually have data for.

        Dash callback inputs come from the browser as raw JSON, so a
        ``MultiSelect``'s allowed ``data`` list is only a UI-level
        constraint -- a client could POST an arbitrary value directly to
        the ``_dash-update-component`` endpoint. Every callback that
        indexes into ``TICKER_COLORS`` or a per-ticker DataFrame column
        should filter through this first rather than trusting the input,
        so a request such as ``ticker-select=DROP_TABLE`` degrades to "no
        data for that ticker" instead of raising a ``KeyError``.
        """
        if not requested:
            return []
        allowed = set(self.quotes_clean.columns)
        return [t for t in requested if t in allowed]


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

        if df_report.empty:
            raise DataLoadError("Report CSV has no rows")
        if df_quotes.empty:
            raise DataLoadError("Quotes CSV has no rows")

        df_report = df_report.copy()
        df_report["tickers_dict"] = df_report["tickers_count"].apply(_safe_parse_dict)
        df_report["date"] = pd.to_datetime(df_report["date"], errors="coerce")
        if df_report["date"].isna().any():
            bad = int(df_report["date"].isna().sum())
            raise DataLoadError(f"Report CSV has {bad} row(s) with an unparseable date")

        df_quotes = df_quotes.copy()
        quote_tickers = {c.split("-")[0] for c in df_quotes.columns}
        missing_tickers = set(Config.TARGET_TICKERS) - quote_tickers
        if missing_tickers:
            raise DataLoadError(
                f"Quotes CSV is missing column(s) for configured tickers: {sorted(missing_tickers)}"
            )

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
                **{t: _mention_count(row["tickers_dict"], t) for t in Config.TARGET_TICKERS},
            }
            for _, row in df_report.iterrows()
        ]
        df_mentions = pd.DataFrame(mentions_records).set_index("Date")
        df_mentions = _fill_missing_mentions(df_mentions)
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


def bootstrap() -> DataBundle:
    """Synchronously run the async loader once, at import time.

    The layout module needs the data frames immediately and synchronously
    when it is imported to build the Dash layout, so this can't be
    deferred to a running event loop. ``asyncio.run`` is safe here since
    nothing else is running an event loop yet at module-import time.
    """
    try:
        return asyncio.run(DataManager.load())
    except DataLoadError:
        logger.exception("Could not load dashboard data at startup")
        raise


DATA = bootstrap()
