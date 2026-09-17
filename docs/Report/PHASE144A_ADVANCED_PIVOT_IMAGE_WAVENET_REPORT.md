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
