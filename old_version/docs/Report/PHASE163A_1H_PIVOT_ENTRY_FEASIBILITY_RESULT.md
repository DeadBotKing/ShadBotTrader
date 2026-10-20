# PHASE163A — 1H Pivot Entry Feasibility Result

## Status

```text
COMPLETED — 1H route not feasible under current spread assumption
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
flat_rows                : 50000
train_rows               : 35000
validation_rows          : 7476
test_rows                : 7476
replay_policy_rows       : 1152
selection_rows           : 384
validation_pass_configs  : 0  # realistic spread=0.06 selection pool
transfer_pass_configs    : 0  # realistic spread=0.06 selection pool
spread_feasible_gate     : 0
route_feasible_gate      : 0
```

Selected realistic-spread row:

```text
policy_id        : 1H|breakout|d=1|rw=48|zone=0.05|top=0.85|bottom=0.15|ex=1|minw=1|maxw=0|spread=0.06
side_mapping     : breakout
entry_delay_bars : 1
validation PF    : 0.9875648654547112
validation PnL   : -0.37308487550487257
test PF          : 0.9567436757286336
test PnL         : -1.3693540267499014
transfer_gate    : 0
```

Decision:

```text
Under the current spread assumption of 0.06%, the 1H pivot-entry route is not feasible.
Do not train a 1H model yet.
```

## Data health

Data integrity is numerically acceptable:

```text
duplicate_timestamps  : 0 on train/validation/test
missing_timestamp_rows: 0 on train/validation/test
nonfinite_ohlc_cells  : 0 on train/validation/test
invalid_ohlc_rows     : 0 on train/validation/test
atr_nonpositive_rows  : 0 on train/validation/test
```

Gap counts exist:

```text
train gap_count      : 1594, max_gap_minutes=5100
validation gap_count : 334,  max_gap_minutes=4500
test gap_count       : 326,  max_gap_minutes=4440
```

Interpretation:

```text
The OHLC/ATR data are usable, but the 1H series has many timestamp gaps, likely market closures/weekends/session gaps. This is not the immediate failure source, but any future 1H phase should remain gap-aware.
```

## Spread / ATR economics

The realistic spread assumption used by Phase163A was:

```text
spread_mode  : pct
spread_value : 0.06
```

Median full spread as ATR fraction:

```text
train      : 0.27117005195240595 ATR
validation : 0.2357716197367245 ATR
test       : 0.1597977693295558 ATR
```

P90 full spread as ATR fraction:

```text
train      : 0.42380219774830835 ATR
validation : 0.35341069330758007 ATR
test       : 0.2601080059217672 ATR
```

Configured feasibility gate:

```text
max_median_spread_atr = 0.12
spread_feasible_gate  = 0
```

Interpretation:

```text
At spread=0.06%, transaction cost is too large relative to 1H ATR, especially on train/validation.
This is the main reason the realistic-spread route fails, even though no-spread diagnostics show raw signal.
```

## No-spread diagnostic signal

No-spread rows are not tradable assumptions, but they are useful diagnostics.
They show that raw 1H pivot/breakout structure has some signal before costs.

Example no-spread transfer rows:

### Breakout d=0, rw=24, zone=0.10

```text
validation PF  : 1.3403610745876438
validation PnL : +28.18914699920569
validation trades: 142

test PF        : 1.0886539671325153
test PnL       : +7.643397584771455
test trades    : 149
transfer_gate  : 1

train PF       : 0.948040866829925
train PnL      : -17.797186798022572
```

### Breakout d=1, rw=24, zone=0.05

```text
validation PF  : 1.5772321533174247
validation PnL : +19.115750089502573
validation trades: 62

test PF        : 1.3548137730296768
test PnL       : +14.379353264011286
test trades    : 71
transfer_gate  : 1

train PF       : 1.1106543920983
train PnL      : +20.41774199451542
```

### Bottom-buy d=1, rw=24, zone=0.15

```text
validation PF  : 1.2125164553074468
validation PnL : +6.9476530713597935
validation trades: 58

test PF        : 1.0584522410737751
test PnL       : +2.484795906189478
test trades    : 72
transfer_gate  : 1

train PF       : 1.0014499976858806
train PnL      : +0.2821249717520323
```

Interpretation:

```text
1H raw pivot/breakout structure may contain usable signal.
But it is not usable under the current spread=0.06% assumption.
```

## Realistic spread result

Best selected realistic-spread row:

```text
mapping    : breakout
entry_delay: 1
rw         : 48
zone       : 0.05
spread     : 0.06%
```

Metrics:

```text
train PF       : 0.5800641051056957
train PnL      : -48.7582224190154
validation PF  : 0.9875648654547112
validation PnL : -0.37308487550487257
test PF        : 0.9567436757286336
test PnL       : -1.3693540267499014
```

This row is not tradable and not training-ready.

## Key conclusion

Phase163A does **not** say that 1H is useless.

It says:

```text
1H raw signal exists in no-spread diagnostics.
But with spread modeled as 0.06% of price, the cost/ATR burden is too high and no realistic-spread config transfers.
```

Therefore the immediate blocker is now:

```text
broker spread/cost calibration and bracket-cost sensitivity
```

not model architecture.

## Decision

```text
Do not train a 1H pivot model yet.
Do not approve paper/live.
Do not continue with 5M bottom-buy rescue.
```

## Recommended next diagnostic

```text
Phase164A — 1H Spread Unit / Bracket Cost Sensitivity Audit
```

Purpose:

```text
Verify whether spread=0.06% is the correct Alpari XAUUSD execution-cost assumption.
Audit fixed spread values and percent spread values.
Compute break-even spread threshold for the no-spread-positive 1H policies.
Audit whether wider 1H brackets can survive realistic spread without overfitting.
```

Candidate grids for Phase164A:

```text
spread_mode=fixed:
  spread_values = 0,0.2,0.5,1.0,1.5,2.0

spread_mode=pct:
  spread_values = 0,0.01,0.02,0.03,0.06

bracket grid:
  tp/sl = 1.5/1.0, 2.0/1.0, 2.5/1.25, 3.0/1.5

hold_bars:
  24,48
```

If actual Alpari spread is closer to a fixed dollar amount than 0.06% of price, Phase163A may be overly pessimistic. This must be checked before accepting or rejecting the 1H route.
