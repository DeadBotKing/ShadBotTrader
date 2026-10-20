# PHASE182A — Entry Event Failure Attribution / Quality Geometry Redesign Decision Report

## Summary

Phase182A has been implemented as a diagnostic-only attribution phase after Phase181B returned:

```text
ready_families = 0/9
entry_event_discovery_ready_gate = 0
```

Phase182A does not train a model. It consumes Phase181B outputs and explains why the entry-event route failed before any redesign decision.

```text
No model training.
No Phase134.
No paper shadow.
No live trading.
No gate relaxation.
```

## Implemented files

```text
scripts/audit_entry_event_failure_attribution.py
tests/unit/ai/test_entry_event_failure_attribution.py
```

GUI integration:

```text
CommandKind.AUDIT_ENTRY_EVENT_FAILURE_ATTRIBUTION
GUI label: Audit entry-event failure attribution
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
run_logs\entry_event_discovery\latest.json
```

The script automatically reads CSV outputs referenced by Phase181B:

```text
latest_replay.csv
latest_events.csv
latest_splits.csv
latest_walkforward.csv
```

## Main attribution reports

Phase182A writes:

```text
latest_family_attribution.csv
latest_side_attribution.csv
latest_timeframe_attribution.csv
latest_quality_geometry.csv
latest_walkforward_attribution.csv
latest_failure_reasons.csv
latest_decision_matrix.csv
latest_next_plan.csv
```

## Main logic

### Family attribution

Attributes each Phase181B family by:

```text
primary failure reason
near_miss_gate
quality/replay/walk-forward status
recommended next action
```

### Side attribution

Separates BUY and SELL behavior:

```text
quality_pass_rate
mean MFE/MAE
replay PF
MAE-first fail rate
timeout rate
```

### Quality geometry attribution

Checks whether current MFE/MAE thresholds are plausible relative to the observed post-trigger path distribution:

```text
pct_mfe_ge_current
pct_mae_le_current
pct_mfe_ge_current_and_mae_le_current
median_trigger_delay_bars
trigger_delay_p75_bars
```

This is diagnostic only; it does not approve a relaxed threshold.

### Walk-forward attribution

Summarizes fold failures:

```text
train_gate_failed_folds
validation_gate_failed_folds
test_gate_failed_folds
worst/best test quality pass rate
```

## Decision matrix

Expected routes:

```text
ENTRY_EVENT_MODEL_TRAINING      : BLOCKED
ENTRY_QUALITY_GEOMETRY_REDESIGN : RECOMMENDED_DIAGNOSTIC or OWNER_REVIEW_REQUIRED
PAPER_OR_LIVE                   : BLOCKED
```

## Recommended owner action

Run from GUI:

```text
AI → Audit entry-event failure attribution
```

Or CLI:

```powershell
python -u scripts\audit_entry_event_failure_attribution.py `
  --phase181b-path run_logs\entry_event_discovery\latest.json `
  --output-dir run_logs\entry_event_failure_attribution
```

Then send:

```text
run_logs\entry_event_failure_attribution\latest.json
```

## Verification

```text
python -m py_compile scripts/audit_entry_event_failure_attribution.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/ai/test_entry_event_failure_attribution.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py
→ passed

python -m pytest tests/unit/ai/test_entry_event_failure_attribution.py tests/unit/ai/test_entry_event_discovery.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
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
BLOCKED — Phase182A is attribution only.
No model training.
No Phase134.
No paper shadow.
No live trading.
```

## Owner run result — 2026-10-03

Phase182A was run on the official Phase181B output.

Result:

```text
near_miss_families              : 3
selected_focus                  : 1D|E3_CONTINUATION
selected_primary_failure_reason : mfe_mae_gate_failed
selected_next_phase             : Phase183A — entry quality-geometry candidate audit
```

Root cause:

```text
Entry events did not fail because of health or cost.
They failed because MFE/MAE, replay and walk-forward transfer are not clean enough.
```

Documented in:

```text
docs/Report/PHASE182A_ENTRY_EVENT_FAILURE_ATTRIBUTION_RESULT.md
```
