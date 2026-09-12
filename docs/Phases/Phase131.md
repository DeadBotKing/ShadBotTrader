# Phase131 — PatchTST Benchmark on 3D Hybrid Telemetry Tensor

**Status:** ✅ Phase131A implemented
**Type:** Transformer-style time-series benchmark
**Priority:** after Phase128 baseline and at least one lighter neural model

---

## What is PatchTST?

PatchTST means Patch Time Series Transformer. It borrows the patch idea from Vision Transformers, but applies it to time series.

Instead of sending every 5M candle as a token, it cuts the time axis into patches:

```text
tensor_window = 288
patch_len     = 16
stride        = 8
```

This produces overlapping temporal patches:

```text
patch 1 = candles 0..15
patch 2 = candles 8..23
patch 3 = candles 16..31
...
```

The Transformer attends over those patches instead of all individual candles.

---

## Why PatchTST is useful here

The telemetry tensor may contain long context:

```text
24h of 5M data = 288 candles
```

PatchTST can learn longer-range regime and transition patterns, for example:

```text
hybrid model works only after volatility compression
range_4h room expands after daily range reset
recent lagged virtual trades degrade before a regime change
```

---

## Advantages

```text
- better long-context modeling than simple MLP/CNN in many time-series tasks
- patching reduces token count and memory vs raw Transformer
- can learn relationships between distant periods in the window
```

---

## Disadvantages

```text
- heavier than LightGBM and TSMixer
- more overfit risk
- needs stronger regularization and careful walk-forward validation
- not the first production candidate unless it clearly beats simpler baselines
```

---

## Input

```text
X = [samples, tensor_window, channels]
```

From:

```text
datasets/processed/XAUUSD/5M/hybrid_telemetry_tensor_latest.npz
```

---

## Output heads

Same Target C:

```text
head_win     -> target_trade_win
head_score_r -> target_trade_score_r
```

Decision after model:

```text
execute hybrid candidate only if:
  pred_win_prob >= threshold
  and/or pred_score_r >= score_threshold
```

---

## Training protocol

Strict chronological validation:

```text
roll-forward folds
purge_gap >= tensor_window + safe_lag
no random split
```

Candidate hyperparameters:

```text
patch_len: 8, 16, 24
stride: 4, 8, 12
d_model: 32, 64
layers: 2, 3
dropout: 0.1 - 0.4
```

---

## Acceptance criteria

```text
- Beats Phase128 LightGBM in out-of-time chronological replay.
- Does not only improve loss while PnL worsens.
- Reports monthly PnL/PF/DD.
- Reports model complexity and runtime cost.
- If not better than simpler models, it remains research-only.
```

---

## Important note on image CNNs

PatchTST is preferred over cat/dog-style image CNN for this dataset because the feature axis is not a natural spatial axis. A CNN over arbitrary feature order may learn column-order artifacts. PatchTST models time structure directly.

---

## Next phase

```text
Phase132 — Meta-filtered hybrid chronological backtest comparison.
```

---

## GUI/operator execution requirement

PatchTST benchmark نیز باید از Dashboard قابل اجرا باشد، نه فقط CLI.

حداقل commandهای لازم:

```text
CommandKind.TRAIN_HYBRID_TELEMETRY_PATCHTST
Dashboard label: Train telemetry PatchTST
Handler: runs scripts/train_hybrid_telemetry_patchtst.py

CommandKind.BACKTEST_HYBRID_TELEMETRY_PATCHTST
Dashboard label: Backtest telemetry PatchTST
Handler: runs scripts/backtest_hybrid_telemetry_patchtst.py
```

فیلدهای مهم GUI:

```text
tensor_path
model_id
patch_len
stride
d_model
layers
heads
dropout
batch_size
epochs
learning_rate
purge_gap
meta_threshold/score_threshold
storage_root
```

تست‌های GUI باید وجود command و arg pass-through را پوشش بدهند.

---

## Phase131A implementation status

Implemented files:

```text
scripts/train_hybrid_telemetry_patchtst.py
scripts/backtest_hybrid_telemetry_patchtst.py
```

GUI commands:

```text
Train telemetry PatchTST
Backtest telemetry PatchTST
```

Tests:

```text
tests/unit/ai/test_hybrid_telemetry_patchtst.py
tests/unit/presentation/test_architecture_knobs_gui.py
```

Training capabilities:

```text
- input: Phase127 NPZ tensor
- task=classifier | regressor | multihead
- patch projection by Conv1D(kernel_size=patch_len, stride=stride)
- trainable positional embedding
- Transformer encoder blocks with MultiHeadAttention
- train-only channel normalization
- chronological train/validation/test split
- purge_gap default = 336 bars
- TensorFlow/Keras artifact saved as pickle_keras with scaler metadata
```

Backtest capabilities:

```text
- loads saved PatchTST artifact
- applies saved scaler
- decision_mode=meta|score|both
- meta_threshold / score_threshold gates
- chronological single-position replay using source_index/target_exit_index
- outputs HTML/JSON/CSV
```

Outputs:

```text
run_logs/hybrid_telemetry_patchtst/latest.json
run_logs/hybrid_telemetry_patchtst_backtest/latest.json
run_logs/hybrid_telemetry_patchtst_backtest/latest.html
run_logs/hybrid_telemetry_patchtst_backtest/latest.csv
```

Precondition:

```text
Phase127A produced datasets/processed/XAUUSD/5M/hybrid_telemetry_tensor_latest.npz
Phase127A produced datasets/processed/XAUUSD/5M/hybrid_telemetry_flat_latest.parquet
TensorFlow installed via requirements-ai.txt
```

First recommended train command:

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
  --max-samples 0 `
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
  --score-threshold 0 `
  --monitor-metric auto `
  --early-stopping-patience 8 `
  --save-record 1 `
  --storage-root datasets
```

First recommended backtest command:

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
  --score-threshold 0 `
  --eval-frac 1.0 `
  --max-windows 0 `
  --initial-capital 100 `
  --units 0.1 `
  --storage-root datasets
```
