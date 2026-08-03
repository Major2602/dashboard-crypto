from __future__ import annotations

from pipeline.text_processing import ALIAS_MAP, normalize_tokens


class TestNormalizeTokens:
    def test_keeps_tokens_already_matching_a_target_ticker(self):
        assert normalize_tokens(["btc", "eth", "dog"], ["btc", "eth", "xrp", "sol", "ada"]) == ["btc", "eth"]

    def test_maps_full_names_via_alias_map(self):
        tokens = list(ALIAS_MAP.keys())
        expected = list(ALIAS_MAP.values())
        assert normalize_tokens(tokens, expected) == expected

    def test_drops_tokens_outside_target_tickers(self):
        assert normalize_tokens(["moon", "hodl", "btc"], ["btc"]) == ["btc"]

    def test_empty_input_returns_empty_list(self):
        assert normalize_tokens([], ["btc", "eth"]) == []

    def test_preserves_order_and_duplicates(self):
        assert normalize_tokens(["eth", "btc", "eth"], ["btc", "eth"]) == ["eth", "btc", "eth"]
