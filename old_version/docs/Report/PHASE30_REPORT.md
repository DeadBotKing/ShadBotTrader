# فاز ۳۰ — دیتاست آموزش و بافر زندهٔ بازار — گزارش

**درخواست تو:** دیتاست ۱۰۰٬۰۰۰ کندلی با فیچرهای ذخیره‌شده، پنجرهٔ ۵۰۰×۱۲۳،
roll-forward با گام یک کندل، آپدیت هفتگی، بافر زندهٔ ۸۰۰ کندلی، بک‌تست روی
همان دیتاست.

**نتیجه:** ✅ ساخته و تست شد. `docs/Phases/Phase30.md`

---

## ۱. ۱۲۳ ستون — حق با تو بود

بررسی نشان داد **قیمت خام واقعاً در ورودی مدل نبود**. کاتالوگ فقط
`high_filter`, `close_filter` و… داشت که قیمت **هموارشده با موجک** است، نه
قیمت واقعی بازار.

| گروه | تعداد | ستون‌ها |
|---|---|---|
| **قیمت خام (جدید)** | **۸** | `open_rel`, `high_rel`, `low_rel`, `close_rel`, `hl2_rel`, `hlc3_rel`, `ohlc4_rel`, `volume_raw_log` |
| مشتق از کندل | ۶ | `return_1`, `range_pct`, `body_pct`, دو wick, `volume_log` |
| کاتالوگ فاز ۱۲ | ۱۰۹ | RSI, MACD, بولینگر, … |
| **جمع** | **۱۲۳** | |

قیمت‌های خام نسبت به close داده می‌شوند (`high/close - 1`) به همان دلیل فاز
۲۹: طلا در ۲۰۰۰ و ۳۰۰۰ نباید دو مسئله باشد. اطلاعات کاملاً حفظ می‌شود.

`close_rel` همیشه صفر است — عمداً نگهش داشتم تا مجموعهٔ ستون‌ها صریح و
پایدار بماند، نه اینکه بی‌صدا یکی کم باشد.

---

## ۲. مهم‌ترین عدد این فاز: ۲۴.۵ گیگابایت

```
۹۹٬۴۹۶ پنجره × ۵۰۰ ردیف × ۱۲۳ ستون × ۴ بایت = ۲۴.۵ GB
ماتریس تختی که همه از آن می‌آید            = ۵۰ MB
```

پنجره‌های متوالی ۴۹۹ ردیف (۹۹.۸٪) همپوشانی دارند. اگر مثل کد قبلی یک
`list` بسازیم، هیچ کامپیوتری اجرایش نمی‌کند.

**راه‌حل:** پنجره‌ها **لحظه‌ای** ساخته می‌شوند، دسته‌به‌دسته. فقط آن ۵۰
مگابایت در حافظه می‌ماند. این بهینه‌سازی نیست — تفاوت بین «کار می‌کند» و
«کار نمی‌کند» است.

```
generator: 99,496 windows of (500 x 123), stride 1
           lazy 50 MB vs materialised 24.5 GB
```

roll-forward دقیقاً همان‌طور که خواستی، گام یک کندل:
```
پنجرهٔ ۰: ردیف   ۰ .. ۴۹۹  → برچسب در ۴۹۹+افق
پنجرهٔ ۱: ردیف   ۱ .. ۵۰۰  → برچسب در ۵۰۰+افق
پنجرهٔ ۲: ردیف   ۲ .. ۵۰۱
```

---

## ۳. چطور اجرا کنی

```powershell
# ساخت دیتاست ۱۰۰k (هر دو تایم‌فریم)
python scripts\run_training_dataset.py --build --candles 100000

# دیدن وضعیت
python scripts\run_training_dataset.py --status

# آپدیت هفتگی — فقط اگر یک هفته گذشته باشد
python scripts\run_training_dataset.py --refresh --if-due

# نمایش بافر زنده
python scripts\run_training_dataset.py --live-demo
```

خروجی واقعی (۶٬۰۰۰ کندل برای سرعت؛ ۱۰۰k همین رفتار را دارد):
```
BUILD — 6,000 candles per timeframe        done in 15.0s
  5M: 6,000 candles -> 5,897 rows x 123 cols
      stride-1 windows of (500 x 123): 5,393
  1H: 6,000 candles -> 5,897 rows x 123 cols
```

و مدل‌ها:
```
 range: feature_count=123  input_shape=(500, 123)
signal: feature_count=123  input_shape=(500, 123)
        batch X=(4, 500, 123)
```

---

## ۴. آپدیت هفتگی — محاسبهٔ مجدد کامل

تو گفتی «فیچرها از اول حساب بشن که یوقت محاسبات اشتباهی نشه». **کاملاً درست
است** و همان‌طور پیاده شد.

**چرا افزایشی خطرناک است:** EMA، MACD و ATR بازگشتی‌اند — مقدارشان به
تاریخچهٔ خودشان وابسته است. اگر مقدار جدید را از تاریخچهٔ ناقص حساب کنیم،
سری به‌شکلی نامحسوس غلط می‌شود که هیچ تستی نمی‌گیرد. ۲ دقیقه برای ۱۰۰k
هزینهٔ ناچیزی است در برابر فیچرهای بی‌صدا خراب.

هر build یک **digest** ثبت می‌کند. دو build از همان کندل‌ها باید digest
یکسان بدهند — این «از اول حساب شد» را **قابل‌بررسی** می‌کند نه یک ادعا.

بعد از refresh، مدل‌ها **لود** می‌شوند و آموزش ادامه پیدا می‌کند (نه از صفر)،
و نسخهٔ قبلی هرگز بازنویسی نمی‌شود.

---

## ۵. بافر زنده — ۸۰۰ کندل خودنگهدار

هر ۵ دقیقه یک کندل ۵M و یک کندل ۱H. بافر خودش را نگه می‌دارد:

| رفتار | چرا |
|---|---|
| قدیمی‌ترین بیرون، جدید تو | همیشه دقیقاً ۸۰۰ تا |
| **timestamp تکراری → جایگزینی** | کندل ۱H جاری قبل از بسته‌شدن ۱۲ بار گرفته می‌شود؛ append کردن ۱۲ ساعت تاریخ **جعلی** می‌سازد |
| **کندل قدیمی ناشناخته → رد** | اختلال بروکر نباید ترتیب سری را خراب کند |
| **کمبود → اعلام، نه padding** | ورودی کوتاه یعنی مدل زباله می‌خواند |

```
5M: primed with 900 candles -> {'appended': 900, ...}
    buffer holds 800 (capacity 800)
    model input : 500 rows x 123 columns
```

**چرا ۸۰۰ و نه ۵۰۰:** warm-up فیچرها ۵۱ ردیف می‌خورد → ۷۴۹ سالم می‌ماند.
بافر این را در زمان اجرا **بررسی** می‌کند؛ اگر روزی فیچری با warm-up بلندتر
اضافه شود، پیام دقیق می‌دهد:

```
5M: 520 candles buffered, but feature warm-up consumes 51 and the model
needs 500 rows. Short by 31. Increase the buffer capacity to at least 551.
```

---

## ۶. 🐞 باگ #۱۶ — digest هرگز تطبیق نمی‌کرد

تست round-trip گرفتش. digest روی `float64` حساب می‌شد ولی ماتریس `float32`
ذخیره می‌شد، پس بعد از reload **همیشه** فرق می‌کرد — یعنی به‌عنوان بررسی
صحت کاملاً بی‌فایده بود.

دو بار اشتباه رفتم: گرد کردن به ۴ رقم، بعد ۶ رقم بامعنا. هیچ‌کدام جواب نداد.
بعد **اندازه‌گیری** کردم:

```
max RELATIVE error: 5.94e-08
  4 sig digits -> identical? False
  6 sig digits -> identical? False
  7 sig digits -> identical? False
```

خطا **نسبی** است، پس هر دقت ثابتی برای بعضی مقادیر روی مرز گرد کردن می‌افتد.
رفع درست: هش روی **شکل ذخیره‌شدهٔ float32** با `struct.pack("<f", …)` —
دقیقاً همان بایت‌هایی که روی دیسک می‌روند. حالا lossless است.

---

## ۷. بک‌تست روی دیتاست ۱۰۰k

موتور بک‌تست **از قبل** کندل ۰ تا آخر را یکی‌یکی طی می‌کند (فاز ۱۶)، پس
هیچ تغییری لازم نبود — فقط باید به دیتاست ۱۰۰k اشاره کند:

```powershell
python scripts\run_backtest.py --symbol XAUUSD_i
python scripts\run_replay.py --symbol XAUUSD_i --open   # با ریپلی زنده
```

---

## ۸. کیفیت

```
black --check .                   363 files ✅
ruff check .                      All checks passed ✅
mypy src --python-version 3.12    no issues in 264 files ✅
pytest                            819 passed, 12 skipped ✅  (قبلاً 759)
RUN_TF=1 pytest                   831 passed ✅             (قبلاً 771)
```

**۶۰ تست جدید:** ۲۱ ژنراتور پنجره · ۱۷ بافر زنده · ۲۱ یکپارچه دیتاست
به‌علاوهٔ ۲ تست فاز ۲۹ که به‌درستی شکستند (۶ ستون → ۱۴) و به‌روز شدند.

---

## ۹. فایل‌ها

**جدید**
```
docs/Phases/Phase30.md
src/ShadBotTrader/domain/dataset/training_dataset.py
src/ShadBotTrader/infrastructure/ai/window_generator.py
src/ShadBotTrader/infrastructure/ai/live_matrix.py
src/ShadBotTrader/infrastructure/data/live_buffer.py
src/ShadBotTrader/application/services/training_data_service.py
scripts/run_training_dataset.py
tests/unit/ai/test_window_generator.py
tests/unit/dataset/test_live_buffer.py
tests/integration/test_training_dataset.py
PHASE30_REPORT.md
```

**ویرایش‌شده**
```
infrastructure/ai/feature_matrix.py    + ۸ ستون قیمت خام (۱۲۳ کل)
tests/unit/ai/test_feature_matrix.py   به‌روزرسانی به ۱۴ ستون
project/builders/snapshot_builder.py
docs/IMPLEMENTATION_STATUS.md · docs/WORKLOG.md
```

معماری منجمد رعایت شد؛ جهت وابستگی تغییر نکرد.

---

## ۱۰. صادقانه: چه چیزی هنوز نیست

- **حلقهٔ ۵ دقیقه‌ای هنوز اجرا نمی‌شود.** بافر، ماتریس زنده و مدل‌ها آماده‌اند؛
  چیزی که وصلشان کند (سرویس تصمیم‌گیری + زمان‌بندی) هنوز ساخته نشده.
- **مدل‌ها هنوز به بک‌تست وصل نیستند** — `MomentumPredictionSource` هنوز
  پیش‌بینی‌کنندهٔ بک‌تست است.
- **۱۰۰k کندل واقعی وجود ندارد** — عمق تاریخچهٔ MT5 به بروکر بستگی دارد؛
  builder گزارش می‌دهد واقعاً چند تا گرفته، نه اینکه به عدد گرد برساند.
- **زمان‌بندی خودکار** به Task Scheduler وصل نشده (کار فاز ۲۴).
