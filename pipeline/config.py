"""Pipeline configuration.

Mirrors the design of ``dashboard.config.Config``: every environment-
dependent value is read from an env var with a safe default, and
``Config.validate()`` is called once at the start of a run so a bad
combination (e.g. an inverted date range) fails immediately with a clear
message instead of partway through an hours-long GPU job.

All variables use a ``PIPELINE_`` prefix so they never collide with the
dashboard app's own environment variables (see ``dashboard/config.py``)
when both are configured in the same shell, ``.env`` file, or CI job.

This module has no dependency on ``dashboard`` (or vice versa) -- the
pipeline is a standalone, optional tool for regenerating the CSVs the app
reads, not a runtime dependency of the app itself.
"""

from __future__ import annotations

import datetime
import logging
import os
from pathlib import Path

# pipeline/config.py -> repo root is one parent up
BASE_DIR = Path(__file__).resolve().parents[1]


class ConfigError(RuntimeError):
    """Raised by ``Config.validate()`` when the environment is unusable."""


def _split_env_list(name: str, default: str) -> tuple[str, ...]:
    """Parse a comma-separated env var into a lowercase tuple, falling back to default."""
    raw = os.getenv(name, default)
    return tuple(item.strip().lower() for item in raw.split(",") if item.strip())


def _env_date(name: str, default: datetime.date) -> datetime.date:
    """Parse an ISO ``YYYY-MM-DD`` env var into a date, falling back to default."""
    raw = os.getenv(name)
    if not raw:
        return default
    try:
        return datetime.date.fromisoformat(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} must be an ISO date (YYYY-MM-DD), got {raw!r}") from exc


class Config:
    """Static, process-wide pipeline configuration."""

    # --- Source data --------------------------------------------------------
    HF_DATASET: str = os.getenv("PIPELINE_HF_DATASET", "maryamfakhari/crypto-news-coindesk-2020-2025")
    START_DATE: datetime.date = _env_date("PIPELINE_START_DATE", datetime.date(2024, 1, 1))
    END_DATE: datetime.date = _env_date("PIPELINE_END_DATE", datetime.date(2025, 1, 1))
    TARGET_TICKERS: tuple[str, ...] = _split_env_list("PIPELINE_TARGET_TICKERS", "btc,eth,xrp,sol,ada")

    # --- Summarization model (see pipeline/summarize.py) ---------------------
    MODEL_ID: str = os.getenv("PIPELINE_MODEL_ID", "cyankiwi/Qwen3.5-2B-AWQ-4bit")
    CHUNK_SIZE: int = int(os.getenv("PIPELINE_CHUNK_SIZE", "3000"))
    GPU_MEMORY_UTILIZATION: float = float(os.getenv("PIPELINE_GPU_MEMORY_UTILIZATION", "0.90"))
    MAX_MODEL_LEN: int = int(os.getenv("PIPELINE_MAX_MODEL_LEN", "262144"))

    # --- Output ---------------------------------------------------------------
    # Deliberately NOT dashboard/data by default -- a pipeline run shouldn't
    # silently overwrite the app's shipped source data. Copying the output
    # over is a separate, explicit step (see pipeline/README.md).
    OUTPUT_DIR: Path = Path(os.getenv("PIPELINE_OUTPUT_DIR", str(BASE_DIR / "pipeline" / "output")))
    QUOTES_FILENAME: str = os.getenv("PIPELINE_QUOTES_FILENAME", "cr_quotes_base.csv")
    REPORT_FILENAME: str = os.getenv("PIPELINE_REPORT_FILENAME", "cr_report.csv")
    CSV_SEPARATOR: str = os.getenv("PIPELINE_CSV_SEPARATOR", ";")

    # --- Observability -----------------------------------------------------------
    LOG_LEVEL: str = os.getenv("PIPELINE_LOG_LEVEL", "INFO").upper()

    @classmethod
    def validate(cls) -> None:
        """Fail fast on obviously broken configuration. Called once at the start of a run."""
        errors: list[str] = []

        if not cls.TARGET_TICKERS:
            errors.append("PIPELINE_TARGET_TICKERS must not be empty")

        if cls.START_DATE >= cls.END_DATE:
            errors.append(
                f"PIPELINE_START_DATE ({cls.START_DATE}) must be before PIPELINE_END_DATE ({cls.END_DATE})"
            )

        if cls.CHUNK_SIZE <= 0:
            errors.append(f"PIPELINE_CHUNK_SIZE must be positive, got {cls.CHUNK_SIZE}")

        if not (0.0 < cls.GPU_MEMORY_UTILIZATION <= 1.0):
            errors.append(
                f"PIPELINE_GPU_MEMORY_UTILIZATION must be in (0, 1], got {cls.GPU_MEMORY_UTILIZATION}"
            )

        if cls.MAX_MODEL_LEN <= 0:
            errors.append(f"PIPELINE_MAX_MODEL_LEN must be positive, got {cls.MAX_MODEL_LEN}")

        if len(cls.CSV_SEPARATOR) != 1:
            errors.append(f"PIPELINE_CSV_SEPARATOR must be a single character, got {cls.CSV_SEPARATOR!r}")

        if errors:
            raise ConfigError("Invalid pipeline configuration:\n  - " + "\n  - ".join(errors))


def configure_logging() -> None:
    """Configure root logging exactly once for the whole process. Safe to call multiple times."""
    root = logging.getLogger()
    if root.handlers:
        return
    logging.basicConfig(
        level=Config.LOG_LEVEL,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )
