# PHASE161A — Pivot Bottom-Buy Chronological Replay Result

## Status

```text
COMPLETED — replay failed transfer
Production — BLOCKED
```

No production/paper/live approval:

```text
No Phase134.
No paper shadow.
No live trading.
```

## Policy replayed

```text
target_id              : B2
side_mapping           : bottom_buy
recent_window_bars     : 48
pivot_zone_atr         : 0.05
top_position_threshold : 0.85
bottom_position        : 0.15
exclude_both_zones     : 1
min_range_width_atr    : 1.0
max_range_width_atr    : 0.0
entry_delay_bars       : 0
tp_atr                 : 1.0
sl_atr                 : 0.75
spread_mode            : pct
spread_value           : 0.06
same_bar_policy        : stop_first
initial_capital        : 100
risk_per_trade         : 0.01
```

## Top-level result

```text
validation_pass_gate : 0
test_pass_gate       : 0
transfer_pass_gate   : 0
```

## Train split

```text
evaluated_rows     : 16800
candidate_rows     : 136
candidate_rate     : 0.8095%
trades             : 84
wins / losses      : 35 / 49
win_rate           : 41.6667%
total_cash_pnl     : -13.2068
final_balance      : 86.7932
return_percent     : -13.2068%
profit_factor      : 0.6670
max_drawdown_cash  : 14.9216
take_profits       : 13
stop_losses        : 37
timeouts           : 34
skipped_while_open : 52
positive_months    : 2
negative_months    : 4
```

## Validation split

```text
evaluated_rows     : 3264
candidate_rows     : 54
candidate_rate     : 1.6544%
trades             : 30
wins / losses      : 13 / 17
win_rate           : 43.3333%
total_cash_pnl     : -3.3832
final_balance      : 96.6168
return_percent     : -3.3832%
profit_factor      : 0.7156
max_drawdown_cash  : 5.9745
take_profits       : 4
stop_losses        : 11
timeouts           : 15
skipped_while_open : 24
monthly_pnl        : 2026-06 -3.2919, 2026-07 -0.0913
```

## Test split

```text
evaluated_rows     : 3264
candidate_rows     : 42
candidate_rate     : 1.2868%
trades             : 21
wins / losses      : 10 / 11
win_rate           : 47.6190%
total_cash_pnl     : -2.2486
final_balance      : 97.7514
return_percent     : -2.2486%
profit_factor      : 0.6853
max_drawdown_cash  : 2.7327
take_profits       : 3
stop_losses        : 5
timeouts           : 13
skipped_while_open : 21
monthly_pnl        : 2026-07 -2.7248, 2026-08 +0.4762
```

## Interpretation

Phase160A event scoring was positive, but Phase161A realistic replay was negative.

The selected bottom-buy rule does not survive:

```text
next-bar entry
spread
risk sizing
single-position chronological execution
monthly replay
```

## Decision

```text
Reject the selected strict bottom-buy rule as a trading candidate under current replay assumptions.
Do not proceed to Phase134/paper/live.
```

## Recommended next diagnostic

```text
Phase162A — Pivot Bottom-Buy Execution Gap / Entry Timing Audit
```

Questions Phase162A should answer:

```text
1. How much edge disappears from candidate close to next open entry?
2. How much is spread cost?
3. How much is lost due to skipped_while_open events?
4. Are event winners being skipped during open trades?
5. Does entry_delay improve chronological replay or only event scoring?
6. Is same_bar_policy sensitivity material?
```

Production remains blocked.
