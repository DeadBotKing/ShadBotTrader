# PHASE176A — Target-definition Walk-forward Root-cause Redesign Audit Result

## Status

```text
COMPLETED — current target definitions rejected
Production — BLOCKED
```

No production/paper/live/model-training approval:

```text
No Phase134.
No paper shadow.
No live trading.
No model training.
No gate relaxation.
```

## Top-level result

```text
source_symbol                                   : XAUUSD
source_timeframe                                : 1H
source_spread_mode/value                        : fixed / 0.4
source_candidate_rows                           : 66
source_walkforward_rows                         : 396
source_walkforward_pass_rows                    : 0
source_walkforward_global_pass_ratio            : 0.0
source_candidates_with_static_learnability_gate : 0
source_candidates_with_walkforward_gate         : 0
source_candidates_with_ready_gate               : 0

target_definitions_audited                      : 3
regime_axes_audited                             : 10
root_cause_confirmed_gate                       : 1
target_definition_redesign_required_gate        : 1
direct_training_blocked_gate                    : 1
paper_live_blocked_gate                         : 1

selected_root_cause                             : target_definition_static_and_walkforward_instability
selected_failed_target_definition               : CA1_BRK_MID
selected_failed_axis                            : family:CA1_BRK_MID
route_decision                                  : CURRENT_TARGET_DEFINITIONS_REJECTED_REDESIGN_DIAGNOSTIC_ONLY
recommended_next_phase                          : Phase177A — walk-forward target-family redesign candidate audit
production_status                               : BLOCKED — Phase176A target-definition root-cause audit only
```

## Key conclusion

Phase176A confirms that the current broker-cost-aware 1H target definitions must be frozen as failed diagnostics.

```text
CA1_BRK_MID    rejected
CA3_BRK_STRICT rejected
CA2_BRK_WIDE   rejected
```

The failure is not isolated to one filter or one session. Every family and every target-definition axis still has:

```text
ready_candidates = 0
walkforward_pass_ratio = 0.0
```

## Target definition attribution

### CA1_BRK_MID

```text
target_label             : cost_breakout_mid
geometry_profile         : mid_zone_rw24
side_mapping             : breakout
entry_delay_bars         : 1
recent_window_bars       : 24
pivot_zone_atr           : 0.10
tp_atr / sl_atr          : 2.0 / 1.0
hold_bars                : 24
candidates               : 22
ready_candidates         : 0
economic_pass            : 1
static_pass              : 0
walkforward_pass         : 0
mean_train_pf            : 0.8152246978569013
mean_validation_pf       : 0.992697955786879
mean_test_pf             : 1.1448585384507168
mean_validation_ap_lift  : -0.003549310827497954
mean_test_ap_lift        : 0.03984988305268222
mean_test_balanced_acc   : 0.4513708305564469
walkforward_pass_ratio   : 0.0
root_failure             : static_learnability_gate_failed
```

Decision:

```text
Freeze CA1_BRK_MID.
Current mid_zone_rw24 with hold=24 and TP/SL=2.0/1.0 does not transfer.
```

### CA3_BRK_STRICT

```text
target_label             : cost_breakout_strict
geometry_profile         : strict_zone_rw24
side_mapping             : breakout
entry_delay_bars         : 1
recent_window_bars       : 24
pivot_zone_atr           : 0.05
tp_atr / sl_atr          : 2.0 / 1.0
hold_bars                : 24
candidates               : 22
ready_candidates         : 0
economic_pass            : 3
static_pass              : 0
walkforward_pass         : 0
mean_train_pf            : 0.8763616314554745
mean_validation_pf       : 1.1776090974020774
mean_test_pf             : 1.0803034040263118
mean_validation_ap_lift  : -0.019824516109722357
mean_test_ap_lift        : 0.08951024913321408
mean_test_balanced_acc   : 0.4540618233245942
walkforward_pass_ratio   : 0.0
root_failure             : static_learnability_gate_failed
```

Decision:

```text
Freeze CA3_BRK_STRICT.
Current strict_zone_rw24 with hold=24 and TP/SL=2.0/1.0 does not transfer.
```

### CA2_BRK_WIDE

```text
target_label             : cost_breakout_wide
geometry_profile         : wide_zone_rw48
side_mapping             : breakout
entry_delay_bars         : 1
recent_window_bars       : 48
pivot_zone_atr           : 0.10
tp_atr / sl_atr          : 2.5 / 1.25
hold_bars                : 48
candidates               : 22
ready_candidates         : 0
economic_pass            : 0
static_pass              : 0
walkforward_pass         : 0
mean_train_pf            : 0.7917012616487692
mean_validation_pf       : 1.01504846361489
mean_test_pf             : 1.2719121214125975
mean_validation_ap_lift  : 0.04524331504788121
mean_test_ap_lift        : 0.030937654036250137
mean_test_balanced_acc   : 0.45415655635617935
walkforward_pass_ratio   : 0.0
root_failure             : economic_gate_failed
```

Decision:

```text
Freeze CA2_BRK_WIDE.
Current wide_zone_rw48 with hold=48 and TP/SL=2.5/1.25 does not transfer.
```

## Axis attribution highlights

All family and geometry axes have:

```text
verdict = REJECTED_WALKFORWARD_ZERO
```

Important axis conclusions:

```text
family CA1_BRK_MID    : top failure = static_learnability_gate_failed
family CA2_BRK_WIDE   : top failure = economic_gate_failed
family CA3_BRK_STRICT : top failure = static_learnability_gate_failed

geometry mid_zone_rw24    : REJECTED_WALKFORWARD_ZERO
geometry strict_zone_rw24 : REJECTED_WALKFORWARD_ZERO
geometry wide_zone_rw48   : REJECTED_WALKFORWARD_ZERO

hold=24 : REJECTED_WALKFORWARD_ZERO
hold=48 : REJECTED_WALKFORWARD_ZERO

TP/SL 2.0/1.0   : REJECTED_WALKFORWARD_ZERO
TP/SL 2.5/1.25  : REJECTED_WALKFORWARD_ZERO
```

Regime axes also rejected:

```text
baseline       : REJECTED_WALKFORWARD_ZERO
side           : REJECTED_WALKFORWARD_ZERO
zone           : REJECTED_WALKFORWARD_ZERO
cost           : REJECTED_WALKFORWARD_ZERO
atr            : REJECTED_WALKFORWARD_ZERO
range_width    : REJECTED_WALKFORWARD_ZERO
session        : REJECTED_WALKFORWARD_ZERO
momentum       : REJECTED_WALKFORWARD_ZERO
side_momentum  : REJECTED_WALKFORWARD_ZERO
side_cost      : REJECTED_WALKFORWARD_ZERO
```

## Redesign hypotheses

All six diagnostic hypotheses are supported:

```text
H1_TARGET_DEFINITION_MISMATCH              : SUPPORTED
H2_TRAIN_EXPECTANCY_INSTABILITY            : SUPPORTED
H3_CLASSIFIER_SIGNAL_NOT_STABLE            : SUPPORTED
H4_RAW_ECONOMICS_DO_NOT_TRANSFER_BY_FOLD   : SUPPORTED
H5_DENSITY_IS_SECONDARY_NOT_PRIMARY        : SUPPORTED
H6_SESSION_FILTERS_NOT_ENOUGH              : SUPPORTED
```

Most important implications:

```text
1. Do not train on CA1/CA3/CA2 targets.
2. A future phase must change the target definition before model design.
3. Feature/model changes should not be attempted until the labels themselves produce stable separability.
4. Session filters created pockets but did not create a route.
5. Density is a constraint, not the primary objective.
```

## Decision matrix

```text
FREEZE_PHASE173_174_TARGETS              : MANDATORY, score=100.0
TARGET_FAMILY_REDESIGN_DIAGNOSTIC        : RECOMMENDED_DIAGNOSTIC, score=86.0
TRAIN_MODEL_NOW                          : BLOCKED, score=0.0
PAPER_OR_LIVE                            : BLOCKED, score=0.0
```

## Final decision

```text
Phase176A completed.
Current target definitions are rejected.
A future target-family redesign may be audited, but only as diagnostic research.
No model training is allowed.
No paper/live/Phase134 is allowed.
```

## Recommended next phase

If the owner wants to continue the research lane, the next phase should be:

```text
Phase177A — Walk-forward Target-family Redesign Candidate Audit
```

Purpose:

```text
Design and audit new target-family candidates that explicitly address:
- train-negative expectancy
- chance-level balanced accuracy
- raw economics not transferring by fold
- session pockets not being enough
- current TP/SL/hold geometry failing all walk-forward gates
```

Not allowed:

```text
No Phase177 model training.
No paper/live.
No gate relaxation to force a pass.
```
