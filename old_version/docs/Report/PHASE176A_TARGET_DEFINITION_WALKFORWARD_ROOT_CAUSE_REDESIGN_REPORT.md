# PHASE176A — Target-definition Walk-forward Root-cause Redesign Audit Report

## Summary

Phase176A has been implemented after Phase175A confirmed that the Phase174A hybrid/regime route failed all walk-forward gates.

It is a diagnostic-only root-cause audit. It consumes Phase174A and Phase175A JSON outputs, attributes failures by target-definition axes, and builds redesign hypotheses. It does not train a model and does not approve paper/live trading.

## Implemented files

```text
scripts/audit_target_definition_walkforward_root_cause_redesign.py
tests/unit/ai/test_target_definition_walkforward_root_cause_redesign.py
```

GUI integration:

```text
CommandKind.AUDIT_TARGET_DEFINITION_WALKFORWARD_ROOT_CAUSE
GUI label: Audit target-definition walk-forward root cause
```

Updated:

```text
src/ShadBotTrader/presentation/commands/commands.py
src/ShadBotTrader/presentation/commands/handlers.py
tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py
```

## Inputs

```text
run_logs\hybrid_regime_first_target_redesign\latest.json
run_logs\hybrid_regime_walkforward_failure_attribution\latest.json
```

## Outputs

```text
run_logs\target_definition_walkforward_root_cause_redesign\latest.json
run_logs\target_definition_walkforward_root_cause_redesign\latest.html
run_logs\target_definition_walkforward_root_cause_redesign\latest_target_definitions.csv
run_logs\target_definition_walkforward_root_cause_redesign\latest_axis_attribution.csv
run_logs\target_definition_walkforward_root_cause_redesign\latest_redesign_hypotheses.csv
run_logs\target_definition_walkforward_root_cause_redesign\latest_decision_matrix.csv
```

## Root-cause axes

Phase176A audits:

```text
family
geometry_profile
hold_bars
TP/SL geometry
regime_axis
regime_rule
```

Target definitions included:

```text
CA1_BRK_MID    : mid_zone_rw24, TP/SL=2.0/1.0, hold=24
CA3_BRK_STRICT : strict_zone_rw24, TP/SL=2.0/1.0, hold=24
CA2_BRK_WIDE   : wide_zone_rw48, TP/SL=2.5/1.25, hold=48
```

## Redesign hypotheses

The script emits explicit hypotheses such as:

```text
H1_TARGET_DEFINITION_MISMATCH
H2_TRAIN_EXPECTANCY_INSTABILITY
H3_CLASSIFIER_SIGNAL_NOT_STABLE
H4_RAW_ECONOMICS_DO_NOT_TRANSFER_BY_FOLD
H5_DENSITY_IS_SECONDARY_NOT_PRIMARY
H6_SESSION_FILTERS_NOT_ENOUGH
```

These are recommendations for diagnostic redesign only, not model approval.

## Recommended command

Dashboard:

```text
Audit target-definition walk-forward root cause
```

PowerShell:

```powershell
cd C:\Users\DeadBotKing\Desktop\ShadBotTrader

.\.venv\Scripts\python.exe -u scripts\audit_target_definition_walkforward_root_cause_redesign.py `
  --phase174-path run_logs\hybrid_regime_first_target_redesign\latest.json `
  --phase175-path run_logs\hybrid_regime_walkforward_failure_attribution\latest.json `
  --output-dir run_logs\target_definition_walkforward_root_cause_redesign `
  --report-title "Phase176A target-definition walk-forward root-cause redesign audit"
```

## Verification

```text
python -m py_compile scripts/audit_target_definition_walkforward_root_cause_redesign.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/ai/test_target_definition_walkforward_root_cause_redesign.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py
→ passed

python -m pytest tests/unit/ai/test_target_definition_walkforward_root_cause_redesign.py tests/unit/ai/test_hybrid_regime_walkforward_failure_attribution.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ passed
```

## Production status

```text
BLOCKED — Phase176A target-definition root-cause audit only
No Phase134.
No paper shadow.
No live trading.
No model training.
```

## Owner run result

The owner ran Phase176A on the Phase174A and Phase175A outputs. The audit rejected the current target definitions:

```text
root_cause_confirmed_gate                : 1
target_definition_redesign_required_gate : 1
direct_training_blocked_gate             : 1
paper_live_blocked_gate                  : 1
route_decision                           : CURRENT_TARGET_DEFINITIONS_REJECTED_REDESIGN_DIAGNOSTIC_ONLY
recommended_next_phase                   : Phase177A — walk-forward target-family redesign candidate audit
```

Detailed result report:

```text
docs/Report/PHASE176A_TARGET_DEFINITION_WALKFORWARD_ROOT_CAUSE_REDESIGN_RESULT.md
```

Decision:

```text
Freeze CA1_BRK_MID, CA3_BRK_STRICT, and CA2_BRK_WIDE as failed diagnostics.
Do not train.
Do not relax gates.
No Phase134.
No paper shadow.
No live trading.
```
