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

## Phase147A Option B training result and Step2 backtest support — 2026-09-19

The owner supplied the first Phase147A Option B training result.

Training input:

```text
model_id          : gold_pivot_pattern_sequence_wavenet_option_b_5m
version           : 1
stored_x_shape    : [24000, 100, 140]
inputs:
  m5_context_input  : [batch, 100, 35]
  source_5m_input   : [batch, 100, 83]
  htf_context_input : [batch, 100, 22]
nonfinite_input_values : 0
```

Final restored metrics:

```text
val_action_accuracy : 0.7273284314
val_top_ap          : 0.4791975234
val_bottom_ap       : 0.2816134870
val_buy_r_mae       : 0.6719624400
val_sell_r_mae      : 0.6719951034
val_selected_rate   : 0.2846200980

test_action_accuracy : 0.6544117647
test_top_ap          : 0.2636572717
test_bottom_ap       : 0.2550490406
test_buy_r_mae       : 0.8204818964
test_sell_r_mae      : 0.8204245567
test_selected_rate   : 0.3134191176
```

A/B diagnostic comparison so far:

```text
Option A full-source [24000,100,140]
  test_action_accuracy : 0.6201
  test_top_ap          : 0.2709
  test_bottom_ap       : 0.3336
  test_buy/sell_r_mae  : ~0.736 / ~0.735
  test_selected_rate   : 0.3609
  test PnL             : +0.8956, PF=1.0184, maxDD=7.2327

Option B grouped inputs [24000,100,140]
  test_action_accuracy : 0.6544  ← better
  test_top_ap          : 0.2637  ← slightly worse
  test_bottom_ap       : 0.2550  ← worse
  test_buy/sell_r_mae  : ~0.820 / ~0.820  ← worse
  test_selected_rate   : 0.3134  ← more selective
  test PnL             : not yet run
```

Interpretation:

```text
Option B improved action classification but weakened bottom-zone AP and R-head MAE.
Because Phase146A showed PnL is very sensitive and weak, the next decision cannot be made from classifier metrics only.
Step 2 now requires a fair Option B PnL audit with the same rules used for Option A.
```

Implemented Step 2 support:

```text
scripts/backtest_pivot_pattern_sequence_wavenet.py
```

now detects Option B records and feeds grouped prediction inputs automatically. The same GUI command can be used:

```text
Backtest pivot sequence WaveNet PnL
```

Recommended Option B backtest command:

```powershell
python -u scripts\backtest_pivot_pattern_sequence_wavenet.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --tensor-path datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_latest.npy `
  --meta-path datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_latest_meta.npz `
  --flat-path datasets\processed\XAUUSD\5M\pivot_pattern_sequence_flat_latest.parquet `
  --model-id gold_pivot_pattern_sequence_wavenet_option_b_5m `
  --model-version 0 `
  --max-samples 24000 `
  --eval-split test `
  --train-frac 0.70 `
  --val-frac 0.15 `
  --purge-gap 336 `
  --max-windows 0 `
  --batch-size 128 `
  --buy-threshold 0.34 `
  --sell-threshold 0.34 `
  --min-margin 0 `
  --top-threshold 0 `
  --bottom-threshold 0 `
  --min-buy-r -999 `
  --min-sell-r -999 `
  --tp-multiplier 0.75 `
  --sl-multiplier 0.75 `
  --hold-bars 48 `
  --spread-mode pct `
  --spread-value 0.06 `
  --same-bar-policy stop_first `
  --initial-capital 100 `
  --risk-per-trade 0.01 `
  --storage-root datasets `
  --output-dir run_logs\pivot_pattern_sequence_wavenet_option_b_backtest `
  --report-title "Phase147B Option B sequence WaveNet PnL audit"
```

Verification after adding Option B backtest support:

```text
python -m py_compile scripts/train_pivot_pattern_sequence_wavenet_option_b.py scripts/backtest_pivot_pattern_sequence_wavenet.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py
→ passed

python -m pytest tests/unit/ai/test_pivot_sequence_tensor.py tests/unit/ai/test_pivot_sequence_tensor_health.py tests/unit/ai/test_pivot_sequence_wavenet_helpers.py tests/unit/ai/test_pivot_sequence_wavenet_backtest.py tests/unit/ai/test_pivot_sequence_wavenet_option_b.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ 56 passed
```

Decision:

```text
Step 1 is complete: Option B is built and trained.
Step 2 is now active: run Option B PnL audit and compare against Option A using the same replay rules.
No Phase134. No paper shadow. No live trading.
```
