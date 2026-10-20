# PHASE178A — Post-failure Research Route Reset / Decision Matrix Report

## Summary

Phase178A has been implemented to freeze the failed 1H broker-cost-aware pivot target-family lane and select the next diagnostic research route.

It does not train a model, build a target tensor, or approve paper/live trading.

## Implemented files

```text
scripts/audit_post_failure_research_route_reset.py
tests/unit/ai/test_post_failure_research_route_reset.py
```

GUI integration:

```text
CommandKind.AUDIT_POST_FAILURE_RESEARCH_ROUTE_RESET
GUI label: Audit post-failure research route reset
```

Updated:

```text
src/ShadBotTrader/presentation/commands/commands.py
src/ShadBotTrader/presentation/commands/handlers.py
tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py
```

## Why this phase was built

The current 1H broker-cost-aware pivot target-family lane failed:

```text
Phase173A broad target learnability failed.
Phase174A regime-first redesign failed.
Phase175A failure attribution confirmed instability.
Phase176A current target definitions rejected.
Phase177A new target-family redesign candidates failed.
```

Therefore another quick target tweak or training phase is not justified.

## Routes compared

```text
FREEZE_CURRENT_1H_PIVOT_TARGET_ROUTE
HIGHER_TIMEFRAME_4H_1D_COST_FEASIBILITY
NON_PIVOT_EVENT_TARGET_ROUTE
BROKER_SESSION_COST_DATA_EXTENSION
PAUSE_FOR_MANUAL_REVIEW
TRAIN_CURRENT_TARGETS_OR_REGIMES
PAPER_OR_LIVE
```

## Expected recommendation

```text
FREEZE_CURRENT_1H_PIVOT_TARGET_ROUTE — mandatory stop
HIGHER_TIMEFRAME_4H_1D_COST_FEASIBILITY — recommended next research route
```

Potential next phase:

```text
Phase179A — 4H/1D broker-cost feasibility and target pre-audit
```

## Outputs

```text
run_logs\post_failure_research_route_reset\latest.json
run_logs\post_failure_research_route_reset\latest.html
run_logs\post_failure_research_route_reset\latest_phase_evidence.csv
run_logs\post_failure_research_route_reset\latest_route_decisions.csv
run_logs\post_failure_research_route_reset\latest_recommended_plan.csv
```

## Recommended command

Dashboard:

```text
Audit post-failure research route reset
```

PowerShell:

```powershell
cd C:\Users\DeadBotKing\Desktop\ShadBotTrader

.\.venv\Scripts\python.exe -u scripts\audit_post_failure_research_route_reset.py `
  --symbol XAUUSD `
  --phase170-path run_logs\broker_spread_capture\latest.json `
  --phase173-path run_logs\broker_cost_aware_1h_target_learnability\latest.json `
  --phase174-path run_logs\hybrid_regime_first_target_redesign\latest.json `
  --phase175-path run_logs\hybrid_regime_walkforward_failure_attribution\latest.json `
  --phase176-path run_logs\target_definition_walkforward_root_cause_redesign\latest.json `
  --phase177-path run_logs\walkforward_target_family_redesign_candidates\latest.json `
  --assume-documented-failures 1 `
  --manual-broker-spread-median 0.39 `
  --manual-broker-spread-p90 0.40 `
  --manual-broker-spread-p99 0.41 `
  --manual-h1-median-spread-atr 0.08347 `
  --output-dir run_logs\post_failure_research_route_reset `
  --report-title "Phase178A post-failure research route reset decision matrix"
```

## Verification

```text
python -m py_compile scripts/audit_post_failure_research_route_reset.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/ai/test_post_failure_research_route_reset.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py
→ passed

python -m pytest tests/unit/ai/test_post_failure_research_route_reset.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ passed
```

## Production status

```text
BLOCKED — Phase178A route reset decision matrix only
No Phase134.
No paper shadow.
No live trading.
No model training.
```

## Owner run result

The owner ran Phase178A. The current 1H pivot target-family lane was frozen and the next diagnostic route was selected:

```text
current_1h_pivot_target_lane_status : FROZEN_FAILED_DIAGNOSTIC
route_reset_ready_gate              : 1
selected_next_research_route_id     : HIGHER_TIMEFRAME_4H_1D_COST_FEASIBILITY
selected_required_phase             : Phase179A — 4H/1D broker-cost feasibility and target pre-audit
selected_route_score                : 88.0
```

Detailed result report:

```text
docs/Report/PHASE178A_POST_FAILURE_RESEARCH_ROUTE_RESET_RESULT.md
```

Decision:

```text
Freeze current 1H pivot target-family lane.
Do not train current targets or regimes.
No Phase134.
No paper shadow.
No live trading.
```
