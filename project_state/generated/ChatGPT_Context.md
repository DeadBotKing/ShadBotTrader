# ChatGPT Context — ShadBotTrader


## Project Identity

- Project name: ShadBotTrader
- Architecture version: 1.0
- Python version: 3.12.10
- Snapshot generated at: 2026-08-19T05:08:56.754319+00:00

## Current Architecture

- Clean Architecture + Domain-Driven Design
- Dependency direction: infrastructure -> application -> domain
- Event-driven + plugin-based core
- Source modules: 295
- Test modules: 116

## Current Phase

Phase 28 - Implementation Foundation + Phases 29-31 (dual models, 100k dataset, live loop) + Phase 24 Deployment + Phases 9/21/22 completed + Phase 32 (multi-account profiles, per-broker symbol mapping, every run driven from the GUI) + Phase 33 (incremental dataset updates with learned market calendar and gap backfill) + Phase 34 (candlestick chart and dataset inspection at /data) + Phase 35 (two separate 5M/1H training datasets, rows trimmed only from the ends, generated candles never stored under a real symbol, one canonical symbol per instrument) + Phase 36 (live training progress in the console and the dashboard, per-fold metrics reported against a majority-class baseline) + Phase 37 (live feature-computation progress, and one feature store per symbol/timeframe instead of a shared directory) + Phase 38 (features reused until the candle fingerprint changes, then fully recomputed; the training matrix is 14 candle columns plus all 109 catalogue features) + Phase 39 (the training matrix reads stored features and is proven byte-identical to the computed one; the 1D timeframe has its own candles, features, dataset and range model; the operator chooses which model trains on which dataset) + Phase 40 (model type, dataset and saved model are dropdowns; trained models are persisted with the role and dataset that produced them; retraining adds a version instead of replacing one) + Phases 41-48 (streamed training, capped progress lines, batch count from fold geometry, batch size scaled to the data, a signal threshold field and a live broker spread, per-epoch checkpoints, the best epoch kept rather than the last, and buttons to test a model on a dataset and inspect a dataset) + Phase 49 (a signal model records the neutral band it was trained with, and evaluation rebuilds the labels with that band instead of a hard-coded 0.08%)

## Implemented Components

- ShadBotTrader

## Git Commit

- Branch: main
- Commit: 75d71d22105b941ee1fe18238ed3bb345c1708a6
- Dirty: no
- Recent commits:
  - 75d71d2 Model Train Update 1
  - 8242d55 Update Gui Train Retrain and show model structure
  - 05c6448 Update Training 1
  - d14b5f5 Update Web Show Train
  - 7b4cac6 Update gitignore For Parquet
  - 6c129ac DeleteDataset
  - c11471b Update .gitignore
  - 4656135 Update .gitignore
  - 3b10dca 1D Features
  - 5f27e4e Adding 1D TimeFrame

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

- Total files: 739
- Source files: 295
- Test files: 116
- Documentation files: 66
- Legacy files: 176
- Total Python lines: 102967
- Modules: 411
- Classes: 719
- Functions: 4034
- External dependencies: 13
