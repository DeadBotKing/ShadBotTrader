# Phase139A Report — TP/SL Bracket Recalibration Replay

Date: 2026-09-15

## Goal

Replay alternative TP/SL bracket policies on existing hybrid candidates after Phase138A showed that far TP / high nominal reward-risk candidates often hit SL quickly.

## Implemented files

```text
scripts/backtest_bracket_recalibration.py
tests/unit/ai/test_bracket_recalibration.py
```

GUI:

```text
Backtest bracket recalibration
```

## Inputs

```text
datasets\processed\XAUUSD\5M\hybrid_telemetry_flat_latest.parquet
5M candles from datasets
```

## Outputs

```text
run_logs\bracket_recalibration\latest.json
run_logs\bracket_recalibration\latest.html
run_logs\bracket_recalibration\latest.csv
run_logs\bracket_recalibration\best_trades.csv
```

## First command

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

## Acceptance of this phase

Accepted if it produces an honest bracket-policy grid and best-policy replay. It does not approve paper/live trading.

## Operator result — global TP/SL/RR cap grid — 2026-09-15

Configuration:

```text
allowed_sides      : BUY,SELL
max_tp_distances   : original,12,14,16,18
max_sl_distances   : original,20,23.56,30
max_reward_risks   : original,1,1.5,2
eval_frac          : 1.0
```

Best policy:

```text
tp=original:sl=original:rr=original
```

Best metrics:

```text
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

Conclusion:

```text
Global TP/SL/RR caps failed. Original bracket was only least-bad; it is still completely unacceptable. The result suggests that candidate quality and side-specific bracket behavior, not a simple global cap, are the next things to isolate.
```

## Operator side-specific results — 2026-09-15

### SELL-only

Best policy:

```text
tp=14:sl=original:rr=original
```

```text
trades        : 633
wins/losses   : 262 / 371
win_rate      : 41.3902%
total_pnl     : -664.0531247957406
profit_factor : 0.7939690496760271
max_drawdown  : 846.2230220278584
```

SELL result improved from original SELL-only but remained negative:

```text
original SELL-only : -848.8387 PF=0.7291
best SELL policy   : -664.0531 PF=0.7940
```

### BUY-only

Best policy:

```text
tp=original:sl=16:rr=original
```

```text
trades        : 1253
wins/losses   : 305 / 948
win_rate      : 24.3416%
total_pnl     : -3667.8429958516326
profit_factor : 0.5476443218994678
max_drawdown  : 3668.8183342898155
```

BUY result improved only slightly and every month remained negative.

## Conclusion

```text
Phase139A failed. Neither global nor side-specific TP/SL cap grids created a tradeable policy. The next problem to audit is candidate direction and entry quality, including counterfactual side flipping and entry-delay tests.
```
