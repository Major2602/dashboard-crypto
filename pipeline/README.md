# pipeline/

Regenerates the two CSVs the dashboard reads (`dashboard/data/cr_report_24.csv`
and `dashboard/data/cr_quotes_base_24.csv`) from the raw news dataset and
market data, so the shipped example data is reproducible rather than an
unauditable, un-regeneratable blob.

**This is a standalone, optional tool.** It is not imported by
`dashboard/`, not installed in the Docker image, not part of the app's CI
job, and running it has no effect on the deployed service. It exists
purely so anyone can trace — and regenerate — where the dashboard's
example numbers came from.

## Architecture

```
pipeline/
├── config.py            # env-driven Config (PIPELINE_* vars) + Config.validate()
├── text_processing.py    # pure ticker-mention extraction — unit-testable without NLTK's corpus
├── news.py                 # loads the HF news dataset, aggregates per day, counts mentions
├── quotes.py                 # downloads market quotes via yfinance, rebases to % change
├── summarize.py                # vLLM two-phase (map-reduce) daily topic summarization
├── run.py                        # orchestration entry point: `python -m pipeline.run`
├── output/                        # default (gitignored) destination for generated CSVs
└── tests/                          # unit tests for the pure parts (config, text_processing)
```

Design notes, following the same conventions as `dashboard/` (see its
README's "Architecture" section):
- **Pure vs. framework code is split the same way.** `text_processing.py`
  only needs the standard library; `news.py` and `quotes.py` need pandas
  and their respective data sources but not vLLM/torch; `summarize.py` is
  the *only* module that imports vLLM, and does so lazily inside
  `run_llm_analysis` rather than at module import time — so the rest of
  the pipeline stays importable (and testable) on a machine with no GPU.
- **Config is env-driven**, same pattern as `dashboard/config.py`, but
  every variable uses a `PIPELINE_` prefix so it can never collide with
  the app's own environment.
- **Output is never written into `dashboard/data/` automatically.**
  `PIPELINE_OUTPUT_DIR` defaults to `pipeline/output/` (gitignored).
  Copying reviewed output into `dashboard/data/` is a separate, explicit
  step — see below.

## Requirements

Separate from the app's `requirements.txt` — see `requirements-pipeline.txt`
at the repo root. `vllm` needs a CUDA-capable GPU; `news.py` and
`quotes.py` alone run fine on CPU.

```bash
pip install -r requirements-pipeline.txt
```

## Running

```bash
cp .env.pipeline.example .env.pipeline   # adjust dates/tickers/model if needed
set -a; source .env.pipeline; set +a
python -m pipeline.run
```

This will, in order:
1. Load the configured Hugging Face news dataset and filter it to
   `PIPELINE_START_DATE`–`PIPELINE_END_DATE`.
2. Aggregate articles per day and count mentions of each
   `PIPELINE_TARGET_TICKERS` entry (`news.py`).
3. Download daily close prices for `<TICKER>-USD` via yfinance and rebase
   each series to a day-0 = 0% change (`quotes.py`).
4. Run the configured model through vLLM to summarize each day's news down
   to a 5-topic report (`summarize.py`) — this is the slow, GPU-bound step.
5. Write `cr_quotes_base.csv` and `cr_report.csv` to `PIPELINE_OUTPUT_DIR`.

A run over a full year of daily news through a local vLLM model takes
hours and needs a GPU with enough VRAM for `PIPELINE_MODEL_ID`; there's no
CPU fallback for the summarization step.

## Using the output in the dashboard

The pipeline **does not** touch `dashboard/data/`. Once you've reviewed
the generated CSVs:

```bash
cp pipeline/output/cr_quotes_base.csv dashboard/data/cr_quotes_base_24.csv
cp pipeline/output/cr_report.csv dashboard/data/cr_report_24.csv
```

(Or point the dashboard's own `.env` at the new filenames directly via
`QUOTES_FILENAME` / `REPORT_FILENAME` — see the main README's "Updating
the source data" section for the format both files must satisfy.)

## Tests

Only the dependency-free parts are unit-tested (`config.py`'s validation,
`text_processing.py`'s pure token-normalization logic) — not collected by
the app's default `pytest` run (`testpaths` in `pyproject.toml` is scoped
to `tests/`), so they don't affect the app's CI. Run them explicitly:

```bash
pip install -r requirements-pipeline.txt pytest
pytest pipeline/tests
```
