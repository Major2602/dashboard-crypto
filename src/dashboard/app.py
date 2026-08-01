"""WSGI entry point with Sentry and Health Check integration."""
from __future__ import annotations

import logging
from flask import jsonify
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration

from src.dashboard.config import settings, configure_logging

configure_logging()
logger = logging.getLogger(__name__)

if settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        integrations=[FlaskIntegration()],
        traces_sample_rate=1.0,
    )
    logger.info("Sentry initialized.")

from src.dashboard.layout import app  # noqa: E402
import src.dashboard.callbacks  # noqa: F401, E402

server = app.server

@server.route("/healthz")
def health_check() -> tuple[Any, int]:
    """Health check endpoint for Render/Kubernetes."""
    return jsonify({"status": "healthy", "service": "crypto-dashboard"}), 200

if __name__ == "__main__":
    app.run_server(debug=settings.debug, host=settings.host, port=settings.port)
