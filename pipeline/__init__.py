"""Source-data reproduction pipeline for the Crypto Sentiment & Market Dashboard.

Standalone and optional: regenerates the two CSVs `dashboard/data/loader.py`
reads (daily ticker mention counts + LLM-generated topics, and normalized
market quotes) from the raw news dataset and market data. Not imported by,
and not a runtime dependency of, `dashboard/` -- see pipeline/README.md.
"""

__version__ = "1.0.0"
