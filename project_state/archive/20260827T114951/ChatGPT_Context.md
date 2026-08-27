# ChatGPT Context — ShadBotTrader


## Project Identity

- Project name: ShadBotTrader
- Architecture version: 1.0
- Python version: 3.13.14
- Snapshot generated at: 2026-08-27T11:18:32.521104+00:00

## Current Architecture

- Clean Architecture + Domain-Driven Design
- Dependency direction: infrastructure -> application -> domain
- Event-driven + plugin-based core
- Source modules: 317
- Test modules: 128

## Current Phase

Phase 28 - Implementation Foundation + Phases 29-31 (dual models, 100k dataset, live loop) + Phase 24 Deployment + Phases 9/21/22 completed + Phase 32 (multi-account profiles, per-broker symbol mapping, every run driven from the GUI) + Phase 33 (incremental dataset updates with learned market calendar and gap backfill) + Phase 34 (candlestick chart and dataset inspection at /data) + Phase 35 (two separate 5M/1H training datasets, rows trimmed only from the ends, generated candles never stored under a real symbol, one canonical symbol per instrument) + Phase 36 (live training progress in the console and the dashboard, per-fold metrics reported against a majority-class baseline) + Phase 37 (live feature-computation progress, and one feature store per symbol/timeframe instead of a shared directory) + Phase 38 (features reused until the candle fingerprint changes, then fully recomputed; the training matrix is 14 candle columns plus all 109 catalogue features) + Phase 39 (the training matrix reads stored features and is proven byte-identical to the computed one; the 1D timeframe has its own candles, features, dataset and range model; the operator chooses which model trains on which dataset) + Phase 40 (model type, dataset and saved model are dropdowns; trained models are persisted with the role and dataset that produced them; retraining adds a version instead of replacing one) + Phases 41-48 (streamed training, capped progress lines, batch count from fold geometry, batch size scaled to the data, a signal threshold field and a live broker spread, per-epoch checkpoints, the best epoch kept rather than the last, and buttons to test a model on a dataset and inspect a dataset) + Phase 50 (the signal model is binary SELL/BUY only; the old neutral-band/HOLD label is no longer part of the neural-network output; no-trade remains a strategy-level decision)

## Implemented Components

- ShadBotTrader

## Git Commit

- Branch: main
- Commit: 4caceb43d83234c724b8fb6dafaee3401ef95f05
- Dirty: yes (2 files)
- Recent commits:
  - 4caceb4 docs: Phase 63 post-fix verification — range retrain healthy (val_mae $9.1, no collapse)
  - 2845ac0 docs: visual schematic of the range dataset (post bug-47 semantics)
  - 1e80fd2 Phase 63 follow-up: printed val-fold size now matches the real fold for the range model
  - 554faf2 Phase 63: fix bug 47/48 — seq2seq range labels were constant (collapse + fake metric)
  - 3ffe030 docs: A/B result — window=150 4x2 beats window=300 5x2 (val_loss 0.587 vs 0.667)
  - da27bc2 docs: why the old 72% and today's 69.9% are not comparable + recovery plan
  - a64e953 docs: end-to-end trace of the signal training dataset (code-verified)
  - 8e2ab84 docs: plain-language appendix for RF/window coverage (Phase 61)
  - 1661ee5 Phase 62: expose architecture/validation knobs in the dashboard
  - 9ec618b Phase 61: architecture knobs (--n-layers/--n-blocks) + RF print & guard

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

- Total files: 792
- Source files: 317
- Test files: 128
- Documentation files: 130
- Legacy files: 176
- Total Python lines: 114281
- Modules: 445
- Classes: 759
- Functions: 4285
- External dependencies: 14
