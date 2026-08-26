# گزارش بررسی و اصلاح پروژه — ShadBotTrader

**تاریخ:** ۲۰۲۶-۰۸-۱۶
**محیط تأیید:** Python 3.13 / TensorFlow-CPU 2.21.0 (معتبر برای Python 3.12 هم)

---

## خلاصه‌ی وضعیت

| بررسی | قبل | بعد |
|---|---|---|
| `ruff check .` | ✅ پاس | ✅ پاس |
| `black --check .` | ✅ پاس | ✅ پاس |
| `mypy src` | ✅ پاس | ✅ پاس |
| `pytest` (بدون TF) | ✅ ۱۷۱ پاس، ۳ skip | ✅ ۱۷۳ پاس، ۵ skip |
| `RUN_TF=1 pytest` | ❌ **۱ شکست** | ✅ **۱۷۸ پاس** |
| `scripts/run_data.py` | ✅ کار می‌کند | ✅ کار می‌کند |
| `scripts/run_features.py` | ✅ کار می‌کند | ✅ کار می‌کند |
| مسیر AI (train→save→load→predict) | ❌ **کرش** | ✅ کار می‌کند |

> نکته‌ی مهم: تست‌های TensorFlow به‌صورت پیش‌فرض skip می‌شوند. برای همین این باگ‌ها
> در اجرای معمولی `pytest` دیده نمی‌شدند و پنهان مانده بودند.

---

## 🐞 باگ ۱ — مدل آموزش‌دیده قابل بارگذاری نبود (بحرانی)

**فایل:** `src/ShadBotTrader/infrastructure/ai/wavenet/wavenet.py`

**علامت:**
```
TypeError: Could not locate class '_GatedActivationUnit'.
Make sure custom classes and functions are decorated with
`@keras.saving.register_keras_serializable()`.
```

**علت:**
کلاس `_GatedActivationUnit` **داخل تابع** `gated_activation_layer()` تعریف شده بود.
هر بار که تابع صدا زده می‌شد، یک کلاس با هویت جدید ساخته می‌شد. Keras هنگام
بارگذاری مدل ذخیره‌شده نمی‌توانست کلاس را پیدا کند.

**تأثیر:** مدل ترین می‌شد و ذخیره می‌شد، ولی **هرگز قابل استفاده برای پیش‌بینی نبود** —
یعنی کل مسیر production شکسته بود.

**اصلاح:**
- کلاس به سطح ماژول منتقل شد (`GatedActivationUnit`) و با
  `@keras.saving.register_keras_serializable(package="ShadBotTrader")` ثبت شد.
- تابع `custom_objects()` اضافه شد و به `load_model(..., custom_objects=...)` پاس داده می‌شود.
- سازگاری با نام قدیمی `_GatedActivationUnit` حفظ شد تا مدل‌های ذخیره‌شده‌ی قبلی هم لود شوند.
- متد `compute_output_shape` اضافه شد (لایه عرض خروجی را نصف می‌کند).
- در TF ≥ 2.16 شیم `tf.keras` صفت `saving` را ندارد، پس مستقیماً از پکیج `keras` استفاده شد
  با fallback به `tf.keras.utils` برای نسخه‌های قدیمی‌تر.

---

## 🐞 باگ ۲ — پیش‌بینی فقط یک ردیف از پنجره را می‌فرستاد (بحرانی)

**فایل:** `src/ShadBotTrader/infrastructure/ai/wavenet/wavenet_trainer.py` → `WavenetPredictor.predict`

**کد معیوب:**
```python
x = np.array([scaled[0]], dtype=np.float32)   # فقط ردیف اول!
```

**علت:**
مدل یک پنجره‌ی کامل با شکل `(window_size, n_features)` انتظار دارد، ولی
`scaled[0]` فقط **اولین ردیف** پنجره را برمی‌داشت. نتیجه شکل `(1, n_features)` بود
به‌جای `(1, window_size, n_features)`.

**تأثیر:** حتی اگر باگ ۱ نبود، پیش‌بینی با `ValueError: Invalid input shape` کرش می‌کرد.

**اصلاح:**
```python
x = np.array([scaled], dtype=np.float32)      # کل پنجره
```
به‌علاوه یک اعتبارسنجی شکل ورودی اضافه شد که خطای واضح بدهد اگر تعداد
گام‌های زمانی یا فیچرها با انتظار مدل نخواند.

---

## 🐞 باگ ۳ — نشت هدف (Target Leakage) در ساخت پنجره‌ها (بحرانی — درستی علمی)

**فایل‌ها:**
- `src/ShadBotTrader/infrastructure/ai/data_windowing.py`
- `src/ShadBotTrader/infrastructure/ai/wavenet/wavenet_trainer.py`
- `src/ShadBotTrader/infrastructure/ai/roll_forward_evaluator.py`

**علت:**
`make_windows()` با `horizon=0` برچسب را از **آخرین ردیف همان پنجره** برمی‌داشت،
ولی ستون هدف را از فیچرها حذف نمی‌کرد. یعنی مدل جواب را مستقیماً در ورودی خودش می‌دید.

مثال با `target_column=4`:
```
پنجره:  [[f0,f1,f2,f3, 1.0],     ← ستون آخر = همان چیزی که باید پیش‌بینی شود
         [f0,f1,f2,f3, 0.0]]
برچسب:  0.0                      ← دقیقاً همان مقدار داخل ردیف آخر پنجره
```

**تأثیر:** این جدی‌ترین مورد است. مدل می‌توانست دقت ظاهراً عالی بگیرد بدون اینکه
واقعاً چیزی یاد گرفته باشد، و در معاملات واقعی کاملاً شکست بخورد. برای پروژه‌ای که
ادعای «roll-forward safe by construction» دارد، این نقض مستقیم آن تضمین است.

**اصلاح:**
- پارامتر `drop_target_column: bool = False` به `make_windows()` و `build_samples()` اضافه شد.
- `WavenetTrainer` حالا `drop_target_column=True` می‌فرستد و `n_features` را
  به `len(series[0]) - 1` اصلاح می‌کند.
- `RollForwardEvaluator` هم همین کار را می‌کند تا ارزیابی با آموزش هماهنگ بماند.
- مقدار پیش‌فرض `False` است تا رفتار سایر مصرف‌کننده‌ها تغییر نکند (سازگاری عقب‌رو).

---

## 🧹 اصلاح ۴ — راهنمای نصب منسوخ TensorFlow

**فایل‌ها:** `README.md`، `wavenet.py`، `pyproject.toml`

پیام خطا و مستندات می‌گفتند:
> «روی ویندوز `tensorflow==2.10.1` با Python 3.9/3.10 نصب کنید»

این اطلاعات **قدیمی** است. TensorFlow روی ویندوز با Python 3.10–3.13 نصب می‌شود.
چیزی که از TF 2.11 قطع شده **پشتیبانی GPU روی ویندوز نیتیو** است، نه خود نصب.

راهنما به `tensorflow-cpu` (با اشاره به WSL2 برای GPU) به‌روزرسانی شد.

---

## ✨ افزوده‌ها

### فایل‌های requirements

| فایل | محتوا |
|---|---|
| `requirements.txt` | فقط رانتایم اصلی (Data + Feature) |
| `requirements-dev.txt` | اصلی + ruff، black، mypy، pytest |
| `requirements-ai.txt` | اصلی + TensorFlow |
| `requirements-lock.txt` | نسخه‌های دقیق پین‌شده‌ی محیط تأییدشده |

`tomli` هم اضافه شد که یک وابستگی گمشده بود: `project/core/config_scanner.py`
روی Python 3.10 به آن نیاز دارد (در ۳.۱۱+ به‌صورت `tomllib` در stdlib هست).

### دستورات کنسول

`[project.scripts]` به `pyproject.toml` اضافه شد:

| دستور | معادل |
|---|---|
| `shadbot` | `python -m ShadBotTrader.main` |
| `shadbot-data` | `python -m ShadBotTrader.data_cli` |
| `shadbot-feature` | `python -m ShadBotTrader.feature_cli` |
| `shadbot-ai` | `python -m ShadBotTrader.ai_cli` |
| `shadbot-pip` | `python -m ShadBotTrader.intelligence` |

### تست‌های رگرسیون (۴ عدد)

| تست | محافظت از |
|---|---|
| `test_make_windows_can_drop_target_column` | باگ ۳ — نشت هدف |
| `test_build_samples_drop_target_column_matches_width` | باگ ۳ — هماهنگی عرض |
| `test_wavenet_model_survives_save_load_roundtrip` | باگ ۱ — سریال‌سازی |
| `test_wavenet_predictor_rejects_wrong_feature_count` | باگ ۲ — شکل ورودی |

### مستندات

- `WINDOWS_SETUP.md` — راهنمای کامل ویندوز
- `setup_windows.ps1` — اسکریپت خودکار راه‌اندازی
- `README.md` — بخش نصب، جدول requirements، جدول CLI، توضیح `RUN_TF=1`

---

## ⚠️ نکاتی که اصلاح نشدند (عمدی)

1. **`scripts/run_ai.py` بسیار کند است.** با پارامترهای فعلی
   (`window_size=16`، ۲ epoch، roll-forward روی ۳۰۰ کندل) روی CPU بیش از ۱۵ دقیقه
   طول می‌کشد. منطق آن درست است — فقط سنگین است. برای تأیید سریع مسیر AI
   از `pytest` استفاده کنید. اگر خواستید می‌توانم نسخه‌ی `--quick` برایش اضافه کنم.

2. **پوشه‌ی `legacy/`** دست‌نخورده ماند. این کد عمداً به‌عنوان مرجع دامنه نگه داشته
   شده و از `ruff`/`black` مستثنا شده است.

3. **`.gitignore` شامل `*.csv` است.** اگر قرار است دیتاست CSV ورودی در ریپو
   کامیت شود، باید استثنا اضافه شود (مثلاً `!datasets/input/*.csv`).
   چون مطمئن نبودم عمدی است یا نه، تغییرش ندادم.
