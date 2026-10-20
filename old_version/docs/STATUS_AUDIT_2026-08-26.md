# STATUS AUDIT — 2026-08-26 · «دقیقاً کجای کاریم؟» + کشف کارهای ثبتنشده

> **هدف این سند:** نتیجهٔ بازبینی ریزِ همهٔ کدها + اجرای تست + تشخیص اختلاف
> «کد واقعی ↔ مستندات». طبق `AGENTOPERATINGRULE`، **کد واقعیت است** و این سند
> هر جا مستندات عقباند را صادقانه ثبت میکند.

---

## ۱. نتیجهٔ اجرای تست — ۲۹ شکست (همگی تستِ کهنه)

```
1415 passed · 29 failed · 49 skipped
```

**مهم:** هر ۲۹ شکست از **تستهای کهنهای** است که با تغییراتِ عمدیِ کد
(فازهای ۵۰–۵۸) همگام نشدهاند — **باگِ واقعی نیستند**. کد سالم است
(۳۱۶ ماژول بدون خطا import میشوند).

### دستهبندی شکستها بر اساس علت

| دسته | فایل(ها)ی شکستخورده | علت (تغییر عمدی کد) |
|---|---|---|
| **تعداد فیچر ۱۰۹ → ۲۲۷** | `test_feature_cache`، `test_feature_pipeline`، `test_feature_visibility`، `test_stored_matrix_identity`، `test_training_dataset`، `test_invariance_audit`، `test_commands`، `test_evaluate_and_inspect` | کاتالوگ استاندارد از ۱۰۹ به **۲۲۷** فیچر گسترش یافته (مدیریت شده با `model_scope`) |
| **Range 1H → 1D** | `test_dual_models` (ModelRoles) | فاز ۵۶ پیشفرض مدل رنج را عمداً به 1D تغییر داد |
| **حذف گیت R/R در Strategy** | `test_dual_model_strategy`، `test_live_decision` | فاز ۵۲ گیت reward/risk را از Strategy حذف کرد (چون entry_price در لحظهٔ تصمیم معلوم نیست؛ اکنون در Bracket با `reward_risk_multiplier` اجرا میشود) |
| **فرمت خروجی Progress** | `test_training_progress`، `test_progress_visibility`، `test_training_visibility`، `test_training_pace` | فاز ۵۳/۵۴ قالب گزارش آموزش را تغییر داد (val_mae، دلار، ETA) |

---

## ۲. خلأ مستندات — «خیلی کارا کردیم که ثبت نشد»

### مشکل در یک جمله
**کد در فاز ۵۸ است؛ مستنداتِ وضعیت فقط تا فاز ۴۹/۵۰ ثبتاند.**

| بخش | وضعیت |
|---|---|
| گزارشهای فاز در `docs/Report/` | تا **PHASE56** موجود ✅ |
| سندهای فاز در `docs/Phases/` | فقط تا **Phase49** |
| `WORKLOG.md` | فقط تا فاز ۴۹ + دو ورودی ۱۹/۲۰ آگست (LR search / binary signal) |
| `IMPLEMENTATION_STATUS.md` | بهروز تا فاز ۵۰ (غیر از اضافههای بعدی) |
| `project_state/generated/*` | کهنه (تا فاز ۵۰) |
| **فازهای ۵۷ و ۵۸** | **در هیچ سندی ثبت نشدهاند** — فقط در کامنتهای کد |

### فازهایی که «انجام شده ولی در WORKLOG/IMPLEMENTATION_STATUS ثبت نشدهاند»

- **فازهای ۵۰–۵۶:** گزارش در `docs/Report/` دارند ولی در `WORKLOG.md` و
  `IMPLEMENTATION_STATUS.md` و `docs/Phases/` **نیستند**.
- **فازهای ۵۷–۵۸:** در هیچ جایی ثبت نشدهاند (فقط در کد).

---

## ۳. خلاصهٔ فازهای ثبتنشده (بر اساس کد + گزارشهای Report)

### فاز ۵۰ — تحلیل Range v1 + رفع باگ `loss_function` در save_model
- تحلیل `v1_training.json` (window=150, feature_columns=182, val_mae≈±4.64$).
- رفع: `loss_function=role.loss` به `ModelRecord` اضافه شد.
- Colab: سلولهای بررسی نتیجه و ادامهٔ آموزش.

### فاز ۵۱ — Resume Training (`--resume`)
- ادامهٔ آموزش از checkpoint بعد از قطعی اینترنت/Colab.
- `_load_resume_weights` + `initial_epoch` + warm-start آخرین fold.

### فاز ۵۲ — فیلتر Session + حداقل فاصلهٔ SL
- `DEFAULT_GOOD_HOURS_UTC = {2,5,6,10,14,15,16,18}` (WR 33.5% → ~55%).
- گیت ۰ (session filter) و گیت ۷ (min SL distance) در `DualModelStrategy`.

### فاز ۵۳ — بهبود Progress Reporter
- نمایش `val_mae` و معادل دلاری، جداسازی range/signal، ۳ خط batch در epoch.

### فاز ۵۴ — Loss سهگانه + AdamW + ReduceLROnPlateau
- Loss ترکیبی Huber+MAE+MSE (وزن ۳:۶:۱) برگرفته از `legacy/TimeSeriesPrediction2.py`.
- `AdamW` (weight_decay) + `ReduceLROnPlateau`.

### فاز ۵۵ — Range Model Seq2Seq (رفع collapse)
- خروجی `[batch, window, horizon*2]` بهجای `[batch, 2]`؛ gradient بسیار قویتر.
- Loss seq2seq-aware (۴۰٪ کل + ۶۰٪ آخرین timestep).
- `target_builder.build_range_labels_seq2seq()`.

### فاز ۵۶ — Range نهایی: horizon=1 روی 1D
- پیشبینی high/low **فردا** (horizon=1) روی تایمفریم 1D.
- سیگنال همچنان 5M.

### فاز ۵۷ — (ثبتنشده؛ فقط در کد) پایداری بکتست + ورود واقعبینانه
- **گسترش SL بهاندازهٔ اسپرد** در `bracket.py` (`spread` در `from_model_levels`)
  تا اسپرد باعث توقفِ زودهنگام ضرر نشود.
- `spread`/`spread_pct` در `dual_model_prediction_source` و `dual_model_backtest_service`.
- **ورود با typical price** `(O+H+L+C)/4` بهجای open تنها در `backtest_engine.py`
  (واقعبینانهتر، چون سرعت اینترنت/محاسبات ممکن است دقیقاً open را نگیرد).
- **EarlyStopping** + **ReduceLROnPlateau** برای هر دو مدل.
- **Resume از همهٔ foldها** (نه فقط آخرین) — همهٔ foldها warm-start میشوند.
- **AdamW برای هر دو regression و classification** (weight_decay متفاوت).

### فاز ۵۸ — (ثبتنشده؛ فقط در کد) معماری Signal
- مدل سیگنال: `window=300` (۲۵ ساعت)، `n_layers_per_block=5`, `n_blocks=2`
  → RF=249 ≈ ۸۳٪ پنجره.

---

## ۴. «دقیقاً کجای کاریم؟» — وضعیت واقعی پروژه

پروژه در فازهای **۵۷/۵۸** است، در دلِ **بهینهسازیِ مدلهای دوگانه برای
سوددهیِ بکتست طلا (XAUUSD)**:

```text
زنجیرهٔ کامل بکتست دومدلی (ساختهشده و با مدلِ آموزشدیده کار میکند):

5M window → سیگنال BUY/SELL + confidence
         → گیت اطمینان
         → پنجرهٔ 1D/1H → range model → high/low فردا
         → براکت TP/SL (SL ± spread)
         → ورود next-open با typical price
         → خروج کندلبهکندل (stop-first) → PnL
```

**گیتهای استراتژی (`dual_model_strategy.py`):**
۱. session filter (ساعت خوب UTC) · ۲. هر دو forecast موجود · ۳. اطمینان ·
۴. انسجام range · ۵. هزینهٔ حرکت · ۶. حداقل فاصلهٔ SL.

**معماری مدلها (فعلی در کد):**
- Range: `1D`, `horizon=1`, `window=150`, seq2seq, ~182 ستون، loss سهگانه، AdamW.
- Signal: `5M`, `window=300`, `n_layers=5`, `n_blocks=2`, binary SELL/BUY.

**تعداد کد/تست (از Statistics.json):**
317 فایل منبع · 47505 خط · 758 کلاس · 4239 تابع · 121 فایل تست · 21051 خط تست.

---

## ۵. تکمیل با گزارش رسمی کاربر (PHASE57_58_REPORT.md — آپدیت 2026-08-26)

کاربر گزارش رسمی فاز ۵۷/۵۸ را به `docs/Report/PHASE57_58_REPORT.md` اضافه کرد و
`CURRENT_STATE.md` را با خلاصهٔ زندهٔ وضعیت بازنویسی کرد. جزئیاتی که استنتاج من
از کد را کاملتر میکنند:

- **معماری Range نهایی:** `window=150, n_layers=4, n_blocks=2, horizon=1, seq2seq=True`
- **معماری Signal نهایی:** `window=300, n_layers=5, n_blocks=2, RF=249` (۲۵ ساعت context)
- **Signal training:** `AdamW(lr=0.0001, wd=1e-5)` + ReduceLROnPlateau + EarlyStopping؛
  `label_smoothing` امتحان شد ولی با `SparseCategoricalCrossentropy` ناسازگار بود و حذف شد.
- **Range training:** `AdamW(lr=0.001, wd=1e-4)` + ReduceLR + EarlyStopping؛
  loss سه‌گانه `3×Huber(δ=0.005) + 6×MAE + 1×MSE`.
- **باگ‌های رفع‌شده در بکتست (فاز ۵۷):**
  - متغیر `configuration` در `run()` shadow می‌شد → Python آن را unbound local می‌دید
    (رفع: نام به `_active_config`).
  - `spread=configuration.spread` قبل از assignment استفاده می‌شد (رفع: `self._configuration.spread`).
- **قابلیت‌های جدید بکتست:** لاگ مدل‌های لودشده در خروجی، ذخیرهٔ هر بکتست در
  `run_logs/backtest_run.log`، فیلد «Spread type» (pct/fixed)، ورود با typical price.
- **وضعیت مدل‌های آموزش‌دیده (از گزارش کاربر):**
  - `gold_signal_5m v1` → val_accuracy ~65–80%
  - `gold_range_1d v1–v3` → val_mae ~0.000079–0.001178
  - `gold_range_1d v3` (آموزش 137 epoch) val_mae = 0.000010 (بسیار کم)
- **تنظیمات بکتست آلپاری:** spread=0.06% (pct)، commission=0، R/R=1.0، confidence 60%.

> ⚠️ **یادداشت هماهنگی:** `CURRENT_STATE.md` قدیمی یک سند طراحیِ منجمد بود؛ کاربر آن را
> با نسخهٔ کوتاهِ «وضعیت زنده» جایگزین کرد. این مطابق `AGENTOPERATINGRULE` است
> (کد/وضعیت = واقعیت).

---

## ۶. کارهای پیشنهادی بعدی (به ترتیب)

1. **همگامسازی مستندات**: ثبت فازهای ۵۰–۵۸ در `WORKLOG.md` و `IMPLEMENTATION_STATUS.md`
   (این خلأ را پر کند).
2. **بهروزرسانی تستهای کهنه** (۲۹ مورد) تا با کدِ فعلی (فاز ۵۲–۵۸) هماهنگ شوند —
   بدون تضعیف آنها، فقط تطبیق با رفتارِ عمدیِ جدید.
3. **بهروزرسانی `project_state/generated/*`** (Snapshot/Context) چون کهنهاند.
4. پس از آن، انتخاب قدم بعدیِ واقعی (ادامهٔ بهینهسازی مدل / بکتست روی دیتای واقعی).

---

*این سند نتیجهٔ ممیزی وضعیت است و باید بعد از اعمال اقداماتِ ۱–۳ بهروز شود.*
