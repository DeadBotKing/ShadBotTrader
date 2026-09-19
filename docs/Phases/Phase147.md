# Phase147 — Option B Grouped Sequence WaveNet and A/B Roadmap

**Status:** ✅ Phase147A Step 1 implemented  
**Type:** Option B architecture for pivot sequence tensor research  
**Production status:** BLOCKED — research only

---

## Why this phase exists

The owner correctly restated the intended roadmap after Phase146A:

```text
Step 1 — Option B بسازیم
Step 2 — A/B benchmark منصفانه
Step 3 — آموزش بزرگ‌تر / full dataset
Step 4 — ذخیره کامل prediction/backtest archive
Step 5 — فیلترسازی، ولی با قانون ضد overfit
```

Phase147A implements Step 1.

---

## Option A recap

Option A uses one feature axis:

```text
Stored X    : [samples, WindowSize, Features]
Keras batch : [batch, WindowSize, Features]
```

Current healthy full-source tensor:

```text
[53098, 100, 140]
```

Option A model input:

```text
[batch, 100, 140]
```

---

## Option B definition

Option B keeps the same stored tensor but feeds the model as grouped Keras inputs:

```text
m5_context_input  : [batch, WindowSize, generated_5m + session]
source_5m_input   : [batch, WindowSize, source_5m telemetry]
htf_context_input : [batch, WindowSize, closed_4H + closed_1D]
```

For the current tensor:

```text
m5_context_input  : [batch, 100, 35]
source_5m_input   : [batch, 100, 83]
htf_context_input : [batch, 100, 22]
```

This avoids forcing generated 5M context, source telemetry, and HTF context through one undifferentiated feature stream at the first layer.

---

## Implemented file

```text
scripts/train_pivot_pattern_sequence_wavenet_option_b.py
```

GUI:

```text
Train pivot sequence WaveNet Option B
```

Tests:

```text
tests/unit/ai/test_pivot_sequence_wavenet_option_b.py
tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py
```

---

## Architecture

```text
Stored tensor [samples, 100, 140]
│
├── m5_context_input [batch,100,35]
│   └── multi-scale causal Conv1D kernels 3,5,9
│
├── source_5m_input [batch,100,83]
│   └── multi-scale causal Conv1D kernels 3,5,9
│
├── htf_context_input [batch,100,22]
│   └── multi-scale causal Conv1D kernels 3,5,9
│
├── late fusion
│
├── gated tanh-sigmoid dilated WaveNet
│   └── dilations 1,2,4,8,16,32
│   └── residual connections
│   └── skip connections
│   └── SE/channel attention
│
├── temporal self-attention
│
├── avg/max/last pooling
│
└── heads:
    ├── action SELL/HOLD/BUY
    ├── top
    ├── bottom
    ├── buy_r
    └── sell_r
```

No Keras Lambda layers are used in Option B for input grouping or last-state pooling.

---

## Step 1 command

```powershell
python -u scripts\train_pivot_pattern_sequence_wavenet_option_b.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --tensor-path datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_latest.npy `
  --meta-path datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_latest_meta.npz `
  --model-id gold_pivot_pattern_sequence_wavenet_option_b_5m `
  --train-frac 0.70 `
  --val-frac 0.15 `
  --purge-gap 336 `
  --max-samples 24000 `
  --stream-chunk-size 512 `
  --batch-size 16 `
  --epochs 80 `
  --learning-rate 0.0005 `
  --branch-filters 48 `
  --temporal-filters 96 `
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
  --early-stopping-patience 8 `
  --checkpoint-each-epoch 1 `
  --batch-log-every 10 `
  --save-model 1 `
  --storage-root datasets `
  --output-dir run_logs\pivot_pattern_sequence_wavenet_option_b `
  --report-title "Option B Pivot Sequence WaveNet training"
```

Outputs:

```text
datasets\models\gold_pivot_pattern_sequence_wavenet_option_b_5m\vN_model.keras
datasets\models\gold_pivot_pattern_sequence_wavenet_option_b_5m\vN_training.json
datasets\models\gold_pivot_pattern_sequence_wavenet_option_b_5m\vN_architecture.json
datasets\models\gold_pivot_pattern_sequence_wavenet_option_b_5m\vN_summary.txt
datasets\models\gold_pivot_pattern_sequence_wavenet_option_b_5m\vN_epoch_checkpoint.keras
run_logs\pivot_pattern_sequence_wavenet_option_b\latest.json
run_logs\pivot_pattern_sequence_wavenet_option_b\latest.html
run_logs\pivot_pattern_sequence_wavenet_option_b\latest_summary.txt
run_logs\pivot_pattern_sequence_wavenet_option_b\latest_architecture.json
run_logs\pivot_pattern_sequence_wavenet_option_b\latest_training_log.csv
run_logs\pivot_pattern_sequence_wavenet_option_b\latest_batch_log.jsonl
```

---

## Next roadmap

```text
Step 2 — A/B benchmark منصفانه
  Option A and B with same tensor, same sample count, same split, same backtest rules.

Step 3 — آموزش بزرگ‌تر / full dataset
  Winner or both models with max_samples=0, chronological split, early stopping.

Step 4 — ذخیره کامل prediction/backtest archive
  Per-sample predictions, decisions, trades, PnL, months, side breakdown.

Step 5 — فیلترسازی با قانون ضد overfit
  Discover filters on train/validation only; confirm on test/walk-forward.
```

---

## Verification

```text
python -m py_compile scripts/train_pivot_pattern_sequence_wavenet_option_b.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py
→ passed

python -m pytest tests/unit/ai/test_pivot_sequence_tensor.py tests/unit/ai/test_pivot_sequence_tensor_health.py tests/unit/ai/test_pivot_sequence_wavenet_helpers.py tests/unit/ai/test_pivot_sequence_wavenet_backtest.py tests/unit/ai/test_pivot_sequence_wavenet_option_b.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ 54 passed
```

## Production status

```text
No Phase134.
No paper shadow.
No live trading.
```
