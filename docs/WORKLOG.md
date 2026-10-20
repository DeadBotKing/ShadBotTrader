# WORKLOG

## 2026-10-20 — active tree slimmed to data, features, and range

Owner asked to start again from the data path and to move everything else into an old-version folder. `legacy/` was not touched.

Kept in the active tree:

```text
MetaTrader ingest
dataset build
feature build
range model trainer and audits
```

Moved to `old_version/`:

```text
backtest, live, execution, simulation, strategy
pivot, hybrid, trend-only scripts
GUI / presentation
historical docs and phase reports
```

`run_dual_models.py` stayed because it is the range trainer. It still contains the signal/trend branches in the same file.

No training. No model replacement. No paper/live.

## 2026-10-20 — dataset and feature inspector

Added a local page for inspecting stored candles and `FXTradingFeatureSetV1`.

```text
python scripts/inspect_dataset_features.py --storage-root datasets --port 8765
```

It does not train and does not write datasets.
