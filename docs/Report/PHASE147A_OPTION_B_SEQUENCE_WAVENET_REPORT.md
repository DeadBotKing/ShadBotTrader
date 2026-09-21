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

## Phase147B Option B PnL audit result / Step2 A-B benchmark — 2026-09-19

The owner supplied `run_logs\pivot_pattern_sequence_wavenet_option_b_backtest\latest.json`, completing Step 2's first fair PnL comparison between Option A and Option B under the same Phase146 replay rules.

Option B backtest configuration:

```text
model_id          : gold_pivot_pattern_sequence_wavenet_option_b_5m
model_version     : 1
tensor_shape      : [53098, 100, 140]
selected_samples  : 24000
eval_split        : test
evaluated_samples : 3264
evaluated period  : 2026-07-03 19:35:00+00:00 → 2026-08-06 19:20:00+00:00
buy_threshold     : 0.34
sell_threshold    : 0.34
min_margin        : 0
top_threshold     : 0
bottom_threshold  : 0
min_buy_r         : -999
min_sell_r        : -999
tp_multiplier     : 0.75
sl_multiplier     : 0.75
hold_bars         : 48
spread_mode/value : pct / 0.06
same_bar_policy   : stop_first
initial_capital   : 100
risk_per_trade    : 0.01
```

Option B aggregate result:

```text
trades             : 134
BUY / SELL trades  : 44 / 90
wins / losses      : 65 / 69
win_rate           : 48.5075%
final_balance      : 101.8764768367
return_percent     : +1.8764768367%
total_cash_pnl     : +1.8764768367
gross_profit       : 51.6444079174
gross_loss         : 49.7679310808
profit_factor      : 1.0377045378
max_drawdown_cash  : 7.7910373699
take_profit        : 41
stop_loss          : 41
timeout            : 52
```

Option B side breakdown:

```text
BUY cash PnL  : +1.9372472043
SELL cash PnL : -0.0607703677
```

Option B monthly result:

```text
2026-07 : +4.1183724559 / 106 trades
2026-08 : -2.2418956192 / 28 trades
positive_months : 1
negative_months : 1
```

Fair comparison against Option A under the same replay settings:

```text
Option A:
  trades        : 135
  final_balance : 100.8955889685
  return        : +0.8956%
  PF            : 1.0184
  maxDD         : 7.2327
  BUY PnL       : +1.7578
  SELL PnL      : -0.8622
  monthly       : Jul +0.6597, Aug +0.2358

Option B:
  trades        : 134
  final_balance : 101.8764768367
  return        : +1.8765%
  PF            : 1.0377
  maxDD         : 7.7910
  BUY PnL       : +1.9372
  SELL PnL      : -0.0608
  monthly       : Jul +4.1184, Aug -2.2419
```

Interpretation:

```text
GOOD:
- Option B improves net PnL and profit factor versus Option A.
- Option B nearly neutralizes the SELL-side loss seen in Option A.
- Option B has fewer timeouts and more take-profits than Option A.
- BUY remains positive.

LIMITS:
- Option B drawdown is slightly worse than Option A.
- Option B has one negative month: August -2.2419.
- PF=1.0377 is still thin; this is not production-grade.
- The result is still only one purged test split, not walk-forward.
```

Decision:

```text
Step 2 preliminary A/B benchmark: Option B is the current research winner by PnL/PF, but not by stability.
Proceed to Step 3 with Option B first: larger/full-dataset training with max_samples=0, still using chronological train/validation/test and early stopping.
Option A can be kept as a robustness comparison, but Option B gets priority.
No Phase134. No paper shadow. No live trading.
```

Recommended next Step 3 command:

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
  --max-samples 0 `
  --stream-chunk-size 512 `
  --batch-size 16 `
  --epochs 160 `
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
  --early-stopping-patience 12 `
  --checkpoint-each-epoch 1 `
  --batch-log-every 25 `
  --save-model 1 `
  --storage-root datasets `
  --output-dir run_logs\pivot_pattern_sequence_wavenet_option_b_full `
  --report-title "Option B Pivot Sequence WaveNet full-dataset training"
```

## Phase148A range-aware sequence archive implemented — 2026-09-19

Implemented Step 4 requested by the owner while Step 3 full Option B training is running.

Implemented:

```text
scripts/backtest_pivot_pattern_sequence_wavenet_range.py
GUI: Backtest sequence WaveNet range-aware archive
```

Purpose:

```text
Create a full prediction/backtest archive and calculate TP/SL from range forecasts rather than fixed ATR brackets.
```

Range source modes:

```text
--range-source auto    # use flat range columns when available, otherwise range models
--range-source flat    # use range columns from sequence flat parquet
--range-source models  # compute forecasts from gold_range_4h / gold_range_1d
```

Supported flat columns include both raw and source-prefixed names:

```text
range_4h_high_price / src5m_range_4h_high_price
range_4h_low_price  / src5m_range_4h_low_price
range_1d_high_price / src5m_range_1d_high_price
range_1d_low_price  / src5m_range_1d_low_price
```

Bracket logic:

```text
BUY : TP from range high, SL from range low
SELL: TP from range low,  SL from range high
```

with:

```text
--range-bracket-mode range|range_capped|atr
--use-1d-tp-cap 1
--max-tp-atr 2.0
--max-sl-atr 1.25
--min-tp-distance 0.5
--min-sl-distance 0.5
```

Full archive outputs:

```text
run_logs\pivot_pattern_sequence_wavenet_range_archive\latest.json
run_logs\pivot_pattern_sequence_wavenet_range_archive\latest.html
run_logs\pivot_pattern_sequence_wavenet_range_archive\latest_predictions.parquet
run_logs\pivot_pattern_sequence_wavenet_range_archive\latest_predictions.csv
run_logs\pivot_pattern_sequence_wavenet_range_archive\latest_trades.parquet
run_logs\pivot_pattern_sequence_wavenet_range_archive\latest_trades.csv
run_logs\pivot_pattern_sequence_wavenet_range_archive\latest_monthly.csv
run_logs\pivot_pattern_sequence_wavenet_range_archive\latest_side.csv
```

Recommended command:

```powershell
python -u scripts\backtest_pivot_pattern_sequence_wavenet_range.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --tensor-path datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_latest.npy `
  --meta-path datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_latest_meta.npz `
  --flat-path datasets\processed\XAUUSD\5M\pivot_pattern_sequence_flat_latest.parquet `
  --model-id gold_pivot_pattern_sequence_wavenet_option_b_5m `
  --model-version 0 `
  --max-samples 0 `
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
  --range-source auto `
  --range-bracket-mode range_capped `
  --range-fallback skip `
  --range-1d-model-id gold_range_1d `
  --range-4h-model-id gold_range_4h `
  --range-1d-version 0 `
  --range-4h-version 0 `
  --use-1d-tp-cap 1 `
  --min-range-4h-room 0 `
  --min-range-1d-room 0 `
  --min-tp-distance 0.5 `
  --min-sl-distance 0.5 `
  --max-tp-atr 2.0 `
  --max-sl-atr 1.25 `
  --atr-tp-multiplier 0.75 `
  --atr-sl-multiplier 0.75 `
  --hold-bars 48 `
  --spread-mode pct `
  --spread-value 0.06 `
  --same-bar-policy stop_first `
  --initial-capital 100 `
  --risk-per-trade 0.01 `
  --storage-root datasets `
  --output-dir run_logs\pivot_pattern_sequence_wavenet_range_archive `
  --report-title "Phase148A range-aware sequence WaveNet archive"
```

Verification:

```text
python -m py_compile scripts/backtest_pivot_pattern_sequence_wavenet_range.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py
→ passed

python -m pytest tests/unit/ai/test_pivot_sequence_tensor.py tests/unit/ai/test_pivot_sequence_tensor_health.py tests/unit/ai/test_pivot_sequence_wavenet_helpers.py tests/unit/ai/test_pivot_sequence_wavenet_backtest.py tests/unit/ai/test_pivot_sequence_wavenet_option_b.py tests/unit/ai/test_pivot_sequence_range_archive.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ 60 passed
```

Production remains blocked.

## Phase147C Option B branch feature expansion to 180 — 2026-09-19

The owner asked whether the small grouped raw input sizes could contribute to overfitting and requested each Option B branch input to support 180 useful features:

```text
m5_context_input  : [batch, 100, 180]
source_5m_input   : [batch, 100, 180]
htf_context_input : [batch, 100, 180]
```

Decision:

```text
We should not pad branches with arbitrary dummy columns or duplicate raw features.
More raw columns do not automatically reduce overfitting; irrelevant columns can make it worse.
```

Implemented a controlled optional causal feature expansion for Option B:

```text
scripts/train_pivot_pattern_sequence_wavenet_option_b.py
```

New flags:

```text
--branch-target-features 180
--feature-augmentation-mode causal
--feature-augmentation-clip 8
```

When enabled, each branch is expanded with deterministic causal transforms of its own normalized feature stream:

```text
original values
lag-1 delta
lag-3 delta
lag-6 delta
causal rolling mean 3
causal rolling mean 6
causal rolling mean 12
abs lag-1 delta
abs lag-3 delta
```

Then the channel axis is clipped/truncated to the requested target count. For the current tensor:

```text
m5_context raw 35  → expanded 180
source_5m raw 83   → expanded 180
htf_context raw 22 → expanded 180
```

The expansion is causal within each 100-candle window and uses only data already inside the input window. It does not add future information beyond the endpoint.

Backtest/prediction support updated:

```text
scripts/backtest_pivot_pattern_sequence_wavenet.py
scripts/backtest_pivot_pattern_sequence_wavenet_range.py
```

The model record stores augmentation settings, and prediction loaders reproduce the same grouped 180-channel inputs.

GUI update:

```text
Train pivot sequence WaveNet Option B
  Expanded features per branch
  Feature augmentation
  Augmentation clip
```

Recommended command after the current full run finishes, only if owner wants the 180-channel experiment:

```powershell
python -u scripts\train_pivot_pattern_sequence_wavenet_option_b.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --tensor-path datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_latest.npy `
  --meta-path datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_latest_meta.npz `
  --model-id gold_pivot_pattern_sequence_wavenet_option_b_180_5m `
  --train-frac 0.70 `
  --val-frac 0.15 `
  --purge-gap 336 `
  --max-samples 24000 `
  --stream-chunk-size 512 `
  --batch-size 16 `
  --epochs 80 `
  --learning-rate 0.0005 `
  --branch-filters 48 `
  --branch-target-features 180 `
  --feature-augmentation-mode causal `
  --feature-augmentation-clip 8 `
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
  --output-dir run_logs\pivot_pattern_sequence_wavenet_option_b_180 `
  --report-title "Option B Pivot Sequence WaveNet 180-channel training"
```

Verification:

```text
python -m py_compile scripts/train_pivot_pattern_sequence_wavenet_option_b.py scripts/backtest_pivot_pattern_sequence_wavenet.py scripts/backtest_pivot_pattern_sequence_wavenet_range.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py
→ passed

python -m pytest tests/unit/ai/test_pivot_sequence_wavenet_option_b.py tests/unit/ai/test_pivot_sequence_wavenet_backtest.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py -q
→ 17 passed
```

Caution:

```text
This is an experiment. The existing overfit symptoms are not necessarily caused by too few input features. More channels may help representation, but may also overfit harder. Compare by validation/test PnL, not training accuracy.
```

## Phase147C Option B 180-channel input health audit completed — 2026-09-19

Completed the owner-requested pre-training dataset/input health step for the Option B 180-channel experiment.

Implemented:

```text
scripts/audit_pivot_pattern_sequence_option_b_inputs.py
GUI: Audit pivot sequence Option B input health
```

Purpose:

```text
Before training, verify the exact training-time Option B expanded inputs:
  m5_context_input  = [batch, 100, 180]
  source_5m_input   = [batch, 100, 180]
  htf_context_input = [batch, 100, 180]
```

The audit does not duplicate the dataset on disk. It:

```text
1. Loads the healthy source tensor [53098,100,140] as memmap.
2. Rebuilds Option B groups from feature metadata.
3. Selects the same sample universe as training.
4. Reconstructs chronological train/validation/test split.
5. Fits the same train-only scaler as training.
6. Builds expanded 180-channel batches exactly like the trainer.
7. Scans each branch for NaN/Inf and clip violations.
8. Confirms the intended Keras input shapes.
```

Recommended health command before 180-channel training:

```powershell
python -u scripts\audit_pivot_pattern_sequence_option_b_inputs.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --tensor-path datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_latest.npy `
  --meta-path datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_latest_meta.npz `
  --train-frac 0.70 `
  --val-frac 0.15 `
  --purge-gap 336 `
  --max-samples 0 `
  --stream-chunk-size 512 `
  --scan-chunk-size 256 `
  --full-scan 1 `
  --max-scan-samples 0 `
  --branch-target-features 180 `
  --feature-augmentation-mode causal `
  --feature-augmentation-clip 8 `
  --storage-root datasets `
  --output-dir run_logs\pivot_pattern_sequence_option_b_input_health
```

Expected outputs:

```text
run_logs\pivot_pattern_sequence_option_b_input_health\latest.json
run_logs\pivot_pattern_sequence_option_b_input_health\latest.html
```

Only after `status=PASS` should the owner run the 180-channel training command.

Verification:

```text
python -m py_compile scripts/audit_pivot_pattern_sequence_option_b_inputs.py scripts/train_pivot_pattern_sequence_wavenet_option_b.py scripts/backtest_pivot_pattern_sequence_wavenet.py scripts/backtest_pivot_pattern_sequence_wavenet_range.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py
→ passed

python -m pytest tests/unit/ai/test_pivot_sequence_tensor.py tests/unit/ai/test_pivot_sequence_tensor_health.py tests/unit/ai/test_pivot_sequence_wavenet_helpers.py tests/unit/ai/test_pivot_sequence_wavenet_backtest.py tests/unit/ai/test_pivot_sequence_wavenet_option_b.py tests/unit/ai/test_pivot_sequence_option_b_input_health.py tests/unit/ai/test_pivot_sequence_range_archive.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ 64 passed
```

## Phase147C Option B 180-channel input health PASS — 2026-09-19

The owner supplied `run_logs\pivot_pattern_sequence_option_b_input_health\latest.json` after running the official Phase147C 180-channel Option B input audit.

Audit input:

```text
stored_x_shape      : [53098, 100, 140]
selected_x_shape    : [53098, 100, 140]
branch_target       : 180
augmentation_mode   : causal
augmentation_clip   : 8.0
```

Chronological split rebuilt by the audit:

```text
train_rows      : 37168
validation_rows : 7629
test_rows       : 7629
purge_gap       : 336
```

Raw branch counts:

```text
m5_context raw  : 35
source_5m raw   : 83
htf_context raw : 22
```

Expanded Keras inputs:

```text
m5_context_input  : [batch, 100, 180]
source_5m_input   : [batch, 100, 180]
htf_context_input : [batch, 100, 180]
```

Full expanded-input scan:

```text
m5_context_input:
  scanned_cells   : 955,764,000
  nonfinite_cells : 0
  min/max/max_abs : -8.0 / 8.0 / 8.0
  chunks          : 208

source_5m_input:
  scanned_cells   : 955,764,000
  nonfinite_cells : 0
  min/max/max_abs : -8.0 / 8.0 / 8.0
  chunks          : 208

htf_context_input:
  scanned_cells   : 955,764,000
  nonfinite_cells : 0
  min/max/max_abs : -6.2252612114 / 8.0 / 8.0
  chunks          : 208
```

Total scanned expanded cells:

```text
2,867,292,000
```

Targets over selected samples:

```text
SELL : 5,384
HOLD : 43,252
BUY  : 4,462
```

Result:

```text
status   : PASS
warnings : []
errors   : []
```

Decision:

```text
The actual 180-channel Option B training-time inputs are accepted as healthy.
The owner can proceed with full-dataset 180-channel Option B training.
This remains research-only; no production/paper/live permission.
```

## Phase147C Option B 180-channel full-dataset training result — 2026-09-19

The owner supplied `run_logs\pivot_pattern_sequence_wavenet_option_b_180_full\latest.json` for the full-dataset 180-channel Option B training run.

Training configuration:

```text
model_id          : gold_pivot_pattern_sequence_wavenet_option_b_180_5m
version           : 1
tensor            : datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_latest.npy
meta              : datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_latest_meta.npz
stored_x_shape    : [53098, 100, 140]
keras inputs:
  m5_context_input  : [batch, 100, 180]
  source_5m_input   : [batch, 100, 180]
  htf_context_input : [batch, 100, 180]
samples           : 53098
train_rows        : 37168
validation_rows   : 7629
test_rows         : 7629
branch_target_features      : 180
feature_augmentation_mode   : causal
feature_augmentation_clip   : 8.0
nonfinite_input_values      : 0
```

Metrics:

```text
val_action_accuracy : 0.5585266745
val_top_ap          : 0.2717308013
val_bottom_ap       : 0.2202253973
val_buy_r_mae       : 0.6357029080
val_sell_r_mae      : 0.6304646134
val_selected_rate   : 0.4700484991

test_action_accuracy : 0.5168436230
test_top_ap          : 0.2486227103
test_bottom_ap       : 0.2121224816
test_buy_r_mae       : 0.7210720181
test_sell_r_mae      : 0.7024750710
test_selected_rate   : 0.4856468738
```

Comparison to the 24k raw-branch Option B run:

```text
Option B raw branches [24000,100,140]
  test_action_accuracy : 0.6544
  test_top_ap          : 0.2637
  test_bottom_ap       : 0.2550
  test_selected_rate   : 0.3134
  PnL/PF               : +1.8765%, PF=1.0377

Option B 180-channel full universe [53098,100,140 → grouped 180]
  test_action_accuracy : 0.5168
  test_top_ap          : 0.2486
  test_bottom_ap       : 0.2121
  test_selected_rate   : 0.4856
  PnL/PF               : not run yet
```

Interpretation:

```text
- The 180-channel input health was PASS, so this is not a NaN/Inf problem.
- The 180-channel causal augmentation did not improve diagnostic metrics in this full-universe run.
- test_selected_rate rose to ~48.6%, suggesting the model became more aggressive.
- Action accuracy and bottom AP are materially worse than the 24k raw-branch Option B run.
- This supports the earlier caution: more channels/features do not automatically reduce overfit; they can add noisy degrees of freedom.
```

Decision:

```text
Do not promote the 180-channel full-dataset model based on current classifier/AP diagnostics.
Keep the raw-branch Option B 24k model as the current preliminary PnL/PF winner until a better full-dataset run proves otherwise.
If testing this 180 model further, run range-aware archive/backtest only as a diagnostic, not as a preferred candidate.
Next recommended route: train raw-branch Option B full dataset or proceed with Step 4 archive on the current best Option B model, then Step 5 anti-overfit filtering.
No Phase134. No paper shadow. No live trading.
```

## Phase149A sequence feature impact audit implemented — 2026-09-19

Implemented validation-only feature/group ablation diagnostics to answer which raw sequence features are useful, neutral, or drop candidates.

Implemented:

```text
scripts/audit_pivot_sequence_feature_impact.py
GUI: Audit pivot sequence feature impact
```

Method:

```text
- Load trained Option A or Option B sequence WaveNet.
- Evaluate a chronological split, default validation.
- Compute baseline metrics.
- Zero-ablate groups/features at inference time.
- Compute metric deltas and composite score deltas.
- Mark features as KEEP_IMPORTANT / NEUTRAL / DROP_CANDIDATE.
```

Composite score:

```text
composite = action_accuracy + 0.5*top_ap + 0.5*bottom_ap - 0.25*buy_r_mae - 0.25*sell_r_mae
```

Outputs:

```text
run_logs\pivot_sequence_feature_impact\latest.json
run_logs\pivot_sequence_feature_impact\latest.html
run_logs\pivot_sequence_feature_impact\latest_features.csv
run_logs\pivot_sequence_feature_impact\latest_groups.csv
```

Recommended command:

```powershell
python -u scripts\audit_pivot_sequence_feature_impact.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --tensor-path datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_latest.npy `
  --meta-path datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_latest_meta.npz `
  --model-id gold_pivot_pattern_sequence_wavenet_option_b_5m `
  --model-version 0 `
  --max-samples 24000 `
  --eval-split validation `
  --train-frac 0.70 `
  --val-frac 0.15 `
  --purge-gap 336 `
  --max-windows 1500 `
  --batch-size 128 `
  --buy-threshold 0.34 `
  --sell-threshold 0.34 `
  --min-margin 0 `
  --min-buy-r -999 `
  --min-sell-r -999 `
  --check-groups 1 `
  --check-features 1 `
  --feature-group-filter all `
  --max-features-to-check 0 `
  --harmful-threshold 0.005 `
  --useful-threshold 0.005 `
  --storage-root datasets `
  --output-dir run_logs\pivot_sequence_feature_impact `
  --report-title "Phase149A sequence feature impact audit"
```

Verification:

```text
python -m py_compile scripts/audit_pivot_sequence_feature_impact.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py
→ passed

python -m pytest tests/unit/ai/test_pivot_sequence_feature_impact.py tests/unit/ai/test_pivot_sequence_tensor.py tests/unit/ai/test_pivot_sequence_tensor_health.py tests/unit/ai/test_pivot_sequence_wavenet_helpers.py tests/unit/ai/test_pivot_sequence_wavenet_backtest.py tests/unit/ai/test_pivot_sequence_wavenet_option_b.py tests/unit/ai/test_pivot_sequence_option_b_input_health.py tests/unit/ai/test_pivot_sequence_range_archive.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ 68 passed
```

Anti-overfit rule:

```text
Use validation for discovery. Do not drop based on final test only.
Retrain/confirm on test and later walk-forward before adopting filters.
```

## Phase149B pruned-feature training support — 2026-09-19

After the Phase149A validation feature-impact result, training and prediction loaders were extended to support controlled feature-zeroing experiments.

Implemented in:

```text
scripts/train_pivot_pattern_sequence_wavenet_option_b.py
scripts/backtest_pivot_pattern_sequence_wavenet.py
scripts/backtest_pivot_pattern_sequence_wavenet_range.py
```

New trainer flags:

```text
--zero-feature-names "name1,name2,..."
--zero-feature-file configs/phase149a_option_b_180_validation_drop_candidates.txt
--zero-feature-groups "closed_4h"
```

Tracked drop-list file:

```text
configs/phase149a_option_b_180_validation_drop_candidates.txt
```

It contains the 26 validation-discovered DROP_CANDIDATE features from Phase149A.

Behavior:

```text
The original tensor is not rewritten.
Selected features are zeroed after train-only normalization and before Option B grouping/causal augmentation.
Model records store the feature_selection payload.
Backtest/range archive loaders apply the same zero mask at prediction time.
```

Recommended controlled experiment command:

```powershell
python -u scripts\train_pivot_pattern_sequence_wavenet_option_b.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --tensor-path datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_latest.npy `
  --meta-path datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_latest_meta.npz `
  --model-id gold_pivot_pattern_sequence_wavenet_option_b_180_pruned_5m `
  --train-frac 0.70 `
  --val-frac 0.15 `
  --purge-gap 336 `
  --max-samples 24000 `
  --stream-chunk-size 512 `
  --batch-size 16 `
  --epochs 80 `
  --learning-rate 0.0005 `
  --branch-filters 48 `
  --branch-target-features 180 `
  --feature-augmentation-mode causal `
  --feature-augmentation-clip 8 `
  --zero-feature-file configs\phase149a_option_b_180_validation_drop_candidates.txt `
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
  --batch-log-every 25 `
  --save-model 1 `
  --storage-root datasets `
  --output-dir run_logs\pivot_pattern_sequence_wavenet_option_b_180_pruned `
  --report-title "Option B 180 pruned validation-drop-candidate training"
```

Verification:

```text
python -m py_compile scripts/train_pivot_pattern_sequence_wavenet_option_b.py scripts/backtest_pivot_pattern_sequence_wavenet.py scripts/audit_pivot_sequence_feature_impact.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py
→ passed

python -m pytest tests/unit/ai/test_pivot_sequence_feature_impact.py tests/unit/ai/test_pivot_sequence_tensor.py tests/unit/ai/test_pivot_sequence_tensor_health.py tests/unit/ai/test_pivot_sequence_wavenet_helpers.py tests/unit/ai/test_pivot_sequence_wavenet_backtest.py tests/unit/ai/test_pivot_sequence_wavenet_option_b.py tests/unit/ai/test_pivot_sequence_option_b_input_health.py tests/unit/ai/test_pivot_sequence_range_archive.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ 69 passed
```

Anti-overfit reminder:

```text
This model is a controlled experiment using validation-discovered drop candidates.
If it improves validation, confirm with test PnL and then walk-forward before adopting.
```

## Phase149B pruned 180-channel training result — 2026-09-19

The owner supplied `run_logs\pivot_pattern_sequence_wavenet_option_b_180_pruned\latest.json` and late batch/epoch logs for the controlled pruned 180-channel Option B experiment.

Training configuration:

```text
model_id              : gold_pivot_pattern_sequence_wavenet_option_b_180_pruned_5m
version               : 1
stored_x_shape        : [24000, 100, 140]
keras inputs          : [batch,100,180] × 3 branches
max_samples           : 24000
branch_target_features: 180
augmentation          : causal, clip=8
zero_feature_file     : configs\phase149a_option_b_180_validation_drop_candidates.txt
zeroed_feature_count  : 26
epochs                : 200
early_stopping_patience: 200
nonfinite_input_values: 0
```

Zeroed validation-discovered DROP_CANDIDATE features included:

```text
m5_fast_mid_dist_atr
m5_mid_slow_dist_atr
m5_pos_in_range_24
m5_pos_in_range_48
m5_dist_low_48_atr
m5_pos_in_range_96
m5_ret24
m5_ret48
h4_ret3
h4_close_mid_dist_atr
h4_rsi14
h4_room_down_atr
d1_ret3
src5m_5m_body_pct
src5m_specialist_max_prob
src5m_range_1d_up_room_pct
src5m_range_1d_down_room_pct
src5m_lagged_trade_count
src5m_last_closed_trade_pnl_lag
src5m_rolling_12_trades_avg_pnl_lag
src5m_rolling_12_trades_profit_factor_lag
src5m_rolling_12_trades_timeout_rate_lag
src5m_rolling_24_trades_avg_pnl_lag
src5m_rolling_48_trades_avg_pnl_lag
src5m_rolling_48_trades_profit_factor_lag
src5m_rolling_48_trades_timeout_rate_lag
```

Final report metrics:

```text
val_action_accuracy : 0.6875000000
val_top_ap          : 0.3458503914
val_bottom_ap       : 0.2774233380
val_buy_r_mae       : 0.6454545856
val_sell_r_mae      : 0.6455140710
val_selected_rate   : 0.3026960784

test_action_accuracy : 0.6611519608
test_top_ap          : 0.2793102151
test_bottom_ap       : 0.2795754914
test_buy_r_mae       : 0.7160413861
test_sell_r_mae      : 0.7160999179
test_selected_rate   : 0.3060661765
```

Late training log showed strong train/validation divergence:

```text
epoch 198 train_acc≈0.9917, val_loss≈3.0868
epoch 199 train_acc≈0.9933, val_loss≈2.7145
epoch 200 train_acc≈0.9945, val_loss≈2.9824
```

Interpretation:

```text
- The model heavily overfit by late epochs.
- The final report metrics are still useful only if restored/best validation weights were used; in any case, the late logs confirm that patience=200 is too large for future runs.
- Despite overfit risk, the pruned 180-channel model improved test diagnostics versus raw Option B on this 24k benchmark.
```

Comparison to raw Option B 24k:

```text
Raw Option B:
  test_action_accuracy : 0.6544
  test_top_ap          : 0.2637
  test_bottom_ap       : 0.2550
  test_buy/sell_r_mae  : ~0.820 / ~0.820
  test_selected_rate   : 0.3134
  PnL/PF               : +1.8765%, PF=1.0377

Pruned 180 Option B:
  test_action_accuracy : 0.6612
  test_top_ap          : 0.2793
  test_bottom_ap       : 0.2796
  test_buy/sell_r_mae  : ~0.716 / ~0.716
  test_selected_rate   : 0.3061
  PnL/PF               : pending
```

Decision:

```text
The pruned 180-channel model is now the strongest classifier/ranking diagnostic among the 24k sequence models.
It must not be promoted until PnL audit and range-aware archive confirm it.
Next action: run fair Phase146A ATR PnL audit for gold_pivot_pattern_sequence_wavenet_option_b_180_pruned_5m, then Phase148A range-aware archive if promising.
No Phase134. No paper shadow. No live trading.
```

## Phase149B pruned 180 PnL audit failure — 2026-09-20

The owner supplied `run_logs\pivot_pattern_sequence_wavenet_option_b_180_pruned_backtest\latest.json` for the ATR-based PnL audit of the pruned 180-channel Option B model.

Backtest configuration:

```text
model_id          : gold_pivot_pattern_sequence_wavenet_option_b_180_pruned_5m
model_version     : 1
eval_split        : test
selected_samples  : 24000
evaluated_samples : 3264
evaluated period  : 2026-07-03 19:35:00+00:00 → 2026-08-06 19:20:00+00:00
buy/sell threshold: 0.34 / 0.34
min_margin        : 0
tp/sl multiplier  : 0.75 / 0.75
hold_bars         : 48
spread            : pct 0.06
same_bar_policy   : stop_first
initial_capital   : 100
risk_per_trade    : 0.01
```

Result:

```text
trades             : 120
BUY / SELL trades  : 41 / 79
wins / losses      : 57 / 63
win_rate           : 47.50%
final_balance      : 91.6591309299
return_percent     : -8.3408690701%
total_cash_pnl     : -8.3408690701
gross_profit       : 36.3334344612
gross_loss         : 44.6743035313
profit_factor      : 0.8132960469
max_drawdown_cash  : 10.2459750447
take_profit        : 26
stop_loss          : 38
timeout            : 56
```

Side breakdown:

```text
BUY cash PnL  : +0.1146579499
SELL cash PnL : -8.4555270200
```

Monthly result:

```text
2026-07 : -5.3828214745 / 99 trades
2026-08 : -2.9580475956 / 21 trades
positive_months : 0
negative_months : 2
```

Comparison to raw Option B 24k benchmark:

```text
Raw Option B:
  final_balance : 101.8764768367
  return        : +1.8765%
  PF            : 1.0377
  maxDD         : 7.7910
  BUY PnL       : +1.9372
  SELL PnL      : -0.0608
  months        : July +4.1184, August -2.2419

Pruned 180 Option B:
  final_balance : 91.6591309299
  return        : -8.3409%
  PF            : 0.8133
  maxDD         : 10.2460
  BUY PnL       : +0.1147
  SELL PnL      : -8.4555
  months        : July -5.3828, August -2.9580
```

Interpretation:

```text
- The pruned 180-channel model improved classifier/ranking diagnostics but failed trading replay badly.
- The validation-discovered DROP_CANDIDATE pruning did not transfer to PnL.
- SELL side became the dominant damage source again.
- Both evaluated months are negative.
- This confirms the anti-overfit warning: feature ablation improvements on validation classification metrics are not sufficient for trade profitability.
```

Decision:

```text
Reject gold_pivot_pattern_sequence_wavenet_option_b_180_pruned_5m as a trading candidate.
Do not continue range-aware archive or full training for this pruned 180 model.
Current best research candidate reverts to raw Option B 24k: gold_pivot_pattern_sequence_wavenet_option_b_5m.
Next steps should focus on raw Option B range-aware archive and/or validation-based TP/SL/side-specific filtering.
No Phase134. No paper shadow. No live trading.
```

## Phase147D raw Option B full-dataset training/backtest result — 2026-09-20

The owner retrained the raw Option B grouped sequence WaveNet on the full available tensor after the previous `gold_pivot_pattern_sequence_wavenet_option_b_5m` model artifact had been deleted.

Training configuration:

```text
model_id          : gold_pivot_pattern_sequence_wavenet_option_b_full_5m
version           : 1
tensor            : datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_latest.npy
meta              : datasets\processed\XAUUSD\5M\pivot_pattern_sequence_tensor_latest_meta.npz
stored_x_shape    : [53098, 100, 140]
samples           : 53098
train_rows        : 37168
validation_rows   : 7629
test_rows         : 7629
keras inputs:
  m5_context_input  : [batch, 100, 35]
  source_5m_input   : [batch, 100, 83]
  htf_context_input : [batch, 100, 22]
branch_target_features    : 0
feature_augmentation_mode : off
zeroed_feature_count      : 0
nonfinite_input_values    : 0
```

Classifier/ranking metrics:

```text
val_action_accuracy  : 0.6051907196
val_top_ap           : 0.3279156938
val_bottom_ap        : 0.2115178335
val_buy_r_mae        : 0.6564043164
val_sell_r_mae       : 0.6502464414
val_selected_rate    : 0.4475029493

test_action_accuracy : 0.5586577533
test_top_ap          : 0.2518729500
test_bottom_ap       : 0.2330887866
test_buy_r_mae       : 0.7078536153
test_sell_r_mae      : 0.7026057839
test_selected_rate   : 0.4570717001
```

ATR PnL check on the same full-universe split:

```text
model_id          : gold_pivot_pattern_sequence_wavenet_option_b_full_5m
eval_split        : test
selected_samples  : 53098
evaluated_samples : 7629
evaluated period  : 2026-07-24 14:05:00+00:00 → 2026-09-02 10:25:00+00:00
trades            : 174
BUY / SELL trades : 93 / 81
wins / losses     : 86 / 88
win_rate          : 49.4253%
final_balance     : 96.1853978886
return_percent    : -3.8146021114%
total_cash_pnl    : -3.8146021114
gross_profit      : 59.9770903102
gross_loss        : 63.7916924216
profit_factor     : 0.9402022118
max_drawdown_cash : 15.1989241036
take_profit       : 44
stop_loss         : 51
timeout           : 79
```

Side and monthly breakdown:

```text
BUY cash PnL  : +1.0795518044
SELL cash PnL : -4.8941539158

2026-07 : +4.9827258346 / 36 trades
2026-08 : -9.2146695014 / 127 trades
2026-09 : +0.4173415553 / 11 trades
positive_months : 2
negative_months : 1
```

Dataset/feature verdict:

```text
The dataset and features used for this run are structurally OK:
- stored tensor shape is the intended [53098,100,140]
- Option B group counts match metadata: 35 / 83 / 22
- source_5m telemetry features are present: 83 source features
- nonfinite_input_values=0
- previous official tensor health audit passed with nonfinite_cells=0 and max_abs=8.0
- chronological split with purge_gap=336 was used
```

Trading verdict:

```text
The full-dataset raw Option B model is NOT promoted as a trading candidate.
It is a clean/healthy-data training run, but the PnL check is negative: final_balance=96.1854, PF=0.9402, maxDD=15.1989.
SELL side and August are the main damage sources in this full run.
```

Comparison to previous raw Option B 24k benchmark:

```text
Raw Option B 24k historical benchmark:
  final_balance : 101.8764768367
  return        : +1.8765%
  PF            : 1.0377
  maxDD         : 7.7910
  period        : 2026-07-03 → 2026-08-06

Raw Option B full-dataset rebuild:
  final_balance : 96.1853978886
  return        : -3.8146%
  PF            : 0.9402
  maxDD         : 15.1989
  period        : 2026-07-24 → 2026-09-02
```

Decision:

```text
Accept the dataset/features as healthy.
Reject this full-dataset raw Option B run as a trading candidate until a validation/range-aware/walk-forward process proves otherwise.
Do not interpret the negative result as data corruption; interpret it as weak model generalization/regime sensitivity.
Current best historical research result remains the deleted/raw 24k Option B benchmark, but it must be rebuilt if more archive/backtest work is required.
No Phase134. No paper shadow. No live trading.
```

## Phase149B/147D PowerShell empty zero-feature flag fix — 2026-09-20

The owner reran raw Option B 24k rebuild with explicit empty zero-feature flags:

```text
--zero-feature-names ""
--zero-feature-file ""
--zero-feature-groups ""
```

PowerShell/native argv handling dropped the empty strings, so argparse saw `--zero-feature-names` without a value and failed:

```text
train_pivot_pattern_sequence_wavenet_option_b.py: error: argument --zero-feature-names: expected one argument
```

Fix implemented in:

```text
scripts/train_pivot_pattern_sequence_wavenet_option_b.py
```

The three optional zero-feature flags now use:

```text
nargs="?"
const=""
default=""
```

Safe forms now include both:

```powershell
# recommended for no pruning: omit these flags entirely

# also accepted now if a shell drops the empty value
--zero-feature-names
--zero-feature-file
--zero-feature-groups
```

Immediate operator workaround on older checkouts:

```text
Remove the three empty zero-feature lines from the raw Option B rebuild command.
```

Verification:

```text
python -m py_compile scripts/train_pivot_pattern_sequence_wavenet_option_b.py
python -m pytest tests/unit/ai/test_pivot_sequence_wavenet_option_b.py -q
→ 4 passed
```

## Phase147E raw Option B 24k rebuild result — previous weak-positive result did not reproduce — 2026-09-20

The owner rebuilt the raw Option B 24k model after the earlier historical current-best artifact had been deleted.

Training configuration:

```text
model_id              : gold_pivot_pattern_sequence_wavenet_option_b_5m
version               : 1
max_samples           : 24000
stored_x_shape        : [24000, 100, 140]
keras inputs          : [batch,100,35] / [batch,100,83] / [batch,100,22]
branch_target_features: 0
augmentation          : off
zeroed_feature_count  : 0
nonfinite_input_values: 0
```

Training diagnostics:

```text
val_action_accuracy  : 0.6875000000
val_top_ap           : 0.4298344451
val_bottom_ap        : 0.3018743404
val_buy_r_mae        : 0.6229432821
val_sell_r_mae       : 0.6397787333
val_selected_rate    : 0.3452818627

test_action_accuracy : 0.6151960784
test_top_ap          : 0.2843775626
test_bottom_ap       : 0.3673007788
test_buy_r_mae       : 0.6919192076
test_sell_r_mae      : 0.6780540347
test_selected_rate   : 0.4056372549
```

ATR PnL check:

```text
eval_split        : test
selected_samples  : 24000
evaluated_samples : 3264
evaluated period  : 2026-07-03 19:35:00+00:00 → 2026-08-06 19:20:00+00:00
trades            : 135
BUY / SELL trades : 46 / 89
wins / losses     : 60 / 75
win_rate          : 44.4444%
final_balance     : 90.7052413035
return_percent    : -9.2947586965%
total_cash_pnl    : -9.2947586965
profit_factor     : 0.8270058072
max_drawdown_cash : 10.7624722054
take_profit       : 34
stop_loss         : 46
timeout           : 55
BUY PnL           : -5.3900375011
SELL PnL          : -3.9047211954
monthly           : 2026-07 -3.6628516601, 2026-08 -5.6319070363
positive_months   : 0
negative_months   : 2
```

Comparison with the deleted historical raw Option B 24k benchmark:

```text
Historical raw B 24k:
  test_action_accuracy : 0.6544
  test_selected_rate   : 0.3134
  final_balance        : 101.8765
  return               : +1.8765%
  PF                   : 1.0377
  maxDD                : 7.7910
  BUY PnL              : +1.9372
  SELL PnL             : -0.0608

Rebuilt raw B 24k:
  test_action_accuracy : 0.6152
  test_selected_rate   : 0.4056
  final_balance        : 90.7052
  return               : -9.2948%
  PF                   : 0.8270
  maxDD                : 10.7625
  BUY PnL              : -5.3900
  SELL PnL             : -3.9047
```

Interpretation:

```text
The dataset/features are still healthy. This is not a tensor-shape or NaN/Inf issue.
The old weak-positive Option B artifact was not reproducible after deletion and retraining.
The new run selected a different local solution: lower action accuracy, higher selected_rate, and materially worse trade timing.
Both BUY and SELL are negative, and both evaluated months are negative.
```

Important root cause / correction:

```text
The Option B trainer did not previously expose a run seed. The batch Sequence shuffle used a fixed RNG, but TensorFlow/Keras initialization, dropout, and some backend operations were not under an explicit recorded seed.
Deleting the old model artifact made exact recovery impossible.
```

Fix implemented:

```text
scripts/train_pivot_pattern_sequence_wavenet_option_b.py
--random-seed 20260919
```

The trainer now calls Python/NumPy/TensorFlow seed setters before model creation and records the seed in the training record/report. The GUI command `Train pivot sequence WaveNet Option B` now has a `Random seed` field and forwards `--random-seed`.

Caution:

```text
A seed improves controlled reruns but does not guarantee byte-identical output across every GPU/TF backend. It also cannot recover the deleted old artifact.
```

Decision:

```text
Reject this rebuilt raw Option B 24k model as a trading candidate.
Do not run Phase148A range-aware archive on this rebuilt v1 as if it were the old winner.
The previous weak-positive raw Option B result is now treated as fragile/non-reproducible until a seeded validation/test process can reproduce it.
Next valid research step is not blind retraining; it is a controlled repeatability/seed audit selected on validation and confirmed on test.
No Phase134. No paper shadow. No live trading.
```

Verification for reproducibility-seed support:

```text
python -m py_compile scripts/train_pivot_pattern_sequence_wavenet_option_b.py src/ShadBotTrader/presentation/commands/handlers.py
python -m pytest tests/unit/ai/test_pivot_sequence_wavenet_option_b.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ 43 passed
```

## Phase147F raw Option B 24k rebuild validation-vs-test transfer failure — 2026-09-20

The owner ran the validation ATR PnL check for the rebuilt raw Option B 24k model after its test PnL failed.

Validation replay configuration:

```text
model_id          : gold_pivot_pattern_sequence_wavenet_option_b_5m
model_version     : 1
eval_split        : validation
selected_samples  : 24000
evaluated_samples : 3264
evaluated period  : 2026-05-28 09:20:00+00:00 → 2026-07-01 09:05:00+00:00
buy/sell threshold: 0.34 / 0.34
min_margin        : 0
tp/sl multiplier  : 0.75 / 0.75
hold_bars         : 48
spread            : pct 0.06
same_bar_policy   : stop_first
initial_capital   : 100
risk_per_trade    : 0.01
```

Validation result:

```text
trades             : 110
BUY / SELL trades  : 70 / 40
wins / losses      : 62 / 48
win_rate           : 56.3636%
final_balance      : 108.7914207603
return_percent     : +8.7914207603%
total_cash_pnl     : +8.7914207603
gross_profit       : 43.2124907078
gross_loss         : 34.4210699475
profit_factor      : 1.2554081199
max_drawdown_cash  : 5.9715931205
take_profit        : 33
stop_loss          : 25
timeout            : 52
BUY PnL            : -1.8550476298
SELL PnL           : +10.6464683900
monthly            : 2026-05 +1.1865238507, 2026-06 +7.6048969096
positive_months    : 2
negative_months    : 0
```

Same rebuilt model on test:

```text
trades             : 135
final_balance      : 90.7052413035
return_percent     : -9.2947586965%
profit_factor      : 0.8270058072
max_drawdown_cash  : 10.7624722054
BUY PnL            : -5.3900375011
SELL PnL           : -3.9047211954
monthly            : 2026-07 -3.6628516601, 2026-08 -5.6319070363
positive_months    : 0
negative_months    : 2
```

Interpretation:

```text
This is a clear validation-to-test transfer failure.
The model has strong validation PnL, but that edge is almost entirely SELL-side and does not survive the later test regime.
Validation: BUY is negative, SELL is strongly positive.
Test: both BUY and SELL are negative.
```

Decision:

```text
Do not promote the rebuilt raw Option B 24k model.
Do not run Step 4/range-aware archive on this model as if it is the historical winner.
The correct next phase is a controlled anti-overfit validation-to-test audit: discover only on validation, confirm on test, and later walk-forward.
No Phase134. No paper shadow. No live trading.
```

Recommended next research phase:

```text
Phase150A — Option B validation-to-test transfer / seed-threshold audit
```

Required anti-overfit rules for Phase150A:

```text
- validation is for discovery only
- test is confirmation only
- no threshold/filter chosen from test
- if validation-selected candidate fails test, reject it
- if test passes, still require walk-forward before paper/live
```
