# Phase171A — Research Route Redesign Decision Matrix

## Status

```text
IMPLEMENTED — research/diagnostic only
```

No production/paper/live approval:

```text
No Phase134.
No paper shadow.
No live trading.
```

## Why this phase exists

Phase168A rejected the current 1H locked-candidate/filter route. Phase170A captured broker spread reality and showed real Alpari `XAUUSD_i` spread was approximately:

```text
median: 0.39
p90   : 0.40
p99   : 0.41
```

The project now needs an owner-facing route decision matrix instead of more patching on rejected rules.

## Implemented executable

```text
scripts/audit_research_route_redesign_decision_matrix.py
```

## GUI command

```text
Audit research route redesign matrix
```

## What it does

```text
1. Reads recent result logs when available:
   Phase162A, Phase166A, Phase168A, Phase170A.

2. Uses documented route decisions if logs are missing.

3. Scores route options:
   STOP_CURRENT_LOCKED_ROUTES
   NEW_1H_COST_AWARE_TARGET_FAMILY
   HYBRID_REGIME_FIRST_REDESIGN
   4H_1D_COST_FEASIBILITY
   TRAIN_CURRENT_1H_LOCKED_RULE
   PAPER_OR_LIVE

4. Produces an owner-facing decision matrix and recommended plan.
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

## Recommended GUI action

Use the Dashboard command:

```text
Audit research route redesign matrix
```

## Equivalent PowerShell command

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

## Expected decision

The current expected route decision is:

```text
STOP_CURRENT_LOCKED_ROUTES
```

The expected recommended research lane is likely:

```text
Phase172A — Broker-cost-aware 1H target-family design audit
```

with strict restrictions:

```text
no training
no paper
no live
no Phase134
no patching rejected BRK_D1_FAST target
```

## Verification

Sandbox targeted verification:

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

## Owner execution result

The owner ran Phase171A.

Top-level:

```text
route_reset_status      : CURRENT_5M_AND_1H_LOCKED_ROUTES_REJECTED_BY_DOCUMENTED_RESULTS
broker_cost_status      : MISSING_PHASE170_USING_DOCUMENTED_MANUAL_VALUES
broker_spread_median    : 0.39
broker_spread_p90       : 0.40
broker_spread_p99       : 0.41
h1_median_spread_atr    : 0.08347
selected_route_id       : NEW_1H_COST_AWARE_TARGET_FAMILY
selected_required_phase : Phase172A — Broker-cost-aware 1H target-family design audit
```

Decision matrix:

```text
1. NEW_1H_COST_AWARE_TARGET_FAMILY — RECOMMENDED_RESEARCH, score=87
2. STOP_CURRENT_LOCKED_ROUTES — MANDATORY, score=94
3. HYBRID_REGIME_FIRST_REDESIGN — SECONDARY_RESEARCH, score=90
4. 4H_1D_COST_FEASIBILITY — SECONDARY_RESEARCH, score=73
5. TRAIN_CURRENT_1H_LOCKED_RULE — BLOCKED, score=0
6. PAPER_OR_LIVE — BLOCKED, score=0
```

Interpretation:

```text
The mandatory stop/rejection action is already enacted.
The next research lane selected by the matrix is Phase172A.
Hybrid/regime-first remains a strong secondary option, not the selected next step.
```

Decision:

```text
Proceed only to Phase172A diagnostic target-family design.
No training, no paper, no live, no Phase134.
```
