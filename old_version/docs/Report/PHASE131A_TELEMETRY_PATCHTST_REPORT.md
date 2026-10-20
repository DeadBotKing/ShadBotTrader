# Phase131A Report — Telemetry PatchTST

Date: 2026-09-09

## Goal

Train and backtest a PatchTST benchmark on the Phase127 causal 3D telemetry tensor.

PatchTST is heavier than TSMixer and WaveNet/TCN but may model longer-range temporal regimes better by turning the 5M telemetry window into overlapping temporal patches.

## Implemented files

```text
scripts/train_hybrid_telemetry_patchtst.py
scripts/backtest_hybrid_telemetry_patchtst.py
tests/unit/ai/test_hybrid_telemetry_patchtst.py
```

GUI:

```text
Train telemetry PatchTST
Backtest telemetry PatchTST
```

## Training architecture

```text
Input: [samples, tensor_window, channels]
Conv1D patch projection: kernel_size=patch_len, stride=stride
Trainable positional embedding
Transformer encoder blocks:
  LayerNorm
  MultiHeadAttention
  residual add
  feed-forward MLP
  residual add
GlobalAveragePooling1D
Dense head(s)
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
architecture=patchtst
patch_len
stride
```

## First train command

```powershell
python -u scripts/train_hybrid_telemetry_patchtst.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --tensor-path datasets\processed\XAUUSD\5M\hybrid_telemetry_tensor_latest.npz `
  --model-id gold_hybrid_telemetry_patchtst_5m `
  --task multihead `
  --candidate-only 1 `
  --train-frac 0.70 `
  --val-frac 0.15 `
  --purge-gap 336 `
  --batch-size 64 `
  --epochs 30 `
  --learning-rate 0.001 `
  --patch-len 16 `
  --stride 8 `
  --d-model 64 `
  --layers 3 `
  --heads 4 `
  --ff-units 128 `
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
python -u scripts/backtest_hybrid_telemetry_patchtst.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --tensor-path datasets\processed\XAUUSD\5M\hybrid_telemetry_tensor_latest.npz `
  --flat-path datasets\processed\XAUUSD\5M\hybrid_telemetry_flat_latest.parquet `
  --model-id gold_hybrid_telemetry_patchtst_5m `
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
run_logs/hybrid_telemetry_patchtst/latest.json
run_logs/hybrid_telemetry_patchtst_backtest/latest.json
run_logs/hybrid_telemetry_patchtst_backtest/latest.html
run_logs/hybrid_telemetry_patchtst_backtest/latest.csv
```

## Acceptance

PatchTST is useful only if it beats the simpler Phase128 LightGBM, Phase129 WaveNet/TCN, Phase130 TSMixer and the base chronological hybrid replay on out-of-time trading metrics.
