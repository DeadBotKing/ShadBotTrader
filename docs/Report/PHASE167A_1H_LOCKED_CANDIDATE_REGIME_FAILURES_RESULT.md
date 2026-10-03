# PHASE167A — 1H Locked Candidate Regime / Failure Attribution Result

## Status

```text
COMPLETED — attribution found regime sensitivity but no strong rescue filter
Production — BLOCKED
```

No production/paper/live approval:

```text
No Phase134.
No paper shadow.
No live trading.
```

## Top-level result

```text
folds                       : 6
baseline_fold_pass_count    : 0
baseline_test_pass_count    : 4
baseline_aggregate_test_pnl : +38.640147609608306
dominant_failure_reason     : monthly_stability_failed
recommendation              : REGIME_FILTER_CONFIRMATION_REQUIRED_NO_TRAINING
```

The attribution confirms the Phase166A diagnosis:

```text
The locked 1H candidate has real test-side signal, but the full train/validation/monthly stability is not robust enough.
```

## Locked candidate audited

```text
policy_key                : BRK_D1_FAST
side_mapping              : breakout
entry_delay_bars          : 1
recent_window_bars        : 24
pivot_zone_atr            : 0.05
top_position_threshold    : 0.85
bottom_position_threshold : 0.15
exclude_both_zones        : 1
min_range_width_atr       : 1.0
max_range_width_atr       : 0.0
bracket_id                : B15_10
tp_atr                    : 1.5
sl_atr                    : 1.0
hold_bars                 : 24
spread_mode               : fixed
spread_value              : 0.2
```

## Main failure reason

```text
dominant_failure_reason = monthly_stability_failed
```

Fold-level failure reasons:

```text
Fold 1: train failed, test failed, monthly failed, stress failed
Fold 2: train failed, validation failed, monthly failed, stress failed
Fold 3: train failed, monthly failed, stress failed
Fold 4: train failed, test failed, monthly failed, stress failed
Fold 5: train failed, validation failed, monthly failed, stress failed
Fold 6: validation failed, monthly failed, stress failed
```

Key observation:

```text
monthly_stability_gate = 0 in all 6 folds
stress_transfer_pass_gate = 0 in all 6 folds
```

This is stronger evidence against immediate model training than the positive test-side aggregate is evidence for it.

## Side attribution

Top-level side attribution reported:

```text
worst_side           : ALL|BUY
worst_side_total_pnl : +32.373761889586895
```

This field being positive means no side is net-negative in the aggregate attribution table; BUY is simply the weaker side by total PnL under this aggregation.

Fold-level behavior is mixed:

```text
Early folds often show BUY weakness.
Some later folds show SELL weakness or positive BUY dominance.
There is no clean single-side kill switch that solves the walk-forward failure.
```

Diagnostic filters confirm this:

```text
buy_leg_only:
  fold_pass_ratio       : 0.16666666666666666
  test_pass_ratio       : 0.3333333333333333
  aggregate_test_pnl    : +31.885510318263545
  median_test_pf        : 1.3055548257488616

sell_leg_only:
  fold_pass_ratio       : 0.0
  test_pass_ratio       : 0.16666666666666666
  aggregate_test_pnl    : +6.888960313805891
```

Interpretation:

```text
BUY-only improves full fold pass from 0/6 to 1/6, but it reduces test pass count from 4/6 to 2/6.
SELL-only is clearly worse.
```

So side filtering alone is not a robust rescue.

## ATR regime attribution

Top-level ATR attribution:

```text
worst_atr_regime           : atr_q3_mid_high
worst_atr_regime_total_pnl : +1.5931376966985034
```

Again, the aggregate worst ATR regime is still slightly positive. Fold-level failures rotate across ATR regimes:

```text
Fold 1 worst ATR regime: atr_q4_high
Fold 2 worst ATR regime: atr_q1_low
Fold 3 worst ATR regime: atr_q1_low
Fold 4 worst ATR regime: atr_q3_mid_high
Fold 5 worst ATR regime: atr_q1_low but still positive
Fold 6 worst ATR regime: atr_q3_mid_high but still positive
```

Filter diagnostics:

```text
min_atr_q50:
  fold_pass_ratio       : 0.0
  test_pass_ratio       : 0.5
  aggregate_test_pnl    : +29.608460110422634
  median_test_pf        : 1.4369941295305733

min_atr_q75:
  fold_pass_ratio       : 0.0
  test_pass_ratio       : 0.16666666666666666
  aggregate_test_pnl    : +23.191597797833698
  median_test_pf        : 1.326213963674625
```

Interpretation:

```text
A simple minimum-ATR filter does not fix fold stability.
```

## Spread/ATR attribution

Diagnostic filters:

```text
max_spread_atr_0.10:
  fold_pass_ratio       : 0.0
  test_pass_ratio       : 0.6666666666666666
  aggregate_test_pnl    : +41.80187789379908
  median_test_pf        : 1.408301745595494

max_spread_atr_0.05:
  fold_pass_ratio       : 0.0
  test_pass_ratio       : 0.3333333333333333
  aggregate_test_pnl    : +34.375445811313185
  median_test_pf        : 1.3634023425436874
```

Interpretation:

```text
max_spread_atr_0.10 improves aggregate test PnL versus baseline and keeps the same test-pass ratio, but it still does not produce any full fold pass.
max_spread_atr_0.05 is too restrictive and reduces test pass count.
```

So spread/ATR filtering is diagnostically interesting but not sufficient by itself.

## Calendar/month attribution

Repeated bad months appear in fold failures:

```text
2018-11
2022-08
```

Examples:

```text
Fold 1 worst_month: 2018-11, pnl=-5.4897689726064005
Fold 2 worst_month: 2018-11, pnl=-5.071719778154557
Fold 3 worst_month: 2022-08, pnl=-4.098970175636167
Fold 4 worst_month: 2022-08, pnl=-4.16897855698513
```

Interpretation:

```text
The candidate is vulnerable to specific historical regimes/months, not just random noise.
```

## Filter summary ranking

```text
1. buy_leg_only:
   fold_pass_ratio=0.1667, test_pass_ratio=0.3333, aggregate_test_pnl=+31.8855

2. max_spread_atr_0.10:
   fold_pass_ratio=0.0, test_pass_ratio=0.6667, aggregate_test_pnl=+41.8019

3. none:
   fold_pass_ratio=0.0, test_pass_ratio=0.6667, aggregate_test_pnl=+38.6401

4. min_atr_q50:
   fold_pass_ratio=0.0, test_pass_ratio=0.5, aggregate_test_pnl=+29.6085

5. max_spread_atr_0.05:
   fold_pass_ratio=0.0, test_pass_ratio=0.3333, aggregate_test_pnl=+34.3754

6. min_atr_q75:
   fold_pass_ratio=0.0, test_pass_ratio=0.1667, aggregate_test_pnl=+23.1916

7. sell_leg_only:
   fold_pass_ratio=0.0, test_pass_ratio=0.1667, aggregate_test_pnl=+6.8890
```

## Decision

```text
Phase167A did not find a strong enough regime filter to justify model training.
```

The script recommendation is:

```text
REGIME_FILTER_CONFIRMATION_REQUIRED_NO_TRAINING
```

This is accurate: if continuing diagnostics, the next step must be confirmation-only, not training.

## Recommended next action

Do not train a model yet.

Recommended next diagnostic only if continuing the 1H route:

```text
Phase168A — 1H Predeclared Filter Confirmation Replay
```

Phase168A should test only a small, predeclared filter set from Phase167A:

```text
A) max_spread_atr_0.10
B) buy_leg_only
C) buy_leg_only + max_spread_atr_0.10
D) baseline none
```

Rules:

```text
No new grid search.
No threshold optimization.
Same locked candidate and fold settings.
Confirmation-only comparison.
```

If Phase168A does not materially improve full fold stability, stop the 1H locked-candidate route and do not train a model around it.

Production remains blocked.
