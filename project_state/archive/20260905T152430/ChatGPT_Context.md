# ChatGPT Context — ShadBotTrader


## Project Identity

- Project name: ShadBotTrader
- Architecture version: 1.0
- Python version: 3.13.14
- Snapshot generated at: 2026-09-05T14:52:44.320734+00:00

## Current Architecture

- Clean Architecture + Domain-Driven Design
- Dependency direction: infrastructure -> application -> domain
- Event-driven + plugin-based core
- Source modules: 319
- Test modules: 145

## Current Phase

Phase 28 - Implementation Foundation + Phases 29-31 (dual models, 100k dataset, live loop) + Phase 24 Deployment + Phases 9/21/22 completed + Phase 32 (multi-account profiles, per-broker symbol mapping, every run driven from the GUI) + Phase 33 (incremental dataset updates with learned market calendar and gap backfill) + Phase 34 (candlestick chart and dataset inspection at /data) + Phase 35 (two separate 5M/1H training datasets, rows trimmed only from the ends, generated candles never stored under a real symbol, one canonical symbol per instrument) + Phase 36 (live training progress in the console and the dashboard, per-fold metrics reported against a majority-class baseline) + Phase 37 (live feature-computation progress, and one feature store per symbol/timeframe instead of a shared directory) + Phase 38 (features reused until the candle fingerprint changes, then fully recomputed; the training matrix is 14 candle columns plus all 109 catalogue features) + Phase 39 (the training matrix reads stored features and is proven byte-identical to the computed one; the 1D timeframe has its own candles, features, dataset and range model; the operator chooses which model trains on which dataset) + Phase 40 (model type, dataset and saved model are dropdowns; trained models are persisted with the role and dataset that produced them; retraining adds a version instead of replacing one) + Phases 41-48 (streamed training, capped progress lines, batch count from fold geometry, batch size scaled to the data, a signal threshold field and a live broker spread, per-epoch checkpoints, the best epoch kept rather than the last, and buttons to test a model on a dataset and inspect a dataset) + Phase 50 (the signal model is binary SELL/BUY only; the old neutral-band/HOLD label is no longer part of the neural-network output; no-trade remains a strategy-level decision)

## Implemented Components

- ShadBotTrader

## Git Commit

- Branch: main
- Commit: d0f92be0f4f88ba4767ebbb22a21b3c047f911e7
- Dirty: yes (1 files)
- Recent commits:
  - d0f92be Phase 98b fix: show REAL server error instead of hardcoded 'not saved'
  - df38839 Phase 98b FINAL fix: fetchTrendColor never used modelOverride
  - 1648634 Phase 98b ROOT CAUSE fix: fetchTrendColor ignored modelOverride
  - 2a4b74e Phase 98b fix: /data only shows same-timeframe models
  - dd32522 Phase 98b fix: fetchTrendColor missing modelOverride parameter
  - 23c6dfa Phase 98b fix: 'trend: color is not defined' — undefined JS variable
  - 2faeecb Phase 98b fix: remove automatic trend-color fetch for non-trend models
  - 5575ce4 Phase 98b fix: /data trend color lookup + ATR barrier tests
  - cb2f30f Phase 98b fix: trend_score in the Train model dropdown
  - 91e0af5 Phase 98b: trend_score model (regression on daily-candle strength score) + HOLD fix

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

- Total files: 822
- Source files: 319
- Test files: 145
- Documentation files: 140
- Legacy files: 176
- Total Python lines: 121453
- Modules: 464
- Classes: 803
- Functions: 4551
- External dependencies: 14
