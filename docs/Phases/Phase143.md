# Phase143 — 4D Pivot Image Tensor + Conv2D/Conv3D

**Status:** ✅ Phase143A implemented
**Type:** Image/volume-like Pattern Recognition research
**Production status:** Research-only; no paper/live permission

---

## Owner correction

The owner clarified that the intended tensor is not `[batch, 288, channels]`. The required dataset must be 4D so Conv2D/Conv3D can detect patterns over a 5M rolling window and multi-timeframe feature axes.

Implemented layout:

```text
Stored X shape:
[samples, WindowSize, Features_5M, Features_4H_1D]

Conv2D Keras batch:
[batch, WindowSize, Features_5M, Features_4H_1D]

Conv3D Keras batch:
[batch, WindowSize, Features_5M, Features_4H_1D, 1]
```

Default:

```text
WindowSize = 100
sample_stride = 1
```

This means roll-forward windows move one 5M candle at a time until the end of the 5M dataset.

---

## Cell construction

Each tensor cell is a 5M × HTF interaction:

```text
X[t, f5, htf] = feature_5M[t, f5] * feature_4H_1D[t, htf]
```

Bias terms are prepended:

```text
__5m_bias__
__htf_bias__
```

So the tensor preserves:

```text
pure 5M features
pure 4H/1D features
5M × 4H/1D interactions
```

---

## Implemented files

```text
scripts/build_pivot_pattern_image_tensor.py
scripts/train_pivot_pattern_image_cnn.py
```

GUI commands:

```text
Build pivot image tensor
Train pivot image CNN
```

Tests:

```text
tests/unit/ai/test_pivot_pattern_image_tensor.py
tests/unit/presentation/test_phase143_pivot_image_cnn_gui.py
```

---

## Tensor builder command

```powershell
python -u scripts/build_pivot_pattern_image_tensor.py `
  --source-mode storage `
  --symbol XAUUSD `
  --five-timeframe 5M `
  --hourly-timeframe 1H `
  --h4-timeframe 4H `
  --daily-timeframe 1D `
  --lookahead-bars 48 `
  --pivot-move-atr 0.75 `
  --pivot-zone-atr 0.35 `
  --recent-window-bars 48 `
  --min-direction-edge 1.10 `
  --window-size 100 `
  --sample-stride 1 `
  --max-samples 0 `
  --max-5m-features 24 `
  --max-htf-features 16 `
  --dtype float16 `
  --chunk-size 256 `
  --max-tensor-mb 8192 `
  --output-name pivot_pattern_image_tensor_latest `
  --storage-root datasets `
  --output-dir run_logs\pivot_pattern_image_tensor
```

Outputs:

```text
datasets\processed\XAUUSD\5M\pivot_pattern_image_tensor_latest.npy
datasets\processed\XAUUSD\5M\pivot_pattern_image_tensor_latest_meta.npz
datasets\processed\XAUUSD\5M\pivot_pattern_image_flat_latest.parquet
run_logs\pivot_pattern_image_tensor\latest.json
run_logs\pivot_pattern_image_tensor\latest.html
```

---

## Conv2D/Conv3D trainer command

Requires TensorFlow/Keras:

```powershell
python -m pip install -r requirements-ai.txt
```

Conv2D command:

```powershell
python -u scripts/train_pivot_pattern_image_cnn.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --tensor-path datasets\processed\XAUUSD\5M\pivot_pattern_image_tensor_latest.npy `
  --meta-path datasets\processed\XAUUSD\5M\pivot_pattern_image_tensor_latest_meta.npz `
  --model-id gold_pivot_pattern_image_cnn_5m `
  --model-kind conv2d `
  --train-frac 0.70 `
  --val-frac 0.15 `
  --purge-gap 336 `
  --max-samples 0 `
  --batch-size 64 `
  --epochs 120 `
  --learning-rate 0.001 `
  --filters 32 `
  --kernel-size 3 `
  --dense-units 96 `
  --dropout 0.20 `
  --class-weight auto `
  --buy-threshold 0.55 `
  --sell-threshold 0.55 `
  --min-margin 0.05 `
  --min-buy-r 0 `
  --min-sell-r 0 `
  --early-stopping-patience 12 `
  --save-model 1 `
  --storage-root datasets `
  --output-dir run_logs\pivot_pattern_image_cnn
```

For Conv3D, change only:

```powershell
--model-kind conv3d
```

Outputs:

```text
datasets\models\gold_pivot_pattern_image_cnn_5m\v*_model.keras
datasets\models\gold_pivot_pattern_image_cnn_5m\v*_training.json
run_logs\pivot_pattern_image_cnn\latest.json
run_logs\pivot_pattern_image_cnn\latest.html
```

---

## Smoke result

Internal TESTSYM smoke with small shape produced:

```text
Stored X      : [160, 20, 5, 4]
Conv2D batch  : [batch, 20, 5, 4]
Conv3D batch  : [batch, 20, 5, 4, 1]
```

This confirms the 4D layout and stride-based roll-forward builder are working.

---

## Acceptance

Implementation accepted when:

```text
4D image tensor builder exists
Conv2D/Conv3D trainer exists
GUI commands exist
tests/docs/owner map updated
```

Trading acceptance is separate and requires real training/backtest/walk-forward results. Until then:

```text
No Phase134.
No paper shadow.
No live trading.
```

---

## Feature-axis correction — 2026-09-17

The first Phase143A default used a conservative smoke-friendly feature budget:

```text
max_5m_features  = 12 + bias = 13
max_htf_features = 8  + bias = 9
```

The owner correctly objected that this is too small for the intended Conv2D/Conv3D pattern-recognition model. It was useful for memory-safe smoke tests but not enough for serious learning.

Defaults were increased:

```text
max_5m_features  = 24 + bias = 25
max_htf_features = 16 + bias = 17
max_tensor_mb    = 8192
```

Approximate size for a 53,198-row 5M dataset with `WindowSize=100`, `stride=1`, and `float16`:

```text
samples ≈ 53,198 - 100 + 1 = 53,099
shape   ≈ [53,099, 100, 25, 17]
size    ≈ 4.3 GB
```

This is a more realistic research tensor while still being feasible on an operator workstation. If GPU/RAM/disk allow it, the operator can increase these further, for example:

```text
--max-5m-features 32
--max-htf-features 24
--max-tensor-mb 12288
```

But the default must balance feature richness and memory safety.

---

## Operator sanity-training result — Conv2D image CNN — 2026-09-17

The operator trained the Phase143A Conv2D image CNN on a 12,000-sample subset.

Configuration:

```text
model_kind      : conv2d
max_samples     : 12,000
batch_size      : 32
epochs          : 10
train/val/test  : 8,400 / 1,464 / 1,464
stored X shape  : [12,000, 100, 32, 23]
keras batch     : [batch, 100, 32, 23]
```

Metrics:

```text
val_action_accuracy  : 0.1441
test_action_accuracy : 0.3743
val_top_ap           : 0.1158
test_top_ap          : 0.1217
val_bottom_ap        : 0.0777
test_bottom_ap       : 0.1012
val_buy_r_mae        : 0.6302
test_buy_r_mae       : 0.6286
val_sell_r_mae       : 0.6222
test_sell_r_mae      : 0.6243
val_selected_rate    : 0.0000
test_selected_rate   : 0.0000
```

Decision:

```text
Sanity training executed, but the model produced no actionable selected signals under the default threshold gate.
This is a no-trade/collapse-at-decision-gate result, not a usable trading model.
```

Interpretation:

```text
The tensor shape is correct and Keras training completed, but the first 10-epoch Conv2D sanity model is weak.
The AP metrics are low, and selected_rate=0 means no backtestable trades would be opened with the current thresholds.
Do not run paper/live. Do not accept this model.
```

Recommended next diagnostic:

```text
Before full 120-epoch training, inspect prediction probability distribution and run a lower-threshold diagnostic.
If selected_rate remains near zero or AP remains near base rate, the model/label/normalization must be improved before heavier training.
```

---

## Sanitization + architecture artifact correction — 2026-09-17

The operator inspected `v1_training.json` and found invalid scaler values:

```text
scaler_mean contained Infinity
scaler_std contained NaN
```

Root cause:

```text
The first image tensor builder multiplied raw 5M features by raw 4H/1D features,
then cast the interaction matrix to float16. Some interaction values exceeded
float16 max range and became Infinity. The trainer then computed scaler mean/std
from a tensor that already contained Infinity, producing Infinity/NaN in the
saved model record.
```

Decision:

```text
gold_pivot_pattern_image_cnn_5m v1 is rejected/poisoned.
Do not continue training or backtesting that v1 artifact.
Rebuild the tensor with sanitization and retrain v2+.
```

Builder correction:

```text
--axis-normalization robust
--feature-clip 8
--interaction-clip 32
```

Implementation behavior:

```text
1. 5M and HTF feature axes are sanitized: NaN/Inf -> finite values.
2. Each axis is robust-normalized before interaction.
3. Axis values are clipped to ±feature_clip.
4. Interaction products are clipped to ±interaction_clip before float16 cast.
5. Tensor metadata stores normalization/clipping settings and nonfinite counters.
```

Trainer correction:

```text
1. Training loader sanitizes any old tensor nonfinite values before scaler fitting.
2. Saved scaler_mean/scaler_std are forced finite.
3. Keras architecture is saved next to the model:
   datasets\models\gold_pivot_pattern_image_cnn_5m\v*_architecture.json
   datasets\models\gold_pivot_pattern_image_cnn_5m\v*_summary.txt
4. Latest copies are also written to:
   run_logs\pivot_pattern_image_cnn\latest_architecture.json
   run_logs\pivot_pattern_image_cnn\latest_summary.txt
```

Correct rebuild command:

```powershell
python -u scripts/build_pivot_pattern_image_tensor.py `
  --source-mode storage `
  --symbol XAUUSD `
  --five-timeframe 5M `
  --hourly-timeframe 1H `
  --h4-timeframe 4H `
  --daily-timeframe 1D `
  --lookahead-bars 48 `
  --pivot-move-atr 0.75 `
  --pivot-zone-atr 0.35 `
  --recent-window-bars 48 `
  --min-direction-edge 1.10 `
  --window-size 100 `
  --sample-stride 1 `
  --max-samples 0 `
  --max-5m-features 31 `
  --max-htf-features 22 `
  --dtype float16 `
  --axis-normalization robust `
  --feature-clip 8 `
  --interaction-clip 32 `
  --chunk-size 256 `
  --max-tensor-mb 8192 `
  --output-name pivot_pattern_image_tensor_latest `
  --storage-root datasets `
  --output-dir run_logs\pivot_pattern_image_tensor
```

After rebuild, verify:

```text
run_logs\pivot_pattern_image_tensor\latest.json
report.nonfinite_interaction_values should be 0 or very low after clipping/sanitization.
No overflow warning should appear.
```

---

## Official tensor health audit command — 2026-09-17

Added official pre-training dataset health checker:

```text
scripts/audit_pivot_pattern_image_tensor.py
GUI: Audit pivot image tensor health
```

It validates:

```text
4D tensor rank and shape
Conv2D/Conv3D batch shapes
metadata alignment
sample_indices monotonicity
timestamp monotonicity
target array lengths and finite values
axis scaler finite values
full tensor finite scan
interaction_clip bounds
builder nonfinite diagnostics
```

Command:

```powershell
python -u scripts/audit_pivot_pattern_image_tensor.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --tensor-path datasets\processed\XAUUSD\5M\pivot_pattern_image_tensor_latest.npy `
  --meta-path datasets\processed\XAUUSD\5M\pivot_pattern_image_tensor_latest_meta.npz `
  --flat-path datasets\processed\XAUUSD\5M\pivot_pattern_image_flat_latest.parquet `
  --builder-report run_logs\pivot_pattern_image_tensor\latest.json `
  --chunk-size 256 `
  --full-scan 1 `
  --max-scan-samples 0 `
  --fail-on-reported-feature-nonfinite 0 `
  --storage-root datasets `
  --output-dir run_logs\pivot_pattern_image_tensor_health
```

Outputs:

```text
run_logs\pivot_pattern_image_tensor_health\latest.json
run_logs\pivot_pattern_image_tensor_health\latest.html
```

The operator stated that the manually run dataset test passed. After this implementation, the official audit should also be run and its JSON should be used as the canonical dataset-health record.

---

## Epoch-checkpoint correction — 2026-09-17

The operator reported that one training epoch completed but no model directory appeared under:

```text
datasets\models\gold_pivot_pattern_image_cnn_5m
```

Root cause:

```text
The previous trainer saved the final `.keras` model only after `model.fit(...)` completed all epochs/early-stopping. Completing one epoch did not create a saved model.
```

This is unsafe for heavy training because RAM usage can reach 27GB+ and an interrupted run would lose progress.

Correction:

```text
--checkpoint-each-epoch 1
```

The trainer now creates the model folder and saves visible artifacts before/during training:

```text
datasets\models\gold_pivot_pattern_image_cnn_5m\vN_architecture.json
datasets\models\gold_pivot_pattern_image_cnn_5m\vN_summary.txt
datasets\models\gold_pivot_pattern_image_cnn_5m\vN_epoch_checkpoint.keras
```

After full training completes it also saves:

```text
datasets\models\gold_pivot_pattern_image_cnn_5m\vN_model.keras
datasets\models\gold_pivot_pattern_image_cnn_5m\vN_training.json
```

Dashboard command `Train pivot image CNN` now exposes:

```text
checkpoint_each_epoch = 1
```

Important distinction:

```text
vN_epoch_checkpoint.keras = latest epoch checkpoint, may exist while training is still running.
vN_model.keras = final model, exists only after training finishes successfully.
```

---

## RAM-safe stream loader — 2026-09-17

The operator reported RAM usage around 27GB on a 32GB system. The previous trainer loaded the selected tensor subset into RAM and then created a normalized copy:

```text
x_loaded = np.asarray(x_all[indices], dtype=float32)
x_norm = normalized copy
```

This doubles memory pressure for large 4D tensors.

Fix:

```text
--loader-mode stream
--stream-chunk-size 256
```

Behavior:

```text
The tensor remains memory-mapped on disk.
Scaler mean/std are computed by streaming chunks.
Each training batch is read from .npy, sanitized and normalized on demand.
No full x_loaded/x_norm copy is created in RAM.
```

This does not reduce the dataset or the model. It only changes how data is fed to Keras.

Both trainers support it:

```text
scripts/train_pivot_pattern_image_cnn.py
scripts/train_pivot_pattern_image_wavenet.py
```

Default mode is now:

```text
loader_mode = stream
```

---

## Batch-level training visibility — 2026-09-17

The operator reported that waiting until an epoch finishes gives no visibility during long training. The image CNN trainer now supports batch-level console and file logging:

```text
--batch-log-every N
--batch-log-file PATH
```

Default:

```text
--batch-log-every 10
--batch-log-file run_logs\pivot_pattern_image_cnn\latest_batch_log.jsonl
```

To print every batch:

```text
--batch-log-every 1
```

The batch logger prints and stores metrics such as:

```text
epoch
batch
global_batch
loss
action_loss
top_loss
bottom_loss
buy_r_loss
sell_r_loss
action_sparse_categorical_accuracy
```
