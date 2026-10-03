# PHASE170A — Broker Spread Capture / Cost Data Pipeline Result

## Status

```text
COMPLETED — broker spread sample captured
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
source_mode              : mt5
symbol                   : XAUUSD
broker_symbol            : XAUUSD_i
samples                  : 121
min_samples              : 20
sample_status            : PASS
broker_cost_reality_gate : 1
capture_duration_seconds : 600
interval_seconds         : 5
```

Captured spread:

```text
spread_price_median : 0.3900000000003274
spread_price_p90    : 0.4000000000005457
spread_price_p99    : 0.41000000000058207
spread_points_median: 39.00000000003274
spread_points_p90   : 40.00000000005457
spread_points_p99   : 41.00000000005821
```

Important note:

```text
The capture contained one invalid/placeholder MT5 tick at 1970-01-01 with spread=0.0.
It did not materially affect the median/p90, but the script was patched after this result to ignore invalid MT5 epoch ticks in future captures.
```

The real sampled window was effectively:

```text
session_utc      : london_morning
real rows        : 120
real first sample: 2026-10-01T08:32:17.175000+00:00
real last sample : 2026-10-01T08:42:11.912000+00:00
real median      : 0.39
real p90         : 0.40
real p99         : 0.41
```

## Spread / ATR cost reality

### 5M

```text
atr_median                  : 39.49214285714301
sample_spread_median        : 0.3900000000003274
median_spread_atr_median    : 0.009875382083243615
p90_spread_atr_median       : 0.010128597008460305
p99_spread_atr_median       : 0.010381811933672389
median_spread_atr_p90       : 0.005773073791730104
feasible_gate               : 1
```

### 1H

```text
atr_median                  : 4.672142857142855
sample_spread_median        : 0.3900000000003274
median_spread_atr_median    : 0.08347347500389216
p90_spread_atr_median       : 0.08561382051685738
p99_spread_atr_median       : 0.08775416602978368
median_spread_atr_p90       : 0.027254757103231532
feasible_gate               : 1
```

## Interpretation

The actual sampled broker spread is close to:

```text
fixed spread ≈ 0.39 to 0.41
```

This means:

```text
1. The previous percent-spread assumption of 0.06% was too expensive for 1H.
2. The previous fixed spread=0.2 assumption used by Phase165A was too optimistic.
3. The realistic sampled cost is closer to the Phase165A/166A stress row around fixed spread=0.5.
```

This is critical because Phase165A stress showed:

```text
fixed spread 0.2: transfer passed
fixed spread 0.5: transfer failed because train failed
fixed spread 1.0: transfer failed hard
```

Therefore the real spread sample strengthens the rejection of the current 1H locked-candidate route.

## Decision

```text
Broker cost reality was captured successfully.
Use fixed spread around 0.4, or at least stress against 0.4/0.5, in future research.
Do not revive the rejected 1H locked-candidate route using fixed spread=0.2.
Do not train a model around the rejected 1H locked rule.
```

## Recommended next action

The current pivot locked-rule routes remain rejected.

If research continues, the next route must be a new target/candidate family and must use broker-realistic costs from the start:

```text
fixed spread median ≈ 0.39
fixed spread p90    ≈ 0.40
fixed spread p99    ≈ 0.41
```

Possible next phase:

```text
Phase171A — Research Route Redesign Decision Matrix
```

Purpose:

```text
Choose whether to:
1. design a new broker-cost-aware 1H target family,
2. move to 4H/1D route exploration,
3. return to hybrid/regime-first architecture,
4. pause pivot research.
```

Production remains blocked.
