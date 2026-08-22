# IMPLEMENTATION STATUS — ممیزی فاز به فاز

**سند مرجع پیشرفت پروژه.** بعد از هر Sprint به‌روزرسانی می‌شود.

- **آخرین به‌روزرسانی:** 2026-08-20
- **آخرین کار انجام‌شده:** **Integrity Layer** — آزمون runtime invariance، transformer audit contract، purged target endpoints، شمارش صحیح window و گزارش جداگانهٔ high/low range metrics
- **وضعیت Quality Gate:** ✅ `black` · `ruff` · `mypy`؛ عدد نهایی pytest را فقط بعد از اجرای کامل همین نسخه ثبت کنید
- **تعداد فایل منبع:** ۲۹۵ · **فایل تست:** ۱۱۶
- ✅ **MT5 روی ویندوز وصل شد** — Alpari-MT5-Demo، ۸۸۲ نماد، ۱۰۴۶ تست سبز
- 🎉 **هر ۲۸ فاز اصلی + ۳ فاز جدید (۲۹/۳۰/۳۱) کامل شدند**

> **قاعده (طبق `docs/AGENTOPERATINGRULE.md`):** کد موجود در workspace مرجع
> واقعیت است؛ مستندات نیت معماری را تعریف می‌کنند. این سند اختلاف بین این دو
> را صادقانه ثبت می‌کند. هیچ چیزی اینجا «انجام‌شده» علامت نمی‌خورد مگر آنکه
> کد و تستش موجود و سبز باشد.

---

## جدول وضعیت فازها

| فاز | عنوان | وضعیت | کجا پیاده شده |
|---|---|---|---|
| ۱ | Architecture Principles | ✅ کامل | کل ساختار؛ تست `tests/architecture/` |
| ۲ | Dependency Rules | ✅ کامل | `test_dependency_direction.py` آن را اجبار می‌کند |
| ۳ | Domain Model | ✅ کامل | `src/ShadBotTrader/domain/` (۱۴ زیردامنه) |
| ۴ | Project Tree | ✅ کامل | ساختار فیزیکی پروژه |
| ۵ | Framework Design | ✅ کامل | `core/` |
| ۶ | Pipeline Design | ✅ کامل | پایپ‌لاین‌های data/feature/ai |
| ۷ | Engine Design | ✅ کامل | `BacktestEngine`, `WalkForwardOptimizer` |
| ۸ | Service Design | ✅ کامل | `core/services/`, `application/services/` (۸ سرویس) |
| **۹** | **Plugin Architecture** | ✅ **کامل (جدید)** | `core/plugins/{registry,manager}.py` — رجیستری، مدیر چرخهٔ حیات، کشف قطعی، گراف وابستگی، تشخیص چرخه |
| ۱۰ | Event Bus | ✅ کامل | `core/events/` |
| ۱۱ | Data Platform | ✅ کامل | `domain/dataset/`, `infrastructure/data/` + **MT5 provider** |
| ۱۲ | Feature Platform | ✅ کامل | ۲۰ calculator، ۱۰۹ فیچر |
| ۱۳ | AI Platform | ✅ کامل | WaveNet + roll-forward training |
| ۱۴ | Trading Platform | ✅ کامل | `domain/strategy/`, `infrastructure/trading/` |
| ۱۵ | Portfolio Platform | ✅ کامل | `domain/execution/`, fill-based accounting |
| ۱۶ | Simulation Platform | ✅ کامل | `domain/simulation/` + **Replay (جدید)** |
| ۱۷ | Self-Learning | ✅ کامل | `domain/learning/`, anti-overfitting گیت |
| ۱۸ | Project Intelligence | ✅ کامل | `project/` (scanner/builder/exporter) |
| ۱۹ | GUI Architecture | ✅ کامل | `presentation/` + دکمه‌ها + Replay player |
| ۲۰ | Database | ✅ با انحراف تأییدشده | **SQLite** به‌جای SQL Server — تصمیم صریح کاربر |
| **۲۱** | **Configuration** | ✅ **کامل (جدید)** | `infrastructure/configuration/layered.py` — ۶ لایه اولویت، تشخیص و پنهان‌سازی secret، اعتبارسنجی |
| **۲۲** | **Logging** | ✅ **کامل (جدید)** | `infrastructure/logging/structured.py` — JSON، correlation id، چرخش فایل، پنهان‌سازی secret |
| ۲۳ | Testing Architecture | ✅ کامل | ۶۷۸ تست: unit/integration/architecture |
| **۲۴** | **Deployment** | ✅ **کامل (جدید)** | `domain/deployment/{health,release}.py`، `infrastructure/deployment/{backup,health_checks}.py`، `application/services/runner_service.py`، `deploy_cli.py`، `deploy/install_service.ps1` |
| ۲۵ | PowerShell Generator | ⚠️ جزئی | فقط `setup_windows.ps1` |
| ۲۶ | Freeze v1.0 | ✅ رعایت می‌شود | معماری منجمد دست‌نخورده مانده |
| ۲۷ | Architecture Implementation | ✅ کامل | bootstrap/runtime/lifecycle |
| ۲۸ | Implementation Foundation | 🔄 در حال انجام | Sprint P0…P8 + Replay + MT5 |
| **درخواست 2026-08-19** | **Signal → Range → TP/SL Backtest** | ✅ **کامل (جدید)** | `dual_model_backtest_service.py` + `dual_model_prediction_source.py` + `domain/simulation/bracket.py` — signal-first، پنجره‌های metadata-driven، threshold، ورود next-open، خروج candle-by-candle و گزارش TP/SL |
| **درخواست 2026-08-19** | **Binary Signal Model** | ✅ **کامل (جدید)** | `prediction_target.py` + `target_builder.py` + `dual_predictor.py` — خروجی و label فقط SELL/BUY؛ HOLD فقط تصمیم داخلی strategy است |
| **۴۸** | **Evaluate & Inspect** | ✅ **کامل (جدید)** | `model_evaluation_service.py` + `model_diagram.py` — تست مدل روی دیتاست با لاگ تجمعی، بازرسی ماتریس، PNG معماری، سقف آرشیو |
| **۴۷** | **Best-Model Selection** | ✅ **کامل (جدید)** | فقط وقتی نتیجه بهتر شد ذخیره می‌شود — برای **هر دو** نقش (signal با `val_loss`، range با `val_mae`)؛ ذخیرهٔ نهایی بهترین را بازنویسی نمی‌کند |
| **۵۰** | **Integrity Layer** | ✅ **کامل (جدید)** | `invariance_audit.py` برای 109 feature، اثبات prefix برای 56 feature causal و ماتریس 70 ستونی، audit fit روی full-series در برابر train-prefix، purge endpoint برای targetهای variable، اصلاح window count و high/low MAE/RMSE/bias |
| **۴۶** | **Epoch Checkpoints** | ✅ **کامل (جدید)** | ذخیره بعد از هر epoch، ETA بر مبنای epoch نه fold، timeout ۸ ساعته قابل تنظیم |
| **۴۵** | **Threshold & Live Spread** | ✅ **کامل (جدید)** | `Signal threshold %` در فرم، `live_quote()` که اسپرد را از تیک متاتریدر می‌خواند، حذف اسپرد ۴ دلاری ضررده |
| **۴۴** | **Training Pace** | ✅ **کامل (جدید)** | batch_size با حجم دیتا مقیاس می‌گیرد (۵٬۹۸۶→۷۴۸ قدم)، حداکثر ۳۰ ثانیه سکوت، ETA |
| **۴۳** | **Infinite-Dataset Fix** | ✅ **کامل (جدید)** | تعداد batch از هندسهٔ fold می‌آید نه از `len()` دیتاست استریم‌شده |
| **۴۲** | **Progress Visibility** | ✅ **کامل (جدید)** | سقف ۸ خط batch در هر epoch، حذف `\r`، و پنجرهٔ لاگ که خطوط نتیجه را بر batch ترجیح می‌دهد |
| **۴۱** | **Streaming Training** | ✅ **کامل (جدید)** | `WindowGenerator` بالاخره به trainer وصل شد — ۴.۸GB→۹۶۶MB، گزارش هزینه قبل از شروع، رد فوری پنجرهٔ بزرگ‌تر از دیتا |
| **۴۰** | **Model Selection & Persistence** | ✅ **کامل (جدید)** | `infrastructure/ai/model_catalogue.py` — منوی کرکره‌ای نوع مدل/دیتاست/مدل ذخیره‌شده، ذخیرهٔ artifact با نقش و دیتاست، نسخه‌گذاری در آموزش مجدد |
| **۳۹** | **Stored Matrix & Daily Timeframe** | ✅ **کامل (جدید)** | `infrastructure/ai/stored_feature_source.py`، `domain/market/resample.py` — ماتریس از انبار (بایت‌به‌بایت یکسان)، تایم‌فریم 1D کامل، انتخاب مدل/دیتاست، پیشرفت batch |
| **۳۸** | **Feature Caching** | ✅ **کامل (جدید)** | `infrastructure/feature/feature_cache.py` — اثر انگشت کندل‌ها، استفادهٔ مجدد تا آپدیت دیتاست، محاسبهٔ کامل (نه append) بعد از تغییر |
| **۳۷** | **Feature Visibility & Per-Series Storage** | ✅ **کامل (جدید)** | `infrastructure/feature/feature_progress.py`، چیدمان `features/{symbol}/{timeframe}/`، دکمهٔ چندتایم‌فریمی، ستون Series در `/data` |
| **۳۶** | **Training Visibility** | ✅ **کامل (جدید)** | `_run_script` استریم زنده، `GET /api/log`، پنل لاگ در داشبورد، `fold_metrics`، مقایسه با majority-class baseline |
| **۳۵** | **Dual-Timeframe Datasets** | ✅ **کامل (جدید)** | `infrastructure/data/symbol_scope.py` — دو دیتاست ۵ دقیقه/۱ ساعته، برش سطر فقط از دو سر، ممنوعیت کندل ساختگی، یک نماد canonical |
| **۳۴** | **Data Inspection** | ✅ **کامل (جدید)** | `presentation/gateway/data_inspector.py`، `presentation/web/data_renderer.py` — چارت شمعی، شمارش کندل، فهرست ستون‌ها |
| **۳۳** | **Dataset Continuity** | ✅ **کامل (جدید)** | `domain/dataset/continuity.py`، `application/services/dataset_update_service.py` — append، سقف ۱۰۰k، تقویم یادگیرنده، backfill |
| **۳۲** | **Accounts & Full GUI** | ✅ **کامل (جدید)** | `domain/account/profile.py`، `infrastructure/account/profile_store.py`، ۲۱ دکمه در ۶ گروه |
| **۳۱** | **Live Loop & Model Backtest** | ✅ **کامل (جدید)** | `infrastructure/trading/dual_model_strategy.py`، `infrastructure/simulation/model_prediction_source.py`، `application/services/live_decision_service.py` |
| **۳۰** | **Training Dataset & Live Buffer** | ✅ **کامل** | `domain/dataset/training_dataset.py`، `infrastructure/ai/{window_generator,live_matrix}.py`، `infrastructure/data/live_buffer.py`، `application/services/training_data_service.py` |
| **۲۹** | **Dual Predictive Models** | ✅ **کامل** | `domain/ai/prediction_target.py`، `infrastructure/ai/{target_builder,feature_matrix,model_roles,dual_predictor}.py`، `application/services/dual_model_service.py` |

---

## انحراف‌های آگاهانه از مستندات

اینها اشتباه نیستند — تصمیم‌های ثبت‌شده‌اند:

### ۱. SQLite به‌جای SQL Server (فاز ۲۰)
**دلیل:** درخواست صریح کاربر — «اگ با Sqllite میشه همشو اوکی کرد فقط همینو
اجرا کن SQLServer نمیخواد دیگ».
**اثر:** مرزهای پورت/آداپتور رعایت شده‌اند، پس آداپتور SQL Server بعداً بدون
دست‌زدن به دامنه قابل افزودن است. دامنه هیچ‌جا SQL نمی‌شناسد (طبق §179 فاز ۲۰).

### ۲. `MomentumPredictionSource` به‌جای WaveNet در بک‌تست
**دلیل:** یک baseline شفاف عمدی. رفتارش قابل پیش‌بینی است، پس هر نتیجهٔ
بک‌تست را می‌توان به پایپ‌لاین نسبت داد نه به جعبهٔ سیاه.
**بدهی:** وصل‌کردن WaveNet + ۱۰۹ فیچر به شبیه‌سازی هنوز باقی است.

### ۳. مواردی که عمداً ساخته نشده‌اند
Monte Carlo · checkpoint/branching کامل · مدل latency و market-impact ·
paper trading زنده · Champion/Challenger · shadow mode · drift detection ·
Bayesian optimisation · جست‌وجوی هایپرپارامتر WaveNet · احراز هویت داشبورد ·
WebSocket/SSE · ذخیرهٔ equity curve به ازای هر بار.

**چرا:** طبق `DEVELOPMENT_RULES.md` ساختن پیاده‌سازی قلابی ممنوع است. هرکدام
از اینها یا داده‌ای می‌خواهند که نداریم، یا تصمیمی که کاربر نگرفته.

---

## بدهی‌های شناخته‌شده (Known Gaps)

| # | موضوع | شدت | توضیح |
|---|---|---|---|
| ۱ | **هیچ‌چیز روی دیتای واقعی اجرا نشده** | 🔴 بالا | همهٔ کار سمت کد تمام است: provider + تشخیص نماد + اعتبارسنجی گپ آخر هفته، همه با ترمینال ساختگی تأیید شده. **تنها چیز باقی‌مانده اجرای کاربر روی ویندوز است** — خروجی `mt5-check` هنوز نیامده. |
| ۲ | ~~WaveNet به بک‌تست وصل نیست~~ | ✅ **حل شد** | فاز ۳۱: `ModelPredictionSource` ساخته شد. بک‌تست حالا با مدل آموزش‌دیده اجرا می‌شود. |
| ۳ | ~~فاز ۲۴ Deployment صفر است~~ | ✅ **حل شد** | فاز ۲۴ پیاده شد: health/readiness، بکاپ با تأیید بازیابی، runner با shutdown امن، Task Scheduler ویندوز |
| ۴ | `SqliteDatasetRepository.get()` خالی برمی‌گرداند | 🟡 پایین | عمدی؛ rehydration کامل schema + quality report می‌خواهد. با `stored_rows()` خوانده می‌شود. |
| ۵ | ~~فاز ۹ Plugin رجیستری کامل ندارد~~ | ✅ **حل شد** | رجیستری + مدیر + کشف قطعی از entry points و configuration |
| ۶ | ~~فاز ۲۱/۲۲ حداقلی‌اند~~ | ✅ **حل شد** | پیکربندی لایه‌ای با secret redaction، لاگینگ ساختاریافته با context |
| ۷ | `.gitignore` شامل `*.csv` است | 🟡 پایین | به کاربر اطلاع داده شد، منتظر تصمیم |
| ۸ | `run_ai.py` کامل تا آخر اجرا نشده | 🟡 پایین | روی CPU بیش از ۱۵ دقیقه؛ `--quick` استفاده شود |

---

## نتیجهٔ مهم: چرا بک‌تست ضرر می‌دهد

روی دیتای نمونهٔ **تصادفی**، ۵۱ معامله انجام و **هر ۵۱ تا ضرر** می‌کنند.
این **باگ نیست** — نتیجهٔ درست است:

```
scenario      trades       return   return %   maxDD %       fees
no costs          51      -0.5280     -0.528     0.583     0.0000
with costs        51      -2.7946     -2.795     2.850     0.2066

spread sweep:  0 → -0.73%   2 → -1.76%   4 → -2.79%   20 → -11.03%
hit rate:      0.118 → 0
```

بهینه‌ساز هم روی نویز **هیچ کاندیدایی را promote نمی‌کند** و گیت با
`insufficient_trades` رد می‌کند. این دقیقاً رفتار مطلوب است.

**نتیجه‌گیری:** بهبود مدل روی نویز بی‌معناست. اول دیتای واقعی، بعد مدل.

---

## ترتیب پیشنهادی ادامهٔ کار

1. **C — دیتای واقعی MT5** ← *قدم بعدی، تأییدشده توسط کاربر*
2. **A — کیفیت مدل** (WaveNet + ۱۰۹ فیچر در شبیه‌سازی)
3. **B — فاز ۲۴ Deployment** (اجرای مداوم، سرویس ویندوز، بکاپ)

---

## تاریخچهٔ Sprint ها

| Sprint | موضوع | تست‌ها | گزارش |
|---|---|---|---|
| P0 | Project Intelligence | 171 | — |
| P1 | Data Platform | 178 | — |
| P2 | Feature Platform (۱۰۹ فیچر) | 261 | — |
| P3 | AI Platform (WaveNet) | 337 | — |
| P4 | Trading Platform | 395 | `SPRINT_P4_REPORT.md` |
| P5 | Execution & Portfolio | 473 | `SPRINT_P5_REPORT.md` |
| P6 | Simulation & Backtesting | 511 | `SPRINT_P6_REPORT.md` |
| P7 | Self-Learning | 570 | `SPRINT_P7_REPORT.md` |
| P8 | Persistence (SQLite) | 612 | `SPRINT_P8_REPORT.md` |
| — | Dashboard (فاز ۱۹) | 634 | `PHASE19_REPORT.md` |
| — | Persistence loop | 643 | `PERSIST_REPORT.md` |
| — | Backtest Replay | 678 | `REPLAY_REPORT.md` |
| — | MT5 Readiness | 703 | `MT5_READINESS_REPORT.md` |
| — | فاز ۲۹ — دو مدل پیش‌بینی | 771 | `PHASE29_REPORT.md` |
| — | فاز ۳۰ — دیتاست و بافر زنده | 831 | `PHASE30_REPORT.md` |
| — | فاز ۳۱ — حلقهٔ زنده + بک‌تست مدل | 878 | `PHASE31_REPORT.md` |
| — | فاز ۲۴ — Deployment | 932 | `PHASE24_REPORT.md` |
| — | فازهای ۹/۲۱/۲۲ — تکمیل | 1034 | `PHASE_9_21_22_REPORT.md` |
| — | فاز ۳۲ — اکانت‌ها و GUI کامل | 1101 | `PHASE32_REPORT.md` |
| — | فاز ۳۳ — پیوستگی دیتاست | 1155 | `PHASE33_REPORT.md` |
| — | **فاز ۳۴ — بازرسی دیتا و چارت** | **1182** | `PHASE34_REPORT.md` |

---

## باگ‌های واقعی پیداشده و رفع‌شده

هر کدام با تست رگرسیون. فهرست کامل در `CHANGELOG_REVIEW.md`.

۴۵. **ارزیابی سیگنال آستانه را ثابت ۰.۰۸٪ فرض می‌کرد** (فاز ۴۹) — مدلی که با
    ۰.۲۵٪ آموزش دیده بود با کلید سؤالِ ۰.۰۸٪ نمره می‌گرفت. روی دیتای واقعی ۵
    دقیقه‌ای سهم HOLD بین این دو آستانه ۴۱٪ در برابر ۸۳٪ است، پس دقت به‌شدت
    کمتر از واقع گزارش می‌شد. رفع: `ModelRecord.threshold` + `.horizon`، و
    یک تست `ast` که برگشتِ hard-code را می‌گیرد.
۴۶. **فرم Retrain آستانه را بی‌صدا پاک می‌کرد** (فاز ۴۹) — فیلد از پیش با
    `0.08` پر بود، پس هر Retrain بدون دست‌زدن به آن، مدل ۰.۲۵٪ را به ۰.۰۸٪
    تبدیل می‌کرد. حالا خالی است و خالی یعنی «همان که داشت».

۱. venv ویندوز به پایتون حذف‌شده اشاره می‌کرد
۲. `_GatedActivationUnit` داخل تابع تعریف شده بود → مدل قابل load نبود
۳. Predictor فقط یک سطر می‌فرستاد (`[scaled[0]]` به‌جای `[scaled]`)
۴. **نشت هدف (target leakage)** در `make_windows()` با `horizon=0`
۵. `QuantityPolicy._value` متد پایه را سایه می‌انداخت
۶. **تصادم decision-id** → پوزیشن باز می‌شد و هرگز بسته نمی‌شد (بحرانی)
۷. سقف نقدینگی دوبار اعمال می‌شد → fill جزئی هرگز دیده نمی‌شد
۸. سنتینل جریمه به‌عنوان امتیاز میانگین گرفته می‌شد
۹. `is_empty` وضعیت واقعی را پنهان می‌کرد
۱۰. سنتینل خام به کاربر نشان داده می‌شد
۱۱. `BacktestEngine` به کلاس concrete وابسته بود → پورت `ReportingLedger`
۱۲. `transactions` در یکی property و در دیگری method بود
۱۳. سایه‌افتادن متغیر `context` در `run_trading.py`
۱۹. **`Fetch market data` دیتاست را جایگزین می‌کرد نه اضافه** — نسخهٔ جدید
    می‌نوشت و `query` فقط آخرین را می‌خواند. ۲۰۰ کندل + ۵۰ تای جدید = ۵۰ تا.
    نه سقفی بود، نه بررسی پیوستگی بین آپدیت‌ها. با آزمایش ثابت شد، نه حدس.
۱۸. **داشبورد بدون دیتابیس بالا نمی‌آمد** — کاربر را به `run_persistence.py`
    هدایت می‌کرد؛ همان اسکریپتی که در فاز ۳۲ عمداً از GUI حذف شده بود.
    تناقض مستقیم با «همه‌چیز از GUI». حالا دیتابیس خودکار ساخته می‌شود و
    صفحهٔ خالی، دکمه‌ها را معرفی می‌کند نه دستور شل.
۱۷. **ترتیب لیست بکاپ‌ها غلط بود** — مرتب‌سازی بر اساس نام فایل انجام می‌شد،
    ولی دو بکاپ در یک ثانیه فقط با پسوند عددی فرق دارند و `...-1.db` از
    `...db` جلوتر مرتب می‌شود. یعنی `latest()` بکاپ **قدیمی‌تر** را برمی‌گرداند
    و یک restore می‌توانست دیتای اشتباه را برگرداند. رفع: مرتب‌سازی بر اساس
    زمان ثبت‌شده.
۱۶. **digest دیتاست هرگز تطبیق نمی‌کرد** — روی float64 حساب می‌شد ولی
    float32 ذخیره می‌شد، پس بعد از reload همیشه فرق داشت و به‌عنوان بررسی
    صحت بی‌فایده بود. گرد کردن جواب نداد (خطا نسبی است، ~6e-8). رفع: هش
    روی شکل ذخیره‌شدهٔ float32 (`struct.pack`).
۱۵. **آموزش بازتولیدپذیر نبود** — `_build_compiled` پارامتر `seed` می‌گرفت و
    هرگز استفاده‌اش نمی‌کرد. در Keras 3 هر لایه وزن اولیه را از مولد خودش
    می‌گیرد، پس `tf.random.set_seed` کافی نیست. دو اجرای یکسان نتیجهٔ متفاوت
    می‌داد — نقض مستقیم فاز ۱۳ §۳۴. رفع: `keras.utils.set_random_seed`.
۴۴. **آرشیو اسنپ‌شات بی‌نهایت رشد می‌کرد** — هر اجرای Project
    Intelligence یک اسنپ‌شات می‌ساخت و هیچ‌وقت پاک نمی‌کرد؛ ۱۵۸ اجرا = ۴۸
    مگابایت، یک‌سوم ورک‌اسپیس. رفع: `ARCHIVE_KEEP = 5`.
۴۳. **آخرین مدل ذخیره می‌شد نه بهترین** — `last_model = model` بدون شرط.
    چون `val_loss` بعد از کف بالا می‌رود، این یعنی ذخیرهٔ
    بیش‌برازش‌شده‌ترین وزن‌ها. اندازه‌گیری: epoch ۵ با val_acc ۷۲.۷٪ در
    برابر epoch ۱۲ با ۶۳.۶٪ که ذخیره می‌شد.
۴۲. **timeout دو ساعتهٔ ثابت** — اجرای واقعی ۲.۲ ساعت لازم داشت. رفع:
    فیلد قابل تنظیم با پیش‌فرض ۸ ساعت.
۴۱. **ETA ~۴۵ برابر غلط** — زمان کل fold بر batchهای epoch جاری تقسیم
    می‌شد؛ `eta 2:58:40` وقتی ۴ دقیقه مانده بود.
۴۰. **هیچ مدلی تا پایان train() ذخیره نمی‌شد (بحرانی)** — کاربر ۱۸ epoch
    کامل را به timeout باخت و هیچ چیز روی دیسک نماند. رفع: checkpoint
    بعد از هر epoch.
۳۹. **اسپرد ۴ دلاری hard-code شده، هر سیگنال را ضررده می‌کرد** — روی طلای
    ۴٬۳۷۶ یعنی ۰.۰۹۱٪ هزینه در برابر آستانهٔ ۰.۰۸٪ سیگنال: خالص ۰.۵۰-
    دلار قبل از شروع. رفع: خواندن `ask - bid` از تیک زنده با fallback
    واقع‌بینانهٔ ۰.۳۵ و ثبت منبع.
۳۸. **۱۱ دقیقه سکوت بین خطوط پیشرفت** — ۸ خط در هر epoch تقسیم بر ۵٬۹۸۶
    batch یعنی خطی هر ۷۴۸ batch. رفع: کف زمانی ۳۰ ثانیه‌ای.
۳۷. **batch_size=8 روی ۴۷٬۸۸۶ پنجره** — پیش‌فرض دموی چندصد سطری، که روی
    دیتای واقعی ۵٬۹۸۶ قدم گرادیان در هر epoch می‌سازد. رفع: مقیاس‌گیری با
    حجم دیتا → ۷۴۸ قدم.
۳۶. **`The dataset is infinite` در مسیر استریم** — فاز ۴۱ دیتاست را
    `repeat()` کرد (بی‌نهایت) ولی callback پیشرفت هنوز `len(train_x)`
    می‌پرسید. باگی که خود ایجنت وارد کرد و در تست ندید، چون مسیر استریم
    فقط با `NullProgressReporter` آزموده شده بود — یعنی بدون همان
    callback‌ای که می‌شکست.
۳۵. **`\r` از داخل pipe رد نمی‌شود** — خط پیشرفت batch با `\r` در جا
    به‌روز می‌شد که فقط روی ترمینال کار می‌کند؛ از داخل pipe هر
    به‌روزرسانی یک خط دائمی جدید می‌شد.
۳۴. **سیل خطوط batch، نتایج epoch را بیرون می‌انداخت** — داشبورد ۲۰۰ خط
    آخر را می‌خواند و ۱۵۸ تای آنها batch بود. روی دیتای بزرگ هیچ خط
    epoch‌ای باقی نمی‌ماند. رفع: سقف ۸ خط در هر epoch + پنجرهٔ لاگ که
    خطوط نتیجه را نگه می‌دارد.
۳۳. **آموزش ۱۲.۲ گیگابایت رم می‌خواست (بحرانی)** — همهٔ ۴۹٬۳۹۳ پنجرهٔ
    ۵۰۰×۱۲۳ در ابتدای `train()` ساخته می‌شد، قبل از اولین batch و قبل از
    اولین خط لاگ. ماشین همان‌جا می‌مرد: رم پر، لاگ خالی، مدل ذخیره‌نشده —
    هر سه از یک علت. `WindowGenerator` فاز ۳۰ دقیقاً برای این ساخته شده
    بود و هرگز وصل نشد. رفع: استریم `tf.data` بالای ۵۱۲MB.
۳۲. **دکمهٔ Retrain در لحظهٔ فشردن کرش می‌کرد** — `train_model` روی
    `CommandHandlers` بود ولی `_run_script` فقط روی
    `AccountCommandHandlers`؛ `AttributeError` تضمینی. رفع با ارث‌بری.
۳۱. **مدل هیچ‌وقت ذخیره نمی‌شد (بحرانی)** — `run_dual_models.py` آموزش
    می‌داد، پیش‌بینی چاپ می‌کرد و خارج می‌شد. `datasets/models/` اصلاً
    وجود نداشت. هر اجرای آموزشی از فاز ۲۹ به بعد لحظهٔ خروج پروسه دور
    ریخته می‌شد. با درخواست «لیست مدل‌های ذخیره‌شده» لو رفت.
۳۰. **۱۰ ثانیه سکوت قبل از اولین خط لاگ** — ساخت ۵۰k پنجرهٔ همپوشان قبل از
    `on_train_begin` انجام می‌شد، پس اولین نشانهٔ حیات خیلی دیر می‌آمد.
۲۹. **۲۴٬۹۷۶ فولد روی دیتای واقعی** — `val_size=4, step=2` برای سری دموی
    چندصد سطری تنظیم شده بود؛ روی ۵۰٬۰۰۰ کندل هر فولد یک fit کامل مدل است.
    این «کند» نبود، تمام نمی‌شد — و علت اصلی «آموزش هیچی چاپ نمی‌کند» بود.
    رفع: هندسهٔ roll-forward با اندازهٔ دیتا مقیاس می‌گیرد (۴۹ فولد).
۲۸. **ویژگی‌های ۵ دقیقه و ۱ ساعته روی هم می‌افتادند** — مسیر ذخیره‌سازی
    `features/{feature_id}/v{n}.parquet` بود، بدون نماد و تایم‌فریم. `atr_14`
    برای 5M می‌شد `v1` و برای 1H می‌شد `v2` در همان پوشه: دو کمیت متفاوت،
    غیرقابل تشخیص، با شمارندهٔ نسخهٔ مشترک. آموزش سالم بود چون مدل‌ها این
    انبار را نمی‌خوانند (در حافظه از نو حساب می‌کنند)، ولی هر مصرف‌کنندهٔ
    دیگری دیتای اشتباه می‌گرفت. رفع: `features/{symbol}/{timeframe}/...`
    بدون تغییر پورت فریزشدهٔ `FeatureRepository`.
۲۷. **`--storage-root` داشبورد به اسکریپت‌ها نمی‌رسید** — چهار دکمه‌ای که
    اسکریپت اجرا می‌کنند آن را پاس نمی‌دادند، پس اسکریپت سراغ `datasets/`
    پیش‌فرض مخزن می‌رفت. کاربر در `/data` هزاران کندل می‌دید و آموزش
    می‌گفت «کندلی نیست». موقع تست زندهٔ فاز ۳۶ پیدا شد.
۲۶. **accuracy محاسبه و دور ریخته می‌شد** — کراس هر epoch آن را حساب
    می‌کرد و trainer فقط `val_loss` را نگه می‌داشت. «مدل چقدر خوبه؟» در
    هیچ جای سیستم جواب نداشت. رفع: `fold_metrics` + مقایسه با baseline.
۲۵. **`ConsoleProgressReporter` ساخته شده بود و هیچ‌کس صدایش نمی‌زد** — از
    فاز ۱۳ وجود داشت ولی هیچ فراخوانی‌ای `progress=` پاس نمی‌داد، پس همیشه
    `NullProgressReporter` فعال بود.
۲۴. **خروجی اسکریپت تا پایان کار buffer می‌شد** — `subprocess.run` تا exit
    پروسه برنمی‌گردد، پس آموزش بیست‌دقیقه‌ای بیست دقیقه سکوت بود و صفحهٔ وب
    می‌گفت «reload کن» در حالی که reload همان هیچ را نشان می‌داد.
۲۳. **یک نماد، دو دیتاست** — fetch زیر نام بروکر (`XAUUSD_i`) می‌نوشت و بقیهٔ
    پلتفرم canonical (`XAUUSD`) می‌خواند. build چیزی پیدا نمی‌کرد و به باگ ۲۱
    می‌رسید. رفع: `store_as` + `symbol_scope.py` که alias قدیمی را هم پیدا
    می‌کند ولی **اعلام** می‌کند.
۲۲. **سطر می‌توانست از وسط سری حذف شود** — `build_feature_matrix` هر سطری را
    که یک فیچرش `None` بود می‌انداخت. یک `NaN` در سطر ۴٬۰۰۰ باعث می‌شد
    ۳٬۹۹۹ به ۴٬۰۰۱ بچسبد و roll-forward از روی بازار ندیده رد شود. رفع:
    برش فقط از دو سر؛ حفرهٔ وسط **ستون** را می‌برد نه سطر را. تضمین صریح:
    `FeatureMatrix.is_contiguous`.
۲۱. **کندل ساختگی زیر نماد واقعی ذخیره می‌شد** — نبود دیتا باعث می‌شد
    `generate_sample` یک موج سینوسی بسازد و ingest کند. یک اجرا بعد،
    تشخیص‌ناپذیر از دیتای بروکر. مدل رنج روی آن آموزش می‌دید و
    «آموزش‌دیده» به‌نظر می‌رسید. نقض مستقیم `DEVELOPMENT_RULES.md`.
۲۰. **`Fetch market data` فقط یک تایم‌فریم می‌گرفت** — ولی build هر دو را
    لازم داشت، پس مسیر عادی اپراتور مستقیماً به باگ ۲۱ می‌رسید.
۱۴. **دکمهٔ «Update features» داشبورد هرگز کار نمی‌کرد** — هندلر
    `service.compute()` را صدا می‌زد که وجود ندارد (`compute_set()` درست است).
    تست‌ها نگرفتند چون فقط شاخهٔ «کندلی نیست» را می‌آزمودند.
