# Phase147D Report — Raw Option B Full-Dataset Result

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
