# PHASE183A — Entry Quality-Geometry Candidate Audit Report

## Summary

Phase183A implements a diagnostic-only audit of redesigned entry quality geometry after Phase182A attributed entry-event failures to MFE/MAE quality, replay economics and walk-forward transfer.

```text
No model training.
No Phase134.
No paper shadow.
No live trading.
No gate relaxation.
```

## Implemented files

```text
scripts/audit_entry_quality_geometry_candidates.py
tests/unit/ai/test_entry_quality_geometry_candidates.py
```

GUI integration:

```text
CommandKind.AUDIT_ENTRY_QUALITY_GEOMETRY_CANDIDATES
GUI label: Audit entry quality-geometry candidates
```

Updated files:

```text
src/ShadBotTrader/presentation/commands/commands.py
src/ShadBotTrader/presentation/commands/handlers.py
tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py
```

## Input

Default inputs:

```text
run_logs\entry_event_failure_attribution\latest.json
run_logs\entry_event_discovery\latest.json
```

## Candidate concept

Phase183A tests target-geometry candidates derived from Phase182A near-misses:

```text
1D E3_CONTINUATION
4H E2_PULLBACK_REJECTION
4H E3_CONTINUATION
1D E2_PULLBACK_REJECTION BUY-only diagnostic
```

It varies:

```text
trigger buffer
MFE target
MAE limit
trigger horizon
quality window
side filter
```

Readiness gates are not relaxed. A candidate must still pass density, stability, MFE/MAE, replay, feature, cost and walk-forward gates.

## Outputs

```text
run_logs\entry_quality_geometry_candidates\latest.json
run_logs\entry_quality_geometry_candidates\latest.html
run_logs\entry_quality_geometry_candidates\latest_candidates.csv
run_logs\entry_quality_geometry_candidates\latest_splits.csv
run_logs\entry_quality_geometry_candidates\latest_walkforward.csv
run_logs\entry_quality_geometry_candidates\latest_events.csv
run_logs\entry_quality_geometry_candidates\latest_replay.csv
run_logs\entry_quality_geometry_candidates\latest_geometry_comparison.csv
run_logs\entry_quality_geometry_candidates\latest_decision_matrix.csv
```

## Recommended owner action

Run from GUI:

```text
AI → Audit entry quality-geometry candidates
```

Or CLI:

```powershell
python -u scripts\audit_entry_quality_geometry_candidates.py `
  --phase182a-path run_logs\entry_event_failure_attribution\latest.json `
  --phase181b-path run_logs\entry_event_discovery\latest.json `
  --symbol XAUUSD `
  --h1-flat-path datasets\processed\XAUUSD\1H\v1.parquet `
  --h4-flat-path datasets\processed\XAUUSD\4H\v1.parquet `
  --d1-flat-path datasets\processed\XAUUSD\1D\v1.parquet `
  --spread-mode fixed `
  --spread-value 0.4 `
  --same-bar-policy stop_first `
  --output-dir run_logs\entry_quality_geometry_candidates
```

Then send:

```text
run_logs\entry_quality_geometry_candidates\latest.json
```

## Verification

```text
python -m py_compile scripts/audit_entry_quality_geometry_candidates.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/ai/test_entry_quality_geometry_candidates.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py
→ passed

python -m pytest tests/unit/ai/test_entry_quality_geometry_candidates.py tests/unit/ai/test_entry_event_failure_attribution.py tests/unit/ai/test_entry_event_discovery.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
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
BLOCKED — Phase183A is a quality-geometry diagnostic only.
No model training.
No Phase134.
No paper shadow.
No live trading.
```

## Owner run result — 2026-10-04

Phase183A was run on the official Phase182A/Phase181B outputs.

Result:

```text
ready_candidates                     : 0/12
selected_candidate_id                : Q7_H4_E2_B00_M10_A10
selected_test_replay_profit_factor   : 1.5527
selected_walkforward_pass_ratio      : 0.0
quality_geometry_redesign_ready_gate : 0
```

Interpretation:

```text
The broad quality-geometry redesign did not rescue the entry route.
Several candidates improved final-test quality/replay, but all remain test-only and fail walk-forward.
```

Documented in:

```text
docs/Report/PHASE183A_ENTRY_QUALITY_GEOMETRY_CANDIDATE_AUDIT_RESULT.md
```
