# ChatGPT Context — ShadBotTrader


## Project Identity

- Project name: ShadBotTrader
- Architecture version: 1.0
- Python version: 3.13.14
- Snapshot generated at: 2026-09-05T05:47:10.867370+00:00

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
- Commit: 0892f655cf0aaf9b17f18def81f282d754375813
- Dirty: no
- Recent commits:
  - 0892f65 Phase 99 UI: trend_signal in Train/Retrain/LR-sweep forms
  - 7dcbefa docs: gold_trend_1d 400x3 run analysis — 57.0% vs 53.2% baseline, edge thin
  - 9754480 Phase 99: trend-signal model — 3-class BUY/HOLD/SELL on rolling 288x5M
  - c5fbf12 Phase 98 fix: trend panel was never shown (render-side, not server-side)
  - 57233d4 Phase 98 fix: /data trend forecast no longer hangs — model + feature caches
  - ff3cdc8 Phase 98: trend model appears in /data dropdown
  - 0eeadd3 Phase 98 fix: trend dataset is plain stride-1 (no sample_ends pair)
  - 1350c6e Phase 98 fix: trend training honors the selected Dataset
  - 440af28 Phase 98 fix: trend model works for EVERY timeframe (not just 4H)
  - d7e72a2 Phase 98 part 1b: trend_4h in training GUIs + candle-color display on /data

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
- Total Python lines: 121254
- Modules: 464
- Classes: 802
- Functions: 4546
- External dependencies: 14
