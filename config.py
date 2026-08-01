# CONFIGURATION
"""Application configuration.

Every environment-dependent value (data location, host/port, log level,
debug flag) is read from an environment variable with a safe local
default, so the exact same code runs unchanged on a laptop, in CI, and on
Render (where these are set as service environment variables).

``Config`` intentionally stays a plain class with class-level attributes
(not a dataclass instance) so existing call sites such as
``Config.TARGET_TICKERS`` or ``Config.TICKER_COLORS[t]`` keep working
without any changes to callers -- notably ``layout.py``, which must not
change.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

import plotly.express as px

BASE_DIR = Path(__file__).resolve().parent


def _split_env_list(name: str, default: str) -> tuple[str, ...]:
    """Parse a comma-separated env var into a tuple, falling back to default."""
    raw = os.getenv(name, default)
    return tuple(item.strip() for item in raw.split(",") if item.strip())


def _env_bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


class Config:
    """Static, process-wide configuration."""

    # --- Domain -----------------------------------------------------
    TARGET_TICKERS: tuple[str, ...] = _split_env_list("TARGET_TICKERS", "BTC,ETH,XRP,SOL,ADA")
    DEFAULT_THEME: str = os.getenv("DEFAULT_THEME", "dark")

    # --- Data sources -------------------------------------------------
    DATA_DIR: Path = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
    QUOTES_PATH: Path = DATA_DIR / os.getenv("QUOTES_FILENAME", "cr_quotes_base_24.csv")
    REPORT_PATH: Path = DATA_DIR / os.getenv("REPORT_FILENAME", "cr_report_24.csv")
    CSV_SEPARATOR: str = os.getenv("CSV_SEPARATOR", ";")

    # --- Server (used by app.py / gunicorn) ----------------------------
    DEBUG: bool = _env_bool("DASH_DEBUG", False)
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8080"))

    # --- Observability --------------------------------------------------
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()

    # --- Derived ---------------------------------------------------------
    TICKER_COLORS: dict[str, str] = {
        t: px.colors.qualitative.Plotly[i % len(px.colors.qualitative.Plotly)]
        for i, t in enumerate(TARGET_TICKERS)
    }


def configure_logging() -> None:
    """Configure root logging exactly once for the whole process.

    Safe to call multiple times (e.g. under Dash's dev-server reloader,
    which re-imports modules in a child process).
    """
    root = logging.getLogger()
    if root.handlers:
        return
    logging.basicConfig(
        level=Config.LOG_LEVEL,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )
