# گزارش Sprint P7 — Self-Learning & Optimisation

**تاریخ:** ۲۰۲۶-۰۸-۱۶
**فاز:** Phase 28 — Implementation Foundation
**مرجع معماری:** `docs/Phases/Phase17.md`

---

## چه چیزی ساخته شد

```
ParameterSpace -> Candidates
                      |
               جستجوی in-sample        <- پارامترها اینجا انتخاب می‌شوند
                      |
               foldهای walk-forward    <- اینجا قضاوت می‌شوند
                      |
                PromotionGate          <- فقط شواهد out-of-sample
                      |
        ارتقا / رد -> LearningMemory
```

### دامنه — `src/ShadBotTrader/domain/learning/`

| فایل | محتوا |
|---|---|
| `learning_types.py` | ۶ enum: ExperimentStatus، CandidateStatus، RejectionReason، ... |
| `parameter_space.py` | `ParameterGrid`، `ParameterSpace`، `CandidateConfiguration` |
| `objective.py` | ۴ تابع هدف + `is_penalty` (نگهبان مقادیر بی‌اعتبار) |
| `candidate.py` | `Candidate`، `EvaluationRecord`، `best_candidate` |
| `promotion.py` | `PromotionPolicy`، `PromotionVerdict`، `PromotionGate` |
| `experiment.py` | `DataWindow`، `WalkForwardPlan`، `LearningExperiment` |
| `ports.py` | ۵ قرارداد انتزاعی |
| `events.py` | ۱۰ رویداد دامنه |

### زیرساخت — `src/ShadBotTrader/infrastructure/learning/`

| کلاس | نقش |
|---|---|
| `GridSearchGenerator` | شمارش کامل شبکه (با سقف اختیاری) |
| `RandomSearchGenerator` | نمونه‌برداری تصادفی بازتولیدپذیر |
| `BacktestCandidateEvaluator` | امتیازدهی از طریق Simulation Platform |
| `WalkForwardOptimizer` | جستجو → اعتبارسنجی → دروازه |
| `InMemoryLearningMemory` | حافظه‌ی بردها و شکست‌ها |
| `ConsoleOptimisationReporter` | گزارش خوانا |

---

## طراحی ضدِ overfitting — اصل کار

| مرحله | داده | نقش |
|---|---|---|
| ۱. جستجو | in-sample | فقط تعیین می‌کند **کدام** کاندیدا ارزش اعتبارسنجی دارد |
| ۲. اعتبارسنجی | foldهای out-of-sample | تنها منبع رتبه‌بندی |
| ۳. دروازه | out-of-sample | مقایسه با baseline + محدودیت‌های مطلق |

یک جستجو که بر اساس in-sample رتبه‌بندی کند، **قابل‌اعتماد** پیکربندی‌هایی
«کشف» می‌کند که پنجره‌ی آموزش را حفظ کرده‌اند. این یکی نمی‌تواند.

### تست تله

`RiggedEvaluator` عمداً یک تله می‌کارد:

- `lookback=1` → امتیاز in-sample **۱۰۰**، out-of-sample **-۲۰**
- `lookback=2` → امتیاز **۲** در هر دو

تست `test_the_in_sample_star_does_not_win` تأیید می‌کند برنده `lookback=2`
است، نه ستاره‌ی in-sample. اگر روزی کسی رتبه‌بندی را به in-sample تغییر دهد،
این تست می‌شکند.

### دروازه چه چیزهایی را رد می‌کند

| دلیل | شرط |
|---|---|
| `WORSE_THAN_BASELINE` | out-of-sample از incumbent بهتر نیست |
| `INSUFFICIENT_TRADES` | معامله‌ی کافی برای قضاوت نبوده |
| `FAILED_VALIDATION_FOLD` | تعداد fold کمتر از حداقل |
| `EXCESSIVE_DRAWDOWN` | افت سرمایه از حد گذشته |
| `NEGATIVE_RETURN` | بازده تجمعی out-of-sample منفی |
| `UNSTABLE_OUT_OF_SAMPLE` | فقط یک fold خوش‌شانس مثبت بوده |
| `OVERFIT_SUSPECTED` | فاصله‌ی in/out از حد گذشته |

---

## 🐞 باگ آماری که پیدا و رفع شد

### میانگین‌گیری از مقدار نگهبان

`RiskAdjustedObjective` برای اجرایی با معاملات خیلی کم مقدار **-۱,۰۰۰,۰۰۰**
برمی‌گرداند — یک **نگهبان (sentinel)** به معنای «شواهد کافی نیست»، نه یک نمره.

ولی `out_of_sample_score` از foldها میانگین می‌گرفت:

```
میانگین(-1000000, -0.4, -0.5) = -333333.63
```

خروجی دمو این بود:

```
out-of-sample -333333.4902 (gap 333332.8493)
```

این عدد از نظر حسابی درست و از نظر آماری **کاملاً بی‌معنا** است. بدتر:
`overfit_gap` را هم بی‌اثر می‌کرد، چون تفاضل یک نمره‌ی واقعی از یک نشانگر
هیچ چیز را اندازه نمی‌گیرد.

**رفع:**

- `PENALTY_THRESHOLD` و تابع `is_penalty()` اضافه شد.
- نگهبان **منتشر می‌شود، رقیق نمی‌شود**: اگر هر fold بی‌اعتبار باشد، کل
  کاندیدا بی‌اعتبار است.
- `overfit_gap` در برابر نگهبان `None` برمی‌گرداند.
- دروازه چنین کاندیدایی را با `INSUFFICIENT_TRADES` رد می‌کند.

خروجی الان صادقانه است:

```
REJECTED (insufficient_trades)
1/3 validation fold(s) produced too little activity to judge
```

۵ تست رگرسیون در `TestPenaltySentinels` اضافه شد.

---

## مرز معماری: یادگیری پیشنهاد می‌دهد، اجرا نمی‌کند

طبق Phase 17، Self-Learning **مستقیماً Live Trading را تغییر نمی‌دهد**.

دو تست این را تضمین می‌کنند:

- `test_self_learning_cannot_reach_live_execution` — نتیجه‌ی بهینه‌سازی هیچ
  سطح اجرایی (venue، ledger، order، broker) ندارد
- `test_a_promoted_candidate_is_only_a_configuration` — کاندیدای ارتقایافته
  متد `apply` یا `deploy` ندارد؛ فقط یک dict پارامتر است

---

## نتیجه‌ی واقعی روی دیتای نمونه

```
=== Promotion gate ===
  REJECTED (insufficient_trades)
  1/3 validation fold(s) produced too little activity to judge

=== Learning memory ===
  candidates remembered : 10
  rejected              : 1
  promoted              : 0
      insufficient_trades        1
```

⚠️ **هیچ کاندیدایی ارتقا نیافت — و این درست است.**

دیتاست نمونه تصادفی تولید شده و الگوی واقعی ندارد. سیستمی که روی نویز
یک «برنده» پیدا می‌کرد، دقیقاً همان چیزی بود که این sprint برای جلوگیری
از آن ساخته شد.

رد شدن، رفتار موفق است.

---

## وضعیت کیفیت

| بررسی | نتیجه |
|---|---|
| `black --check .` | ✅ ۲۹۹ فایل |
| `ruff check .` | ✅ پاس |
| `mypy src` | ✅ ۲۲۷ فایل |
| `pytest` | ✅ **۴۶۷ passed, 6 skipped** |
| `RUN_TF=1 pytest` | ✅ **۴۷۳ passed** |

**رشد تست‌ها:** ۳۹۵ → **۴۷۳** (۷۸ تست جدید)

- ۵۴ تست دامنه‌ی یادگیری (فضای پارامتر، اهداف، کاندیدا، walk-forward، دروازه)
- ۲۴ تست یکپارچگی (شامل تله‌ی overfitting و مرز معماری)

---

## دستورات جدید

```bash
python scripts/run_optimisation.py
python scripts/run_optimisation.py --demo-overfit
python scripts/run_optimisation.py --random 8 --folds 4 --objective sharpe

shadbot-learn objectives
shadbot-learn policy
shadbot-learn optimise --folds 3 --top 5
```

---

## آنچه عمداً ساخته نشد

Phase 17 فهرست بلندی دارد؛ این sprint هسته‌ی حلقه را ساخت، نه همه‌چیز را:

- **Champion/Challenger و Shadow Mode** — نیاز به اجرای موازی زنده دارند
- **Drift Detection و Retraining Trigger** — نیاز به پایش تولید دارند
- **Bayesian optimisation** — grid و random پیاده شدند؛ TPE/GP نیاز به
  وابستگی جدید دارد و بدون داده‌ی واقعی ارزشی اضافه نمی‌کند
- **بهینه‌سازی هایپرپارامتر مدل WaveNet** — فعلاً پارامترهای استراتژی و
  ریسک تنظیم می‌شوند، نه معماری شبکه
- **ذخیره‌سازی پایدار** — حافظه و مخزن آزمایش‌ها in-memory هستند

هیچ‌کدام را به‌صورت قلابی نساختم.

---

## مرحله‌ی بعدی — دو گزینه

### گزینه A — Sprint P8: Persistence & Project Intelligence (فازهای ۱۸، ۲۰)

همه‌چیز الان in-memory است. دیتاست‌ها، مدل‌ها، ژورنال‌ها و آزمایش‌ها با
هر اجرا از بین می‌روند. ذخیره‌سازی پایدار (SQL Server طبق فاز ۲۰) پیش‌نیاز
هر استفاده‌ی جدی است.

### گزینه B — داده‌ی واقعی بازار

مهم‌ترین محدودیت فعلی این است که همه‌چیز روی **داده‌ی تصادفی** اجرا می‌شود.
یک provider واقعی (MetaTrader5 پشت همان `MarketDataProvider` موجود) باعث
می‌شود بک‌تست و بهینه‌سازی معنای واقعی پیدا کنند.

**پیشنهاد من گزینه B است.** زیرساخت آماده است؛ چیزی که کم است داده‌ی
واقعی است. بدون آن، بهینه‌سازی روی نویز اجرا می‌شود و هیچ‌وقت چیزی
ارتقا نخواهد یافت.
