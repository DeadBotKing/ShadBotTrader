# Phase183A — Entry Quality-Geometry Candidate Audit

## Status

```text
COMPLETED — owner run recorded
Result: ready_candidates=0/12, TEST_ONLY_NOT_TRANSFERRED
Production — BLOCKED
```

Phase183A is a diagnostic-only audit of redesigned entry quality geometry after Phase182A attributed the Phase181B failures to MFE/MAE, replay and walk-forward transfer.

```text
No model training.
No Phase134.
No paper shadow.
No live trading.
No gate relaxation.
```

## Purpose

Phase182A found near-miss pockets but no training-ready family:

```text
1D | E3_CONTINUATION
4H | E2_PULLBACK_REJECTION
4H | E3_CONTINUATION
optional: 1D | E2_PULLBACK_REJECTION | BUY-only
```

Phase183A tests whether changing **target geometry** can improve entry quality without relaxing readiness gates.

Geometry candidates vary:

```text
trigger buffer
trigger horizon
MFE target
MAE limit
quality window
optional side filter
```

## Implemented command

GUI command:

```text
Audit entry quality-geometry candidates
```

Command kind:

```text
CommandKind.AUDIT_ENTRY_QUALITY_GEOMETRY_CANDIDATES
```

Script:

```text
scripts/audit_entry_quality_geometry_candidates.py
```

## Default candidates

Default diagnostic candidates include:

```text
Q1_D1_E3_M10_A10
Q2_D1_E3_M08_A10
Q3_D1_E3_B00_M10_A10
Q4_D1_E3_M10_A125
Q5_H4_E2_M10_A10
Q6_H4_E2_M08_A10
Q7_H4_E2_B00_M10_A10
Q8_H4_E3_M10_A10
Q9_H4_E3_M08_A10
Q10_H4_E3_M10_A125
Q11_D1_E2_BUY_M10_A10
Q12_D1_E2_BUY_M08_A10
```

Important distinction:

```text
Changing MFE/MAE in Phase183A is a target-definition redesign candidate.
It is not a readiness-gate relaxation.
The readiness gates remain active.
```

## Outputs

```text
run_logs/entry_quality_geometry_candidates/latest.json
run_logs/entry_quality_geometry_candidates/latest.html
run_logs/entry_quality_geometry_candidates/latest_candidates.csv
run_logs/entry_quality_geometry_candidates/latest_splits.csv
run_logs/entry_quality_geometry_candidates/latest_walkforward.csv
run_logs/entry_quality_geometry_candidates/latest_events.csv
run_logs/entry_quality_geometry_candidates/latest_replay.csv
run_logs/entry_quality_geometry_candidates/latest_geometry_comparison.csv
run_logs/entry_quality_geometry_candidates/latest_decision_matrix.csv
```

## Recommended GUI run

```text
AI → Audit entry quality-geometry candidates
```

Default fields:

```text
Phase182A result path : run_logs/entry_event_failure_attribution/latest.json
Phase181B result path : run_logs/entry_event_discovery/latest.json
Spread mode/value     : fixed / 0.4
Output dir            : run_logs/entry_quality_geometry_candidates
```

## CLI equivalent

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

## Verification in sandbox

```text
python -m py_compile scripts/audit_entry_quality_geometry_candidates.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/ai/test_entry_quality_geometry_candidates.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py
→ passed

python -m pytest tests/unit/ai/test_entry_quality_geometry_candidates.py tests/unit/ai/test_entry_event_failure_attribution.py tests/unit/ai/test_entry_event_discovery.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ passed
```

## Production status

```text
BLOCKED — quality-geometry audit only.
No model training.
No Phase134.
No paper shadow.
No live trading.
```

## Owner run result — 2026-10-04

Owner ran Phase183A on Phase182A/Phase181B outputs.

Top-level result:

```text
evaluated_candidates                 : 12
ready_candidates                     : 0
selected_candidate_id                : Q7_H4_E2_B00_M10_A10
selected_timeframe                   : 4H
selected_family_type                 : pullback_rejection
selected_side_filter                 : ALL
selected_test_quality_pass_rate      : 0.5929203539823009
selected_test_replay_profit_factor   : 1.5526937756187313
selected_walkforward_pass_ratio      : 0.0
quality_geometry_redesign_ready_gate : 0
no_training_gate                     : 1
no_paper_live_gate                   : 1
```

Interpretation:

```text
Geometry redesign improved several final-test rows, but nothing transferred through train/validation and walk-forward.
The selected Q7 candidate is test-positive only: validation PF=0.8996 and WF=0/4.
```

Decision:

```text
Do not train.
No Phase134.
No paper shadow.
No live trading.
No gate relaxation.
```

Recommended next decision:

```text
Stop/freeze current entry-quality geometry route
or run one narrower Phase184A attribution-only stop-or-narrow decision.
```

Result report:

```text
docs/Report/PHASE183A_ENTRY_QUALITY_GEOMETRY_CANDIDATE_AUDIT_RESULT.md
```
