# ChatGPT Context — ShadBotTrader


## Project Identity

- Project name: ShadBotTrader
- Architecture version: 1.0
- Python version: 3.13.14
- Snapshot generated at: 2026-09-09T12:22:56.904560+00:00

## Current Architecture

- Clean Architecture + Domain-Driven Design
- Dependency direction: infrastructure -> application -> domain
- Event-driven + plugin-based core
- Source modules: 322
- Test modules: 161

## Current Phase

Phase 28 - Implementation Foundation + Phases 29-31 (dual models, 100k dataset, live loop) + Phase 24 Deployment + Phases 9/21/22 completed + Phase 32 (multi-account profiles, per-broker symbol mapping, every run driven from the GUI) + Phase 33 (incremental dataset updates with learned market calendar and gap backfill) + Phase 34 (candlestick chart and dataset inspection at /data) + Phase 35 (two separate 5M/1H training datasets, rows trimmed only from the ends, generated candles never stored under a real symbol, one canonical symbol per instrument) + Phase 36 (live training progress in the console and the dashboard, per-fold metrics reported against a majority-class baseline) + Phase 37 (live feature-computation progress, and one feature store per symbol/timeframe instead of a shared directory) + Phase 38 (features reused until the candle fingerprint changes, then fully recomputed; the training matrix is 14 candle columns plus all 109 catalogue features) + Phase 39 (the training matrix reads stored features and is proven byte-identical to the computed one; the 1D timeframe has its own candles, features, dataset and range model; the operator chooses which model trains on which dataset) + Phase 40 (model type, dataset and saved model are dropdowns; trained models are persisted with the role and dataset that produced them; retraining adds a version instead of replacing one) + Phases 41-48 (streamed training, capped progress lines, batch count from fold geometry, batch size scaled to the data, a signal threshold field and a live broker spread, per-epoch checkpoints, the best epoch kept rather than the last, and buttons to test a model on a dataset and inspect a dataset) + Phase 50 (the signal model is binary SELL/BUY only; the old neutral-band/HOLD label is no longer part of the neural-network output; no-trade remains a strategy-level decision)

## Implemented Components

- ShadBotTrader

## Git Commit

- Branch: main
- Commit: a27b8bf6dfbae6ca35fd7de20519aef2cc24bae4
- Dirty: yes (10 files)
- Recent commits:
  - a27b8bf docs: record full streamed hybrid failure
  - 7f7d793 Phase 116: stream full hybrid replay report
  - ab36196 docs: record hybrid replay sizing result
  - 94ddf4d Phase 116: add hybrid candle replay report
  - 6037a28 Phase 116: add full hybrid 5M report
  - 5ce471a Phase 113: add hybrid significance check
  - 22f9a5b docs: record Phase 125 hybrid backtest results
  - ffe5a4f Phase 125: backtest hybrid head with range brackets
  - c53263d docs: record Phase 124 hybrid head result
  - 00b6695 docs: update operational phase status after hybrid matrix

## Quality Gate

Run from the repository root:
```bash
python -m black --check .
python -m ruff check .
python -m mypy src
python -m pytest
```

## Known Issues

- None recorded for the current foundation.

## Next Phase

Decide how a simulated trade opens and closes. Phase 49 fixed the signal threshold so evaluation grades a model against its own label rule. What remains unanswered is the trade itself: the backtest still runs on the momentum baseline rather than the two trained models, a position closes only when the direction flips, and there is no stop loss, no take profit and no holding period. The operator is reviewing that chain before the next change is made.

## Statistics

- Total files: 898
- Source files: 322
- Test files: 161
- Documentation files: 183
- Legacy files: 176
- Total Python lines: 134752
- Modules: 483
- Classes: 814
- Functions: 4755
- External dependencies: 14
