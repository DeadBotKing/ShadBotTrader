# PHASE179A — 4H/1D Broker-cost Feasibility and Target Pre-audit Result

## Status

```text
COMPLETED — higher-timeframe target gate failed
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
symbol                              : XAUUSD
spread_mode                         : fixed
spread_value                        : 0.4
evaluated_timeframes                : 2
evaluated_candidates                : 8
ready_candidates                    : 0
selected_timeframe                  : 1D data path was used; run label printed as "1" because PowerShell passed 1D as numeric 1
selected_family_id                  : D1_R1_BK_MID_B20_10_H5
selected_family_ready_gate          : 0
selected_walkforward_pass_ratio     : 0.2
higher_timeframe_feasibility_gate   : 0
recommendation                      : NO_HIGHER_TIMEFRAME_TARGET_READY
production_status                   : BLOCKED — Phase179A 4H/1D feasibility pre-audit only
```

Important implementation note:

```text
The owner run displayed the daily timeframe as "1" instead of "1D" because PowerShell can pass unquoted 1D as numeric 1.
The D1 flat path and D1 candidate families were still used, so the main candidate/cost conclusions remain usable.
The script was patched after this run to canonicalize "1"/"D1" to "1D" and "4"/"H4" to "4H" in future runs.
```

## Broker cost feasibility

Cost pressure improved materially on higher timeframes.

### 4H spread/ATR

```text
train median spread/ATR      : 0.06885104839445252
validation median spread/ATR : 0.042461235228031455
test median spread/ATR       : 0.027249945272937434
cost_feasible_gate           : 1 for train/validation/test
```

### 1D spread/ATR

```text
train median spread/ATR      : 0.025360597027245434
validation median spread/ATR : 0.01611835477650174
test median spread/ATR       : 0.0103267684590986
cost_feasible_gate           : 1 for train/validation/test
```

Interpretation:

```text
The higher-timeframe route passed broker-cost feasibility.
Spread is no longer the primary blocker at 4H/1D under fixed spread=0.4.
The blocker remains target learnability / walk-forward transfer.
```

## Dataset health

```text
4H rows  : 34038
1D rows  : 5698
health_gate = 1 for both
```

4H had expected calendar/session gaps:

```text
4H gap_count       : 1247
4H max_gap_minutes : 6720
```

Daily run note:

```text
In this run the daily label printed as "1", so expected_step_minutes was 0.0 in the health row.
This was fixed in code after the run by canonicalizing the timeframe token.
```

## Selected best failed candidate

```text
family_id        : D1_R1_BK_MID_B20_10_H5
label            : d1_breakout_mid
side_mapping     : breakout
recent_window    : 20
tp/sl/hold       : 2.0 / 1.0 / 5
```

Metrics:

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

Gate result:

```text
density_gate                     : 1
economic_gate                    : 1
static_learnability_gate         : 0
walkforward_gate                 : 0
target_family_ready_gate         : 0
```

Why it failed:

```text
1. Test AP lift is below gate: 0.0112 < 0.02.
2. Test balanced accuracy is chance: 0.5000 < 0.52.
3. Walk-forward pass ratio is 0.2 < 0.5.
```

## Best 4H candidate

```text
family_id                    : H4_R2_BK_STRICT_B15_10_H6
train_independent_pf         : 0.8248681526670225
validation_independent_pf    : 1.2107802767748224
test_independent_pf          : 1.269952134110483
validation_ap_lift           : 0.03560148097941623
test_ap_lift                 : 0.1427660222201747
validation_balanced_accuracy : 0.4969924812030075
test_balanced_accuracy       : 0.5399584846912299
walkforward_pass_ratio       : 0.0
ready_gate                   : 0
```

Why it failed:

```text
Train PF and train expectancy were negative/weak.
Validation balanced accuracy was below gate.
Walk-forward pass ratio was 0.0.
```

## Candidate decision

All 8 higher-timeframe candidates failed:

```text
D1_R1_BK_MID_B20_10_H5       : ready=0, WF=1/5
D1_R3_BK_WIDE_B25_125_H10    : ready=0, WF=0/5
D1_R2_BK_STRICT_B15_10_H5    : ready=0, WF=0/5
D1_R4_REV_MID_B10_075_H5     : ready=0, WF=0/5
H4_R2_BK_STRICT_B15_10_H6    : ready=0, WF=0/5
H4_R1_BK_MID_B15_10_H6       : ready=0, WF=0/5
H4_R3_BK_WIDE_B20_10_H12     : ready=0, WF=0/5
H4_R4_REV_MID_B10_075_H6     : ready=0, WF=0/5
```

## Decision matrix

```text
HIGHER_TIMEFRAME_TARGET_READY : NOT_CONFIRMED, score=35.0
TRAIN_MODEL_NOW               : BLOCKED, score=0.0
PAPER_OR_LIVE                 : BLOCKED, score=0.0
```

## Final decision

```text
Phase179A failed target-readiness gates.
Higher timeframe cost feasibility improved, but no 4H/1D target family is ready for model training.
```

Operational decision:

```text
Do not train D1/H4 candidates.
Do not open Phase134.
Do not paper shadow.
Do not live trade.
Do not relax gates.
```

## Recommended next action

The important positive finding is:

```text
Cost feasibility passed strongly on 4H/1D.
```

The important negative finding is:

```text
Target/learnability/walk-forward transfer still failed.
```

Recommended next step if continuing:

```text
Phase180A — Higher-timeframe target failure attribution / candidate redesign decision
```

Purpose:

```text
Attribute why the daily candidate D1_R1 only passed 1/5 walk-forward folds and whether the issue is label horizon, bracket geometry, feature separability, or fold economics.
```

Not allowed:

```text
No model training.
No paper/live.
No gate relaxation.
```
