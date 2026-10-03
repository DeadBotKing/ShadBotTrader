# PHASE168A — 1H Predeclared Filter Confirmation Replay Result

## Status

```text
COMPLETED — confirmation failed
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
filters tested:
  none
  max_spread_atr_0.10
  buy_leg_only
  buy_leg_only+max_spread_atr_0.10

folds                    : 6
selected_filter_name     : buy_leg_only
selected_filter_pass_gate: 0
selected_fold_pass_ratio : 0.16666666666666666
selected_test_pass_ratio : 0.3333333333333333
selected_aggregate_test_pnl: +31.885510318263545
selected_median_test_pf  : 1.3055548257488616
confirmation_pass_gate   : 0
recommendation           : STOP_1H_LOCKED_FILTER_ROUTE_OR_REDESIGN
```

## Decision

```text
Phase168A failed.
No predeclared filter confirmed the locked 1H candidate.
Stop the current 1H locked-candidate route.
Do not train a model around this rule/filter set.
Do not proceed to paper/live/Phase134.
```

## Filter comparison

### buy_leg_only — script-selected by fold-pass ranking

```text
fold_pass_count       : 1 / 6
fold_pass_ratio       : 0.16666666666666666
train_pass_count      : 1 / 6
validation_pass_count : 2 / 6
test_pass_count       : 2 / 6
test_pass_ratio       : 0.3333333333333333
aggregate_train_pnl   : -18.277487298739565
aggregate_validation_pnl: +17.089142763466548
aggregate_test_pnl    : +31.885510318263545
median_test_pf        : 1.3055548257488616
worst_test_pf         : 0.9218327811277753
worst_test_pnl        : -1.0991541256322344
pass_gate             : 0
```

Interpretation:

```text
buy_leg_only improves full fold pass from 0/6 to 1/6, but materially worsens test pass count from 4/6 to 2/6 and lowers aggregate test PnL versus baseline.
This is not an acceptable rescue.
```

### buy_leg_only + max_spread_atr_0.10

```text
fold_pass_count       : 1 / 6
fold_pass_ratio       : 0.16666666666666666
test_pass_count       : 2 / 6
test_pass_ratio       : 0.3333333333333333
aggregate_test_pnl    : +31.885510318263545
median_test_pf        : 1.3055548257488616
pass_gate             : 0
```

Interpretation:

```text
Adding max_spread_atr_0.10 to buy_leg_only did not improve the selected result.
```

### max_spread_atr_0.10

```text
fold_pass_count       : 0 / 6
fold_pass_ratio       : 0.0
train_pass_count      : 1 / 6
validation_pass_count : 3 / 6
test_pass_count       : 4 / 6
test_pass_ratio       : 0.6666666666666666
aggregate_train_pnl   : +45.755584066254045
aggregate_validation_pnl: +35.86424255003535
aggregate_test_pnl    : +41.80187789379908
median_test_pf        : 1.408301745595494
worst_test_pf         : 0.7849777518968888
worst_test_pnl        : -5.560744993965023
pass_gate             : 0
```

Interpretation:

```text
max_spread_atr_0.10 improves aggregate PnL versus baseline and keeps test pass at 4/6, but still produces 0/6 full fold pass.
It confirms signal exists but does not solve stability.
```

### none / baseline

```text
fold_pass_count       : 0 / 6
fold_pass_ratio       : 0.0
train_pass_count      : 1 / 6
validation_pass_count : 3 / 6
test_pass_count       : 4 / 6
test_pass_ratio       : 0.6666666666666666
aggregate_train_pnl   : +27.549662675633076
aggregate_validation_pnl: +32.702512265844575
aggregate_test_pnl    : +38.640147609608306
median_test_pf        : 1.383576104732664
worst_test_pf         : 0.7849777518968888
worst_test_pnl        : -5.560744993965023
pass_gate             : 0
```

Interpretation:

```text
Baseline remains test-positive but fails full-fold stability.
```

## Key conclusion

```text
The 1H locked candidate has persistent test-side signal, but none of the predeclared filters makes it walk-forward stable.
```

The failure is not solved by:

```text
buy-only filtering
spread/ATR filtering at 0.10
combining buy-only and spread/ATR filtering
```

## What this means for the project

```text
The 1H locked-candidate route should stop here.
No model should be trained around BRK_D1_FAST + B15_10 + fixed spread 0.2.
No paper shadow or live trading is allowed.
```

If continuing research, it must be a redesign/new target-family decision, not another patch to this locked rule.

## Recommended next action

```text
Stop the current 1H locked-candidate route.
Do not continue optimizing this rule.
Do not train a model on this target.
```

Possible next research direction only with explicit owner approval:

```text
A new target/candidate family for 1H, or a pause of the pivot route and return to broader architecture/model-family review.
```

Production remains blocked.
