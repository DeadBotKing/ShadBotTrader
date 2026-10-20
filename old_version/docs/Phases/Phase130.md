# Phase130 — TSMixer Benchmark on 3D Hybrid Telemetry Tensor

**Status:** ✅ Phase130A implemented
**Type:** Neural temporal benchmark / MLP mixer
**Priority:** after Phase129 or in parallel as a lighter neural baseline

---

## What is TSMixer?

TSMixer is a time-series neural architecture built mostly from MLP blocks. It works on tensors shaped like:

```text
X = [samples, time, channels]
```

It mixes information in two directions:

```text
1) time mixing    — relationships across candles
2) feature mixing — relationships across channels/features
```

Unlike Transformer/PatchTST, it does not use attention. Unlike WaveNet/TCN, it does not rely on causal dilated convolutions.

---

## Why TSMixer is relevant here

Our Phase127 data is exactly a multivariate time series:

```text
5M candle channels
model probability channels
range/bracket channels
lagged telemetry channels
aligned 4H/1D channels
```

TSMixer can learn interactions such as:

```text
hybrid confidence high
but recent lagged trade quality falling
and price near 1D high
and 4H room shrinking
→ skip candidate
```

---

## Advantages

```text
- lighter than PatchTST
- usually lower RAM than Transformer-based models
- easier to implement than full attention models
- good first neural benchmark for [time, channels] data
- less sensitive to artificial feature ordering than image CNNs
```

---

## Disadvantages

```text
- no explicit attention over distant patches
- may underperform PatchTST on long-range regime patterns
- still needs careful chronological validation
```

---

## Model inputs

```text
datasets/processed/XAUUSD/5M/hybrid_telemetry_tensor_latest.npz
```

Fields:

```text
X                    [N, tensor_window, channels]
target_trade_win     [N]
target_trade_score_r [N]
```

---

## Model heads

Recommended multi-head:

```text
win_head     -> target_trade_win
score_r_head -> target_trade_score_r
```

Same target set as Phase129 to allow fair comparison.

---

## Training protocol

```text
chronological split
roll-forward folds
purge_gap >= tensor_window + safe_lag
```

Metrics:

```text
val_trade_win_ap
val_trade_win_precision_at_threshold
val_score_r_mae
filtered chronological PnL
profit_factor
max_drawdown
coverage
```

---

## Baselines it must beat

```text
Phase128 LightGBM meta-labeler
Phase129 WaveNet/TCN if already built
base hybrid head without meta-filter
```

---

## Acceptance criteria

```text
- Trains on Phase127 tensor without flattening away time.
- Produces meta_win_prob and expected_score_r.
- Runs Phase126A-style chronological replay with its filter.
- Beats the flat LightGBM baseline in out-of-time trading metrics.
```

---

## Next phase

```text
Phase131 — PatchTST benchmark.
```

---

## GUI/operator execution requirement

TSMixer benchmark باید از Dashboard قابل اجرا باشد.

حداقل commandهای لازم:

```text
CommandKind.TRAIN_HYBRID_TELEMETRY_TSMIXER
Dashboard label: Train telemetry TSMixer
Handler: runs scripts/train_hybrid_telemetry_tsmixer.py

CommandKind.BACKTEST_HYBRID_TELEMETRY_TSMIXER
Dashboard label: Backtest telemetry TSMixer
Handler: runs scripts/backtest_hybrid_telemetry_tsmixer.py
```

فیلدهای مهم GUI:

```text
tensor_path
model_id
tensor_window
mixer_layers
hidden_size
dropout
batch_size
epochs
learning_rate
monitor_metric
meta_threshold/score_threshold
storage_root
```

هر command اجرایی باید در GUI coverage tests ثبت شود.

---

## Phase130A implementation status

Implemented files:

```text
scripts/train_hybrid_telemetry_tsmixer.py
scripts/backtest_hybrid_telemetry_tsmixer.py
```

GUI commands:

```text
Train telemetry TSMixer
Backtest telemetry TSMixer
```

Tests:

```text
tests/unit/ai/test_hybrid_telemetry_tsmixer.py
tests/unit/presentation/test_architecture_knobs_gui.py
```

Training capabilities:

```text
- input: Phase127 NPZ tensor
- task=classifier | regressor | multihead
- TSMixer residual blocks: time mixing + feature mixing
- train-only channel normalization
- chronological train/validation/test split
- purge_gap default = 336 bars
- anti-collapse metrics reused from Phase129
- TensorFlow/Keras artifact saved as pickle_keras with scaler metadata
```

Backtest capabilities:

```text
- loads saved TSMixer artifact
- applies saved scaler
- decision_mode=meta|score|both
- meta_threshold / score_threshold gates
- chronological single-position replay using source_index/target_exit_index
- outputs HTML/JSON/CSV
```

Outputs:

```text
run_logs/hybrid_telemetry_tsmixer/latest.json
run_logs/hybrid_telemetry_tsmixer_backtest/latest.json
run_logs/hybrid_telemetry_tsmixer_backtest/latest.html
run_logs/hybrid_telemetry_tsmixer_backtest/latest.csv
```

Precondition:

```text
Phase127A produced datasets/processed/XAUUSD/5M/hybrid_telemetry_tensor_latest.npz
Phase127A produced datasets/processed/XAUUSD/5M/hybrid_telemetry_flat_latest.parquet
TensorFlow installed via requirements-ai.txt
```

First recommended train command:

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
  --max-samples 0 `
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
  --score-threshold 0 `
  --monitor-metric auto `
  --early-stopping-patience 8 `
  --save-record 1 `
  --storage-root datasets
```

First recommended backtest command:

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
  --score-threshold 0 `
  --eval-frac 1.0 `
  --max-windows 0 `
  --initial-capital 100 `
  --units 0.1 `
  --storage-root datasets
```
