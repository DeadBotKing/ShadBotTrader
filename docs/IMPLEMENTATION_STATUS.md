# IMPLEMENTATION STATUS — ممیزی فاز به فاز

**سند مرجع پیشرفت پروژه.** بعد از هر Sprint به‌روزرسانی می‌شود.

- **آخرین به‌روزرسانی:** 2026-08-16
- **آخرین کار انجام‌شده:** **فاز ۳۲** — پروفایل چند-اکانتی، نگاشت نماد per-broker، همهٔ ران‌ها در GUI
- **وضعیت Quality Gate:** ✅ `black` · `ruff` · `mypy (283 files)` · `pytest 1101 passed, 12 skipped`
- **تعداد فایل منبع:** ۲۸۳ · **فایل تست:** ۸۱
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
| — | **فاز ۳۲ — اکانت‌ها و GUI کامل** | **1097** | `PHASE32_REPORT.md` |

---

## باگ‌های واقعی پیداشده و رفع‌شده

هر کدام با تست رگرسیون. فهرست کامل در `CHANGELOG_REVIEW.md`.

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
۱۴. **دکمهٔ «Update features» داشبورد هرگز کار نمی‌کرد** — هندلر
    `service.compute()` را صدا می‌زد که وجود ندارد (`compute_set()` درست است).
    تست‌ها نگرفتند چون فقط شاخهٔ «کندلی نیست» را می‌آزمودند.
