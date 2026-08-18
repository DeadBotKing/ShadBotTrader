# ChatGPT Context — ShadBotTrader


## Project Identity

- Project name: ShadBotTrader
- Architecture version: 1.0
- Python version: 3.13.14
- Snapshot generated at: 2026-08-18T09:07:54.687800+00:00

## Current Architecture

- Clean Architecture + Domain-Driven Design
- Dependency direction: infrastructure -> application -> domain
- Event-driven + plugin-based core
- Source modules: 293
- Test modules: 112

## Current Phase

Phase 28 - Implementation Foundation + Phases 29-31 (dual models, 100k dataset, live loop) + Phase 24 Deployment + Phases 9/21/22 completed + Phase 32 (multi-account profiles, per-broker symbol mapping, every run driven from the GUI) + Phase 33 (incremental dataset updates with learned market calendar and gap backfill) + Phase 34 (candlestick chart and dataset inspection at /data) + Phase 35 (two separate 5M/1H training datasets, rows trimmed only from the ends, generated candles never stored under a real symbol, one canonical symbol per instrument) + Phase 36 (live training progress in the console and the dashboard, per-fold metrics reported against a majority-class baseline) + Phase 37 (live feature-computation progress, and one feature store per symbol/timeframe instead of a shared directory) + Phase 38 (features reused until the candle fingerprint changes, then fully recomputed; the training matrix is 14 candle columns plus all 109 catalogue features) + Phase 39 (the training matrix reads stored features and is proven byte-identical to the computed one; the 1D timeframe has its own candles, features, dataset and range model; the operator chooses which model trains on which dataset) + Phase 40 (model type, dataset and saved model are dropdowns; trained models are persisted with the role and dataset that produced them; retraining adds a version instead of replacing one)

## Implemented Components

- ShadBotTrader

## Git Commit

- Branch: main
- Commit: d14b5f50a06c90685fedfc0d6dcd6c751801e959
- Dirty: yes (34 files)
- Recent commits:
  - d14b5f5 Update Web Show Train

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

Train on real market data. Every synthetic path into the store is now closed (Phase 35), MT5 is connected, and the platform builds two real datasets — 5M for the signal model and 1H for the range model. What has never happened is a training run on actual broker prices: from the dashboard, Fetch market data (5M,1H) -> Build training dataset -> Train both models — and Phase 36 now shows the loss and accuracy of that run as it happens. Only then does any backtest number mean anything.

## Statistics

- Total files: 720
- Source files: 293
- Test files: 112
- Documentation files: 62
- Legacy files: 176
- Total Python lines: 100508
- Modules: 405
- Classes: 686
- Functions: 3933
- External dependencies: 12
