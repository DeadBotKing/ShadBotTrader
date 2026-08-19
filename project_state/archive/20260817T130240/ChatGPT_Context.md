# ChatGPT Context — ShadBotTrader


## Project Identity

- Project name: ShadBotTrader
- Architecture version: 1.0
- Python version: 3.13.14
- Snapshot generated at: 2026-08-17T12:56:38.714778+00:00

## Current Architecture

- Clean Architecture + Domain-Driven Design
- Dependency direction: infrastructure -> application -> domain
- Event-driven + plugin-based core
- Source modules: 292
- Test modules: 106

## Current Phase

Phase 28 - Implementation Foundation + Phases 29-31 (dual models, 100k dataset, live loop) + Phase 24 Deployment + Phases 9/21/22 completed + Phase 32 (multi-account profiles, per-broker symbol mapping, every run driven from the GUI) + Phase 33 (incremental dataset updates with learned market calendar and gap backfill) + Phase 34 (candlestick chart and dataset inspection at /data) + Phase 35 (two separate 5M/1H training datasets, rows trimmed only from the ends, generated candles never stored under a real symbol, one canonical symbol per instrument) + Phase 36 (live training progress in the console and the dashboard, per-fold metrics reported against a majority-class baseline) + Phase 37 (live feature-computation progress, and one feature store per symbol/timeframe instead of a shared directory) + Phase 38 (features reused until the candle fingerprint changes, then fully recomputed; the training matrix is 14 candle columns plus all 109 catalogue features)

## Implemented Components

- ShadBotTrader

## Git Commit

- Branch: main
- Commit: f8bf0a92976a0d387f8a4e15eca7ee7b51204346
- Dirty: yes (29 files)
- Recent commits:
  - f8bf0a9 Real Dataset

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

- Total files: 697
- Source files: 292
- Test files: 106
- Documentation files: 55
- Legacy files: 176
- Total Python lines: 97995
- Modules: 398
- Classes: 650
- Functions: 3796
- External dependencies: 12
