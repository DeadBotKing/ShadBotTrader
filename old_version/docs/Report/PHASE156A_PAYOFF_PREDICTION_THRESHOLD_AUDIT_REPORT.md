# PHASE156A — Payoff Prediction Threshold Calibration Audit Report

## Summary

Phase156A has been implemented to answer whether the Phase155A payoff Option B models contain usable low-confidence signal hidden behind too-strict fixed thresholds.

This phase does not retrain. It loads existing B4/B2 models and runs validation-only threshold selection followed by one test confirmation.

## Implemented files

```text
scripts/audit_pivot_payoff_prediction_thresholds.py
tests/unit/ai/test_pivot_payoff_prediction_thresholds.py
```

GUI integration:

```text
CommandKind.AUDIT_PIVOT_PAYOFF_PREDICTION_THRESHOLDS
GUI label: Audit payoff prediction thresholds
```

Updated:

```text
src/ShadBotTrader/presentation/commands/commands.py
src/ShadBotTrader/presentation/commands/handlers.py
tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py
```

## Method

For each candidate:

```text
B4 → gold_pivot_payoff_option_b_b4_5m
B2 → gold_pivot_payoff_option_b_b2_5m
```

The script:

```text
1. Loads tensor/meta/flat.
2. Loads latest or specified Keras model.
3. Predicts validation and test splits.
4. Computes probability summaries.
5. Scans threshold policies on validation only.
6. Selects by validation score/pass gate.
7. Runs the exact selected policy on test once.
```

## Default threshold grid

```text
buy_thresholds  = 0.05,0.10,0.15,0.20,0.25,0.30,0.34,0.40,0.50
sell_thresholds = 0.05,0.10,0.15,0.20,0.25,0.30,0.34,0.40,0.50
margins         = 0,0.03,0.05,0.10
min_buy_r       = none,0,0.25
min_sell_r      = none,0,0.25
```

## Outputs

```text
run_logs\pivot_payoff_prediction_thresholds\latest.json
run_logs\pivot_payoff_prediction_thresholds\latest.html
run_logs\pivot_payoff_prediction_thresholds\latest_validation_grid.csv
run_logs\pivot_payoff_prediction_thresholds\latest_selection.csv
run_logs\pivot_payoff_prediction_thresholds\latest_probability_summary.csv
```

## Recommended owner command

```powershell
python -u scripts\audit_pivot_payoff_prediction_thresholds.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --candidates B4,B2 `
  --model-version 0 `
  --max-samples 24000 `
  --train-frac 0.70 `
  --val-frac 0.15 `
  --purge-gap 336 `
  --batch-size 128 `
  --validation-min-trades 20 `
  --validation-min-profit-factor 1.05 `
  --test-min-trades 20 `
  --test-min-profit-factor 1.05 `
  --score-metric drawdown_adjusted `
  --storage-root datasets `
  --output-dir run_logs\pivot_payoff_prediction_thresholds
```

## Verification

```text
python -m py_compile scripts/audit_pivot_payoff_prediction_thresholds.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/ai/test_pivot_payoff_prediction_thresholds.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py
→ passed

python -m pytest tests/unit/ai/test_pivot_payoff_prediction_thresholds.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ 49 passed
```

Full ruff/black unavailable in this sandbox image:

```text
No module named ruff
No module named black
```

## Production status

```text
BLOCKED — threshold audit only
No Phase134.
No paper shadow.
No live trading.
```
