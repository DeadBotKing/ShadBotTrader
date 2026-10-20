# Phase180A — Higher-timeframe Target Failure Attribution / Candidate Redesign Decision

## Status

```text
COMPLETED — owner run confirmed cost feasible but target not ready
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

Phase180A was run on the Phase179A output.

Top-level result:

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

Main diagnosis:

```text
Cost is feasible on 4H/1D, especially 1D.
Target readiness still failed.
D1_R1_BK_MID_B20_10_H5 is a near-miss, not a training-ready target.
```

Decision:

```text
Do not train 4H/1D models.
Do not open Phase134.
No paper shadow.
No live trading.
```

Detailed result report:

```text
docs/Report/PHASE180A_HIGHER_TIMEFRAME_TARGET_FAILURE_ATTRIBUTION_RESULT.md
```

## Why this phase exists

Phase179A showed a mixed result:

```text
4H/1D broker cost feasibility improved.
No 4H/1D target family passed readiness gates.
Best failed candidate: D1_R1_BK_MID_B20_10_H5 with walk-forward pass 1/5.
```

Phase180A consumes the Phase179A output and attributes why higher-timeframe targets are still not ready.

## Implemented executable

```text
scripts/audit_higher_timeframe_target_failure_attribution.py
```

## GUI command

```text
Audit higher-timeframe target failures
```

Command kind:

```text
AUDIT_HIGHER_TIMEFRAME_TARGET_FAILURES
```

## Inputs

```text
run_logs\higher_timeframe_cost_feasibility\latest.json
```

## What it audits

Phase180A attributes the Phase179A result by:

```text
timeframe: 4H vs 1D
candidate family
candidate failure reason
walk-forward fold failure reason
near-miss target candidates
cost-feasibility vs target-readiness separation
```

It canonicalizes timeframe labels:

```text
"1" / "D1" / "1D" -> "1D"
"4" / "H4" / "4H" -> "4H"
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

## Expected decision logic

Phase180A should preserve:

```text
no_training_gate = 1
no_paper_live_gate = 1
```

If D1 remains a near-miss, the likely next diagnostic is:

```text
Phase181A — daily target failure attribution and redesign decision
```

But this is still diagnostic-only, not model training.

## Recommended GUI action

Use:

```text
Audit higher-timeframe target failures
```

Then send:

```text
run_logs\higher_timeframe_target_failure_attribution\latest.json
```

## Equivalent PowerShell command

```powershell
cd C:\Users\DeadBotKing\Desktop\ShadBotTrader

.\.venv\Scripts\python.exe -u scripts\audit_higher_timeframe_target_failure_attribution.py `
  --phase179-path run_logs\higher_timeframe_cost_feasibility\latest.json `
  --output-dir run_logs\higher_timeframe_target_failure_attribution `
  --report-title "Phase180A higher-timeframe target failure attribution"
```

## Verification

Sandbox targeted verification:

```text
python -m py_compile scripts/audit_higher_timeframe_target_failure_attribution.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/ai/test_higher_timeframe_target_failure_attribution.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py
→ passed

python -m pytest tests/unit/ai/test_higher_timeframe_target_failure_attribution.py tests/unit/ai/test_higher_timeframe_cost_feasibility.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ passed
```
