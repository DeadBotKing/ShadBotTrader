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
انتظار: **۱۷۳ passed, 5 skipped** (پنج تای skip شده تست‌های TensorFlow هستند)

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

### د) ریپلی زندهٔ بک‌تست — دیدن کندل‌ها و معامله‌ها

```powershell
# پخش‌کنندهٔ HTML بسازید و باز کنید
python scripts\run_replay.py --open

# یا همان چیز در ترمینال
python scripts\run_replay.py --console
python scripts\run_replay.py --console --all-bars --delay 0.05

# از طریق CLI
python -m ShadBotTrader.backtest_cli replay --out replay.html
shadbot-backtest replay --console --every 25
```

`replay.html` یک فایل کاملاً مستقل است (بدون اینترنت، CDN یا فونت خارجی).
داخلش: نمودار شمعی که جلو می‌رود، مثلث آبی = ورود، دایرهٔ سبز/قرمز = خروج با
سود/ضرر، نوار equity، و جدولی که هر معامله را همان لحظه‌ای که بسته می‌شود
اضافه می‌کند. کنترل‌ها: Play/Pause (Space)، یک کندل جلو/عقب (فلش‌ها)، اسلایدر،
سرعت و تعداد کندل قابل مشاهده.

از داشبورد هم می‌شود: دکمهٔ **Record a replay** را بزنید و بعد آدرس `/replay`
را باز کنید.

```powershell
python -m ShadBotTrader.dashboard_cli --db shadbot.db serve
# http://localhost:8080/         داشبورد
# http://localhost:8080/replay   ریپلی
```

### ه) دیتای واقعی از متاتریدر ۵ (ویندوز)

```powershell
pip install -r requirements-mt5.txt

shadbot-data mt5-check                          # اتصال را بررسی کن
shadbot-data mt5-resolve --symbol XAUUSD        # بروکرت طلا را چه می‌نامد؟
shadbot-data mt5-symbols --pattern XAU          # فهرست کامل

# اجرای کامل: دریافت → بک‌تست → بهینه‌سازی
python scripts\run_real_data.py --symbol XAUUSD --auto-symbol

# ریپلی روی همان دیتای واقعی
python scripts\run_replay.py --symbol XAUUSD.i --open
```

**چرا `mt5-resolve`؟** بروکرها طلا را `XAUUSD`، `XAUUSD.i`، `XAUUSDm`،
`GOLD` یا `GOLDmicro` می‌نامند. این دستور می‌گوید مال تو کدام است:

```
  -> XAUUSD.i    90  same instrument, broker suffix
     shadbot-data mt5-ingest --symbol XAUUSD.i --timeframe 5M --bars 5000
```

اگر فهرست خالی بود: در MT5 → پنجرهٔ **Market Watch** → راست‌کلیک → **Show All**.

> گپ آخر هفته در دیتای واقعی **طبیعی است** و باعث رد شدن دیتا نمی‌شود؛ فقط
> به‌صورت `GAP_DETECTED` گزارش می‌شود.

### و) استقرار و اجرای مداوم (فاز ۲۴)

```powershell
# سلامت سیستم
shadbot-deploy health

# بکاپ دیتابیس (خودش تأیید می‌کند که قابل بازیابی است)
shadbot-deploy backup --note "before migration"
shadbot-deploy backups
shadbot-deploy restore --file backups\shadbot-....db --yes

# دروازهٔ قبل از استقرار
shadbot-deploy preflight --environment production

# اجرای مداوم — Ctrl+C برای توقف تمیز
python scripts\run_service.py --demo --interval 300 --backup-every 12

# نگهداری هفتگی (بکاپ + محاسبهٔ مجدد فیچرها + ادامهٔ آموزش)
python scripts\run_weekly_update.py --dry-run
python scripts\run_weekly_update.py

# ثبت خودکار در Task Scheduler ویندوز
.\deploy\install_service.ps1 -WhatIf     # اول ببین چه می‌کند
.\deploy\install_service.ps1
.\deploy\install_service.ps1 -Remove     # حذف
```

> **چرا Task Scheduler و نه Windows Service؟** سرویس واقعی در session 0
> اجرا می‌شود و آنجا ترمینال MT5 در دسترس **نیست** — متاتریدر از IPC محلی
> در session کاربر استفاده می‌کند. این محدودیت واقعی است، نه میان‌بر.

### ز) 🎛 تنها دستور اجرای پروژه — همه‌چیز از داشبورد

پس از نصب اولیه، برای اجرای روزمرهٔ پروژه فقط همین دستور را اجرا کنید:

```powershell
python -m ShadBotTrader.dashboard_cli --db shadbot.db serve
```

مرورگر: `http://localhost:8080`

> دیتابیس اگر نباشد **خودش ساخته می‌شود**. تمام عملیات Data، Feature، AI،
> Simulation، Trading و Operations از داخل داشبورد در دسترس هستند و برای
> اجرای آن‌ها نیازی به اجرای جداگانهٔ `run_*.py` نیست.

**دکمه‌ها در ۶ گروه:** Accounts · Data · AI · Simulation · Trading · Operations

**سه صفحه:**
| صفحه | چه نشان می‌دهد |
|---|---|
| `/` | داشبورد و دکمه‌ها |
| `/data` | **چارت شمعی + تعداد کندل + فهرست ۱۲۳ ستون** |
| `/replay` | پخش کندل‌به‌کندل بک‌تست |

#### اولین بار — تنظیم اکانت

۱. **Accounts → Add account**
   `name=alpari-demo`، `login=53102853`، `server=Alpari-MT5-Demo`
۲. (اختیاری) رمز — فقط اگر ترمینال لاگین نیست:
   ```powershell
   $env:SHADBOT_MT5_PASSWORD_ALPARI_DEMO = 'your-password'
   ```
۳. **Accounts → Check account** — اتصال و نمادها را تأیید می‌کند
۴. **Accounts → Detect symbol names** — می‌گوید بروکرت هر ابزار را چه می‌نامد

> 🔐 **رمز هرگز ذخیره نمی‌شود.** پروفایل فقط نام متغیر محیطی را نگه می‌دارد.
> اگر ست نکنی، از session خودِ متاتریدر استفاده می‌شود.

#### چند اکانت با نام‌های نماد متفاوت

اگر بروکر دیگری طلا را `XAUUSD_i` بنامد:
```
Accounts → Add account      (پروفایل دوم)
Accounts → Map a symbol     XAUUSD → XAUUSD_i
Accounts → Switch account   بین اکانت‌ها جابه‌جا شو
```
دیتاست‌ها با نام canonical (`XAUUSD`) ذخیره می‌مانند، پس تاریخچهٔ یادگیری
با عوض‌کردن بروکر از بین نمی‌رود.

> **فاز ۳۵:** پلتفرم دو دیتاست مجزا می‌سازد — `5M` برای مدل سیگنال و `1H`
> برای مدل رنج — و **هرگز** کندل ساختگی جای دیتای واقعی نمی‌گذارد. اگر
> تایم‌فریمی دیتا نداشته باشد، Build با پیام روشن رد می‌کند. پس در
> `Fetch market data` حتماً `5M,1H` را با هم بگیرید.

#### روال روزمره

```
Data  → Fetch market data      Timeframes = 5M,1H,1D  (هر سه در یک اجرا)
Data  → Update features        ویژگی‌ها برای 5M و 1H، هرکدام جدا
                               ↳ لاگ زنده: کدام ویژگی، چندتا از ۱۰۹
                               ↳ تا دیتاست عوض نشده، از انبار خوانده می‌شود
Data  → Build training dataset دو دیتاست: 5M و 1H، هرکدام ۱۲۳ ستون
Data  → Build a higher timeframe  اگر بروکر 1D نداد: از 1H بساز
AI    → Train a model          Model type و Dataset را از منو انتخاب کن
AI    → Retrain a saved model  مدل ذخیره‌شده + دیتاست را از منو انتخاب کن
                               ↳ لاگ زنده هر ۲ ثانیه در همان صفحه
Sim   → Record a replay        تماشای کندل‌به‌کندل در /replay
Trade → Run one live tick      یک چرخهٔ کامل تصمیم‌گیری
Ops   → Back up the database   قبل از هر کار مهم
```

---

> **دیتای تست:** پروژه بدون دیتای بازار تحویل داده می‌شود. برای آزمایش
> سریع، دیتای مصنوعی کوچک بساز (زیر نماد `TESTSYM`، نه XAUUSD):
> ```
> python scripts/make_test_data.py --candles 600 --features
> ```
> دیتای واقعی از `Data → Fetch market data` می‌آید.

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
│   ├── presentation/      داشبورد، دکمه‌های Command، پخش‌کنندهٔ ریپلی
│   ├── project/           Project Intelligence (scanner، builder، exporter)
│   ├── main.py            نقطه‌ی ورود اصلی
│   └── *_cli.py           رابط‌های خط فرمان
├── tests/                 ۱۰۹۷ تست (unit / integration / architecture)
├── scripts/               دموهای اجرایی
├── datasets/              parquet های raw / processed / features
├── docs/                  مستندات معماری فازهای ۱–۲۸
├── legacy/                کد قدیمی (مرجع دامنه، از لینت مستثنا)
├── requirements*.txt      وابستگی‌ها
├── CHANGELOG_REVIEW.md    گزارش باگ‌های پیداشده و اصلاحات
├── docs/IMPLEMENTATION_STATUS.md  وضعیت هر ۲۸ فاز
├── docs/WORKLOG.md        دفترچهٔ کار (هر تغییر ثبت می‌شود)
├── WINDOWS_SETUP.md       راهنمای ویندوز
└── setup_windows.ps1      اسکریپت خودکار راه‌اندازی
```
