# Phase138A Report — Trade Anatomy / TP-SL Failure Analysis

Date: 2026-09-14

## Goal

Diagnose why hybrid candidates keep failing after model, meta-filter, tensor, no-trade gate and manual-regime tests.

Phase138A focuses on the trade construction layer:

```text
entry
TP
SL
reward/risk
4H/1D range context
hold bars
outcome type
BUY/SELL asymmetry
```

## Implemented files

```text
scripts/analyze_trade_anatomy.py
tests/unit/ai/test_trade_anatomy.py
```

GUI:

```text
Analyze trade anatomy
```

## Inputs

```text
datasets\processed\XAUUSD\5M\hybrid_telemetry_flat_latest.parquet
```

## Outputs

```text
run_logs\trade_anatomy\latest.json
run_logs\trade_anatomy\latest.html
run_logs\trade_anatomy\latest_anatomy.csv
```

## First command

```powershell
python -u scripts/analyze_trade_anatomy.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --flat-path datasets\processed\XAUUSD\5M\hybrid_telemetry_flat_latest.parquet `
  --candidate-only 1 `
  --allowed-sides BUY,SELL `
  --min-group-rows 20 `
  --quantile-bins 5 `
  --top-n 15 `
  --storage-root datasets
```

## Acceptance of this phase

Phase138A is accepted if it generates the anatomy report and exposes actionable TP/SL/bracket hypotheses. It is not a trading-strategy pass.

## Operator result — 2026-09-15

Top-level result:

```text
candidate_rows : 13757
total_pnl      : -43309.811259036884
win_rate       : 41.2663%
profit_factor  : 0.6215092452270718
max_drawdown   : 45887.01167863794
take_profit    : 37.3846%
stop_loss      : 52.7441%
timeout        : 9.8713%
```

Side result:

```text
BUY:
  rows            : 8583
  total_pnl       : -39003.70734734554
  PF              : 0.5106436955011304
  stop_loss_rate  : 59.0703%
  avg_sl_distance : 17.6224

SELL:
  rows            : 5174
  total_pnl       : -4306.103911691345
  PF              : 0.8759889582324059
  stop_loss_rate  : 42.2497%
  avg_sl_distance : 17.5396
```

Most important finding:

```text
Stop-loss candidates carry higher nominal reward/risk and farther TP than take-profit candidates.
```

```text
stop_loss: avg_tp_distance=22.5691, avg_sl_distance=14.7448, avg_reward_risk=2.8001, avg_hold_bars=12.2172
take_profit: avg_tp_distance=13.0167, avg_sl_distance=20.5877, avg_reward_risk=0.8209, avg_hold_bars=16.2364
```

Interpretation:

```text
The current bracket policy appears to produce too many far-TP / high nominal RR candidates that hit SL quickly. This explains why reward/risk filters did not save Phase137A. The next work should simulate alternative TP/SL policies.
```
