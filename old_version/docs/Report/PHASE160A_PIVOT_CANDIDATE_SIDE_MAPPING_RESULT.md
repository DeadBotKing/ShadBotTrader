# PHASE160A — Pivot Candidate Side-Mapping Result

## Status

```text
COMPLETED — first positive transfer diagnostic found
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
geometry_policies_loaded      : 2
evaluated_rows                : 64
validation_pass_rows          : 14
transfer_pass_rows            : 3
selected_geometry_policy_id   : B2|fallback|rw=48|zone=0.05|top=0.85|bottom=0.15|exclude_both=1|minw=1|maxw=0
selected_side_mapping         : bottom_buy
selected_entry_delay_bars     : 0
selected_validation_mean_r    : +0.0277777780
selected_test_mean_r          : +0.0773809552
selected_validation_PF        : 1.2
selected_test_PF              : 5.3333
selected_transfer_pass_gate   : 1
```

## Selected policy

```text
target_id              : B2
side_mapping           : bottom_buy
entry_delay_bars       : 0
recent_window_bars     : 48
pivot_zone_atr         : 0.05
top_position_threshold : 0.85
bottom_position        : 0.15
exclude_both_zones     : 1
min_range_width_atr    : 1.0
```

## Validation result

```text
validation_events       : 54
validation_event_rate   : 1.6544%
validation_win_rate     : 16.6667%
validation_mean_r       : +0.0277777780
validation_sum_r        : +1.5
validation_profit_factor: 1.2
validation_pass_gate    : 1
```

## Test result

```text
test_events       : 42
test_event_rate   : 1.2868%
test_win_rate     : 9.5238%
test_mean_r       : +0.0773809552
test_sum_r        : +3.25
test_profit_factor: 5.3333
test_pass_gate    : 1
```

## Interpretation

The broad reversal mapping was not the right interpretation. The first useful signal is narrower:

```text
bottom-zone BUY only
```

This means the useful part of the pivot work is likely not generic top/bottom reversal, but a selective bottom-buy continuation/reversal pocket under tight geometry.

## Caveats

```text
This is not a full backtest.
It is first-hit event scoring.
It does not include spread, cash risk sizing, one-position chronological execution or monthly drawdown.
Sample size is small: 54 validation events, 42 test events.
```

## Decision

```text
Proceed to Phase161A chronological replay of selected bottom_buy policy.
Do not proceed to production/paper/live.
Do not train a model yet.
```

## Recommended Phase161A

```text
Replay policy:
  target_id=B2
  side_mapping=bottom_buy
  entry_delay=0
  recent_window=48
  pivot_zone_atr=0.05
  bottom_position<=0.15
  exclude_both=1
  min_range_width_atr=1.0

Replay assumptions:
  TP=1.0 ATR
  SL=0.75 ATR
  spread=pct 0.06
  same_bar_policy=stop_first
  chronological single-position mode
  train/validation/test reports
```

Production remains blocked.
