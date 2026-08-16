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

## Installation

Requires **Python 3.10 – 3.13** (64-bit).

```bash
# 1. create and activate a virtual environment
python -m venv .venv                 # Windows: py -3.12 -m venv .venv
source .venv/bin/activate            # Windows: .\.venv\Scripts\Activate.ps1

# 2. install
pip install --upgrade pip setuptools wheel
pip install -r requirements-dev.txt  # core + lint/type/test tooling
pip install -r requirements-ai.txt   # optional: TensorFlow for the WaveNet
pip install -e .                     # the package itself (editable)
```

| File | Contents |
|---|---|
| `requirements.txt` | core runtime only (Data + Feature platforms) |
| `requirements-dev.txt` | core + ruff, black, mypy, pytest |
| `requirements-ai.txt` | core + TensorFlow (WaveNet trainer/predictor) |
| `requirements-lock.txt` | exact pinned versions of the verified environment |

> **Windows:** TensorFlow installs normally on Python 3.10–3.13, but native
> Windows has been **CPU-only since TF 2.11**. Use WSL2 if you need GPU.
> See [`WINDOWS_SETUP.md`](WINDOWS_SETUP.md) for a full walkthrough.

## Quality gate

Every change must pass, from the repository root:

```bash
python -m black --check .
python -m ruff check .
python -m mypy src
python -m pytest
```

TensorFlow-dependent tests are skipped unless `RUN_TF=1` is set:

```bash
RUN_TF=1 python -m pytest          # Windows: $env:RUN_TF=1; python -m pytest
```

## Running

```bash
pip install -e .
python -m ShadBotTrader.main
```

Installing the package also exposes these console commands:

| Command | Equivalent module |
|---|---|
| `shadbot` | `python -m ShadBotTrader.main` |
| `shadbot-data` | `python -m ShadBotTrader.data_cli` |
| `shadbot-feature` | `python -m ShadBotTrader.feature_cli` |
| `shadbot-ai` | `python -m ShadBotTrader.ai_cli` |
| `shadbot-trading` | `python -m ShadBotTrader.trading_cli` |
| `shadbot-exec` | `python -m ShadBotTrader.execution_cli` |
| `shadbot-pip` | `python -m ShadBotTrader.intelligence` |

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

## Execution & Portfolio (Sprint P5)

Turns risk-approved intents into real fills and keeps the books:

```bash
python scripts/run_execution.py                    # full chain demo

shadbot-exec quote --mid 2000 --spread 2
shadbot-exec pnl --entry 2000 --exit 2100 --quantity 2 --fee 4
shadbot-exec execute --side buy --quantity 5 --liquidity 2
```

```
TradingIntent (risk-approved)
      |
IntentResolver    -> ResolvedOrder     policies become numbers
      |
ExecutionVenue    -> ExecutionResult   real fills, possibly partial
      |
PortfolioLedger   -> PositionState     fill-based PnL accounting
```

The simulated venue models spread (buys lift the ask, sells hit the bid),
slippage, commission and partial fills — deterministically, so backtests
are reproducible.

Accounting follows Phase 15: average entry price comes from **real fills**
(never from an intent), realized PnL is booked when a position shrinks,
unrealized PnL is marked to market, and fees are tracked separately from
gross PnL. Every amount is `Decimal`; floats are never used for money.

Protections enforced by tests: an **expired** intent is never executed, the
**same intent never fills twice**, and the ledger only ever reflects
quantities that actually traded.

## Trading Platform (Sprint P4)

Turns predictions into risk-approved trading intents:

```bash
# full demo of the decision pipeline
python scripts/run_trading.py

# CLI
PYTHONPATH=src python -m ShadBotTrader.trading_cli policy
PYTHONPATH=src python -m ShadBotTrader.trading_cli evaluate --value 0.9 --confidence 0.85
```

The pipeline is:

```
StrategyContext -> Strategy -> TradingSignal
                                   |
                              SignalValidator      (schema, freshness)
                                   |
                              DecisionEngine  -> TradingDecision
                                   |
                                RISK GATE          (mandatory)
                                   |
                              IntentFactory   -> TradingIntent
                                   |
                          Execution Platform (Sprint P5)
```

Three invariants are enforced by tests, not convention:

* a strategy emits **signals, never orders**
* a `TradingDecision` **is not an `Order`**
* **no `TradingIntent` exists without an approving risk verdict**

A `TradingIntent` carries *policies* (`quantity_policy`, `price_policy`),
not resolved broker values — the Execution Platform resolves them. Every
decision, including each rejection and its machine-readable reason, is
recorded in a `DecisionJournal` for audit.

## AI Platform (Sprint P3)

Model registry, artifacts (with SHA-256 integrity), reproducible
training runs and prediction serving — with a WaveNet direction
classifier trained using genuine roll-forward (walk-forward) training:

```bash
# optional: install the ML framework
# optional: install the ML framework (Python 3.10-3.13)
#   pip install -r requirements-ai.txt
# Windows note: TensorFlow installs fine, but native Windows is CPU-only
# since TF 2.11 — use WSL2 if you need GPU acceleration.

# full demo (ingest -> features -> train Wavenet -> evaluate)
python scripts/run_ai.py

# CLI
PYTHONPATH=src python -m ShadBotTrader.ai_cli train   --model gold_direction
PYTHONPATH=src python -m ShadBotTrader.ai_cli predict --model gold_direction
```

### Live training report

Roll-forward training trains one model per fold, so a run can be long.
`run_ai.py` prints a live report — learning rate, epochs, per-epoch
loss/accuracy, the current fold and a progress bar with ETA:

```bash
python scripts/run_ai.py --quick        # fast smoke run (~30s)
python scripts/run_ai.py --folds 10     # cap the number of folds
python scripts/run_ai.py --no-epoch-lines   # only the per-fold bar
```

```
fold   3/5 | train[0:192] (192 samples) -> val[192:200] (8 samples)
  epoch 1/2 | loss 0.7169 | val_loss 0.7126 | acc 0.4896 | lr 1.50e-04
[#################-----------]  60.0% | fold 3/5 | 3.0s/fold | eta 6s
```

The Wavenet uses causal convolutions (explicit left-padding, Keras 3
compatible) with gated activations and skip connections, so it is
roll-forward safe by construction. TensorFlow tests are skipped by
default; run them with `RUN_TF=1 python -m pytest`.
