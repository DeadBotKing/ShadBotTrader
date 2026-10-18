# PHASE184A — Entry Route Test-only Failure Attribution / Stop-or-Narrow Decision Report

## Summary

Phase184A implements the owner-approved closure / decision audit after Phase183A failed to produce any training-ready quality-geometry candidate.

It consumes Phase183A outputs and determines whether the current entry-quality geometry route should be frozen or whether exactly one narrow diagnostic exception is justified.

```text
No model training.
No Phase134.
No paper shadow.
No live trading.
No gate relaxation.
No broad parameter search.
```

## Implemented files

```text
scripts/audit_entry_route_test_only_failure_attribution.py
tests/unit/ai/test_entry_route_test_only_failure_attribution.py
```

GUI integration:

```text
CommandKind.AUDIT_ENTRY_ROUTE_TEST_ONLY_FAILURE
GUI label: Audit entry route test-only failure
```

Updated files:

```text
src/ShadBotTrader/presentation/commands/commands.py
src/ShadBotTrader/presentation/commands/handlers.py
tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py
```

## Input

Default input:

```text
run_logs\entry_quality_geometry_candidates\latest.json
```

Phase184A optionally reads referenced CSV files:

```text
latest_candidates.csv
latest_splits.csv
latest_walkforward.csv
latest_replay.csv
```

## Main analysis

Phase184A creates:

```text
candidate closure attribution
split transfer attribution
walk-forward closure attribution
monthly replay attribution if replay CSV is available
failure reason summary
decision matrix
next plan
```

## Main output decision

Expected decision routes:

```text
ENTRY_GEOMETRY_MODEL_PREFLIGHT  : BLOCKED
FREEZE_ENTRY_EVENT_GEOMETRY_ROUTE: RECOMMENDED if no narrow candidate exists
ALLOW_ONE_NARROW_PHASE185A       : BLOCKED unless evidence is strong enough
PAPER_OR_LIVE                    : BLOCKED
```

## Recommended owner action

Run from GUI:

```text
AI → Audit entry route test-only failure
```

Or CLI:

```powershell
python -u scripts\audit_entry_route_test_only_failure_attribution.py `
  --phase183a-path run_logs\entry_quality_geometry_candidates\latest.json `
  --output-dir run_logs\entry_route_test_only_failure_attribution
```

Then send:

```text
run_logs\entry_route_test_only_failure_attribution\latest.json
```

## Verification

```text
python -m py_compile scripts/audit_entry_route_test_only_failure_attribution.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/ai/test_entry_route_test_only_failure_attribution.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py
→ passed

python -m pytest tests/unit/ai/test_entry_route_test_only_failure_attribution.py tests/unit/ai/test_entry_quality_geometry_candidates.py tests/unit/ai/test_entry_event_failure_attribution.py tests/unit/ai/test_entry_event_discovery.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ passed
```

Unavailable in sandbox:

```text
python -m ruff check .        → No module named ruff
python -m black --check .     → No module named black
python -m mypy src            → No module named mypy
```

## Production status

```text
BLOCKED — Phase184A is closure attribution only.
No model training.
No Phase134.
No paper shadow.
No live trading.
```

## Owner run result — 2026-10-05

Phase184A was run on the official Phase183A output.

Result:

```text
test_only_candidates       : 8
narrow_candidate_count     : 0
selected_candidate_id      : Q7_H4_E2_B00_M10_A10
selected_decision          : FREEZE_ENTRY_EVENT_GEOMETRY_ROUTE
```

Conclusion:

```text
Phase183A positives were test-only and did not transfer through validation or walk-forward.
The current E1/E2/E3 entry-quality geometry route should be frozen as failed diagnostic.
```

Documented in:

```text
docs/Report/PHASE184A_ENTRY_ROUTE_TEST_ONLY_FAILURE_ATTRIBUTION_RESULT.md
```
