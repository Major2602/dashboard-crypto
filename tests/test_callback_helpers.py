from __future__ import annotations

from datetime import date

import pandas as pd

from dashboard.callback_helpers import clean_topics_table, resolve_date_range


class TestResolveDateRange:
    def test_no_trigger_returns_existing_range(self):
        existing = [date(2024, 1, 1), date(2024, 6, 1)]
        assert resolve_date_range(None, existing, date(2024, 12, 31), date(2024, 1, 1)) == existing

    def test_unrelated_trigger_returns_existing_range(self):
        existing = [date(2024, 1, 1), date(2024, 6, 1)]
        assert resolve_date_range("ticker-select", existing, date(2024, 12, 31), date(2024, 1, 1)) == existing

    def test_btn_all_returns_full_span(self):
        min_d, max_d = date(2024, 1, 1), date(2024, 12, 31)
        assert resolve_date_range("btn-all", [date(2024, 3, 1), date(2024, 4, 1)], max_d, min_d) == [min_d, max_d]

    def test_btn_1m_returns_30_days_back_from_max(self):
        max_d, min_d = date(2024, 12, 31), date(2024, 1, 1)
        start, end = resolve_date_range("btn-1m", [], max_d, min_d)
        assert end == max_d
        assert (max_d - start).days == 30

    def test_btn_12m_returns_360_days_back_from_max(self):
        max_d, min_d = date(2024, 12, 31), date(2023, 1, 1)
        start, end = resolve_date_range("btn-12m", [], max_d, min_d)
        assert end == max_d
        assert (max_d - start).days == 360


class TestCleanTopicsTable:
    def test_filters_by_date_range(self, sample_report_df: pd.DataFrame):
        records = clean_topics_table(sample_report_df, pd.Timestamp("2024-01-02"), pd.Timestamp("2024-01-03"))
        assert {r["date"] for r in records} == {"2024-01-02", "2024-01-03"}

    def test_sorted_descending_by_date(self, sample_report_df: pd.DataFrame):
        records = clean_topics_table(sample_report_df, pd.Timestamp("2024-01-01"), pd.Timestamp("2024-01-03"))
        dates = [r["date"] for r in records]
        assert dates == sorted(dates, reverse=True)

    def test_strips_disallowed_characters_but_keeps_punctuation(self, sample_report_df: pd.DataFrame):
        records = clean_topics_table(sample_report_df, pd.Timestamp("2024-01-01"), pd.Timestamp("2024-01-01"))
        text = records[0]["clean_topics"]
        assert "<" not in text and ">" not in text and "&" not in text
        # Markdown-ish emphasis characters, digits, punctuation and newlines survive.
        assert "*bold*" in text
        assert "\n" in text

    def test_empty_range_returns_no_rows(self, sample_report_df: pd.DataFrame):
        records = clean_topics_table(sample_report_df, pd.Timestamp("2025-01-01"), pd.Timestamp("2025-01-31"))
        assert records == []
