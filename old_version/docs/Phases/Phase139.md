# Phase139 — TP/SL Bracket Recalibration Replay

**Status:** ✅ Phase139A implemented
**Type:** Research replay / TP-SL geometry recalibration
**Production status:** Research-only; no paper/live permission

---

## Why this phase exists

Phase138A showed that the current bracket geometry is likely harmful:

```text
stop_loss_rate = 52.7441%
BUY / stop_loss total_pnl = -75934.2056
stop-loss candidates avg_tp_distance = 22.5691
stop-loss candidates avg_reward_risk = 2.8001
take-profit candidates avg_tp_distance = 13.0167
take-profit candidates avg_reward_risk = 0.8209
```

High nominal reward/risk and far TP are not acting as quality signals. They are often associated with quick stop-losses.

Phase139A therefore re-simulates alternative TP/SL policies on the existing candidate stream without training a new model.

---

## Implemented file

```text
scripts/backtest_bracket_recalibration.py
```

GUI:

```text
Backtest bracket recalibration
```

---

## What it does

For every candidate row, the script starts from the stored candidate entry and original TP/SL distances, then applies optional caps:

```text
max TP distance
max SL distance
max reward/risk
BUY-specific max TP/SL/RR overrides
SELL-specific max TP/SL/RR overrides
```

Then it replays the modified bracket on real 5M candles with chronological single-position logic.

---

## Important interpretation

This is not a model-training phase. It tests execution geometry:

```text
If recalibrated brackets improve replay, the current execution geometry is part of the edge problem.
If recalibrated brackets fail, direction/entry/candidate quality is still insufficient.
```

---

## Outputs

```text
run_logs\bracket_recalibration\latest.json
run_logs\bracket_recalibration\latest.html
run_logs\bracket_recalibration\latest.csv
run_logs\bracket_recalibration\best_trades.csv
```

---

## First recommended command

```powershell
python -u scripts/backtest_bracket_recalibration.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --flat-path datasets\processed\XAUUSD\5M\hybrid_telemetry_flat_latest.parquet `
  --eval-frac 1.0 `
  --max-windows 0 `
  --allowed-sides BUY,SELL `
  --max-tp-distances original,12,14,16,18 `
  --max-sl-distances original,20,23.56,30 `
  --max-reward-risks original,1.0,1.5,2.0 `
  --min-trades 10 `
  --score-metric total_pnl `
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
run_logs\bracket_recalibration\latest.json
```

---

## BUY is not deleted

Phase139A supports side-specific overrides. BUY remains testable:

```text
--allowed-sides BUY,SELL
--buy-max-tp-distance 14
--buy-max-sl-distance 20
--buy-max-reward-risk 1.0
```

SELL can also be recalibrated separately:

```text
--sell-max-tp-distance 14
--sell-max-sl-distance 23.56
--sell-max-reward-risk 1.5
```

---

## Acceptance

Phase139A itself is diagnostic. Any promising policy still requires recent-holdout and walk-forward validation before Phase134.

---

## Operator global bracket-grid result — 2026-09-15

Configuration:

```text
allowed_sides    : BUY,SELL
max_tp_distances : original,12,14,16,18
max_sl_distances : original,20,23.56,30
max_reward_risks : original,1,1.5,2
eval_frac        : 1.0
```

Best policy:

```text
policy            : tp=original:sl=original:rr=original
trades            : 1693
buy/sell          : 1118 / 575
wins/losses       : 512 / 1181
win_rate          : 30.2422%
total_pnl         : -4590.797210656048
profit_factor     : 0.5787103197097719
max_drawdown      : 4590.797210656047
final_balance     : -359.0797210656049
would_breach_zero : true
```

Decision:

```text
FAIL. The global TP/SL/RR cap grid did not improve the original bracket. Original was selected only because it was the least-bad policy, not because it is acceptable.
```

Engineering implication:

```text
Naive global bracket caps are not enough. The next diagnostic, if continuing Phase139, should isolate SELL-only and BUY-only bracket recalibration grids. If side-specific grids also fail, the project should move away from bracket tweaking and back to candidate-generation / target-definition rework.
```

---

## Operator side-specific bracket grid results — 2026-09-15

### SELL-only grid

Best policy:

```text
tp=14:sl=original:rr=original
```

Metrics:

```text
trades            : 633
wins/losses       : 262 / 371
win_rate          : 41.3902%
total_pnl         : -664.0531247957406
profit_factor     : 0.7939690496760271
max_drawdown      : 846.2230220278584
final_balance     : 33.594687520425936
```

Comparison:

```text
original SELL-only : -848.8387 PF=0.7291
best SELL policy   : -664.0531 PF=0.7940
```

Decision:

```text
SELL improved but still failed. Bracket caps do not make SELL deployable.
```

### BUY-only grid

Best policy:

```text
tp=original:sl=16:rr=original
```

Metrics:

```text
trades            : 1253
wins/losses       : 305 / 948
win_rate          : 24.3416%
total_pnl         : -3667.8429958516326
profit_factor     : 0.5476443218994678
max_drawdown      : 3668.8183342898155
final_balance     : -266.7842995851633
```

Comparison:

```text
original BUY-only : -3838.3925 PF=0.5142
best BUY policy   : -3667.8430 PF=0.5476
```

Decision:

```text
BUY remains structurally untradeable under the tested bracket caps. BUY is not removed from the project, but it needs candidate-generation/entry-direction rework.
```

Overall Phase139A decision:

```text
FAIL. Global and side-specific bracket caps do not create a profitable edge. Next diagnostic should audit candidate direction and counterfactual entries rather than continue simple TP/SL cap grids.
```
