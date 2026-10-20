# PHASE164A — 1H Spread Unit / Bracket Cost Sensitivity Result

## Status

```text
COMPLETED — 1H route has cost-sensitive positive diagnostics
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
evaluated_configs          : 352
validation_pass_configs    : 244
transfer_pass_configs      : 131
fixed_transfer_pass_configs: 69
pct_transfer_pass_configs  : 62
route_feasible_gate        : 1
```

Phase164A changed the conclusion from Phase163A:

```text
Phase163A: 1H failed under one cost assumption: spread=0.06%, bracket=1.5/1.0.
Phase164A: 1H has many positive validation→test transfer diagnostics when spread unit/bracket are varied.
```

## Important caveat

The script-selected top row is no-spread:

```text
selected_config_id: BRK_D0_MID|breakout|d=0|rw=24|zone=0.1|bracket=B25_125|hold=24|spread_mode=fixed|spread=0
validation PF     : 1.4744696009702762
validation PnL    : +38.81352959768986
test PF           : 1.0845370178384561
test PnL          : +7.788579434364673
```

This is useful as a diagnostic, but it is not tradable by itself because spread is zero.

## Main operational interpretation

Phase164A shows that the Phase163A failure was largely a cost-unit/bracket issue, not proof that 1H has no signal.

Nonzero-cost transfer rows exist under both fixed and percent spread assumptions.

## Fixed-spread diagnostics

The most useful fixed-spread interpretation is that broker spread may be a fixed XAUUSD price distance, not a percent-of-price value.

### Example robust nonzero fixed-spread candidate — BRK_D1_FAST, B15_10, fixed 0.2

```text
config_id: BRK_D1_FAST|breakout|d=1|rw=24|zone=0.05|bracket=B15_10|hold=24|spread_mode=fixed|spread=0.2

train PF       : 1.060733745773545
train PnL      : +11.074247798276177
validation PF  : 1.6359758199652334
validation PnL : +20.318939484345947
test PF        : 1.3548137730296756
test PnL       : +14.379353264011254
validation trades: 61
test trades      : 71
transfer_gate    : 1
```

This row is important because it is:

```text
nonzero spread
train positive
validation positive
test positive
```

### Example fixed-spread tolerance — BRK_D0_WIDE B25_125

Break-even row:

```text
group_id: BRK_D0_WIDE|breakout|0|B25_125|24|fixed
max_transfer_pass_spread      : 1.5
max_both_nonnegative_spread   : 1.5
zero validation PF            : 1.2863553912280237
zero test PF                  : 1.187427361425542
```

Caution:

```text
Some high spread-tolerant rows can have weak/negative train behavior.
Phase165A must add train-stability and monthly-stability gates before any model/trading step.
```

## Percent-spread diagnostics

Percent-spread results also improved versus Phase163A once wider brackets were tested.

Examples from break-even rows:

```text
BRK_D1_FAST|breakout|1|B30_15|24|pct:
  max_transfer_pass_spread = 0.06
  zero validation PF       = 1.3101
  zero test PF             = 1.5367

BRK_D0_MID|breakout|0|B20_10|24|pct:
  max_transfer_pass_spread = 0.03
  zero validation PF       = 1.3395
  zero test PF             = 1.1285
```

This means Phase163A's single bracket was too narrow/pessimistic for percent spread.

Still, percent-spread assumptions should be verified against actual Alpari XAUUSD execution data before trusting them.

## Spread/ATR findings

Fixed spread examples:

```text
fixed spread 0.2:
  train median spread/ATR      = 0.05248
  validation median spread/ATR = 0.03098
  test median spread/ATR       = 0.01257
  spread_feasible_gate         = 1 on all splits

fixed spread 0.5:
  train median spread/ATR      = 0.13121
  validation median spread/ATR = 0.07745
  test median spread/ATR       = 0.03144
  train spread_feasible_gate   = 0, validation/test = 1

pct spread 0.06:
  train median spread/ATR      = 0.27117
  validation median spread/ATR = 0.23577
  test median spread/ATR       = 0.15980
  spread_feasible_gate         = 0
```

Interpretation:

```text
Fixed spread 0.2 looks economically plausible and feasible.
Percent spread 0.06 is still very expensive relative to 1H ATR.
```

## Decision

```text
Phase164A is positive as a diagnostic.
The 1H route should not be rejected.
But it is still not approved for model training/paper/live.
```

Reason:

```text
The current selected row is no-spread.
Nonzero-spread rows exist, but a locked candidate must be selected with explicit train-stability and monthly-stability gates.
Broker spread units still need confirmation.
```

## Recommended next phase

```text
Phase165A — 1H Fixed-Spread Candidate Lockdown / Stability Replay
```

Purpose:

```text
1. Select only nonzero-cost policies.
2. Prefer fixed-spread rows that match Alpari-like XAUUSD cost assumptions.
3. Add train-stability gate.
4. Add monthly stability gate.
5. Lock exactly one replay candidate before any model training.
```

Recommended starting candidate for Phase165A:

```text
policy_key       : BRK_D1_FAST
side_mapping     : breakout
entry_delay      : 1
recent_window    : 24
zone             : 0.05
top              : 0.85
bottom           : 0.15
bracket          : B15_10
TP/SL            : 1.5 / 1.0 ATR
hold_bars        : 24
spread_mode      : fixed
spread_value     : 0.2
```

Why this candidate:

```text
It is nonzero-cost and positive on train, validation, and test in Phase164A.
```

Still no production approval:

```text
No Phase134.
No paper shadow.
No live trading.
```
