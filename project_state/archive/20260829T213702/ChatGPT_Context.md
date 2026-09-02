# ChatGPT Context — ShadBotTrader


## Project Identity

- Project name: ShadBotTrader
- Architecture version: 1.0
- Python version: 3.13.14
- Snapshot generated at: 2026-08-29T21:23:56.318344+00:00

## Current Architecture

- Clean Architecture + Domain-Driven Design
- Dependency direction: infrastructure -> application -> domain
- Event-driven + plugin-based core
- Source modules: 318
- Test modules: 133

## Current Phase

Phase 28 - Implementation Foundation + Phases 29-31 (dual models, 100k dataset, live loop) + Phase 24 Deployment + Phases 9/21/22 completed + Phase 32 (multi-account profiles, per-broker symbol mapping, every run driven from the GUI) + Phase 33 (incremental dataset updates with learned market calendar and gap backfill) + Phase 34 (candlestick chart and dataset inspection at /data) + Phase 35 (two separate 5M/1H training datasets, rows trimmed only from the ends, generated candles never stored under a real symbol, one canonical symbol per instrument) + Phase 36 (live training progress in the console and the dashboard, per-fold metrics reported against a majority-class baseline) + Phase 37 (live feature-computation progress, and one feature store per symbol/timeframe instead of a shared directory) + Phase 38 (features reused until the candle fingerprint changes, then fully recomputed; the training matrix is 14 candle columns plus all 109 catalogue features) + Phase 39 (the training matrix reads stored features and is proven byte-identical to the computed one; the 1D timeframe has its own candles, features, dataset and range model; the operator chooses which model trains on which dataset) + Phase 40 (model type, dataset and saved model are dropdowns; trained models are persisted with the role and dataset that produced them; retraining adds a version instead of replacing one) + Phases 41-48 (streamed training, capped progress lines, batch count from fold geometry, batch size scaled to the data, a signal threshold field and a live broker spread, per-epoch checkpoints, the best epoch kept rather than the last, and buttons to test a model on a dataset and inspect a dataset) + Phase 50 (the signal model is binary SELL/BUY only; the old neutral-band/HOLD label is no longer part of the neural-network output; no-trade remains a strategy-level decision)

## Implemented Components

- ShadBotTrader

## Git Commit

- Branch: main
- Commit: 983ed36b776b3aa23ca4fee6e0de16b3eefeea2c
- Dirty: yes (1 files)
- Recent commits:
  - 983ed36 Phase 85: click any /data candle → per-step range forecast path from a chosen model
  - 5dc46a9 Phase 84: signal labels view on /data — operator-set threshold, first-passage markers
  - 2c4fa0d Phase 83: wheel scrolls time (MT-style), Ctrl+wheel zooms price
  - ed5cc57 Phase 82: price zoom & time pan on the /data candle chart
  - 947ce0c Phase 81: price & time zoom on the replay chart (MetaTrader-style)
  - 5084467 docs: zero-trade 1H analysis — signal threshold sits on the range band edge, gate 7 (now fixed) correctly refuses
  - 7b59185 Phase 80: range horizon configurable in the dashboard
  - ea91da3 docs: 1H horizon sweep experiment plan (12/24/6/1) with exact commands
  - 026737b Phase 79: fix bug 55 — streamed range training fed [batch,2] labels to a seq2seq loss
  - 8eb5612 Phase 78: build_trainer accepts and forwards ES/ReduceLR patience (fixes TypeError from Phase 74)

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

- Total files: 806
- Source files: 318
- Test files: 133
- Documentation files: 137
- Legacy files: 176
- Total Python lines: 116590
- Modules: 451
- Classes: 765
- Functions: 4362
- External dependencies: 14
