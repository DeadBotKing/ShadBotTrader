# Phase138 — Trade Anatomy / TP-SL Failure Analysis

**Status:** ✅ Phase138A implemented
**Type:** Research diagnostic / TP-SL and bracket anatomy
**Production status:** Research-only; no paper/live permission

---

## Why this phase exists

Phase137A manual regime filters did not survive recent holdout:

```text
SELL h8/9 + SL<=23.56 full-history : +23.1475 raw, PF=1.0609
SELL h8/9 + SL<=23.56 recent 15%   : -22.4050 raw, PF=0.4098
```

So the next problem is not another hand filter. The project needs to inspect whether the trade construction itself is broken:

```text
entry
TP distance
SL distance
reward/risk
range 4H / 1D bracket context
stop-loss concentration
BUY vs SELL anatomy
hold time / timeout behavior
```

---

## Implemented file

```text
scripts/analyze_trade_anatomy.py
```

GUI:

```text
Analyze trade anatomy
```

---

## Inputs

```text
datasets\processed\XAUUSD\5M\hybrid_telemetry_flat_latest.parquet
```

---

## Outputs

```text
run_logs\trade_anatomy\latest.json
run_logs\trade_anatomy\latest.html
run_logs\trade_anatomy\latest_anatomy.csv
```

---

## What it analyzes

Core groups:

```text
side
outcome
side_outcome
month
month_side
hour
side_hour
```

Numeric anatomy bins:

```text
tp_distance_bin
sl_distance_bin
reward_risk_bin
hold_bars_bin
side_4h_room_bin
side_1d_room_bin
range_4h_width_bin
range_1d_width_bin
candidate_confidence_bin
candidate_reward_risk_bin
candidate_sl_distance_bin
candidate_tp_distance_bin
```

Each row reports:

```text
rows
buy/sell rows
win rate
total pnl
profit factor
max drawdown
take-profit rate
stop-loss rate
timeout rate
average TP distance
average SL distance
average reward/risk
average hold bars
```

---

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

Send back:

```text
run_logs\trade_anatomy\latest.json
```

Open:

```text
run_logs\trade_anatomy\latest.html
```

---

## Interpretation

This phase does not approve a strategy. It should identify whether the next work must target:

```text
BUY bracket design
SL distance caps
TP placement
range model usage
same-bar policy sensitivity
timeout behavior
or side-specific target/reward construction
```

No Phase134/paper/live is allowed from this diagnostic alone.

---

## Operator result — 2026-09-15

Phase138A was executed on the full candidate telemetry matrix.

Top-level anatomy:

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

Side anatomy:

```text
BUY  rows=8583, total_pnl=-39003.7073, PF=0.5106, stop_loss_rate=59.0703%
SELL rows=5174, total_pnl= -4306.1039, PF=0.8760, stop_loss_rate=42.2497%
```

Worst anatomy:

```text
stop_loss rows=7256, total_pnl=-106988.0392
BUY / stop_loss rows=5070, total_pnl=-75934.2056
SELL / stop_loss rows=2186, total_pnl=-31053.8336
SL distance high bin (23.56,124.647] total_pnl=-22248.0623
2026-02 total_pnl=-21573.3665, stop_loss_rate=66.4267%
```

Key TP/SL insight:

```text
stop-loss candidates:
  avg_tp_distance = 22.5691
  avg_sl_distance = 14.7448
  avg_reward_risk = 2.8001
  avg_hold_bars   = 12.2172

take-profit candidates:
  avg_tp_distance = 13.0167
  avg_sl_distance = 20.5877
  avg_reward_risk = 0.8209
  avg_hold_bars   = 16.2364
```

Conclusion:

```text
The current high nominal reward/risk / far-TP bracket pattern is likely harmful. Stop-losses happen quickly, especially on BUY. The next phase should simulate alternative TP/SL bracket policies rather than continue model/filter tweaking.
```

Recommended next phase:

```text
Phase139A — TP/SL Bracket Recalibration Replay
```
