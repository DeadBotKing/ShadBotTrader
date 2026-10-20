# فاز ۱۲۰ — Anti-collapse metrics برای trend_signal

**وضعیت:** ✅ پیاده‌سازی شد  
**نوع:** Evaluation safety / جلوگیری از گول‌خوردن با F1 ظاهراً خوب  
**تاریخ:** 2026-09-08

---

## مسئله

در pilotهای `gold_trend_signal_5m` مشخص شد مدل WaveNet سه‌کلاسه سالم یاد نمی‌گیرد:

```text
class_weight auto → uniform collapse نزدیک 33/33/33
class_weight off  → single-class collapse مثل always-BUY یا always-SELL
```

مشکل مهم این بود که `val_buy_sell_f1` می‌توانست گمراه‌کننده باشد. اگر مدل فقط SELL بگوید و BUY را اصلاً predict نکند، ممکن است:

```text
sell_f1 بالا
buy_f1 = 0
val_buy_sell_f1 = متوسط این دو
```

و عدد ظاهراً قابل قبول شود، در حالی که مدل فقط یک سمت را می‌زند.

---

## تغییرات پیاده‌سازی‌شده

در `classification_report_metrics` متریک‌های زیر اضافه شدند:

```text
val_sell_predicted
val_hold_predicted
val_buy_predicted
val_predicted_class_count
val_single_class_collapse
val_action_min_f1
val_action_min_recall
val_action_min_f1_supported
val_action_min_recall_supported
val_action_supported_class_count
val_action_predicted_supported_count
val_action_collapse
```

مسیر:

```text
src/ShadBotTrader/infrastructure/ai/wavenet/wavenet_trainer.py
```

---

## معنی متریک‌های جدید

### `val_predicted_class_count`

چند کلاس واقعاً توسط مدل predict شده‌اند؟

```text
1 → مدل single-class collapse کرده
2 یا 3 → حداقل چند کلاس را استفاده کرده
```

### `val_action_min_f1`

```text
min(sell_f1, buy_f1)
```

اگر یکی از BUY/SELL صفر باشد، این متریک صفر می‌شود.

### `val_action_min_f1_supported`

فقط سمت‌هایی را حساب می‌کند که در validation واقعاً support دارند. برای مثال اگر یک fold اصلاً SELL نداشته باشد، SELL را جریمه نمی‌کند؛ اما اگر SELL و BUY هر دو در validation باشند و مدل یکی را predict نکند، صفر می‌شود.

### `val_action_collapse`

```text
1 = در validation هر دو سمت BUY/SELL وجود داشتند ولی مدل حداقل یکی را هیچ‌وقت predict نکرد.
0 = collapse اکشن از این نوع دیده نشد.
```

---

## تغییر CLI/GUI

`--monitor-metric` در CLI حالا این گزینه‌ها را هم قبول می‌کند:

```text
val_action_min_f1
val_action_min_f1_supported
```

برای trend_signal، اگر بخواهیم ضد-collapse train/checkpoint کنیم، بهتر است به جای `val_buy_sell_f1` از این استفاده شود:

```text
--monitor-metric val_action_min_f1_supported
```

---

## معیار تصمیم از این به بعد

مدل trend_signal فقط وقتی قابل ادامه است که حداقل این‌ها را پاس کند:

```text
val_action_collapse = 0
val_action_min_f1_supported > 0
val_predicted_class_count >= 2
val_balanced_accuracy > 0.333
```

اگر فقط `val_accuracy` یا `val_buy_sell_f1` خوب باشد ولی `val_action_min_f1_supported=0` باشد، مدل رد می‌شود.

---

## تست‌ها

```text
tests/unit/ai/test_classification_weights_metrics.py
```

تست اضافه شد که single-action collapse را تشخیص دهد.
