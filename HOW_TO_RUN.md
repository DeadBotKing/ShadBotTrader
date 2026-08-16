# راهنمای نصب، تست و اجرا — ShadBotTrader

سیستم: **ویندوز + Python 3.12.10**

---

## گام ۱ — آماده‌سازی محیط

پروژه‌ی به‌روزشده را از زیپ در مسیر دلخواه باز کنید (مثلاً روی دسکتاپ)، سپس:

```powershell
cd C:\Users\DeadBotKing\Desktop\ShadBotTrader

# اگر venv قدیمی فعال است، اول خارج شوید
deactivate

# پاک‌سازی venv های قدیمی
Remove-Item -Recurse -Force .venv, Venv -ErrorAction SilentlyContinue

# ساخت venv با پایتون 3.12
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1

python --version    # باید Python 3.12.10 باشد
```

> اگر `Activate.ps1` خطای execution policy داد:
> `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`

---

## گام ۲ — نصب پکیج‌ها

### 🎯 دستور کامل (توصیه‌شده — همه‌چیز)

```powershell
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements-dev.txt
pip install -r requirements-ai.txt
pip install -e .
```

⏱ حدود ۵ تا ۱۰ دقیقه (تنسورفلو ~۳۵۰ مگابایت است).

### گزینه‌های دیگر

```powershell
# فقط رانتایم (بدون ابزار توسعه و بدون AI)
pip install -r requirements.txt ; pip install -e .

# رانتایم + ابزار تست/لینت (بدون TensorFlow)
pip install -r requirements-dev.txt ; pip install -e .

# نسخه‌های دقیقاً پین‌شده‌ی محیط تأییدشده
pip install -r requirements-lock.txt ; pip install -e .
```

### بررسی نصب

```powershell
python -c "import ShadBotTrader, numpy, pandas, pyarrow, pywt, yaml; print('core OK')"
python -c "import tensorflow as tf; print('TF', tf.__version__)"
```

---

## گام ۳ — تست

### تست سریع (بدون TensorFlow) — چند ثانیه

```powershell
python -m pytest
```
انتظار: **۱۷۵ passed, 3 skipped** (سه تای skip شده تست‌های TF هستند)

### تست کامل (با TensorFlow) — حدود ۱ تا ۲ دقیقه

```powershell
$env:RUN_TF=1
python -m pytest
```
انتظار: **۱۷۸ passed**

بعد از اتمام، برای خاموش کردن:
```powershell
Remove-Item Env:\RUN_TF
```

### تست‌های تفکیک‌شده

```powershell
python -m pytest tests/unit -q                  # فقط unit
python -m pytest tests/integration -q           # فقط integration
python -m pytest tests/architecture -q          # قوانین معماری
python -m pytest tests/unit/ai -q               # فقط AI
python -m pytest -v                             # با جزئیات
python -m pytest --tb=short -x                  # توقف در اولین خطا
```

### کیفیت کد (Quality Gate)

```powershell
python -m black --check .
python -m ruff check .
python -m mypy src
python -m pytest
```
هر چهار مورد باید سبز باشند.

اگر `black` شکایت کرد، خودکار اصلاح کنید:
```powershell
python -m black .
python -m ruff check --fix .
```

---

## گام ۴ — اجرای پروژه

### الف) اپلیکیشن اصلی

```powershell
python -m ShadBotTrader.main
# یا با دستور کوتاه:
shadbot
```
یک چرخه‌ی کامل start → shutdown اجرا می‌کند و لاگ ساختاریافته چاپ می‌کند.

### ب) دموهای کامل (ساده‌ترین راه برای دیدن خروجی)

```powershell
python scripts\run_data.py       # Data Platform  (~۲ ثانیه)
python scripts\run_features.py   # Feature Platform (~۳ ثانیه)
python scripts\run_pip.py        # Project Intelligence (~۵ ثانیه)
python scripts\run_ai.py         # AI Platform  ⚠️ روی CPU خیلی کند است
```

> ⚠️ **درباره `run_ai.py`:** با تنظیمات فعلی (`window_size=16`، roll-forward روی
> ۳۰۰ کندل) روی CPU ممکن است **بیش از ۱۵ دقیقه** طول بکشد. منطقش درست است، فقط
> سنگین است. برای تأیید سریع مسیر AI از `$env:RUN_TF=1; python -m pytest tests/unit/ai`
> استفاده کنید.

### ج) دستورات CLI

بعد از `pip install -e .` این دستورها در دسترس‌اند:

```powershell
# --- Data Platform ---
shadbot-data --help
shadbot-data catalog                                  # فهرست دیتاست‌ها

# --- Feature Platform ---
shadbot-feature --help
shadbot-feature list                                  # فهرست ۱۰۹ فیچر استاندارد
shadbot-feature compute --symbol XAUUSD_i --timeframe 5M

# --- AI Platform ---
shadbot-ai --help
shadbot-ai train   --model gold_direction
shadbot-ai predict --model gold_direction

# --- Project Intelligence ---
shadbot-pip                                           # تولید project_state/generated/
```

معادل بدون نصب (با ماژول):
```powershell
python -m ShadBotTrader.data_cli catalog
python -m ShadBotTrader.feature_cli list
python -m ShadBotTrader.ai_cli train --model gold_direction
python -m ShadBotTrader.intelligence
```

---

## گام ۵ — ترتیب پیشنهادی برای اولین اجرا

```powershell
# 1. تست سریع — مطمئن شوید همه‌چیز سالم است
python -m pytest

# 2. Data Platform را ببینید
python scripts\run_data.py

# 3. Feature Platform را ببینید
python scripts\run_features.py

# 4. فهرست فیچرها
shadbot-feature list

# 5. تست کامل با TensorFlow
$env:RUN_TF=1 ; python -m pytest ; Remove-Item Env:\RUN_TF

# 6. اپلیکیشن اصلی
shadbot
```

---

## عیب‌یابی

| مشکل | راه‌حل |
|---|---|
| `did not find executable at 'C:\Python314\python.exe'` | داخل venv قدیمی هستید → `deactivate` سپس `py -3.12 -m venv .venv` |
| `ModuleNotFoundError: ShadBotTrader` | venv فعال نیست، یا `pip install -e .` اجرا نشده |
| `ImportError: TensorFlow is required` | `pip install -r requirements-ai.txt` |
| تست‌های AI همیشه skip می‌شوند | این طبیعی است — `$env:RUN_TF=1` را ست کنید |
| `Activate.ps1 cannot be loaded` | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| نصب TF کند/قطع می‌شود | `pip install tensorflow-cpu --no-cache-dir` |
| خطای long path هنگام نصب | با ادمین: `New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name LongPathsEnabled -Value 1 -PropertyType DWORD -Force` |
| پیام‌های `oneDNN` / `AVX2` از TF | فقط اطلاعاتی است، خطا نیست. برای خاموش کردن: `$env:TF_CPP_MIN_LOG_LEVEL=2` |
| `run_ai.py` تمام نمی‌شود | طبیعی است روی CPU؛ به‌جایش تست‌های AI را اجرا کنید |

---

## ساختار پروژه

```
ShadBotTrader/
├── src/ShadBotTrader/
│   ├── core/              DI container، event bus، lifecycle، plugins
│   ├── domain/            ai, dataset, feature, market, portfolio, trading, risk
│   ├── application/       bootstrap، runtime، سرویس‌ها
│   ├── infrastructure/    data، feature (۲۰ calculator)، ai (WaveNet)، config، logging
│   ├── project/           Project Intelligence (scanner، builder، exporter)
│   ├── main.py            نقطه‌ی ورود اصلی
│   └── *_cli.py           رابط‌های خط فرمان
├── tests/                 ۱۷۸ تست (unit / integration / architecture)
├── scripts/               دموهای اجرایی
├── datasets/              parquet های raw / processed / features
├── docs/                  مستندات معماری فازهای ۱–۲۸
├── legacy/                کد قدیمی (مرجع دامنه، از لینت مستثنا)
├── requirements*.txt      وابستگی‌ها
├── CHANGELOG_REVIEW.md    گزارش باگ‌های پیداشده و اصلاحات
├── WINDOWS_SETUP.md       راهنمای ویندوز
└── setup_windows.ps1      اسکریپت خودکار راه‌اندازی
```
