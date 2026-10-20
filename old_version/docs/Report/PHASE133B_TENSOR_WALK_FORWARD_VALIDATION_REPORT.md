# Phase133B Report — Tensor Model Walk-Forward Validation

Date: 2026-09-13

## Goal

Validate tensor telemetry models without leakage:

```text
train a fresh tensor model on past months
select thresholds only on past validation months
test on the next unseen month
```

This phase was added because Phase129A WaveNet/TCN v1 produced the first strong 3D tensor signal, but its best threshold was selected on a diagnostic holdout slice.

## Implemented file

```text
scripts/run_hybrid_tensor_walk_forward_validation.py
```

GUI:

```text
Run tensor walk-forward validation
```

## Current implemented model family

```text
model_family=wavenet
```

This uses the existing Phase129A causal WaveNet/TCN implementation:

```text
scripts/train_hybrid_telemetry_wavenet.py
```

The fold models are trained in memory for validation and are not saved as production artifacts.

## Inputs

```text
datasets\processed\XAUUSD\5M\hybrid_telemetry_tensor_latest.npz
datasets\processed\XAUUSD\5M\hybrid_telemetry_flat_latest.parquet
```

Tensor shape expected from the current Phase127A full build:

```text
[52683, 150, 94]
```

## Protocol

For each eligible test month:

```text
train_months      = all months before validation block
validation_months = immediate month(s) before test month
test_month        = next unseen month

validation rows too close to test boundary are purged
train rows too close to validation boundary are purged
train samples can be candidate-only
early stopping uses candidate validation samples
threshold grid is selected only on validation replay
test replay uses the selected validation threshold
```

Default purge:

```text
purge_gap_bars = 336
```

## Threshold selection

Supported decision modes:

```text
meta  -> predicted win probability threshold only
score -> predicted target_trade_score_r threshold only
both  -> both win probability and score thresholds
```

For `decision_mode=score`, `meta_threshold` is ignored by design.

## First recommended full command

```powershell
python -u scripts/run_hybrid_tensor_walk_forward_validation.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --tensor-path datasets\processed\XAUUSD\5M\hybrid_telemetry_tensor_latest.npz `
  --flat-path datasets\processed\XAUUSD\5M\hybrid_telemetry_flat_latest.parquet `
  --model-family wavenet `
  --model-id gold_hybrid_tensor_walkforward_wavenet_5m `
  --task multihead `
  --candidate-only 1 `
  --train-months-min 3 `
  --validation-months 1 `
  --purge-gap-bars 336 `
  --decision-modes score,both `
  --meta-thresholds 0.55,0.60,0.65,0.70 `
  --score-thresholds=-0.10,0,0.05,0.10,0.20 `
  --min-trades 10 `
  --min-train-samples 200 `
  --score-metric total_pnl `
  --max-folds 0 `
  --max-train-samples 0 `
  --batch-size 64 `
  --epochs 500 `
  --learning-rate 0.001 `
  --filters 48 `
  --kernel-size 3 `
  --n-layers 5 `
  --n-blocks 2 `
  --dense-units 64 `
  --dropout 0.20 `
  --score-loss-weight 0.50 `
  --class-weight auto `
  --monitor-metric auto `
  --early-stopping-patience 8 `
  --verbose 2 `
  --initial-capital 100 `
  --units 0.1 `
  --storage-root datasets
```

## Pilot/smoke command

For a faster first check:

```powershell
python -u scripts/run_hybrid_tensor_walk_forward_validation.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --tensor-path datasets\processed\XAUUSD\5M\hybrid_telemetry_tensor_latest.npz `
  --flat-path datasets\processed\XAUUSD\5M\hybrid_telemetry_flat_latest.parquet `
  --task multihead `
  --candidate-only 1 `
  --train-months-min 3 `
  --validation-months 1 `
  --purge-gap-bars 336 `
  --decision-modes score,both `
  --score-thresholds=-0.10,0,0.05,0.10,0.20 `
  --min-trades 10 `
  --max-folds 1 `
  --epochs 80 `
  --batch-size 64 `
  --filters 48 `
  --n-layers 5 `
  --n-blocks 2 `
  --storage-root datasets
```

## Outputs

```text
run_logs\hybrid_tensor_walk_forward_validation\latest.json
run_logs\hybrid_tensor_walk_forward_validation\latest.csv
run_logs\hybrid_tensor_walk_forward_validation\latest.html
```

## Acceptance

A tensor model can move toward Phase134 only if Phase133B shows:

```text
out-of-time tensor_total_pnl > 0 by a meaningful margin
tensor_profit_factor > 1.10
positive_months > negative_months
no single month explains all profit
max_drawdown acceptable for the chosen units/initial capital
coverage non-zero but not overtrading
```

Until this passes, Phase134 paper/live remains blocked.

## Operator result — 2026-09-13

Configuration:

```text
model_family      : wavenet
task              : multihead
candidate_only    : 1
train_months_min  : 3
validation_months : 1
purge_gap_bars    : 336
decision_modes    : score,both
score_thresholds  : -0.10,0,0.05,0.10,0.20
score_metric      : total_pnl
```

Aggregate result:

```text
folds                    : 6
positive_months          : 2
negative_months          : 3
base_total_pnl           : -1288.8456037938595
tensor_total_pnl         : -409.51990616321564
tensor_gross_profit      : 608.841717839241
tensor_gross_loss        : 1018.3616240024567
tensor_profit_factor     : 0.5978639645181408
tensor_max_drawdown      : 464.1122056245804
tensor_trades            : 200
tensor_avg_pnl           : -2.047599530816078
tensor_final_balance     : 59.04800938367843
tensor_return_percent    : -0.40951990616321565
tensor_would_breach_zero : false
```

Fold table:

```text
2026-04: val=-102.5548, selected=score score=0.05, tensor=-144.8683, PF=0.3253, trades=35
2026-05: val= -42.2108, selected=score score=-0.10, tensor=-270.3103, PF=0.5553, trades=115
2026-06: val=-107.0676, selected=both meta=0.70 score=0.20, tensor=+7.8459, PF=1.0769, trades=25
2026-07: val= +26.0419, selected=both meta=0.65 score=0.05, tensor=-23.4140, PF=0.4207, trades=8
2026-08: val= +44.9376, selected=both meta=0.65 score=-0.10, tensor=+21.2268, PF=1.3981, trades=17
2026-09: val= +44.3921, selected=score score=0.20, tensor=+0.0000, PF=0.0000, trades=0
```

Decision:

```text
FAILED. No Phase134 paper/live transition is allowed.
```

Important lesson:

```text
The static WaveNet v1 diagnostic result did not survive true walk-forward retraining. The model can reduce base damage, but it is not a deployable alpha layer yet.
```

Potential next research step:

```text
Implement a validation no-trade/risk gate and rerun Phase133B. In live operation, a system should not trade when the best validation threshold is still negative or below a minimum PF/score requirement.
```
