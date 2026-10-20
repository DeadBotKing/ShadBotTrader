# بک‌تست و شبیه‌سازی الان دقیقاً چطور کار می‌کنند

**تاریخ:** 2026-08-18 · نوشته شده از روی کد، نه از روی مستندات قدیمی.

این سند قدیمی، رفتار baseline قبل از پیاده‌سازی بک‌تست دومدلی را توصیف می‌کند. رفتار جدید و مرجع فعلی در `docs/DUAL_MODEL_BACKTEST.md` ثبت شده است.

از این نسخه به بعد، وقتی هر دو مدل و هر دو تایم‌فریم در دسترس باشند، حالت `auto`/`dual` این زنجیره را اجرا می‌کند:

```text
5M binary signal window -> BUY/SELL + probability threshold
                -> 1H range window -> predicted high/low
                -> next 5M open -> fixed TP/SL -> candle-by-candle exit
```

این سند فقط توصیف baseline قدیمی است و ادعاهای «فقط مومنتوم»، «بدون TP/SL» و «اجرای روی close» را نباید به مسیر جدید نسبت داد. جزئیات مرجع در سند بالا آمده است.

هدف این سند قدیمی این است که رفتار baseline را جداگانه نگه دارد تا نتایج آن با مدل واقعی قاطی نشود.

---

## ۱. زنجیرهٔ کامل — از کندل تا معامله

```
کندل ذخیره‌شده
   ↓  CandleMarketDataProvider          (infrastructure/simulation/candle_data_provider.py)
MarketEvent (یکی به ازای هر کندل، مرتب‌شده بر اساس open_time)
   ↓  SimulationEventQueue + SimulationClock
BacktestEngine._process(event)          (infrastructure/simulation/backtest_engine.py)
   ↓  PredictionSource.predict(event)   ← ⚠️ اینجا مدل نیست، مومنتوم است
یک عدد بین ۰ و ۱
   ↓  AiDirectionalStrategy             (infrastructure/trading/ai_directional_strategy.py)
BUY / SELL / HOLD
   ↓  PositionAwareDecisionEngine       (infrastructure/trading/decision_engine.py)
ENTER / EXIT / HOLD
   ↓  PolicyRiskGate                    (infrastructure/trading/risk_gate.py)
تأیید یا رد
   ↓  DefaultIntentFactory              (infrastructure/trading/intent_factory.py)
TradingIntent (سمت + سیاست حجم + سیاست قیمت)
   ↓  DefaultIntentResolver             (infrastructure/execution/intent_resolver.py)
ResolvedOrder (حجم عددی، نوع سفارش)
   ↓  SimulatedExecutionVenue           (infrastructure/execution/simulated_venue.py)
Fill (قیمت اجرا، کارمزد)
   ↓  PortfolioLedger
پوزیشن + PnL + منحنی سرمایه
```

هر بار که دکمهٔ **Run a backtest** یا **Record a replay** را می‌زنی، همین
زنجیره برای **هر کندل، یک‌بار** اجرا می‌شود.

---

## ۲. سیگنال از کجا می‌آید؟ (مهم‌ترین نکته)

دکمهٔ بک‌تست داشبورد این خط را دارد
(`presentation/commands/handlers.py`):

```python
prediction_source=MomentumPredictionSource(lookback=6)
```

یعنی:

> **بک‌تست فعلی اصلاً از مدل‌های آموزش‌دیدهٔ تو استفاده نمی‌کند.**

`MomentumPredictionSource` این است
(`infrastructure/simulation/prediction_sources.py`):

```python
change = (close[t] - close[t-6]) / close[t-6]
raw    = 0.5 + change * 200          # sensitivity = 200
value  = clamp(raw, 0, 1)
```

سپس:

```python
confidence = 0.75 + |value - 0.5| * 2 * 0.2      # بین 0.75 و 0.95
```

پس «پیش‌بینی» فقط یک قانون مومنتوم ۶ کندلی است. هیچ WaveNet‌ای، هیچ مدل
range یا signal‌ای، هیچ ماتریس ۵۰۰×۱۲۳‌ای در بک‌تست دخیل نیست.

**چرا اینطور ساخته شد؟** به‌عنوان baseline شفاف: اگر نتیجهٔ بک‌تست بد است،
می‌خواستیم مطمئن باشیم مشکل از پایپ‌لاین است نه از جعبهٔ سیاه. ولی حالا که
مدل‌ها آموزش می‌بینند، این دیگر یک حفره است نه یک ویژگی.

> نکته: کلاس `DualModelStrategy` که هر دو مدل را می‌خواند **وجود دارد و
> تست شده** — ولی فقط در حلقهٔ **لایو** (`LiveDecisionService`) استفاده
> می‌شود، نه در بک‌تست.

---

## ۳. یک معامله دقیقاً کِی باز می‌شود؟

سه فیلتر پشت سر هم:

### فیلتر ۱ — استراتژی (`AiDirectionalStrategy`)

```python
if prediction is None:                 → HOLD
if age > 300 ثانیه:                    → HOLD (کهنه)
if confidence < min_confidence (0.55): → HOLD
if value >= 0.5: BUY   else: SELL
```

توجه کن: **هیچ باند خنثایی وجود ندارد.** دقیقاً `0.5` مرز است. مومنتوم
+۰.۰۰۱٪ می‌شود BUY و −۰.۰۰۱٪ می‌شود SELL. یعنی استراتژی همیشه یک نظر
دارد و عملاً هیچ‌وقت واقعاً HOLD نمی‌گوید (چون confidence حداقل ۰.۷۵ است
و همیشه از ۰.۵۵ بیشتر است).

### فیلتر ۲ — موتور تصمیم (`PositionAwareDecisionEngine`)

جدول کامل:

| پوزیشن فعلی | سیگنال | تصمیم |
|---|---|---|
| FLAT | BUY | **ENTER** |
| FLAT | SELL | **ENTER** |
| LONG | BUY | HOLD (هم‌جهت، کاری نمی‌کند) |
| LONG | SELL | **EXIT** ← فقط می‌بندد، برعکس نمی‌کند |
| SHORT | SELL | HOLD |
| SHORT | BUY | **EXIT** |

`allow_reversal=False` پیش‌فرض است. یعنی برای برگشتن از long به short
**دو کندل** لازم است: یکی برای بستن، یکی برای باز کردن جدید.

### فیلتر ۳ — گیت ریسک (`PolicyRiskGate`)

بک‌تست داشبورد با `RiskPolicy()` پیش‌فرض اجرا می‌شود:

```
max_drawdown_percent   = 20
max_daily_loss_percent = 5
max_exposure_ratio     = 0.5
max_open_positions     = 5
min_confidence         = 0.0
```

ولی — و این مهم است — بک‌تست هیچ‌وقت `risk_state` را در context پر
نمی‌کند (`StrategyContext` فقط `predictions` و `portfolio` می‌گیرد). پس
**سه محدودیت اول هرگز چک نمی‌شوند.** عملاً فقط `max_open_positions` فعال
است، و چون هر نماد حداکثر یک پوزیشن دارد، آن هم هیچ‌وقت فعال نمی‌شود.

**نتیجه: گیت ریسک در بک‌تست فعلی عملاً هیچ چیزی را رد نمی‌کند.**

---

## ۴. حجم معامله چقدر است؟

```python
base_quantity = Decimal("0.01")     # ثابت، در handlers.py
quantity_policy_type = FIXED
```

پس هر معامله دقیقاً **۰.۰۱ لات** است. نه درصدی از سرمایه، نه بر اساس
اطمینان، نه بر اساس نوسان. `DefaultIntentResolver` سیاست‌های
`PERCENT_EQUITY` و `RISK_AMOUNT` را پشتیبانی می‌کند ولی بک‌تست از آن‌ها
استفاده نمی‌کند.

برای **بستن** پوزیشن، سیاست حجم نادیده گرفته می‌شود و همان مقدار باز
موجود بسته می‌شود (`held = position.quantity`) — نمی‌شود بیشتر از آنچه
داری ببندی.

---

## ۵. با چه قیمتی اجرا می‌شود؟

### کوت چطور ساخته می‌شود

```python
MarketQuote.from_mid(mid=candle.close, spread=spread)
half = spread / 2
bid  = close - half
ask  = close + half
```

یعنی **قیمت اجرا همیشه از close همان کندل** ساخته می‌شود — نه open کندل
بعدی. این یک فرض خوش‌بینانه است: سیگنال از close کندل t می‌آید و معامله
هم روی همان close انجام می‌شود. در واقعیت زودترین اجرای ممکن، open کندل
t+1 است.

### اسپرد

فیلد فرم `Spread` با پیش‌فرض **`4`** است. روی طلای ۴٬۳۷۶ دلار این یعنی
**۰.۰۹۱٪** — بزرگ‌تر از آستانهٔ سیگنال ۰.۰۸٪ که مدل با آن آموزش می‌بیند.
(همان باگ ۳۹ که در فاز ۴۵ برای حلقهٔ **لایو** حل شد؛ بک‌تست هنوز حل
نشده.)

### داخل SimulatedExecutionVenue

```python
touch = quote.ask  اگر BUY   else  quote.bid
execution_price = touch + slippage
fee = quantity * execution_price * commission_rate
```

بک‌تست داشبورد: `commission_rate = 0.0001` و `slippage_rate = 0`.

---

## ۶. یک معامله کِی بسته می‌شود؟

**فقط و فقط وقتی سیگنال جهت عوض شود.**

نه استاپ‌لاسی هست، نه تیک‌پرافیتی، نه سقف زمانی نگهداری، نه trailing
stop، نه بستن در پایان روز. اگر مومنتوم ۲۰۰ کندل هم‌جهت بماند، پوزیشن
۲۰۰ کندل باز می‌ماند — هرچقدر هم زیان بدهد.

جست‌وجو در کل `src/` برای `stop_loss` / `take_profit` **هیچ نتیجه‌ای
ندارد**. این مفاهیم اصلاً در دامنه وجود ندارند.

در پایان بک‌تست هم پوزیشن باز **بسته نمی‌شود**؛ فقط به‌صورت
unrealized در منحنی سرمایه می‌ماند و در فهرست `trades` نمی‌آید.

---

## ۷. سود و زیان چطور شمرده می‌شود؟

`PortfolioLedger` بر مبنای fill کار می‌کند:

- **average entry price** فقط از fill های واقعی می‌آید
- **realized PnL** فقط وقتی پوزیشن کم یا بسته شود ثبت می‌شود
- **fees** جدا از PnL ناخالص نگه داشته می‌شود
- reversal به «بستن + باز کردن» تجزیه می‌شود و فقط بخش بستن PnL می‌سازد

`BacktestEngine._capture_trade` یک `TradeRecord` می‌سازد **فقط وقتی
realized PnL تغییر کند**. یعنی:

> **معاملهٔ باز که هنوز بسته نشده، در آمار `trade_count` و `hit_rate`
> اصلاً شمرده نمی‌شود.**

منحنی سرمایه ولی هر کندل ثبت می‌شود (equity = cash + unrealized).

---

## ۸. warmup

```python
warmup_bars = 20    # در handlers.py
```

۲۰ کندل اول فقط رد می‌شوند: `observe()` صدا زده می‌شود (بافر پر شود) ولی
`predict()` نه. برای مومنتومِ ۶ کندلی این کافی است. برای مدل واقعی که
پنجرهٔ ۵۰۰ می‌خواهد، **کافی نیست** — این عدد باید با پنجرهٔ مدل هماهنگ
شود.

---

## ۹. تفاوت «Run a backtest» و «Record a replay»

هیچ تفاوت منطقی‌ای ندارند. دقیقاً همان تنظیمات، همان مومنتوم، همان
سرمایه. تنها فرق:

```python
record_replay=True
```

که باعث می‌شود `ReplayRecorder` هر کندل و هر fill را ضبط کند و در
`/replay` یک پخش‌کنندهٔ HTML بسازد. برای اجراهای زیاد این خاموش است چون
حافظه می‌خورد.

---

## ۱۰. جمع‌بندی — چه چیزهایی الان وجود ندارند

| موضوع | وضعیت فعلی |
|---|---|
| مدل‌های آموزش‌دیده در بک‌تست | ❌ فقط مومنتوم ۶ کندلی |
| باند خنثی (HOLD واقعی) | ❌ مرز دقیقاً ۰.۵ |
| استاپ لاس | ❌ وجود ندارد |
| تیک پرافیت | ❌ وجود ندارد |
| سقف زمان نگهداری | ❌ وجود ندارد |
| اجرا روی open کندل بعدی | ❌ روی close همان کندل |
| اسپرد از بروکر | ❌ ثابت ۴ (لایو حل شده، بک‌تست نه) |
| حجم بر اساس ریسک | ❌ ثابت ۰.۰۱ |
| گیت ریسک فعال | ❌ `risk_state` پر نمی‌شود |
| بستن پوزیشن در پایان بک‌تست | ❌ باز می‌ماند |
| reversal یک‌مرحله‌ای | ❌ دو کندل لازم است |
| اسلیپیج | ⚠️ پشتیبانی می‌شود ولی صفر تنظیم شده |
| کارمزد | ✅ ۰.۰۱٪ |
| اسپرد | ✅ اعمال می‌شود (BUY روی ask، SELL روی bid) |
| حسابداری fill-based | ✅ کامل و تست‌شده |
| تعیّن (determinism) | ✅ همان ورودی = همان خروجی |

---

## ۱۱. سؤال‌هایی که باید جواب بدهی

قبل از اینکه چیزی عوض کنم، این‌ها را مشخص کن:

1. **بک‌تست باید از کدام مدل‌ها استفاده کند؟** فقط signal؟ signal + range
   با هم (مثل `DualModelStrategy` در لایو)؟
2. **خروج از معامله بر چه اساسی؟** استاپ/تیک ثابت بر حسب دلار؟ بر حسب
   درصد؟ از خروجی مدل range (high/low پیش‌بینی‌شده)؟ یا هنوز فقط با
   برگشت سیگنال؟
3. **اجرا روی close همان کندل بماند یا برود روی open کندل بعدی؟**
   (دومی واقع‌گرایانه‌تر ولی نتایج را بدتر می‌کند.)
4. **اسپرد در بک‌تست چقدر؟** میانگین واقعی طلا در بروکرت چند است؟
5. **حجم:** ثابت بماند یا درصدی از موجودی/ریسک شود؟
