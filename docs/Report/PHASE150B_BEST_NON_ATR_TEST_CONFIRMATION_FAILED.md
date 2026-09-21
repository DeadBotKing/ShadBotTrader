# Phase150B Result — Best Non-ATR Test Confirmation Failed

## Phase150A best non-ATR test confirmation failed — 2026-09-21

The owner ran the optional diagnostic test confirmation for the best non-ATR validation policy from Phase150A.

Policy:

```text
range_bracket_mode : range_capped
range_fallback     : atr
use_1d_tp_cap      : 0
min_tp_distance    : 0.5
min_sl_distance    : 15
max_tp_atr         : 2.0
max_sl_atr         : 1.25
same_bar_policy    : stop_first
```

Validation rank-16 result was:

```text
validation_final_balance : 106.7675
validation_PF            : 1.1440
validation_maxDD         : 9.7927
```

Test confirmation result:

```text
eval_split        : test
evaluated period  : 2026-07-03 19:35:00+00:00 → 2026-08-06 19:20:00+00:00
trades            : 157
BUY / SELL trades : 50 / 107
wins / losses     : 74 / 83
win_rate          : 47.1338%
final_balance     : 88.0744190317
return_percent    : -11.9255809683%
total_cash_pnl    : -11.9255809683
profit_factor     : 0.8215049757
max_drawdown_cash : 15.8457758848
BUY PnL           : -5.7357534232
SELL PnL          : -6.1898275451
monthly           : 2026-07 -8.6762935082, 2026-08 -3.2492874601
positive_months   : 0
negative_months   : 2
```

Comparison to ATR test for rebuilt raw Option B:

```text
ATR test:
  final_balance : 90.7052
  PF            : 0.8270
  maxDD         : 10.7625

Best non-ATR test:
  final_balance : 88.0744
  PF            : 0.8215
  maxDD         : 15.8458
```

Interpretation:

```text
The best non-ATR validation policy failed test and was slightly worse than ATR test.
This closes the current range-rescue attempt for the rebuilt Option B candidate.
```

Decision:

```text
Reject current range_capped + fallback=atr policy.
Range TP/SL is not a rescue path for this candidate.
No Phase134. No paper shadow. No live trading.
```
