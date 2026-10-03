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
