# Phase184A — Entry Route Test-only Failure Attribution / Stop-or-Narrow Decision

## Status

```text
COMPLETED — owner run recorded
Result: FREEZE_ENTRY_EVENT_GEOMETRY_ROUTE
Production — BLOCKED
```

Phase184A is a closure / decision phase after Phase183A produced final-test pockets that did not transfer through validation or walk-forward.

```text
No model training.
No Phase134.
No paper shadow.
No live trading.
No gate relaxation.
No broad parameter search.
```

## Purpose

Phase183A showed:

```text
ready_candidates = 0/12
best final-test candidate = Q7_H4_E2_B00_M10_A10
final test PF = 1.5527
validation PF = 0.8996
walk-forward pass = 0/4
```

Phase184A does not create new candidates. It answers:

```text
Are Phase183A positives test-only artifacts?
Should the current entry-geometry route be frozen?
Is there enough evidence for exactly one narrow diagnostic exception?
```

## Implemented command

GUI command:

```text
Audit entry route test-only failure
```

Command kind:

```text
CommandKind.AUDIT_ENTRY_ROUTE_TEST_ONLY_FAILURE
```

Script:

```text
scripts/audit_entry_route_test_only_failure_attribution.py
```

## Input

Default input:

```text
run_logs/entry_quality_geometry_candidates/latest.json
```

Optional CSVs are read from the Phase183A JSON:

```text
latest_candidates.csv
latest_splits.csv
latest_walkforward.csv
latest_replay.csv
```

## Outputs

```text
run_logs/entry_route_test_only_failure_attribution/latest.json
run_logs/entry_route_test_only_failure_attribution/latest.html
run_logs/entry_route_test_only_failure_attribution/latest_candidate_closure.csv
run_logs/entry_route_test_only_failure_attribution/latest_split_transfer.csv
run_logs/entry_route_test_only_failure_attribution/latest_walkforward_closure.csv
run_logs/entry_route_test_only_failure_attribution/latest_replay_months.csv
run_logs/entry_route_test_only_failure_attribution/latest_failure_reasons.csv
run_logs/entry_route_test_only_failure_attribution/latest_decision_matrix.csv
run_logs/entry_route_test_only_failure_attribution/latest_next_plan.csv
```

## Main decision logic

Phase184A can return:

```text
FREEZE_ENTRY_EVENT_GEOMETRY_ROUTE
```

or, only if evidence is strong enough:

```text
ALLOW_ONE_NARROW_PHASE185A
```

Default expectation after Phase183A:

```text
FREEZE_ENTRY_EVENT_GEOMETRY_ROUTE
```

because Phase183A produced test-only pockets and no walk-forward transfer.

## Recommended GUI run

```text
AI → Audit entry route test-only failure
```

Default fields:

```text
Phase183A result path : run_logs/entry_quality_geometry_candidates/latest.json
Output dir            : run_logs/entry_route_test_only_failure_attribution
```

## CLI equivalent

```powershell
python -u scripts\audit_entry_route_test_only_failure_attribution.py `
  --phase183a-path run_logs\entry_quality_geometry_candidates\latest.json `
  --output-dir run_logs\entry_route_test_only_failure_attribution
```

## Verification in sandbox

```text
python -m py_compile scripts/audit_entry_route_test_only_failure_attribution.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/ai/test_entry_route_test_only_failure_attribution.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py
→ passed

python -m pytest tests/unit/ai/test_entry_route_test_only_failure_attribution.py tests/unit/ai/test_entry_quality_geometry_candidates.py tests/unit/ai/test_entry_event_failure_attribution.py tests/unit/ai/test_entry_event_discovery.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ passed
```

## Production status

```text
BLOCKED — closure attribution only.
No model training.
No Phase134.
No paper shadow.
No live trading.
```

## Owner run result — 2026-10-05

Owner ran Phase184A on Phase183A output.

Top-level result:

```text
evaluated_candidates       : 12
ready_candidates           : 0
test_only_candidates       : 8
narrow_candidate_count     : 0
selected_candidate_id      : Q7_H4_E2_B00_M10_A10
selected_closure_verdict   : TEST_ONLY_NOT_TRANSFERRED
selected_decision_route_id : FREEZE_ENTRY_EVENT_GEOMETRY_ROUTE
selected_decision          : FREEZE_ENTRY_EVENT_GEOMETRY_ROUTE
no_training_gate           : 1
no_paper_live_gate         : 1
```

Dominant failure:

```text
walkforward_transfer_failed      : 12/12
walkforward_transfer_gate_failed : 12/12
static_transfer_gate_failed      : 12/12
test_only_not_transferred        : 8/12
```

Decision:

```text
FREEZE_ENTRY_EVENT_GEOMETRY_ROUTE
```

No model training, no Phase134, no paper/live.

Result report:

```text
docs/Report/PHASE184A_ENTRY_ROUTE_TEST_ONLY_FAILURE_ATTRIBUTION_RESULT.md
```
