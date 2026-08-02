# dashboard-crypto

Crypto Sentiment & Market Dashboard — a Dash app correlating crypto asset
prices with LLM-summarized daily media/social mentions (price charts,
correlation heatmaps, a mentions-vs-price regression, and a radar
comparison across tickers).

## Architecture

```
dashboard/
├── app.py              # assembly: logging, config validation, layout, callbacks, health route
├── config.py            # env-driven Config + Config.validate()
├── callback_helpers.py  # pure (Dash-free) helpers used by callbacks.py — unit-testable in isolation
├── health.py             # /healthz route on the underlying Flask server
├── callbacks.py           # Dash callbacks (async, CPU-bound work dispatched via asyncio.to_thread)
├── data/
│   └── loader.py           # CSV loading, validation and preprocessing (DataManager, DataBundle)
├── ui/
│   ├── layout.py             # dash.Dash instance + app.layout
│   ├── components.py          # regression snippets, performance panels
│   └── theme.py                 # table_theme() — pure, Dash-free
└── viz/
    └── charts.py                # Visualizer — pure Plotly figure builders

run.py       # entry point: `python run.py` locally, `gunicorn run:server` in production
data/        # source CSVs (cr_quotes_base_24.csv, cr_report_24.csv)
tests/       # pytest suite
```

Design notes:
- **Pure vs. framework code is deliberately split.** `callback_helpers.py`,
  `ui/theme.py` and `viz/charts.py` only import the standard library /
  pandas / numpy / plotly — no Dash, no Mantine — so the business logic
  can be unit-tested without spinning up a browser or even a Dash app.
- **Data loads once at startup**, synchronously, because Dash needs the
  date range and ticker list to build `app.layout` before any request
  arrives. `DataManager.load()` is `async` so the same code path can be
  reused from a future periodic-refresh task without blocking the event
  loop; `dashboard/data/loader.py::bootstrap()` just runs it once via
  `asyncio.run()` at import time.
- **Callback inputs are re-validated server-side.** `DataBundle.valid_tickers()`
  filters the `ticker-select` value against columns we actually have data
  for — the `MultiSelect`'s `data=` list is a UI affordance, not a
  security boundary, since Dash callback inputs are just JSON POSTed to
  `/_dash-update-component`.

## Local development

Requires Python 3.11+.

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env                # adjust if needed
python run.py
```

The app serves on `http://localhost:8080` by default. Set `DASH_DEBUG=true`
in `.env` for the Dash dev server's hot reload.

### Configuration

All configuration is via environment variables (see `.env.example` for the
full list and defaults): `APP_ENV`, `TARGET_TICKERS`, `DEFAULT_THEME`,
`DATA_DIR` / `QUOTES_FILENAME` / `REPORT_FILENAME` / `CSV_SEPARATOR`,
`HOST` / `PORT` / `DASH_DEBUG`, `SECRET_KEY`, `LOG_LEVEL`.

`Config.validate()` runs at startup and raises `ConfigError` immediately
on an invalid combination (e.g. `APP_ENV=production` with the default
`SECRET_KEY`, or `DASH_DEBUG=true` in production) instead of letting the
app boot into a bad state.

## Tests & linting

```bash
pip install -r requirements-dev.txt
ruff check .                                  # lint
pytest --cov=dashboard --cov-report=term-missing   # tests + coverage
```

`tests/test_data_loader.py`, `test_callback_helpers.py`, `test_theme.py`
and `test_config.py` cover the pure logic (CSV parsing/validation,
forward-fill of missing mention counts, date-range resolution, topics
text cleaning, config validation) without needing a browser.
`tests/test_health.py` is a light integration test that boots the real
app and hits `/healthz` and `/` through Flask's test client.

CI (`.github/workflows/ci.yml`) runs `ruff` + `pytest` on Python 3.11 and
3.12 on every push/PR, then does a `docker build` sanity check.

## Docker

```bash
docker build -t dashboard-crypto .
docker run --rm -p 8080:8080 \
  -e SECRET_KEY="$(openssl rand -hex 32)" \
  -e APP_ENV=production \
  dashboard-crypto
```

The image runs as a non-root user, bakes in a `HEALTHCHECK` against
`/healthz`, and starts gunicorn with the same worker/thread settings as
`Procfile`.

## Deploying to Render

1. **New Web Service** → connect this repo.
2. **Build command:** `pip install -r requirements.txt`
3. **Start command:** leave blank to use `Procfile`, or set explicitly:
   `gunicorn run:server --workers=4 --threads=2 --timeout=120`
4. **Environment variables:** set at minimum
   - `APP_ENV=production`
   - `SECRET_KEY` — a long random value (`openssl rand -hex 32`); the app
     refuses to boot in production without this
   - `DASH_DEBUG=false` (also enforced by `Config.validate()`)
   - Any of the vars in `.env.example` you want to override (`TARGET_TICKERS`,
     `DEFAULT_THEME`, etc.) — `PORT`/`HOST` are provided by Render itself.
5. **Health check path:** `/healthz` (returns `200` with a small JSON body
   when the source data loaded successfully, `503` otherwise).

Alternatively, point Render at the `Dockerfile` directly (Render supports
Docker-based web services) — the `HEALTHCHECK` and non-root user are
already set up for that path.

## Updating the source data

Replace `data/cr_quotes_base_24.csv` and `data/cr_report_24.csv` (or point
`DATA_DIR` / `QUOTES_FILENAME` / `REPORT_FILENAME` at different files).
Requirements the loader enforces:
- `cr_report_24.csv` needs `date`, `tickers_count` (a stringified dict like
  `{'btc': 355, ...}`) and `top_5_topics` columns.
- `cr_quotes_base_24.csv` needs one column per `TARGET_TICKERS` entry,
  named `<TICKER>-<something>` (e.g. `BTC-USD`) — only the part before the
  first `-` is used.
- Both files use `CSV_SEPARATOR` (`;` by default) and are aligned by row
  position, so keep them in sync date-for-date.
