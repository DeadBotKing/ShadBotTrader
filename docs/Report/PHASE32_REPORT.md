# فاز ۳۲ — پروفایل اکانت و کنترل کامل از GUI

**اول تبریک:** MT5 وصل شد ✅ — `Alpari-MT5-Demo`، لاگین `53102853`،
**۸۸۲ نماد**، و `XAUUSD` تطابق دقیق (۱۰۰). روی ویندوز **۱۰۴۶ تست سبز**.

---

## ۱. ممیزی: ۱۸ اسکریپت، ولی فقط ۸ دکمه

ده عملیات فقط از ترمینال قابل اجرا بودند. حالا:

**۲۱ دکمه در ۶ گروه**

| گروه | دکمه‌ها |
|---|---|
| **Accounts** | افزودن · تعویض · بررسی · نگاشت نماد · تشخیص خودکار · حذف |
| **Data** | دریافت دیتا · محاسبهٔ فیچرها · ساخت دیتاست · آپدیت هفتگی |
| **AI** | آموزش مدل جهت · **آموزش هر دو مدل** |
| **Simulation** | بک‌تست · ریپلی · بهینه‌سازی |
| **Trading** | چرخهٔ معاملاتی · دموی اجرا · **یک tick زنده** |
| **Operations** | بکاپ · health · بازتولید project state |

---

## ۲. مدیریت اکانت در GUI

### افزودن اکانت

```
Accounts → Add account
  name    : alpari-demo
  login   : 53102853
  server  : Alpari-MT5-Demo
  is_demo : 1
```

خروجی واقعی:
```
SUCCEEDED  Added 'alpari-demo' and made it active
  login    : 53102853 @ Alpari-MT5-Demo
  type     : demo

  The password is NOT stored. Set it in your shell:
      $env:SHADBOT_MT5_PASSWORD_ALPARI_DEMO = 'your-password'

  Or leave it unset to use the terminal's existing session.
```

### 🔐 چرا رمز ذخیره نمی‌شود

پروفایل فقط **نام متغیر محیطی** را نگه می‌دارد. یک credential در فایل JSON
کنار کد، یک screenshot یا یک screen-share با عمومی‌شدن فاصله دارد.

ترتیب خواندن رمز هنگام اتصال:
1. رمزی که همان لحظه تایپ شده
2. `SHADBOT_MT5_PASSWORD_{PROFILE}`
3. `SHADBOT_MT5_PASSWORD` (مشترک)
4. **هیچ‌کدام → از session خود ترمینال استفاده کن**

گزینهٔ ۴ حالت عادی است: متاتریدر معمولاً از قبل لاگین است، پس پلتفرم اصلاً
به رمز نیاز ندارد.

پنل Accounts در داشبورد نشان می‌دهد: پروفایل فعال، لاگین، سرور،
demo/**LIVE**، aliasها، و اینکه رمز ست شده یا نه.

---

## ۳. نگاشت نماد per-broker — همان که گفتی

> «ممکنه در ی مدل کانکت دیگ اسمش بشه XAUUSD_i»

پلتفرم داخلاً **یک** نام می‌شناسد و هر پروفایل ترجمه می‌کند:

```
canonical  XAUUSD
  Alpari   -> XAUUSD
  Broker B -> XAUUSD_i
  Broker C -> GOLD
```

**چرا این مهم است:** بدون آن، یک ابزار سه دیتاست، سه ماتریس فیچر و سه مدل
جدا می‌ساخت که قابل مقایسه نیستند. عوض‌کردن بروکر **بی‌صدا** تاریخچهٔ
یادگیری را از نو شروع می‌کرد.

### دو راه

**دستی:** `Map a symbol` → `XAUUSD` → `XAUUSD_i`

**خودکار:** `Detect symbol names` از بروکر فهرست می‌گیرد و پیشنهاد می‌دهد:
```
XAUUSD     -> XAUUSD
EURUSD     -> EURUSD
GBPUSD     -> GBPUSD

Suggestions only — re-run with 'Apply suggestions' = 1 to save.
```

**فقط با تأیید ذخیره می‌شود.** بستن بی‌صدای یک دیتاست به ابزار حدس‌زده‌شده،
دقیقاً همان اشتباهی است که این مکانیزم برای جلوگیری از آن ساخته شده.

### در ران‌ها اعمال می‌شود

`Fetch market data` حالا: با نام **بروکر** می‌گیرد، با نام **canonical**
ذخیره می‌کند، و می‌گوید چه کرد:
```
source: MetaTrader 5 (real broker data)
account: broker-b (XAUUSD -> XAUUSD_i)
valid candles : 5000
```

---

## ۴. اسکریپت‌هایی که عمداً دکمه ندارند

| اسکریپت | چرا |
|---|---|
| `run_dashboard.py` | خودِ GUI را بالا می‌آورد |
| `run_service.py` | ناظری که GUI را میزبانی می‌کند |
| `parquet_view.py` | بازرس فایل، نه عملیات پلتفرم |
| `run_pip.py` | همان «Refresh project state» |
| `run_persistence.py` | دموی ذخیره‌سازی، جایش را ران‌های واقعی گرفتند |
| `run_real_data.py` | جادوگر راه‌اندازی، جایش را Accounts + Fetch گرفت |

هر استثنا **در یک تست ثبت شده**، پس این فهرست نمی‌تواند بی‌صدا به جایی برای
پنهان‌کردن دکمه‌های فراموش‌شده تبدیل شود.

---

## ۵. 🐞 نقصی که تست گرفت

`health_check` هنگام شکست، جزئیات را در `detail` می‌گذاشت نه `lines` — یعنی
GUI **کادر خالی** نشان می‌داد، دقیقاً وقتی که اپراتور بیشتر از همیشه به دیدن
نیاز دارد. رفع شد: حالا هر خط چک نمایش داده می‌شود.

---

## ۶. تأیید زنده از طریق HTTP

```
add_account     → SUCCEEDED  متغیر رمز اعلام شد
map_symbol      → SUCCEEDED  XAUUSD -> XAUUSD.i
activate        → SUCCEEDED  symbols: {'XAUUSD': 'XAUUSD.i'}
health_check    → SUCCEEDED  degraded — ready=True
۲۱ دکمه در ۶ گروه رندر شد ✓
```

---

## ۷. کیفیت

```
black ✅  ruff ✅  mypy (283 files) ✅
pytest  1097 passed, 12 skipped     (قبلاً 1034)
```

**۶۳ تست جدید:** ۳۹ پروفایل و نگاشت · ۲۴ پوشش GUI

مهم‌ترینشان `test_every_script_is_reachable_from_the_gui` — اگر کسی
اسکریپت جدیدی اضافه کند بدون دکمه، این تست **شکست می‌خورد**.

---

## ۸. حالا روی ویندوز چه کار کنی

```powershell
# ۱) داشبورد را بالا بیاور
python -m ShadBotTrader.dashboard_cli --db shadbot.db serve

# ۲) مرورگر: http://localhost:8080
#    Accounts → Add account
#       name=alpari-demo  login=53102853  server=Alpari-MT5-Demo

# ۳) (اختیاری) رمز، فقط اگر ترمینال لاگین نیست
$env:SHADBOT_MT5_PASSWORD_ALPARI_DEMO = 'your-password'

# ۴) Accounts → Check account      اتصال و نمادها را تأیید می‌کند
# ۵) Accounts → Detect symbol names
# ۶) Data → Fetch market data      دیتای واقعی
# ۷) Data → Build training dataset
# ۸) AI → Train both models
# ۹) Trading → Run one live tick
```

از این به بعد **همه‌چیز از همان صفحه**.

---

## ۹. صادقانه: چه چیزی هنوز نیست

- **بدون احراز هویت داشبورد.** به localhost bind می‌شود؛ در معرض شبکه
  گذاشتنش اول auth لازم دارد.
- **بدون keychain سیستم‌عامل.** برای نصب تک‌ماشینه، متغیر محیطی سطح درستی
  است؛ keyring یک وابستگی و یک حالت شکست اضافه می‌کند بدون سود واقعی.
- **runner هنوز `--demo` است** — ارسال سفارش واقعی به بروکر تصمیم جداگانه‌ای
  است با پول واقعی.
- **مدل‌ها هنوز روی دیتای واقعی آموزش ندیده‌اند** — حالا با MT5 وصل، این
  قدم بعدی طبیعی است.
