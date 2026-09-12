# Phase128A Report — Hybrid Meta-Labeler Baseline

Date: 2026-09-09

## Goal

Train and backtest a flat LightGBM/CatBoost/XGBoost meta-labeler on the Phase127 causal telemetry projection.

The model does not choose BUY or SELL from scratch. The base hybrid head creates trade candidates. The meta-labeler decides whether a candidate should be executed or skipped.

## Implemented files

```text
scripts/train_hybrid_meta_labeler.py
scripts/backtest_hybrid_meta_labeler.py
tests/unit/ai/test_hybrid_meta_labeler.py
```

GUI integration:

```text
Train hybrid meta-labeler
Backtest hybrid meta-labeler
```

## Input

```text
datasets/processed/XAUUSD/5M/hybrid_telemetry_flat_latest.parquet
```

Produced by Phase127A.

## Training targets

Classifier:

```text
target_trade_win
```

Regressor:

```text
target_trade_score_r
```

Raw PnL remains analysis-only:

```text
target_trade_pnl
```

## Training protocol

```text
chronological train/validation/test split
candidate_only=1 by default
no random split
```

## Backtest protocol

The meta backtest uses candidate rows from the telemetry flat matrix:

```text
candidate_mask == 1
meta_probability >= meta_threshold
one open position at a time
target_exit_index controls skipped_while_open
target_trade_pnl controls account/equity metrics
```

This is a fast meta-filter comparison backtest. Phase132 will later compare multiple meta models and thresholds more broadly.

## First train command

```powershell
python -u scripts/train_hybrid_meta_labeler.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --task classifier `
  --target target_trade_win `
  --booster lightgbm `
  --candidate-only 1 `
  --train-frac 0.70 `
  --val-frac 0.15 `
  --class-weight auto `
  --n-estimators 500 `
  --learning-rate 0.03 `
  --max-depth 3 `
  --num-leaves 31 `
  --meta-threshold 0.55 `
  --save-record 1 `
  --storage-root datasets
```

## First backtest command

```powershell
python -u scripts/backtest_hybrid_meta_labeler.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --meta-model-id gold_hybrid_meta_lightgbm_5m `
  --meta-model-version 0 `
  --meta-threshold -1 `
  --eval-frac 1.0 `
  --max-windows 0 `
  --initial-capital 100 `
  --units 0.1 `
  --storage-root datasets
```

## Outputs

```text
run_logs/hybrid_meta_labeler/latest.json
run_logs/hybrid_meta_backtest/latest.json
run_logs/hybrid_meta_backtest/latest.html
run_logs/hybrid_meta_backtest/latest.csv
```

## Acceptance for moving forward

Phase128 is useful only if the meta-filter improves the base chronological replay:

```text
higher profit_factor
lower max_drawdown
better final_balance
not collapsed to near-zero trades
monthly losses reduced
```

If it does not improve, keep the data and move to Phase129 WaveNet/TCN and Phase130 TSMixer benchmarks.

## Operator train result

Phase128A LightGBM classifier was trained by the operator:

```text
model_id       : gold_hybrid_meta_lightgbm_5m
version        : 1
rows           : 2307
features       : 94
train/val/test : 1614 / 346 / 347
record_path    : datasets\models\gold_hybrid_meta_lightgbm_5m\v1_training.json
```

Validation:

```text
AP             : 0.7864284978741574
base_rate      : 0.6445086705202312
precision@0.55 : 0.6572327044025157
recall@0.55    : 0.9372197309417041
positive_rate  : 0.9190751445086706
```

Test:

```text
AP             : 0.619043571505885
base_rate      : 0.484149855907781
precision@0.55 : 0.49554896142433236
recall@0.55    : 0.9940476190476191
positive_rate  : 0.9711815561959655
```

Interpretation:

```text
There is ranking signal, but the initial 0.55 threshold is too permissive. The model should be evaluated through trading backtests and threshold grids, not accepted from classification metrics alone.
```

## Operator backtest result

The operator ran Phase128A meta backtest with the saved threshold:

```text
model              : gold_hybrid_meta_lightgbm_5m v1
meta_threshold     : 0.55
rows/evaluated     : 8000 / 8000
trades             : 143
buy/sell           : 74 / 69
wins/losses        : 94 / 49
win_rate           : 65.7343%
total_pnl          : +509.5359231829643
profit_factor      : 2.608242691826868
max_drawdown       : 91.44515466690063
coverage           : 1.7875%
```

Sizing view:

```text
initial_capital    : 100
units              : 0.1
final_balance      : 150.95359231829644
net_profit         : +50.953592318296444
max_drawdown_cash  : 9.144515466690065
would_breach_zero  : false
```

Monthly:

```text
2026-07: +526.1065, 60 wins / 0 losses
2026-08: -16.5706, 34 wins / 49 losses
```

Interpretation:

```text
The flat meta-labeler improved the 8000-row replay materially, but the profit is concentrated in one month. Proceed to Phase132 threshold comparison and Phase133 walk-forward validation before treating it as robust.
```

## Full-stream v2 training result — 2026-09-12

The operator retrained `gold_hybrid_meta_lightgbm_5m` on the full Phase127A stream telemetry matrix:

```text
version         : 2
rows            : 13757 candidate rows
features        : 94
train/val/test  : 9629 / 2064 / 2064
booster         : lightgbm
class_weight    : auto
```

Validation:

```text
AP             : 0.6117950637217242
base_rate      : 0.4806201550387597
precision@0.55 : 0.5464733025708636
recall@0.55    : 0.8356854838709677
positive_rate  : 0.7349806201550387
```

Test:

```text
AP             : 0.7147311817866087
base_rate      : 0.5184108527131783
precision@0.55 : 0.6214614878209348
recall@0.55    : 0.8822429906542056
positive_rate  : 0.7359496124031008
```

Interpretation:

```text
The full-stream classifier has statistical ranking signal, but Phase133A walk-forward trading validation failed. Therefore v2 is not accepted for production/paper deployment.
```
