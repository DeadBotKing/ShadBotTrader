# Phase176A — Target-definition Walk-forward Root-cause Redesign Audit

## Status

```text
COMPLETED — owner run rejected current target definitions
research/diagnostic only
```

No production/paper/live/model-training approval:

```text
No Phase134.
No paper shadow.
No live trading.
No model training.
No gate relaxation.
```


## Owner execution result — 2026-10-01

Phase176A was run on the Phase174A and Phase175A outputs.

Top-level result:

```text
root_cause_confirmed_gate                : 1
target_definition_redesign_required_gate : 1
direct_training_blocked_gate             : 1
paper_live_blocked_gate                  : 1
route_decision                           : CURRENT_TARGET_DEFINITIONS_REJECTED_REDESIGN_DIAGNOSTIC_ONLY
recommended_next_phase                   : Phase177A — walk-forward target-family redesign candidate audit
```

Target definitions audited:

```text
CA1_BRK_MID    : ready=0, static_pass=0, walkforward_pass=0, root_failure=static_learnability_gate_failed
CA3_BRK_STRICT : ready=0, static_pass=0, walkforward_pass=0, root_failure=static_learnability_gate_failed
CA2_BRK_WIDE   : ready=0, static_pass=0, walkforward_pass=0, root_failure=economic_gate_failed
```

All target-definition axes were rejected with:

```text
verdict = REJECTED_WALKFORWARD_ZERO
```

Supported redesign hypotheses:

```text
H1_TARGET_DEFINITION_MISMATCH
H2_TRAIN_EXPECTANCY_INSTABILITY
H3_CLASSIFIER_SIGNAL_NOT_STABLE
H4_RAW_ECONOMICS_DO_NOT_TRANSFER_BY_FOLD
H5_DENSITY_IS_SECONDARY_NOT_PRIMARY
H6_SESSION_FILTERS_NOT_ENOUGH
```

Decision:

```text
Freeze CA1_BRK_MID, CA3_BRK_STRICT, and CA2_BRK_WIDE as failed diagnostics.
Do not train.
Do not relax gates.
No Phase134, no paper shadow, no live trading.
```

Detailed result report:

```text
docs/Report/PHASE176A_TARGET_DEFINITION_WALKFORWARD_ROOT_CAUSE_REDESIGN_RESULT.md
```

## Why this phase exists

Phase175A confirmed that Phase174A failed for broad target/regime instability:

```text
candidate_rows                      : 66
walkforward_rows                    : 396
walkforward_pass_rows               : 0
candidates_with_static_learnability : 0
candidates_with_walkforward_gate    : 0
candidates_with_ready_gate          : 0
```

The selected recommendation was diagnostic-only:

```text
TARGET_DEFINITION_FAILURE_REDESIGN_AUDIT
```

Phase176A is therefore not a model-training phase. It attributes the failed route by target-definition axes and redesign hypotheses before any future target-family candidate build can be considered.

## Implemented executable

```text
scripts/audit_target_definition_walkforward_root_cause_redesign.py
```

## GUI command

```text
Audit target-definition walk-forward root cause
```

Command kind:

```text
AUDIT_TARGET_DEFINITION_WALKFORWARD_ROOT_CAUSE
```

## Inputs

Phase176A consumes already-produced diagnostic results:

```text
run_logs\hybrid_regime_first_target_redesign\latest.json
run_logs\hybrid_regime_walkforward_failure_attribution\latest.json
```

It does not recompute labels from market data and does not train a model.

## What it audits

Phase176A groups Phase174A/175A failures by target-definition axes:

```text
family
geometry_profile
hold_bars
TP/SL geometry
regime_axis
regime_rule
```

Target-family metadata audited:

```text
CA1_BRK_MID    : mid_zone_rw24, TP/SL=2.0/1.0, hold=24
CA3_BRK_STRICT : strict_zone_rw24, TP/SL=2.0/1.0, hold=24
CA2_BRK_WIDE   : wide_zone_rw48, TP/SL=2.5/1.25, hold=48
```

Regime axes:

```text
baseline
side
zone
cost
atr
range_width
session
momentum
side_momentum
side_cost
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

## Decision policy

Phase176A can confirm whether a future target-family redesign audit is justified, but it cannot approve:

```text
training
paper shadow
live trading
Phase134
gate relaxation
```

Expected top-level gates:

```text
root_cause_confirmed_gate = 1
target_definition_redesign_required_gate = 1
direct_training_blocked_gate = 1
paper_live_blocked_gate = 1
```

## Recommended GUI action

Use:

```text
Audit target-definition walk-forward root cause
```

Then send:

```text
run_logs\target_definition_walkforward_root_cause_redesign\latest.json
```

## Equivalent PowerShell command

```powershell
cd C:\Users\DeadBotKing\Desktop\ShadBotTrader

.\.venv\Scripts\python.exe -u scripts\audit_target_definition_walkforward_root_cause_redesign.py `
  --phase174-path run_logs\hybrid_regime_first_target_redesign\latest.json `
  --phase175-path run_logs\hybrid_regime_walkforward_failure_attribution\latest.json `
  --output-dir run_logs\target_definition_walkforward_root_cause_redesign `
  --report-title "Phase176A target-definition walk-forward root-cause redesign audit"
```

## Verification

Sandbox targeted verification:

```text
python -m py_compile scripts/audit_target_definition_walkforward_root_cause_redesign.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/ai/test_target_definition_walkforward_root_cause_redesign.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py
→ passed

python -m pytest tests/unit/ai/test_target_definition_walkforward_root_cause_redesign.py tests/unit/ai/test_hybrid_regime_walkforward_failure_attribution.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ passed
```
