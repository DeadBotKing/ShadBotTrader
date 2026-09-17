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
