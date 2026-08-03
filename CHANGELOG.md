# Changelog

## 1.2.0 — Reproducible source-data pipeline

**Added**
- `pipeline/`: a standalone, optional package that regenerates
  `data/cr_quotes_base_24.csv` and `data/cr_report_24.csv` from the raw
  news dataset and market data — ported and refactored from an ad hoc
  notebook script into the project's module/config/test conventions
  (`pipeline/config.py`'s env-driven `Config` + `validate()`,
  `pipeline/text_processing.py`'s pure/framework split, `pipeline/tests/`).
  Not imported by `dashboard/`, not installed in the Docker image, and not
  part of the app's `ci.yml` job — see `pipeline/README.md`.
- `requirements-pipeline.txt` and `.env.pipeline.example` for the
  pipeline's own (GPU-only, `PIPELINE_`-prefixed) dependencies and config,
  kept separate from the app's `requirements.txt` / `.env.example`.
- Documented the pipeline in the main `README.md`
  ("Reproducing the source data").

**Fixed relative to the original script**
- Removed the notebook-only `display()` call and module-level side
  effects; wrapped execution behind `python -m pipeline.run` /
  `if __name__ == "__main__"`.
- `nltk.download()` no longer runs as an import-time side effect — deferred
  into a lazily-initialized lemmatizer so pure logic stays importable
  without network access.
- vLLM/torch imports moved out of the module top level and into
  `summarize.run_llm_analysis`, so the rest of the pipeline (and its unit
  tests) don't require a GPU or those packages to be installed.
- Quotes CSV is now written without an index column, matching what
  `dashboard.data.loader` actually expects (it aligns quotes to the report
  file by row position, not by a date column in the quotes file).
- Added `NewsLoadError` / `QuotesLoadError` / `SummarizationError` /
  `ConfigError` with explicit validation (missing dataset columns, empty
  date-range results, missing quote symbols, inverted date range, etc.)
  instead of letting failures surface as bare exceptions deep in pandas or
  yfinance internals.

## 1.1.0 — Production-readiness pass

**Empty states**
- Added `Visualizer.empty_state_figure()`; the main price chart,
  correlation heatmaps, and radar chart now render a themed "no data"
  placeholder (instead of a blank/broken-looking figure) when no tickers
  are selected or the date range has no overlapping rows.
- Fixed the correlation heatmap's empty-data fallback, which previously
  returned an unstyled `go.Figure()` regardless of the dark/light theme.
- Added matching placeholders for the regression snippets and
  performance panels (`ui/components.py::_no_data_placeholder`).
- Wrapped the main graphs, radar chart, correlation heatmaps, topics
  table, regression panel, and performance panel in `dcc.Loading` so
  filter changes give immediate feedback while `update_dashboard`
  recomputes.

**Typing**
- Tightened bare `dict` / `list` generics to fully parametrized types
  (`dict[str, Any]`, `list[date]`, `list[dict[str, str]]`,
  `dict[str, float] | None`) across `data/loader.py`,
  `callback_helpers.py`, `callbacks.py`, and `ui/theme.py`.
- Added a `[tool.mypy]` configuration (`disallow_untyped_defs`,
  `check_untyped_defs`, etc.) and a `mypy` CI step.

**Formatting**
- Added `black` as a dev dependency with a `[tool.black]` config matching
  the existing `ruff` line length (110).
- CI now runs `black --check --diff .` alongside `ruff check`.
- Added `autoformat.yml`: auto-applies `black` on every push to `main`
  and commits the result, so formatting drift self-heals.

**Deployment**
- Added `keep-alive.yml`: a scheduled GitHub Action that pings
  `/healthz` every ~10 minutes to prevent Render's free tier from
  spinning the service down after inactivity.

**Docs**
- Documented the empty-state/loading design, the three GitHub Actions
  workflows, and the `black`/`mypy` commands in `README.md`.

**Tests**
- Added `tests/test_charts.py` and `tests/test_components.py` covering
  the new placeholder behavior and the existing populated-data paths.

## 1.0.0

Initial refactored release: async data loading, Dash callback structure,
Docker/Render deployment, ruff + pytest CI.
