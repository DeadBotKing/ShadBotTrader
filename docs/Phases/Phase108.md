# فاز ۱۰۸ — پیشنهاد: class weights + F1/PR-AUC برای trend_signal

**وضعیت:** 🟡 پیشنهادی / آمادهٔ اجرا
**نوع:** AI training quality improvement
**اولویت:** بسیار بالا

---

## هدف

`trend_signal` سه‌کلاسه است:

```text
0 = SELL
1 = HOLD
2 = BUY
```

در چنین مسئله‌ای accuracy ساده گمراه‌کننده است. اگر HOLD زیاد باشد، مدل می‌تواند با گفتن HOLD ظاهراً خوب شود ولی برای trading بی‌ارزش باشد. باید class weighting و metrics مخصوص BUY/SELL اضافه شود.

---

## تغییرات trainer

در `WavenetTrainer`:

```text
class_weight یا sample_weight per fold
```

فرمول برای هر fold و فقط train fold:

```text
weight_i = total_train_samples / (num_classes * count_i)
```

برای مسیر `tf.data` اگر `class_weight` با dataset کار نکرد، باید sample_weight در generator تولید شود.

---

## metrics لازم

```text
val_sell_precision
val_sell_recall
val_sell_f1
val_hold_precision
val_hold_recall
val_hold_f1
val_buy_precision
val_buy_recall
val_buy_f1
val_macro_f1
val_buy_sell_f1
val_balanced_accuracy
val_pr_auc_buy
val_pr_auc_sell
```

---

## monitor پیشنهادی

برای `gold_trend_signal_*`:

```text
monitor=val_buy_sell_f1
```

یا اگر پیاده‌سازی ساده‌تر باشد:

```text
monitor=val_macro_f1
```

نه `val_loss` تنها.

---

## CLI/GUI پیشنهادی

```text
--class-weight auto|off
--monitor-metric auto|val_loss|val_macro_f1|val_buy_sell_f1
```

GUI:

```text
Class weight = auto/off
Monitor metric = auto
```

---

## فایل‌های درگیر

```text
src/ShadBotTrader/infrastructure/ai/wavenet/wavenet_trainer.py
src/ShadBotTrader/infrastructure/ai/window_generator.py
src/ShadBotTrader/application/services/dual_model_service.py
src/ShadBotTrader/infrastructure/ai/training_progress.py
scripts/run_dual_models.py
src/ShadBotTrader/presentation/commands/handlers.py
```

---

## معیار پذیرش

```text
- class weights فقط از train fold محاسبه شود.
- metricهای per-class در fold_metrics ذخیره شوند.
- مدل روی کلاس HOLD قفل نشود بدون اینکه گزارش شود.
- checkpoint/best epoch بتواند با F1 انتخاب شود.
```
