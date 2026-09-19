# Phase144A Report — Advanced 4D Pivot Image WaveNet

Date: 2026-09-17

## Goal

Build the real professional architecture requested by the owner for the 4D pivot image tensor, instead of the simple Conv2D baseline.

Required components:

```text
Residual connections
SE/Attention blocks
dilated conv over time
separate 5M/HTF branches
temporal attention
multi-scale kernels
activation=tanh / gated WaveNet activation
```

## Implemented

```text
scripts/train_pivot_pattern_image_wavenet.py
```

GUI:

```text
Train advanced pivot image WaveNet
```

Tests:

```text
tests/unit/ai/test_pivot_image_wavenet_helpers.py
tests/unit/presentation/test_phase144_pivot_image_wavenet_gui.py
```

## Input shape

```text
Stored X:    [samples, WindowSize, Features_5M, Features_4H_1D]
Keras batch: [batch, WindowSize, Features_5M, Features_4H_1D]
```

Example from operator dataset:

```text
[batch, 100, 32, 23]
```

## Architecture implemented

```text
Input [100, 32, 23]
│
├── pure 5M branch
│   └── Lambda: x[:, :, :, 0]
│   └── multi-scale causal Conv1D kernels: 3,5,9
│
├── pure HTF branch
│   └── Lambda: x[:, :, 0, :]
│   └── multi-scale causal Conv1D kernels: 3,5,9
│
├── spatial interaction branch
│   └── reshape to [time, F5, FHTF, 1]
│   └── TimeDistributed Conv2D kernels: 1,3,5
│   └── TimeDistributed GlobalAveragePooling2D
│
├── branch fusion
│
├── WaveNet temporal core
│   └── gated tanh-sigmoid Conv1D
│   └── causal dilations: 1,2,4,8,16,32
│   └── residual connections
│   └── skip connections
│   └── SE channel attention
│
├── temporal MultiHeadAttention
│
├── pooling
│   └── average pool + max pool + last temporal state
│
└── heads
    ├── action softmax SELL/HOLD/BUY
    ├── top sigmoid
    ├── bottom sigmoid
    ├── buy_r linear
    └── sell_r linear
```

## Tanh decision

Plain `tanh` everywhere can saturate. The implemented WaveNet block uses the canonical gated form:

```text
tanh(filter) * sigmoid(gate)
```

General branch activation is configurable:

```text
--activation tanh|swish|gelu
```

Default:

```text
--activation tanh
```

## Checkpoint behavior

This model also supports epoch checkpointing:

```text
--checkpoint-each-epoch 1
```

During training:

```text
vN_epoch_checkpoint.keras
vN_architecture.json
vN_summary.txt
latest_training_log.csv
```

After training finishes:

```text
vN_model.keras
vN_training.json
```

## Verification

```text
python -m ruff check scripts/train_pivot_pattern_image_wavenet.py tests/unit/ai/test_pivot_image_wavenet_helpers.py tests/unit/presentation/test_phase144_pivot_image_wavenet_gui.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py
→ passed

python -m black --check scripts/train_pivot_pattern_image_wavenet.py tests/unit/ai/test_pivot_image_wavenet_helpers.py tests/unit/presentation/test_phase144_pivot_image_wavenet_gui.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py
→ passed

python -m pytest tests/unit/ai/test_pivot_image_wavenet_helpers.py tests/unit/presentation/test_phase144_pivot_image_wavenet_gui.py tests/integration/test_gui_coverage.py::TestEveryRunHasAButton::test_every_command_kind_has_a_handler tests/integration/test_gui_coverage.py::TestEveryRunHasAButton::test_every_command_kind_has_a_descriptor tests/integration/test_gui_coverage.py::TestDashboardPage::test_every_button_is_rendered -q
→ passed
```

Full real training was not run in the sandbox. It must run on the operator machine with the real 4D tensor and TensorFlow runtime.

## Production status

```text
No Phase134.
No paper shadow.
No live trading.
```

## Full gate status

```text
python -m pytest -q
→ passed

python -m pytest --collect-only
→ 1908 tests collected
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

Added stream loading to avoid full RAM copies of the 4D tensor:

```text
--loader-mode stream
--stream-chunk-size 256
```

Use this mode by default on the operator's 32GB RAM system.

## RAM-safe stream loader implementation — 2026-09-17

Added memory-safe stream loading to Phase144A:

```text
--loader-mode stream
--stream-chunk-size 256
```

Old memory-heavy path:

```text
x_loaded = full selected tensor in RAM
x_norm = second normalized full copy in RAM
```

New path:

```text
X stays on disk as .npy memmap
scaler is computed chunk-by-chunk
only current batch is read and normalized
model and dataset size are unchanged
```

Use stream mode on the 32GB RAM operator machine.

Verification:

```text
Targeted ruff/black/tests
→ passed

python -m pytest -q
→ passed

python -m pytest --collect-only
→ 1909 tests collected
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

## Batch-level training visibility — 2026-09-17

Added to `scripts/train_pivot_pattern_image_wavenet.py`:

```text
--batch-log-every
--batch-log-file
```

Default output:

```text
run_logs\pivot_pattern_image_wavenet\latest_batch_log.jsonl
```

For per-batch console output:

```text
--batch-log-every 1
```

This is useful because one epoch can take a long time on the 4D tensor.

## Phase144A operator result — advanced 4D Image WaveNet v1 — 2026-09-19

The owner supplied `run_logs\pivot_pattern_image_wavenet\latest.json` for the first full operator-machine run of the advanced 4D Image WaveNet.

Run configuration summary:

```text
model_id          : gold_pivot_pattern_image_wavenet_5m
version           : 1
tensor            : datasets\processed\XAUUSD\5M\pivot_pattern_image_tensor_latest.npy
meta              : datasets\processed\XAUUSD\5M\pivot_pattern_image_tensor_latest_meta.npz
stored_x_shape    : [12000, 100, 32, 23]
keras_batch_shape : [batch, 100, 32, 23]
loader_mode       : stream
batch_size        : 8
epochs requested  : 20
learning_rate     : 0.0005
nonfinite_input_values : 0
```

Validation metrics:

```text
val_action_accuracy : 0.5628415301
val_top_ap          : 0.2038051024
val_bottom_ap       : 0.1501470022
val_buy_r_mae       : 0.6300964952
val_sell_r_mae      : 0.6807333231
val_selected_rate   : 0.4187158470
```

Test metrics:

```text
test_action_accuracy : 0.5969945355
test_top_ap          : 0.2327647696
test_bottom_ap       : 0.2356605000
test_buy_r_mae       : 0.6400972009
test_sell_r_mae      : 0.6506559253
test_selected_rate   : 0.4009562842
```

Interpretation:

```text
GOOD:
- The sanitized/streamed 4D pipeline is numerically healthy: nonfinite_input_values=0.
- The advanced WaveNet is not a dead/no-trade model: selected_rate is ~41.87% validation and ~40.10% test.
- Action/top/bottom heads materially improved versus the rejected simple Conv2D sanity run.

LIMITS:
- This is still a research classifier/pattern model, not a trading system.
- No PnL, spread/slippage, TP/SL, max-hold, or walk-forward trading validation is present in this report.
- The gate is intentionally loose: buy_threshold=0.34, sell_threshold=0.34, min_margin=0, min_buy_r=-999, min_sell_r=-999.
- R-head MAE did not materially improve; buy_r/sell_r heads are not yet reliable as trading filters.
- The run uses max_samples=12000, not the full tensor.
```

Decision:

```text
Phase144A v1 is a useful research improvement over the simple Conv2D baseline, but production remains BLOCKED.
Next required evidence is backtest/walk-forward or comparison against Phase145A Option A sequence WaveNet.
No Phase134. No paper shadow. No live trading.
```

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

