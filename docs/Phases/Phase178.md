# Phase178A — Post-failure Research Route Reset / Decision Matrix

## Status

```text
COMPLETED — owner run selected higher-timeframe feasibility route
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

Phase178A was run after Phase173A-177A failures.

Top-level result:

```text
current_1h_pivot_target_lane_status : FROZEN_FAILED_DIAGNOSTIC
route_reset_ready_gate              : 1
selected_next_research_route_id     : HIGHER_TIMEFRAME_4H_1D_COST_FEASIBILITY
selected_required_phase             : Phase179A — 4H/1D broker-cost feasibility and target pre-audit
selected_route_score                : 88.0
```

Decision matrix:

```text
FREEZE_CURRENT_1H_PIVOT_TARGET_ROUTE    : MANDATORY, score=100.0
HIGHER_TIMEFRAME_4H_1D_COST_FEASIBILITY : RECOMMENDED_NEXT_RESEARCH, score=88.0
NON_PIVOT_EVENT_TARGET_ROUTE            : SECONDARY_RESEARCH, score=73.0
BROKER_SESSION_COST_DATA_EXTENSION      : SUPPORTING_RESEARCH, score=64.0
PAUSE_FOR_MANUAL_REVIEW                 : VALID_OWNER_OPTION, score=60.0
TRAIN_CURRENT_TARGETS_OR_REGIMES        : BLOCKED, score=0.0
PAPER_OR_LIVE                           : BLOCKED, score=0.0
```

Decision:

```text
Freeze current 1H pivot target-family lane.
Do not train current CA/R targets or regimes.
Proceed only to Phase179A diagnostic feasibility audit if owner approves.
No Phase134, no paper shadow, no live trading.
```

Detailed result report:

```text
docs/Report/PHASE178A_POST_FAILURE_RESEARCH_ROUTE_RESET_RESULT.md
```

## Why this phase exists

The 1H broker-cost-aware pivot target-family lane failed repeatedly:

```text
Phase173A broad target learnability failed.
Phase174A regime-first redesign failed.
Phase175A failure attribution confirmed instability.
Phase176A current target definitions rejected.
Phase177A new target-family redesign candidates failed.
```

Phase178A freezes that route and builds an owner-facing decision matrix for the next research route.

## Implemented executable

```text
scripts/audit_post_failure_research_route_reset.py
```

## GUI command

```text
Audit post-failure research route reset
```

Command kind:

```text
AUDIT_POST_FAILURE_RESEARCH_ROUTE_RESET
```

## Inputs

Phase178A can read these run logs if they exist:

```text
run_logs\broker_spread_capture\latest.json
run_logs\broker_cost_aware_1h_target_learnability\latest.json
run_logs\hybrid_regime_first_target_redesign\latest.json
run_logs\hybrid_regime_walkforward_failure_attribution\latest.json
run_logs\target_definition_walkforward_root_cause_redesign\latest.json
run_logs\walkforward_target_family_redesign_candidates\latest.json
```

If some logs are missing, default owner-documented failed gates can be used with:

```text
--assume-documented-failures 1
```

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

## Expected decision

The intended next diagnostic route is:

```text
HIGHER_TIMEFRAME_4H_1D_COST_FEASIBILITY
```

Required next phase if selected:

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

## Recommended GUI action

Use:

```text
Audit post-failure research route reset
```

Then send:

```text
run_logs\post_failure_research_route_reset\latest.json
```

## Equivalent PowerShell command

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

Sandbox targeted verification:

```text
python -m py_compile scripts/audit_post_failure_research_route_reset.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/ai/test_post_failure_research_route_reset.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py
→ passed

python -m pytest tests/unit/ai/test_post_failure_research_route_reset.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ passed
```
