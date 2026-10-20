# PHASE162A — Pivot Bottom-Buy Execution Gap Result

## Status

```text
COMPLETED — execution-gap audit failed transfer
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
evaluated_configs       : 16
validation_pass_configs : 4
transfer_pass_configs   : 0
selected_config         : entry_delay=0, same_bar_policy=stop_first, spread_value=0.0
selected_validation_PF  : 1.203013055453164
selected_validation_PnL : +1.9564356399935086
selected_test_PF        : 0.9105459631947063
selected_test_PnL       : -0.5422007496410663
selected_transfer_gate  : 0
```

Interpretation:

```text
No execution configuration transferred from validation to test.
Even the validation-selected no-spread configuration failed confirmation on test.
The realistic spread=0.06 configuration reproduces the Phase161A failure.
```

## Selected validation configuration — no spread

The validation-selected diagnostic row was:

```text
entry_delay_bars  : 0
same_bar_policy   : stop_first
spread_value      : 0.0
```

Validation:

```text
trades       : 28
PF           : 1.203013055453164
cash PnL     : +1.9564356399935086
final        : 101.95643563999353
event mean   : +0.0277777778 ATR
replay mean  : +0.0438892663 ATR
skipped W/L  : 11 / 15
```

Test:

```text
trades       : 20
PF           : 0.9105459631947063
cash PnL     : -0.5422007496410663
final        : 99.45779925035895
event mean   : +0.0773809524 ATR
replay mean  : +0.1108117616 ATR
skipped W/L  : 15 / 7
skipped sum  : +5.0221294762 ATR
executed mean: -0.0184017744 ATR
```

Diagnostic flag:

```text
test skipped winners dominate
average BUY entry gap adverse
```

Meaning:

```text
The independent test opportunities are positive, but chronological single-position execution trades a weaker subset and skips many winners.
```

## Realistic spread=0.06 result

The actual Phase161-style execution row is:

```text
entry_delay_bars  : 0
same_bar_policy   : stop_first or tp_first
spread_value      : 0.06
```

Validation:

```text
trades                    : 30
PF                        : 0.7155627225917369
cash PnL                  : -3.3831902713290325
final                     : 96.61680972867092
event mean                : +0.0277777778 ATR
independent replay mean   : -0.0377218628 ATR
event→replay mean delta   : -0.0654996406 ATR
adjusted gap mean         : +0.0286779611 ATR
adverse adjusted gap rate : 98.1481%
```

Test:

```text
trades                    : 21
PF                        : 0.685300120022801
cash PnL                  : -2.2485716644271294
final                     : 97.75142833557287
event mean                : +0.0773809524 ATR
independent replay mean   : +0.0483602650 ATR
event→replay mean delta   : -0.0290206874 ATR
adjusted gap mean         : +0.0383393041 ATR
adverse adjusted gap rate : 100.0%
skipped W/L               : 12 / 9
executed mean             : -0.0791624950 ATR
```

This confirms the Phase161A replay numbers and identifies why they are negative:

```text
1. Spread turns the BUY entry gap adverse almost always.
2. Spread decays the small event-scoring edge.
3. Single-position chronological execution skips a meaningful share of winners.
4. The executed subset is worse than the independent candidate universe.
```

## Entry-delay sensitivity

No-spread rows:

```text
delay=0: validation pass, test fails
  validation PF=1.2030, test PF=0.9105

delay=1: validation pass, test near-breakeven but fails gate
  validation PF=1.1204, test PF=1.0209, test PnL=+0.1229

delay=2: validation fails, test passes
  validation PF=0.8791, test PF=1.1305

delay=3: validation fails, test fails
  validation PF=0.7569, test PF=0.8337
```

Realistic spread=0.06 rows:

```text
delay=0: validation/test both fail
  validation PF=0.7156, test PF=0.6853

delay=1: validation almost breakeven, test fails badly
  validation PF=0.9969, test PF=0.6235

delay=2: validation/test both fail
  validation PF=0.8352, test PF=0.6960

delay=3: validation/test both fail
  validation PF=0.4990, test PF=0.6122
```

Conclusion:

```text
Entry delay does not provide a robust transferable fix.
No-spread delay=1 is too weak and disappears under realistic spread.
```

## Same-bar policy sensitivity

```text
event_ambiguous = 0 across the shown rows
stop_first rows == tp_first rows for the same delay/spread
```

Conclusion:

```text
Same-bar TP/SL ambiguity is not the failure source in this policy.
```

## Train-split stability check

For the selected no-spread row:

```text
train PF       : 0.8604026818678046
train cash PnL : -4.910946517523243
train event mean: -0.1415441176 ATR
```

For the realistic spread=0.06 row:

```text
train PF       : 0.6669805735738112
train cash PnL : -13.206794724215673
```

Conclusion:

```text
The validation edge is not supported by train stability.
The rule is regime-fragile even before considering production risk.
```

## Decision

```text
Phase162A failed transfer.
No validated execution adjustment rescues the bottom-buy candidate.
Reject strict B2 bottom-buy as a trading candidate under current assumptions.
Do not train a model around this rule.
Do not proceed to Phase134, paper shadow, or live trading.
```

## Recommended next action

```text
Stop the pivot bottom-buy rescue lane.
Do not keep optimizing entry_delay/spread/same_bar_policy on this rule.
```

If the pivot route continues at all, it should restart from a different candidate/target family with walk-forward replay gates from the beginning. The current B2 strict bottom-buy execution rule should not be patched into production logic.
