# PHASE175A — Hybrid/regime Walk-forward Failure Attribution Audit Result

## Status

```text
COMPLETED — failure attribution confirmed route instability
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
phase174_path                         : run_logs\hybrid_regime_first_target_redesign\latest.json
source_symbol                         : XAUUSD
source_timeframe                      : 1H
source_spread_mode                    : fixed
source_spread_value                   : 0.4
source_evaluated_regime_candidates    : 66
source_ready_regime_candidates        : 0
source_hybrid_regime_first_ready_gate : 0
candidate_rows                        : 66
walkforward_rows                      : 396
walkforward_pass_rows                 : 0
walkforward_global_pass_ratio         : 0.0
candidates_with_class_balance_gate    : 53
candidates_with_economic_gate         : 4
candidates_with_static_learnability   : 0
candidates_with_walkforward_gate      : 0
candidates_with_ready_gate            : 0
```

Decision fields:

```text
route_decision          : ROUTE_NOT_CONFIRMED_STOP_OR_TARGET_DEFINITION_REDESIGN
recommended_next_phase  : Phase176A — target-definition walk-forward root-cause redesign audit
no_training_gate        : 1
no_paper_live_gate      : 1
production_status       : BLOCKED — Phase175A failure attribution audit only
```

## Main diagnosis

Phase175A confirms the failure is not a simple model-capacity issue.

```text
root_cause_summary:
Phase174A produced validation/test pockets but no stable walk-forward transfer.
Dominant failure attribution points to target/regime instability rather than model capacity;
training remains blocked.
```

The strongest evidence is:

```text
static_learnability_gate_failed   : 66 / 66 candidates
walkforward_learnability_failed   : 66 / 66 candidates
walkforward_pass_ratio_failed     : 66 / 66 candidates
walkforward_pass_rows             : 0 / 396 folds
```

## Dominant candidate-level failures

```text
static_learnability_gate_failed      : 66 / 66 = 1.0000
walkforward_learnability_gate_failed : 66 / 66 = 1.0000
walkforward_pass_ratio_failed        : 66 / 66 = 1.0000
test_balanced_accuracy_failed        : 63 / 66 = 0.9545
economic_gate_failed                 : 62 / 66 = 0.9394
train_negative_expectancy_failed     : 57 / 66 = 0.8636
train_raw_economics_failed           : 55 / 66 = 0.8333
validation_ap_lift_failed            : 52 / 66 = 0.7879
validation_balanced_accuracy_failed  : 49 / 66 = 0.7424
```

Interpretation:

```text
Most candidates were not just failing one metric.
They failed static learnability, walk-forward transfer, balanced accuracy, and/or train economics together.
```

## Dominant walk-forward fold failures

```text
fold_pass_gate_failed                  : 396 / 396 = 1.0000
test_balanced_accuracy_failed          : 292 / 396 = 0.7374
validation_balanced_accuracy_failed    : 292 / 396 = 0.7374
validation_raw_economics_failed        : 253 / 396 = 0.6389
test_raw_economics_failed              : 241 / 396 = 0.6086
test_ap_lift_failed                    : 206 / 396 = 0.5202
validation_ap_lift_failed              : 190 / 396 = 0.4798
test_density_failed                    : 116 / 396 = 0.2929
validation_density_failed              : 113 / 396 = 0.2854
train_density_failed                   : 105 / 396 = 0.2652
```

Interpretation:

```text
The walk-forward issue is broad and recurring.
It is not one bad split, one bad side, or one small-density subset only.
```

## Selected near-miss

Phase175A selected the best failed diagnostic candidate as:

```text
selected_near_miss_family_id          : CA1_BRK_MID
selected_near_miss_regime_rule_id     : WIDTH_GE_Q75
selected_near_miss_ready_gate         : 0
selected_near_miss_primary_failure    : static_learnability_gate_failed
```

Metrics:

```text
train_events / validation_events / test_events : 194 / 42 / 54
train_positive_rate                            : 0.32989690721649484
validation_positive_rate                       : 0.40476190476190477
test_positive_rate                             : 0.35185185185185186
validation_label_psi                           : 0.024180562178840796
test_label_psi                                 : 0.0021459264507231383
validation_ap_lift                             : 0.1417466843907602
test_ap_lift                                   : 0.199135480858877
validation_balanced_accuracy                   : 0.5588235294117647
test_balanced_accuracy                         : 0.5
train_independent_profit_factor                : 0.9584213251508534
validation_independent_profit_factor           : 1.2922853120600728
test_independent_profit_factor                 : 1.0857142857142843
train_mean_atr_score                           : -0.02786199861025283
walkforward_pass_folds                         : 0 / 6
```

Failure reasons:

```text
static_learnability_gate_failed
test_balanced_accuracy_failed
train_negative_expectancy_failed
walkforward_learnability_gate_failed
walkforward_pass_ratio_failed
```

Interpretation:

```text
This is the best failed candidate, but it is still not trainable.
The test balanced accuracy is exactly chance, train expectancy is slightly negative,
and walk-forward pass is 0/6.
```

## Decision matrix

```text
STOP_PHASE174_REGIME_TRAINING                 : MANDATORY, score=100.0
TARGET_DEFINITION_FAILURE_REDESIGN_AUDIT      : RECOMMENDED_DIAGNOSTIC, score=82.0
TRAIN_MODEL_NOW                               : BLOCKED, score=0.0
PAPER_OR_LIVE                                 : BLOCKED, score=0.0
```

The recommendation is diagnostic-only:

```text
Owner may authorize a diagnostic-only target-definition redesign/root-cause phase.
```

## Final decision

```text
Phase175A completed.
It confirms Phase173A/174A should remain frozen as failed diagnostics.
No model training is allowed.
No paper/live/Phase134 is allowed.
```

## Recommended next step

If continuing, the next phase should be:

```text
Phase176A — Target-definition Walk-forward Root-cause Redesign Audit
```

Purpose:

```text
Investigate target-definition failure by fold, side, time, ATR, and payoff horizon before building another target family.
```

Not allowed:

```text
No Phase176 model training.
No paper/live.
No gate relaxation to force a pass.
```
