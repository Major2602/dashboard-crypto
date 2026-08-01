# APP ENTRY POINT
"""WSGI entry point.

Local dev:      python app.py
Production:     gunicorn app:server   (see Procfile; used by Render)

Host/port/debug all come from environment variables via ``config.Config``,
so this file needs no changes between environments.
"""

from __future__ import annotations

from config import Config, configure_logging

configure_logging()

from layout import app  # noqa: E402  (logging must be configured before other imports log)
import callbacks  # noqa: F401,E402  (import registers the callbacks as a side effect)

server = app.server

if __name__ == "__main__":
    app.run_server(debug=Config.DEBUG, host=Config.HOST, port=Config.PORT)
