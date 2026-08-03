"""Pure, Dash-free helper functions used by ``dashboard.callbacks``.

Split out so these can be unit-tested without importing Dash / Mantine /
scikit-learn -- everything here only touches the standard library and
pandas.
"""

from __future__ import annotations

import re
from datetime import date, timedelta

import pandas as pd

_TOPICS_ALLOWED_CHARS = re.compile(r"[^\w\s\d.,!?\-\n*]")

PERIOD_BUTTON_DAYS: dict[str, int] = {
    "btn-1m": 30,
    "btn-3m": 90,
    "btn-6m": 180,
    "btn-9m": 270,
    "btn-12m": 360,
}


def resolve_date_range(
    trigger: str | None, date_range: list[date], max_d: date, min_d: date
) -> list[date]:
    """Translate a quick-range button click (if any) into an explicit [start, end]."""
    if trigger == "btn-all":
        return [min_d, max_d]
    days = PERIOD_BUTTON_DAYS.get(trigger)
    if days is not None:
        return [max_d - timedelta(days=days), max_d]
    return date_range


def clean_topics_table(df_report: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> list[dict[str, str]]:
    """Build the row records consumed by the topics DataTable."""
    mask = (df_report["date"] >= start) & (df_report["date"] <= end)
    table_df = df_report.loc[mask].sort_values("date", ascending=False).copy()
    table_df["date_str"] = table_df["date"].dt.strftime("%Y-%m-%d")
    table_df["clean_topics"] = table_df["top_5_topics"].astype(str).str.replace(
        _TOPICS_ALLOWED_CHARS, "", regex=True
    )
    return (
        table_df[["date_str", "clean_topics"]]
        .rename(columns={"date_str": "date"})
        .to_dict("records")
    )
