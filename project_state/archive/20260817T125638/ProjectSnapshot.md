# Project Snapshot

- Project name: ShadBotTrader
- Architecture version: 1.0
- Current phase: Phase 28 - Implementation Foundation + Phases 29-31 (dual models, 100k dataset, live loop) + Phase 24 Deployment + Phases 9/21/22 completed + Phase 32 (multi-account profiles, per-broker symbol mapping, every run driven from the GUI) + Phase 33 (incremental dataset updates with learned market calendar and gap backfill) + Phase 34 (candlestick chart and dataset inspection at /data) + Phase 35 (two separate 5M/1H training datasets, rows trimmed only from the ends, generated candles never stored under a real symbol, one canonical symbol per instrument) + Phase 36 (live training progress in the console and the dashboard, per-fold metrics reported against a majority-class baseline) + Phase 37 (live feature-computation progress, and one feature store per symbol/timeframe instead of a shared directory) + Phase 38 (features reused until the candle fingerprint changes, then fully recomputed; the training matrix is 14 candle columns plus all 109 catalogue features)
- Generated at: 2026-08-17T12:48:39.769097+00:00
- Python version: 3.13.14
- Git branch: main
- Git commit: f8bf0a92976a0d387f8a4e15eca7ee7b51204346
- Dirty: yes

## Statistics

- Source files: 292
- Test files: 106
- Documentation files: 55
- Legacy files: 176
- Total Python lines: 97981
- Modules: 398
- Classes: 650
- Functions: 3795

## External dependencies (top 20)

- pytest: used by 65 module(s)
- numpy: used by 11 module(s)
- tests: used by 11 module(s)
- pandas: used by 7 module(s)
- tensorflow: used by 5 module(s)
- conftest: used by 4 module(s)
- keras: used by 2 module(s)
- pyarrow: used by 2 module(s)
- yaml: used by 2 module(s)
- MetaTrader5: used by 1 module(s)
- pywt: used by 1 module(s)
- tomli: used by 1 module(s)