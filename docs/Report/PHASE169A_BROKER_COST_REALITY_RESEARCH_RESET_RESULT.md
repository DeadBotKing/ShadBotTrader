# PHASE169A — Broker Cost Reality + Research Lane Reset Result

## Status

```text
COMPLETED — cost audit useful, route-log evidence missing
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
route_decision             : INSUFFICIENT_ROUTE_EVIDENCE
broker_cost_reality_status : BROKER_SPREAD_SAMPLE_MISSING_OR_UNVERIFIED
recommended_next_phase     : Restore missing phase logs or run confirmation diagnostics
```

Important interpretation:

```text
Phase169A did not find the prior Phase162A–Phase168A run_logs on disk.
Therefore its automatic route-decision table is incomplete.
This does not invalidate the previously pasted Phase162A–Phase168A results.
It only means the run_logs were unavailable to the Phase169A script at runtime.
```

Likely reason:

```text
run_logs are intentionally excluded from project zip snapshots and may not exist in the project copy used for Phase169A.
```

## Dataset health

### 5M

```text
status                  : PASS
rows                    : 53197
first_timestamp         : 2025-11-28 08:50:00+00:00
last_timestamp          : 2026-09-02 10:25:00+00:00
duplicate_timestamps    : 0
nonfinite_ohlc_cells    : 0
invalid_ohlc_rows       : 0
atr_nonpositive_rows    : 0
atr_mean                : 46.51232799110583
atr_median              : 39.49214285714301
atr_p90                 : 67.55500000000004
```

### 1H

```text
status                  : PASS
rows                    : 50000
first_timestamp         : 2017-11-15 21:00:00+00:00
last_timestamp          : 2026-08-17 18:00:00+00:00
duplicate_timestamps    : 0
nonfinite_ohlc_cells    : 0
invalid_ohlc_rows       : 0
atr_nonpositive_rows    : 0
atr_mean                : 6.7840589456959695
atr_median              : 4.672142857142855
atr_p90                 : 14.309428571428583
```

Conclusion:

```text
The 5M and 1H OHLC/ATR datasets are numerically healthy for this audit.
```

## Cost-assumption audit

### 5M cost/ATR

Under the current ATR source used by the audit, all tested spread assumptions were under the median spread/ATR gate:

```text
fixed 0.2 median spread/ATR : 0.005064298504223244
fixed 0.5 median spread/ATR : 0.01266074626055811
fixed 1.0 median spread/ATR : 0.02532149252111622
fixed 2.0 median spread/ATR : 0.05064298504223244
pct 0.06 median spread/ATR  : 0.06858626526637644
```

Caution:

```text
This does not revive the 5M bottom-buy route.
Phase162A rejected that route due to chronological execution, spread/replay edge decay and skipped-winner behavior, not only median spread/ATR burden.
```

### 1H fixed-spread cost/ATR

```text
fixed 0.2 median spread/ATR : 0.0428069102583703  -> feasible_gate=1
fixed 0.5 median spread/ATR : 0.10701727564592575 -> feasible_gate=1
fixed 1.0 median spread/ATR : 0.2140345512918515  -> feasible_gate=0
fixed 1.5 median spread/ATR : 0.32105182693777723 -> feasible_gate=0
fixed 2.0 median spread/ATR : 0.428069102583703   -> feasible_gate=0
```

### 1H percent-spread cost/ATR

```text
pct 0.01 median spread/ATR : 0.041304840192541194 -> feasible_gate=1
pct 0.02 median spread/ATR : 0.08260968038508239  -> feasible_gate=1
pct 0.03 median spread/ATR : 0.12391452057762359  -> feasible_gate=0
pct 0.06 median spread/ATR : 0.24782904115524718  -> feasible_gate=0
```

Conclusion:

```text
For 1H, fixed spread 0.2–0.5 is economically plausible under the configured median spread/ATR gate.
Percent spread 0.06 remains too expensive.
```

## Broker spread sample

```text
status: NOT_PROVIDED
```

This is a blocker for cost-reality certainty:

```text
No real Alpari XAUUSD spread sample was supplied.
Therefore broker cost reality is still unverified.
```

## Phase-source availability

All expected phase logs were missing in this Phase169A run:

```text
Phase162A: MISSING
Phase163A: MISSING
Phase164A: MISSING
Phase165A: MISSING
Phase166A: MISSING
Phase167A: MISSING
Phase168A: MISSING
```

Therefore the automatic route decisions were:

```text
5M pivot bottom-buy            : UNKNOWN
1H locked breakout BRK_D1_FAST : UNKNOWN
1H cost model                  : COST_UNIT_UNRESOLVED
```

Operational note:

```text
The project docs already record the pasted Phase162A–Phase168A results.
Based on those recorded results, the actual research decision remains:
  - 5M bottom-buy route rejected.
  - 1H locked-candidate route rejected after Phase168A.
```

## Decision

From this Phase169A run alone:

```text
Automatic route reset could not be completed because the run_logs were missing.
Broker cost assumptions were audited successfully.
Broker spread reality remains unverified because no broker spread sample was provided.
```

From the full recorded project evidence:

```text
Stop current 5M and 1H locked pivot routes.
Do not train a model on these rejected rules.
Do not run paper/live/Phase134.
```

## Recommended next action

Two safe options exist:

### Option 1 — Cost reality first

```text
Phase170A — Broker Spread Capture / Cost Data Pipeline
```

Purpose:

```text
Collect real Alpari XAUUSD bid/ask or spread samples by session, then re-run cost assumptions using actual broker spread data.
```

### Option 2 — Research redesign pause

```text
Stop the pivot rule-rescue lane and return to broader target/model-family design.
```

Recommended immediate next step:

```text
Phase170A broker spread capture is the cleanest next diagnostic if the owner wants to continue trading-research work.
```
