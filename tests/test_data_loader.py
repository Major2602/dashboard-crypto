from __future__ import annotations

import math

import pandas as pd
import pytest

from dashboard.data.loader import (
    DataBundle,
    DataLoadError,
    DataManager,
    _fill_missing_mentions,
    _mention_count,
    _safe_parse_dict,
)


class TestSafeParseDict:
    def test_parses_valid_dict_literal(self):
        assert _safe_parse_dict("{'btc': 1, 'eth': 2}") == {"btc": 1, "eth": 2}

    def test_returns_empty_dict_on_garbage(self):
        assert _safe_parse_dict("not a dict") == {}

    def test_returns_empty_dict_on_non_dict_literal(self):
        assert _safe_parse_dict("[1, 2, 3]") == {}

    def test_returns_empty_dict_on_none(self):
        assert _safe_parse_dict(None) == {}


class TestMentionCount:
    def test_returns_value_for_known_ticker(self):
        assert _mention_count({"btc": 355}, "BTC") == 355.0

    def test_returns_nan_for_missing_key(self):
        assert math.isnan(_mention_count({"btc": 355}, "ETH"))

    def test_returns_nan_for_explicit_none(self):
        assert math.isnan(_mention_count({"ada": None}, "ADA"))

    def test_returns_nan_for_non_numeric_value(self):
        assert math.isnan(_mention_count({"btc": "lots"}, "BTC"))


class TestFillMissingMentions:
    def test_forward_fills_interior_gap(self):
        df = pd.DataFrame(
            {"BTC": [10.0, float("nan"), float("nan"), 40.0]},
            index=pd.date_range("2024-01-01", periods=4),
        )
        filled = _fill_missing_mentions(df)
        assert filled["BTC"].tolist() == [10, 10, 10, 40]

    def test_leading_gap_defaults_to_zero_not_backfilled(self):
        df = pd.DataFrame(
            {"ETH": [float("nan"), 5.0, 6.0]},
            index=pd.date_range("2024-01-01", periods=3),
        )
        filled = _fill_missing_mentions(df)
        # Must NOT be back-filled to 5 (that would be look-ahead bias).
        assert filled["ETH"].tolist() == [0, 5, 6]

    def test_result_is_integer_dtype(self):
        df = pd.DataFrame({"BTC": [1.0, 2.0]}, index=pd.date_range("2024-01-01", periods=2))
        filled = _fill_missing_mentions(df)
        assert filled["BTC"].dtype.kind == "i"

    def test_no_gaps_is_a_noop(self):
        df = pd.DataFrame({"BTC": [1.0, 2.0, 3.0]}, index=pd.date_range("2024-01-01", periods=3))
        filled = _fill_missing_mentions(df)
        assert filled["BTC"].tolist() == [1, 2, 3]


class TestPreprocess:
    def test_raises_on_missing_report_columns(self, sample_quotes_df):
        bad_report = pd.DataFrame({"date": ["2024-01-01"]})
        with pytest.raises(DataLoadError, match="missing required columns"):
            DataManager._preprocess(bad_report, sample_quotes_df)

    def test_raises_on_empty_report(self, sample_quotes_df):
        empty_report = pd.DataFrame(columns=["date", "tickers_count", "top_5_topics"])
        with pytest.raises(DataLoadError, match="no rows"):
            DataManager._preprocess(empty_report, sample_quotes_df)

    def test_raises_on_unparseable_date(self, sample_report_df, sample_quotes_df):
        bad = sample_report_df.copy()
        bad.loc[0, "date"] = "not-a-date"
        with pytest.raises(DataLoadError, match="unparseable date"):
            DataManager._preprocess(bad, sample_quotes_df)

    def test_raises_when_configured_ticker_has_no_quotes_column(self, sample_report_df):
        # sample_quotes_df fixture covers ADA/BTC/ETH/SOL/XRP; drop one to
        # simulate a TARGET_TICKERS entry the quotes file doesn't have.
        incomplete_quotes = pd.DataFrame({"BTC-USD": [0.0, 1.0, 2.0]})
        with pytest.raises(DataLoadError, match="missing column"):
            DataManager._preprocess(sample_report_df, incomplete_quotes)

    def test_aligns_mismatched_lengths_by_position(self, sample_report_df, sample_quotes_df):
        shorter_quotes = sample_quotes_df.iloc[:2]
        df_report, df_quotes, df_mentions, df_diff, quotes_clean = DataManager._preprocess(
            sample_report_df, shorter_quotes
        )
        assert len(df_quotes) == 2
        assert len(quotes_clean) == 2

    def test_quotes_clean_columns_are_ticker_only(self, sample_report_df, sample_quotes_df):
        _, _, _, _, quotes_clean = DataManager._preprocess(sample_report_df, sample_quotes_df)
        assert set(quotes_clean.columns) == {"ADA", "BTC", "ETH", "SOL", "XRP"}

    def test_mentions_dataframe_has_forward_filled_gap(self, sample_report_df, sample_quotes_df):
        # sample_report_df's 2024-01-02 row has an explicit null 'ada' count.
        _, _, df_mentions, _, _ = DataManager._preprocess(sample_report_df, sample_quotes_df)
        assert df_mentions.loc["2024-01-02", "ADA"] == df_mentions.loc["2024-01-01", "ADA"]


class TestDataBundleValidTickers:
    def _bundle(self) -> DataBundle:
        quotes_clean = pd.DataFrame({"BTC": [1, 2], "ETH": [1, 2]})
        empty = pd.DataFrame()
        return DataBundle(report=empty, quotes=empty, mentions=empty, mentions_diff=empty, quotes_clean=quotes_clean)

    def test_filters_out_unknown_tickers(self):
        bundle = self._bundle()
        assert bundle.valid_tickers(["BTC", "DROP_TABLE", "ETH"]) == ["BTC", "ETH"]

    def test_none_returns_empty_list(self):
        assert self._bundle().valid_tickers(None) == []

    def test_empty_list_returns_empty_list(self):
        assert self._bundle().valid_tickers([]) == []

    def test_all_unknown_returns_empty_list(self):
        assert self._bundle().valid_tickers(["FOO", "BAR"]) == []
