"""Loading and aggregating the source news dataset from Hugging Face.

Groups raw articles by publication date and counts crypto-ticker mentions
per day using ``pipeline.text_processing``. This module only needs
``pandas``, ``datasets`` and ``tqdm`` -- it does not import vLLM/torch (see
``pipeline/summarize.py`` for that), so it stays fast to import and usable
on machines without a GPU.
"""

from __future__ import annotations

import logging

import pandas as pd
from datasets import load_dataset
from tqdm.auto import tqdm

from pipeline.config import Config
from pipeline.text_processing import get_tickers_count

logger = logging.getLogger(__name__)

_REQUIRED_COLUMNS = {"published_on", "body"}


class NewsLoadError(RuntimeError):
    """Raised when the source news dataset can't be loaded or is empty for the configured range."""


def load_and_prepare_data() -> pd.DataFrame:
    """Load the HF news dataset, filter to the configured date range, and aggregate per day.

    Returns a DataFrame with one row per calendar day in range:
    ``published_on`` (date), ``body`` (that day's article bodies
    concatenated) and ``tickers_dict`` (mention counts per configured
    ticker, from ``pipeline.text_processing.get_tickers_count``).
    """
    logger.info("Loading news dataset %r", Config.HF_DATASET)
    try:
        ds = load_dataset(Config.HF_DATASET, split="train")
    except Exception as exc:
        raise NewsLoadError(f"Failed to load dataset {Config.HF_DATASET!r}: {exc}") from exc

    df_raw = pd.DataFrame(ds)
    missing = _REQUIRED_COLUMNS - set(df_raw.columns)
    if missing:
        raise NewsLoadError(f"Dataset {Config.HF_DATASET!r} is missing required column(s): {sorted(missing)}")

    df_raw["published_on"] = pd.to_datetime(df_raw["published_on"]).dt.date
    mask = (df_raw["published_on"] >= Config.START_DATE) & (df_raw["published_on"] < Config.END_DATE)
    df_filtered = df_raw.loc[mask].copy()

    if df_filtered.empty:
        raise NewsLoadError(
            f"No articles found between {Config.START_DATE} and {Config.END_DATE}. "
            "Check PIPELINE_START_DATE / PIPELINE_END_DATE."
        )

    df_filtered["body"] = df_filtered["body"].fillna("")
    df_agg = df_filtered.groupby("published_on")["body"].apply(" ".join).reset_index()

    logger.info(
        "Aggregated %d articles into %d daily rows; counting ticker mentions...",
        len(df_filtered), len(df_agg),
    )
    tqdm.pandas(desc="Counting ticker mentions")
    df_agg["tickers_dict"] = df_agg["body"].progress_map(
        lambda text: get_tickers_count(text, Config.TARGET_TICKERS)
    )

    return df_agg
