# فاز ۱۰۸ — class weights + F1/PR-AUC برای trend_signal

**تاریخ:** 2026-09-07
**وضعیت:** ✅ کامل — class weights، metricهای per-class، GUI و تست انجام شد
**گزارش:** `docs/Report/PHASE108_TREND_SIGNAL_CLASS_WEIGHT_F1_REPORT.md`

---

## هدف

`trend_signal` سه‌کلاسه است:

```text
0 = SELL
1 = HOLD
2 = BUY
```

accuracy ساده برای چنین مسئله‌ای کافی نیست. خروجی واقعی Phase107 نشان داد baseline اکثریت 40% است و foldهای validation آخر regime-shift دارند. پس باید class weights و metricهای per-class اضافه شود.

---

## CLI جدید

```text
--class-weight {auto,off}
```

رفتار:

```text
trend_signal + auto → وزن متعادل جداگانه برای train fold همان fold
سایر مدل‌ها → off
```

---

## فرمول class weight

```text
weight_i = total_train_samples / (num_classes * count_i)
```

کلاس‌های بدون نمونه حذف می‌شوند.

---

## metricهای جدید

برای validation محاسبه می‌شود:

```text
val_sell_precision / val_sell_recall / val_sell_f1 / val_sell_ap
val_hold_precision / val_hold_recall / val_hold_f1 / val_hold_ap
val_buy_precision  / val_buy_recall  / val_buy_f1  / val_buy_ap
val_balanced_accuracy
val_macro_f1
val_weighted_f1
val_buy_sell_f1
probability mean/stdev per class
```

---

## GUI

در فرم‌های Train/Retrain/Optimise فیلد جدید اضافه شد:

```text
Trend-signal class weights = auto / off
```

فقط برای model=`trend_signal` به CLI پاس داده می‌شود:

```text
--class-weight auto
```

---

## تغییرات کد

```text
scripts/run_dual_models.py
src/ShadBotTrader/infrastructure/ai/wavenet/wavenet_trainer.py
src/ShadBotTrader/infrastructure/ai/window_generator.py
src/ShadBotTrader/infrastructure/ai/training_progress.py
src/ShadBotTrader/application/services/dual_model_service.py
src/ShadBotTrader/presentation/commands/handlers.py
```

---

## تست‌ها

```text
tests/unit/ai/test_classification_weights_metrics.py
tests/unit/ai/test_phase108_trend_signal_training_config.py
tests/unit/ai/test_window_generator.py
tests/integration/test_streamed_fold_progress.py
tests/integration/test_training_visibility.py
tests/unit/presentation/test_architecture_knobs_gui.py
```

Targeted tests و ruff/black روی فایل‌های تغییرکرده سبز شد.

---

## نحوه اجرا

GUI:

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

CLI:

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

## گام بعد

Phase109:

```text
threshold calibration و heatmap backtest
```

اما قبلش اپراتور باید یک training واقعی `trend_signal` با class weights اجرا کند و خروجی QUALITY را بفرستد.
