# Phase128 — LightGBM/CatBoost Meta-Labeler Baseline

**Status:** ✅ Phase128A implemented
**Type:** Flat telemetry baseline / trade filter
**Priority:** immediately after Phase127 tensor is verified

---

## Goal

Train a fast, interpretable baseline on the Phase127 telemetry dataset before trying heavier neural models.

The first job of this model is not to predict direction. Direction already comes from:

```text
gold_hybrid_lightgbm_head_5m
```

The first job is:

```text
Should this hybrid candidate trade be executed or skipped?
```

---

## Inputs

Use the flat projection of Phase127:

```text
datasets/processed/XAUUSD/5M/hybrid_telemetry_flat_latest.parquet
```

Only online-safe feature columns are allowed:

```text
model outputs
range/bracket features
aligned 4H/1D context
lagged backtest telemetry
compact 5M features
```

Forbidden as input:

```text
target_trade_win
target_trade_score_r
target_trade_pnl
any unlagged future outcome
```

---

## Targets

Primary classifier target:

```text
target_trade_win
```

Secondary regression/ranker target:

```text
target_trade_score_r
```

Raw PnL target is for analysis only:

```text
target_trade_pnl
```

---

## Model IDs

Recommended IDs:

```text
gold_hybrid_meta_lightgbm_5m
gold_hybrid_score_lightgbm_5m
```

Optional alternatives:

```text
gold_hybrid_meta_catboost_5m
gold_hybrid_meta_xgboost_5m
```

---

## Training protocol

No random split.

Minimum first version:

```text
chronological train/validation/test
```

Better version:

```text
walk-forward monthly blocks
```

Example split:

```text
train: earliest 70%
validation: next 15%
test: latest 15%
```

The model must never see future rows when training.

---

## Backtest usage

Base rule:

```text
hybrid head produces BUY/SELL candidate
```

Meta filter:

```text
execute only if meta_win_prob >= meta_threshold
and/or expected_score_r >= score_threshold
```

Then run chronological single-position replay:

```text
Phase126A replay engine
```

---

## Metrics

Classification:

```text
precision
recall
F1
PR-AUC
calibration curve
```

Trading:

```text
trades
coverage
win_rate
label_precision
total_pnl
avg_pnl
profit_factor
max_drawdown
return on initial_capital with units
monthly breakdown
```

---

## Why LightGBM first?

```text
- fastest baseline
- low RAM
- handles noisy tabular features well
- easier feature importance/debugging
- already worked better than WaveNet on the first trend_signal path
```

This phase is the reference that all neural models must beat.

---

## Acceptance criteria

```text
- Uses only Phase127 online-safe features.
- Trains classifier on target_trade_win.
- Optionally trains regressor/ranker on target_trade_score_r.
- Writes model record and thresholds.
- Produces chronological replay comparison vs base hybrid head.
- Report clearly says whether it reduces full-history losses.
```

---

## Next phase

```text
Phase129 — WaveNet/TCN on the 3D telemetry tensor.
```

---

## GUI/operator execution requirement

این فاز فقط وقتی کامل است که مدل meta-labeler از Dashboard قابل اجرا باشد. هیچ آموزش/بک‌تست قابل‌اجرایی نباید فقط CLI بماند.

حداقل commandهای لازم:

```text
CommandKind.TRAIN_HYBRID_META_LABELER
Dashboard label: Train hybrid meta-labeler
Handler: runs scripts/train_hybrid_meta_labeler.py

CommandKind.BACKTEST_HYBRID_META_LABELER
Dashboard label: Backtest hybrid meta-labeler
Handler: runs scripts/backtest_hybrid_meta_labeler.py
```

فیلدهای مهم GUI:

```text
symbol
timeframe
tensor/flat_matrix_path
booster = lightgbm|catboost|xgboost
target = target_trade_win|target_trade_score_r
train_frac/validation_frac/test_frac
meta_threshold
score_threshold
storage_root
```

تست GUI الزامی است و باید پاس‌دادن args را بررسی کند.

---

## Phase128A implementation status

Implemented files:

```text
scripts/train_hybrid_meta_labeler.py
scripts/backtest_hybrid_meta_labeler.py
```

GUI commands:

```text
Train hybrid meta-labeler
Backtest hybrid meta-labeler
```

Tests:

```text
tests/unit/ai/test_hybrid_meta_labeler.py
tests/unit/presentation/test_architecture_knobs_gui.py
```

Training script:

```text
scripts/train_hybrid_meta_labeler.py
```

Capabilities:

```text
- classifier task on target_trade_win
- regressor task on target_trade_score_r
- candidate-only training default = 1
- chronological train/validation/test split
- LightGBM/XGBoost/CatBoost backends
- model artifact and ModelRecord save
- initial decision threshold saved in record.decision_thresholds
```

Backtest script:

```text
scripts/backtest_hybrid_meta_labeler.py
```

Capabilities:

```text
- loads saved meta model
- applies meta_threshold / score_threshold to candidate rows
- single-position chronological replay using Phase127 target_exit_index
- HTML/JSON/CSV report
- account view with initial_capital and units
```

Outputs:

```text
run_logs/hybrid_meta_labeler/latest.json
run_logs/hybrid_meta_backtest/latest.json
run_logs/hybrid_meta_backtest/latest.html
run_logs/hybrid_meta_backtest/latest.csv
```

First recommended train command:

```powershell
python -u scripts/train_hybrid_meta_labeler.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --task classifier `
  --target target_trade_win `
  --booster lightgbm `
  --candidate-only 1 `
  --train-frac 0.70 `
  --val-frac 0.15 `
  --class-weight auto `
  --n-estimators 500 `
  --learning-rate 0.03 `
  --max-depth 3 `
  --num-leaves 31 `
  --meta-threshold 0.55 `
  --save-record 1 `
  --storage-root datasets
```

First recommended backtest command after training:

```powershell
python -u scripts/backtest_hybrid_meta_labeler.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --meta-model-id gold_hybrid_meta_lightgbm_5m `
  --meta-model-version 0 `
  --meta-threshold -1 `
  --eval-frac 1.0 `
  --max-windows 0 `
  --initial-capital 100 `
  --units 0.1 `
  --storage-root datasets
```

Important precondition:

```text
Phase127A must already have produced:
datasets/processed/XAUUSD/5M/hybrid_telemetry_flat_latest.parquet
```

---

## Operator train result — 2026-09-10

کاربر Phase128A را روی Phase127A matrix-mode telemetry اجرا کرد:

```text
model_id       : gold_hybrid_meta_lightgbm_5m
version        : 1
rows           : 2307
feature_columns: 94
train_rows     : 1614
val_rows       : 346
test_rows      : 347
candidate_only : 1
record_path    : datasets\models\gold_hybrid_meta_lightgbm_5m\v1_training.json
```

Validation metrics:

```text
accuracy      : 0.6445086705202312
precision     : 0.6572327044025157
recall        : 0.9372197309417041
f1            : 0.7726432532347505
AP            : 0.7864284978741574
positive_rate : 0.9190751445086706
base_rate     : 0.6445086705202312
```

Test metrics:

```text
accuracy      : 0.5072046109510087
precision     : 0.49554896142433236
recall        : 0.9940476190476191
f1            : 0.6613861386138613
AP            : 0.619043571505885
positive_rate : 0.9711815561959655
base_rate     : 0.484149855907781
```

نتیجه:

```text
مدل ranking signal دارد چون AP از base_rate بهتر است، اما threshold=0.55 خیلی permissive است. تست بعدی باید backtest معاملاتی و سپس threshold grid در Phase132 باشد.
```

---

## Operator backtest result — 2026-09-10

کاربر `scripts/backtest_hybrid_meta_labeler.py` را برای `gold_hybrid_meta_lightgbm_5m v1` اجرا کرد.

```text
threshold_source : model_record:gold_hybrid_meta_lightgbm_5m:v1
meta_threshold   : 0.55
rows/evaluated   : 8000 / 8000
trades           : 143
buy/sell         : 74 / 69
wins/losses      : 94 / 49
win_rate         : 65.7343%
total_pnl        : +509.5359231829643
profit_factor    : 2.608242691826868
max_drawdown     : 91.44515466690063
coverage         : 1.7875%
```

Account view:

```text
initial_capital   : 100
units             : 0.1
final_balance     : 150.95359231829644
net_profit        : +50.953592318296444
max_drawdown_cash : 9.144515466690065
would_breach_zero : false
```

Monthly concentration:

```text
2026-07: +526.1065, 60 wins / 0 losses
2026-08: -16.5706, 34 wins / 49 losses
```

نتیجه:

```text
PASS به‌عنوان اولین meta-filter backtest روی 8000-row matrix، اما هنوز robust نیست. سود به‌شدت روی July متمرکز است، بنابراین Phase132 threshold grid و Phase133 walk-forward الزامی‌اند.
```

---

## Operator full-stream train result — 2026-09-12

After Phase127A full stream telemetry succeeded, the operator retrained the flat LightGBM meta-labeler:

```text
model_id          : gold_hybrid_meta_lightgbm_5m
version           : 2
flat_path         : datasets\processed\XAUUSD\5M\hybrid_telemetry_flat_latest.parquet
task              : classifier
target            : target_trade_win
rows              : 13757
feature_columns   : 94
train/val/test    : 9629 / 2064 / 2064
candidate_only    : 1
booster           : lightgbm
class_weight      : auto
n_estimators      : 500
learning_rate     : 0.03
max_depth         : 3
num_leaves        : 31
record_path       : datasets\models\gold_hybrid_meta_lightgbm_5m\v2_training.json
```

Validation metrics:

```text
accuracy           : 0.5876937984496124
precision@0.55     : 0.5464733025708636
recall@0.55        : 0.8356854838709677
f1@0.55            : 0.6608210442407334
AP                 : 0.6117950637217242
positive_rate      : 0.7349806201550387
base_rate          : 0.4806201550387597
tp/fp/tn/fn        : 829 / 688 / 384 / 163
```

Test metrics:

```text
accuracy           : 0.6603682170542635
precision@0.55     : 0.6214614878209348
recall@0.55        : 0.8822429906542056
f1@0.55            : 0.7292390884511395
AP                 : 0.7147311817866087
positive_rate      : 0.7359496124031008
base_rate          : 0.5184108527131783
tp/fp/tn/fn        : 944 / 575 / 419 / 126
```

Interpretation:

```text
The full-stream v2 classifier has ranking signal: AP is above base rate on both validation and test.
However, classification metrics alone are not acceptance. The decisive check is Phase133 walk-forward trading performance.
```
