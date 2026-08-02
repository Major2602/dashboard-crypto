from __future__ import annotations

import pytest

from dashboard.config import Config, ConfigError


class TestConfigValidate:
    def test_default_config_from_repo_is_valid(self):
        # Sanity check: whatever ships in the repo must pass its own validation.
        Config.validate()

    def test_rejects_empty_target_tickers(self, monkeypatch):
        monkeypatch.setattr(Config, "TARGET_TICKERS", ())
        with pytest.raises(ConfigError, match="TARGET_TICKERS"):
            Config.validate()

    def test_rejects_out_of_range_port(self, monkeypatch):
        monkeypatch.setattr(Config, "PORT", 70000)
        with pytest.raises(ConfigError, match="PORT"):
            Config.validate()

    def test_rejects_invalid_theme(self, monkeypatch):
        monkeypatch.setattr(Config, "DEFAULT_THEME", "solarized")
        with pytest.raises(ConfigError, match="DEFAULT_THEME"):
            Config.validate()

    def test_rejects_multi_character_csv_separator(self, monkeypatch):
        monkeypatch.setattr(Config, "CSV_SEPARATOR", ";;")
        with pytest.raises(ConfigError, match="CSV_SEPARATOR"):
            Config.validate()

    def test_rejects_default_secret_key_in_production(self, monkeypatch):
        monkeypatch.setattr(Config, "ENV", "production")
        monkeypatch.setattr(Config, "SECRET_KEY", "dev-only-insecure-key-change-me")
        monkeypatch.setattr(Config, "DEBUG", False)
        with pytest.raises(ConfigError, match="SECRET_KEY"):
            Config.validate()

    def test_rejects_debug_true_in_production(self, monkeypatch):
        monkeypatch.setattr(Config, "ENV", "production")
        monkeypatch.setattr(Config, "SECRET_KEY", "a-real-secret")
        monkeypatch.setattr(Config, "DEBUG", True)
        with pytest.raises(ConfigError, match="DASH_DEBUG"):
            Config.validate()

    def test_accepts_overridden_secret_key_in_production(self, monkeypatch):
        monkeypatch.setattr(Config, "ENV", "production")
        monkeypatch.setattr(Config, "SECRET_KEY", "a-real-secret")
        monkeypatch.setattr(Config, "DEBUG", False)
        Config.validate()
