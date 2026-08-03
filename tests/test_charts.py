from __future__ import annotations

import pandas as pd
import pytest

from dashboard.data.loader import DataBundle
from dashboard.viz.charts import Visualizer


def _is_placeholder(fig) -> bool:
    """A figure produced by ``Visualizer.empty_state_figure`` has exactly
    one centered annotation and no traces."""
    return len(fig.data) == 0 and len(fig.layout.annotations) == 1


@pytest.fixture
def bundle() -> DataBundle:
    dates = pd.date_range("2024-01-01", periods=5, freq="D")
    quotes_clean = pd.DataFrame({"BTC": [10.0, 11.0, 9.0, 12.0, 13.0], "ETH": [1.0, 1.1, 0.9, 1.2, 1.3]}, index=dates)
    mentions = pd.DataFrame({"BTC": [5, 6, 4, 7, 8], "ETH": [1, 2, 1, 3, 2]}, index=dates)
    mentions_diff = mentions.diff().fillna(0)
    empty = pd.DataFrame()
    return DataBundle(report=empty, quotes=empty, mentions=mentions, mentions_diff=mentions_diff, quotes_clean=quotes_clean)


@pytest.fixture(autouse=True)
def _patch_data(monkeypatch: pytest.MonkeyPatch, bundle: DataBundle) -> None:
    monkeypatch.setattr("dashboard.viz.charts.DATA", bundle)


class TestMainPriceChartPlaceholder:
    def test_no_tickers_selected_returns_placeholder(self, bundle: DataBundle):
        fig = Visualizer.create_main_price_chart(bundle.quotes_clean.index[0], bundle.quotes_clean.index[-1], [], "dark")
        assert _is_placeholder(fig)

    def test_date_range_outside_data_returns_placeholder(self, bundle: DataBundle):
        out_of_range = pd.Timestamp("2030-01-01")
        fig = Visualizer.create_main_price_chart(out_of_range, out_of_range + pd.Timedelta(days=1), ["BTC"], "dark")
        assert _is_placeholder(fig)

    def test_valid_selection_returns_populated_figure(self, bundle: DataBundle):
        fig = Visualizer.create_main_price_chart(bundle.quotes_clean.index[0], bundle.quotes_clean.index[-1], ["BTC"], "dark")
        assert len(fig.data) > 0


class TestCorrelationHeatmapPlaceholder:
    def test_empty_frame_returns_placeholder(self):
        fig = Visualizer.create_correlation_heatmap(pd.DataFrame(), "dark")
        assert _is_placeholder(fig)

    def test_populated_frame_returns_heatmap(self, bundle: DataBundle):
        fig = Visualizer.create_correlation_heatmap(bundle.quotes_clean, "light")
        assert len(fig.data) == 1


class TestRadarChartPlaceholder:
    def test_no_tickers_returns_placeholder(self, bundle: DataBundle):
        fig = Visualizer.create_radar_chart([], bundle.quotes_clean.index[0], bundle.quotes_clean.index[-1], "dark")
        assert _is_placeholder(fig)

    def test_out_of_range_dates_return_placeholder(self, bundle: DataBundle):
        out_of_range = pd.Timestamp("2030-01-01")
        fig = Visualizer.create_radar_chart(["BTC"], out_of_range, out_of_range + pd.Timedelta(days=1), "dark")
        assert _is_placeholder(fig)

    def test_valid_selection_returns_populated_figure(self, bundle: DataBundle):
        fig = Visualizer.create_radar_chart(["BTC", "ETH"], bundle.quotes_clean.index[0], bundle.quotes_clean.index[-1], "dark")
        assert len(fig.data) == 2
