# فاز ۲۹ — دو مدل پیش‌بینی — گزارش

> **به‌روزرسانی:** در نسخهٔ فعلی، مدل Signal به‌صورت binary بازطراحی شده و فقط `SELL` و `BUY` را پیش‌بینی می‌کند. بخش‌های قدیمی این گزارش که از کلاس `HOLD` سه‌گانه صحبت می‌کنند، تاریخچهٔ نسخهٔ قبلی هستند؛ عدم معاملهٔ فعلی در لایهٔ strategy/risk gate اتفاق می‌افتد، نه در خروجی مدل.

**درخواست تو:** مدلی که high و low تا ۵ کندل آینده را پیش‌بینی کند، و مدلی که
سیگنال را با درصد احتمال بدهد. هر دو roll-forward، با همهٔ فیچرها.
رنج روی ۱H، سیگنال روی ۵M.

**نتیجه:** ✅ هر دو ساخته و تست شدند.

---

## ۱. اول بررسی کردم — کد این قابلیت را **نداشت**

| نیاز تو | وضعیت قبل از فاز ۲۹ |
|---|---|
| پیش‌بینی high/low | ❌ **غیرممکن بود.** `_build_compiled` فقط `SparseCategoricalCrossentropy` را هاردکد کرده بود. هیچ مسیر رگرسیونی وجود نداشت. |
| سیگنال با درصد احتمال | ⚠️ **نیمه.** شبکه softmax می‌داد ولی `WavenetPredictor.predict` آن را به یک `float` فشرده می‌کرد و بقیهٔ بردار دور ریخته می‌شد. |
| استفاده از ۱۰۹ فیچر | ❌ **نبود.** `build_direction_series` فقط **۴** فیچر دستی می‌ساخت. کاتالوگ فاز ۱۲ هرگز به AI وصل نشده بود. |
| تایم‌فریم جدا برای هر مدل | ❌ مفهومش وجود نداشت. |
| roll-forward | ✅ بود و درست — بدون تغییر استفاده شد. |

پس این یک فاز جدید واقعی بود، نه یک تنظیم. `docs/Phases/Phase29.md` نوشته شد.

---

## ۲. چطور اجرا کنی

```powershell
# هر دو مدل، سریع (فقط OHLCV)
python scripts\run_dual_models.py

# با کل ۱۰۹ فیچر
python scripts\run_dual_models.py --with-features

# فقط یکی
python scripts\run_dual_models.py --model range  --with-features
python scripts\run_dual_models.py --model signal --with-features --epochs 3

# تنظیم افق و باند خنثی
python scripts\run_dual_models.py --horizon 10 --threshold 0.0015
```

---

## ۳. خروجی واقعی (اجرا شده، نه ادعا)

### مدل رنج — ۱H، ۵ کندل جلوتر

```
candles loaded : 600
usable rows    : 497
feature columns: 115        ← ۶ خام + ۱۰۹ کاتالوگ
dropped warmup : 51
fold losses    : [0.105008]

PREDICTION for the next 5 1H candles:
  current close  : 1990.69
  highest high   : 2001.80 (+0.558%)
  lowest low     : 1990.36 (-0.016%)
  reward / risk  : 33.93
```

### مدل سیگنال — ۵M، ۵ کندل جلوتر

```
usable rows    : 197
feature columns: 115
label balance  : {'sell': 61, 'hold': 170, 'buy': 64}

PREDICTION for the next 5 5M candles:
  sell :  33.6%
  hold :  34.1%
  buy  :  32.3%
  -> hold 34.1%
  actionable (>=60%): False
```

> این دقیقاً همان «۹۰ درصد احتمال خرید» است که خواستی — فقط روی دیتای
> **تصادفی** نمونه، مدل صادقانه می‌گوید نمی‌داند. روی دیتای واقعی معنا پیدا می‌کند.

---

## ۴. سه تصمیم طراحی که مهم‌اند

### ۴.۱ هدف‌ها نسبت به close، نه قیمت مطلق

```
high_offset = (future_high - close) / close
```

**چرا:** طلا در ۲۰۰۰ و طلا در ۳۰۰۰ نباید دو مسئلهٔ جدا باشند. مدلی که روی
قیمت مطلق آموزش ببیند، لحظه‌ای که بازار از بازهٔ آموزشش خارج شود **بی‌صدا**
از کار می‌افتد. نسبت ایستا (stationary) است؛ قیمت نیست.

همین قانون روی فیچرها هم اعمال شد: میانگین‌های متحرک و باندها به نسبت تبدیل
می‌شوند، ولی RSI و استوکاستیک که خودشان کران‌دار هستند دست‌نخورده می‌مانند.

### ۴.۲ کلاس HOLD — سه‌کلاسه به‌جای دوکلاسه

مدل دوکلاسه **مجبور** است هر کندل یک طرف را بگیرد، حتی وقتی هیچ اتفاقی
نمی‌افتد. بیشتر کندل‌ها نویزند.

باند خنثی (پیش‌فرض ۸ واحد پایه) هر حرکت کوچک‌تر را HOLD برچسب می‌زند.
**باید از هزینهٔ رفت‌وبرگشت بیشتر باشد**، وگرنه مدل را آموزش می‌دهی حرکاتی را
شکار کند که بعد از اسپرد و کمیسیون قابل گرفتن نیستند.

سیستم هم اگر یک کلاس تقریباً غایب باشد هشدار می‌دهد (`is_degenerate`) — چون
مدلی که ۹۹٪ HOLD ببیند یاد می‌گیرد همیشه HOLD بگوید و نمرهٔ خوبی هم می‌گیرد.

### ۴.۳ `is_coherent` به‌جای تعمیر بی‌صدا

اگر مدل سقف را **زیر** کف پیش‌بینی کند (که با آموزش کم اتفاق می‌افتد)، سیستم
گزارشش می‌کند:

```
[!] The model put its high BELOW its low. With this little training
    that is expected; it is reported, not hidden.
```

جابه‌جا کردن بی‌صدای دو عدد، یک مدل خراب را پنهان می‌کند.

---

## ۵. محافظت از نشت داده (سه قانون)

هر دو هدف ذاتاً به آینده نگاه می‌کنند — دقیقاً جایی که پروژه‌های سری‌زمانی
نشت می‌کنند. هر قانون تست اختصاصی دارد:

| قانون | تضمین | تست |
|---|---|---|
| **R1** | برچسب سطر `t` فقط از کندل‌های `t+1..t+N` می‌آید | کندل ۰ با high=999 گذاشتم؛ در برچسب خودش ظاهر نشد ✅ |
| **R2** | N سطر آخر که پنجرهٔ آینده‌شان ناقص است **حذف** می‌شوند | ۲۰ کندل، افق ۵ → دقیقاً ۱۵ برچسب ✅ |
| **R3** | ستون‌های هدف از ورودی مدل حذف می‌شوند | عرض پنجره = تعداد فیچر، بدون هدف ✅ |

R2 همان اشتباهی است که بک‌تست را عالی و حساب واقعی را بازنده نشان می‌دهد.

---

## ۶. 🐞 باگ #۱۵ — آموزش بازتولیدپذیر نبود

حین تست idempotency پیدا شد: دو اجرای **کاملاً یکسان** پیش‌بینی متفاوت داد.

```
run 1: highest high 2007.65 (+0.852%)
run 2: highest high 2004.04 (+0.671%)   ← نباید فرق کند
```

**علت:** `_build_compiled` پارامتر `seed` می‌گرفت و **هرگز استفاده‌اش نمی‌کرد**.
در Keras 3 هر لایه وزن اولیه‌اش را از مولد تصادفی خودش می‌گیرد، پس
`tf.random.set_seed` به‌تنهایی کافی نیست.

**این نقض مستقیم فاز ۱۳ §۳۴** بود که بازتولیدپذیری را الزام می‌کند.

**رفع:** `keras.utils.set_random_seed(seed)` که پایتون، NumPy و بک‌اند را با هم
seed می‌کند.

```
run 1: fold losses [0.117292] -> high 1988.97  lowest low 1975.54
run 2: fold losses [0.117292] -> high 1988.97  lowest low 1975.54   ✅
```

دو تست رگرسیون اضافه شد.

---

## ۷. کیفیت

```
black --check .                   ✅
ruff check .                      All checks passed ✅
mypy src --python-version 3.12    no issues in 259 files ✅
pytest                            759 passed, 12 skipped ✅   (قبلاً 697)
RUN_TF=1 pytest                   771 passed ✅              (قبلاً 703)
```

**۶۸ تست جدید:**
- ۲۱ — هدف‌ها و forecast ها
- ۱۷ — برچسب‌گذاری آینده (شامل ۳ تست نشت داده)
- ۱۱ — ماتریس فیچر و اتصال برچسب
- ۱۹ — یکپارچه با TensorFlow واقعی (شامل ۲ بازتولیدپذیری)

---

## ۸. فایل‌ها

**جدید**
```
docs/Phases/Phase29.md                                  ← معماری فاز
src/ShadBotTrader/domain/ai/prediction_target.py
src/ShadBotTrader/infrastructure/ai/target_builder.py
src/ShadBotTrader/infrastructure/ai/feature_matrix.py
src/ShadBotTrader/infrastructure/ai/model_roles.py
src/ShadBotTrader/infrastructure/ai/dual_predictor.py
src/ShadBotTrader/application/services/dual_model_service.py
scripts/run_dual_models.py
tests/unit/ai/test_prediction_target.py
tests/unit/ai/test_target_builder.py
tests/unit/ai/test_feature_matrix.py
tests/integration/test_dual_models.py
PHASE29_REPORT.md
```

**ویرایش‌شده (افزایشی — رفتار قبلی دست‌نخورده)**
```
infrastructure/ai/wavenet/wavenet_trainer.py   task-aware loss + seed fix
infrastructure/ai/data_windowing.py            پنجره‌بندی چندهدفه
project/builders/snapshot_builder.py
docs/IMPLEMENTATION_STATUS.md
docs/WORKLOG.md
```

معماری منجمد رعایت شد: هیچ پورت، موجودیت یا جهت وابستگی موجودی تغییر نکرد.
مدل جهت قبلی دقیقاً مثل قبل کار می‌کند (تست‌هایش سبزند).

---

## ۹. صادقانه: چه چیزی هنوز نیست

- **مدل‌ها هنوز به بک‌تست وصل نیستند.** `BacktestEngine` همچنان
  `MomentumPredictionSource` را می‌خواند. قدم بعدی یک `ModelPredictionSource` است.
- **روی دیتای واقعی آموزش ندیده‌اند** — منتظر MT5 تو.
- **هایپرپارامترها تنظیم نشده‌اند.** جست‌وجو کار فاز ۱۷ است.
- **سودآوری تضمین نشده.** دو مدلی که خواستی، صادقانه ساخته شدند. اینکه بازار
  در این افق‌ها قابل پیش‌بینی هست یا نه، سؤالی تجربی است که بک‌تست جواب می‌دهد.
