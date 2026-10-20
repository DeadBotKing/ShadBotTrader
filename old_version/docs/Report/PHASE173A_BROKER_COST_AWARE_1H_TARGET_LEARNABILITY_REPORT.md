# PHASE173A — Broker-cost-aware 1H Target Learnability / Dataset Build Audit Report

## Summary

Phase173A has been implemented to determine whether the broker-cost-aware 1H target families from Phase172A are learnable before any model-training phase.

It builds event-level datasets and runs a lightweight dependency-free centroid baseline. It does not train a production model and does not approve paper/live trading.

## Implemented files

```text
scripts/audit_broker_cost_aware_1h_target_learnability.py
tests/unit/ai/test_broker_cost_aware_1h_target_learnability.py
```

GUI integration:

```text
CommandKind.AUDIT_BROKER_COST_AWARE_1H_TARGET_LEARNABILITY
GUI label: Audit broker-cost-aware 1H target learnability
```

Updated:

```text
src/ShadBotTrader/presentation/commands/commands.py
src/ShadBotTrader/presentation/commands/handlers.py
tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py
```

## Target families

Default audited families:

```text
CA1_BRK_MID
CA3_BRK_STRICT
CA2_BRK_WIDE
```

CA4 reversal is excluded by default because it failed Phase172A stress gate.

## Outputs

```text
run_logs\broker_cost_aware_1h_target_learnability\latest.json
run_logs\broker_cost_aware_1h_target_learnability\latest.html
run_logs\broker_cost_aware_1h_target_learnability\latest_families.csv
run_logs\broker_cost_aware_1h_target_learnability\latest_splits.csv
run_logs\broker_cost_aware_1h_target_learnability\latest_walkforward.csv
run_logs\broker_cost_aware_1h_target_learnability\latest_dataset.csv
```

## Recommended command

Dashboard:

```text
Audit broker-cost-aware 1H target learnability
```

PowerShell:

```powershell
cd C:\Users\DeadBotKing\Desktop\ShadBotTrader

.\.venv\Scripts\python.exe -u scripts\audit_broker_cost_aware_1h_target_learnability.py `
  --symbol XAUUSD `
  --timeframe 1H `
  --flat-path datasets\processed\XAUUSD\1H\v1.parquet `
  --max-rows 0 `
  --families "CA1_BRK_MID:cost_breakout_mid:breakout:1:24:0.10:0.85:0.15:1:1.0:0:2.0:1.0:24;CA3_BRK_STRICT:cost_breakout_strict:breakout:1:24:0.05:0.90:0.10:1:1.0:0:2.0:1.0:24;CA2_BRK_WIDE:cost_breakout_wide:breakout:1:48:0.10:0.85:0.15:1:1.0:0:2.5:1.25:48" `
  --spread-mode fixed `
  --spread-value 0.4 `
  --same-bar-policy stop_first `
  --train-frac 0.70 `
  --val-frac 0.15 `
  --purge-gap 24 `
  --fold-train-bars 18000 `
  --fold-validation-bars 4000 `
  --fold-test-bars 4000 `
  --fold-step-bars 4000 `
  --max-folds 0 `
  --min-train-events 100 `
  --min-validation-events 20 `
  --min-test-events 20 `
  --min-positive-rate 0.10 `
  --max-positive-rate 0.70 `
  --max-label-psi 0.20 `
  --min-ap-lift 0.03 `
  --min-balanced-accuracy 0.53 `
  --min-walkforward-pass-ratio 0.50 `
  --min-walkforward-folds 5 `
  --max-dataset-rows 20000 `
  --storage-root datasets `
  --output-dir run_logs\broker_cost_aware_1h_target_learnability `
  --report-title "Phase173A broker-cost-aware 1H target learnability audit"
```

## Verification

```text
python -m py_compile scripts/audit_broker_cost_aware_1h_target_learnability.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/ai/test_broker_cost_aware_1h_target_learnability.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py
→ passed

python -m pytest tests/unit/ai/test_broker_cost_aware_1h_target_learnability.py tests/unit/ai/test_broker_cost_aware_1h_target_family.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ passed
```

Full ruff/black unavailable in sandbox:

```text
python -m ruff ...  → No module named ruff
python -m black ... → No module named black
```

## Production status

```text
BLOCKED — Phase173A target learnability audit only
No Phase134.
No paper shadow.
No live trading.
```

## Owner run result

The owner ran Phase173A on the full 1H XAUUSD dataset. The learnability gates failed:

```text
learnable_families             : 0
selected_family_id             : CA3_BRK_STRICT
selected_family_ready_gate     : 0
target_learnability_ready_gate : 0
```

Detailed result report:

```text
docs/Report/PHASE173A_BROKER_COST_AWARE_1H_TARGET_LEARNABILITY_RESULT.md
```

Decision:

```text
Do not train CA1/CA3/CA2.
No Phase134.
No paper shadow.
No live trading.
```
