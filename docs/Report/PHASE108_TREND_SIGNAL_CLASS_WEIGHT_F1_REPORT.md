# فاز ۱۰۸ — class weights + F1/PR-AUC برای trend_signal

تاریخ: 2026-09-07
وضعیت: ✅ کامل — پیاده‌سازی، GUI، تست و مستندسازی انجام شد.

---

## 1) دلیل فاز

خروجی واقعی Phase107 روی دیتای اپراتور:

```text
SELL=21,130 (40.0%)
HOLD=12,715 (24.0%)
BUY =19,036 (36.0%)
majority baseline=40.0%
```

توزیع کلی extreme نیست، اما foldهای validation آخر regime-shift دارند:

```text
fold 1 val: SELL=424, HOLD=594, BUY=982
fold 2 val: SELL=627, HOLD=441, BUY=932
fold 3 val: SELL=640, HOLD=469, BUY=891
```

پس accuracy تنها کافی نیست. باید per-class precision/recall/F1 و class weighting داشته باشیم.

---

## 2) خروجی‌های اصلی فاز

### CLI جدید

به `scripts/run_dual_models.py` اضافه شد:

```text
--class-weight {auto,off}
```

رفتار:

```text
trend_signal + auto → balanced class weights per roll-forward train fold
سایر مدل‌ها → off، حتی اگر فلگ داده شود
```

در لاگ training برای trend_signal چاپ می‌شود:

```text
class wgt.: auto (balanced per roll-forward train fold)
```

---

## 3) class weight per fold

در `WavenetTrainer`، برای classification و وقتی `class_weight_mode='auto'` باشد، وزن کلاس‌ها فقط از train slice همان fold محاسبه می‌شود:

```text
weight_i = total_train_samples / (num_classes * count_i)
```

کلاس‌های غایب حذف می‌شوند، چون نمونه‌ای برای وزن دادن ندارند.

نمونه helper:

```python
class_weight_for_labels([0,0,0,1,2,2], num_classes=3)
# {0: 0.666..., 1: 2.0, 2: 1.0}
```

برای مسیرهای بزرگ streamed، sample weights داخل `tf.data.Dataset` به صورت triple برگردانده می‌شوند:

```text
(x, y, sample_weight)
```

برای مسیر in-memory، `sample_weight=` به `model.fit` پاس داده می‌شود.

---

## 4) metricهای جدید

در validation epoch-end محاسبه و به logs تزریق می‌شود:

```text
val_sell_precision
val_sell_recall
val_sell_f1
val_sell_support
val_sell_ap
val_sell_prob_mean
val_sell_prob_stdev

val_hold_precision
val_hold_recall
val_hold_f1
val_hold_support
val_hold_ap
val_hold_prob_mean
val_hold_prob_stdev

val_buy_precision
val_buy_recall
val_buy_f1
val_buy_support
val_buy_ap
val_buy_prob_mean
val_buy_prob_stdev

val_accuracy_from_confusion
val_balanced_accuracy
val_macro_f1
val_weighted_f1
val_buy_sell_f1
```

`AP` همان Average Precision / PR-AUC approximation بدون dependency اضافی sklearn است.

---

## 5) checkpoint / monitor

فاز ۱۰۸ امکان monitorهای max را آماده کرد:

```text
val_macro_f1
val_buy_sell_f1
val_auc
val_precision
val_recall
```

تابع جدید:

```python
metric_monitor_mode(metric)
```

اگر metric از جنس F1/AUC/accuracy/precision/recall باشد، checkpoint و callbacks باید maximize کنند؛ برای loss/MAE همچنان minimize.

فعلاً auto monitor برای trend_signal را به صورت محافظه‌کارانه روی `val_loss` نگه داشتیم تا رفتار historical ناگهان عوض نشود. اما اگر اپراتور خواست می‌تواند CLI بدهد:

```text
--monitor-metric val_buy_sell_f1
```

در آن حالت custom classification callback قبل از checkpoint اجرا می‌شود و logs شامل F1 خواهد بود.

---

## 6) GUI

در فرم‌های training/retraining/optimise فیلد جدید اضافه شد:

```text
Trend-signal class weights = auto / off
```

این فیلد فقط وقتی model=`trend_signal` باشد به CLI پاس داده می‌شود:

```text
--class-weight auto
```

برای سایر مدل‌ها نادیده گرفته می‌شود.

---

## 7) فایل‌های تغییرکرده/جدید

### تغییرکرده

```text
scripts/run_dual_models.py
src/ShadBotTrader/infrastructure/ai/wavenet/wavenet_trainer.py
src/ShadBotTrader/infrastructure/ai/window_generator.py
src/ShadBotTrader/infrastructure/ai/training_progress.py
src/ShadBotTrader/application/services/dual_model_service.py
src/ShadBotTrader/presentation/commands/handlers.py
```

### تست‌های جدید/تغییرکرده

```text
tests/unit/ai/test_classification_weights_metrics.py
tests/unit/ai/test_phase108_trend_signal_training_config.py
tests/unit/ai/test_window_generator.py
tests/integration/test_streamed_fold_progress.py
tests/integration/test_training_visibility.py
tests/unit/presentation/test_architecture_knobs_gui.py
```

---

## 8) تست‌ها

Targeted:

```text
python -m pytest tests/unit/ai/test_classification_weights_metrics.py \
  tests/unit/ai/test_window_generator.py \
  tests/integration/test_streamed_fold_progress.py \
  tests/unit/ai/test_phase108_trend_signal_training_config.py \
  tests/integration/test_training_visibility.py \
  tests/unit/presentation/test_architecture_knobs_gui.py -q
```

نتیجه:

```text
passed (با skipهای TensorFlow طبق markerهای موجود)
```

همچنین targeted ruff/black روی فایل‌های تغییرکرده سبز شد.

Full pytest:

```text
python -m pytest -q
→ passed (TF tests طبق markerهای موجود skip شدند)
```

Full `mypy src` همچنان همان 28 خطای pre-existing را دارد و بعد از رفع دو خطای جدید، خطای جدیدی از Phase108 باقی نماند.

---

## 9) smoke test بدون TensorFlow

```bash
PYTHONPATH=src python scripts/run_dual_models.py --with-features --symbol TESTSYM \
  --model trend_signal --signal-timeframe 5M --epochs 1 --folds 1 \
  --window 50 --label-horizon 20 --atr-mult 0.5 \
  --class-weight auto --storage-root datasets
```

در لاگ درست چاپ شد:

```text
class wgt.: auto (balanced per roll-forward train fold)
```

چون در سندباکس TensorFlow نصب نبود، training skip شد؛ ولی مسیر prepare/CLI/GUI تأیید شد.

---

## 10) نحوه اجرای پیشنهادی برای اپراتور

از GUI:

```text
Train a model
model = trend_signal
dataset = 5M
window = 288
label_horizon = 288
atr_mult = 0.5
Trend-signal class weights = auto
epochs = 50
folds = 3
learning_rate = 0.0008
```

یا CLI:

```powershell
python -u scripts/run_dual_models.py `
  --with-features `
  --symbol XAUUSD `
  --model trend_signal `
  --signal-timeframe 5M `
  --epochs 50 `
  --folds 3 `
  --window 288 `
  --label-horizon 288 `
  --atr-mult 0.5 `
  --class-weight auto `
  --learning-rate 0.0008 `
  --storage-root datasets
```

---

## 11) انتظار خروجی بعد از training

در هر fold باید خطی شبیه این ببینی:

```text
class weights : class 0: n=... w=... | class 1: n=... w=... | class 2: n=... w=...
```

در epochها برای classification اگر metrics callback اجرا شود:

```text
macro_f1=...
buy_sell_f1=...
```

در QUALITY:

```text
val_macro_f1
val_buy_sell_f1
val_balanced_accuracy
SELL P/R/F1
HOLD P/R/F1
BUY P/R/F1
```

---

## 12) گام بعد

Phase109:

```text
threshold calibration و heatmap backtest برای BUY threshold × SELL threshold
```

اما قبل از Phase109 بهتر است اپراتور یک training trend_signal با class weights اجرا کند و خروجی QUALITY را بفرستد.
