# PHASE171A — Research Route Redesign Decision Matrix Report

## Summary

Phase171A has been implemented to convert the recent rejected pivot-lane evidence and broker-cost reality into an owner-facing decision matrix.

It does not train a model. It does not run trading. It does not approve paper/live/production.

## Implemented files

```text
scripts/audit_research_route_redesign_decision_matrix.py
tests/unit/ai/test_research_route_redesign_decision_matrix.py
```

GUI integration:

```text
CommandKind.AUDIT_RESEARCH_ROUTE_REDESIGN_DECISION_MATRIX
GUI label: Audit research route redesign matrix
```

Updated:

```text
src/ShadBotTrader/presentation/commands/commands.py
src/ShadBotTrader/presentation/commands/handlers.py
tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py
```

## Inputs

Default result paths:

```text
run_logs\broker_spread_capture\latest.json
run_logs\pivot_1h_predeclared_filter_confirmation\latest.json
run_logs\pivot_1h_locked_candidate_walk_forward\latest.json
run_logs\pivot_bottom_buy_execution_gap\latest.json
```

If logs are missing, the script can use documented prior decisions:

```text
--assume-documented-route-decisions 1
```

## Route options scored

```text
STOP_CURRENT_LOCKED_ROUTES
NEW_1H_COST_AWARE_TARGET_FAMILY
HYBRID_REGIME_FIRST_REDESIGN
4H_1D_COST_FEASIBILITY
TRAIN_CURRENT_1H_LOCKED_RULE
PAPER_OR_LIVE
```

Blocked routes remain blocked:

```text
TRAIN_CURRENT_1H_LOCKED_RULE
PAPER_OR_LIVE
```

## Outputs

```text
run_logs\research_route_redesign_decision_matrix\latest.json
run_logs\research_route_redesign_decision_matrix\latest.html
run_logs\research_route_redesign_decision_matrix\latest_decision_matrix.csv
run_logs\research_route_redesign_decision_matrix\latest_criteria.csv
run_logs\research_route_redesign_decision_matrix\latest_recommended_plan.csv
run_logs\research_route_redesign_decision_matrix\latest_evidence.csv
```

## Recommended command

Dashboard:

```text
Audit research route redesign matrix
```

PowerShell:

```powershell
cd C:\Users\DeadBotKing\Desktop\ShadBotTrader

.\.venv\Scripts\python.exe -u scripts\audit_research_route_redesign_decision_matrix.py `
  --symbol XAUUSD `
  --phase170-path run_logs\broker_spread_capture\latest.json `
  --phase168-path run_logs\pivot_1h_predeclared_filter_confirmation\latest.json `
  --phase166-path run_logs\pivot_1h_locked_candidate_walk_forward\latest.json `
  --phase162-path run_logs\pivot_bottom_buy_execution_gap\latest.json `
  --assume-documented-route-decisions 1 `
  --manual-broker-spread-median 0.39 `
  --manual-broker-spread-p90 0.40 `
  --manual-broker-spread-p99 0.41 `
  --manual-h1-median-spread-atr 0.08347 `
  --max-production-risk strict `
  --output-dir run_logs\research_route_redesign_decision_matrix `
  --report-title "Phase171A research route redesign decision matrix"
```

## Verification

```text
python -m py_compile scripts/audit_research_route_redesign_decision_matrix.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/ai/test_research_route_redesign_decision_matrix.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py
→ passed

python -m pytest tests/unit/ai/test_research_route_redesign_decision_matrix.py tests/unit/ai/test_broker_spread_capture_pipeline.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ passed
```

Full ruff/black unavailable in sandbox:

```text
python -m ruff ...  → No module named ruff
python -m black ... → No module named black
```

## Production status

```text
BLOCKED — Phase171A route redesign decision only
No Phase134.
No paper shadow.
No live trading.
```

## Owner execution result summary

The owner ran Phase171A.

```text
route_reset_status      : CURRENT_5M_AND_1H_LOCKED_ROUTES_REJECTED_BY_DOCUMENTED_RESULTS
selected_research_route : NEW_1H_COST_AWARE_TARGET_FAMILY
selected_required_phase : Phase172A — Broker-cost-aware 1H target-family design audit
```

The result document is:

```text
docs/Report/PHASE171A_RESEARCH_ROUTE_REDESIGN_DECISION_MATRIX_RESULT.md
```

Final decision:

```text
Build Phase172A only as a diagnostic audit.
No model training.
No paper/live/Phase134.
```
