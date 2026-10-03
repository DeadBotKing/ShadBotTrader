# PHASE173A — Broker-cost-aware 1H Target Learnability / Dataset Build Audit Result

## Status

```text
COMPLETED — target learnability gates failed
Production — BLOCKED
```

No production/paper/live approval:

```text
No Phase134.
No paper shadow.
No live trading.
No model-training phase is approved from this result.
```

## Top-level result

```text
symbol                          : XAUUSD
timeframe                       : 1H
flat_path                       : datasets\processed\XAUUSD\1H\v1.parquet
flat_rows                       : 50000
train_rows                      : 35000
validation_rows                 : 7476
test_rows                       : 7476
spread_mode                     : fixed
spread_value                    : 0.4
candidate_families              : 3
learnable_families              : 0
selected_family_id              : CA3_BRK_STRICT
selected_family_ready_gate      : 0
target_learnability_ready_gate  : 0
production_status               : BLOCKED — Phase173A target learnability audit only
```

Important interpretation:

```text
Phase172A target-family structure passed.
Phase173A learnability did not pass.
Therefore CA1/CA3/CA2 must not advance to model training yet.
```

The `selected_family_id=CA3_BRK_STRICT` field is only the diagnostic best among failed families. It does not mean the family is training-ready because `selected_family_ready_gate=0`.

## Feature set audited

Phase173A used causal event-level features only:

```text
side_buy, side_sell, zone_top, zone_bottom, atr,
range_atr, body_atr, upper_wick_atr, lower_wick_atr,
recent_position, recent_width_atr, dist_top_atr, dist_bottom_atr,
ret_1_atr, ret_3_atr, ret_6_atr, ret_12_atr, ret_24_atr,
hour_sin, hour_cos, dow_sin, dow_cos, spread_to_atr
```

Labels:

```text
POSITIVE -> 1
NEGATIVE/TIMEOUT -> 0
```

## Family comparison

| family | events train/val/test | positive rate train/val/test | validation AP lift | test AP lift | validation balanced acc | test balanced acc | walk-forward pass | ready |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| CA3_BRK_STRICT | 344 / 68 / 82 | 0.3314 / 0.3971 / 0.3659 | -0.0460 | +0.1219 | 0.5000 | 0.5000 | 0/6 | 0 |
| CA1_BRK_MID | 775 / 184 / 202 | 0.3084 / 0.3641 / 0.3713 | -0.0397 | +0.0305 | 0.4448 | 0.5018 | 0/6 | 0 |
| CA2_BRK_WIDE | 574 / 144 / 141 | 0.2944 / 0.3681 / 0.4184 | -0.0208 | +0.0191 | 0.5024 | 0.5000 | 0/6 | 0 |

## Gate diagnosis

### What passed

Class balance and label-density were acceptable:

```text
CA1 class_balance_gate : 1
CA3 class_balance_gate : 1
CA2 class_balance_gate : 1
```

Label PSI was also low for the main chronological split:

```text
CA1 validation_label_psi : 0.01394638636661747
CA1 test_label_psi       : 0.017673124891912508
CA3 validation_label_psi : 0.01865799134306241
CA3 test_label_psi       : 0.005231961037590895
CA2 validation_label_psi : 0.024549926691410616
CA2 test_label_psi       : 0.06756398214045817
```

So the failure is not caused by missing labels or extreme class imbalance.

### What failed

Static learnability failed for every family:

```text
CA1 static_learnability_gate : 0
CA3 static_learnability_gate : 0
CA2 static_learnability_gate : 0
```

Walk-forward learnability failed for every family:

```text
CA1 walkforward_pass_folds : 0 / 6
CA3 walkforward_pass_folds : 0 / 6
CA2 walkforward_pass_folds : 0 / 6
```

The main reason is that validation-side predictive lift is not stable:

```text
CA1 validation_ap_lift : -0.039655326743611774
CA3 validation_ap_lift : -0.04598810133709075
CA2 validation_ap_lift : -0.02084860991206433
```

Balanced accuracy is also around chance or worse:

```text
CA1 validation/test balanced accuracy : 0.4448 / 0.5018
CA3 validation/test balanced accuracy : 0.5000 / 0.5000
CA2 validation/test balanced accuracy : 0.5024 / 0.5000
```

## Side AP notes

Some side-specific AP values look locally interesting, for example:

```text
CA3 validation_buy_ap : 0.5083
CA3 test_sell_ap      : 0.6570
CA2 test_sell_ap      : 0.5263
```

But this is not enough to continue to model training because:

```text
1. The global static gates failed.
2. The walk-forward pass ratio is 0.0 for all families.
3. Side strength is not stable across validation/test.
4. Thresholds selected on train do not transfer into validation/test classification quality.
```

## Decision

```text
Phase173A failed.
learnable_families = 0
target_learnability_ready_gate = 0
```

Operational decision:

```text
Do not train CA1_BRK_MID.
Do not train CA3_BRK_STRICT.
Do not train CA2_BRK_WIDE.
Do not open Phase134.
Do not paper shadow.
Do not live trade.
```

## Recommended next decision

A new model-training phase is blocked. The next action requires explicit owner authorization because it changes the research lane.

Recommended diagnostic path:

```text
Phase174A — Hybrid/regime-first target redesign decision/audit
```

Purpose:

```text
Use the Phase171A secondary route: HYBRID_REGIME_FIRST_REDESIGN.
Do not train a deep model yet.
First audit whether predeclared regime partitions or richer causal regime features can create stable learnability before redesigning target families or training.
```

Alternative:

```text
Stop the 1H broker-cost-aware target-family route and pause for manual review.
```
