"""Color/style dicts for the dashboard, independent of any Dash import.

Split out of ``dashboard.ui.components`` so it can be unit-tested without
pulling in Dash Mantine Components.
"""

from __future__ import annotations


def table_theme(mode: str) -> dict[str, dict]:
    """Style dicts for the topics DataTable + section title, per color scheme.

    Returns a dict with keys ``cell``, ``header``, ``data``, ``title`` so
    callers can spread the relevant piece straight into the matching Dash
    Output.
    """
    is_dark = mode == "dark"
    palette = {
        "bg": "#1A1B1E" if is_dark else "#FFFFFF",
        "text": "#C1C2C5" if is_dark else "#000000",
        "border": "#373A40" if is_dark else "#dee2e6",
        "header": "#25262B" if is_dark else "#f8f9fa",
    }
    border = f'1px solid {palette["border"]}'
    return {
        "cell": {
            "backgroundColor": palette["bg"], "color": palette["text"], "textAlign": "left",
            "border": border, "padding": "10px", "whiteSpace": "normal", "font-family": "sans-serif",
        },
        "header": {
            "backgroundColor": palette["header"], "color": palette["text"], "fontWeight": "bold",
            "border": border, "font-family": "sans-serif",
        },
        "data": {"border": border},
        "title": {"fontWeight": 800, "color": "white" if is_dark else "black"},
    }
