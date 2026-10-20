# Phase149A Report — Sequence Feature Impact Audit

Date: 2026-09-19

## Goal

Build a diagnostic that helps answer:

```text
Which features should be kept?
Which features may hurt validation performance and should become drop candidates?
```

## Implemented

```text
scripts/audit_pivot_sequence_feature_impact.py
```

GUI:

```text
Audit pivot sequence feature impact
```

## What the audit does

```text
- Loads a trained sequence WaveNet model.
- Supports Option A and Option B records.
- Rebuilds chronological validation/test/tail split.
- Predicts baseline metrics.
- Zero-ablates feature groups and individual features.
- Computes metric deltas.
- Writes ranked CSVs for feature pruning research.
```

## Outputs

```text
run_logs\pivot_sequence_feature_impact\latest.json
run_logs\pivot_sequence_feature_impact\latest.html
run_logs\pivot_sequence_feature_impact\latest_features.csv
run_logs\pivot_sequence_feature_impact\latest_groups.csv
```

## First command

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

## Verification

```text
python -m py_compile scripts/audit_pivot_sequence_feature_impact.py src/ShadBotTrader/presentation/commands/commands.py src/ShadBotTrader/presentation/commands/handlers.py
→ passed

python -m pytest tests/unit/ai/test_pivot_sequence_feature_impact.py tests/unit/ai/test_pivot_sequence_tensor.py tests/unit/ai/test_pivot_sequence_tensor_health.py tests/unit/ai/test_pivot_sequence_wavenet_helpers.py tests/unit/ai/test_pivot_sequence_wavenet_backtest.py tests/unit/ai/test_pivot_sequence_wavenet_option_b.py tests/unit/ai/test_pivot_sequence_option_b_input_health.py tests/unit/ai/test_pivot_sequence_range_archive.py tests/unit/presentation/test_phase145_pivot_sequence_wavenet_gui.py tests/integration/test_gui_coverage.py -q
→ 68 passed
```

## Production status

```text
BLOCKED — diagnostic only.
No Phase134.
No paper shadow.
No live trading.
```

## Phase149A feature impact result — 2026-09-19

The owner supplied `run_logs\pivot_sequence_feature_impact\latest.json` for the validation-only feature/group ablation audit.

Audit target/model:

```text
model_id        : gold_pivot_pattern_sequence_wavenet_option_b_180_5m
model_version   : 1
eval_split      : validation
max_samples     : 24000
max_windows     : 1500
evaluated period: 2026-05-28 09:20:00+00:00 → 2026-06-29 10:35:00+00:00
option_b_model  : true
branch_target_features : 180
augmentation    : causal, clip=8
```

Baseline validation metrics on the audit subset:

```text
action_accuracy : 0.6466666667
top_ap          : 0.6543383331
bottom_ap       : 0.4293868145
buy_r_mae       : 0.5251473784
sell_r_mae      : 0.5323911309
selected_rate   : 0.4813333333
composite       : 0.9241446131
```

Group ablation result:

```text
KEEP_IMPORTANT:
- generated_5m   Δcomposite=-0.39947
- source_5m      Δcomposite=-0.45480
- session        Δcomposite=-0.04034
- closed_1d      Δcomposite=-0.04649
- m5_context     Δcomposite=-0.42006
- htf_context    Δcomposite=-0.01588
- all_features   Δcomposite=-1.16648

DROP_CANDIDATE:
- closed_4h      Δcomposite=+0.02278
```

Feature-level summary:

```text
feature_count       : 140
checked_feature_count : 140
DROP_CANDIDATE      : 26
KEEP_IMPORTANT      : 31
NEUTRAL             : 83
```

Strongest DROP_CANDIDATE examples from validation-only ablation:

```text
src5m_rolling_12_trades_timeout_rate_lag
m5_pos_in_range_48
src5m_specialist_max_prob
src5m_rolling_12_trades_profit_factor_lag
src5m_rolling_48_trades_profit_factor_lag
src5m_rolling_48_trades_timeout_rate_lag
m5_pos_in_range_96
src5m_rolling_24_trades_avg_pnl_lag
m5_mid_slow_dist_atr
d1_ret3
src5m_lagged_trade_count
h4_ret3
h4_rsi14
src5m_last_closed_trade_pnl_lag
src5m_rolling_12_trades_avg_pnl_lag
m5_fast_mid_dist_atr
m5_dist_low_48_atr
src5m_range_1d_up_room_pct
src5m_range_1d_down_room_pct
m5_ret48
m5_pos_in_range_24
h4_room_down_atr
src5m_5m_body_pct
h4_close_mid_dist_atr
m5_ret24
src5m_rolling_48_trades_avg_pnl_lag
```

Strongest KEEP_IMPORTANT examples:

```text
src5m_rolling_24_trades_profit_factor_lag
src5m_specialist_buy_minus_sell
src5m_booster_buy_prob
src5m_specialist_sell_minus_buy
src5m_buy_specialist_prob
src5m_booster_sell_prob
session_dow_sin
session_hour_cos
src5m_sell_specialist_prob
d1_mid_slow_dist_atr
d1_room_down_atr
m5_ema_fast
m5_atr
m5_dist_high_48_atr
m5_ema_slow
m5_volatility_24
src5m_4h_last_closed_age_5m
m5_dist_low_24_atr
h4_range_pct
d1_fast_mid_dist_atr
d1_close_mid_dist_atr
src5m_session_hour_cos
m5_dist_high_96_atr
src5m_1d_return_1
src5m_booster_action_margin
session_dow_cos
m5_ret1
m5_upper_wick_pct
src5m_session_dow_cos
m5_ema_mid
src5m_1d_body_pct
```

Interpretation:

```text
- source_5m and generated_5m are strongly important as groups.
- session/time is useful despite only four raw columns.
- closed_1d is useful.
- closed_4h as a group is suspicious in this 180-channel model and should become a controlled ablation candidate.
- Individual DROP_CANDIDATE labels are not delete commands; they are validation-discovered hypotheses.
```

Anti-overfit rule:

```text
Do not delete features solely from this audit.
Use this result to define controlled pruning experiments, then retrain and confirm on test/walk-forward.
```

Recommended controlled pruning experiments:

```text
P0 baseline: current raw-branch Option B winner
P1 remove closed_4h group only
P2 remove top 10 validation DROP_CANDIDATE features
P3 remove all 26 validation DROP_CANDIDATE features
P4 remove closed_4h + top 10 DROP_CANDIDATE features
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
