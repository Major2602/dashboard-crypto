from __future__ import annotations

from dashboard.ui.theme import table_theme


class TestTableTheme:
    def test_returns_expected_keys(self):
        theme = table_theme("dark")
        assert set(theme.keys()) == {"cell", "header", "data", "title"}

    def test_dark_mode_uses_dark_palette(self):
        theme = table_theme("dark")
        assert theme["cell"]["backgroundColor"] == "#1A1B1E"
        assert theme["title"]["color"] == "white"

    def test_light_mode_uses_light_palette(self):
        theme = table_theme("light")
        assert theme["cell"]["backgroundColor"] == "#FFFFFF"
        assert theme["title"]["color"] == "black"

    def test_unknown_mode_falls_back_to_light(self):
        theme = table_theme("solarized")
        assert theme["cell"]["backgroundColor"] == "#FFFFFF"
