# PHASE185A — Range Model Reliability / Calibration / Decision-Utility Audit Report

## Summary

Phase185A has been implemented to audit the 4H and 1D range models before trusting them as TP/SL engines, signal engines, or context features.

```text
No model training.
No Phase134.
No paper shadow.
No live trading.
No gate relaxation.
```

## Implemented files

```text
scripts/audit_range_model_reliability.py
tests/unit/ai/test_range_model_reliability.py
```

GUI integration:

```text
CommandKind.AUDIT_RANGE_MODEL_RELIABILITY
GUI label: Audit range model reliability
```

Updated files:

```text
src/ShadBotTrader/presentation/commands/commands.py
src/ShadBotTrader/presentation/commands/handlers.py
tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py
```

## Audit scope

The audit measures:

```text
forecast coherence
forecast error in ATR units
calibration bins
directional ranking correlation
regime breakdown
simple decision-utility proxy
range-vs-baseline decision matrix
```

## Main outputs

```text
run_logs\range_model_reliability\latest.json
run_logs\range_model_reliability\latest.html
run_logs\range_model_reliability\latest_forecast_errors.csv
run_logs\range_model_reliability\latest_summary.csv
run_logs\range_model_reliability\latest_calibration_bins.csv
run_logs\range_model_reliability\latest_regime_breakdown.csv
run_logs\range_model_reliability\latest_decision_utility.csv
run_logs\range_model_reliability\latest_decision_matrix.csv
```

## Recommended owner action

Run from GUI:

```text
AI → Audit range model reliability
```

or CLI:

```powershell
python -u scripts\audit_range_model_reliability.py `
  --symbol XAUUSD `
  --timeframes "4H,1D" `
  --source-mode models `
  --range-4h-model-id gold_range_4h `
  --range-4h-version 0 `
  --range-1d-model-id gold_range_1d `
  --range-1d-version 0 `
  --h4-flat-path datasets\processed\XAUUSD\4H\v1.parquet `
  --d1-flat-path datasets\processed\XAUUSD\1D\v1.parquet `
  --storage-root datasets `
  --output-dir run_logs\range_model_reliability
```

Then send:

```text
run_logs\range_model_reliability\latest.json
```

## Verification

```text
python -m py_compile scripts/audit_range_model_reliability.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/ai/test_range_model_reliability.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py
→ passed

python -m pytest tests/unit/ai/test_range_model_reliability.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ passed
```

Unavailable in sandbox:

```text
python -m ruff check .        → No module named ruff
python -m black --check .     → No module named black
python -m mypy src            → No module named mypy
```

## Production status

```text
BLOCKED — Phase185A is reliability audit only.
No model training.
No Phase134.
No paper shadow.
No live trading.
```

## Performance hotfix — 2026-10-05

The first owner run with `--source-mode models` did not finish after many hours. Root cause: the initial implementation used a per-row model forecast path that was too slow for full 4H/1D history and had no progress logging.

Fixed in:

```text
scripts/audit_range_model_reliability.py
```

The audit now:

```text
- loads the range model once per timeframe
- runs batch inference via --batch-size
- prints progress via --progress-every
```

Recommended retry:

```powershell
python -u scripts\audit_range_model_reliability.py `
  --symbol XAUUSD `
  --timeframes "4H,1D" `
  --source-mode models `
  --range-4h-model-id gold_range_4h `
  --range-4h-version 0 `
  --range-1d-model-id gold_range_1d `
  --range-1d-version 0 `
  --h4-flat-path datasets\processed\XAUUSD\4H\v1.parquet `
  --d1-flat-path datasets\processed\XAUUSD\1D\v1.parquet `
  --batch-size 256 `
  --progress-every 2000 `
  --storage-root datasets `
  --output-dir run_logs\range_model_reliability
```

## Owner run result — 2026-10-06

Phase185A was run on current 4H and 1D range models.

Result:

```text
reliable_timeframes                : 0/2
range_model_reliability_ready_gate : 0
selected_timeframe                 : 4H
```

Key interpretation:

```text
4H range has coherent forecasts, low median ATR-unit error, monotonic calibration and meaningful ranking signal, but no demonstrated decision utility.
1D range is coherent and low-error but has almost no ranking skill; it behaves like static ATR-climatology.
```

Documented in:

```text
docs/Report/PHASE185A_RANGE_MODEL_RELIABILITY_RESULT.md
```
