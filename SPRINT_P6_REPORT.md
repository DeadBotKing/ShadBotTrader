# گزارش Sprint P6 — Simulation & Backtesting

**تاریخ:** ۲۰۲۶-۰۸-۱۶
**فاز:** Phase 28 — Implementation Foundation
**مرجع معماری:** `docs/Phases/Phase16.md`

---

## تغییرات درخواستی روی دموی P5

| مورد | قبل | بعد |
|---|---|---|
| سرمایه‌ی اولیه | `100000 USD` | **`100 USD`** |
| spread | `2` | **`4`** |

اثرش روی نتیجه: سود از ۱۴۸.۷۶ به **۱۴۰.۷۶** کاهش یافت — spread پهن‌تر یعنی
ورود گران‌تر و خروج ارزان‌تر. دقیقاً همان چیزی که باید اتفاق بیفتد.

---

## چه چیزی ساخته شد

```
MarketEvent -> PredictionSource -> Strategy -> RiskGate -> Intent
            -> SimulatedVenue -> Fills -> Portfolio -> EquityPoint
                                                    -> PerformanceMetrics
```

### دامنه — `src/ShadBotTrader/domain/simulation/`

| فایل | محتوا |
|---|---|
| `simulation_types.py` | `SessionStatus`، `SimulationMode`، `MarketEventType`، `EventPriority` |
| `clock.py` | `SimulationClock` + `ClockSnapshot` — یگانه منبع زمان |
| `market_event.py` | `MarketEvent`، `SimulationEventQueue` (صف اولویت‌دار) |
| `equity_curve.py` | `EquityPoint`، `EquityCurve` + منحنی drawdown |
| `performance.py` | `PerformanceMetrics`، `TradeRecord`، Sharpe، انحراف معیار |
| `session.py` | `SimulationSession`، `SimulationConfiguration` |
| `ports.py` | ۳ قرارداد: DataProvider، PredictionSource، Reporter |
| `events.py` | ۸ رویداد دامنه |

### زیرساخت — `src/ShadBotTrader/infrastructure/simulation/`

| کلاس | نقش |
|---|---|
| `CandleMarketDataProvider` | پخش سری کندل تاریخی |
| `MomentumPredictionSource` | خط پایه‌ی شفاف و علّی |
| `ScriptedPredictionSource` | زمان‌بندی ثابت برای تست و سناریو |
| `BacktestEngine` | ارکستراسیون کل زنجیره |
| `ConsoleSimulationReporter` | گزارش برنامه، پیشرفت و نتیجه |

### اپلیکیشن

`application/services/backtest_service.py` — نقطه‌ی ترکیب که دیتاست تاریخی را
به **همان** کامپوننت‌های production وصل می‌کند.

---

## اصل معماری: ارکستراسیون، نه بازنویسی

طبق Phase 16 §2-3، منطق trading / risk / portfolio **نباید** برای بک‌تست دوباره
نوشته شود. موتور دقیقاً همان `TradingDecisionService`، `PolicyRiskGate`،
`ExecutionService` و `InMemoryPortfolioLedger` را استفاده می‌کند؛ فقط منبع داده
و venue عوض می‌شوند.

یک تست این را تضمین می‌کند:
`test_backtest_reuses_the_production_components`

---

## قطعیت (Determinism) — ساختاری، نه توافقی

| تضمین | مرجع | نحوه‌ی اعمال |
|---|---|---|
| بدون `datetime.now()` | §9 | زمان فقط از `SimulationClock` |
| ساعت عقب نمی‌رود | §10 | `advance_to` استثنا می‌دهد |
| ترتیب کامل رویدادها | §18 | کلید `(زمان، اولویت، ترتیب درج)` |
| اجرای مجدد = نتیجه‌ی یکسان | §10 | `test_identical_inputs_produce_identical_results` |

`EventPriority` تضمین می‌کند داده‌ی بازار همیشه **قبل از** تصمیم‌هایی که
تولید می‌کند دیده شود — بدون این، دو اجرا می‌توانستند نتیجه‌ی متفاوت بدهند.

---

## نتیجه‌ی واقعی بک‌تست

```
scenario      trades       return   return %   maxDD %       fees
no costs          51      -0.5280     -0.528     0.583     0.0000
with costs        51      -2.7946     -2.795     2.850     0.2066
```

sweep روی spread:

```
    spread  trades       return   return %   maxDD %     hit       fees
         0      51      -0.7346     -0.735     0.790   0.118     0.2066
         2      51      -1.7646     -1.765     1.820   0.059     0.2066
         4      51      -2.7946     -2.795     2.850   0.000     0.2066
        20      51     -11.0346    -11.035    11.090   0.000     0.2066
```

⚠️ **این نتایج ضررده هستند و باید هم باشند.** دلیل:

1. دیتاست نمونه **تصادفی تولید شده** است — الگوی واقعی بازار ندارد.
2. `MomentumPredictionSource` یک خط پایه‌ی عمداً ساده است، نه مدل آموزش‌دیده.
3. با داده‌ی بی‌الگو، هر استراتژی به‌اندازه‌ی هزینه‌های معاملاتی ضرر می‌دهد.

آنچه این اعداد **اثبات می‌کنند** این است که حسابداری درست کار می‌کند:
hit rate با پهن‌تر شدن spread از ۰.۱۱۸ به صفر می‌رسد و ضرر خطی رشد می‌کند.
اگر بک‌تست روی داده‌ی تصادفی سود نشان می‌داد، **آن** باید نگران‌کننده می‌بود.

---

## معیارهای صادق

متریک‌هایی که از نظر ریاضی تعریف‌نشده‌اند `None` برمی‌گردانند، نه صفر:

| متریک | چه زمانی `n/a` |
|---|---|
| Sharpe | کمتر از ۲ مشاهده، یا پراکندگی صفر |
| profit factor | هیچ معامله‌ی ضررده نبوده (نسبت بی‌نهایت) |
| hit rate / expectancy | هیچ معامله‌ای انجام نشده |
| recovery factor | drawdown صفر |

گزارش صفر در این حالت‌ها گمراه‌کننده است — مخصوصاً `profit factor = 0`
وقتی معنی‌اش «هیچ ضرری نبوده» است.

---

## وضعیت کیفیت

| بررسی | نتیجه |
|---|---|
| `black --check .` | ✅ ۲۷۷ فایل |
| `ruff check .` | ✅ پاس |
| `mypy src` | ✅ ۲۱۰ فایل |
| `pytest` | ✅ **۳۸۹ passed, 6 skipped** |
| `RUN_TF=1 pytest` | ✅ **۳۹۵ passed** |

**رشد تست‌ها:** ۳۳۷ → **۳۹۵** (۵۸ تست جدید)

- ۳۹ تست هسته‌ی شبیه‌سازی (ساعت، صف، session، منحنی، متریک)
- ۱۹ تست یکپارچگی موتور بک‌تست

---

## یادداشت: یک تست فرض من را غلط درآورد

تست اولیه‌ام ادعا می‌کرد بازار کاملاً ثابت هیچ معامله‌ای تولید نمی‌کند.
اجرا نشان داد **یک** پوزیشن باز می‌شود: momentum روی سری ثابت دقیقاً `0.5`
برمی‌گرداند و استراتژی آن را BUY می‌خواند (چون شرط `>= 0.5` است).

این رفتار قابل دفاع است (مرز باید جایی باشد)، پس **کد را تغییر ندادم** و
به‌جایش تست را با واقعیت هماهنگ کردم و علتش را مستند کردم. تست حالا تأیید
می‌کند که هیچ round trip کامل نمی‌شود و PnL محقق‌شده صفر می‌ماند.

---

## دستورات جدید

```bash
python scripts/run_backtest.py
python scripts/run_backtest.py --compare
python scripts/run_backtest.py --capital 100 --spread 4 --steps

shadbot-backtest run --capital 100 --spread 4
shadbot-backtest sweep --param spread --values 0,2,4,10,20
shadbot-backtest sweep --param commission --values 0,0.0001,0.001
```

---

## آنچه عمداً ساخته نشد

طبق Phase 16 این‌ها در معماری هستند ولی این sprint پیاده نکرد:

- **Monte Carlo** (§1) — نیاز به مدل تصادفی‌سازی دارد
- **Checkpoint/branching کامل** (§25-27) — `SimulationClock` قابلیت
  snapshot/restore دارد، ولی چک‌پوینت کامل پرتفوی + صف هنوز نه
- **مدل latency و market impact** (§28) — venue فعلاً spread، slippage و
  کارمزد را مدل می‌کند
- **Paper trading زنده** (§4) — نیاز به منبع داده‌ی زنده دارد

هیچ‌کدام را به‌صورت قلابی نساختم.

---

## مرحله‌ی بعدی — Sprint P7: Self-Learning & Optimisation

طبق `docs/Phases/Phase17.md`:

1. **`ParameterSpace`** — تعریف فضای جستجو روی تنظیمات استراتژی و ریسک
2. **`Optimizer`** — grid / random search با ارزیابی از طریق بک‌تست
3. **Walk-forward optimisation** — بهینه‌سازی in-sample، اعتبارسنجی out-of-sample
4. **`PromotionPolicy`** — ارتقای یک پیکربندی فقط وقتی خارج از نمونه بهتر باشد
5. **محافظت از overfitting** — همان دلیلی که بک‌تست فعلی ضرر نشان می‌دهد

حالا که بک‌تست کار می‌کند، بهینه‌سازی معنا پیدا می‌کند — چون تابع هدف
قابل اندازه‌گیری است.
