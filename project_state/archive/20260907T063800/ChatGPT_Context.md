# ChatGPT Context — ShadBotTrader


## Project Identity

- Project name: ShadBotTrader
- Architecture version: 1.0
- Python version: 3.13.14
- Snapshot generated at: 2026-09-07T06:37:33.350782+00:00

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
- Commit: e5ca86308c5cdcc4fc46ec102a6a3888f0ff555e
- Dirty: yes (18 files)
- Recent commits:
  - e5ca863 Phase 101: fix Windows dashboard live training log streaming
  - d6ac7c7 docs: Phase 100 model card — dataset, real-candle target with worked examples, full WaveNet architecture (activations+RangeLoss), and the range-vs-score learnability proof (vol clusters corr 0.997 vs daily drift corr 0.002)
  - 08b596d Phase 100: trend_score on the REAL next 1D candle — first-class wiring, sanity-pred crash fix, stream-threshold env knob; trained gold_trend_score_1d v1 + gold_trend_1d v1 on 10y real gold data (honest verdict documented)
  - a062474 docs: trend_score_1d proposal — real daily candle score target analysis
  - a7f1ff9 docs: score constant across candles — model converged to mean, not a code bug
  - 57f9467 Phase 98b: full target statistics printed before trend_score training
  - b97546c Phase 98b fix: /data inspector model_role → range for trend_score (184 features, 1-output tanh — verified end-to-end in sandbox)
  - 2b634ea Phase 98b: trend_score uses full range seq2seq architecture with 1 output
  - 997516e Phase 98b: trend_score architecture verified — Dense(1, tanh) ✓
  - a013858 Phase 98b: /data trend endpoint handles all 3 model types (score, signal, color)

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

- Total files: 828
- Source files: 319
- Test files: 145
- Documentation files: 144
- Legacy files: 176
- Total Python lines: 122472
- Modules: 464
- Classes: 803
- Functions: 4566
- External dependencies: 14
