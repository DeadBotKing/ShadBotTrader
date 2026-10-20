# Phase137 — Regime-Filtered Hybrid Replay

**Status:** ✅ Phase137A implemented
**Type:** Research replay / live-safe rule filtering
**Production status:** Research-only; no paper/live permission

---

## Why this phase exists

Phase136A showed that the current hybrid candidate stream is structurally damaged by BUY candidates:

```text
BUY total_pnl  : -39003.7073
SELL total_pnl :  -4306.10
```

But this does **not** mean BUY is removed from the project. It means BUY must be tested separately and probably gated more strictly.

Phase137A exists to test hypotheses such as:

```text
SELL-only diagnostic replay
BUY-only diagnostic replay
BUY,SELL mixed replay with stricter BUY filters
SELL hour 8/9 pocket replay
range-width and SL-distance filters
specialist-conflict filters
```

---

## Implemented file

```text
scripts/backtest_regime_filtered_hybrid.py
```

GUI:

```text
Backtest regime-filtered hybrid
```

---

## Important statement about BUY

BUY is not deleted or permanently disabled.

The command default is:

```text
--allowed-sides BUY,SELL
```

To test SELL-only, pass:

```text
--allowed-sides SELL
```

To keep BUY but make it stricter, use side-specific gates such as:

```text
--allowed-sides BUY,SELL
--buy-min-confidence 0.98
--buy-min-side-4h-room 5
--buy-min-side-1d-room 10
--buy-max-sl-distance 20
```

---

## Inputs

```text
datasets\processed\XAUUSD\5M\hybrid_telemetry_flat_latest.parquet
```

---

## Outputs

```text
run_logs\regime_filtered_hybrid\latest.json
run_logs\regime_filtered_hybrid\latest.html
run_logs\regime_filtered_hybrid\latest.csv
```

---

## Filters

Side and session:

```text
--allowed-sides BUY,SELL | SELL | BUY
--allowed-hours 8,9
--buy-allowed-hours 8,9
--sell-allowed-hours 8,9
```

Candidate quality:

```text
--min-candidate-confidence
--buy-min-confidence
--sell-min-confidence
--min-reward-risk
--buy-min-reward-risk
--sell-min-reward-risk
--max-sl-distance
--buy-max-sl-distance
--sell-max-sl-distance
```

Range context:

```text
--min-side-4h-room
--buy-min-side-4h-room
--sell-min-side-4h-room
--min-side-1d-room
--buy-min-side-1d-room
--sell-min-side-1d-room
--min-range-4h-width
--max-range-4h-width
--min-range-1d-width
--max-range-1d-width
```

Model confidence/uncertainty:

```text
--block-specialist-conflict 1
--max-booster-entropy
--min-booster-action-margin
--min-specialist-max-prob
```

---

## First diagnostic command — SELL-only

```powershell
python -u scripts/backtest_regime_filtered_hybrid.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --flat-path datasets\processed\XAUUSD\5M\hybrid_telemetry_flat_latest.parquet `
  --eval-frac 1.0 `
  --max-windows 0 `
  --allowed-sides SELL `
  --initial-capital 100 `
  --units 0.1 `
  --storage-root datasets
```

## Second diagnostic command — mixed with stricter BUY

```powershell
python -u scripts/backtest_regime_filtered_hybrid.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --flat-path datasets\processed\XAUUSD\5M\hybrid_telemetry_flat_latest.parquet `
  --eval-frac 1.0 `
  --max-windows 0 `
  --allowed-sides BUY,SELL `
  --buy-min-confidence 0.98 `
  --buy-min-side-4h-room 5 `
  --buy-min-side-1d-room 10 `
  --buy-max-sl-distance 20 `
  --initial-capital 100 `
  --units 0.1 `
  --storage-root datasets
```

Send back:

```text
run_logs\regime_filtered_hybrid\latest.json
```

---

## Interpretation

Phase137A is not a production gate. It is a chronological replay of manually specified live-safe filters.

If a filter looks promising, it still needs walk-forward validation before Phase134/paper/live.

---

## Operator initial diagnostic results — 2026-09-14

### SELL-only full replay

```text
allowed_sides          : SELL
source_candidates      : 13757
kept_candidates        : 5174
base_total_pnl         : -4590.797205492854
filtered_total_pnl     : -848.8386568725109
filtered_profit_factor : 0.7290926647116155
filtered_max_drawdown  : 1040.8391872644424
filtered_trades        : 581
filtered_final_balance : 15.116134312748898
would_breach_zero      : true
```

Monthly positives:

```text
2026-04: +40.9952 PF=1.1149
2026-07: +87.4448 PF=1.2510
```

Monthly failures:

```text
2026-02: -430.7218 PF=0.3631
2026-05: -423.1884 PF=0.5078
2026-08:  -52.8203 PF=0.5398
```

Decision:

```text
SELL-only reduces damage but fails as a strategy.
```

### Mixed with initial strict BUY gates

```text
allowed_sides          : BUY,SELL
buy_min_confidence     : 0.98
buy_min_side_4h_room   : 5
buy_min_side_1d_room   : 10
buy_max_sl_distance    : 20
filtered_total_pnl     : -2018.1994965970516
filtered_profit_factor : 0.585046282276268
filtered_trades        : 883
filtered_final_balance : -101.81994965970517
```

Decision:

```text
The tested strict-BUY gates are not sufficient. BUY remains part of the project, but it needs separate gating/rework. Do not treat this as evidence that BUY is permanently removed.
```

Next diagnostic:

```text
Test SELL-focused pockets from Phase136A, especially SELL hours 8 and 9, using chronological replay.
```

---

## Operator focused SELL h8/9 result — 2026-09-14

Configuration:

```text
allowed_sides      : SELL
sell_allowed_hours : 8,9
eval_frac          : 1.0
```

Result:

```text
source_candidates      : 13757
kept_candidates        : 583
filtered_trades        : 77
filtered_total_pnl     : +16.920441061258316
filtered_profit_factor : 1.037288325923403
filtered_max_drawdown  : 89.34972810745239
filtered_final_balance : 101.69204410612583
would_breach_zero      : false
```

Monthly:

```text
2026-01: +18.0882 PF=2.1592 trades=5
2026-02: -44.2072 PF=0.5853 trades=7
2026-03: +38.7940 PF=1.7817 trades=8
2026-04: +52.3129 PF=2.5081 trades=9
2026-05: -71.4458 PF=0.5502 trades=24
2026-06: +21.1881 PF=1.5779 trades=11
2026-07:  +0.1820 PF=1.0035 trades=11
2026-08:  +2.0082 PF=6.8089 trades=2
```

Decision:

```text
Weak positive diagnostic, not accepted. PF is below 1.10 and total PnL is small. Continue with live-safe SL/range filters.
```

---

## Operator SELL h8/9 + max SL result — 2026-09-14

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

Comparison:

```text
SELL h8/9 only        : +16.9204 PF=1.0373 trades=77
SELL h8/9 + SL<=23.56: +23.1475 PF=1.0609 trades=73
```

Decision:

```text
Slight improvement, but still not a pass. PF remains below 1.10 and losses remain in 2026-02 and 2026-05.
```

Next diagnostic:

```text
Add a live-safe 4H range width cap, because Phase136A showed wide 4H range bins were strongly negative.
```

---

## Operator SELL h8/9 + SL + broad 4H width cap result — 2026-09-14

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

Comparison:

```text
SELL h8/9 + SL<=23.56            : +23.1475 PF=1.0609 trades=73
SELL h8/9 + SL<=23.56 + 4H<=33.305: -26.3309 PF=0.8915 trades=50
```

Decision:

```text
Reject the broad 4H width cap. It worsened the replay by removing profitable exposure without removing the main May loss.
```

Next diagnostic:

```text
Test exact 4H positive pocket from Phase136A:
min_range_4h_width=21.741
max_range_4h_width=26.928
```

---

## Operator exact 4H pocket result — 2026-09-14

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
filtered_win_rate      : 57.1429%
filtered_final_balance : 101.13762148916722
```

Monthly:

```text
2026-04:  +6.8169 trades=1
2026-05:  +6.6403 trades=3
2026-06: +12.7187 trades=4
2026-07: -16.8079 trades=4
2026-08:  +2.0082 trades=2
```

Decision:

```text
Promising micro-regime but not accepted. PF passes 1.10, but only 14 trades and low total PnL are not enough for production/paper.
```

Next diagnostic:

```text
Run the same filter with eval_frac=0.15 for a recent-holdout sanity check.
```

---

## Operator exact 4H pocket recent-holdout result — 2026-09-14

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
evaluated_rows         : 7924
source_candidates      : 1445
kept_candidates        : 70
filtered_trades        : 4
filtered_total_pnl     : -17.275230020284653
filtered_profit_factor : 0.11992036742639664
filtered_max_drawdown  : 19.283453941345215
filtered_final_balance : 98.27247699797154
```

Decision:

```text
Reject exact 4H pocket as robust. It did not survive recent holdout.
```

Next sanity check:

```text
Run recent holdout for current best less-restrictive manual regime:
SELL h8/9 + sell_max_sl_distance=23.56
```

---

## Operator current-best SELL filter recent-holdout result — 2026-09-14

Configuration:

```text
allowed_sides        : SELL
sell_allowed_hours   : 8,9
sell_max_sl_distance : 23.56
eval_frac            : 0.15
```

Result:

```text
evaluated_rows         : 7924
source_candidates      : 1445
kept_candidates        : 104
filtered_trades        : 8
filtered_total_pnl     : -22.4049571454525
filtered_profit_factor : 0.40983705655862596
filtered_max_drawdown  : 37.618305921554565
filtered_final_balance : 97.75950428545475
```

Monthly:

```text
2026-07: -24.4132 trades=6
2026-08:  +2.0082 trades=2
```

Decision:

```text
Reject as robust. The current-best full-history manual filter failed recent holdout.
```

Conclusion:

```text
Manual regime filtering has not produced a stable tradeable rule. Stop adding blind hand filters. Next phase should inspect TP/SL anatomy, BUY-side failures and stop-loss concentration.
```
