# Phase133C Report — Validation No-Trade / Risk Gate

Date: 2026-09-13

## Goal

Prevent tensor walk-forward folds from being forced to trade when validation says every threshold is weak.

Phase133B failed partly because several folds selected the least-bad validation threshold even when validation PnL was negative:

```text
2026-04 validation_score = -102.5548 -> test = -144.8683
2026-05 validation_score =  -42.2108 -> test = -270.3103
2026-06 validation_score = -107.0676 -> test =   +7.8459
```

In live operation, a system should be allowed to choose:

```text
NO_TRADE
```

when validation quality is below minimum requirements.

## Implementation

Phase133C extends the existing tensor walk-forward script:

```text
scripts/run_hybrid_tensor_walk_forward_validation.py
```

GUI command remains:

```text
Run tensor walk-forward validation
```

with new risk-gate fields:

```text
allow_no_trade
min_validation_score
min_validation_profit_factor
max_validation_drawdown
```

## New CLI flags

```text
--allow-no-trade {0,1}
--min-validation-score FLOAT
--min-validation-profit-factor FLOAT
--max-validation-drawdown FLOAT
```

Gate behavior:

```text
if allow_no_trade=1 and best validation trades < min_trades:
    selected_decision_mode = no_trade

if allow_no_trade=1 and best validation score < min_validation_score:
    selected_decision_mode = no_trade

if allow_no_trade=1 and best validation PF < min_validation_profit_factor:
    selected_decision_mode = no_trade

if allow_no_trade=1 and max_validation_drawdown >= 0 and validation DD > max_validation_drawdown:
    selected_decision_mode = no_trade
```

A no-trade fold records:

```text
tensor_trades = 0
tensor_total_pnl = 0
tensor_profit_factor = 0
tensor_max_drawdown = 0
no_trade_selected = 1
```

## Recommended Phase133C command

Use the v1-like WaveNet architecture because v2 was rejected:

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
  --allow-no-trade 1 `
  --min-validation-score 0 `
  --min-validation-profit-factor 1.10 `
  --max-validation-drawdown 120 `
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

## Outputs

```text
run_logs\hybrid_tensor_walk_forward_validation\latest.json
run_logs\hybrid_tensor_walk_forward_validation\latest.csv
run_logs\hybrid_tensor_walk_forward_validation\latest.html
```

## Expected interpretation

This phase is a risk-control diagnostic, not a guarantee of profitability. Passing requires:

```text
tensor_total_pnl > 0
tensor_profit_factor > 1.10
positive_months > negative_months
no single month explains all profit
drawdown acceptable
```

If Phase133C only reduces losses but remains negative or near zero, production/paper remains blocked.

## Operator result — 2026-09-13

Configuration:

```text
allow_no_trade               : 1
min_validation_score         : 0.0
min_validation_profit_factor : 1.10
max_validation_drawdown      : 120.0
```

Aggregate:

```text
folds                    : 6
positive_months          : 0
negative_months          : 1
no_trade_months          : 3
base_total_pnl           : -1288.8456037938595
tensor_total_pnl         : -32.83297738432884
tensor_gross_profit      : 107.19759202003479
tensor_gross_loss        : 140.03056940436363
tensor_profit_factor     : 0.7655299301860462
tensor_max_drawdown      : 86.88896641135216
tensor_trades            : 35
tensor_avg_pnl           : -0.9380850681236812
tensor_final_balance     : 96.71670226156712
tensor_return_percent    : -0.03283297738432878
```

Fold detail:

```text
2026-04: selected both meta=0.55 score=0.05, validation +280.8103 PF=5.1298, test trades=0, PnL=0
2026-05: no_trade, validation score -36.3806 below 0, PnL=0
2026-06: no_trade, validation score -107.9652 below 0, PnL=0
2026-07: no_trade, validation PF 1.0427 below 1.10, PnL=0
2026-08: selected both meta=0.70 score=-0.10, validation +60.4502 PF=1.4048, test -32.8330 PF=0.7655, trades=35
2026-09: selected score=-0.10, validation +43.1543 PF=2.0536, test trades=0, PnL=0
```

Decision:

```text
FAILED. The risk gate greatly reduced damage but did not produce an acceptable strategy.
```

Lesson:

```text
Validation-positive months still do not reliably transfer to the next month. Fold 5 was validation-positive and passed the gates, but test August lost money. The next work should be failure/regime diagnostics, not larger WaveNet training.
```
