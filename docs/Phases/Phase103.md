# فاز ۱۰۳ — ممیزی محاسبه/نرمال‌سازی trend_score و حذف fake tail label

**تاریخ:** 2026-09-07  
**وضعیت:** ✅ کامل  
**Commit:** `db515b4`

---

## مسئله

اپراتور پرسید آیا نرمال‌سازی دیتاست و محاسبات score درست انجام شده‌اند؟ چون مدل score حتی روی train loss هم به اندازهٔ انتظار مدل قوی کاهش نشان نمی‌داد.

---

## audit انجام‌شده

بررسی شد:

```text
src/ShadBotTrader/infrastructure/ai/feature_matrix.py
src/ShadBotTrader/infrastructure/ai/data_windowing.py
src/ShadBotTrader/infrastructure/ai/window_generator.py
src/ShadBotTrader/infrastructure/ai/target_builder.py
src/ShadBotTrader/application/services/dual_model_service.py
```

---

## نتیجه audit

### محاسبه score درست بود

برای `label_horizon=1`:

```text
score[t] = (close[t+1] - open[t+1]) / (high[t+1] - low[t+1])
```

چند نمونه دستی با target آماده‌شده مقایسه شد و diff صفر بود.

### target داخل input نبود

windowهای ورودی فقط featureها را داشتند و target column حذف می‌شد.

### feature scaling درست بود

در آن زمان scaling عمومی per-window به `[-2,+2]` بود و مقدارها finite و داخل بازه بودند.

---

## باگ واقعی پیدا شده

در مسیر `trend_score`، rowهایی که آینده نداشتند این‌طور پر می‌شدند:

```python
score_by_index.get(orig, 0.0)
```

یعنی آخرین row بدون کندل آینده، به جای حذف شدن، target جعلی `0.0` می‌گرفت.

این برای training غلط است، چون `0.0` یعنی کندل آینده واقعاً بی‌رون بوده، در حالی که اصلاً آینده‌ای وجود نداشت.

---

## اصلاح

در `DualModelService.prepare()` برای `gold_trend_score_*`:

```text
targets = [[score] for score in ts.scores]
target_source_index = ts.source_index
attach_targets(...)
```

یعنی:

```text
ردیف‌های بدون آینده حذف می‌شوند.
هیچ fake 0.0 برای tail ساخته نمی‌شود.
```

شاخه duplicate تاریخی trend_score هم اصلاح شد.

---

## عدد audit بعد از fix

روی دیتای سندباکس:

```text
candles = 2513
rows    = 2295
finite  = True
y_min   = -1.0
y_max   = +1.0
y_mean  = +0.039367
y_median= +0.058824
last_target = -0.3608903
```

آخرین target حالا score کندل واقعی آخر است، نه fake zero.

---

## اهمیت

این bug integrity باید fix می‌شد، اما احتمالاً علت اصلی ضعف score نبود، چون تعداد rowهای آلوده بسیار کم بود. علت اصلی همچنان noise-heavy بودن direction/score یک‌روزهٔ gold با featureهای price-only است.
