# فاز ۶۵ — نقاط انتخاب مدل سیگنال روی ریپلی (درخواست اپراتور)

**تاریخ:** 2026-08-27 · **وضعیت:** ✅ کامل (pytest 1483 passed · 49 skipped · ruff/black ✅)

**درخواست:** «توی ریپلی نقاطی که قراره ترید گرفته بشه رو رنگی نشون بده — حتی اگه
از نظر حد سود/ضرر رد بشن و ترید باز نشه — و خرید و فروش مجزا باشن.»

---

## ۱. چی اضافه شد

### دامنه (`domain/simulation/replay.py`)
- VO جدید **`SignalMarker`**: `bar · timestamp · side(buy/sell) · confidence ·
  outcome · reason` با سه وضعیت: `candidate` (انتخاب شد، حکم بعداً) ·
  `filled` (واقعاً ترید شد) · `rejected` (گیت/براکت رد کرد).
- `ReplayRecorder.record_signal()` + `resolve_signal()`؛ `build()` کاندیداهای
  باقی‌مانده را با entry واقعی جفت می‌کند (**claim-based**: هر fill حداکثر
  یک candidate — نزدیک‌ترین قبل از خودش — می‌گیرد؛ از آخر به اول پردازش).
- `ReplayTape.signal_points` + خروجی JSON (`to_dict`) برای رندرر.

### موتور (`infrastructure/simulation/backtest_engine.py`)
- `_record_signal_point()` بعد از هر strategy.evaluate: فقط پیش‌بینی‌های
  **actionable** (عبور از آستانهٔ confidence همان source) ثبت می‌شوند؛
  BUY/SELL از کلاس برنده.
- رد گیت‌های استراتژی → `rejected` + دلیل (confidence/range/cost/…).
- مسیر next-open: اگر کندل بعد براکت رد کرد یا quote نبود → `rejected`
  با دلیل (`bracket rejected (R/R or gap)`).
- مبهم‌گذاری filled: در `build()` با entry markerهای واقعی — نه حدس.

### رندرر (`presentation/web/replay_renderer.py`)
- مثلث‌ها روی چارت: **▲ سبز = BUY** زیر کندل، **▼ قرمز = SELL** بالای کندل.
- **توپر = ترید واقعاً باز شد** · **توخالی = رد شد** (گیت یا براکت).
- legend با شمارش: تعداد BUY / SELL / filled / rejected.

## ۲. رفع‌های جانبی (گیت سبز)
- `dual_model_prediction_source`: property `min_signal_confidence` + import
  `Decimal` جاافتاده از فاز ۵۷ (F821 قدیمی) + مرتب‌سازی import.
- `backtest_engine`: E741 (`l`) و F841/B023/E501 قدیمی trainer... (همین فایل: E741 اصلاح شد).

## ۳. تست‌ها
`tests/unit/simulation/test_replay_signal_points.py` — ۵ تست: اعتبارسنجی VO،
عدم-جهش state در resolution، جفت‌شدن candidate با entry، عدم اشتراک دو
candidate در یک fill، خوراک JSON رندرر.

```
ruff ✅ black ✅
pytest 1483 passed, 49 skipped   (قبلاً 1478)
```

## ۴. یادداشت استفاده
بعد از بکتست، `replay.html` را باز کن: مثلث‌های توخالی = نقاطی که مدل
انتخاب کرد ولی گیت/براکت رد کرد — با شمارش‌های legend می‌توانی ببینی گلوگاه
کدام مرحله است (مثلاً همه BUY پر و SELL همه توخالی = سوگیری R/R نسبت به
شورت). این دقیقاً همان قیفی است که برای دیباگ trades=0 لازم بود.

---

## فاز ۶۶ — سطوح TP/SL مدل کنار هر نقطه سیگنال (درخواست اپراتور)

**درخواست:** «توی همین نقاط احتمالی، مقادیر حد سود و حد ضرر هم نمایش داده بشه.»

### تغییرات
- **SignalMarker:** فیلدهای اختیاری `take_profit` / `stop_loss` (سطح مطلق).
- **Engine:** در لحظهٔ تصمیم، اگر رنج forecast منسجم داشته باشد:
  BUY → tp=predicted_high, sl=predicted_low؛ SELL برعکس. برای نقاط
  `rejected` هم ثبت می‌شود (قرارداد دیده شود حتی وقتی ترید رد شد).
- **Next-open fill:** بعد از fill موفق، سطوح **واقعی براکت** (با گسترش
  spread و R/R) جایگزین سطوح خام مدل می‌شوند — یعنی چیزی که رسم می‌شود
  «قرارداد اجراشده» است.
- **Renderer:** خط‌چین افقی سبز (TP) و قرمز (SL) با عرض ~۲× کندل، اتصال
  عمودی نقطه‌دار مثلث↔سطوح، قیمت‌ها فقط در زوم کافی (step>8)؛ rejected با
  شفافیت کمتر. دو آیتم legend جدید.
- **۲ تست جدید** (+۱ به‌روز): حفظ سطوح در resolution، override براکت،
  اعتبارسنجی سطح غیرمثبت، payload.

```
ruff ✅ black ✅  pytest 1485 passed, 49 skipped   (قبلاً 1483)

---

## فاز ۶۷ — باگ ۵۰: بافر 1D از تاریخچه پیش‌پر نمی‌شد → هیچ TP/SLای رسم نمی‌شد

**گزارش اپراتور:** «مثلث‌ها هستن ولی هیچ حد سود/ضرری با خط‌چین مشخص نشده —
یا رندر خرابه یا از مدل رنج قیمتی نیومده.»

### ریشه (با شبیه‌سازی واقعی، نه حدس)

زنجیرهٔ ثبت TP/SL سالم بود؛ مشکل بالاتر بود: `DualModelPredictionSource`
بافر کندل‌های 1D را فقط با `observe` (کندل‌های بسته‌شده *در طول replay*)
پر می‌کرد — بافر شروع = **خالی**:

```
۹٬۰۰۰ کندل 5M = ۳۱ روز replay → فقط ~۳۱ کندل 1D در طول replay بسته می‌شود
مدل رنج window=150 می‌خواهد → رنج تا «۱۵۰ روز بعد از شروع replay» هرگز
تولید نمی‌شد → هر نقطهٔ سیگنال tp/sl=None → خط‌چینی برای رسم وجود نداشت
```

(دیتای 5M کاربر 50k است؛ پس حتی کل دیتاست هم 173 روز بود — هنوز کم!)

### رفع

در سازندهٔ source: کندل‌های 1D **بسته‌شدهٔ قبل از اولین کندل 5M** از
تاریخچه (همان ۵٬۶۹۸ کندل کاربر) یک‌جا در بافر pre-fill می‌شوند و cursor
جلو می‌رود تا `observe` تکرار نکند. علیت دست نمی‌خورد — اینها همه قبل از
شروع replay بسته شده‌اند و مدل حق دارد ببیندشان (مثل آموزش).

### تأیید عددی (شبیه‌سازی با forecast جعلی)

قبل: `range_predictions_made=0 · abstentions=300`
بعد: **`range_predictions_made=151`** · `last_range = (2012.0, 1990.0)` ✓

### تست

`tests/unit/simulation/test_range_history_prefix.py` — ۲ تست: pre-fill
تاریخچه + رنج از اولین سیگنال در replay کوتاه.

```
ruff ✅ black ✅
pytest 1487 passed, 49 skipped   (قبلاً 1485)
```
