# Phase129A Report — Telemetry WaveNet/TCN

Date: 2026-09-09

## Goal

Retry WaveNet/TCN on the new Phase127 causal 3D telemetry tensor instead of the old collapsed raw `trend_signal` problem.

This is not `gold_trend_signal_5m` revived as-is. It is a new meta/score model over:

```text
X = [samples, tensor_window, channels]
```

with Target C:

```text
target_trade_win
target_trade_score_r
target_trade_pnl for analysis/backtest
```

## Implemented files

```text
scripts/train_hybrid_telemetry_wavenet.py
scripts/backtest_hybrid_telemetry_wavenet.py
tests/unit/ai/test_hybrid_telemetry_wavenet.py
```

GUI:

```text
Train telemetry WaveNet/TCN
Backtest telemetry WaveNet/TCN
```

## Training implementation

```text
causal Conv1D / TCN blocks
residual connections
gated tanh/sigmoid activations
skip aggregation
global average pooling
classifier, regressor or multihead outputs
train-only normalization
chronological split with purge_gap
```

Default purge gap:

```text
336 bars = tensor_window 288 + safe_lag 48
```

## Artifact payload

The saved artifact format is `pickle_keras`:

```text
model_bytes
channel_names
scaler_mean
scaler_std
args
task
meta_threshold
score_threshold
```

This lets the backtest and later production path normalize online tensors with the same train-only scaler.

## First train command

```powershell
python -u scripts/train_hybrid_telemetry_wavenet.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --tensor-path datasets\processed\XAUUSD\5M\hybrid_telemetry_tensor_latest.npz `
  --model-id gold_hybrid_telemetry_wavenet_5m `
  --task multihead `
  --candidate-only 1 `
  --train-frac 0.70 `
  --val-frac 0.15 `
  --purge-gap 336 `
  --batch-size 64 `
  --epochs 30 `
  --learning-rate 0.001 `
  --filters 48 `
  --kernel-size 3 `
  --n-layers 5 `
  --n-blocks 2 `
  --dropout 0.20 `
  --score-loss-weight 0.50 `
  --class-weight auto `
  --meta-threshold 0.55 `
  --save-record 1 `
  --storage-root datasets
```

## First backtest command

```powershell
python -u scripts/backtest_hybrid_telemetry_wavenet.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --tensor-path datasets\processed\XAUUSD\5M\hybrid_telemetry_tensor_latest.npz `
  --flat-path datasets\processed\XAUUSD\5M\hybrid_telemetry_flat_latest.parquet `
  --model-id gold_hybrid_telemetry_wavenet_5m `
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
run_logs/hybrid_telemetry_wavenet/latest.json
run_logs/hybrid_telemetry_wavenet_backtest/latest.json
run_logs/hybrid_telemetry_wavenet_backtest/latest.html
run_logs/hybrid_telemetry_wavenet_backtest/latest.csv
```

## Quality checks

Targeted tests cover split purging, train-only normalization, candidate filtering, gate modes and chronological skip-while-open behavior.

## Acceptance

A trained WaveNet/TCN is useful only if it beats Phase128 LightGBM and base hybrid chronological replay on out-of-time trading metrics. If not, it remains research-only.
