# WORKLOG — دفترچهٔ کار

**هدف:** هر تغییر معنادار اینجا ثبت می‌شود تا اگر گفت‌وگو عوض شد، ایجنت دیگری
آمد، یا چند هفته بعد برگشتیم، بشود ادامه داد.

قاعدهٔ ثبت (طبق `AGENTOPERATINGRULE.md` § CHAT HANDOFF RULE): پروژه باید فقط
از روی «کد + گیت + مستندات وضعیت» قابل بازیابی باشد.

**فرمت هر ورودی:** تاریخ · چه شد · چرا · کجا · تست · وضعیت گیت

---

## 2026-08-16 — Backtest Replay (پخش زندهٔ کندل و معاملات)

**درخواست کاربر:** «اجرای بک تست رو میتونی یکاری کنی که به صورت لایو کندلا
نمایش داده بشن و نشون بده کجاها معامله کرده و نتیجه معامله چی بود؟»

**مجوز معماری:** فاز ۱۶ §۲۳ صراحتاً می‌گوید شبیه‌سازی باید step-by-step قابل
بازرسی باشد؛ فاز ۱۹ §۸ نقش View را «فقط رندر» تعریف می‌کند. پس این کار داخل
معماری منجمد است، نه تغییر آن.

### ساخته شد

| فایل | نقش |
|---|---|
| `domain/simulation/replay.py` | `TradeMarker`, `ReplayBar`, `ReplayTape`, `ReplayRecorder` |
| `infrastructure/simulation/console_replay.py` | `ConsoleReplayPlayer`, `summarise_tape` |
| `presentation/web/replay_renderer.py` | پخش‌کنندهٔ HTML مستقل (canvas + JS درون‌خطی) |
| `scripts/run_replay.py` | اسکریپت دمو |
| `tests/unit/simulation/test_replay.py` | ۱۲ تست |
| `tests/integration/test_backtest_replay.py` | ۱۶ تست |

### تغییر کرد

- `infrastructure/simulation/backtest_engine.py` — پارامتر `record_replay`، پراپرتی `tape`،
  و `_capture_trade` حالا `(realized_delta, fee_delta)` برمی‌گرداند
- `application/services/backtest_service.py` — عبور `record_replay`
- `backtest_cli.py` — دستور `replay`
- `presentation/commands/` — `CommandKind.RECORD_REPLAY` + هندلر
- `presentation/web/server.py` — مسیر `GET /replay`
- `presentation/web/renderer.py` — لینک ریپلی در هدر
- `dashboard_cli.py` — آپشن `--replay`
- `project/builders/{snapshot,context}_builder.py` — فاز جاری و فاز بعدی

### دو تصمیم طراحی که باید یادت بماند

1. **ورودِ باز نتیجه ندارد:** `realized_pnl` یک entry برابر `None` است نه صفر.
   صفر یعنی «سربه‌سر بست» که دروغ است.
2. **پوزیشن باز در پایان دیتا معامله شمرده نمی‌شود.** جدا با عنوان
   «Still open at the end» گزارش می‌شود.
3. **ضبط، ناظر منفعل است:** پیش‌فرض خاموش تا sweep هزینه ندهد. تستی هست که
   ثابت می‌کند نتیجهٔ اجرا با و بدون ضبط یکسان است.

### تأیید

- خروجی ریپلی دقیقاً با `run_backtest.py` یکی است: ۵۱ معامله، `-2.7946`
- هر دو اسکریپت دو بار اجرا شدند → خروجی بایت‌به‌بایت یکسان
- دکمهٔ داشبورد به‌صورت زنده تست شد (POST /run → ۳۰۰ بار ضبط شد)
- `672 passed, 6 skipped` · `RUN_TF=1 → 678 passed`

**گزارش کامل:** `REPLAY_REPORT.md`

---

## 2026-08-16 — ممیزی مستندات و ساخت اسناد وضعیت

**درخواست کاربر:** «طبق نقشه هم داریم پیش میریم دیگ؟ / فایلای docs رو یادت
نره ک همشوباید پیاده سازی کنیما / هرکاری هم ک میکنی توی docs ثبت کن»

**انجام شد:**
- خواندن `docs/AGENTOPERATINGRULE.md` (قبلاً در جریان کار خوانده نشده بود)
- ممیزی فاز ۱ تا ۲۸ در برابر کد واقعی
- ساخت `docs/IMPLEMENTATION_STATUS.md` — جدول وضعیت هر ۲۸ فاز
- ساخت `docs/WORKLOG.md` — همین فایل

**یافتهٔ مهم ممیزی:** ۲۲ فاز از ۲۸ کامل‌اند. سه فاز حداقلی‌اند (۹ Plugin،
۲۱ Config، ۲۲ Logging)، یکی صفر است (۲۴ Deployment)، یکی جزئی (۲۵ PowerShell)،
و فاز ۲۸ در حال انجام است. فاز ۲۰ با انحراف تأییدشده (SQLite) کامل است.

**نکتهٔ صادقانه:** `docs/PROJECT_STATE.md` و `docs/CURRENT_STATE.md` اسناد
اصلی و منجمد معماری‌اند و می‌گویند «هنوز چیزی پیاده نشده» — که دیگر درست
نیست. به‌جای دستکاری آنها (که خلاف قاعدهٔ freeze فاز ۲۶ است)،
`IMPLEMENTATION_STATUS.md` به‌عنوان لایهٔ وضعیت زنده اضافه شد و از هر دو به
آن ارجاع داده شد.

---

## 2026-08-16 — آماده‌سازی دیتای واقعی MT5 (گزینهٔ C)

**درخواست کاربر:** «باشه بریم» (تأیید قدم C).

### 🐞 باگ #۱۴ — دکمهٔ «Update features» داشبورد هرگز کار نمی‌کرد

**شدت: بالا.** حین تست مسیر واقعی کشف شد.

`presentation/commands/handlers.py::compute_features` این‌ها را صدا می‌زد:

| صدا زده می‌شد | واقعیت |
|---|---|
| `service.compute(symbol, timeframe)` | متد وجود ندارد → `compute_set(...)` |
| `outcome.results` | `outcome.outcomes` |
| `result.definition` | وجود ندارد؛ تعاریف از `feature_set.definitions` |
| `outcome.feature_set.name` | `outcome.set_name` |

**پیام خطای واقعی:**
```
FAILED: Feature computation failed
'FeatureComputationService' object has no attribute 'compute'
```

**چرا تست‌ها نگرفتند:** تست موجود فقط شاخهٔ «کندلی ذخیره نشده» را می‌آزمود که
*قبل* از رسیدن به کد خراب return می‌کند. کلاسیک‌ترین نوع نقطهٔ کور تست.

**رفع:** فراخوانی درست `compute_set(...)` با `standard_feature_set_v1()`.
حالا: `Computed 109 features over 300 candles`.

**تست رگرسیون:** ۳ تست در `TestComputeFeaturesCommand` — یکی‌شان
(`test_the_service_contract_the_handler_relies_on_exists`) دقیقاً همان عدم
تطابق امضا را قفل می‌کند.

**اقدام پیشگیرانه:** هر ۷ دکمهٔ داشبورد با دیتای واقعی اجرا شدند. نتیجه:
```
fetch_market_data   OK    compute_features   OK (رفع شد)
run_backtest        OK    record_replay      OK
run_optimisation    OK    run_trading_cycle  OK
refresh_project_state OK  train_model        SKIP (کند، نیاز TF)
```

### ✅ شکل واقعی بازار اعتبارسنجی شد

نگرانی اصلی: دیتای واقعی **گپ آخر هفته** دارد (بازار جمعه شب تا یکشنبه بسته
است). آیا pipeline آن را «دیتای خراب» تلقی و قرنطینه می‌کند؟

**پاسخ: نه.** با ۳ هفته دیتای ۵ دقیقه‌ای واقعی‌شکل (۴۳۲۰ کندل) آزمایش شد:
```
quarantined   : False
overall score : 99.99
issues        : [warning] GAP_DETECTED: 2 gap(s)
```
گپ گزارش می‌شود (درست) ولی باعث دور ریختن دیتا نمی‌شود (هم درست).

۴ تست جدید در `test_mt5_ingestion.py`: گپ آخر هفته، بک‌تست کامل روی سری
گپ‌دار (ترتیب زمانی equity curve حفظ می‌شود)، حفظ اسپرد متغیر rollover
(۱۰ و ۴۵)، و جهش قیمتی یکشنبه.

### ✅ حل‌کنندهٔ نام نماد — `mt5_symbol_resolver.py`

**چرا:** شایع‌ترین دلیل شکست اولین اجرای واقعی. بروکرها طلا را
`XAUUSD` / `XAUUSD.i` / `XAUUSDm` / `GOLD` / `GOLDmicro` صدا می‌زنند.

```
XAUUSD.i  → XAUUSD      GOLDmicro → XAUUSD (alias)
XAUUSDm   → XAUUSD      XAUUSD.pro.ecn → XAUUSD
USTEC     → USTEC (دست‌نخورده)   US30 → US30 (دست‌نخورده)
```

**دو محافظ مهم:**
1. `USTEC` به `UST` تبدیل نمی‌شود (پسوند `C` کورکورانه کنده نمی‌شود)
2. `GOLD` به `GOL` تبدیل نمی‌شود (`_PROTECTED`)
3. پسوند ناشناخته → نام دست‌نخورده می‌ماند. **بهتر است نماد پیدا نشود تا
   اینکه نماد اشتباه معامله شود.**

امتیازدهی شفاف است (۱۰۰ دقیق / ۹۰ پسوند بروکر / ۸۰ alias / ۶۰ شامل) و هر
پیشنهاد **دلیلش** را همراه دارد.

**اضافه شد:**
- `shadbot-data mt5-resolve --symbol XAUUSD` — دستور جدید
- `mt5-ingest` هنگام شکست خودش پیشنهاد می‌دهد (`_suggest_symbol`)
- `run_real_data.py --auto-symbol` — نزدیک‌ترین نماد را می‌پذیرد، ولی
  **هرگز بی‌صدا**؛ همیشه چاپ می‌کند چه چیزی را جایگزین کرد

**۱۸ تست** در `tests/unit/dataset/test_mt5_symbol_resolver.py`.

### تأیید نهایی

کل سفر ویندوز با ترمینال ساختگی شبیه‌سازی شد (بروکری که طلا را `XAUUSD.i`
می‌نامد): اتصال → فهرست نمادها → تشخیص خودکار → ingest ۲۸۸۰ کندل → بدون قرنطینه.

```
black ✅  ruff ✅  mypy (253 files) ✅
pytest            697 passed, 6 skipped   (قبلاً 672)
RUN_TF=1 pytest   703 passed              (قبلاً 678)
```

**گزارش کامل:** `MT5_READINESS_REPORT.md`

---

## 2026-08-16 — فاز ۲۹: دو مدل پیش‌بینی (درخواست کاربر)

**درخواست:** یک مدل که high/low تا ۵ کندل آینده را پیش‌بینی کند، و یک مدل که
سیگنال را با درصد احتمال بدهد. هر دو roll-forward، با همهٔ فیچرها.
رنج روی ۱H، سیگنال روی ۵M.

### ممیزی اول — کد این قابلیت را نداشت

| نیاز | وضعیت قبل |
|---|---|
| رگرسیون high/low | ❌ `_build_compiled` فقط `SparseCategoricalCrossentropy` |
| سیگنال با احتمال | ⚠️ softmax بود ولی `predict()` به یک float فشرده می‌کرد |
| ۱۰۹ فیچر | ❌ `build_direction_series` فقط **۴** فیچر می‌ساخت |
| تایم‌فریم per-model | ❌ وجود نداشت |
| roll-forward | ✅ بود و درست |

پس فاز جدید لازم بود. `docs/Phases/Phase29.md` نوشته شد.

### ساخته شد

```
domain/ai/prediction_target.py          PredictionTarget, RangeForecast,
                                        SignalForecast, SignalClass
infrastructure/ai/target_builder.py     برچسب‌گذاری آینده + محافظ نشت
infrastructure/ai/feature_matrix.py     ۱۰۹ فیچر + OHLCV -> ماتریس
infrastructure/ai/model_roles.py        نقش رنج (۱H) و سیگنال (۵M)
infrastructure/ai/dual_predictor.py     حفظ کامل بردار احتمال
application/services/dual_model_service.py
scripts/run_dual_models.py
```

### سه تصمیم طراحی که باید یادت بماند

۱. **هدف‌ها نسبت به close، نه قیمت مطلق.** طلا در ۲۰۰۰ و ۳۰۰۰ نباید دو مسئلهٔ
   جدا باشد. مدلی که روی قیمت مطلق آموزش ببیند، بیرون از بازهٔ آموزشش
   بی‌صدا از کار می‌افتد.
۲. **کلاس HOLD.** مدل دوکلاسه مجبور است هر کندل یک طرف را بگیرد، حتی وقتی
   هیچ اتفاقی نمی‌افتد. «معامله نکن» ارزشمندترین خروجی یک مدل معاملاتی است.
۳. **`is_coherent` به‌جای تعمیر خودکار.** اگر مدل سقف را زیر کف پیش‌بینی کند،
   گزارش می‌شود نه اینکه جایشان عوض شود. جابه‌جایی بی‌صدا، مدل خراب را پنهان
   می‌کند.

### 🐞 باگ #۱۵ — آموزش بازتولیدپذیر نبود

حین تست idempotency پیدا شد: دو اجرای یکسان پیش‌بینی متفاوت می‌داد.

**علت:** `_build_compiled` پارامتر `seed` می‌گرفت و **هرگز استفاده‌اش
نمی‌کرد**. در Keras 3 هر لایه وزن اولیه را از مولد خودش می‌گیرد، پس
`tf.random.set_seed` به‌تنهایی کافی نیست.

**نقض مستقیم فاز ۱۳ §۳۴** که بازتولیدپذیری را الزام می‌کند.

**رفع:** `keras.utils.set_random_seed(seed)`. حالا دو اجرا دقیقاً یکی است
(`fold losses [0.117292]` هر بار). دو تست رگرسیون اضافه شد.

### تأیید عملی

```
RANGE MODEL (1H, ۵ کندل جلوتر) — با ۱۰۹ فیچر
  usable rows: 497 | feature columns: 115 | dropped warmup: 51
  current close 1990.69 -> high 2001.80 (+0.558%) low 1990.36 (-0.016%)

SIGNAL MODEL (5M, ۵ کندل جلوتر) — با ۱۰۹ فیچر
  label balance: {'sell': 61, 'hold': 170, 'buy': 64}
  sell 33.6% | hold 34.1% | buy 32.3%  -> hold 34.1%  actionable=False
```

**۱۱۵ ستون** = ۶ خام + ۱۰۹ کاتالوگ. کاتالوگ فاز ۱۲ بالاخره به AI وصل شد.

```
pytest 759 passed, 12 skipped  |  RUN_TF=1 → 771 passed   (قبلاً 703)
```

**۶۸ تست جدید** — ۲۱ هدف‌ها، ۱۷ برچسب‌گذاری (شامل ۳ تست نشت داده)،
۱۱ ماتریس فیچر، ۱۹ یکپارچه (شامل ۲ بازتولیدپذیری).

**گزارش کامل:** `PHASE29_REPORT.md`

---

## 2026-08-16 — فاز ۳۰: دیتاست آموزش و بافر زندهٔ بازار

**درخواست کاربر:** دیتاست ۱۰۰٬۰۰۰ کندلی (۵M و ۱H) با فیچرهای ذخیره‌شده،
پنجرهٔ ورودی ۵۰۰×۱۲۳، roll-forward با گام یک کندل، آپدیت هفتگی با محاسبهٔ
مجدد کامل فیچرها، بافر زندهٔ ۸۰۰ کندلی، و بک‌تست روی همان دیتاست ۱۰۰k.

### تصمیم‌های کلیدی

۱. **۱۲۳ ستون.** کاربر درست گفت که قیمت خام در ورودی نبود — کاتالوگ فقط
   `*_filter` داشت که قیمت **هموارشده با موجک** است. ۸ ستون خام اضافه شد
   (`open_rel`…`ohlc4_rel`, `volume_raw_log`)، همه نسبت به close.
   ۸ خام + ۶ مشتق + ۱۰۹ کاتالوگ = **۱۲۳**.

۲. **ژنراتور به‌جای ماتریس.** ۹۹٬۴۹۶ پنجرهٔ ۵۰۰×۱۲۳ = **۲۴.۵ گیگابایت**.
   ماتریس تخت فقط ۵۰ مگابایت است. پنجره‌ها لحظه‌ای ساخته می‌شوند. این
   بهینه‌سازی نیست — بدون آن قابلیت اصلاً اجرا نمی‌شود.

۳. **محاسبهٔ مجدد کامل، نه افزایشی.** EMA/MACD/ATR بازگشتی‌اند؛ مقدار
   محاسبه‌شده از تاریخچهٔ ناقص به‌شکلی نامحسوس غلط است. ~۲ دقیقه برای
   ۱۰۰k در برابر فیچرهای بی‌صدا خراب، معاملهٔ خوبی است.

۴. **بافر: جایگزینی نه تکرار.** کندل ۱H جاری قبل از بسته‌شدن ۱۲ بار گرفته
   می‌شود؛ append کردنش ۱۲ ساعت تاریخ جعلی می‌سازد. کندل با timestamp
   موجود **جایگزین** می‌شود، و کندل قدیمی ناشناخته **رد** می‌شود.

۵. **۸۰۰ به‌جای ۵۰۰.** warm-up فیچرها ۵۱ ردیف می‌خورد → ۷۴۹ باقی می‌ماند.
   بافر این را در زمان اجرا **بررسی** می‌کند و اگر کم بیاورد پنجرهٔ کوتاه
   نمی‌دهد، چون ورودی کوتاه یعنی مدل زباله می‌خواند.

### 🐞 باگ #۱۶ — digest دیتاست هرگز تطبیق نمی‌کرد

تست round-trip گرفتش: digest روی float64 حساب می‌شد ولی ماتریس float32
ذخیره می‌شد، پس بعد از reload **همیشه** فرق داشت — یعنی به‌عنوان بررسی
صحت کاملاً بی‌فایده بود.

گرد کردن به ۴ و ۶ رقم جواب نداد؛ اندازه‌گیری نشان داد خطا **نسبی** است
(~6e-8) و هر دقت ثابتی برای بعضی مقادیر روی مرز گرد کردن می‌افتد.
رفع: هش روی شکل ذخیره‌شدهٔ float32 با `struct.pack("<f", …)` — دقیقاً
همان بایت‌هایی که روی دیسک می‌روند.

### تأیید عملی

```
BUILD 6,000 candles/timeframe -> 15.0s
  5M: 6,000 -> 5,897 rows x 123 cols | stride-1 windows: 5,393
  1H: 6,000 -> 5,897 rows x 123 cols | stride-1 windows: 5,393

generator (100k): 99,496 windows of (500 x 123), stride 1
                  lazy 50 MB vs materialised 24.5 GB

dual models: input_shape=(500, 123) — both range and signal
LIVE BUFFER: 900 primed -> holds 800 -> model input 500 x 123
```

```
pytest 819 passed, 12 skipped  |  RUN_TF=1 → 831 passed   (قبلاً 771)
```

**۶۰ تست جدید** — ۲۱ ژنراتور پنجره، ۱۷ بافر زنده، ۲۱ یکپارچه دیتاست،
به‌علاوهٔ ۲ تست به‌روزشدهٔ فاز ۲۹ (۶ ستون → ۱۴ ستون).

**گزارش کامل:** `PHASE30_REPORT.md`

---

## 2026-08-16 — فاز ۳۱: حلقهٔ زندهٔ تصمیم‌گیری + بک‌تست با مدل واقعی

**درخواست کاربر:** «به همون ترتیبی ک خودت میدونی بهترینه انجام بده» →
ترتیب انتخابی: **A (حلقهٔ زنده) بعد B (وصل مدل به بک‌تست)**.

### شکافی که پر شد

فازهای ۲۹-۳۰ مدل‌ها و داده را ساختند، ولی هیچ چیز آن‌ها را به معامله وصل
نمی‌کرد. بافر ۸۰۰ کندلی خوانده نمی‌شد، ماتریس ۵۰۰×۱۲۳ مصرف نمی‌شد، و
`MomentumPredictionSource` هنوز پیش‌بینی‌کنندهٔ بک‌تست بود.

### الف) حلقهٔ زنده

`DualModelStrategy` — شش دروازه، هر کدام با دلیل:
۱) هر دو forecast موجود · ۲) مدل HOLD نگوید · ۳) اطمینان کافی ·
۴) رنج منسجم · ۵) reward/risk کافی · ۶) حرکت بزرگ‌تر از هزینه.

`LiveDecisionService` — یک tick کامل: بافر → فیچر → ۵۰۰×۱۲۳ → دو مدل →
استراتژی → گیت ریسک → اجرا.

**قاعدهٔ سخت: tick هرگز exception نمی‌دهد.** حلقهٔ بدون نظارت که با یک
اختلال بروکر بمیرد، یعنی قطعی سرویس. هر خطا به `TickResult` با
`status` و `reason` تبدیل می‌شود.

### ب) بک‌تست با مدل

`ModelPredictionSource` پورت موجود را پیاده می‌کند، پس موتور دست‌نخورده
ماند. دو تضمین علیت:
- منبع پنجرهٔ **خودش** را نگه می‌دارد و فقط باری را که موتور تحویل داده
  اضافه می‌کند — چیز دیگری در دسترس نیست
- تا پر شدن پنجره `None` برمی‌گرداند (خودداری)، نه padding

سه کلاس روی یک محور: از **directional confidence** استفاده می‌شود، پس
۰.۴۵/۰.۱۰/۰.۴۵ برابر ۰.۵ خوانده می‌شود (بلاتکلیف) نه خرید ضعیف.

### 🐞 ناسازگاری گزارش reward/risk

برای **فروش**، reward و risk جا عوض می‌کنند. `RangeForecast.reward_risk()`
دید long-oriented است، پس چاپ آن با دروازه‌ای که تازه معامله را تأیید کرده
تناقض داشت: `r/r 0.25` نمایش داده می‌شد در حالی که دروازه ۴.۰ حساب کرده بود.
رفع: استراتژی نسبت جهت‌آگاه خودش را گزارش می‌کند.

**mypy هم سایه‌افتادن متغیر گرفت** — نام `forecast` برای دو نوع مختلف در یک
scope استفاده شده بود.

### تأیید عملی

```
LIVE LOOP (سه tick، هر سه مسیر):
  tick 1  [no_trade] signal model says hold (65.0%)
  tick 2  [no_trade] reward/risk 0.30 < 1.20
  tick 3  [traded]   signal buy 90.0%, target 2046.85, r/r 3.33
                     filled : 0.01 @ 2028.58

MODEL-DRIVEN BACKTEST (مدل واقعاً آموزش‌دیده):
  bars 700 | model calls 59 | trades 7 | return +12.35%
```

> ⚠️ آن +۱۲.۳۵٪ روی یک **موج سینوسی** است که ذاتاً قابل پیش‌بینی است.
> عدد معناداری نیست — فقط ثابت می‌کند زنجیره کامل کار می‌کند.

```
pytest 866 passed, 12 skipped  |  RUN_TF=1 → 878 passed   (قبلاً 831)
```

**۴۷ تست جدید** — ۱۶ استراتژی دومدلی، ۱۵ حلقهٔ زنده (شامل تاب‌آوری در
برابر مدل خراب)، ۱۶ بک‌تست مدل (بیشترشان دربارهٔ علیت).

**گزارش کامل:** `PHASE31_REPORT.md`

---

## 2026-08-16 — فاز ۲۴: Deployment (تنها فاز کاملاً صفر)

**درخواست کاربر:** «فاز ۲۴ رو اجرا کن»

### ساخته شد

| فایل | نقش |
|---|---|
| `domain/deployment/health.py` | liveness / readiness / health با دسته‌بندی وابستگی |
| `domain/deployment/release.py` | نسخه، محیط، manifest، shutdown امن |
| `infrastructure/deployment/backup.py` | بکاپ + تأیید + بازیابی + prune |
| `infrastructure/deployment/health_checks.py` | probe های واقعی |
| `application/services/runner_service.py` | اجرای مداوم با نظارت |
| `deploy_cli.py` | `health`, `manifest`, `backup`, `restore`, `preflight` |
| `deploy/install_service.ps1` | ثبت در Task Scheduler ویندوز |
| `scripts/run_service.py`, `scripts/run_weekly_update.py` | اجرا |

### چهار تصمیم که باید یادت بماند

۱. **liveness ≠ readiness ≠ health.** سیستمی که تازه بالا آمده زنده است ولی
   آماده نیست. جمع‌کردن این سه در یک boolean دقیقاً همان چیزی است که باعث
   می‌شود پلتفرم روی سیستم نیمه‌آماده معامله کند.

۲. **وابستگی بحرانی از اختیاری جدا شد.** نبودن MT5 یا TensorFlow سیستم را
   `degraded` می‌کند نه `unhealthy` — داشبورد باید کار کند.

۳. **بکاپی که هرگز بازیابی نشده، بکاپ نیست** (§۸۰). هر بکاپ بلافاصله باز،
   integrity-check و row-count می‌شود. از SQLite backup API استفاده شد نه
   کپی فایل: کپی‌کردن دیتابیس وسط یک تراکنش فایلی می‌سازد که سالم به‌نظر
   می‌رسد و خراب restore می‌شود — بدترین حالت ممکن.

۴. **Task Scheduler نه Windows Service.** سرویس واقعی در session 0 اجرا
   می‌شود و آنجا ترمینال MT5 **در دسترس نیست** (IPC محلی در session کاربر).
   این محدودیت است، نه میان‌بر — در خود اسکریپت مستند شد.

### 🐞 باگ #۱۷ — ترتیب لیست بکاپ‌ها غلط بود

تست گرفتش: مرتب‌سازی بر اساس **نام فایل** بود، ولی دو بکاپ در یک ثانیه فقط
با پسوند عددی فرق دارند و `live-...-1.db` از `live-...db` **جلوتر** مرتب
می‌شود. یعنی `latest()` بکاپ **قدیمی‌تر** را برمی‌گرداند — و یک restore
می‌توانست بی‌صدا دیتای اشتباه را برگرداند.

رفع: مرتب‌سازی بر اساس زمان ثبت‌شده، با mtime به‌عنوان tie-breaker.

### 🐞 نقض معماری که تست گرفت

`default_monitor` در لایهٔ **domain** بود ولی از `infrastructure.data` import
می‌کرد. `test_dependency_direction` شکست. به `infrastructure/deployment/
health_checks.py` منتقل شد — دامنه باید از SQLite و TensorFlow و MT5 بی‌خبر
بماند.

### تأیید عملی

```
health      : degraded (MT5 optional missing) | ready=True | exit 0
backup      : 128 KB | schema v1 | 9 rows | verified=True
preflight   : READY. production requires explicit confirmation
service     : 3 cycles, 1 trade, backup at cycle 2
shutdown    : stopped accepting work -> in-flight completed -> persisted -> stopped
weekly      : revision 1, 2,897 rows x 123 cols, 9.1s
restore     : بدون --yes رد می‌شود ✓ | فایل خراب قبل از overwrite رد می‌شود ✓
```

```
pytest 932 passed, 12 skipped   (قبلاً 866)
```

**۶۶ تست جدید** — ۳۹ واحد (health/release)، ۲۷ یکپارچه (backup/runner).

**گزارش کامل:** `PHASE24_REPORT.md`

---

## 2026-08-16 — تکمیل فازهای ۹، ۲۱، ۲۲ (سه فاز حداقلی)

**درخواست کاربر:** «بررسی کن کامل اگ فاز ۲۴ تکمیل شده، برو سراغ ۹ و ۲۱ و ۲۲»

### اول: تأیید فاز ۲۴

فایل‌ها (هر ۱۰ تا) + عملکرد + ۶۶ تست → **کامل تأیید شد** ✅

### فاز ۹ — معماری پلاگین (۳۷ → ۵۹۵ خط)

`registry.py` + `manager.py`. خط جداکننده‌ای که سند می‌کشد رعایت شد:
Registry می‌گوید «چه چیزی ثبت شده»، Manager می‌گوید «وضعیت عملیاتی چیست».

- state machine واقعی با ۹ حالت؛ انتقال غیرمجاز **رد** می‌شود
- پلاگین شکست‌خورده **دلیلش را نگه می‌دارد** (§۱۸)
- کشف **قطعی**: هرگز پوشه اسکن نمی‌شود — آن اجرای کد دلخواه است
- گراف وابستگی + تشخیص چرخه؛ اگر وابستگی fail شود، dependent اجرا نمی‌شود
- یک پلاگین خراب کل استارتاپ را نمی‌خواباند

### فاز ۲۱ — پیکربندی لایه‌ای (۱۲۰ → ۴۵۰ خط)

شش لایه با اولویت قطعی. mapping ها بازگشتی merge، لیست‌ها جایگزین.

**محافظت از secret** مهم‌ترین بخش: تشخیص خودکار بر اساس نام کلید، و
redaction در `as_dict`, `to_json` **و `__repr__`**. یک traceback که شیء
config را چاپ کند نباید رمز بروکر را لو بدهد. قاعده در **یک نقطه** اعمال
شد نه در هر call site.

اعتبارسنجی همهٔ خطاها را یکجا گزارش می‌کند (§۲۸).

### فاز ۲۲ — لاگینگ ساختاریافته (۲۴ → ۴۰۰ خط)

JSON، correlation id که خودش منتشر می‌شود، bound logger، چرخش فایل.

از `contextvars` استفاده شد نه global: command bus و runner threaded هستند
و تستی ثابت می‌کند context بین thread ها نشت نمی‌کند.

secret ها **داخل logger** پنهان می‌شوند — قبل از رسیدن به هر sink.

### 🐞 هشداری که ruff گرفت

`ContextVar("...", default={})` — آن dict بین هر context ای که مقدار ست
نکرده **مشترک** است. یک mutation درجا فیلدها را بین عملیات‌های نامرتبط نشت
می‌داد. با `default=None` رفع شد. نکتهٔ ظریفی بود.

### کیفیت

```
black ✅ ruff ✅ mypy (279 files) ✅
pytest 1034 passed, 12 skipped     (قبلاً 932)
```

**۱۰۲ تست جدید:** ۲۹ پلاگین · ۴۲ پیکربندی · ۳۱ لاگینگ

🎉 **هر ۲۸ فاز اصلی + ۳ فاز جدید کامل شدند.**

**گزارش:** `PHASE_9_21_22_REPORT.md`

---

## قدم بعدی توافق‌شده

**C — اتصال به دیتای واقعی MetaTrader 5.**

کاربر گفت «باشه بریم». کار سمت سندباکس (لینوکس) تمام است؛ ادامه‌اش نیازمند
اجرای کاربر روی ویندوز است:

```powershell
pip install -r requirements-mt5.txt
shadbot-data mt5-check
shadbot-data mt5-symbols --pattern XAU
python scripts\run_real_data.py --symbol XAUUSD
```

⚠️ نام نماد بین بروکرها فرق دارد: `XAUUSD`, `XAUUSD.i`, `XAUUSDm`, `GOLD`.
اگر فهرست خالی بود: در MT5 → Market Watch → راست‌کلیک → **Show All**.

**بعد از آن:** A (وصل‌کردن WaveNet به بک‌تست) سپس B (فاز ۲۴ Deployment).
