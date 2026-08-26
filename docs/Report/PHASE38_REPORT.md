# فاز ۳۸ — کش ویژگی‌ها، و پاسخ به «چه ماتریسی به مدل می‌دهی؟»

**تاریخ:** 2026-08-17
**وضعیت:** ✅ کامل — Quality Gate سبز

---

## ۱. اول جواب سؤال عصبانی‌ات، با عدد

> «حتما از ویژگی ها توی دیتایی که قراره بدیم ب مدل برای آموزش استفاده چرا تا
> الان استفاده نکردی پس؟ قبلا گفته بودم که!!!! پس الان چ ماترسیو داری برای
> آموزش ب مدل میدی؟؟؟؟؟»

**۱۰۹ ویژگی کاتالوگ از فاز ۲۹ در ماتریس آموزش هستند.** اندازه‌گیری زنده:

```
matrix given to the model: 297 rows x 123 cols
  candle-derived columns : 14
  CATALOGUE features     : 109
  sample catalogue cols  : ['open_filter', 'close_filter', 'low_filter', ...]
  ...  ['volume_return_1', 'open_target_m1', 'open_target_p1'] ...
       ['rsi_sell_secondry', 'rsi_sell_primary', 'rsi_buy_secondry']
```

`۱۲۳ = ۱۴ + ۱۰۹`. دکمهٔ `Train both models` هم `--with-features` را پاس
می‌دهد، پس مسیر GUI همیشه نسخهٔ ۱۲۳ ستونی است.

**پس چرا این سوءتفاهم پیش آمد؟ تقصیر من بود.** در گزارش فاز ۳۷ نوشتم:

> «ویژگی‌های ذخیره‌شده هنوز توسط هیچ‌کس خوانده نمی‌شوند»

این جمله **درست ولی گمراه‌کننده** بود. منظورم *فایل‌های پارکت روی دیسک* بود،
نه خود ویژگی‌ها. واقعیت دقیق:

| | وضعیت |
|---|---|
| ویژگی‌ها در ماتریس آموزش | ✅ بله، ۱۰۹ تا، از فاز ۲۹ |
| ویژگی‌ها از **فایل پارکت** خوانده می‌شدند | ❌ نه — هر بار در حافظه از نو حساب می‌شدند |

یعنی مدل همیشه ویژگی‌ها را می‌گرفت؛ فقط دوباره‌کاری می‌شد. جملهٔ من این دو
را قاطی کرد و طبیعی بود که فکر کنی مدل بدون ویژگی آموزش می‌بیند. عذر
می‌خواهم — باید می‌نوشتم «انبار پارکت مصرف‌کننده ندارد، ولی ماتریس آموزش
۱۲۳ ستونه است».

حالا این ادعا **تست دارد** تا دیگر نه من بتوانم مبهم بنویسم، نه کد بتواند
بی‌صدا به حالت ۱۴ ستونی برگردد:

```python
def test_the_matrix_carries_all_109_catalogue_features()
def test_named_indicators_are_present_by_name()        # atr_14, rsi_14, macd_12_26_9, ...
def test_the_prepared_training_dataset_is_123_columns_wide()
def test_without_the_catalogue_it_is_only_14_columns()  # تفاوت را پین می‌کند
def test_the_gui_training_button_asks_for_the_catalogue()
```

و خروجی `Build training dataset` حالا صریح می‌گوید:

```
columns = 14 candle-derived + 109 catalogue features
```

---

## ۲. قاعدهٔ کش — دقیقاً همان که گفتی

> «تا زمانی که دیتاست آپدیت نشده نیازی نیس دوباره ویژگی ها حساب بشن از انبار
> خونده بشن، ولی زمانی که دیتاست آپدیت شدش باید ویژگی ها هم از اول حساب بشن
> و دوباره ذخیره بشن»

هر دو نیمه پیاده شد. نیمهٔ دوم مهم‌تر است: **از اول**، نه append.

**چرا append ممنوع است:** EMA، MACD، ATR بازگشتی‌اند و حالت را از کندل اول
حمل می‌کنند. مقدار محاسبه‌شده روی ۱۰۰٬۰۰۰ کندل با مقداری که از کندل ۹۹٬۰۰۰
ادامه بدهی **یکی نیست** — تفاوتش نامرئی است و هیچ تستی نمی‌گیردش. پس سری
تغییرکرده = محاسبهٔ کامل.

### تشخیص تغییر با اثر انگشت، نه تاریخ فایل

تاریخ تغییر فایل دروغ می‌گوید (بازنویسی با محتوای یکسان، یا ویرایش درجا).
`FeatureFingerprint` این‌ها را پوشش می‌دهد:

- تعداد کندل‌ها، اولین و آخرین زمان
- **digest همهٔ مقادیر OHLCV** (نه فقط تعداد)
- نام و نسخهٔ feature set
- فهرست شناسهٔ ۱۰۹ ویژگی

اگر هرکدام فرق کند → محاسبهٔ کامل. اگر همه یکی باشند → خواندن از انبار.

### اندازه‌گیری واقعی

```
1. first run (1000 candles)        reused=  0/109  1.54s
2. same candles again              reused=109/109  0.53s   ← کش
3. same candles a third time       reused=109/109  0.52s   ← کش
4. AFTER dataset update (1100)     reused=  0/109  1.63s   ← محاسبهٔ کامل
5. same 1100 again                 reused=109/109  0.53s   ← کش

versions on disk: ['v1.parquet', 'v2.parquet']   ← فقط دو نسخه، نه پنج
```

اجرای تکراری **نسخهٔ جدید نمی‌نویسد** — انبار از نسخه‌های تکراری پر نمی‌شود.

### در داشبورد

```
RUN 1 (اولین بار):
  5M: 109/109 recomputed over 1,000 candles
  1H: 109/109 recomputed over 1,000 candles

RUN 2 (چیزی عوض نشده):
  5M: 109 feature(s) REUSED from the store — the dataset has not changed
  1H: 109 feature(s) REUSED from the store — the dataset has not changed

بعد از آپدیت دیتاست به ۱۲۰۰ کندل:
  5M: 109/109 recomputed over 1,200 candles
  1H: 109/109 recomputed over 1,200 candles
```

و در لاگ زنده **دلیلش** را می‌نویسد:

```
recompute : candle count changed: 1,000 -> 1,200 (the dataset was updated)
```

دلایل ممکن: تغییر تعداد کندل · تغییر مقادیر درجا · تغییر نسخهٔ feature set ·
تغییر کاتالوگ · اثر انگشت خراب (که همیشه به محاسبهٔ کامل منجر می‌شود، چون
نمی‌شود به دیتایی که نمی‌توانیم تأییدش کنیم اعتماد کرد).

دکمه یک فیلد `Force recompute` هم گرفت برای وقتی که می‌خواهی صرف‌نظر از
اثر انگشت، از نو حساب شود.

---

## ۳. فایل‌ها

### جدید
| فایل | نقش |
|---|---|
| `infrastructure/feature/feature_cache.py` | `FeatureFingerprint`، `FeatureCache`، `candles_digest` |
| `tests/integration/test_feature_cache.py` | ۲۱ تست (۶ اثر انگشت، ۸ قاعدهٔ کش، ۶ اثبات کاتالوگ) |

### تغییر کرده
| فایل | تغییر |
|---|---|
| `application/services/feature_computation_service.py` | پارامتر `force`، بررسی کش، `_result_from_cache`، `from_cache` و `reused_count` |
| `infrastructure/feature/feature_progress.py` | `on_cache_hit`، پارامتر `reason` در `on_set_begin` |
| `presentation/commands/handlers.py` | گزارش REUSED در برابر recomputed، فیلد `Force recompute` |
| `scripts/run_training_dataset.py` | چاپ `14 candle-derived + 109 catalogue features` |
| `tests/integration/test_feature_visibility.py` | یک تست فاز ۳۷ با قاعدهٔ جدید تطبیق داده شد |

---

## ۴. تأیید

```
black --check .                 ✅
ruff check .                    ✅
mypy src --python-version 3.12  ✅ 290 files
pytest                          ✅ 1267 passed, 13 skipped   (قبلاً 1247)
RUN_TF=1                        ✅ 278 + 410 + 592
```
**۲۱ تست جدید.**

یک تست ثابت می‌کند مقادیر کش‌شده **دقیقاً** با محاسبهٔ مجدد یکی‌اند — کشی
که عدد متفاوت برگرداند بدتر از نبودن کش است.

---

## ۵. آنچه هنوز باز است

- **ماتریس آموزش هنوز از انبار پارکت نمی‌خواند.** کش الان لایهٔ
  `FeatureComputationService` را پوشش می‌دهد (دکمهٔ Update features)، ولی
  `build_feature_matrix` که ماتریس مدل را می‌سازد همچنان مستقل و در حافظه
  حساب می‌کند. یعنی `Build training dataset` هنوز ~۲ دقیقه به ازای ۱۰۰k
  کندل می‌برد حتی اگر ویژگی‌ها تازه محاسبه شده باشند.

  **چرا این بار وصلش نکردم:** ماتریس مدل ویژگی‌ها را نسبت به close همان
  سطر نرمال می‌کند (`is_price_scaled`)، ولی انبار مقدار خام را دارد.
  وصل‌کردن یعنی انتقال منطق نرمال‌سازی، و اگر اشتباه شود مدل روی مقیاس
  اشتباه آموزش می‌بیند — بی‌صدا. این کار یک فاز مستقل با تست تطابق
  بیت‌به‌بیت می‌خواهد، نه یک وصلهٔ عجله‌ای در انتهای این فاز.

  اگر بگویی، فاز بعد همین را می‌زنم: خواندن از انبار + تستی که ثابت کند
  ماتریسِ خوانده‌شده با ماتریسِ محاسبه‌شده **بایت‌به‌بایت** یکی است.
- کش با `dataset_version` کاری ندارد؛ فقط به محتوای کندل‌ها نگاه می‌کند.
  عمدی است: نسخه می‌تواند بالا برود بدون آنکه عددی عوض شود.
