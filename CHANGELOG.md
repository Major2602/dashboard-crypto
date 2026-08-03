# Changelog

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
