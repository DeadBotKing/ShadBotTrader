# Phase133 — Walk-Forward Out-of-Time Hybrid Validation

**Status:** ✅ Phase133A implemented
**Type:** Robustness validation / anti-leakage final research gate
**Priority:** before any live/paper trading

---

## Goal

Determine whether the hybrid/meta system generalizes across time, instead of winning only on one selected holdout.

This phase answers:

```text
If we train only on the past, does the system work on the next unseen block/month?
```

---

## Why not train on all data then backtest all data?

That is leakage:

```text
train on full history
backtest on same full history
```

The model has seen the period being evaluated. It can look good in-sample and fail live.

Production final training on all past data is allowed only after walk-forward passes. Then the only valid test is future paper/live data.

---

## Walk-forward protocol

Recommended monthly version:

```text
for each test_month M:
  train_data      = all data before M, excluding purge gap
  validation_data = last slice before M
  test_data       = month M only

  train Phase128/129/130/131 candidate model
  calibrate thresholds on validation_data only
  run chronological replay on test_data
  record metrics
```

Purge gap:

```text
purge_gap >= tensor_window + safe_lag
```

Default:

```text
tensor_window = 288
safe_lag = 48
purge_gap >= 336 bars
```

---

## What is evaluated

```text
base hybrid head + Phase125 thresholds
LightGBM meta-filter
WaveNet/TCN telemetry model
TSMixer telemetry model
PatchTST telemetry model
```

Only models already built in prior phases are included.

---

## Metrics per fold/month

```text
train rows
validation rows
test rows
trades
coverage
win_rate
label_precision
total_pnl
avg_pnl
profit_factor
max_drawdown
final_balance
would_breach_zero
skipped_while_open
skipped_by_meta_filter
```

Aggregate metrics:

```text
months_positive
months_negative
median_monthly_pnl
mean_monthly_pnl
worst_month
best_month
total_pnl
max_drawdown
profit_factor
```

---

## Acceptance criteria

```text
- No random split.
- No training row overlaps future test labels.
- Thresholds are selected only from validation/past data.
- Monthly report is honest even if negative.
- Proceed to production consolidation only if out-of-time results are stable enough.
```

---

## Pass/fail guideline

A candidate can move forward if it satisfies approximately:

```text
profit_factor > 1.10 out-of-time
max_drawdown acceptable for units/initial_capital
more positive months than negative months
no single month explains all profit
coverage non-zero but not over-trading
```

Exact thresholds can be adjusted after seeing fold counts.

---

## Next phase

```text
Phase134 — Production consolidation / online bot assembly.
```

---

## GUI/operator execution requirement

Walk-forward validation زمان‌بر است، اما باید از Dashboard قابل اجرا باشد تا اپراتور مجبور نباشد دستورهای بلند را دستی بسازد.

حداقل command لازم:

```text
CommandKind.RUN_HYBRID_WALK_FORWARD_VALIDATION
Dashboard label: Run hybrid walk-forward validation
Handler: runs scripts/run_hybrid_walk_forward_validation.py
```

فیلدهای مهم GUI:

```text
symbol
timeframe
start_month
end_month
tensor_window
safe_lag_bars
purge_gap
candidate_models
train_months_min
validation_months
initial_capital
units
storage_root
```

Dashboard باید log زندهٔ fold/month را نشان دهد. تست GUI و log visibility الزامی است.

---

## Phase133A implementation status

Implemented file:

```text
scripts/run_hybrid_walk_forward_validation.py
```

GUI command:

```text
Run hybrid walk-forward validation
```

Tests:

```text
tests/unit/ai/test_hybrid_walk_forward_validation.py
tests/unit/presentation/test_architecture_knobs_gui.py
tests/integration/test_gui_coverage.py
```

Implemented scope:

```text
Phase133A starts with the Phase128 flat telemetry meta-labeler baseline.
It retrains a fresh booster per test month using only earlier months.
```

Protocol:

```text
for each test_month:
  train_months      = all earlier months before validation block
  validation_months = immediate month(s) before test month
  test_month        = next unseen month

  purge train rows before validation boundary
  purge validation rows before test boundary
  train meta model on train rows
  choose threshold on validation only
  run chronological candidate replay on test month
  record base vs meta metrics
```

Outputs:

```text
run_logs/hybrid_walk_forward_validation/latest.json
run_logs/hybrid_walk_forward_validation/latest.csv
run_logs/hybrid_walk_forward_validation/latest.html
```

First recommended command:

```powershell
python -u scripts/run_hybrid_walk_forward_validation.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --flat-path datasets\processed\XAUUSD\5M\hybrid_telemetry_flat_latest.parquet `
  --task classifier `
  --target target_trade_win `
  --booster lightgbm `
  --candidate-only 1 `
  --train-months-min 3 `
  --validation-months 1 `
  --purge-gap-bars 336 `
  --meta-thresholds 0.45,0.50,0.55,0.60,0.65,0.70 `
  --min-trades 10 `
  --score-metric total_pnl `
  --class-weight auto `
  --n-estimators 400 `
  --learning-rate 0.03 `
  --max-depth 3 `
  --num-leaves 31 `
  --initial-capital 100 `
  --units 0.1 `
  --storage-root datasets
```

Important limitation:

```text
Phase133A validates the flat LightGBM/CatBoost/XGBoost baseline first.
Neural walk-forward for WaveNet/TSMixer/PatchTST can be added later if the flat baseline is promising.
```

---

## Operator walk-forward result on full-stream telemetry — 2026-09-12

Input:

```text
flat_path        : datasets\processed\XAUUSD\5M\hybrid_telemetry_flat_latest.parquet
model_id         : gold_hybrid_meta_walkforward_5m
task             : classifier
target           : target_trade_win
booster          : lightgbm
candidate_only   : 1
train_months_min : 3
validation_months: 1
purge_gap_bars   : 336
meta_thresholds  : 0.45,0.50,0.55,0.60,0.65,0.70
score_metric     : total_pnl
initial_capital  : 100
units            : 0.1
```

Fold results:

```text
2026-04: base=-228.3295, meta= +25.1883, PF=1.1654, trades=24,  threshold=0.70
2026-05: base=-465.0026, meta=-122.8658, PF=0.4854, trades=35,  threshold=0.60
2026-06: base=-381.2333, meta=-210.3758, PF=0.6922, trades=100, threshold=0.70
2026-07: base=  +3.7473, meta= -59.0373, PF=0.8710, trades=100, threshold=0.70
2026-08: base=-202.4170, meta= -20.8577, PF=0.8181, trades=29,  threshold=0.70
2026-09: base= -15.6105, meta=  +0.0000, PF=0.0000, trades=0,   threshold=0.70
```

Aggregate:

```text
folds                  : 6
positive_months        : 1
negative_months        : 4
base_total_pnl         : -1288.8456037938595
meta_total_pnl         : -387.9482191801071
meta_profit_factor     : 0.764435361497561
meta_trades            : 288
meta_avg_pnl           : -1.3470424277087052
meta_max_drawdown      : 460.49957263469696
meta_final_balance     : 61.20517808198929
meta_return_percent    : -38.79482191801071%
meta_would_breach_zero : false
best_month             : 2026-04
worst_month            : 2026-06
```

Decision:

```text
FAIL for production/paper gate.
```

Reason:

```text
- Out-of-time total PnL is negative: -387.95 raw / -38.79 cash at units=0.1.
- Profit factor is 0.7644, below the required >1.10 guideline.
- Only 1 of 6 test months is positive; 4 are negative and September has zero meta trades.
- The meta-filter reduces base-hybrid damage (-387.95 vs -1288.85), but it does not create a profitable walk-forward edge.
- Validation-selected thresholds do not transfer robustly to the next month.
```

Operational consequence:

```text
Do not proceed to Phase134 paper shadow or any live trading with this flat LightGBM meta-filter configuration.
The current model can be considered a damage-reduction filter, not a deployable alpha filter.
```
