# Crypto Sentiment & Market Dashboard

A production-ready asynchronous Dash application deployed on Render. It visually cross-references cryptocurrency market dynamics (prices, correlations) with LLM-parsed topics and reference metrics from the community.

## Features

- **Asynchronous Data Loading**: Efficient unblocking data layer offloaded to worker threads.
- **Production Infrastructure**: Built with Docker, Gunicorn, and strictly validated via Pydantic.
- **Continuous Integration (CI/CD)**: Code formatting with Ruff, type checking with Mypy, and testing via Pytest all bundled in GitHub Actions.
- **Observability**: Error tracking supported via Sentry and a native `/healthz` endpoint.
- **Keep-Alive**: GitHub Actions automated cron job prevents Render free-tier cold starts.

## Architecture

```text
src/
 ├─ dashboard/
 │   ├─ app.py          # WSGI application entry and endpoints
 │   ├─ config.py       # Pydantic BaseSettings environment parsing
 │   ├─ layout.py       # UI definitions and DOM structure
 │   ├─ callbacks.py    # Async responsive triggers
 │   ├─ data_layer.py   # Pandas-based loading with Dependency Injection
 │   └─ vis_helpers.py  # Synchronous Plotly chart factories
