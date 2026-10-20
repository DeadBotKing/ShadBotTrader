# PHASE180A — Higher-timeframe Target Failure Attribution / Candidate Redesign Decision Report

## Summary

Phase180A has been implemented after Phase179A found that 4H/1D broker cost is feasible but target readiness still failed.

This phase consumes Phase179A output and attributes failure reasons by timeframe, target candidate, and walk-forward fold. It does not train a model and does not approve paper/live trading.

## Implemented files

```text
scripts/audit_higher_timeframe_target_failure_attribution.py
tests/unit/ai/test_higher_timeframe_target_failure_attribution.py
```

GUI integration:

```text
CommandKind.AUDIT_HIGHER_TIMEFRAME_TARGET_FAILURES
GUI label: Audit higher-timeframe target failures
```

Updated:

```text
src/ShadBotTrader/presentation/commands/commands.py
src/ShadBotTrader/presentation/commands/handlers.py
tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py
```

## Input

```text
run_logs\higher_timeframe_cost_feasibility\latest.json
```

## Outputs

```text
run_logs\higher_timeframe_target_failure_attribution\latest.json
run_logs\higher_timeframe_target_failure_attribution\latest.html
run_logs\higher_timeframe_target_failure_attribution\latest_candidate_failures.csv
run_logs\higher_timeframe_target_failure_attribution\latest_timeframe_summary.csv
run_logs\higher_timeframe_target_failure_attribution\latest_fold_failures.csv
run_logs\higher_timeframe_target_failure_attribution\latest_failure_reasons.csv
run_logs\higher_timeframe_target_failure_attribution\latest_decision_matrix.csv
run_logs\higher_timeframe_target_failure_attribution\latest_next_plan.csv
```

## Recommended command

Dashboard:

```text
Audit higher-timeframe target failures
```

PowerShell:

```powershell
cd C:\Users\DeadBotKing\Desktop\ShadBotTrader

.\.venv\Scripts\python.exe -u scripts\audit_higher_timeframe_target_failure_attribution.py `
  --phase179-path run_logs\higher_timeframe_cost_feasibility\latest.json `
  --output-dir run_logs\higher_timeframe_target_failure_attribution `
  --report-title "Phase180A higher-timeframe target failure attribution"
```

## Verification

```text
python -m py_compile scripts/audit_higher_timeframe_target_failure_attribution.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/ai/test_higher_timeframe_target_failure_attribution.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py
→ passed

python -m pytest tests/unit/ai/test_higher_timeframe_target_failure_attribution.py tests/unit/ai/test_higher_timeframe_cost_feasibility.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ passed
```

## Production status

```text
BLOCKED — Phase180A higher-timeframe failure attribution only
No Phase134.
No paper shadow.
No live trading.
No model training.
```

## Owner run result

The owner ran Phase180A on the Phase179A output. The audit confirmed cost feasibility but rejected model training because target readiness failed:

```text
cost_feasibility_confirmed_gate        : 1
target_readiness_confirmed_failed_gate : 1
selected_next_route_id                 : D1_TARGET_FAILURE_ATTRIBUTION_AND_REDESIGN_DECISION
selected_next_phase                    : Phase181A — daily target failure attribution and redesign decision
selected_focus_timeframe               : 1D
selected_focus_family_id               : D1_R1_BK_MID_B20_10_H5
no_training_gate                       : 1
no_paper_live_gate                     : 1
```

Detailed result report:

```text
docs/Report/PHASE180A_HIGHER_TIMEFRAME_TARGET_FAILURE_ATTRIBUTION_RESULT.md
```

Decision:

```text
Do not train.
No Phase134.
No paper shadow.
No live trading.
```
