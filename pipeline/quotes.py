"""Downloading and normalizing daily market quotes via yfinance."""

from __future__ import annotations

import logging

import pandas as pd
import yfinance as yf

from pipeline.config import Config

logger = logging.getLogger(__name__)


class QuotesLoadError(RuntimeError):
    """Raised when market quotes can't be downloaded for the configured tickers/range."""


def fetch_quotes() -> pd.DataFrame:
    """Download close prices for the configured tickers and rebase each to a % change series.

    Each column is normalized against its own first value in the range
    (day 0 == 0%). Columns are named ``<TICKER>-USD`` (e.g. ``BTC-USD``),
    matching what ``dashboard.data.loader`` expects: it keeps only the
    part before the first ``-`` as the ticker symbol.
    """
    symbols = [f"{t.upper()}-USD" for t in Config.TARGET_TICKERS]
    logger.info("Downloading quotes for %s (%s to %s)", symbols, Config.START_DATE, Config.END_DATE)

    try:
        raw = yf.download(symbols, start=Config.START_DATE, end=Config.END_DATE, progress=False)
    except Exception as exc:
        raise QuotesLoadError(f"Failed to download quotes for {symbols}: {exc}") from exc

    if raw.empty:
        raise QuotesLoadError(f"yfinance returned no data for {symbols} in the configured date range")

    if isinstance(raw.columns, pd.MultiIndex):
        close = raw["Close"]
    else:
        # yfinance collapses to a flat column index when only one ticker is requested.
        close = raw[["Close"]].rename(columns={"Close": symbols[0]})

    missing = [s for s in symbols if s not in close.columns]
    if missing:
        raise QuotesLoadError(f"No quote data returned for: {missing}")
    close = close[symbols]

    if close.iloc[0].isna().any():
        nan_tickers = close.columns[close.iloc[0].isna()].tolist()
        logger.warning(
            "First-day close price missing for %s; their rebased series will stay NaN "
            "until the first non-missing value. Consider a later PIPELINE_START_DATE.",
            nan_tickers,
        )

    return (close / close.iloc[0] - 1) * 100
