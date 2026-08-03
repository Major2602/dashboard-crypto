from __future__ import annotations

import pandas as pd
import pytest

from dashboard.data.loader import DataBundle
from dashboard.ui.components import build_performance_grid, build_regression_snippets


@pytest.fixture
def bundle() -> DataBundle:
    dates = pd.date_range("2024-01-01", periods=10, freq="D")
    quotes_clean = pd.DataFrame({"BTC": range(10), "ETH": [x / 10 for x in range(10)]}, index=dates)
    mentions = pd.DataFrame({"BTC": range(10), "ETH": range(10)}, index=dates)
    empty = pd.DataFrame()
    return DataBundle(report=empty, quotes=empty, mentions=mentions, mentions_diff=empty, quotes_clean=quotes_clean)


@pytest.fixture(autouse=True)
def _patch_data(monkeypatch: pytest.MonkeyPatch, bundle: DataBundle) -> None:
    monkeypatch.setattr("dashboard.ui.components.DATA", bundle)
    monkeypatch.setattr("dashboard.viz.charts.DATA", bundle)


class TestRegressionSnippetsPlaceholder:
    def test_no_tickers_returns_single_placeholder(self, bundle: DataBundle):
        result = build_regression_snippets([], bundle.quotes_clean.index[0], bundle.quotes_clean.index[-1], "dark")
        assert len(result) == 1

    def test_ticker_with_enough_points_produces_a_snippet(self, bundle: DataBundle):
        result = build_regression_snippets(["BTC"], bundle.quotes_clean.index[0], bundle.quotes_clean.index[-1], "dark")
        assert len(result) == 1


class TestPerformanceGridPlaceholder:
    def test_no_tickers_returns_single_placeholder(self, bundle: DataBundle):
        result = build_performance_grid([], bundle.quotes_clean.index[0], bundle.quotes_clean.index[-1], "dark")
        assert len(result) == 1

    def test_selected_tickers_return_one_panel_each(self, bundle: DataBundle):
        result = build_performance_grid(["BTC", "ETH"], bundle.quotes_clean.index[0], bundle.quotes_clean.index[-1], "dark")
        assert len(result) == 2
