# Phase142A/142B Report — 3D Pivot Tensor + Keras WaveNet

Date: 2026-09-16

## Owner correction

The owner correctly clarified that the intended model is not a flat sklearn baseline. It must be a real sequence Pattern Recognition model:

```text
3D tensor dataset
TensorFlow/Keras
WaveNet/TCN
window = 288
channels = engineered causal features
```

Shape clarification:

```text
Stored tensor X shape       : [samples, 288, channels]
Keras runtime batch X shape : [batch, 288, channels]
```

The phrase `[batch, samples, 288, channels]` would be a 4D layout and is not the normal input for Conv1D/WaveNet. In Keras, `samples` is represented by dataset length; the loader adds `batch`.

## Implemented files

```text
scripts/build_pivot_pattern_tensor.py
scripts/train_pivot_pattern_wavenet.py
scripts/backtest_pivot_pattern_wavenet.py
scripts/run_pivot_pattern_wavenet_walk_forward.py
```

Tests:

```text
tests/unit/ai/test_pivot_pattern_tensor.py
tests/unit/ai/test_pivot_wavenet_helpers.py
tests/unit/presentation/test_phase142_pivot_wavenet_gui.py
```

GUI commands:

```text
Build pivot pattern tensor
Train pivot WaveNet pattern model
Backtest pivot WaveNet pattern model
Run pivot WaveNet walk-forward
```

## Tensor builder

The tensor builder reads project storage by default:

```text
--source-mode storage
```

It uses:

```text
datasets\processed\XAUUSD\5M\v*.parquet
datasets\processed\XAUUSD\1D\v*.parquet
datasets\processed\XAUUSD\4H\v*.parquet if available
otherwise datasets\processed\XAUUSD\1H\v*.parquet -> 4H resample
```

Outputs:

```text
datasets\processed\XAUUSD\5M\pivot_pattern_tensor_latest.npz
datasets\processed\XAUUSD\5M\pivot_pattern_flat_latest.parquet
run_logs\pivot_pattern_tensor\latest.json
run_logs\pivot_pattern_tensor\latest.html
```

Tensor arrays:

```text
X                  : [samples, 288, channels]
sample_indices     : index into pivot_pattern_flat_latest.parquet
row_id             : original row id
timestamp          : sample timestamp
target_action      : SELL/HOLD/BUY
target_top_zone    : binary top zone
target_bottom_zone : binary bottom zone
target_buy_r       : clipped future_up_r - future_down_r
target_sell_r      : clipped future_down_r - future_up_r
```

Smoke test on internal TESTSYM with smaller window produced:

```text
X shape     : [238, 24, 57]
keras batch : [batch, 24, 57]
```

## Keras WaveNet trainer

The trainer requires TensorFlow/Keras:

```powershell
python -m pip install -r requirements-ai.txt
```

Architecture:

```text
Input [window, channels]
1x1 Conv1D projection
Residual causal dilated Conv1D blocks
Dilation schedule: 1,2,4,8,16,32 per block
GlobalAveragePooling1D + GlobalMaxPooling1D
Dense + Dropout
Multi-head outputs:
  action softmax: SELL/HOLD/BUY
  top sigmoid
  bottom sigmoid
  buy_r regression
  sell_r regression
```

Losses:

```text
action: SparseCategoricalCrossentropy
top/bottom: BinaryCrossentropy
buy_r/sell_r: Huber
```

Train output:

```text
datasets\models\gold_pivot_pattern_wavenet_5m\v*_model.keras
datasets\models\gold_pivot_pattern_wavenet_5m\v*_training.json
run_logs\pivot_pattern_wavenet\latest.json
run_logs\pivot_pattern_wavenet\latest.html
```

## Backtest

The backtest script loads a saved `.keras` model and its training record, applies train-only scaler statistics, predicts on tensor samples, and replays trades on the flat OHLC frame.

Replay uses:

```text
entry = next 5M open
TP/SL = previous 4H ATR * multipliers
single-position chronological logic
spread and same-bar policy
$100 initial balance
risk_per_trade percentage sizing
```

Outputs:

```text
run_logs\pivot_pattern_wavenet_backtest\latest.json
run_logs\pivot_pattern_wavenet_backtest\latest.html
run_logs\pivot_pattern_wavenet_backtest\latest_trades.csv
```

## Walk-forward

The walk-forward script trains a fresh Keras WaveNet per fold:

```text
train only on past samples
select thresholds/TP/SL/R gates on validation
test the next unseen period
```

Outputs:

```text
run_logs\pivot_pattern_wavenet_walk_forward\latest.json
run_logs\pivot_pattern_wavenet_walk_forward\latest.html
run_logs\pivot_pattern_wavenet_walk_forward\latest_folds.csv
run_logs\pivot_pattern_wavenet_walk_forward\latest_trades.csv
```

## Implementation verification

Targeted checks:

```text
python -m ruff check scripts/build_pivot_pattern_tensor.py scripts/train_pivot_pattern_wavenet.py scripts/backtest_pivot_pattern_wavenet.py scripts/run_pivot_pattern_wavenet_walk_forward.py tests/unit/ai/test_pivot_pattern_tensor.py tests/unit/ai/test_pivot_wavenet_helpers.py tests/unit/presentation/test_phase142_pivot_wavenet_gui.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py
→ passed

python -m black --check scripts/build_pivot_pattern_tensor.py scripts/train_pivot_pattern_wavenet.py scripts/backtest_pivot_pattern_wavenet.py scripts/run_pivot_pattern_wavenet_walk_forward.py tests/unit/ai/test_pivot_pattern_tensor.py tests/unit/ai/test_pivot_wavenet_helpers.py tests/unit/presentation/test_phase142_pivot_wavenet_gui.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py
→ passed

python -m pytest tests/unit/ai/test_pivot_pattern_tensor.py tests/unit/ai/test_pivot_wavenet_helpers.py tests/unit/presentation/test_phase142_pivot_wavenet_gui.py tests/integration/test_gui_coverage.py::TestEveryRunHasAButton::test_every_command_kind_has_a_handler tests/integration/test_gui_coverage.py::TestEveryRunHasAButton::test_every_command_kind_has_a_descriptor tests/integration/test_gui_coverage.py::TestDashboardPage::test_every_button_is_rendered -q
→ passed
```

Full training was not executed in this sandbox because the complete XAUUSD 5M/1H project-storage dataset and TensorFlow runtime are on the operator machine, not in this snapshot. The implementation now gives the correct commands for the operator to run on the real project data.

## Production status

```text
No Phase134.
No paper shadow.
No live trading.
```

Phase142 is a research implementation. Trading acceptance requires successful walk-forward results from:

```text
run_logs\pivot_pattern_wavenet_walk_forward\latest.json
```

## Full repository gate status

```text
python -m pytest -q
→ passed

python -m pytest --collect-only
→ 1890 tests collected
```

Known repository-wide debt remains:

```text
python -m ruff check .
→ still fails with pre-existing repository debt: 219 errors

python -m black --check .
→ still fails with pre-existing formatting debt: 21 files would be reformatted

python -m mypy src
→ still fails with pre-existing type debt: 28 errors in 10 files
```
