# Phase140 — Candidate Direction / Counterfactual Entry Audit

**Status:** ✅ Phase140A implemented
**Type:** Research diagnostic / no training
**Production status:** Research-only; no paper/live permission

---

## Why this phase exists

Phase139A proved that simple TP/SL and reward/risk caps do **not** rescue the current candidate stream:

```text
Global bracket grid: failed
SELL-only bracket grid: failed
BUY-only bracket grid: failed
```

The next unanswered question is more basic:

```text
Are the candidate directions wrong or contrarian?
Are entries too early by 1/2/3 bars?
Or is the candidate stream itself no-edge even after flip/delay?
```

Phase140A answers that with counterfactual replay only. It does not train a model.

---

## Implemented file

```text
scripts/audit_candidate_direction_entry.py
```

GUI command:

```text
Audit candidate direction/entry
```

Test file:

```text
tests/unit/ai/test_candidate_direction_entry_audit.py
```

---

## What it audits

For existing Phase127 telemetry candidate rows, the script tests this matrix:

```text
side_mode:
  original  = execute candidate side as stored
  flipped   = BUY candidate executed as SELL, SELL candidate executed as BUY

entry_delay_bars:
  0, 1, 2, 3 by default

execution_mode:
  independent   = every candidate evaluated independently for direction-quality diagnosis
  chronological = one-position-at-a-time replay for executable strategy impact
```

The flipped-side test mirrors the stored TP/SL **distances** around the delayed entry price. This isolates direction/timing from the old absolute 4H range bracket.

---

## Inputs

```text
datasets\processed\XAUUSD\5M\hybrid_telemetry_flat_latest.parquet
5M candles from datasets
```

Required telemetry columns:

```text
timestamp
source_index
candidate_mask
candidate_side or target_side
candidate_entry_price
candidate_take_profit / candidate_stop_loss or candidate_tp_distance / candidate_sl_distance
```

---

## Outputs

```text
run_logs\candidate_direction_entry_audit\latest.json
run_logs\candidate_direction_entry_audit\latest.html
run_logs\candidate_direction_entry_audit\latest.csv
run_logs\candidate_direction_entry_audit\latest_groups.csv
run_logs\candidate_direction_entry_audit\best_chronological_trades.csv
```

`latest.csv` is the scenario matrix.
`latest_groups.csv` contains side/month/session group matrices.
`best_chronological_trades.csv` stores detailed trades for the best chronological scenario.

---

## First recommended command

PowerShell:

```powershell
python -u scripts/audit_candidate_direction_entry.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --flat-path datasets\processed\XAUUSD\5M\hybrid_telemetry_flat_latest.parquet `
  --candidate-only 1 `
  --allowed-sides BUY,SELL `
  --entry-delays 0,1,2,3 `
  --side-modes original,flipped `
  --execution-modes independent,chronological `
  --eval-frac 1.0 `
  --max-windows 0 `
  --max-hold-bars 48 `
  --spread-mode pct `
  --spread-value 0.06 `
  --same-bar-policy stop_first `
  --initial-capital 100 `
  --units 0.1 `
  --storage-root datasets
```

Send back:

```text
run_logs\candidate_direction_entry_audit\latest.json
```

---

## How to interpret results

### If flipped side improves materially

```text
Candidate direction may be inverted/contrarian.
```

Next work should audit target sign, side labeling, and whether BUY/SELL head probabilities are being interpreted incorrectly.

### If entry delay improves materially

```text
Candidate timing may be too early.
```

Next work should audit entry trigger timing, confirmation bars, and whether candidate generation should wait for post-signal confirmation.

### If neither flip nor delay helps

```text
Candidate generation is likely no-edge under the current target/bracket definition.
```

Next work should return to target/candidate definition instead of adding another meta-filter.

---

## BUY policy

BUY is **not** removed from the architecture. Phase140A tests BUY explicitly in two ways:

```text
BUY original
BUY flipped-to-SELL
```

If BUY flipped-to-SELL improves, that is a diagnostic sign of contrarian/inverted BUY candidates, not permission to permanently delete BUY.

---

## Acceptance

Phase140A is accepted if it produces the full counterfactual direction/entry report and GUI command. It does not approve paper/live trading.

Production decision remains:

```text
No Phase134.
No paper shadow.
No live trading.
```

---

## Operator result — Phase140A full direction/entry audit — 2026-09-16

Configuration:

```text
rows evaluated   : 52,832
candidate rows   : 13,757
side_modes       : original, flipped
entry_delays     : 0,1,2,3
execution_modes  : independent, chronological
spread           : pct 0.06
same_bar_policy  : stop_first
```

Top-level result:

```text
best_independent_scenario          : independent:flipped:delay=0
best_independent_total_pnl         : -37,742.8296
best_independent_profit_factor     : 0.6561

best_chronological_scenario        : chronological:original:delay=3
best_chronological_total_pnl       : -3,123.7836
best_chronological_profit_factor   : 0.6512

original_delay0_independent_pnl    : -43,309.8113
flipped_delay0_independent_pnl     : -37,742.8296

original_delay0_chronological_pnl  : -4,590.7972
flipped_delay0_chronological_pnl   : -4,113.8428
```

Scenario matrix, chronological mode:

```text
chronological:original:delay=0  trades=1693  pnl=-4590.7972  PF=0.5787  win=30.2422%
chronological:original:delay=1  trades=1523  pnl=-4245.3885  PF=0.5962  win=30.6632%
chronological:original:delay=2  trades=1393  pnl=-3921.5867  PF=0.5985  win=34.3862%
chronological:original:delay=3  trades=1305  pnl=-3123.7836  PF=0.6512  win=35.4789%

chronological:flipped:delay=0   trades=1612  pnl=-4113.8428  PF=0.6542  win=34.4913%
chronological:flipped:delay=1   trades=1452  pnl=-3793.2209  PF=0.6427  win=35.2617%
chronological:flipped:delay=2   trades=1322  pnl=-3540.6702  PF=0.6396  win=35.1740%
chronological:flipped:delay=3   trades=1291  pnl=-4025.3053  PF=0.5850  win=34.9342%
```

Side-level diagnosis from independent delay=0:

```text
BUY original       : -39,003.7074  PF=0.5106  win=35.7917%
BUY flipped→SELL   : -15,831.0041  PF=0.7545  win=41.1278%
change             : +23,172.7033 raw PnL improvement, but still negative

SELL original      : -4,306.1039   PF=0.8760  win=50.3479%
SELL flipped→BUY   : -21,911.8255  PF=0.5157  win=32.8952%
change             : much worse when flipped
```

Chronological original delay=3 side split:

```text
BUY→BUY    trades=842  pnl=-2765.11  PF=0.562  win=32.2%
SELL→SELL  trades=463  pnl=-358.67   PF=0.864  win=41.5%
```

Important month-side pockets under best chronological scenario:

```text
Best SELL months with original delay=3:
2026-04 / SELL  +161.25  PF=1.810  trades=52
2026-03 / SELL  +154.23  PF=1.598  trades=39
2026-01 / SELL   +75.54  PF=1.901  trades=13
2026-07 / SELL   +57.94  PF=1.156  trades=95
2026-06 / SELL   +12.64  PF=1.064  trades=49

Worst areas with original delay=3:
2026-03 / BUY   -762.21
2026-02 / BUY   -713.07
2026-02 / SELL  -493.87
2025-12 / BUY   -420.50
2026-05 / SELL  -308.69
```

Decision:

```text
FAIL as strategy. Phase140A reduced damage diagnostically but every full scenario remained negative.
```

Engineering interpretation:

```text
1. Global side flip is NOT the solution.
2. BUY candidates are partially contrarian/inverted: BUY→SELL is much less bad than BUY→BUY, but still not profitable.
3. SELL direction is not inverted: SELL→BUY is much worse than SELL→SELL.
4. Entry delay helps materially, especially chronological original delay=3, but still does not create edge.
5. The next useful diagnostic is a side-transform policy grid: BUY original/flip/skip combined with SELL original/flip/skip and side-specific delays, tested chronologically.
```

Production remains blocked:

```text
No Phase134.
No paper shadow.
No live trading.
```
