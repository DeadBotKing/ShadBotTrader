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

## Feature Platform (Sprint P2)

Compute the full standard FX feature set (109 features) over Data
Platform candles:

```bash
# list the standard feature set
PYTHONPATH=src python -m ShadBotTrader.feature_cli list

# full demo (ingest + compute)
python scripts/run_features.py

# compute directly (requires ingested candles)
PYTHONPATH=src python -m ShadBotTrader.feature_cli compute --symbol XAUUSD_i --timeframe 5M
```

The set mirrors the legacy feature catalog: wavelet-filtered prices,
SMA/EMA (5-35), ATR (Wilder + TR), Bollinger bands, Ichimoku, RSI,
MACD, Stochastic, per-column returns, target lags (past + future),
Fourier resonance sin/cos, candle balance (color/extension/power),
7 PCA components and 12 classic price/oscillator divergence features. Future-looking features (targets +1,
Fourier) are flagged research-only (non-causal) and never enter live
trading. Every feature is deterministic and causal where marked (warmup
respected), passes a
quality engine (NaN/Inf/range/alignment) and a leakage check
(availability-time <= decision-time). Results are stored immutably as
Parquet under `datasets/features/{feature_id}/v{version}.parquet`.

## AI Platform (Sprint P3)

Model registry, artifacts (with SHA-256 integrity), reproducible
training runs and prediction serving — with a WaveNet direction
classifier trained using genuine roll-forward (walk-forward) training:

```bash
# optional: install the ML framework
# Windows note: native TensorFlow ended at 2.10 — use
#   pip install tensorflow==2.10.1   (Python 3.9/3.10 only)
# or install inside WSL2. Linux/macOS: pip install tensorflow

# full demo (ingest -> features -> train Wavenet -> evaluate)
python scripts/run_ai.py

# CLI
PYTHONPATH=src python -m ShadBotTrader.ai_cli train   --model gold_direction
PYTHONPATH=src python -m ShadBotTrader.ai_cli predict --model gold_direction
```

The Wavenet uses causal convolutions (explicit left-padding, Keras 3
compatible) with gated activations and skip connections, so it is
roll-forward safe by construction. TensorFlow tests are skipped by
default; run them with `RUN_TF=1 python -m pytest`.
