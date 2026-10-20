# بک‌تست دومدلی، سیگنال → رنج → حد سود/ضرر

**وضعیت:** پیاده‌سازی شده

این سند رفتار جدید بک‌تست و شبیه‌سازی را از روی کد توضیح می‌دهد.

## جریان اجرا

برای هر کندل بسته‌شدهٔ ۵ دقیقه‌ای، به‌ترتیب زیر عمل می‌شود:

1. پنجرهٔ آخر مدل سیگنال از دیتای `5M` ساخته می‌شود. اندازهٔ پنجره به‌صورت پیش‌فرض از `vN_training.json` همان مدل خوانده می‌شود؛ بنابراین در artifact فعلی سیگنال `100` ردیف است.
2. مدل سیگنال فقط دو احتمال `sell / buy` را برمی‌گرداند.
3. اگر احتمال برندهٔ BUY یا SELL کمتر از آستانهٔ انتخابی باشد، هیچ معامله‌ای انجام نمی‌شود و مدل رنج صدا زده نمی‌شود. این عدم معامله یک **تصمیم استراتژی** است، نه کلاس HOLD در مدل.
4. فقط در صورت عبور از آستانه، پنجرهٔ مدل رنج از کندل‌های بسته‌شدهٔ `1H` ساخته می‌شود. در artifact فعلی مدل رنج پنجرهٔ `500` ردیفی دارد.
6. مدل رنج `predicted_high` و `predicted_low` را می‌دهد.
7. برای BUY:
   - `take_profit = predicted_high`
   - `stop_loss = predicted_low`
8. برای SELL:
   - `take_profit = predicted_low`
   - `stop_loss = predicted_high`
9. معامله در بک‌تست روی **بازشدن کندل ۵ دقیقه‌ای بعدی** اجرا می‌شود. اگر گپ باعث شود حدها دیگر در دو طرف ورود نباشند، معامله رد می‌شود؛ حدها بی‌صدا جابه‌جا نمی‌شوند.
10. پس از بازشدن معامله، سیگنال‌های بعدی نادیده گرفته می‌شوند؛ فقط TP/SL همان معامله فعال است.
11. هر کندل آینده با `high` و `low` بررسی می‌شود. وقتی یک سطح لمس شد، خروج ثبت و PnL بر اساس همان سطح محاسبه می‌شود. کارمزد و slippage، اگر برای شبیه‌سازی تنظیم شده باشند، جداگانه روی fill اعمال می‌شوند.
12. اگر confidence یا range/risk gate رد شود، استراتژی یک تصمیم داخلی `HOLD/no_trade` ثبت می‌کند؛ این با خروجی مدل سیگنال فرق دارد، چون مدل فقط SELL/BUY دارد.

## برخورد هم‌زمان TP و SL

OHLC ترتیب حرکت داخل کندل را نشان نمی‌دهد. قانون پیش‌فرض محافظه‌کارانه است:

```text
same_bar_policy = stop_first
```

یعنی اگر `high` و `low` هر دو سطح را لمس کنند، حد ضرر اول در نظر گرفته می‌شود. گزینه‌های قابل تنظیم:

- `stop_first`
- `target_first`
- `skip_ambiguous`

## جلوگیری از نگاه‌به‌آینده

- منبع مدل فقط کندل‌هایی را می‌بیند که موتور شبیه‌سازی قبلاً تحویل داده است.
- مدل رنج فقط کندل `1H` را می‌بیند که زمان بسته‌شدنش از زمان تصمیم ۵ دقیقه‌ای گذشته باشد.
- پنجرهٔ کوتاه padding نمی‌شود؛ تا زمانی که تعداد ردیف usable کامل نباشد، مدل abstain می‌کند.
- برای سرعت، ماتریس feature هر تایم‌فریم یک‌بار روی سری تاریخی ساخته و در هر گام فقط slice می‌شود؛ این کار مدل را به آیندهٔ event جاری دسترسی نمی‌دهد و از recompute هزاران‌باره جلوگیری می‌کند.

## ساخت دیتاست و پنجرهٔ آموزش Signal

در بخش `Train a model` کاربر `Window rows` و `Signal movement threshold %` را وارد می‌کند. برای هر کندل شروع:

- BUY barrier = `close[start] * (1 + threshold)`
- SELL barrier = `close[start] * (1 - threshold)`
- آینده تا اولین برخورد هر barrier جست‌وجو می‌شود؛ تعداد کندل‌های رسیدن (`bars_to_hit`) متغیر است.
- برای BUY، قبل از برخورد هدف، اگر Low هر کندل آینده از Low کندل شروع پایین‌تر شود، آن شروع BUY معتبر نیست. برای SELL برعکس است: High بالاتر از High کندل شروع، SELL را invalid می‌کند.
- اگر هیچ barrier تا انتهای دیتاست لمس نشود، آن شروع label نمی‌گیرد و حذف می‌شود.
- ورودی مدل همیشه پنجرهٔ ثابتی است که کاربر تعیین کرده و با کندل سیگنال تمام می‌شود؛ کندل‌های قبل از همان سیگنال داخل پنجره هستند. تعداد کندل‌های تا برخورد، طول ورودی شبکه را تغییر نمی‌دهد.
- در هیچ مرحله‌ای کلاس HOLD ساخته نمی‌شود.

## مدل‌ها و متادیتا

مسیرهای پیش‌فرض:

```text
datasets/models/gold_signal_5m/v1.bin
datasets/models/gold_signal_5m/v1_training.json
datasets/models/gold_range_1h/v1.bin
datasets/models/gold_range_1h/v1_training.json
```

`window_size` و `horizon` از training record خوانده می‌شوند. Signal threshold در بخش Train a model، آستانهٔ حرکت قیمت برای اولین برخورد آینده است؛ مثلاً `0.15%` یعنی اولین Close که `+0.15%` برسد BUY و اولین Close که `-0.15%` برسد SELL. جست‌وجو تا هر تعداد کندل آینده ادامه دارد. آستانهٔ بک‌تست جداست و احتمال ورود، مثلاً `60%`، را کنترل می‌کند.

## اجرا

### CLI اصلی

```bash
# حالت dual صریح
python -m ShadBotTrader.backtest_cli dual \
  --symbol XAUUSD \
  --signal-timeframe 5M \
  --range-timeframe 1H \
  --threshold 0.60 \
  --same-bar stop_first
```

یا:

```bash
python scripts/run_backtest.py --symbol XAUUSD --mode dual --threshold 0.60
# روی داده‌ای که با MT5 ذخیره شده:
python scripts/run_real_data.py --symbol XAUUSD --mode auto --skip-ingest --skip-optimise
```

`run_backtest.py --mode auto` حالت پیش‌فرض است: اگر هر دو دیتاست و هر دو مدل موجود باشند، مسیر دومدلی را اجرا می‌کند؛ اگر پروژه فقط دیتای demo تک‌تایم‌فریمی داشته باشد، با پیام واضح به baseline قدیمی برمی‌گردد تا اجرای قدیمی بی‌دلیل نشکند. `--mode dual` در نبود پیش‌نیازها خطا می‌دهد و fallback نمی‌کند.

### داشبورد

در `Run a backtest` یا `Record a replay`:

- `Engine = auto` یا `dual`
- `Signal probability % = 60`
- `Range timeframe = 1H`
- `Signal window` و `Range window` با مقدار `0` یعنی «از training metadata بخوان»
- در گروه AI دکمهٔ `Find best learning rate` چند مقدار را روی pilot walk-forward تست می‌کند، کمترین `val_loss` برای Signal یا `val_mae` برای Range را انتخاب می‌کند و سپس مدل نهایی را با همان مقدار آموزش و ذخیره می‌کند.
- قانون کندل مبهم به‌صورت پیش‌فرض `stop_first` است

وقتی حالت dual اجرا شود، خروجی تعداد `take profits` و `stop losses` را نیز گزارش می‌کند.

برای یکسان‌بودن نتیجه، `Record a replay` به‌صورت پیش‌فرض تنظیمات آخرین `Run a backtest` را دوباره استفاده می‌کند. اگر گزینهٔ `Use last backtest settings` را روی `0` بگذاری، Replay با تنظیمات فرم خودش اجرا می‌شود و ممکن است نتیجهٔ متفاوتی داشته باشد.

## اجزای کد

```text
src/ShadBotTrader/domain/simulation/bracket.py
    TradeBracket و قانون برخورد TP/SL

src/ShadBotTrader/infrastructure/simulation/dual_model_prediction_source.py
    پنجره‌بندی causal، signal-first و forecast مدل رنج

src/ShadBotTrader/application/services/dual_model_backtest_service.py
    بارگذاری artifact/metadata و composition root

src/ShadBotTrader/infrastructure/simulation/backtest_engine.py
    next-open entry، pending entry، bracket exit و حساب‌کردن fill

src/ShadBotTrader/infrastructure/trading/bracket_exit_strategy.py
    بستن bracket از مسیر عادی strategy → decision → risk → intent → execution
```

حسابداری همچنان fill-based است و از همان `PortfolioLedger`، `ExecutionService` و `SimulatedExecutionVenue` مسیر قبلی استفاده می‌کند.
