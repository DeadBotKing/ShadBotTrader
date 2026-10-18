# Phase182A — Entry Event Failure Attribution / Quality Geometry Redesign Decision

## Status

```text
IMPLEMENTED — awaiting owner run
Production — BLOCKED
```

Phase182A consumes the Phase181B entry-event discovery outputs and attributes why no entry-event family passed readiness gates.

```text
No model training.
No Phase134.
No paper shadow.
No live trading.
No gate relaxation.
```

## Purpose

Phase181B found that entry-event families can be:

```text
stable
feature-separable
cost-feasible
```

but still fail:

```text
MFE/MAE quality
replay economics
walk-forward transfer
```

Phase182A explains those failures before any redesign or model preflight.

## Implemented command

GUI command:

```text
Audit entry-event failure attribution
```

Command kind:

```text
CommandKind.AUDIT_ENTRY_EVENT_FAILURE_ATTRIBUTION
```

Script:

```text
scripts/audit_entry_event_failure_attribution.py
```

## Inputs

Primary input:

```text
run_logs/entry_event_discovery/latest.json
```

The script can also consume CSVs referenced by that JSON:

```text
latest_events.csv
latest_replay.csv
latest_splits.csv
latest_walkforward.csv
```

Optional overrides:

```text
--events-path
--replay-path
--splits-path
--walkforward-path
```

## Attribution dimensions

Phase182A attributes failure by:

```text
family
side BUY/SELL
timeframe
MFE/MAE geometry
trigger delay
replay outcome
walk-forward fold gates
failure reasons
```

## Near-miss logic

A family is marked as near-miss only if structural gates passed but final readiness failed:

```text
density_gate == 1
direction_balance_gate == 1
temporal_stability_gate == 1
feature_separability_gate == 1
cost_gate == 1
entry_family_ready_gate == 0
```

and either:

```text
test_replay_profit_factor >= min_near_miss_test_pf
```

or:

```text
test_quality_pass_rate >= min_near_miss_test_quality
```

with sufficient feature separation.

Default thresholds:

```text
min_near_miss_test_pf      = 1.0
min_near_miss_test_quality = 0.35
min_near_miss_feature_smd  = 0.25
```

## Outputs

```text
run_logs/entry_event_failure_attribution/latest.json
run_logs/entry_event_failure_attribution/latest.html
run_logs/entry_event_failure_attribution/latest_family_attribution.csv
run_logs/entry_event_failure_attribution/latest_side_attribution.csv
run_logs/entry_event_failure_attribution/latest_timeframe_attribution.csv
run_logs/entry_event_failure_attribution/latest_quality_geometry.csv
run_logs/entry_event_failure_attribution/latest_walkforward_attribution.csv
run_logs/entry_event_failure_attribution/latest_failure_reasons.csv
run_logs/entry_event_failure_attribution/latest_decision_matrix.csv
run_logs/entry_event_failure_attribution/latest_next_plan.csv
```

## Recommended GUI run

```text
AI → Audit entry-event failure attribution
```

Default fields:

```text
Phase181B result path : run_logs/entry_event_discovery/latest.json
Output dir            : run_logs/entry_event_failure_attribution
```

## CLI equivalent

```powershell
python -u scripts\audit_entry_event_failure_attribution.py `
  --phase181b-path run_logs\entry_event_discovery\latest.json `
  --output-dir run_logs\entry_event_failure_attribution
```

## Decision rules

Phase182A keeps model training blocked unless a later owner-approved phase explicitly opens a model preflight.

Possible decisions:

```text
ENTRY_EVENT_MODEL_TRAINING     : BLOCKED
ENTRY_QUALITY_GEOMETRY_REDESIGN: RECOMMENDED_DIAGNOSTIC or OWNER_REVIEW_REQUIRED
PAPER_OR_LIVE                  : BLOCKED
```

## Verification in sandbox

```text
python -m py_compile scripts/audit_entry_event_failure_attribution.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py tests/unit/ai/test_entry_event_failure_attribution.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py
→ passed

python -m pytest tests/unit/ai/test_entry_event_failure_attribution.py tests/unit/ai/test_entry_event_discovery.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ passed
```

## Production status

```text
BLOCKED — failure attribution only.
No model training.
No Phase134.
No paper shadow.
No live trading.
```

## Owner run result — 2026-10-03

Owner ran Phase182A using:

```text
run_logs\entry_event_discovery\latest.json
```

Top-level result:

```text
family_rows                     : 9
near_miss_families              : 3
selected_focus                  : 1D|E3_CONTINUATION
selected_primary_failure_reason : mfe_mae_gate_failed
selected_next_route_id          : ENTRY_QUALITY_GEOMETRY_REDESIGN
selected_next_phase             : Phase183A — entry quality-geometry candidate audit
no_training_gate                : 1
no_paper_live_gate              : 1
```

Dominant root cause:

```text
mfe_mae_gate_failed            : 9/9
walkforward_pass_ratio_failed  : 9/9
entry_family_ready_gate_failed : 9/9
```

Selected focus:

```text
1D | E3_CONTINUATION
train/validation/test replay PF    : 0.7631 / 0.6793 / 1.2878
train/validation/test quality pass : 0.3189 / 0.2923 / 0.4459
walk-forward pass                  : 0/4
quality verdict                    : MAE_LIMIT_TOO_TIGHT_OR_ENTRY_LATE
```

Decision:

```text
Do not train.
No Phase134.
No paper shadow.
No live trading.
No gate relaxation.
```

Recommended next diagnostic:

```text
Phase183A — Entry Quality-Geometry Candidate Audit
```

Result report:

```text
docs/Report/PHASE182A_ENTRY_EVENT_FAILURE_ATTRIBUTION_RESULT.md
```
