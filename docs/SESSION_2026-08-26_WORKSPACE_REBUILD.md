# SESSION — 2026-08-26 (جلسهٔ دوم) · کلون ورک‌اسپیس + پاکسازی + بازخوانی کامل Docs و کد

> **هدف این سند:** ثبت دقیق کارِ این جلسه طبق `AGENTOPERATINGRULE.md`
> (قاعدهٔ CHAT HANDOFF RULE) تا پروژه فقط از روی «کد + مستندات وضعیت» قابل
> بازیابی باشد. از این جلسه به بعد **هر کاری که انجام شود در `docs/` ثبت می‌شود**.
>
> سندهای مرتبط: `SESSION_2026-08-26.md` (جلسهٔ اول امروز) ·
> `Report/SESSION_2026_08_26.md` · `STATUS_AUDIT_2026-08-26.md` ·
> `PROJECT_UNDERSTANDING.md`

---

## ۱. کلون و پاکسازی ورک‌اسپیس

**چه شد:** پروژه از `https://github.com/DeadBotKing/ShadBotTrader` با
clone کم‌عمق (`--depth 1`) در `/home/user/ShadBotTrader` کلون شد.

```text
بعد از کلون    : 16 MB  (شامل .git کم‌عمق = 2.2 MB)
بعد از پاکسازی : 12 MB
```

### تغییرات این جلسه (تفاوت با جلسهٔ اول امروز)

| آیتم | قبل | بعد | دلیل |
|---|---|---|---|
| `project_state/archive/` | 3.5 MB · ۱۶۰ پوشهٔ اسنپ‌شات قدیمی | حذف شد | اسنپ‌شات‌های تکراری تاریخ‌دار؛ نسخهٔ فعلی در `generated/` می‌ماند. (باگ ۴۴: `ARCHIVE_KEEP=5` روی این ۱۶۰ تا اجرا نشده بود) |
| `datasets/models/*/v*_architecture.txt` | 3 فایل (~80 KB) | حذف · ساختار پوشه با `.gitkeep` ماند | خروجی auto-generated از `model.summary()` — قابل تولید مجدد |
| `out.html` | 9 KB | حذف شد | خروجی generated موقت در ریشه |
| `__pycache__` | چند مورد | پاک شد | کش تولیدشده |
| `.git/` | — | **نگه داشته شد** (2.2 MB کم‌عمق) | برخلاف جلسهٔ اول؛ برای مدیریت نسخه در ورک‌اسپیس |
| `legacy/` | 2.2 MB | نگه داشته شد | انتخاب کاربر (جلسهٔ اول) |
| `docs/` | 3.2 MB | کامل | مرجع اصلی درک پروژه |

**نتیجه:** 12 MB · src=317 فایل/47,505 خط · tests=123 فایل/21,236 خط

---

## ۲. بازخوانی Docs — اسنادی که در این جلسه کامل خوانده شد

`STATUS_AUDIT_2026-08-26.md` · `CURRENT_STATE.md` · `AGENTOPERATINGRULE.md` ·
`Handoff.md` (Master Handoff فریزشدهٔ فاز ۲۶) · `IMPLEMENTATION_STATUS.md` ·
`SESSION_2026-08-26.md` · `Report/SESSION_2026_08_26.md` ·
`Report/PHASE57_58_REPORT.md` · `PROJECT_UNDERSTANDING.md` ·
`WORKLOG.md` (انتها) · `README.md` و `PROJECT_STATE.md` (سرآغاز) ·
`DEVELOPMENT_RULES.md` (سرفصل‌ها) · `DUAL_MODEL_BACKTEST.md` ·
`docs/README.md` (سرآغاز)

### جمع‌بندی درک از پروژه (خلاصهٔ یک‌نگاهی)

- **ShadBotTrader** = پلتفرم معاملاتی AI سازمانی (Python · Clean Architecture + DDD ·
  Dependency Inversion · Event-Driven · Domain مستقل از Infrastructure).
- **کجای کاریم:** فازهای **۵۷/۵۸** — بهینه‌سازی مدل‌های دوگانه برای سوددهیِ
  بکتست طلا (XAUUSD، بروکر Alpari: spread=0.06%، commission=0).
- **زنجیرهٔ ترید دومدلی:** پنجرهٔ 5M(300) → سیگنال BUY/SELL + confidence →
  گیت اطمینان → پنجرهٔ 1D(150) → range مدل seq2seq horizon=1 → high/low فردا →
  براکت TP/SL (SL ± spread · R/R با `reward_risk_multiplier` در bracket) →
  ورود next-open با typical price → خروج کندل‌به‌کندل (stop-first) → PnL.
- **گیتهای استراتژی:** session filter (فاز ۵۲) · موجود بودن هر دو forecast ·
  اطمینان · انسجام range · کف هزینهٔ حرکت · حداقل فاصلهٔ SL.
- **وضعیت Quality Gate (طبق مستندات):** 1449 passed · 0 failed · 49 skipped
  (TensorFlow) · ruff/black سبز. ۲۹ تست کهنه با کد فازهای ۵۲–۵۸ همگام شده.
- **وضعیت مدل‌ها:** signal v1 (~65-80% val_acc) · range_1d v3 (val_mae=0.000010) —
  ولی بکتست هنوز `trades=0` می‌دهد → نیاز به آموزش بهتر/تنظیم آستانه.
- **قواعد حاکم:** کد = واقعیت؛ مستندات قدیمی = نیت طراحی. هیچ placeholder
  و redesign بدون اجازه. Quality Gate قبل از هر پایان کار. ثبت وضعیت بعد از
  هر تغییر مهم.

---

## ۳. بازبینی کد — فایل‌های کلیدی که این جلسه کامل خوانده شد

| فایل | نقش | نکتهٔ بررسی |
|---|---|---|
| `infrastructure/ai/model_roles.py` | تعریف دو نقش مدل | Range: 1D/window=150/n_layers=4/seq2seq · Signal: 5M/window=300/n_layers=5 (RF=249) — هماهنگ با فاز ۵۶/۵۸ ✅ |
| `infrastructure/trading/dual_model_strategy.py` | ۷ گیت ورود | گیت R/R حذف شده (فاز ۵۲)؛ جایگزین: `reward_risk_multiplier` در bracket ✅ |
| `application/services/dual_model_backtest_service.py` | composition root بکتست | باگ‌های فاز ۵۷ رفع شده: `_active_config` + `self._configuration.spread` ✅ · pad/trim ماتریس فیچر |
| `infrastructure/simulation/dual_model_prediction_source.py` | علیت دو-تایم‌فریمی | فقط کندل بسته‌شده دیده می‌شود؛ 1H/1D فقط بعد از close؛ spread → `from_model_levels` (فاز ۵۷) ✅ |
| `domain/simulation/bracket.py` | براکت TP/SL | گسترش SL با spread (BUY: low−spread) · R/R با multiplier · `trigger` با نیم‌اسپرد و stop-first ✅ |
| `infrastructure/ai/dual_predictor.py` | inference دومدلی | خروجی seq2seq `[window, horizon*2]` و fallback scalar هر دو پشتیبانی می‌شود ✅ |
| `domain/ai/prediction_target.py` | قرارداد target/forecast | باینری SELL/BUY؛ HOLD فقط تصمیم strategy ✅ |
| `infrastructure/ai/target_builder.py` | ساخت label | `build_range_labels_seq2seq` + first-passage باینری ✅ |
| `infrastructure/ai/wavenet/wavenet_trainer.py` | آموزش (44KB) | ساختار کلاس‌ها بررسی شد: checkpoint هر epoch، resume، seq2seq targets، Loss سه‌گانه |
| `infrastructure/simulation/backtest_engine.py` | موتور بکتست | ورود با typical price (O+H+L+C)/4 — فاز ۵۷ ✅ |
| `scripts/run_dual_models.py` | CLI آموزش | آپشن‌های `--model signal/range`، `--window`، `--resume` و... |

### بررسی سلامت

- `python -m compileall src tests scripts` → **EXIT 0** (صفر خطای syntax در کل کدبیس).
- آمار مستقل: src=317 فایل/47,505 خط — **دقیقاً برابر** `Statistics.json` ✅
  (تست‌ها 123 فایل/21,236 خط — کمی جلوتر از عدد ثبت‌شدهٔ 121/21051)
- ساختار لایه‌ها: core(16 فایل) · domain(102) · application(25) ·
  infrastructure(127) · presentation(15) · project(19)

---

## ۴. یافته‌های این جلسه

1. **Typo در `.gitignore`:** خط `config.inirun_logs/` — newline بین
   `config.ini` و `run_logs/` افتاده؛ یعنی الگوی `config.inirun_logs/` هیچ
   فایلی را ignore نمی‌کند و `run_logs/` هم بی‌جهت دوبار آمده (یک بار درست).
   پیشنهاد: تبدیل به دو خط `config.ini` و `run_logs/`.
2. **دریفت کوچک آمار تست:** `PROJECT_UNDERSTANDING.md` می‌گوید 121 فایل تست/
   21051 خط؛ مقدار واقعی 123/21,236 است (احتمالاً تست‌های جدید فاز ۵۷/۵۸
   اضافه شده). در بهروزرسانی بعدی مستندات اصلاح شود.
3. **`project_state/generated/*` کهنه است** (تا فاز ۵۰) — همان گفتهٔ
   STATUS_AUDIT؛ اولویت ۲ از لیست اقدامات.
4. **`.gitignore` فیلترهای سنگین دارد:** `*.json`، `*.png`، `*.csv`،
   `*.parquet` سراسری ignore می‌شوند — عمدی است ولی باید موقع push دیتا/گزارش حواس
   جمع باشد (مثلاً `v1_training.json` مدل‌ها نیاز به `!` استثنا دارند).

---

## ۵. وضعیت «کجای کاریم» — پایان این جلسه

```text
کد        : فاز ۵۷/۵۸ کامل و سالم (compile ✅ · آمار ✅ · ساختار ✅)
مدل‌ها    : signal v1 + range_1d v3 آموزش دیده‌اند ولی بکتست trades=0
ورک‌اسپیس : 12 MB پاکسازی‌شده · docs کامل · .git کم‌عمق نگه داشته شد
مستندات   : وضعیت تا فاز ۵۸ ثبت است (STATUS_AUDIT + PHASE57_58_REPORT)
```

### گام‌های بعدی (به ترتیب پیشنهادی — از CURRENT_STATE و STATUS_AUDIT)

1. **آموزش signal با window=300** و **آموزش range با seq2seq** (روی Colab GPU —
   دستورها در `CURRENT_STATE.md`).
2. **بکتست با مدل‌های جدید** → هدف: `trades > 0` → بعدش فعال‌کردن session filter.
3. **بهروزرسانی `project_state/generated/*`** (کهنه تا فاز ۵۰).
4. اصلاح‌های ریز مستندات (بند ۴ همین سند) + typo گیت‌ایگنور.

---

*ورودی بعدی هر جلسه در همین فایل یا `SESSION_<تاریخ>.md` جدید ثبت می‌شود؛
تغییرات مهم کد علاوه بر آن در `WORKLOG.md` و `IMPLEMENTATION_STATUS.md` می‌آید.*

---

## ۶. ادامهٔ جلسه — تحلیل لاگ آموزش Signal v2 (دیتای واقعی MT5)

**چه شد:** کاربر آموزش `gold_signal_5m v2` را روی ویندوز با دیتای واقعی
(50k کندل 5M، threshold=0.6%، window=300، LR=3e-4، resume) اجرا کرد؛ لاگ
میانی بررسی شد. تحلیل کامل در
`docs/Report/SIGNAL_TRAINING_LOG_REVIEW_2026-08-26.md` ثبت شد.

**جمع‌بندی:** resume/best-keep/استریم همگی سالم ✅ · یافتهٔ اصلی:
استخر لیبل فقط ~6,150 پنجره از 34,661 است (threshold 0.6% → 17.8% لیبل‌دار)
· val فقط 123 نمونه → val_acc 61% هنوز از نظر آماری قابل تفکیک از
baseline (54.5%) نیست · امضای بیش‌برازش (train 76% vs val 61%) در جریان —
EarlyStopping/best-keep محافظت می‌کنند · پیشنهاد: پایان اجرا → ارزیابی
holdout 30% → A/B با threshold دیگر → folds بیشتر برای val کم‌نویزتر.

### ادامهٔ همین جلسه — اجرای کامل signal v1 (10:22:30) → تحلیل + **فاز ۶۰**

**چه شد:** کاربر اجرای ۴ فولد × ۶۰ epoch را فرستاد. فاز ۵۹ در عمل تأیید شد
(val=702=10.0%) و best-keep نجات‌دهنده بود (epoch 19 نگه داشته شد نه 60).
اما تحلیل لاگ **باگ فاز ۶۰** را لو داد: ReduceLR + EarlyStopping به‌خاطر
`loss=None` در سیم‌کشی، هرگز به مدل سیگنال وصل نبودند → ~۷ ساعت epoch
نامنتخاب‌پذیر اجرا شد. رفع شد + baseline حکم QUALITY اصلاح شد (فولد آخر
65.2% sell داشت، نه 50.3%). تحلیل کامل اجرا:
`Report/SIGNAL_V1_FULLRUN_REVIEW_2026-08-26.md` · گزارش فاز:
`Report/PHASE60_REPORT.md`. Quality Gate: **1458 passed · 0 failed**.

### ادامهٔ همین جلسه — گزارش مشکل val از کاربر → **فاز ۵۹**

**چه شد:** کاربر کشف کرد با train-ratio 80% لیبل ولید ۱۴۰ می‌شود و با 20%
فقط ۳۴ — «اشتباه در ساخت دیتای ولید». ریشه‌یابی: فرمول `rows // 50` (۲٪
استخر لیبل) + coupling با train-ratio. **اصلاح شد** (پیش‌فرض ۱۰٪ + گارد +
`--val-size`/`--val-ratio` + چاپ صریح). جزئیات کامل:
`Report/PHASE59_REPORT.md` · ورودی WORKLOG: «فاز ۵۹». Quality Gate سبز:
**1456 passed · 0 failed · 49 skipped** + ruff/black.

### تصمیم — resume یا اجرای تازه؟ (پرسش کاربر بعد از فاز ۶۰)

**پاسخ: اجرای تازه بدون `--resume`.** دلایل (از کد):
1. اجرای قبلی کامل شده؛ resume فقط برای نجات اجرای نصفه‌کاره است. v1 فعلی
   = بهترین weights (epoch 19) — resume از همین warm-start می‌کند ولی
   `training.json` می‌گوید epochs=60 → با `--epochs 25` جواب می‌دهد
   «Nothing to do».
2. با `--epochs` بزرگ‌تر، warm-start همهٔ فولدها از وزن‌های فولد ۴ یعنی
   فولدهای ۱–۳ دادهٔ ولیدشان را در آموزشِ فولد ۴ دیده‌اند (expanding) →
   آلودگی اعتبارسنجی و best-keep سوگیرانه.
3. هدف فاز ۶۰ (ReduceLR + ES از epoch صفر) فقط در مسیر تازه معنا دارد —
   مخصوصاً برای بهبود کالیبراسیون (نقطه‌ضعف مدل فعلی).
4. ریسک صفر: best-keep اجازه نمی‌دهد اجرای بدتر v1 را بازنویسی کند.
