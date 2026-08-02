"""Application configuration.

Every environment-dependent value (data location, host/port, log level,
debug flag) is read from an environment variable with a safe local
default, so the same code runs unchanged on a laptop, in CI, in Docker,
and on Render (where these are set as service environment variables).

``Config`` stays a plain class with class-level attributes (not a
dataclass instance) so existing call sites such as
``Config.TARGET_TICKERS`` or ``Config.TICKER_COLORS[t]`` keep working.
``Config.validate()`` is called once at startup (see ``dashboard.app``)
so misconfiguration fails fast with a clear message instead of surfacing
later as a confusing KeyError deep in a callback.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

import plotly.express as px

# dashboard/config.py -> repo root is two parents up
BASE_DIR = Path(__file__).resolve().parents[1]


class ConfigError(RuntimeError):
    """Raised by ``Config.validate()`` when the environment is unusable."""


def _split_env_list(name: str, default: str) -> tuple[str, ...]:
    """Parse a comma-separated env var into a tuple, falling back to default."""
    raw = os.getenv(name, default)
    return tuple(item.strip().upper() for item in raw.split(",") if item.strip())


def _env_bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


class Config:
    """Static, process-wide configuration."""

    # --- Environment --------------------------------------------------
    ENV: str = os.getenv("APP_ENV", "development")  # development | staging | production

    # --- Domain ---------------------------------------------------------
    TARGET_TICKERS: tuple[str, ...] = _split_env_list("TARGET_TICKERS", "BTC,ETH,XRP,SOL,ADA")
    DEFAULT_THEME: str = os.getenv("DEFAULT_THEME", "dark")

    # --- Data sources -----------------------------------------------------
    DATA_DIR: Path = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
    QUOTES_PATH: Path = DATA_DIR / os.getenv("QUOTES_FILENAME", "cr_quotes_base_24.csv")
    REPORT_PATH: Path = DATA_DIR / os.getenv("REPORT_FILENAME", "cr_report_24.csv")
    CSV_SEPARATOR: str = os.getenv("CSV_SEPARATOR", ";")

    # --- Server (used by dashboard.app / gunicorn) -------------------------
    DEBUG: bool = _env_bool("DASH_DEBUG", False)
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8080"))

    # --- Security ------------------------------------------------------------
    # Flask needs a secret key for signed cookies/sessions. Dash doesn't use
    # sessions by default, but a fixed dev fallback is set so the app never
    # silently runs with Flask's insecure auto-generated key; production
    # deployments must override this via the environment (validate() enforces
    # it when ENV=production).
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-only-insecure-key-change-me")

    # --- Observability ---------------------------------------------------------
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()

    # --- Derived -----------------------------------------------------------------
    TICKER_COLORS: dict[str, str] = {
        t: px.colors.qualitative.Plotly[i % len(px.colors.qualitative.Plotly)]
        for i, t in enumerate(TARGET_TICKERS)
    }

    @classmethod
    def validate(cls) -> None:
        """Fail fast on obviously broken configuration.

        Called once at startup. Intentionally does NOT check that the data
        files exist -- ``DataManager`` already raises a clear
        ``DataLoadError`` for that, and duplicating the check here would
        just produce two different error messages for the same problem.
        """
        errors: list[str] = []

        if not cls.TARGET_TICKERS:
            errors.append("TARGET_TICKERS must not be empty")

        if not (1 <= cls.PORT <= 65535):
            errors.append(f"PORT must be between 1 and 65535, got {cls.PORT}")

        if cls.DEFAULT_THEME not in {"dark", "light"}:
            errors.append(f"DEFAULT_THEME must be 'dark' or 'light', got {cls.DEFAULT_THEME!r}")

        if len(cls.CSV_SEPARATOR) != 1:
            errors.append(f"CSV_SEPARATOR must be a single character, got {cls.CSV_SEPARATOR!r}")

        if cls.ENV == "production" and cls.SECRET_KEY == "dev-only-insecure-key-change-me":
            errors.append("SECRET_KEY must be overridden via env var when APP_ENV=production")

        if cls.ENV == "production" and cls.DEBUG:
            errors.append("DASH_DEBUG must be false when APP_ENV=production")

        if errors:
            raise ConfigError("Invalid configuration:\n  - " + "\n  - ".join(errors))


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
