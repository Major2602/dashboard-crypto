"""Liveness/readiness endpoint.

Registered directly on the underlying Flask server (``app.server``), not
as a Dash callback, so it responds even if the Dash render tree or a
client-side asset ever breaks -- and so uptime monitors / Render's health
check don't pay the cost of rendering the full page.
"""

from __future__ import annotations

import flask

from dashboard.data import DATA


def register_health_check(server: flask.Flask) -> None:
    @server.route("/healthz")
    def healthz() -> tuple[flask.Response, int]:
        try:
            ok = not DATA.report.empty and not DATA.quotes_clean.empty
        except Exception:  # pragma: no cover - defensive
            ok = False
        status = 200 if ok else 503
        return flask.jsonify(
            status="ok" if ok else "unhealthy",
            report_rows=int(len(DATA.report)) if ok else 0,
        ), status
