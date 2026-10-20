# PHASE172A — Broker-cost-aware 1H Target-family Design Audit Report

## Summary

Phase172A has been implemented as the diagnostic target-family audit selected by Phase171A.

It designs and audits new 1H target families using broker-realistic costs from Phase170A. It does not train a model, does not paper trade and does not approve live trading.

## Implemented files

```text
scripts/audit_broker_cost_aware_1h_target_family.py
tests/unit/ai/test_broker_cost_aware_1h_target_family.py
```

GUI integration:

```text
CommandKind.AUDIT_BROKER_COST_AWARE_1H_TARGET_FAMILY
GUI label: Audit broker-cost-aware 1H target family
```

Updated:

```text
src/ShadBotTrader/presentation/commands/commands.py
src/ShadBotTrader/presentation/commands/handlers.py
tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py
```

## Target families

```text
CA1_BRK_MID
CA2_BRK_WIDE
CA3_BRK_STRICT
CA4_REV_MID
```

All are evaluated with:

```text
primary fixed spread = 0.4
stress fixed spread  = 0.5
```

## Outputs

```text
run_logs\broker_cost_aware_1h_target_family\latest.json
run_logs\broker_cost_aware_1h_target_family\latest.html
run_logs\broker_cost_aware_1h_target_family\latest_candidates.csv
run_logs\broker_cost_aware_1h_target_family\latest_splits.csv
run_logs\broker_cost_aware_1h_target_family\latest_walkforward.csv
run_logs\broker_cost_aware_1h_target_family\latest_events.csv
```

## Recommended command

Dashboard:

```text
Audit broker-cost-aware 1H target family
```

PowerShell:

```powershell
cd C:\Users\DeadBotKing\Desktop\ShadBotTrader

.\.venv\Scripts\python.exe -u scripts\audit_broker_cost_aware_1h_target_family.py `
  --symbol XAUUSD `
  --timeframe 1H `
  --flat-path datasets\processed\XAUUSD\1H\v1.parquet `
  --max-rows 0 `
  --families "CA1_BRK_MID:cost_breakout_mid:breakout:1:24:0.10:0.85:0.15:1:1.0:0:2.0:1.0:24;CA2_BRK_WIDE:cost_breakout_wide:breakout:1:48:0.10:0.85:0.15:1:1.0:0:2.5:1.25:48;CA3_BRK_STRICT:cost_breakout_strict:breakout:1:24:0.05:0.90:0.10:1:1.0:0:2.0:1.0:24;CA4_REV_MID:cost_reversal_mid:reversal:1:24:0.10:0.85:0.15:1:1.0:0:1.5:1.0:24" `
  --spread-mode fixed `
  --spread-value 0.4 `
  --stress-spread-value 0.5 `
  --same-bar-policy stop_first `
  --train-frac 0.70 `
  --val-frac 0.15 `
  --purge-gap 24 `
  --fold-train-bars 18000 `
  --fold-validation-bars 4000 `
  --fold-test-bars 4000 `
  --fold-step-bars 4000 `
  --max-folds 0 `
  --initial-capital 100 `
  --risk-per-trade 0.01 `
  --min-train-events 100 `
  --min-validation-events 20 `
  --min-test-events 20 `
  --min-positive-rate 0.10 `
  --max-positive-rate 0.70 `
  --max-label-psi 0.20 `
  --min-walkforward-pass-ratio 0.50 `
  --min-walkforward-folds 5 `
  --storage-root datasets `
  --output-dir run_logs\broker_cost_aware_1h_target_family `
  --report-title "Phase172A broker-cost-aware 1H target-family design audit"
```

## Verification

```text
python -m py_compile scripts/audit_broker_cost_aware_1h_target_family.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/ai/test_broker_cost_aware_1h_target_family.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py
→ passed

python -m pytest tests/unit/ai/test_broker_cost_aware_1h_target_family.py tests/unit/ai/test_research_route_redesign_decision_matrix.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ passed
```

Full ruff/black unavailable in sandbox:

```text
python -m ruff ...  → No module named ruff
python -m black ... → No module named black
```

## Production status

```text
BLOCKED — Phase172A target-family design audit only
No Phase134.
No paper shadow.
No live trading.
```

## Owner execution result summary

The owner ran Phase172A.

```text
ready_families                        : 3
selected_family_id                    : CA1_BRK_MID
target_family_ready_for_training_gate : 1
```

Key conclusion:

```text
The broker-cost-aware 1H target-family route passed structural target gates.
CA1_BRK_MID is selected as the primary target family.
CA3_BRK_STRICT and CA2_BRK_WIDE are backups.
CA4_REV_MID is rejected.
```

Important caveat:

```text
CA1 train replay economics are negative, so this is not a trading strategy and not a paper/live/model-training approval.
```

Detailed result:

```text
docs/Report/PHASE172A_BROKER_COST_AWARE_1H_TARGET_FAMILY_RESULT.md
```
