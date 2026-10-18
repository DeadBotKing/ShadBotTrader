# PHASE180A — Higher-timeframe Target Failure Attribution Result

## Status

```text
COMPLETED — cost feasibility confirmed, target readiness still failed
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
phase179_path                           : run_logs\higher_timeframe_cost_feasibility\latest.json
source_symbol                           : XAUUSD
source_timeframes                       : 4H, 1D
source_spread_mode/value                : fixed / 0.4
source_evaluated_candidates             : 8
source_ready_candidates                 : 0
source_higher_timeframe_feasibility_gate: 0

cost_feasibility_confirmed_gate         : 1
target_readiness_confirmed_failed_gate  : 1
selected_next_route_id                  : D1_TARGET_FAILURE_ATTRIBUTION_AND_REDESIGN_DECISION
selected_next_phase                     : Phase181A — daily target failure attribution and redesign decision
selected_focus_timeframe                : 1D
selected_focus_family_id                : D1_R1_BK_MID_B20_10_H5
no_training_gate                        : 1
no_paper_live_gate                      : 1
production_status                       : BLOCKED — Phase180A higher-timeframe failure attribution only
```

## Main diagnosis

```text
Higher timeframes materially reduce spread/ATR, but target readiness still fails.
The daily D1_R1 candidate is a near-miss, not a training-ready target.
```

The result is now clearly separated into two facts:

```text
1. Cost feasibility is confirmed.
2. Target readiness is still not confirmed.
```

## Timeframe summary

### 1D

```text
health_gate                    : 1
candidate_count                : 4
ready_candidates               : 0
near_miss_candidates           : 1
cost_gate_pass_splits          : 3 / 3
median_spread_atr_train        : 0.025360597027245434
median_spread_atr_validation   : 0.01611835477650174
median_spread_atr_test         : 0.0103267684590986
best_family_id                 : D1_R1_BK_MID_B20_10_H5
best_family_ready_gate         : 0
best_walkforward_pass_ratio    : 0.2
best_train_independent_pf      : 1.126307793286277
best_validation_independent_pf : 1.1464230646980718
best_test_independent_pf       : 1.4117136055682946
best_validation_ap_lift        : 0.030854212243725865
best_test_ap_lift              : 0.011215791489045668
best_test_balanced_accuracy    : 0.5
dominant_failure_reason        : static_learnability_gate_failed
verdict                        : TARGET_NOT_READY_COST_FEASIBLE
```

### 4H

```text
health_gate                    : 1
candidate_count                : 4
ready_candidates               : 0
near_miss_candidates           : 0
cost_gate_pass_splits          : 3 / 3
median_spread_atr_train        : 0.06885104839445252
median_spread_atr_validation   : 0.042461235228031455
median_spread_atr_test         : 0.027249945272937434
best_family_id                 : H4_R2_BK_STRICT_B15_10_H6
best_family_ready_gate         : 0
best_walkforward_pass_ratio    : 0.0
best_train_independent_pf      : 0.8248681526670225
best_validation_independent_pf : 1.2107802767748224
best_test_independent_pf       : 1.269952134110483
best_validation_ap_lift        : 0.03560148097941623
best_test_ap_lift              : 0.1427660222201747
best_test_balanced_accuracy    : 0.5399584846912299
dominant_failure_reason        : economic_gate_failed
verdict                        : TARGET_NOT_READY_COST_FEASIBLE
```

## Selected focus candidate

```text
selected_focus_timeframe  : 1D
selected_focus_family_id  : D1_R1_BK_MID_B20_10_H5
near_miss_gate            : 1
```

Candidate metrics:

```text
train_events                     : 150
validation_events                : 34
test_events                      : 50
train_positive_rate              : 0.44
validation_positive_rate         : 0.5294117647058824
test_positive_rate               : 0.48
validation_label_psi             : 0.03209391415055135
test_label_psi                   : 0.0064447739657340665
train_independent_profit_factor  : 1.126307793286277
validation_independent_pf        : 1.1464230646980718
test_independent_pf              : 1.4117136055682946
train_mean_atr_score             : 0.0640646047619284
validation_mean_atr_score        : 0.0668837240261654
test_mean_atr_score              : 0.19272291487919463
validation_ap_lift               : 0.030854212243725865
test_ap_lift                     : 0.011215791489045668
validation_balanced_accuracy     : 0.5243055555555556
test_balanced_accuracy           : 0.5
walkforward_pass_folds           : 1 / 5
walkforward_pass_ratio           : 0.2
```

Failure reasons:

```text
static_learnability_gate_failed
target_family_ready_gate_failed
test_ap_lift_failed
test_balanced_accuracy_failed
walkforward_gate_failed
walkforward_pass_ratio_failed
```

Why it is a near-miss but not trainable:

```text
1. Economics are positive in train/validation/test.
2. Cost is low at 1D.
3. But test AP lift is below gate.
4. Test balanced accuracy is exactly chance at 0.5000.
5. Walk-forward pass is only 1/5, below the required threshold.
```

## Failure attribution

Candidate-level dominant failures:

```text
static_learnability_gate_failed    : 8 / 8 = 1.000
walkforward_gate_failed            : 8 / 8 = 1.000
walkforward_pass_ratio_failed      : 8 / 8 = 1.000
economic_gate_failed               : 7 / 8 = 0.875
train_expectancy_failed            : 6 / 8 = 0.750
test_balanced_accuracy_failed      : 5 / 8 = 0.625
test_ap_lift_failed                : 3 / 8 = 0.375
density_gate_failed                : 1 / 8 = 0.125
```

Walk-forward fold-level failures:

```text
test_gate_failed       : 37 / 40 = 0.925
validation_gate_failed : 34 / 40 = 0.850
train_gate_failed      : 30 / 40 = 0.750
```

## Decision matrix

```text
HIGHER_TIMEFRAME_MODEL_TRAINING : BLOCKED, score=0.0
D1_TARGET_REDESIGN_ATTRIBUTION  : RECOMMENDED_DIAGNOSTIC, score=82.0
NON_PIVOT_EVENT_ROUTE           : SECONDARY_RESEARCH, score=70.0
PAPER_OR_LIVE                   : BLOCKED, score=0.0
```

## Final decision

```text
Phase180A completed.
Cost feasibility is confirmed on 4H/1D.
Target readiness remains failed.
D1_R1 is a near-miss, not a training-ready target.
```

Operational decision:

```text
Do not train 4H/1D models.
Do not open Phase134.
Do not paper shadow.
Do not live trade.
Do not relax gates.
```

## Recommended next phase

If continuing, the recommended next diagnostic is:

```text
Phase181A — Daily target failure attribution and redesign decision
```

Purpose:

```text
Focus on D1_R1_BK_MID_B20_10_H5, especially:
- why only 1/5 folds passed
- why test AP lift stayed below gate
- why test balanced accuracy stayed at chance
- whether daily target geometry should be redesigned or the pivot-family route should be stopped
```

Not allowed:

```text
No Phase181 model training.
No paper/live.
No gate relaxation.
```
