# PHASE166A — 1H Locked Candidate Walk-Forward / Anti-Overfit Replay Result

## Status

```text
COMPLETED — walk-forward anti-overfit gate failed
Production — BLOCKED
```

No production/paper/live approval:

```text
No Phase134.
No paper shadow.
No live trading.
```

## Locked candidate tested

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

## Top-level result

```text
folds                    : 6
fold_pass_count          : 0
fold_pass_ratio          : 0.0
test_pass_count          : 4
test_pass_ratio          : 0.6666666666666666
aggregate_test_trades    : 220
aggregate_test_cash_pnl  : +38.640147609608306
median_test_profit_factor: 1.383576104732664
mean_test_profit_factor  : 1.4109730098527464
worst_test_profit_factor : 0.7849777518968888
worst_test_cash_pnl      : -5.560744993965023
worst_test_max_drawdown  : 6.86223346129448
walk_forward_pass_gate   : 0
```

## Interpretation

Phase166A produced a mixed result:

```text
Positive signs:
  - test_pass_count = 4/6
  - aggregate_test_cash_pnl = +38.64
  - median_test_profit_factor = 1.3836
  - worst_test_drawdown is bounded at 6.8622

Negative signs:
  - fold_pass_count = 0/6
  - no fold passed full train + validation + test + monthly stability gates
  - train stability fails in 5 of 6 folds
  - monthly_stability_gate = 0 in all folds
  - stress_transfer_pass_gate = 0 in all folds
```

Therefore the locked candidate has useful recent/out-of-sample test behavior, but it is not stable enough across rolling folds to justify model training or deployment.

## Fold-by-fold result

### Fold 1

```text
train PF / PnL      : 0.9316 / -6.2122  -> train fail
validation PF / PnL : 1.5687 / +10.8298 -> validation pass
test PF / PnL       : 0.7850 / -5.5607  -> test fail
monthly gate        : 0
fold_pass           : 0
```

### Fold 2

```text
train PF / PnL      : 0.9548 / -3.9707  -> train fail
validation PF / PnL : 0.7850 / -5.5607  -> validation fail
test PF / PnL       : 1.3466 / +8.4917  -> test pass
monthly gate        : 0
fold_pass           : 0
```

### Fold 3

```text
train PF / PnL      : 0.8911 / -9.9823  -> train fail
validation PF / PnL : 1.3466 / +8.4917  -> validation pass
test PF / PnL       : 1.1712 / +3.2903  -> test pass
monthly gate        : 0
fold_pass           : 0
```

### Fold 4

```text
train PF / PnL      : 1.1006 / +10.3446 -> train fails monthly ratio
validation PF / PnL : 1.1712 / +3.2903  -> validation pass
test PF / PnL       : 2.0194 / +8.6946  -> test fails trade-count gate, trades=19 < 20
monthly gate        : 0
fold_pass           : 0
```

### Fold 5

```text
train PF / PnL      : 1.1343 / +14.2312 -> train fails monthly ratio
validation PF / PnL : 2.3178 / +9.7925  -> validation fails trade-count gate, trades=18 < 20
test PF / PnL       : 1.4206 / +8.5322  -> test pass
monthly gate        : 0
fold_pass           : 0
```

### Fold 6

```text
train PF / PnL      : 1.2505 / +23.1391 -> train pass
validation PF / PnL : 1.2779 / +5.8590  -> validation fails monthly ratio
test PF / PnL       : 1.7231 / +15.1921 -> test pass
monthly gate        : 0
fold_pass           : 0
```

## Key diagnosis

The locked candidate is not uniformly stable across time.

The most important pattern is:

```text
Test segments are often profitable, but train/validation/monthly stability is not robust enough.
```

This means:

```text
1. The 1H breakout signal exists.
2. The static Phase165A split was too optimistic.
3. The edge is regime-sensitive.
4. Model training now would likely learn a regime-specific artifact.
```

## Stress result

```text
stress_transfer_pass_gate = 0 for all folds
```

At fixed spread 0.5:

```text
train fails in every fold shown, even when test remains positive in several folds.
```

At fixed spread 0.2:

```text
fold transfer still fails because at least one of train/validation/test/monthly gates fails in every fold.
```

## Decision

```text
Phase166A failed.
Do not train a 1H model around this locked candidate yet.
Do not proceed to paper/live/Phase134.
The 1H route remains research-only and must not be promoted.
```

## Recommended next action

Do not optimize this candidate directly with another grid.

Recommended diagnostic only if continuing 1H route:

```text
Phase167A — 1H Locked Candidate Regime / Failure Attribution Audit
```

Purpose:

```text
Identify why fold pass is 0/6 despite 4/6 test splits passing.
```

Questions Phase167A should answer:

```text
1. Are failures concentrated in low-ATR / high spread-to-ATR regimes?
2. Are failures concentrated in specific years/months?
3. Are BUY or SELL legs responsible for instability?
4. Are train failures caused by older low-volatility regimes while recent test improves?
5. Does a pre-declared volatility/liquidity filter explain the fold failures without curve-fitting?
6. Should the 1H route be stopped, or reframed as regime-conditional only?
```

No model training should happen before this attribution is complete.
