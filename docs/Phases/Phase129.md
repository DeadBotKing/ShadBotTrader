# Phase129 — WaveNet/TCN on 3D Hybrid Telemetry Tensor

**Status:** ✅ Phase129A implemented
**Type:** Neural temporal model / causal Conv1D / roll-forward training
**Priority:** after Phase128 LightGBM baseline

---

## Why this phase exists

The previous WaveNet path on raw `trend_signal` collapsed:

```text
uniform 1/3 probabilities
or always BUY/SELL behavior
loss near random
no stable trade edge
```

That does not mean WaveNet is permanently useless. It means the old input/target pair was weak.

Phase129 retries WaveNet/TCN on a better problem:

```text
input  = causal 3D telemetry tensor from Phase127
target = Target C:
         target_trade_win
         target_trade_score_r
         target_trade_pnl for analysis
```

The model is no longer asked to discover direction from scratch. It learns temporal trade quality and regime behavior around already-built hybrid/range signals.

---

## Model family

Use causal WaveNet/TCN style blocks:

```text
Dilated causal Conv1D
Residual blocks
Skip connections
Dropout
LayerNorm/BatchNorm if stable
```

Input:

```text
X.shape = [samples, tensor_window, channels]
```

Recommended default:

```text
tensor_window = 288
safe_lag = 48
```

---

## Outputs / heads

Recommended multi-head model:

```text
head_win     : sigmoid, predicts target_trade_win
head_score_r : regression, predicts target_trade_score_r
```

Optional analysis only:

```text
head_pnl or no direct PnL head initially
```

The practical decision should use:

```text
meta_win_prob
expected_score_r
```

not raw `target_trade_pnl`.

---

## Loss

Suggested combined loss:

```text
loss = BCE(target_trade_win, pred_win)
     + alpha * Huber(target_trade_score_r, pred_score_r)
```

Start with:

```text
alpha = 0.5
```

If regression destabilizes training, train two separate models first:

```text
classifier WaveNet
score-regression WaveNet
```

---

## Roll-forward protocol

No random split.

Minimum:

```text
expanding roll-forward folds
purge_gap >= tensor_window + safe_lag
```

Monitor metrics:

```text
val_trade_win_ap
val_trade_win_precision_at_threshold
val_score_r_mae
val_expected_trade_pnl_after_filter
val_action_collapse / predicted trade rate sanity
```

Do not monitor only `val_loss`.

---

## Anti-collapse checks

The old WaveNet failed by collapse. This phase must fail fast if:

```text
pred_win_stdev ~= 0
predicted_trade_rate == 0
predicted_trade_rate too high
single-regime output constant
validation PnL worse than LightGBM baseline
```

Acceptance thresholds should be compared to Phase128, not to zero.

---

## Backtest integration

WaveNet/TCN is not the first decision model. It is a filter/scorer:

```text
base hybrid candidate
+ WaveNet meta_win_prob
+ WaveNet expected_score_r
→ execute / skip
```

Then run:

```text
Phase126A chronological replay
Phase133 walk-forward validation
```

---

## Model IDs

Recommended:

```text
gold_hybrid_meta_wavenet_5m
gold_hybrid_score_wavenet_5m
```

If implemented as one multi-head artifact:

```text
gold_hybrid_telemetry_wavenet_5m
```

---

## Acceptance criteria

```text
- Uses Phase127 3D tensor only.
- Enforces chronological/roll-forward split.
- Includes purge gap to prevent target/feature overlap leakage.
- Reports anti-collapse metrics.
- Produces chronological replay after filtering base hybrid trades.
- Must beat Phase128 LightGBM baseline before being considered useful.
```

---

## Important note

This is not a revival of the old `gold_trend_signal_5m` as-is. It is a new WaveNet/TCN experiment with a better target and richer causal telemetry inputs.

---

## Next phase

```text
Phase130 — TSMixer benchmark on the same 3D tensor.
```

---

## GUI/operator execution requirement

WaveNet/TCN جدید نباید فقط با terminal قابل اجرا باشد. این فاز باید Dashboard command داشته باشد تا اپراتور بتواند train و audit را از GUI اجرا کند.

حداقل commandهای لازم:

```text
CommandKind.TRAIN_HYBRID_TELEMETRY_WAVENET
Dashboard label: Train telemetry WaveNet/TCN
Handler: runs scripts/train_hybrid_telemetry_wavenet.py

CommandKind.BACKTEST_HYBRID_TELEMETRY_WAVENET
Dashboard label: Backtest telemetry WaveNet/TCN
Handler: runs scripts/backtest_hybrid_telemetry_wavenet.py
```

فیلدهای مهم GUI:

```text
tensor_path
model_id
tensor_window
n_layers
n_blocks/dilations
batch_size
epochs
learning_rate
monitor_metric
purge_gap
meta_threshold/score_threshold
storage_root
```

تست الزامی: descriptor وجود داشته باشد و handler همهٔ flagهای مهم را پاس کند.

---

## Phase129A implementation status

Implemented files:

```text
scripts/train_hybrid_telemetry_wavenet.py
scripts/backtest_hybrid_telemetry_wavenet.py
```

GUI commands:

```text
Train telemetry WaveNet/TCN
Backtest telemetry WaveNet/TCN
```

Tests:

```text
tests/unit/ai/test_hybrid_telemetry_wavenet.py
tests/unit/presentation/test_architecture_knobs_gui.py
```

Training capabilities:

```text
- input: Phase127 NPZ tensor
- task=classifier | regressor | multihead
- causal dilated Conv1D WaveNet/TCN blocks
- train-only channel normalization
- chronological train/validation/test split
- purge_gap default = 336 bars
- anti-collapse metrics: prediction stdev, selected/positive rates
- optional class weights
- TensorFlow/Keras artifact saved as pickle_keras with scaler metadata
```

Backtest capabilities:

```text
- loads saved WaveNet/TCN artifact
- applies saved scaler
- decision_mode=meta|score|both
- meta_threshold / score_threshold gates
- chronological single-position replay using source_index/target_exit_index
- outputs HTML/JSON/CSV
```

Outputs:

```text
run_logs/hybrid_telemetry_wavenet/latest.json
run_logs/hybrid_telemetry_wavenet_backtest/latest.json
run_logs/hybrid_telemetry_wavenet_backtest/latest.html
run_logs/hybrid_telemetry_wavenet_backtest/latest.csv
```

Precondition:

```text
Phase127A produced datasets/processed/XAUUSD/5M/hybrid_telemetry_tensor_latest.npz
Phase127A produced datasets/processed/XAUUSD/5M/hybrid_telemetry_flat_latest.parquet
TensorFlow installed via requirements-ai.txt
```

First recommended train command:

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
  --max-samples 0 `
  --batch-size 64 `
  --epochs 30 `
  --learning-rate 0.001 `
  --filters 48 `
  --kernel-size 3 `
  --n-layers 5 `
  --n-blocks 2 `
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
python -u scripts/backtest_hybrid_telemetry_wavenet.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --tensor-path datasets\processed\XAUUSD\5M\hybrid_telemetry_tensor_latest.npz `
  --flat-path datasets\processed\XAUUSD\5M\hybrid_telemetry_flat_latest.parquet `
  --model-id gold_hybrid_telemetry_wavenet_5m `
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
