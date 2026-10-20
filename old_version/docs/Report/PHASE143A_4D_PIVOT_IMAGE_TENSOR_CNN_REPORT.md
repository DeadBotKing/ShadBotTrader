# Phase143A Report — 4D Pivot Image Tensor + Conv2D/Conv3D

Date: 2026-09-16

## Goal

Correct the tensor design to the owner-requested 4D image/volume-like layout:

```text
[samples, WindowSize, Features_5M, Features_4H_1D]
```

Default roll-forward:

```text
WindowSize = 100
Stride = 1
```

## Implemented

```text
scripts/build_pivot_pattern_image_tensor.py
scripts/train_pivot_pattern_image_cnn.py
```

GUI:

```text
Build pivot image tensor
Train pivot image CNN
```

## Tensor semantics

```text
X[t, f5, htf] = feature_5M[t, f5] * feature_4H_1D[t, htf]
```

Bias feature is added to both axes so pure 5M and pure HTF features are preserved.

## Shapes

```text
Stored X      : [samples, WindowSize, Features_5M, Features_4H_1D]
Conv2D batch  : [batch, WindowSize, Features_5M, Features_4H_1D]
Conv3D batch  : [batch, WindowSize, Features_5M, Features_4H_1D, 1]
```

## Smoke verification

```text
TESTSYM smoke:
Stored X      : [160, 20, 5, 4]
Conv2D batch  : [batch, 20, 5, 4]
Conv3D batch  : [batch, 20, 5, 4, 1]
```

## Outputs

```text
datasets\processed\XAUUSD\5M\pivot_pattern_image_tensor_latest.npy
datasets\processed\XAUUSD\5M\pivot_pattern_image_tensor_latest_meta.npz
datasets\processed\XAUUSD\5M\pivot_pattern_image_flat_latest.parquet
run_logs\pivot_pattern_image_tensor\latest.json
run_logs\pivot_pattern_image_tensor\latest.html

datasets\models\gold_pivot_pattern_image_cnn_5m\v*_model.keras
datasets\models\gold_pivot_pattern_image_cnn_5m\v*_training.json
run_logs\pivot_pattern_image_cnn\latest.json
run_logs\pivot_pattern_image_cnn\latest.html
```

## Verification

```text
python -m ruff check scripts/build_pivot_pattern_image_tensor.py scripts/train_pivot_pattern_image_cnn.py tests/unit/ai/test_pivot_pattern_image_tensor.py tests/unit/presentation/test_phase143_pivot_image_cnn_gui.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py
→ passed

python -m black --check scripts/build_pivot_pattern_image_tensor.py scripts/train_pivot_pattern_image_cnn.py tests/unit/ai/test_pivot_pattern_image_tensor.py tests/unit/presentation/test_phase143_pivot_image_cnn_gui.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py
→ passed

targeted pytest for Phase143 and GUI coverage
→ passed
```

## Status

This is an implementation correction. Real XAUUSD training/backtest must be run by the operator after replacing the local project with the new zip.

Production remains blocked.

## Full gate status

```text
python -m pytest -q
→ passed

python -m pytest --collect-only
→ 1898 tests collected
```

Known full-repository debt remains:

```text
python -m ruff check .
→ 219 pre-existing errors

python -m black --check .
→ 21 pre-existing files would be reformatted

python -m mypy src
→ 28 pre-existing errors in 10 files
```

## Feature-axis correction — 2026-09-17

The initial 4D tensor feature budget was intentionally conservative for smoke/memory safety:

```text
13 × 9 axes after bias
```

The owner correctly noted that this is too small for the intended Pattern Recognition model.

Updated defaults:

```text
max_5m_features  = 24 + bias = 25
max_htf_features = 16 + bias = 17
max_tensor_mb    = 8192
```

Estimated full XAUUSD tensor with about 53,198 5M rows:

```text
[53,099, 100, 25, 17] float16 ≈ 4.3 GB
```

The model can be expanded by operator command if hardware allows:

```text
--max-5m-features 32
--max-htf-features 24
--max-tensor-mb 12288
```

## Feature-axis correction verification — 2026-09-17

```text
python -m ruff check scripts/build_pivot_pattern_image_tensor.py tests/unit/presentation/test_phase143_pivot_image_cnn_gui.py src/ShadBotTrader/presentation/commands/handlers.py src/ShadBotTrader/presentation/commands/commands.py
→ passed

python -m black --check scripts/build_pivot_pattern_image_tensor.py tests/unit/presentation/test_phase143_pivot_image_cnn_gui.py src/ShadBotTrader/presentation/commands/handlers.py src/ShadBotTrader/presentation/commands/commands.py
→ passed

python -m pytest tests/unit/ai/test_pivot_pattern_image_tensor.py tests/unit/presentation/test_phase143_pivot_image_cnn_gui.py tests/integration/test_gui_coverage.py::TestEveryRunHasAButton::test_every_command_kind_has_a_handler tests/integration/test_gui_coverage.py::TestEveryRunHasAButton::test_every_command_kind_has_a_descriptor tests/integration/test_gui_coverage.py::TestDashboardPage::test_every_button_is_rendered -q
→ passed

python -m pytest -q
→ passed

python -m pytest --collect-only
→ 1898 tests collected
```

Known full-repository debt remains unchanged:

```text
python -m ruff check .
→ 219 pre-existing errors

python -m black --check .
→ 21 pre-existing files would be reformatted

python -m mypy src
→ 28 pre-existing errors in 10 files
```

## Operator sanity-training result — Conv2D, 12k samples — 2026-09-17

The operator trained the Phase143A Conv2D model on the generated 4D tensor.

Configuration:

```text
model_kind      : conv2d
max_samples     : 12,000
batch_size      : 32
epochs          : 10
train_rows      : 8,400
validation_rows : 1,464
test_rows       : 1,464
stored_x_shape  : [12,000, 100, 32, 23]
keras_batch     : [batch, 100, 32, 23]
```

Result metrics:

```text
val_action_accuracy  : 0.1441256831
test_action_accuracy : 0.3743169399
val_top_ap           : 0.1158035542
test_top_ap          : 0.1216554847
val_bottom_ap        : 0.0776606503
test_bottom_ap       : 0.1012060929
val_buy_r_mae        : 0.6302291751
test_buy_r_mae       : 0.6286138892
val_sell_r_mae       : 0.6221737862
test_sell_r_mae      : 0.6242960691
val_selected_rate    : 0.0
test_selected_rate   : 0.0
```

Model artifact:

```text
datasets\models\gold_pivot_pattern_image_cnn_5m\v1_model.keras
datasets\models\gold_pivot_pattern_image_cnn_5m\v1_training.json
```

Interpretation:

```text
The first Conv2D sanity training completed, so the 4D tensor can be consumed by Keras.
However, the trained model is not actionable: selected_rate is zero on both validation and test.
```

Decision:

```text
FAILED as signal model / no-trade under current threshold gate.
```

Next diagnostic:

```text
Run a lower-threshold diagnostic or add probability-distribution diagnostics before spending time on full 120-epoch training.
```

## Sanitization + architecture artifact correction — 2026-09-17

The operator inspected the saved training record and found:

```text
scaler_mean: Infinity
scaler_std : NaN
```

This invalidates the first Conv2D sanity artifact:

```text
datasets\models\gold_pivot_pattern_image_cnn_5m\v1_model.keras
```

Root cause:

```text
Raw 5M × raw 4H/1D interaction values were cast to float16 before being normalized.
Some values overflowed to Infinity, then scaler statistics were fitted on the
poisoned tensor.
```

Fixes implemented:

```text
build_pivot_pattern_image_tensor.py
  --axis-normalization {robust,standard,none}, default=robust
  --feature-clip FLOAT, default=8
  --interaction-clip FLOAT, default=32
  stores nonfinite_feature_values and nonfinite_interaction_values
  stores axis centers/scales in meta npz

train_pivot_pattern_image_cnn.py
  sanitizes nonfinite tensor values before fitting scaler
  forces saved scaler_mean/scaler_std to finite values
  saves architecture artifacts:
    v*_architecture.json
    v*_summary.txt
    latest_architecture.json
    latest_summary.txt
```

Decision:

```text
Reject Phase143A Conv2D v1. Rebuild tensor and retrain v2+.
```

## Sanitization fix verification — 2026-09-17

```text
python -m ruff check scripts/build_pivot_pattern_image_tensor.py scripts/train_pivot_pattern_image_cnn.py tests/unit/ai/test_pivot_pattern_image_tensor.py tests/unit/presentation/test_phase143_pivot_image_cnn_gui.py src/ShadBotTrader/presentation/commands/handlers.py src/ShadBotTrader/presentation/commands/commands.py
→ passed

python -m black --check scripts/build_pivot_pattern_image_tensor.py scripts/train_pivot_pattern_image_cnn.py tests/unit/ai/test_pivot_pattern_image_tensor.py tests/unit/presentation/test_phase143_pivot_image_cnn_gui.py src/ShadBotTrader/presentation/commands/handlers.py src/ShadBotTrader/presentation/commands/commands.py
→ passed

python -m pytest tests/unit/ai/test_pivot_pattern_image_tensor.py tests/unit/presentation/test_phase143_pivot_image_cnn_gui.py tests/integration/test_gui_coverage.py::TestEveryRunHasAButton::test_every_command_kind_has_a_handler tests/integration/test_gui_coverage.py::TestEveryRunHasAButton::test_every_command_kind_has_a_descriptor tests/integration/test_gui_coverage.py::TestDashboardPage::test_every_button_is_rendered -q
→ passed

python -m pytest -q
→ passed

python -m pytest --collect-only
→ 1899 tests collected
```

Known full-repository debt remains unchanged:

```text
python -m ruff check .
→ 219 pre-existing errors

python -m black --check .
→ 21 pre-existing files would be reformatted

python -m mypy src
→ 28 pre-existing errors in 10 files
```

## Official tensor health audit implementation — 2026-09-17

Added:

```text
scripts/audit_pivot_pattern_image_tensor.py
GUI: Audit pivot image tensor health
```

Purpose:

```text
Promote the manual dataset-health snippet into a repeatable project command.
```

The audit checks:

```text
rank-4 tensor shape
metadata/sample alignment
target length and finite values
axis scaler finite values
full tensor NaN/Inf scan
max_abs <= interaction_clip
builder nonfinite diagnostics
```

The operator stated that the dataset health test passed. The canonical artifact path for future runs is:

```text
run_logs\pivot_pattern_image_tensor_health\latest.json
```

## Epoch-checkpoint correction — 2026-09-17

The operator observed that after one epoch completed, no model folder existed. This was expected under the old implementation because final model saving happened only after all epochs finished.

Fix implemented:

```text
train_pivot_pattern_image_cnn.py
  --checkpoint-each-epoch 1
```

The trainer now creates the model directory before training and writes:

```text
vN_architecture.json
vN_summary.txt
vN_epoch_checkpoint.keras
```

After training finishes:

```text
vN_model.keras
vN_training.json
```

This prevents losing all progress if a long run is interrupted after one or more epochs.

## Epoch-checkpoint verification — 2026-09-17

```text
Targeted ruff/black/tests
→ passed

python -m pytest -q
→ passed

python -m pytest --collect-only
→ 1904 tests collected
```

Known full-repository debt remains unchanged:

```text
python -m ruff check .
→ 219 pre-existing errors

python -m black --check .
→ 21 pre-existing files would be reformatted

python -m mypy src
→ 28 pre-existing errors in 10 files
```

## RAM-safe stream loader — 2026-09-17

To reduce RAM without reducing dataset/model size, both image-tensor trainers now support streaming batches from the `.npy` memmap:

```text
--loader-mode stream
--stream-chunk-size 256
```

Old behavior:

```text
load selected X into RAM
create normalized full copy
train from memory
```

New behavior:

```text
keep tensor on disk as memmap
compute scaler in chunks
load/normalize only the current batch
train from Sequence generator
```

This is the correct mode for a 32GB RAM workstation.

## RAM-safe stream loader implementation — 2026-09-17

The Conv2D/Conv3D baseline trainer also supports:

```text
--loader-mode stream
--stream-chunk-size 256
```

This keeps the full image tensor on disk and feeds Keras batches from the memory-mapped `.npy` file, reducing RAM without reducing model/dataset size.

## Batch-level training visibility — 2026-09-17

Added to `scripts/train_pivot_pattern_image_cnn.py`:

```text
--batch-log-every
--batch-log-file
```

Default output:

```text
run_logs\pivot_pattern_image_cnn\latest_batch_log.jsonl
```

Setting `--batch-log-every 1` prints every train batch and writes each batch's metrics to JSONL.

## Phase143A 4D image tensor health PASS — 2026-09-19

The owner supplied `run_logs\pivot_pattern_image_tensor_health\latest.json` after running the official tensor health audit for the rebuilt 4D pivot image tensor.

Audit command inputs:

```text
tensor_path    : datasets\processed\XAUUSD\5M\pivot_pattern_image_tensor_latest.npy
meta_path      : datasets\processed\XAUUSD\5M\pivot_pattern_image_tensor_latest_meta.npz
flat_path      : datasets\processed\XAUUSD\5M\pivot_pattern_image_flat_latest.parquet
builder_report : run_logs\pivot_pattern_image_tensor\latest.json
full_scan      : 1
chunk_size     : 256
```

Result:

```text
status       : PASS
tensor_shape : [53098, 100, 32, 23]
dtype        : float16
flat_rows    : 53197
sample index : min=99 max=53196 step=1
first time   : 2025-11-28 17:05:00+00:00
last time    : 2026-09-02 10:25:00+00:00
```

Full tensor scan:

```text
scanned_cells     : 3,908,012,800
chunks            : 208
nonfinite_cells   : 0
min_value         : -32.0
max_value         : 32.0
max_abs           : 32.0
interaction_clip  : 32.0
warnings          : []
errors            : []
```

Target counts on sampled windows:

```text
SELL : 5,384
HOLD : 43,252
BUY  : 4,462
```

Interpretation:

```text
- The 4D image tensor is structurally healthy.
- The full tensor scan found no NaN/Inf cells.
- max_abs equals interaction_clip, so clipping is active and within the configured bound.
- sample_indices are strictly contiguous with stride=1 from 99 to 53196.
- feature_5m_names length matches axis 2: 32.
- feature_htf_names length matches axis 3: 23.
```

Note on target-count difference versus builder report:

```text
Builder target_counts were computed on the flat frame after target availability.
Health-audit target_counts are computed on the sampled tensor windows.
Because window_size=100, the first 99 flat rows are not tensor samples, so small count differences are expected and not an error.
```

Decision:

```text
Phase143A rebuilt 4D pivot image tensor is accepted as healthy for research training.
It is safe to train Phase144A advanced 4D Image WaveNet on this tensor.
Production remains BLOCKED until model backtest/walk-forward proves trading edge.
No Phase134. No paper shadow. No live trading.
```
