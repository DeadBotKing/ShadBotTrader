# PHASE159A — Pivot Candidate Geometry Tightening Result

## Status

```text
COMPLETED — no validation/test transfer pass
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
policies                 : 1620
validation_pass_policies : 0
transfer_pass_policies   : 0
selected_policy_id       : B2|rw=48|zone=0.05|top=0.85|bottom=0.15|exclude_both=1|minw=1|maxw=0
selected_target_id       : B2
selected_validation_mean_r : -0.0050505050
selected_test_mean_r       : -0.0272277221
selected_validation_PF     : 0.9629629630
selected_test_PF           : 0.7179487179
selected_transfer_pass_gate: 0
```

## Selected policy

```text
target_id              : B2
lookahead_bars         : 24
tp_atr                 : 1.0
sl_atr                 : 0.75
recent_window_bars     : 48
pivot_zone_atr         : 0.05
top_position_threshold : 0.85
bottom_position_threshold : 0.15
exclude_both_zones     : 1
min_range_width_atr    : 1.0
max_range_width_atr    : off
```

## Validation metrics

```text
event_count       : 99
event_rate        : 3.0331%
win_rate          : 13.1313%
mean_r            : -0.0050505050
sum_r             : -0.5
profit_factor     : 0.962963
best_side         : BUY
```

## Test metrics

```text
event_count       : 101
event_rate        : 3.0944%
win_rate          : 6.9307%
mean_r            : -0.0272277221
sum_r             : -2.75
profit_factor     : 0.717949
best_side         : BUY
```

## What improved

Candidate density was fixed:

```text
Phase158A B2 validation/test zone-event rate: ~70.22% / 69.09%
Phase159A selected validation/test event rate: ~3.03% / 3.09%
```

Side preference was stable:

```text
validation_best_side : BUY
test_best_side       : BUY
side_preference_stable_gate = 1
event_mean_r_sign_flip      = 0
```

## What failed

Expectancy is still negative:

```text
validation_mean_r < 0
test_mean_r < 0
validation_pass_gate = 0
test_pass_gate       = 0
transfer_pass_gate   = 0
```

## Interpretation

Phase159A successfully made the candidate geometry selective, but the selected candidate universe is still not positive-expectancy under the current reversal-style mapping.

The route is not ready for model training.

## Decision

```text
Do not train on the selected geometry.
Do not proceed to production/paper/live.
```

## Recommended next phase

```text
Phase160A — Pivot Candidate Side-Mapping / Counterfactual Direction Audit
```

Purpose:

```text
Test whether the tightened pivot candidates should be mapped differently:
  reversal: top→SELL, bottom→BUY
  breakout: top→BUY, bottom→SELL
  top-only / bottom-only
  validation-selected side confirmed on test
  optional entry delays
```

Production remains blocked.
