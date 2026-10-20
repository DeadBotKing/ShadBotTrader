# Phase137A Report — Regime-Filtered Hybrid Replay

Date: 2026-09-14

## Goal

Turn Phase136A hypotheses into executable, live-safe replay tests without permanently deleting BUY.

## Implemented file

```text
scripts/backtest_regime_filtered_hybrid.py
```

GUI:

```text
Backtest regime-filtered hybrid
```

## Core principle

BUY is not removed from the architecture. Phase137A supports:

```text
BUY,SELL mixed filters
SELL-only diagnostic filters
BUY-only diagnostic filters
strict-BUY mixed filters
```

The default is:

```text
allowed_sides = BUY,SELL
```

## Output files

```text
run_logs\regime_filtered_hybrid\latest.json
run_logs\regime_filtered_hybrid\latest.html
run_logs\regime_filtered_hybrid\latest.csv
```

## Recommended first tests

1. SELL-only diagnostic replay:

```powershell
python -u scripts/backtest_regime_filtered_hybrid.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --flat-path datasets\processed\XAUUSD\5M\hybrid_telemetry_flat_latest.parquet `
  --eval-frac 1.0 `
  --allowed-sides SELL `
  --initial-capital 100 `
  --units 0.1 `
  --storage-root datasets
```

2. Mixed replay with stricter BUY gates:

```powershell
python -u scripts/backtest_regime_filtered_hybrid.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --flat-path datasets\processed\XAUUSD\5M\hybrid_telemetry_flat_latest.parquet `
  --eval-frac 1.0 `
  --allowed-sides BUY,SELL `
  --buy-min-confidence 0.98 `
  --buy-min-side-4h-room 5 `
  --buy-min-side-1d-room 10 `
  --buy-max-sl-distance 20 `
  --initial-capital 100 `
  --units 0.1 `
  --storage-root datasets
```

## Acceptance

This phase is accepted if it produces honest base-vs-filtered replay JSON/HTML/CSV.

It does not approve production. Promising filters must be validated by future walk-forward logic.

## Operator results — initial Phase137A diagnostics — 2026-09-14

### SELL-only replay

```text
allowed_sides          : SELL
kept_candidates        : 5174 / 13757
filtered_trades        : 581
filtered_total_pnl     : -848.8386568725109
filtered_profit_factor : 0.7290926647116155
filtered_max_drawdown  : 1040.8391872644424
filtered_final_balance : 15.116134312748898
```

Conclusion:

```text
SELL-only improves over the full base replay but remains strongly negative. It is not deployable.
```

### Mixed strict-BUY replay

```text
allowed_sides          : BUY,SELL
buy_min_confidence     : 0.98
buy_min_side_4h_room   : 5
buy_min_side_1d_room   : 10
buy_max_sl_distance    : 20
kept_candidates        : 6360 / 13757
filtered_trades        : 883
filtered_total_pnl     : -2018.1994965970516
filtered_profit_factor : 0.585046282276268
filtered_final_balance : -101.81994965970517
```

Conclusion:

```text
The initial strict-BUY filter did not fix BUY. BUY is not deleted from the project, but it cannot be allowed under this simple gate.
```

## Operator result — SELL hours 8/9 — 2026-09-14

Configuration:

```text
allowed_sides      : SELL
sell_allowed_hours : 8,9
```

Result:

```text
kept_candidates        : 583 / 13757
filtered_trades        : 77
filtered_total_pnl     : +16.920441061258316
filtered_profit_factor : 1.037288325923403
filtered_max_drawdown  : 89.34972810745239
filtered_final_balance : 101.69204410612583
```

Conclusion:

```text
This is the first Phase137A manual regime replay that is positive, but it is too weak for acceptance. The next diagnostic should keep SELL h8/9 and add live-safe loss-control filters such as max SL distance and range width constraints.
```

## Operator result — SELL h8/9 + SL distance cap — 2026-09-14

Configuration:

```text
allowed_sides        : SELL
sell_allowed_hours   : 8,9
sell_max_sl_distance : 23.56
```

Result:

```text
kept_candidates        : 503 / 13757
filtered_trades        : 73
filtered_total_pnl     : +23.147499471902847
filtered_profit_factor : 1.0608648649692447
filtered_max_drawdown  : 89.64815473556519
filtered_final_balance : 102.31474994719028
```

Conclusion:

```text
The SL cap improves the weak-positive SELL h8/9 replay, but not enough. PF is still below 1.10 and the result is not accepted. Continue with live-safe range-width filters.
```

## Operator result — SELL h8/9 + SL cap + broad 4H width cap — 2026-09-14

Configuration:

```text
allowed_sides        : SELL
sell_allowed_hours   : 8,9
sell_max_sl_distance : 23.56
max_range_4h_width   : 33.305
```

Result:

```text
kept_candidates        : 428 / 13757
filtered_trades        : 50
filtered_total_pnl     : -26.330932468175888
filtered_profit_factor : 0.8915300951853891
filtered_max_drawdown  : 89.88325047492981
filtered_final_balance : 97.3669067531824
```

Conclusion:

```text
Rejected. The broad 4H width cap worsened the current best weak-positive filter. Continue diagnostics with exact width pockets rather than broad caps.
```

## Operator result — SELL h8/9 + SL cap + exact 4H pocket — 2026-09-14

Configuration:

```text
allowed_sides        : SELL
sell_allowed_hours   : 8,9
sell_max_sl_distance : 23.56
min_range_4h_width   : 21.741
max_range_4h_width   : 26.928
```

Result:

```text
kept_candidates        : 166 / 13757
filtered_trades        : 14
filtered_total_pnl     : +11.376214891672134
filtered_profit_factor : 1.1828907946231388
filtered_max_drawdown  : 19.283453941345215
filtered_final_balance : 101.13762148916722
```

Conclusion:

```text
The exact 4H pocket improves quality and lowers drawdown, but sample size is too small. This is not accepted until recent-holdout and walk-forward validation pass.
```

## Operator result — exact 4H pocket recent holdout — 2026-09-14

Configuration:

```text
allowed_sides        : SELL
sell_allowed_hours   : 8,9
sell_max_sl_distance : 23.56
min_range_4h_width   : 21.741
max_range_4h_width   : 26.928
eval_frac            : 0.15
```

Result:

```text
kept_candidates        : 70 / 1445 recent candidates
filtered_trades        : 4
filtered_total_pnl     : -17.275230020284653
filtered_profit_factor : 0.11992036742639664
filtered_max_drawdown  : 19.283453941345215
```

Conclusion:

```text
The exact 4H pocket is rejected as a robust filter because it failed recent holdout.
```

## Operator result — current-best SELL filter recent holdout — 2026-09-14

Configuration:

```text
allowed_sides        : SELL
sell_allowed_hours   : 8,9
sell_max_sl_distance : 23.56
eval_frac            : 0.15
```

Result:

```text
kept_candidates        : 104 / 1445 recent candidates
filtered_trades        : 8
filtered_total_pnl     : -22.4049571454525
filtered_profit_factor : 0.40983705655862596
filtered_max_drawdown  : 37.618305921554565
```

Conclusion:

```text
The current-best manual SELL filter failed recent holdout. Manual filter search should pause; the next step should diagnose TP/SL and BUY-side loss anatomy.
```
