"""Application assembly.

Single place that, in order: configures logging, validates configuration,
builds the Dash layout, registers callbacks (import side effect) and the
health-check route, and exposes the WSGI ``server`` gunicorn runs.

Kept separate from the repo-root ``run.py`` entry point so the package is
importable (e.g. from tests) without needing ``run.py`` on the path.
"""

from __future__ import annotations

from dashboard.config import Config, configure_logging

configure_logging()
Config.validate()

from dashboard.ui.layout import app  # noqa: E402  (logging/config must run first)
from dashboard.health import register_health_check  # noqa: E402

import dashboard.callbacks  # noqa: F401,E402  (import registers the callbacks as a side effect)

server = app.server
register_health_check(server)


def main() -> None:
    app.run(debug=Config.DEBUG, host=Config.HOST, port=Config.PORT)


if __name__ == "__main__":
    main()
