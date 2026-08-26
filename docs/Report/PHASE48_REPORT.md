# فاز ۴۸ — تست مدل، بازرسی دیتاست، و نقشهٔ شبکه

**تاریخ:** 2026-08-18
**وضعیت:** ✅ کامل — Quality Gate سبز

---

## ۰. تمیزکاری ورک‌اسپیس

```
BEFORE: 129M          AFTER: 73M
```

| چه چیزی حذف شد | حجم |
|---|---|
| ۱۵۵ اسنپ‌شات قدیمی `project_state/archive` | ۴۶M |
| مدل‌ها و دیتای تست مصنوعی (`TESTSYM`) | ۳M |
| `shadbot.db`, `out.html`, لاگ‌ها، کش‌ها | ~۷M |

**دیتای واقعی XAUUSD تو دست نخورد** — با `git status` تأیید شد که هیچ
فایل track‌شده‌ای حذف نشده.

### ریشهٔ باد کردن حجم

`_archive_previous()` هر اجرا یک اسنپ‌شات می‌ساخت و **هیچ‌وقت چیزی پاک
نمی‌کرد**. بعد از ۱۵۸ اجرا شد ۴۸ مگابایت اسنپ‌شات تقریباً یکسان.
حالا `ARCHIVE_KEEP = 5` سقف دارد. تست شد: بعد از سه اجرای دیگر باز هم ۵.

---

## ۱. تست مدل روی دیتاست انتخابی

دکمهٔ **Test a model on a dataset** در گروه AI:

```
Model    → [gold_range_1d ▼]     (فقط مدل‌های ذخیره‌شده)
Dataset  → [5M] [1H] [1D ▼]      (فقط دیتاست‌های موجود)
Sample at most → 5000
```

نتیجه:
```
gold_range_1d on TESTSYM 1D: mae 0.002858

  model    : gold_range_1d v1 (range)
  dataset  : TESTSYM 1D
  windows  : 500 of 64 x 123
  result   : mae 0.002858
      high_mae    : 0.002808
      low_mae     : 0.002909
      mse         : 0.000013

  NOTE: this model was TRAINED on this timeframe. The score flatters it —
  a model always does better on data it has already seen.

  appended to run_logs/evaluations.jsonl
```

سه تصمیم که عمدی‌اند:

**آموزش اتفاق نمی‌افتد.** وزن‌ها بارگذاری و منجمد می‌شوند. نمره‌ای که از
مدلی بیاید که بی‌سروصدا روی دیتای تست یاد گرفته، ارزیابی نیست.

**پنجره‌ها دقیقاً مثل آموزش ساخته می‌شوند** — همان اندازه، همان
مقیاس‌بندی، همان ترتیب ستون. اگر جور دیگری ساخته می‌شد، عدد مدلی را
توصیف می‌کرد که وجود ندارد.

**اگر روی همان تایم‌فریمِ آموزش تست کنی، می‌گوید.** خطا نیست، ولی عدد
خیلی کمتر معنا دارد.

### لاگ تجمعی

`run_logs/evaluations.jsonl` — یک خط در هر اجرا، **هرگز بازنویسی
نمی‌شود**. مقایسه بی‌ارزش است اگر عدد دیروز پاک شده باشد:

```
model           dataset   mae         trained on  note
gold_range_1d   1D        0.002932    1D          <-- same data it learned
gold_range_1d   1H        0.002932    1D          genuine out-of-sample
```

برای مدل سیگنال، `accuracy` به‌همراه **baseline کلاس غالب** گزارش می‌شود:
`accuracy 83.00% vs baseline 58.00% — BETTER`.

---

## ۲. بازرسی دیتاست

دکمهٔ **Inspect a dataset** در گروه Data:

```
TESTSYM 1D: matrix 597 x 123

  symbol / dataset : TESTSYM 1D
  candles stored   : 700
  range            : 2024-09-17 .. 2026-08-17
  price range      : 1977.68 .. 2021.64

  dataset matrix : 597 rows x 123 columns
                   14 candle-derived + 109 catalogue features
  model input    : 64 rows x 123 columns per window
  windows        : 529 (stride 1, horizon 5)
  tensor shape   : (529, 64, 123)

  columns by kind:
      candle shape  : 6
      feature       : 109
      raw price     : 8

  digest   : 7ac185dfb4b9bda6
  constant columns (1): close_rel
```

اگر ماتریس ساخته نشده باشد، به‌جای خطا می‌گوید کدام دکمه را بزنی.

---

## ۳. ماتریس و نقشهٔ شبکه در هر آموزش

حالا **اول هر اجرا** (چه آموزش اول، چه یادگیری مجدد):

```
==========================================================================
  INPUT MATRIX
==========================================================================
  dataset matrix : 597 rows x 123 columns
                   14 candle-derived + 109 catalogue features
  model input    : 64 rows x 123 columns per window
  windows        : 529 (stride 1, horizon 5)
  tensor shape   : (529, 64, 123)
  if materialised: 0.0 GB  (streamed instead when large)
```

و نقشهٔ معماری به‌صورت PNG، یک بار در هر اجرا:

```
datasets/models/gold_range_1d/v1_architecture.png
```

### سه‌مرحله‌ای، چون graphviz معمولاً روی ویندوز نیست

| تلاش | نتیجه |
|---|---|
| `keras.plot_model` | PNG واقعی از گراف لایه‌ها |
| Pillow | خلاصهٔ متنی رندرشده به PNG |
| آخرین چاره | فایل `.txt` + توضیح چرا |

هر کدام که شد، **آموزش ادامه پیدا می‌کند** و به تو می‌گوید کدام را
گرفتی. در سندباکس مرحلهٔ دوم فعال شد و خروجی خوانا بود:

```
+==================+===============+=========+
| Layer (type)     | Output Shape  | Param # |
+==================+===============+=========+
| input_layer      | (None, 64, 123)|      0 |
| separable_conv1d | (None, 64, 32) | 103,352|
| gated_activation | (None, 64, 32) |      0 |
```

**یک باگ ریز که همین‌جا پیدا شد:** کراس جدولش را با کاراکترهای
box-drawing می‌کشد و فونت پیش‌فرض Pillow آنها را مربع خالی نشان می‌داد.
به ASCII تبدیل شد.

---

## تأیید

```
black ✅  ruff ✅  mypy (295 files) ✅
pytest 1441 passed, 12 skipped   (قبلاً 1419)
```
**۲۲ تست جدید.**

تست زندهٔ داشبورد: هر چهار دکمه رندر شدند و
`inspect_dataset` از طریق HTTP اجرا و درست جواب داد.

---

## بدهی صریح

- **ارزیابی سیگنال، آستانه را از رکورد مدل نمی‌خواند.** فعلاً ۰.۰۸٪ ثابت
  فرض می‌شود. اگر مدلی با ۰.۱۵٪ آموزش دیده باشد، لیبل‌های ارزیابی با
  لیبل‌های آموزش فرق می‌کنند و دقت کمتر از واقع گزارش می‌شود. باید
  `threshold` در `ModelRecord` ذخیره شود (بدهی فاز ۴۵ هم بود).
- **`max_windows=5000` نمونه‌برداری می‌کند نه کل دیتاست.** در نتیجه ثبت
  می‌شود (`sampled every N windows`) ولی عدد یک تخمین است.
- **PNG در سندباکس از مسیر Pillow آمد، نه graphviz.** روی ویندوز اگر
  `pip install graphviz pydot` بزنی، نقشهٔ گرافیکی واقعی می‌گیری.
