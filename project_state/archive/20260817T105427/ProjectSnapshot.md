# Project Snapshot

- Project name: ShadBotTrader
- Architecture version: 1.0
- Current phase: Phase 28 - Implementation Foundation + Phases 29-31 (dual models, 100k dataset, live loop) + Phase 24 Deployment + Phases 9/21/22 completed + Phase 32 (multi-account profiles, per-broker symbol mapping, every run driven from the GUI) + Phase 33 (incremental dataset updates with learned market calendar and gap backfill) + Phase 34 (candlestick chart and dataset inspection at /data) + Phase 35 (two separate 5M/1H training datasets, rows trimmed only from the ends, generated candles never stored under a real symbol, one canonical symbol per instrument) + Phase 36 (live training progress in the console and the dashboard, per-fold metrics reported against a majority-class baseline) + Phase 37 (live feature-computation progress, and one feature store per symbol/timeframe instead of a shared directory)
- Generated at: 2026-08-17T10:48:50.469445+00:00
- Python version: 3.13.14
- Git branch: main
- Git commit: 22e6743c8c948a0916fc4183319e6b123bd6db72
- Dirty: yes

## Statistics

- Source files: 290
- Test files: 104
- Documentation files: 54
- Legacy files: 175
- Total Python lines: 96756
- Modules: 394
- Classes: 640
- Functions: 3733

## External dependencies (top 20)

- pytest: used by 63 module(s)
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