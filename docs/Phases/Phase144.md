# Phase144 — Advanced 4D Pivot Image WaveNet

**Status:** ✅ Phase144A implemented
**Type:** Advanced TensorFlow/Keras model for 4D pivot image tensor
**Production status:** Research-only; no paper/live permission

---

## Why this phase exists

The owner rejected the simple Conv2D baseline architecture because it did not include the intended professional components:

```text
Residual connections
SE/Attention blocks
dilated conv over time
separate 5M/HTF branches
temporal attention
multi-scale kernels
```

Phase144A implements the advanced architecture for the existing Phase143A 4D image tensor:

```text
X = [samples, WindowSize, Features_5M, Features_4H_1D]
```

Keras batch:

```text
[batch, WindowSize, Features_5M, Features_4H_1D]
```

---

## Implemented file

```text
scripts/train_pivot_pattern_image_wavenet.py
```

GUI command:

```text
Train advanced pivot image WaveNet
```

Tests:

```text
tests/unit/ai/test_pivot_image_wavenet_helpers.py
tests/unit/presentation/test_phase144_pivot_image_wavenet_gui.py
```

---

## Architecture

Input:

```text
[WindowSize, Features_5M, Features_4H_1D]
```

Default expected shape after Phase143A:

```text
[100, 32, 23]
```

Architecture stages:

```text
1. Pure 5M branch
   Extracts pure 5M feature sequence from HTF-bias column.
   Uses multi-scale temporal Conv1D kernels.

2. Pure 4H/1D branch
   Extracts pure HTF feature sequence from 5M-bias row.
   Uses multi-scale temporal Conv1D kernels.

3. Spatial interaction branch
   Adds channel axis and applies TimeDistributed Conv2D over
   [Features_5M, Features_4H_1D] at each 5M window step.
   Uses multi-scale spatial kernels.

4. Branch fusion
   Concatenates 5M branch + HTF branch + spatial interaction branch.

5. Temporal WaveNet core
   Gated tanh-sigmoid causal dilated Conv1D residual blocks over WindowSize.
   Dilation schedule defaults to 1,2,4,8,16,32.
   Includes residual connections and skip connections.

6. SE channel attention
   Squeeze-excitation block inside each residual WaveNet block.

7. Temporal self-attention
   MultiHeadAttention over the temporal sequence after WaveNet skips.

8. Temporal pooling
   GlobalAveragePooling1D + GlobalMaxPooling1D + last temporal state.

9. Multi-head outputs
   action softmax: SELL/HOLD/BUY
   top sigmoid
   bottom sigmoid
   buy_r regression
   sell_r regression
```

---

## Activation decision

The owner asked whether `tanh` is better than `relu`.

Phase144A uses the WaveNet-style gated activation:

```text
tanh(filter) * sigmoid(gate)
```

This is closer to classic WaveNet than plain ReLU. The general branch activation is configurable:

```text
--activation tanh|swish|gelu
```

Default:

```text
--activation tanh
```

---

## Command

Because this model is heavier than the Conv2D baseline and the operator machine has 32GB RAM, start with a controlled run:

```powershell
python -u scripts/train_pivot_pattern_image_wavenet.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --tensor-path datasets\processed\XAUUSD\5M\pivot_pattern_image_tensor_latest.npy `
  --meta-path datasets\processed\XAUUSD\5M\pivot_pattern_image_tensor_latest_meta.npz `
  --model-id gold_pivot_pattern_image_wavenet_5m `
  --train-frac 0.70 `
  --val-frac 0.15 `
  --purge-gap 336 `
  --max-samples 12000 `
  --batch-size 8 `
  --epochs 20 `
  --learning-rate 0.0005 `
  --spatial-filters 24 `
  --branch-filters 24 `
  --temporal-filters 48 `
  --spatial-kernels 1,3,5 `
  --temporal-kernels 3,5,9 `
  --dilations 1,2,4,8,16,32 `
  --residual-blocks 2 `
  --attention-heads 4 `
  --attention-key-dim 16 `
  --se-ratio 8 `
  --dense-units 128 `
  --dropout 0.25 `
  --activation tanh `
  --action-loss-weight 1.0 `
  --top-loss-weight 0.5 `
  --bottom-loss-weight 0.5 `
  --r-loss-weight 0.5 `
  --class-weight auto `
  --buy-threshold 0.34 `
  --sell-threshold 0.34 `
  --min-margin 0 `
  --min-buy-r -999 `
  --min-sell-r -999 `
  --early-stopping-patience 6 `
  --checkpoint-each-epoch 1 `
  --save-model 1 `
  --storage-root datasets `
  --output-dir run_logs\pivot_pattern_image_wavenet `
  --report-title "Advanced Pivot Image WaveNet controlled training"
```

Output model files:

```text
datasets\models\gold_pivot_pattern_image_wavenet_5m\vN_model.keras
datasets\models\gold_pivot_pattern_image_wavenet_5m\vN_training.json
datasets\models\gold_pivot_pattern_image_wavenet_5m\vN_architecture.json
datasets\models\gold_pivot_pattern_image_wavenet_5m\vN_summary.txt
datasets\models\gold_pivot_pattern_image_wavenet_5m\vN_epoch_checkpoint.keras
```

Run-log files:

```text
run_logs\pivot_pattern_image_wavenet\latest.json
run_logs\pivot_pattern_image_wavenet\latest.html
run_logs\pivot_pattern_image_wavenet\latest_architecture.json
run_logs\pivot_pattern_image_wavenet\latest_summary.txt
run_logs\pivot_pattern_image_wavenet\latest_training_log.csv
```

---

## Acceptance

Implementation acceptance:

```text
Advanced architecture exists
GUI command exists
Architecture/summary/checkpoints are saved
Targeted tests pass
```

Trading acceptance still requires real training, backtest, and walk-forward validation. Until then:

```text
No Phase134.
No paper shadow.
No live trading.
```

---

## RAM-safe stream loader — 2026-09-17

Phase144A advanced Image WaveNet is heavier than the Conv2D baseline, so it now defaults to stream loading:

```text
--loader-mode stream
--stream-chunk-size 256
```

This keeps the full 4D tensor on disk and feeds normalized batches to Keras on demand. It does not reduce model size or dataset size.

---

## Batch-level training visibility — 2026-09-17

Advanced Image WaveNet training can now print and save batch-level progress before an epoch finishes:

```text
--batch-log-every N
--batch-log-file PATH
```

Default:

```text
--batch-log-every 10
--batch-log-file run_logs\pivot_pattern_image_wavenet\latest_batch_log.jsonl
```

Use this for full per-batch visibility:

```text
--batch-log-every 1
```

This writes JSON lines to the batch log and prints compact batch metrics to console. It does not change the model or dataset.

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

