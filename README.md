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

pipeline/    # OPTIONAL, standalone: regenerates the CSVs in data/ from
             # scratch (raw news + market data). Not used by the app at
             # runtime, not installed in Docker, not part of app CI.
             # See "Reproducing the source data" below and pipeline/README.md.
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
- **Every chart degrades to an explicit empty state, never a blank one.**
  `Visualizer.empty_state_figure()` renders a themed "No data available"
  placeholder whenever a chart has nothing to plot — no tickers selected,
  or the selected date range doesn't overlap any rows. The regression
  snippets and performance panels use the same pattern via
  `ui/components.py::_no_data_placeholder()`. This keeps an empty
  selection visually distinct from a broken callback.
- **Graphs and panels show a loading indicator while `update_dashboard`
  recomputes them** (`dcc.Loading` in `ui/layout.py`), so filter changes
  give immediate visual feedback instead of an unresponsive-looking UI
  during the ~second it takes to rebuild everything.

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
ruff check .                                       # lint
black --check --diff .                             # formatting (PEP 8, via Black)
mypy dashboard                                      # static type checking
pytest --cov=dashboard --cov-report=term-missing    # tests + coverage
```

Run `black .` (no `--check`) to auto-fix formatting locally before committing.

`tests/test_data_loader.py`, `test_callback_helpers.py`, `test_theme.py`
and `test_config.py` cover the pure logic (CSV parsing/validation,
forward-fill of missing mention counts, date-range resolution, topics
text cleaning, config validation) without needing a browser.
`tests/test_charts.py` and `tests/test_components.py` cover the
empty-state placeholders (no tickers selected, date range with no
overlapping data) as well as the populated/happy-path outputs.
`tests/test_health.py` is a light integration test that boots the real
app and hits `/healthz` and `/` through Flask's test client.

`pipeline/tests/` covers the standalone data-reproduction pipeline
separately (see [Reproducing the source data](#reproducing-the-source-data-optional))
and is not collected by the commands above — `pyproject.toml` scopes
`testpaths` to `tests/`, so the app's test/lint/CI story is unaffected by
the pipeline's presence. Run it explicitly with `pytest pipeline/tests`.

## Reproducing the source data (optional)

`data/cr_quotes_base_24.csv` and `data/cr_report_24.csv` aren't hand-written
— they're generated from a raw crypto-news dataset and market data via an
LLM summarization step. `pipeline/` contains that generation code, ported
into the repo for reproducibility.

It's intentionally kept separate from the app:
- its own dependency file, `requirements-pipeline.txt` (not installed by
  the Docker image or the app's `requirements.txt`);
- its own env-var namespace (`PIPELINE_*`, see `.env.pipeline.example`),
  distinct from the app's `Config`;
- it writes to `pipeline/output/` by default, never directly into
  `data/` — copying reviewed output over is a separate, explicit step.

Running it end-to-end needs a CUDA GPU (for the vLLM summarization step)
and takes hours for a full year of daily news. See `pipeline/README.md`
for the full walkthrough, or in short:

```bash
pip install -r requirements-pipeline.txt
cp .env.pipeline.example .env.pipeline   # adjust dates/tickers/model if needed
set -a; source .env.pipeline; set +a
python -m pipeline.run
# review pipeline/output/, then:
cp pipeline/output/cr_quotes_base.csv data/cr_quotes_base_24.csv
cp pipeline/output/cr_report.csv data/cr_report_24.csv
```

## CI/CD (GitHub Actions)

Three workflows live under `.github/workflows/`:

- **`ci.yml`** — on every push/PR to `main`: `ruff check`, `black --check`,
  `mypy`, then `pytest --cov` on Python 3.11 and 3.12, followed by a
  `docker build` sanity check. This is the required status check for PRs.
- **`autoformat.yml`** — on every push to `main` (and manually, via
  `workflow_dispatch`): runs `black .` and commits any formatting fixes
  straight back to `main` using the default `GITHUB_TOKEN`. Acts as a
  safety net so the default branch never drifts from PEP 8 / Black
  formatting even if a contributor forgot to run `black` locally; its own
  commit doesn't retrigger CI (GitHub doesn't fire workflows off commits
  made with the default token) so there's no loop.
- **`keep-alive.yml`** — a scheduled job (`cron: "*/10 * * * *"`, plus
  manual `workflow_dispatch`) that pings the deployed app's `/healthz`
  endpoint so Render's free-tier service doesn't spin down from
  inactivity. Requires a repository secret **`RENDER_APP_URL`** set to
  the service's base URL (e.g. `https://dashboard-crypto.onrender.com`) —
  add it under *Settings → Secrets and variables → Actions*. GitHub's
  `schedule` trigger is best-effort and can run a few minutes late under
  load; that's fine here, the goal is just "at least one request every
  ~15 minutes".

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
6. **(Optional, free tier) Prevent spin-down:** add a repository secret
   named `RENDER_APP_URL` set to your service's URL, so the
   `keep-alive.yml` GitHub Action can ping `/healthz` on a schedule and
   keep the service warm. See [CI/CD](#cicd-github-actions) above.

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
