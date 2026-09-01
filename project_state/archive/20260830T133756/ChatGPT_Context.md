# ChatGPT Context — ShadBotTrader


## Project Identity

- Project name: ShadBotTrader
- Architecture version: 1.0
- Python version: 3.13.14
- Snapshot generated at: 2026-08-30T13:33:30.301621+00:00

## Current Architecture

- Clean Architecture + Domain-Driven Design
- Dependency direction: infrastructure -> application -> domain
- Event-driven + plugin-based core
- Source modules: 319
- Test modules: 136

## Current Phase

Phase 28 - Implementation Foundation + Phases 29-31 (dual models, 100k dataset, live loop) + Phase 24 Deployment + Phases 9/21/22 completed + Phase 32 (multi-account profiles, per-broker symbol mapping, every run driven from the GUI) + Phase 33 (incremental dataset updates with learned market calendar and gap backfill) + Phase 34 (candlestick chart and dataset inspection at /data) + Phase 35 (two separate 5M/1H training datasets, rows trimmed only from the ends, generated candles never stored under a real symbol, one canonical symbol per instrument) + Phase 36 (live training progress in the console and the dashboard, per-fold metrics reported against a majority-class baseline) + Phase 37 (live feature-computation progress, and one feature store per symbol/timeframe instead of a shared directory) + Phase 38 (features reused until the candle fingerprint changes, then fully recomputed; the training matrix is 14 candle columns plus all 109 catalogue features) + Phase 39 (the training matrix reads stored features and is proven byte-identical to the computed one; the 1D timeframe has its own candles, features, dataset and range model; the operator chooses which model trains on which dataset) + Phase 40 (model type, dataset and saved model are dropdowns; trained models are persisted with the role and dataset that produced them; retraining adds a version instead of replacing one) + Phases 41-48 (streamed training, capped progress lines, batch count from fold geometry, batch size scaled to the data, a signal threshold field and a live broker spread, per-epoch checkpoints, the best epoch kept rather than the last, and buttons to test a model on a dataset and inspect a dataset) + Phase 50 (the signal model is binary SELL/BUY only; the old neutral-band/HOLD label is no longer part of the neural-network output; no-trade remains a strategy-level decision)

## Implemented Components

- ShadBotTrader

## Git Commit

- Branch: main
- Commit: 1f1515679cf81719cb1d35b043bd4a841b600b52
- Dirty: yes (53 files)
- Recent commits:
  - 1f15156 docs: root cause analysis — constant offset is a structural limitation, not a code bug
  - dd52ad0 docs: range model constant-offset analysis — structural limitation of minmax-scaled input + percentage targets
  - 0ef5eeb Phase 94: fix bug 58 — statsHtml was const but received += Base price
  - 0b008a9 Phase 94: silence browser-abort errors in server; show base price in forecast table
  - 1e66be8 Phase 93: remove duplicate plotW/step/yP/xOf declarations in draw — SyntaxError made /data chart black
  - 53b78ae Phase 92: fix forecast path never drawing on /data — renderForecast was missing forecastPath wiring
  - bb21be6 Phase 91: vertical pan on the price axis (when zoomed)
  - 8ad4bd8 Phase 90: warmup pad for /data forecast + price-axis wheel zoom
  - 39f3ed7 Phase 89: restore range model dropdown JS + extend candles to 5000
  - dc2dfc8 Phase 88: fix signal markers not drawing — index mismatch between computeSignals (local) and indexOf (global)

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

- Total files: 812
- Source files: 319
- Test files: 136
- Documentation files: 139
- Legacy files: 176
- Total Python lines: 118014
- Modules: 455
- Classes: 777
- Functions: 4410
- External dependencies: 14
