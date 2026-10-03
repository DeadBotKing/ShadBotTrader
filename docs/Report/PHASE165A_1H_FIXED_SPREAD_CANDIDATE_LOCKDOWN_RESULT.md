# PHASE165A — 1H Fixed-Spread Candidate Lockdown Result

## Status

```text
COMPLETED — locked 1H fixed-spread candidate passed diagnostic gates
Production — BLOCKED
```

No production/paper/live approval:

```text
No Phase134.
No paper shadow.
No live trading.
```

## Locked candidate

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

Mapping meaning:

```text
breakout: top zone -> BUY, bottom zone -> SELL
```

## Top-level result

```text
train_pass_gate       : 1
validation_pass_gate  : 1
test_pass_gate        : 1
transfer_pass_gate    : 1
monthly_stability_gate: 1
lockdown_pass_gate    : 1
```

This is the first strict 1H fixed-spread candidate that passes train, validation, test, and monthly-stability gates.

## Train split

```text
evaluated_rows              : 35000
candidate_events            : 344
candidate_event_rate        : 0.9829%
trades                      : 305
buy_trades / sell_trades    : 178 / 127
wins / losses               : 128 / 177
win_rate                    : 41.9672%
total_cash_pnl              : +11.074247798276177
final_balance               : 111.07424779827605
return_percent              : +11.0742%
profit_factor               : 1.060733745773545
max_drawdown_cash           : 23.520721785388957
take_profits / stop_losses  : 126 / 176
timeouts                    : 3
positive_months             : 36
negative_months             : 36
positive_month_ratio        : 0.50
worst_month_pnl             : -5.4897689726064005
best_month_pnl              : +7.928596411441383
pass_gate                   : 1
```

Train interpretation:

```text
Train passes, but only barely on monthly ratio and PF.
The max drawdown is large versus initial capital, so risk/drawdown must remain a future gate before any deployment conversation.
```

## Validation split

```text
evaluated_rows              : 7476
candidate_events            : 68
candidate_event_rate        : 0.9096%
trades                      : 61
buy_trades / sell_trades    : 45 / 16
wins / losses               : 32 / 29
win_rate                    : 52.4590%
total_cash_pnl              : +20.318939484345947
final_balance               : 120.31893948434596
return_percent              : +20.3189%
profit_factor               : 1.6359758199652334
max_drawdown_cash           : 5.382938511517068
take_profits / stop_losses  : 32 / 29
timeouts                    : 0
positive_months             : 8
negative_months             : 6
positive_month_ratio        : 0.5714285714285714
worst_month_pnl             : -3.262167302850812
best_month_pnl              : +6.136355062500028
pass_gate                   : 1
```

Validation interpretation:

```text
Validation is strong under the locked fixed spread=0.2 candidate.
```

## Test split

```text
evaluated_rows              : 7476
candidate_events            : 82
candidate_event_rate        : 1.0968%
trades                      : 71
buy_trades / sell_trades    : 48 / 23
wins / losses               : 34 / 37
win_rate                    : 47.8873%
total_cash_pnl              : +14.379353264011254
final_balance               : 114.37935326401126
return_percent              : +14.3794%
profit_factor               : 1.3548137730296756
max_drawdown_cash           : 4.691881753934851
take_profits / stop_losses  : 34 / 37
timeouts                    : 0
positive_months             : 8
negative_months             : 8
positive_month_ratio        : 0.50
worst_month_pnl             : -3.5011694037553847
best_month_pnl              : +9.1154243877299
pass_gate                   : 1
```

Test interpretation:

```text
Test passes, but positive_month_ratio is exactly at the 0.50 gate.
This is acceptable for diagnostic lockdown, but not enough for production/paper approval.
```

## Spread-stress result

```text
spread fixed 0.2:
  train PF=1.0607, validation PF=1.6360, test PF=1.3548, transfer=1

spread fixed 0.5:
  train PF=0.8719, validation PF=1.6360, test PF=1.2830, transfer=0

spread fixed 1.0:
  train PF=0.6142, validation PF=1.2564, test PF=1.2151, transfer=0
```

Interpretation:

```text
The locked candidate is viable only around fixed spread=0.2.
It is not robust to fixed spread=0.5 or 1.0 because train stability fails.
Actual Alpari XAUUSD spread/cost must be confirmed before any deployment path.
```

## Key strengths

```text
1. Nonzero spread is used.
2. Train, validation and test all pass.
3. Candidate event rates are low and controlled: ~0.9% to 1.1%.
4. Both BUY and SELL trades occur.
5. Validation/test drawdowns are modest relative to initial capital.
6. Full trade and monthly exports are available.
```

## Key weaknesses / risks

```text
1. Train PF is weak: 1.0607.
2. Train max_drawdown_cash is large: 23.52.
3. Train and test positive_month_ratio are exactly 0.50, not comfortably above it.
4. Spread stress fails above fixed 0.2.
5. The candidate is rule-based and selected from diagnostic grids; it still needs walk-forward/anti-overfit confirmation.
6. No model has been trained or validated around this target yet.
```

## Decision

```text
Phase165A passes as a diagnostic candidate lockdown.
The 1H fixed-spread breakout route is now the leading research lane.
```

But:

```text
This is not a production strategy.
Do not start paper shadow.
Do not start live trading.
Do not run Phase134.
```

## Recommended next phase

```text
Phase166A — 1H Locked Candidate Walk-Forward / Anti-Overfit Replay
```

Purpose:

```text
Confirm that the locked candidate survives rolling/walk-forward evaluation instead of one static train/validation/test split.
```

Recommended Phase166A checks:

```text
1. Rolling windows across 2017-2026.
2. Each fold: train/calibration/test chronological segments.
3. Same locked rule only; no new grid search.
4. Fixed spread=0.2 and stress spread=0.5.
5. Fold-level PF, PnL, max drawdown, monthly stability.
6. Pass if majority folds pass and worst fold drawdown is bounded.
7. No model training yet unless Phase166A passes.
```

If Phase166A passes, then the next phase can design a 1H target/model around this locked rule.

Production remains blocked.
