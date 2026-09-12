# Phase132A Report — Meta-Filtered Hybrid Comparison

Date: 2026-09-09

## Goal

Compare the base hybrid chronological candidate replay against every trained meta-filter candidate on the same evaluation rows.

Candidate families:

```text
base hybrid candidates
Phase128 flat LightGBM/CatBoost/XGBoost meta-labeler
Phase129 WaveNet/TCN telemetry model
Phase130 TSMixer telemetry model
Phase131 PatchTST telemetry model
```

## Implemented file

```text
scripts/backtest_meta_filtered_hybrid.py
```

GUI:

```text
Backtest meta-filtered hybrid
```

## Inputs

```text
datasets/processed/XAUUSD/5M/hybrid_telemetry_flat_latest.parquet
datasets/processed/XAUUSD/5M/hybrid_telemetry_tensor_latest.npz
```

## Method

If a tensor exists, Phase132 uses the tensor `source_index` list as the shared evaluation universe and aligns the flat telemetry rows to those source indices. This makes comparisons fairer across base, flat, and tensor candidates.

Base candidate:

```text
scores = 1 for every candidate row
meta threshold = 0
```

Flat models:

```text
payload['model'] + payload['feature_names']
```

Tensor models:

```text
payload['model_bytes'] + scaler_mean/scaler_std
```

All candidates use chronological single-position replay through the telemetry target exit index.

## Outputs

```text
run_logs/hybrid_meta_comparison/latest.json
run_logs/hybrid_meta_comparison/latest.csv
run_logs/hybrid_meta_comparison/latest.html
run_logs/hybrid_meta_comparison/best_replay.html
```

## First command

```powershell
python -u scripts/backtest_meta_filtered_hybrid.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --flat-path datasets\processed\XAUUSD\5M\hybrid_telemetry_flat_latest.parquet `
  --tensor-path datasets\processed\XAUUSD\5M\hybrid_telemetry_tensor_latest.npz `
  --candidates base,gold_hybrid_meta_lightgbm_5m,gold_hybrid_telemetry_wavenet_5m,gold_hybrid_telemetry_tsmixer_5m,gold_hybrid_telemetry_patchtst_5m `
  --candidate-versions 0 `
  --decision-modes meta,both `
  --meta-thresholds record,0.55,0.60,0.65 `
  --score-thresholds 0,0.05,0.10 `
  --eval-frac 1.0 `
  --max-windows 0 `
  --min-trades 10 `
  --score-metric total_pnl `
  --initial-capital 100 `
  --units 0.1 `
  --skip-missing 1 `
  --storage-root datasets
```

## Acceptance

A candidate is useful only if it improves the base chronological replay on identical rows:

```text
higher total_pnl / final_balance
higher profit_factor
lower max_drawdown
coverage not collapsed to almost zero
monthly losses reduced
```

The selected best is only a research candidate until Phase133 walk-forward validation passes.

## Operator comparison result

The operator compared `base` vs `gold_hybrid_meta_lightgbm_5m` on the 8000-row telemetry matrix.

Base:

```text
samples       : 7851
trades        : 219
win_rate      : 42.4658%
total_pnl     : +55.14647939801216
profit_factor : 1.0677528759144055
max_drawdown  : 98.2512731552124
coverage      : 2.7895%
```

Best meta-filter:

```text
candidate      : gold_hybrid_meta_lightgbm_5m:meta:meta=record:score=0.0
version        : 1
meta_threshold : 0.55
trades         : 142
buy/sell       : 74 / 68
wins/losses    : 93 / 49
win_rate       : 65.4930%
total_pnl      : +502.82915729284286
avg_pnl        : +3.541050403470724
profit_factor  : 2.5870741996012305
max_drawdown   : 91.44515466690063
coverage       : 1.8087%
final_balance  : 150.2829157292843
```

Threshold grid:

```text
0.55/record : +502.8292 PF=2.5871 trades=142 DD=91.4452
0.60        : +488.5258 PF=2.5521 trades=140 DD=91.4452
0.65        : +481.7925 PF=2.5413 trades=138 DD=89.2924
0.70        : +467.5121 PF=2.5073 trades=136 DD=89.2924
0.75        : +446.6142 PF=2.4499 trades=131 DD=89.2924
0.80        : +420.5321 PF=2.3652 trades=130 DD=89.2924
```

Interpretation:

```text
The flat meta-filter is promising and beats the base replay on this dataset. It is still not robust proof because the comparison uses the same 8000-row telemetry set that includes model training periods. The next mandatory step is full stream telemetry plus Phase133 walk-forward validation.
```
