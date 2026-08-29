# ChatGPT Context — ShadBotTrader


## Project Identity

- Project name: ShadBotTrader
- Architecture version: 1.0
- Python version: 3.13.14
- Snapshot generated at: 2026-08-29T07:10:36.685421+00:00

## Current Architecture

- Clean Architecture + Domain-Driven Design
- Dependency direction: infrastructure -> application -> domain
- Event-driven + plugin-based core
- Source modules: 317
- Test modules: 131

## Current Phase

Phase 28 - Implementation Foundation + Phases 29-31 (dual models, 100k dataset, live loop) + Phase 24 Deployment + Phases 9/21/22 completed + Phase 32 (multi-account profiles, per-broker symbol mapping, every run driven from the GUI) + Phase 33 (incremental dataset updates with learned market calendar and gap backfill) + Phase 34 (candlestick chart and dataset inspection at /data) + Phase 35 (two separate 5M/1H training datasets, rows trimmed only from the ends, generated candles never stored under a real symbol, one canonical symbol per instrument) + Phase 36 (live training progress in the console and the dashboard, per-fold metrics reported against a majority-class baseline) + Phase 37 (live feature-computation progress, and one feature store per symbol/timeframe instead of a shared directory) + Phase 38 (features reused until the candle fingerprint changes, then fully recomputed; the training matrix is 14 candle columns plus all 109 catalogue features) + Phase 39 (the training matrix reads stored features and is proven byte-identical to the computed one; the 1D timeframe has its own candles, features, dataset and range model; the operator chooses which model trains on which dataset) + Phase 40 (model type, dataset and saved model are dropdowns; trained models are persisted with the role and dataset that produced them; retraining adds a version instead of replacing one) + Phases 41-48 (streamed training, capped progress lines, batch count from fold geometry, batch size scaled to the data, a signal threshold field and a live broker spread, per-epoch checkpoints, the best epoch kept rather than the last, and buttons to test a model on a dataset and inspect a dataset) + Phase 50 (the signal model is binary SELL/BUY only; the old neutral-band/HOLD label is no longer part of the neural-network output; no-trade remains a strategy-level decision)

## Implemented Components

- ShadBotTrader

## Git Commit

- Branch: main
- Commit: c8b3749f02a1fe815b8db610da9250bcba16d367
- Dirty: yes (2 files)
- Recent commits:
  - c8b3749 Phase 75: recenter inverted brackets around entry instead of rejecting
  - 7aee78e docs: post-fix analysis of the 154-trade backtest — bug 53 (SL hugging entry)
  - ccc404f docs: the NameError belonged to the interim 84d4851 zip — fixed since 5188801
  - 5188801 Phase 74: configurable EarlyStopping/ReduceLROnPlateau patience
  - f18533c Phase 73 lint: dedupe pytest import
  - f61eb51 Phase 73: fix bug 52 — refuse brackets whose stop lands on the profit side
  - 3527b8c docs: full analysis of the 2110-trade backtest — bracket inversion bug 52 exposed
  - 84d4851 Phase 72: full 'start conditions' section in the backtest report
  - 8f97a67 Phase 70: fix bug 51 — _RangeLoss/_Seq2SeqMAE were function-local, range models could never load
  - dbd0570 Phase 69: surface signal/range counts and silent errors in the backtest report

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

- Total files: 799
- Source files: 317
- Test files: 131
- Documentation files: 134
- Legacy files: 176
- Total Python lines: 115528
- Modules: 448
- Classes: 763
- Functions: 4340
- External dependencies: 14
