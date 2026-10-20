# PHASE186A — Range Candle-by-Candle Forecast Accuracy Audit Report

## Summary

Phase186A is implemented. The owner run is recorded in `docs/Report/PHASE186A_RANGE_MULTISTEP_ACCURACY_RESULT.md`.

Owner result, short form:

```text
model_output_horizon=1 on gold_range_4h v3 and gold_range_1d v2
keras_output_shape=(None, 150, 2)
steps 2,3,4,5 were not emitted
candle_forecast_ready_gate=0
CANDLE_BY_CANDLE_FUTURE_STEPS=NOT_AVAILABLE
PAPER_OR_LIVE=BLOCKED
```

It measures high/low accuracy for each future candle the range model actually emits.

```text
No model training.
No Phase134.
No paper shadow.
No live trading.
No gate relaxation.
```

The owner result is now recorded. Use the result document for the measured numbers. This implementation report does not replace it.

## Implemented files

```text
scripts/audit_range_multistep_accuracy.py
tests/unit/ai/test_range_multistep_accuracy.py
```

GUI integration:

```text
CommandKind.AUDIT_RANGE_MULTISTEP_ACCURACY
GUI label: Audit range multistep accuracy
```

Updated files:

```text
src/ShadBotTrader/presentation/commands/commands.py
src/ShadBotTrader/presentation/commands/handlers.py
tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py
```

## Audit contract

```text
step k is candle t+k, not the max/min envelope over t+1..t+H
seq2seq layout is the last timestep: [high_1, low_1, ..., high_H, low_H]
scalar [high, low] is step 1 only
missing steps are reported, not imputed
recursive rollout is not used
open/close are not model targets
```

## What the owner should read first

```text
model_output_horizon
multi_step_available
missing_steps
capability_verdict
owner_answer
```

If the live tensor still has `model_output_horizon=1`, only the next candle is auditable. That is a capability result, not a hidden failure of the audit.

## Main outputs

```text
run_logs\range_multistep_accuracy\latest.json
run_logs\range_multistep_accuracy\latest.html
run_logs\range_multistep_accuracy\latest_model_capability.csv
run_logs\range_multistep_accuracy\latest_step_errors.csv
run_logs\range_multistep_accuracy\latest_bias_by_step.csv
run_logs\range_multistep_accuracy\latest_calibration_by_step.csv
run_logs\range_multistep_accuracy\latest_degradation_curve.csv
run_logs\range_multistep_accuracy\latest_regime_breakdown.csv
```

## Recommended owner action

Run from GUI:

```text
AI → Audit range multistep accuracy
```

or CLI:

```powershell
python -u scripts\audit_range_multistep_accuracy.py `
  --symbol XAUUSD `
  --timeframes "4H,1D" `
  --source-mode models `
  --range-4h-model-id gold_range_4h `
  --range-4h-version 0 `
  --range-1d-model-id gold_range_1d `
  --range-1d-version 0 `
  --requested-steps 5 `
  --batch-size 256 `
  --progress-every 2000 `
  --storage-root datasets `
  --output-dir run_logs\range_multistep_accuracy
```

Then send:

```text
run_logs\range_multistep_accuracy\latest.json
```

## Verification

```text
python -m py_compile scripts/audit_range_multistep_accuracy.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/ai/test_range_multistep_accuracy.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py
→ passed

python -m pytest tests/unit/ai/test_range_multistep_accuracy.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ 86 passed

ruff/black/mypy
→ unavailable in this sandbox
```

## Production status

```text
BLOCKED
```
