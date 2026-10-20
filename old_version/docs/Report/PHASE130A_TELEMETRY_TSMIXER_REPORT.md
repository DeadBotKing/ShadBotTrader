# Phase130A Report — Telemetry TSMixer

Date: 2026-09-09

## Goal

Train and backtest a TSMixer benchmark on the Phase127 causal 3D telemetry tensor.

TSMixer is the lighter neural benchmark after WaveNet/TCN. It operates directly on:

```text
X = [samples, tensor_window, channels]
```

and mixes across:

```text
time axis
feature/channel axis
```

## Implemented files

```text
scripts/train_hybrid_telemetry_tsmixer.py
scripts/backtest_hybrid_telemetry_tsmixer.py
tests/unit/ai/test_hybrid_telemetry_tsmixer.py
```

GUI:

```text
Train telemetry TSMixer
Backtest telemetry TSMixer
```

## Training architecture

Each block:

```text
LayerNorm
Permute to [channels, time]
Dense time mixer
Permute back
Residual add
LayerNorm
Dense feature mixer
Residual add
```

Heads:

```text
classifier  -> target_trade_win
regressor   -> target_trade_score_r
multihead   -> both
```

## Validation rules

```text
chronological split
purge_gap default = 336 bars
train-only scaler
no random split
```

## Artifact payload

Saved as `pickle_keras` with:

```text
model_bytes
channel_names
scaler_mean
scaler_std
args
task
meta_threshold
score_threshold
architecture=tsmixer
```

## First train command

```powershell
python -u scripts/train_hybrid_telemetry_tsmixer.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --tensor-path datasets\processed\XAUUSD\5M\hybrid_telemetry_tensor_latest.npz `
  --model-id gold_hybrid_telemetry_tsmixer_5m `
  --task multihead `
  --candidate-only 1 `
  --train-frac 0.70 `
  --val-frac 0.15 `
  --purge-gap 336 `
  --batch-size 64 `
  --epochs 30 `
  --learning-rate 0.001 `
  --mixer-layers 4 `
  --time-hidden-units 64 `
  --feature-hidden-units 128 `
  --dense-units 64 `
  --dropout 0.20 `
  --score-loss-weight 0.50 `
  --class-weight auto `
  --meta-threshold 0.55 `
  --save-record 1 `
  --storage-root datasets
```

## First backtest command

```powershell
python -u scripts/backtest_hybrid_telemetry_tsmixer.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --tensor-path datasets\processed\XAUUSD\5M\hybrid_telemetry_tensor_latest.npz `
  --flat-path datasets\processed\XAUUSD\5M\hybrid_telemetry_flat_latest.parquet `
  --model-id gold_hybrid_telemetry_tsmixer_5m `
  --model-version 0 `
  --decision-mode meta `
  --meta-threshold -1 `
  --eval-frac 1.0 `
  --max-windows 0 `
  --initial-capital 100 `
  --units 0.1 `
  --storage-root datasets
```

## Outputs

```text
run_logs/hybrid_telemetry_tsmixer/latest.json
run_logs/hybrid_telemetry_tsmixer_backtest/latest.json
run_logs/hybrid_telemetry_tsmixer_backtest/latest.html
run_logs/hybrid_telemetry_tsmixer_backtest/latest.csv
```

## Acceptance

TSMixer is useful only if it beats Phase128 LightGBM, Phase129 WaveNet/TCN and the base hybrid chronological replay on out-of-time trading metrics.
