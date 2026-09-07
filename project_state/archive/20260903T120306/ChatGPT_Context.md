# ChatGPT Context — ShadBotTrader


## Project Identity

- Project name: ShadBotTrader
- Architecture version: 1.0
- Python version: 3.13.14
- Snapshot generated at: 2026-09-03T11:57:32.022523+00:00

## Current Architecture

- Clean Architecture + Domain-Driven Design
- Dependency direction: infrastructure -> application -> domain
- Event-driven + plugin-based core
- Source modules: 319
- Test modules: 144

## Current Phase

Phase 28 - Implementation Foundation + Phases 29-31 (dual models, 100k dataset, live loop) + Phase 24 Deployment + Phases 9/21/22 completed + Phase 32 (multi-account profiles, per-broker symbol mapping, every run driven from the GUI) + Phase 33 (incremental dataset updates with learned market calendar and gap backfill) + Phase 34 (candlestick chart and dataset inspection at /data) + Phase 35 (two separate 5M/1H training datasets, rows trimmed only from the ends, generated candles never stored under a real symbol, one canonical symbol per instrument) + Phase 36 (live training progress in the console and the dashboard, per-fold metrics reported against a majority-class baseline) + Phase 37 (live feature-computation progress, and one feature store per symbol/timeframe instead of a shared directory) + Phase 38 (features reused until the candle fingerprint changes, then fully recomputed; the training matrix is 14 candle columns plus all 109 catalogue features) + Phase 39 (the training matrix reads stored features and is proven byte-identical to the computed one; the 1D timeframe has its own candles, features, dataset and range model; the operator chooses which model trains on which dataset) + Phase 40 (model type, dataset and saved model are dropdowns; trained models are persisted with the role and dataset that produced them; retraining adds a version instead of replacing one) + Phases 41-48 (streamed training, capped progress lines, batch count from fold geometry, batch size scaled to the data, a signal threshold field and a live broker spread, per-epoch checkpoints, the best epoch kept rather than the last, and buttons to test a model on a dataset and inspect a dataset) + Phase 50 (the signal model is binary SELL/BUY only; the old neutral-band/HOLD label is no longer part of the neural-network output; no-trade remains a strategy-level decision)

## Implemented Components

- ShadBotTrader

## Git Commit

- Branch: main
- Commit: 1350c6e5fd32ad18e168f97dba5c2c03fd5e4f7e
- Dirty: yes (2 files)
- Recent commits:
  - 1350c6e Phase 98 fix: trend training honors the selected Dataset
  - 440af28 Phase 98 fix: trend model works for EVERY timeframe (not just 4H)
  - d7e72a2 Phase 98 part 1b: trend_4h in training GUIs + candle-color display on /data
  - aeb3188 Phase 98 part 1: TREND model — next-candle color (GREEN/RED) classification
  - dc2b2a8 Phase 97d: final-SL floor inside _triple_bracket (post-fallback)
  - 73a06a5 Phase 97b: license 4 — entry must sit near the daily level
  - 1ffd367 Phase 97: triple-timeframe strategy (5M signal · 4H bracket · 1D trend)
  - 6ddd6ee Phase 96v: /data range-model list spans every timeframe
  - 58d9413 Phase 96h: MT5 session-first connection (OTP/certificate accounts)
  - 132aef6 Phase 96d: MT5 symbol_select before every data call + actionable error

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

- Total files: 821
- Source files: 319
- Test files: 144
- Documentation files: 140
- Legacy files: 176
- Total Python lines: 120742
- Modules: 463
- Classes: 800
- Functions: 4531
- External dependencies: 14
