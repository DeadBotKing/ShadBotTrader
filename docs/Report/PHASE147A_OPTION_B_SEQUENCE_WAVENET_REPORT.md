# Phase147A Report — Option B Grouped Sequence WaveNet

Date: 2026-09-19

## Goal

Implement Step 1 of the owner-approved roadmap:

```text
Step 1 — Option B بسازیم
Step 2 — A/B benchmark منصفانه
Step 3 — آموزش بزرگ‌تر / full dataset
Step 4 — ذخیره کامل prediction/backtest archive
Step 5 — فیلترسازی، ولی با قانون ضد overfit
```

Phase147A implements Option B as a grouped-input sequence WaveNet.

## Implemented

```text
scripts/train_pivot_pattern_sequence_wavenet_option_b.py
```

GUI:

```text
Train pivot sequence WaveNet Option B
```

## Tensor source

Option B uses the existing healthy Phase145A full-source tensor:

```text
datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_latest.npy
shape: [53098, 100, 140]
```

Instead of passing `[batch,100,140]` to one input, the training sequence splits feature groups into three inputs:

```text
m5_context_input  : generated_5m + session
source_5m_input   : source_5m telemetry
htf_context_input : closed_4H + closed_1D
```

For the current tensor:

```text
m5_context_input  : [batch, 100, 35]
source_5m_input   : [batch, 100, 83]
htf_context_input : [batch, 100, 22]
```

## Architecture

```text
m5_context branch
source_5m branch
htf_context branch
late fusion
gated tanh-sigmoid dilated WaveNet
residual/skip connections
SE channel attention
temporal self-attention
avg/max/last pooling
action/top/bottom/buy_r/sell_r heads
```

No Lambda layers are needed for the grouped inputs or last-timestep pooling.

## First command

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

## Verification

```text
python -m py_compile scripts/train_pivot_pattern_sequence_wavenet_option_b.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py
→ passed

python -m pytest tests/unit/ai/test_pivot_sequence_tensor.py tests/unit/ai/test_pivot_sequence_tensor_health.py tests/unit/ai/test_pivot_sequence_wavenet_helpers.py tests/unit/ai/test_pivot_sequence_wavenet_backtest.py tests/unit/ai/test_pivot_sequence_wavenet_option_b.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ 54 passed
```

## Production status

```text
BLOCKED — research only.
No Phase134.
No paper shadow.
No live trading.
```
