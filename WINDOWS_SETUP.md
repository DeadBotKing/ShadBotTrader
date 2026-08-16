# ShadBotTrader — راه‌اندازی روی ویندوز (Python 3.12)

## مشکل ۱ — ارور ساخت venv

```
(Venv) PS C:\Users\DeadBotKing\Desktop\ShadBotTrader> python -m venv .venv
did not find executable at 'C:\Python314\python.exe': The system cannot find the file specified.
```

### 🔴 علت اصلی — تو داخل venv قدیمی هستی

به ابتدای خط پرامپت نگاه کن:

```
(Venv) PS C:\Users\DeadBotKing\Desktop\ShadBotTrader>
 ^^^^^
```

آن `(Venv)` یعنی **venv قدیمیِ ساخته‌شده با پایتون ۳.۱۴ همین الان فعال است**.

وقتی داخل یک venv باشی، دستور `python` به `Venv\Scripts\python.exe` می‌رسد — و آن فایل فقط یک **shim** کوچک است که به مفسر پایه‌اش (یعنی `C:\Python314\python.exe`) ارجاع می‌دهد.

چون پایتون ۳.۱۴ را پاک کرده‌ای، آن shim به یک فایل ناموجود اشاره می‌کند → دقیقاً همان اروری که می‌گیری.

**پس داری با پایتونِ مُرده تلاش می‌کنی venv جدید بسازی.** پایتون ۳.۱۲.۱۰ تو هیچ مشکلی ندارد، فقط اصلاً صدایش نمی‌زنی.

### ✅ راه حل

**قدم ۱ — از venv مُرده خارج شو:**

```powershell
deactivate
```

اگر `deactivate` ارور داد (چون shim خراب است)، **PowerShell را کامل ببند و دوباره باز کن**.

مطمئن شو که `(Venv)` دیگر ابتدای پرامپت نیست.

**قدم ۲ — پاک‌سازی و ساخت مجدد:**

```powershell
cd C:\Users\DeadBotKing\Desktop\ShadBotTrader

Remove-Item -Recurse -Force .venv, Venv -ErrorAction SilentlyContinue
py -0p                      # لیست پایتون‌های نصب‌شده و مسیرشان
py -3.12 -m venv .venv      # ساخت venv با 3.12 به‌طور صریح
.\.venv\Scripts\Activate.ps1
python --version            # باید 3.12.10 باشد
```

> ⚠️ پوشه‌ی قدیمی‌ات اسمش `Venv` بوده (با V بزرگ). دستور بالا هم `Venv` و هم `.venv` را پاک می‌کند تا قاطی نشوند.

### چرا اصلاً `py -3.12` و نه `python`؟

`py` همان **Python Launcher** ویندوز است و مستقل از PATH و مستقل از venv فعال، مستقیماً سراغ نصب‌های واقعی پایتون می‌رود. برای ساخت venv همیشه امن‌ترین گزینه است.

### راه حل ۲ (تمیزکاری دائمی PATH)

1. `Win + R` → `sysdm.cpl` → تب **Advanced** → **Environment Variables**
2. در `Path` (هم User و هم System) هر ورودی مربوط به `C:\Python314` یا `C:\Python314\Scripts` را **حذف** کن.
3. Settings → Apps → **App execution aliases** → `python.exe` و `python3.exe` را **خاموش** کن.
4. PowerShell را ببند و دوباره باز کن، سپس:
   ```powershell
   where.exe python      # باید فقط مسیر واقعی 3.12 را نشان دهد
   python --version
   ```

### اگر خطای execution policy گرفتی

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

---

## مشکل ۲ — نصب TensorFlow

### خبر خوب
Python **3.12 روی ویندوز کاملاً پشتیبانی می‌شود**. آخرین TensorFlow (2.21.0) ویل رسمی `cp312-cp312-win_amd64` دارد.

### چرا ۳.۱۲ انتخاب درستی بود
کار درستی کردی که از ۳.۱۴ آمدی پایین — **تنسورفلو برای پایتون ۳.۱۴ اصلاً ویل ندارد**. آخرین نسخه (۲.۲۱.۰) فقط `cp310` تا `cp313` را پوشش می‌دهد. یعنی روی ۳.۱۴ هر کاری می‌کردی TF نصب نمی‌شد.

| نسخه پایتون | ویل TensorFlow روی ویندوز |
|---|---|
| 3.10 | ✅ |
| 3.11 | ✅ |
| **3.12** | ✅ **(نسخه‌ی تو)** |
| 3.13 | ✅ |
| 3.14 | ❌ موجود نیست |

> راهنمای داخل `README.md` پروژه که می‌گوید «روی ویندوز فقط تا TF 2.10» **قدیمی است** و مربوط به دوران پشتیبانی GPU است.

### نکته‌ی مهم درباره GPU
- از **TF 2.11 به بعد** روی **ویندوز نیتیو GPU پشتیبانی نمی‌شود**.
- آخرین نسخه با GPU روی ویندوز نیتیو: **TF 2.10.1** (فقط Python 3.9/3.10).
- برای GPU روی ویندوز → باید **WSL2** استفاده کنی.
- برای این پروژه (WaveNet با دیتاست کوچک) **CPU کاملاً کافی است**.

### نصب (داخل venv فعال‌شده)

```powershell
python -m pip install --upgrade pip setuptools wheel
pip install -e ".[dev]"
pip install tensorflow-cpu
python -c "import tensorflow as tf; print(tf.__version__)"
```

> ✅ حتماً `tensorflow-cpu` نصب کن، نه `tensorflow`.
> روی ویندوز هر دو CPU-only هستند، ولی `tensorflow-cpu` سبک‌تر است (~۳۵۰MB در برابر حجم بیشتر).

---

## اسکریپت خودکار

به‌جای همه‌ی مراحل بالا، فقط این را اجرا کن:

```powershell
cd C:\Users\DeadBotKing\Desktop\ShadBotTrader
.\setup_windows.ps1
```

این اسکریپت:
1. پایتون ۳.۱۲ واقعی را با `py` launcher پیدا می‌کند (و ۶۴-بیتی بودنش را چک می‌کند)
2. `.venv` قدیمی خراب را پاک و از نو می‌سازد
3. pip / setuptools / wheel را آپدیت می‌کند
4. پروژه را به‌صورت editable با extras مربوط به dev نصب می‌کند
5. `tensorflow-cpu` را نصب و همه‌چیز را verify می‌کند

---

## بعد از نصب

```powershell
.\.venv\Scripts\Activate.ps1

python -m pytest                    # تست‌ها (تست‌های TF به‌صورت پیش‌فرض skip می‌شوند)
$env:RUN_TF=1; python -m pytest     # همراه با تست‌های TensorFlow

python scripts\run_data.py          # دموی Data Platform
python scripts\run_features.py      # دموی Feature Platform
python scripts\run_ai.py            # دموی AI (نیاز به TensorFlow)
```

---

## عیب‌یابی

| علامت | راه حل |
|---|---|
| `did not find executable at 'C:\Python314\python.exe'` | از `py -3.12 -m venv .venv` استفاده کن |
| `is not a supported wheel on this platform` | پایتونت ۳۲-بیتی است؛ نسخه ۶۴-بیتی نصب کن (`py -3.12 -c "import struct; print(struct.calcsize('P')*8)"` باید ۶۴ بدهد) |
| `Activate.ps1 cannot be loaded` | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| نصب TF خیلی کند است | `pip install tensorflow-cpu --no-cache-dir` |
| ارور long path هنگام نصب | Long paths را فعال کن: `New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name LongPathsEnabled -Value 1 -PropertyType DWORD -Force` (نیاز به ادمین) |
| `ModuleNotFoundError: ShadBotTrader` | مطمئن شو venv فعال است و `pip install -e .` اجرا شده |
