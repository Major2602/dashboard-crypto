"""WSGI entry point.

Local dev:      python run.py
Production:     gunicorn run:server   (see Procfile; used by Render)

Host/port/debug all come from environment variables via
``dashboard.config.Config``, so this file needs no changes between
environments.
"""

from dashboard.app import main, server

__all__ = ["server"]

if __name__ == "__main__":
    main()
