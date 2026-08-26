# فاز ۳۷ — پیشرفت زندهٔ ویژگی‌ها، و یک انبار جدا برای هر سری

**تاریخ:** 2026-08-17
**وضعیت:** ✅ کامل — Quality Gate سبز

**دو درخواست کاربر:**

> «ویژگی ها رو هم Update features وقتی ران میزنم، نشون بده که الان کدوم ویژگی
> داره حساب میشه چندتاشو حساب کرده دیتا رو ساخته چندتای دیگ مونده»

> «و اینک چک کن که برای 5 دقیقه و 1ساعته برای هرکدومشون جدا جدا ویژگی ها
> محاسبه و ذخیره میشن؟»

سؤال دوم یک **باگ جدی** را لو داد. جواب صادقانه: محاسبه بله، ذخیره **نه**.

---

## ۱. باگ ۲۸ — ویژگی‌های ۵ دقیقه و ۱ ساعته روی هم می‌افتادند

مسیر ذخیره‌سازی این بود:

```
features/{feature_id}/v{version}.parquet
```

**نه نماد، نه تایم‌فریم.** یعنی:

```
محاسبهٔ atr_14 برای XAUUSD 5M  →  features/atr_14/v1.parquet
محاسبهٔ atr_14 برای XAUUSD 1H  →  features/atr_14/v2.parquet   ← همان پوشه!
```

دو کمیت کاملاً متفاوت — یکی میانگین دامنهٔ ۵ دقیقه‌ای، یکی ۱ ساعته — کنار هم
می‌نشستند و هیچ چیز آن‌ها را از هم تشخیص نمی‌داد. `load("atr_14", 1)`
نمی‌توانست بگوید کدام سری را برگردانده.

### اثباتش (قبل از رفع)

```
computed 5M
computed 1H

files under features/atr_14 : ['v1.parquet', 'v2.parquet']
  v1.parquet: 300 rows
  v2.parquet: 300 rows

-> no symbol or timeframe anywhere in the path or the file.
```

در مخزن خودت هم ۲۲ نسخهٔ بی‌نام‌ونشان زیر `datasets/features/atr_14/` بود.

**چرا تا حالا فاجعه نشده بود:** مدل‌ها ویژگی‌ها را از این انبار نمی‌خوانند —
`build_feature_matrix` همه را در حافظه از نو حساب می‌کند. پس آموزش سالم بود.
ولی هر چیزی که *بخواهد* این انبار را بخواند (بازرسی `/data`، تحلیل بعدی،
هر مصرف‌کنندهٔ آینده) دیتای اشتباه می‌گرفت. یک بمب ساعتی، نه یک انفجار.

### حالا

```
features/{symbol}/{timeframe}/{feature_id}/v{version}.parquet
```

```
features/XAUUSD/5M/atr_14/v1.parquet    ← first value 2.7312
features/XAUUSD/1H/atr_14/v1.parquet    ← first value 6.5696
```

هر سری شمارندهٔ نسخهٔ **مستقل** خودش را دارد. `for_series(symbol, timeframe)`
یک نمونهٔ جدید برمی‌گرداند (نه mutate) تا سرویسی که store دارد، زیر پایش
عوض نشود.

**پورت `FeatureRepository` دست نخورد.** طبق فریز فاز ۲۶، امضای متدها
(`feature_id`, `version`) همان است؛ scope به **نمونه** بسته شد نه به امضا.

---

## ۲. پیشرفت زنده — دقیقاً همان چیزی که خواستی

```
==========================================================================
  FEATURES  FXTradingFeatureSetV1
==========================================================================
  series    : XAUUSD 5M
  candles   : 1,000
  features  : 109
--------------------------------------------------------------------------
[----------------------------]   0.0% |   1/109 | open_filter
      stored v1 | 1,000 values | quality 98.69
[----------------------------]   0.9% |   2/109 | close_filter
      stored v1 | 1,000 values | quality 98.69
[#---------------------------]   1.8% |   3/109 | low_filter
      stored v1 | 1,000 values | quality 98.69
...
--------------------------------------------------------------------------
  109/109 stored | 0 quarantined | 32 research-only
  total time: 1s
==========================================================================
```

هر خط می‌گوید: **کدام** ویژگی، **چندتا از چندتا**، **چند درصد**، و بعد از
محاسبه: چند مقدار تولید شد و کیفیتش چقدر بود. اگر قرنطینه شود، دلیلش را
می‌نویسد.

قرارداد `FeatureProgressReporter` عمداً شبیه `TrainingProgressReporter` فاز
۳۶ است — دو عملیات طولانی در یک محصول نباید دو شکل مختلف گزارش بدهند.

### در داشبورد

دکمهٔ `Update features` حالا در همان پنل لاگ زندهٔ فاز ۳۶ می‌نویسد (هر ۲
ثانیه رفرش). این هندلر داخل خود پروسه اجرا می‌شود نه زیرپروسه، پس
مستقیماً در `run_logs/compute_features.log` می‌نویسد.

### فیلد Timeframes

مثل فاز ۳۵، این دکمه هم حالا لیست می‌گیرد و پیش‌فرضش `5M,1H` است:

```
succeeded | XAUUSD: features computed for 5M, 1H
   feature set : FXTradingFeatureSetV1
   5M: 109/109 stored over 1,000 candles (0 quarantined, 32 research-only)
   1H: 109/109 stored over 1,000 candles (0 quarantined, 32 research-only)
   109 definitions registered in the database
   Each timeframe is stored separately: features/{symbol}/{timeframe}/
```

اگر یک تایم‌فریم کندل نداشته باشد، همان یکی SKIP می‌شود و بقیه ادامه
می‌دهند — با گزارش صریح.

### صفحهٔ /data

جدول ویژگی‌ها یک ستون **Series** گرفت:

| Feature | Series | Latest | Versions | Size |
|---|---|---|---|---|
| atr_14 | XAUUSD 5M | v1 | 1 | 3.2 KB |
| atr_14 | XAUUSD 1H | v1 | 1 | 3.2 KB |

دیتای قدیمی (قبل از فاز ۳۷) پنهان نمی‌شود؛ با برچسب
`legacy (no timeframe recorded)` می‌آید تا بدانی کدام‌ها هویت نامعلوم دارند.

---

## ۳. فایل‌ها

### جدید
| فایل | نقش |
|---|---|
| `infrastructure/feature/feature_progress.py` | `FeatureProgressReporter`، `NullFeatureProgress`، `ConsoleFeatureProgress` |
| `tests/integration/test_feature_visibility.py` | ۱۹ تست |

### تغییر کرده
| فایل | تغییر |
|---|---|
| `infrastructure/feature/parquet_feature_store.py` | چیدمان `{symbol}/{timeframe}/`، `for_series()`، `scope`، `root`، پاک‌سازی نام مسیر |
| `application/services/feature_computation_service.py` | پارامتر `progress`، scope کردن خودکار repository، فراخوانی reporter |
| `presentation/commands/handlers.py` | `compute_features` چند‌تایم‌فریمی با لاگ زنده |
| `presentation/gateway/data_inspector.py` | پیمایش چیدمان جدید + برچسب legacy |
| `presentation/web/data_renderer.py` | ستون Series |
| `tests/integration/test_feature_pipeline.py` | تطبیق با قرارداد جدید (`for_series`) |
| `tests/unit/presentation/test_commands.py` | تطبیق با پیام جدید |

---

## ۴. تأیید

```
black --check .                 ✅
ruff check .                    ✅
mypy src --python-version 3.12  ✅ 289 files
pytest                          ✅ 1247 passed, 12 skipped   (قبلاً 1228)
RUN_TF=1                        ✅ 278 + 389 + 592
```
**۱۹ تست جدید.**

### تست زندهٔ داشبورد

```
POST /run  command=compute_features  timeframe=5M,1H

succeeded | XAUUSD: features computed for 5M, 1H
  5M: 109/109 stored over 1,000 candles
  1H: 109/109 stored over 1,000 candles

on disk:
  /tmp/live37/features/XAUUSD/5M/atr_14/v1.parquet
  /tmp/live37/features/XAUUSD/1H/atr_14/v1.parquet
  5M: 109 پوشه   1H: 109 پوشه

run log: 218 خط "stored v1"  (109 × 2)
```

یک تست هم هست که ثابت می‌کند **reporter نتیجه را عوض نمی‌کند**: اجرای با و
بدون گزارشگر، دقیقاً همان feature_id/version/available_count را می‌دهد. یک
ناظر که چیزی را که می‌بیند تغییر بدهد، باگ است نه امکانات.

---

## ۵. دربارهٔ دیتای قدیمی مخزن

`datasets/features/` فعلی (۲۲ نسخه به ازای هر ویژگی، بدون نماد و تایم‌فریم)
**پاک نشد**. سه دلیل:

1. حذف دیتای کاربر بدون اجازه، کار من نیست.
2. هویتشان قابل بازیابی نیست — نمی‌شود حدس زد کدام v چه تایم‌فریمی بوده،
   و حدس‌زدن دقیقاً همان اشتباهی است که این فاز رفعش کرد.
3. `/data` آن‌ها را با برچسب `legacy` نشان می‌دهد، پس نامرئی نیستند.

اگر خواستی پاکشان کنم بگو — یا فقط `datasets/features/` را دستی حذف کن و
`Update features` را دوباره بزن تا با چیدمان جدید ساخته شوند.

---

## ۶. آنچه هنوز باز است

- **ویژگی‌های ذخیره‌شده هنوز توسط هیچ‌کس خوانده نمی‌شوند.** آموزش از
  `build_feature_matrix` استفاده می‌کند که همه را در حافظه از نو حساب
  می‌کند. انبار الان درست است ولی هنوز مصرف‌کننده ندارد؛ وصل‌کردنش یک
  تصمیم معماری جداست (محاسبهٔ مجدد امن‌تر است، خواندن از انبار سریع‌تر).
- **پیشرفت درون یک ویژگی** دیده نمی‌شود. اگر یک calculator روی ۱۰۰ هزار
  کندل دو دقیقه طول بکشد، همان دو دقیقه روی یک خط می‌ماند. ریزدانگی در
  حد «هر ویژگی» است.
- `FeatureQualityEngine` نمرهٔ ۹۸.۶۹ می‌دهد ولی مقیاسش (۰-۱۰۰) در خروجی
  توضیح داده نشده.
