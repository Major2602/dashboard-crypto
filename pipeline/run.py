"""Pipeline entry point: regenerate the dashboard's source CSVs from scratch.

    python -m pipeline.run

Standalone and optional -- see pipeline/README.md. This module is never
imported by ``dashboard/``; running it (or not) has no effect on
``dashboard/app.py`` or the deployed service. It exists purely so the two
CSVs under ``dashboard/data/`` are reproducible from the raw news dataset
and market data, rather than being unauditable, un-regeneratable blobs.
"""

from __future__ import annotations

import logging

from pipeline.config import Config, configure_logging
from pipeline.news import load_and_prepare_data
from pipeline.quotes import fetch_quotes
from pipeline.summarize import run_llm_analysis

logger = logging.getLogger(__name__)


def main() -> None:
    configure_logging()
    Config.validate()

    logger.info(
        "Starting pipeline run: %s to %s, tickers=%s",
        Config.START_DATE, Config.END_DATE, Config.TARGET_TICKERS,
    )

    df_news = load_and_prepare_data()
    df_quotes = fetch_quotes()
    df_report = run_llm_analysis(df_news)

    Config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    quotes_path = Config.OUTPUT_DIR / Config.QUOTES_FILENAME
    report_path = Config.OUTPUT_DIR / Config.REPORT_FILENAME

    # No index column in either file -- dashboard.data.loader aligns the two
    # CSVs by row position, not by a date column in the quotes file (see
    # its docstring), and expects ticker-named columns only.
    df_quotes.to_csv(quotes_path, sep=Config.CSV_SEPARATOR, index=False)
    df_report.to_csv(report_path, sep=Config.CSV_SEPARATOR, index=False)

    logger.info("Wrote %s and %s", quotes_path, report_path)
    logger.info(
        "These are NOT picked up by the dashboard automatically. To use them, "
        "copy/rename both files into dashboard/data/ (or point QUOTES_FILENAME/"
        "REPORT_FILENAME at them) -- see the main README's "
        "'Updating the source data' section."
    )


if __name__ == "__main__":
    main()
