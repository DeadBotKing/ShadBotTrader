# فاز ۴۰ — منوهای کرکره‌ای، و مدل‌هایی که واقعاً ذخیره می‌شوند

**تاریخ:** 2026-08-17
**وضعیت:** ✅ کامل — Quality Gate سبز

---

## ۰. باگی که درخواست چهارم لو داد

قبل از هر چیز، مهم‌ترین چیزی که این فاز پیدا کرد:

> **`run_dual_models.py` هیچ‌وقت مدل را ذخیره نمی‌کرد.**

شبکه را آموزش می‌داد، یک پیش‌بینی چاپ می‌کرد، و خارج می‌شد. هیچ چیزی به
`datasets/models/` نمی‌رسید:

```
$ ls datasets/models
ls: cannot access 'datasets/models': No such file or directory
$ find . -name "*.bin"
(هیچی)
```

یعنی **هر اجرای آموزشی از فاز ۲۹ تا الان، لحظهٔ خروج پروسه دور ریخته
می‌شد.** آن مدل رنج روزانه که دیروز روی دیتای واقعی آموزش دادیم و
`val_mae 0.0164` گرفت؟ وجود ندارد. فقط عددش در گزارش ماند.

این را وقتی فهمیدم که خواستی «Retrain» از لیست مدل‌های ذخیره‌شده انتخاب
کند — لیست همیشه خالی می‌ماند، چون چیزی ذخیره نمی‌شد.

---

## ۱. منوی کرکره‌ای نوع مدل

`CommandField` حالا `kind="select"` با `options` دارد و رندرر آن را
`<select>` واقعی می‌سازد:

```
Model type  →  [all] [range ✓] [signal]
```

- **range** = پیش‌بینی high و low آینده
- **signal** = پیش‌بینی خرید/فروش/نگه‌داشتن

## ۲. حذف دو پارامتر اضافه

`Signal dataset` و `Range dataset(s)` حذف شدند. یک تست جلوی برگشتشان را
می‌گیرد:

```python
assert "range_timeframes" not in names
assert "signal_timeframe" not in names
```

## ۳. یک منوی کرکره‌ای برای دیتاست

فقط دیتاست‌هایی که **واقعاً روی دیسک هستند** نمایش داده می‌شوند:

```
Dataset  →  [5M ✓] [1H] [1D]
```

`stored_dataset_choices()` پوشهٔ `processed/` را می‌خواند. اگر تایم‌فریمی
دیتا نداشته باشد، در لیست نیست — پیشنهاد دادنش یعنی پیشنهاد یک شکست حتمی.

## ۴. ذخیرهٔ مدل با نقش و دیتاست

هر مدل حالا کنار خودش یک رکورد دارد:

```json
{
  "model_id": "gold_range_1d",
  "role": "range",
  "symbol": "TESTSYM",
  "timeframe": "1D",
  "version": 1,
  "rows": 497,
  "windows": 461,
  "feature_columns": 123,
  "metrics": { "val_mae": 0.002484, "val_loss": 0.0021 },
  "trained_at": "2026-08-17T14:49:21+00:00"
}
```

روی دیسک:
```
datasets/models/gold_range_1d/
    v1.bin              ← وزن‌های مدل (2.8 MB)
    v1.json             ← متادیتای artifact + checksum
    v1_training.json    ← نقش، دیتاست، کیفیت
```

## ۵. Retrain با لیست مدل‌های ذخیره‌شده

```
Saved model  →  [gold_range_1d ✓]
Dataset      →  [5M] [1H] [1D ✓]
```

سه رفتار که عمدی‌اند:

| حالت | رفتار |
|---|---|
| هیچ مدلی نیست | رد با پیام «اول Train a model را بزن» |
| مدل ناشناس | رد، با فهرست مدل‌های موجود |
| دیتاست متفاوت از آموزش اصلی | **اجازه هست**، ولی هشدار می‌دهد |

نقش مدل از رکوردش خوانده می‌شود، پس یک مدل range همیشه به‌عنوان range
دوباره آموزش می‌بیند — نه اینکه از اسم فایل حدس زده شود.

**نسخه‌گذاری:** هر آموزش مجدد یک نسخهٔ **جدید** می‌سازد و قبلی را نگه
می‌دارد:
```
v1_training.json  v2_training.json  v3_training.json
```
artifactها تغییرناپذیرند، پس تنها راه صادقانه برای نگه‌داشتن هر دو،
شماره‌گذاری جدید است (`ModelArtifact.with_version` — payload و checksum
دست‌نخورده).

---

## ۶. باگ دومی که سر راه پیدا شد

`train_model` روی کلاس `CommandHandlers` بود ولی `_run_script` فقط روی
`AccountCommandHandlers`. یعنی دکمهٔ Retrain لحظه‌ای که زده می‌شد
`AttributeError` می‌داد. حالا `AccountCommandHandlers` از
`CommandHandlers` **ارث می‌برد** — این کار تکرارشدن مشکل را غیرممکن
می‌کند، نه فقط رفعش.

---

## ۷. ورک‌اسپیس بدون دیتای واقعی

دیتای واقعی MT5 پاک شد. جایش `scripts/make_test_data.py`:

```
=== synthetic test data (NOT market data) ===
symbol TESTSYM | 600 candles per timeframe
   5M: 600 stored     1H: 600 stored     1D: 600 stored
   5M: 109/109 features   1H: 109/109   1D: 109/109
```

دو محافظ:
1. نماد `TESTSYM` است — نه XAUUSD و نه هیچ alias آن. تست ثابت می‌کند
   `TESTSYM` در `alias_candidates("XAUUSD", profile)` نیست.
2. فقط ۶۰۰ کندل. کسی ۶۰۰ کندل را با ۹ سال طلا اشتباه نمی‌گیرد.

**دیتا در zip نیست:**
```
data files in zip: 0
```

⚠️ دیتای واقعی تو روی گیت‌هاب امن است (`3b10dca 1D Features`). من فقط
کپی محلی را پاک کردم.

---

## ۸. تأیید

```
black --check .                 ✅
ruff check .                    ✅
mypy src --python-version 3.12  ✅ 293 files
pytest                          ✅ 1330 passed, 12 skipped   (قبلاً 1300)
RUN_TF=1                        ✅ 278 + 472 + 592
```
**۳۰ تست جدید.** سه تست قدیمی با نام‌های جدید تطبیق داده شدند.

### تست زنده

```
<select name="saved_model"> [gold_range_1d selected]
<select name="dataset">     [5M selected] [1H] [1D]
<select name="model">       [all] [range selected] [signal]
```

آموزش روی دیتای مصنوعی → `SAVED gold_range_1d v1` → Retrain از داشبورد →
`v3`، با `v1` و `v2` دست‌نخورده.

---

## ۹. آنچه هنوز باز است

- **`all` هنوز مدل سیگنال را روی 5M آموزش می‌دهد**، حتی اگر دیتاست دیگری
  انتخاب کنی. عمدی است: یک مدل سیگنال روی کندل روزانه محصول دیگری است نه
  یک تنظیم، و بی‌صدا عوض‌کردنش بدتر از محدودکردنش بود. اگر می‌خواهی
  سیگنال روی 1H آموزش ببیند، `Model type = signal` و `Dataset = 1H`.
- **رکورد مدل نماد را ثبت می‌کند ولی `model_id` نمی‌کند.** یعنی آموزش
  `gold_range_1d` روی TESTSYM و بعد روی XAUUSD، دو نسخه از یک مدل
  می‌سازد نه دو مدل جدا. برای چند-نمادی شدن باید `model_id` نماد را هم
  بگیرد — بدهی ثبت‌شده.
- مدل‌های قدیمی‌تر از v1 در لیست نمی‌آیند؛ فقط آخرین نسخهٔ هر مدل انتخاب
  می‌شود. تاریخچه روی دیسک هست ولی از GUI قابل انتخاب نیست.
