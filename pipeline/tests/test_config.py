from __future__ import annotations

import datetime

import pytest

from pipeline.config import Config, ConfigError


class TestConfigValidate:
    def test_default_config_from_repo_is_valid(self):
        # Sanity check: whatever ships in the repo must pass its own validation.
        Config.validate()

    def test_rejects_empty_target_tickers(self, monkeypatch):
        monkeypatch.setattr(Config, "TARGET_TICKERS", ())
        with pytest.raises(ConfigError, match="PIPELINE_TARGET_TICKERS"):
            Config.validate()

    def test_rejects_start_date_not_before_end_date(self, monkeypatch):
        monkeypatch.setattr(Config, "START_DATE", datetime.date(2024, 6, 1))
        monkeypatch.setattr(Config, "END_DATE", datetime.date(2024, 6, 1))
        with pytest.raises(ConfigError, match="PIPELINE_START_DATE"):
            Config.validate()

    def test_rejects_non_positive_chunk_size(self, monkeypatch):
        monkeypatch.setattr(Config, "CHUNK_SIZE", 0)
        with pytest.raises(ConfigError, match="PIPELINE_CHUNK_SIZE"):
            Config.validate()

    def test_rejects_out_of_range_gpu_memory_utilization(self, monkeypatch):
        monkeypatch.setattr(Config, "GPU_MEMORY_UTILIZATION", 1.5)
        with pytest.raises(ConfigError, match="PIPELINE_GPU_MEMORY_UTILIZATION"):
            Config.validate()

    def test_rejects_multi_character_csv_separator(self, monkeypatch):
        monkeypatch.setattr(Config, "CSV_SEPARATOR", ";;")
        with pytest.raises(ConfigError, match="PIPELINE_CSV_SEPARATOR"):
            Config.validate()
