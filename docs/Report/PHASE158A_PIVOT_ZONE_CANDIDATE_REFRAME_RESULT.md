# PHASE158A — Pivot-Zone Candidate Reframe Result

## Status

```text
COMPLETED — no candidate reframe pass
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
completed_candidates     : 2
reframe_ready_candidates : 0
best_candidate_id        : B2
best_candidate_reason    : no gate pass; best diagnostic score only
```

## B4 result

Zone event density:

```text
train zone events      : 14824 / 16800 = 88.2381%
validation zone events : 2954 / 3264   = 90.5025%
test zone events       : 2908 / 3264   = 89.0931%
```

Event quality:

```text
validation event_win_rate : 5.3487%
test event_win_rate       : 4.8831%
validation event_mean_r   : -0.0680433
test event_mean_r         : -0.0689477
```

Learnability:

```text
event_validation_ap       : 0.11818
event_test_ap             : 0.05764
event_validation_ap_lift  : +0.06470
event_test_ap_lift        : +0.00880
event_balanced_accuracy   : 0.5 / 0.5
event_validation_f1       : 0.0
event_test_f1             : 0.0
```

Side stability:

```text
validation best side : SELL
  SELL mean R = -0.03014
  BUY mean R  = -0.10114

test best side : BUY
  SELL mean R = -0.08616
  BUY mean R  = -0.05325

side_preference_stable_gate = 0
```

Gate:

```text
enrichment_gate          : 0
event_learnability_gate  : 0
candidate_reframe_gate   : 0
```

## B2 result

Zone event density:

```text
train zone events      : 11117 / 16800 = 66.1726%
validation zone events : 2292 / 3264   = 70.2206%
test zone events       : 2255 / 3264   = 69.0870%
```

Event quality:

```text
validation event_win_rate : 5.9773%
test event_win_rate       : 5.1885%
validation event_mean_r   : -0.0272688
test event_mean_r         : -0.0402439
```

Learnability:

```text
event_validation_ap_lift : +0.05470
event_test_ap_lift       : +0.01048
event_balanced_accuracy  : 0.5 / 0.5
event_f1                 : 0.0 / 0.0
```

Side stability:

```text
validation best side : SELL
test best side       : BUY
side_preference_stable_gate = 0
```

Gate:

```text
candidate_reframe_gate = 0
```

## Interpretation

The current pivot-zone definitions are too broad:

```text
B4 marks about 90% of rows as zone events.
B2 marks about 70% of rows as zone events.
```

Those zones are not enriched:

```text
Event win rate is only around 5%.
Mean R is negative in both validation and test.
```

Side preference is unstable:

```text
Validation is SELL-less-bad.
Test is BUY-less-bad.
```

## Decision

```text
Reject current B4/B2 zone candidate universe for modeling.
Do not train another deep model on this candidate definition.
```

## Recommended next phase

```text
Phase159A — Pivot Candidate Geometry Tightening Audit
```

Suggested grid:

```text
recent_window_bars: 24,48,96
pivot_zone_atr: 0.05,0.10,0.15,0.20,0.25
position top thresholds: 0.85,0.90,0.95
position bottom thresholds: 0.15,0.10,0.05
exclude both-zone rows: 1/0
min recent range width / ATR bins
session/hour breakdown
```

Minimum acceptance before training:

```text
candidate event rate must be meaningfully below 70–90%
validation/test event_mean_r should not be negative
side preference should be more stable
```

Production remains blocked.
