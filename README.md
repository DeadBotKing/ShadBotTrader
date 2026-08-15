# ShadBotTrader

Enterprise AI Trading Platform — a clean-architecture, domain-driven,
event-driven and plugin-based trading platform written in Python.

## Status

Phase 28 (Implementation Foundation). The architecture (Phases 1-27)
is frozen and documented under `docs/`.

## Repository layout

```
src/ShadBotTrader/          # the platform package
  core/                     # DI container, event bus, lifecycle, plugins, services
  domain/                   # framework-independent business concepts
  application/              # composition root, runtime, startup/shutdown
  infrastructure/           # configuration + logging (and future adapters)
tests/                      # unit and architecture tests
configs/                    # runtime configuration (YAML)
datasets/{raw,processed,features}/
docs/                       # canonical architecture documentation
architecture/               # the frozen architecture baseline
legacy/                     # the pre-platform code, kept as domain reference
project_state/              # generated project state (PIP)
```

## Quality gate

Every change must pass, from the repository root:

```bash
python -m black --check .
python -m ruff check .
python -m mypy src
python -m pytest
```

## Running

```bash
pip install -e .
python -m ShadBotTrader.main
```

The foundation runtime performs a clean start -> shutdown cycle and
prints structured logs (`Starting`, `Shutdown complete`).

## Project Intelligence (PIP)

The platform can scan itself and generate canonical project-state
artifacts under `project_state/generated/`:

```bash
# Linux / macOS
PYTHONPATH=src python -m ShadBotTrader.intelligence

# any OS, without installing the package
python scripts/run_pip.py
```

Generated files: `ProjectSnapshot.md`, `ProjectSnapshot.json`,
`ChatGPT_Context.md`, `Architecture.md`, `Statistics.json`. Previous
state is archived under `project_state/archive/`.

## Data Platform (Sprint P1)

Ingest market data through the L0 → L1 → L2 → L3 pipeline:

```bash
# generate a sample candle CSV (demos/tests)
python scripts/run_data.py

# or use the CLI directly
PYTHONPATH=src python -m ShadBotTrader.data_cli sample --symbol XAUUSD_i --timeframe 5M --rows 200
PYTHONPATH=src python -m ShadBotTrader.data_cli ingest  --csv datasets/samples/XAUUSD_i_5M.csv --symbol XAUUSD_i --timeframe 5M
PYTHONPATH=src python -m ShadBotTrader.data_cli catalog
```

The pipeline validates rows (schema/type/range/duplicates), normalises
symbols and timestamps to UTC, runs the quality engine (gaps,
duplicates, outliers) and stores raw + normalized data immutably as
Parquet under `datasets/{raw,processed}/{SYMBOL}/{TIMEFRAME}/v{version}.parquet`.
