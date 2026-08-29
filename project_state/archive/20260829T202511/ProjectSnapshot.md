# Project Snapshot

- Project name: ShadBotTrader
- Architecture version: 1.0
- Current phase: Phase 28 - Implementation Foundation + Phases 29-31 (dual models, 100k dataset, live loop) + Phase 24 Deployment + Phases 9/21/22 completed + Phase 32 (multi-account profiles, per-broker symbol mapping, every run driven from the GUI) + Phase 33 (incremental dataset updates with learned market calendar and gap backfill) + Phase 34 (candlestick chart and dataset inspection at /data) + Phase 35 (two separate 5M/1H training datasets, rows trimmed only from the ends, generated candles never stored under a real symbol, one canonical symbol per instrument) + Phase 36 (live training progress in the console and the dashboard, per-fold metrics reported against a majority-class baseline) + Phase 37 (live feature-computation progress, and one feature store per symbol/timeframe instead of a shared directory) + Phase 38 (features reused until the candle fingerprint changes, then fully recomputed; the training matrix is 14 candle columns plus all 109 catalogue features) + Phase 39 (the training matrix reads stored features and is proven byte-identical to the computed one; the 1D timeframe has its own candles, features, dataset and range model; the operator chooses which model trains on which dataset) + Phase 40 (model type, dataset and saved model are dropdowns; trained models are persisted with the role and dataset that produced them; retraining adds a version instead of replacing one) + Phases 41-48 (streamed training, capped progress lines, batch count from fold geometry, batch size scaled to the data, a signal threshold field and a live broker spread, per-epoch checkpoints, the best epoch kept rather than the last, and buttons to test a model on a dataset and inspect a dataset) + Phase 50 (the signal model is binary SELL/BUY only; the old neutral-band/HOLD label is no longer part of the neural-network output; no-trade remains a strategy-level decision)
- Generated at: 2026-08-29T18:37:26.855804+00:00
- Python version: 3.13.14
- Git branch: main
- Git commit: 947ce0ccf140101dd9238abe2b1b566921d89a94
- Dirty: yes

## Statistics

- Source files: 317
- Test files: 133
- Documentation files: 137
- Legacy files: 176
- Total Python lines: 115994
- Modules: 450
- Classes: 763
- Functions: 4356

## External dependencies (top 20)

- pytest: used by 82 module(s)
- numpy: used by 25 module(s)
- pandas: used by 22 module(s)
- tests: used by 12 module(s)
- tensorflow: used by 10 module(s)
- conftest: used by 4 module(s)
- keras: used by 2 module(s)
- pyarrow: used by 2 module(s)
- yaml: used by 2 module(s)
- MetaTrader5: used by 1 module(s)
- PIL: used by 1 module(s)
- pywt: used by 1 module(s)
- run_dual_models: used by 1 module(s)
- tomli: used by 1 module(s)