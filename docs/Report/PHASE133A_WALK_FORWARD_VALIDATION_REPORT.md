# Phase133A Report — Walk-Forward Validation

Date: 2026-09-09

## Goal

Validate the hybrid telemetry meta-labeler without leakage:

```text
train on past
calibrate threshold on past validation
test on next unseen month
```

## Implemented file

```text
scripts/run_hybrid_walk_forward_validation.py
```

GUI:

```text
Run hybrid walk-forward validation
```

## Input

```text
datasets/processed/XAUUSD/5M/hybrid_telemetry_flat_latest.parquet
```

Produced by Phase127A.

## Implemented scope

Phase133A starts with the Phase128 flat telemetry meta-labeler baseline because it is the fastest and most interpretable model family. It trains a fresh booster per test month.

Supported boosters:

```text
lightgbm
xgboost
catboost
auto
```

Supported tasks:

```text
classifier -> target_trade_win
regressor  -> target_trade_score_r
```

## Walk-forward protocol

For each eligible test month:

```text
train_months      = all months before validation block
validation_months = immediate month(s) before test
validation purge  = rows too close to test boundary removed
train purge       = rows too close to validation boundary removed
threshold         = selected on validation only
test              = next unseen month
```

Default purge:

```text
purge_gap_bars = 336
```

because:

```text
tensor_window 288 + safe_lag 48 = 336
```

## Outputs

```text
run_logs/hybrid_walk_forward_validation/latest.json
run_logs/hybrid_walk_forward_validation/latest.csv
run_logs/hybrid_walk_forward_validation/latest.html
```

## First command

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

## Acceptance

Proceed toward production only if walk-forward metrics are stable:

```text
out-of-time profit_factor > 1.10
more positive test months than negative months
no single month explains all profit
drawdown acceptable for units/initial capital
coverage non-zero but not over-trading
```

If Phase133A fails, do not proceed to live/paper. Return to telemetry features, regimes, thresholds, or model choice.

## Operator result — full-stream telemetry — 2026-09-12

The operator ran Phase133A on the full Phase127A stream telemetry output.

Aggregate result:

```text
folds                  : 6
test_months            : 6
positive_months        : 1
negative_months        : 4
base_total_pnl         : -1288.8456037938595
meta_total_pnl         : -387.9482191801071
meta_gross_profit      : 1258.938264489174
meta_gross_loss        : 1646.886483669281
meta_profit_factor     : 0.764435361497561
meta_max_drawdown      : 460.49957263469696
meta_trades            : 288
meta_avg_pnl           : -1.3470424277087052
meta_final_balance     : 61.20517808198929
meta_return_percent    : -0.38794821918010713
meta_would_breach_zero : false
best_month             : 2026-04
worst_month            : 2026-06
```

Month/fold detail:

```text
2026-04: meta= +25.1883, PF=1.1654, trades=24,  base=-228.3295
2026-05: meta=-122.8658, PF=0.4854, trades=35,  base=-465.0026
2026-06: meta=-210.3758, PF=0.6922, trades=100, base=-381.2333
2026-07: meta= -59.0373, PF=0.8710, trades=100, base=  +3.7473
2026-08: meta= -20.8577, PF=0.8181, trades=29,  base=-202.4170
2026-09: meta=  +0.0000, PF=0.0000, trades=0,   base= -15.6105
```

Decision:

```text
FAIL — current flat LightGBM meta-filter does not generalize as a profitable walk-forward trading layer.
```

Important nuance:

```text
The meta-filter is not useless: it reduced full walk-forward loss from -1288.85 to -387.95 raw PnL.
But the acceptance target is profitability and month-to-month stability, not merely loss reduction. No paper/live deployment is allowed from this result.
```
