# فازهای ۹، ۲۱، ۲۲ — تکمیل شدند

**سه فازی که «کار می‌کردند ولی به عمق مستندات نبودند».** حالا کاملند.

قبل: پلاگین ۳۷ خط · پیکربندی ۱۲۰ خط · لاگینگ ۲۴ خط
بعد: ۵۹۵ خط · ۴۵۰ خط · ۴۰۰ خط — با ۱۰۲ تست

---

## ۱. تأیید فاز ۲۴ (اول بررسی کردم)

قبل از رفتن سراغ کار جدید، فاز ۲۴ را واقعاً آزمودم:

```
فایل‌ها      : هر ۱۰ فایل موجود ✅
health       : ready=True, degraded (MT5 optional) — exit code 0
backup       : 128 KB | schema v1 | 9 rows | verified=True
preflight    : READY. production requires explicit confirmation
تست‌ها       : ۶۶ تست سبز
```

**فاز ۲۴ کامل است** ✅

---

## ۲. فاز ۹ — معماری پلاگین

### خط جداکننده‌ای که سند می‌کشد

```
PluginRegistry  →  "چه پلاگین‌هایی ثبت شده‌اند؟"
PluginManager   →  "وضعیت عملیاتی‌شان چیست؟"
```

دو نگرانی جدا، دو شیء جدا. ادغامشان کلاسی می‌سازد که هم کاتالوگ دارد هم
چرخهٔ حیات را تغییر می‌دهد — و آن‌وقت هیچ‌کدام از دو سؤال بدون عارضهٔ جانبی
قابل پاسخ نیست.

### چرخهٔ حیات (§۱۸) — با state machine واقعی

```
DISCOVERED → VALIDATED → LOADED → INITIALIZED → STARTED → ACTIVE
                                                    ↓
                                              STOPPING → STOPPED
                              (هر مرحله) → FAILED
```

انتقال‌های غیرمجاز **رد می‌شوند**. state machine ای که همه‌چیز را قبول کند،
state machine نیست.

### سه رفتار که مهم‌اند

**۱. پلاگین شکست‌خورده دلیلش را نگه می‌دارد** (§۱۸):
```
bad start : False
reason    : factory raised: RuntimeError: boom
```

**۲. کشف قطعی است** (§۱۴). هرگز پوشه‌ای اسکن و هر فایل پایتونی که پیدا شد
import نمی‌شود — آن اجرای کد دلخواه است با لباس قابلیت. فقط پیکربندی صریح و
entry point های اعلام‌شده.

**۳. یک پلاگین خراب کل استارتاپ را نمی‌خواباند:**
```
discover_configured([{module: "no.such.module"}])
  → FAILED با دلیل، بقیه بالا می‌آیند
```

### گراف وابستگی و تشخیص چرخه

```
load order: ['data', 'ai', 'ui']        ← وابستگی‌ها اول
cycle     : ['a', 'b', 'a']             ← تشخیص داده می‌شود
```

اگر وابستگی یک پلاگین شکست بخورد، خودش **اجرا نمی‌شود** — اجرا شدن روی چیزی
که نیست، بدتر از اجرا نشدن است.

**۲۹ تست**

---

## ۳. فاز ۲۱ — پیکربندی لایه‌ای

### شش لایه با اولویت قطعی (§۵)

```
۱. built-in defaults
۲. base.yaml
۳. {environment}.yaml
۴. local.yaml          ← تنظیمات توسعه‌دهنده، هرگز commit نمی‌شود
۵. متغیرهای محیطی      SHADBOT_TRADING__BASE_QUANTITY=0.05
۶. runtime overrides   ← CLI
```

خروجی واقعی:
```
logging.level              -> WARNING  (فایل محیط بر base غلبه کرد)
trading.base_quantity      -> 0.05     (متغیر محیطی بر فایل‌ها غلبه کرد)
simulation.spread          -> 4.0      (default زنده ماند)
```

**mapping ها بازگشتی merge می‌شوند؛ لیست‌ها جایگزین.** ترکیب عنصربه‌عنصر دو
لیست، نیت سومی می‌سازد که هیچ‌کس ننوشته.

### محافظت از secret — مهم‌ترین بخش

تشخیص خودکار بر اساس نام کلید (§۲۱): `secret`, `password`, `token`,
`api_key`, `private_key`, `credential`, `auth`

```
secrets detected : ['broker.api_key', 'broker.password']
secret readable  : SUPER_SECRET_123        ← برنامه می‌خواند
as_dict redacted : {'api_key': '***REDACTED***'}
repr safe        : LayeredConfiguration(..., secrets_redacted=True)
```

**چرا `__repr__` هم امن شد:** یک traceback که شیء config را چاپ کند،
رمز بروکر را در لاگ می‌ریزد. قاعده در **یک نقطه** اعمال شد، نه در هر
فراخوانی — چیزی که در یک جا اجبار شود، در جای دیگر فراموش نمی‌شود.

### اعتبارسنجی — همهٔ خطاها یکجا

```
[
  "logging.level: 'LOUD' is not one of [DEBUG, INFO, WARNING, ERROR]",
  "trading.max_open_positions: -5 is below the minimum 0"
]
```

گزارش یک خطا در هر اجرا، یک اشتباه پنج‌کلیدی را به پنج اجرا تبدیل می‌کند (§۲۸).

**۴۲ تست**

---

## ۴. فاز ۲۲ — لاگینگ ساختاریافته

### رکورد داده است، نه نثر

```json
{"timestamp":"...","level":"INFO","message":"signal produced",
 "event":"signal","correlation_id":"ee3b5919","component":"TradingEngine",
 "metadata":{"symbol":"XAUUSD","confidence":0.9,
             "broker_password":"***REDACTED***"}}
```

فقط `timestamp`، `level` و `message` اجباری‌اند (§۹). بقیه وقتی درج می‌شوند
که واقعاً معلوم باشند — فیلد خالی هر خط را شلوغ‌تر می‌کند بدون اینکه چیزی
اضافه کند.

### context خودش منتشر می‌شود

```python
with correlation_scope() as cid:
    log.info("cycle begins")           # cid دارد
    bound = log.bind(symbol="XAUUSD")
    bound.info("signal produced")      # cid + symbol دارد
log.info("outside")                    # cid ندارد ✓
```

یک correlation id که بالای چرخهٔ معاملاتی ست شود، روی **هر** رکورد آن چرخه
ظاهر می‌شود — بدون عبور دادن از چهل امضای تابع.

از **`contextvars`** استفاده شد نه متغیر سراسری: command bus و runner هر دو
threaded هستند و تستی هست که ثابت می‌کند context بین thread ها نشت نمی‌کند.

### secret ها به sink نمی‌رسند

redaction **داخل logger** انجام می‌شود. تستی هست که بررسی می‌کند رشتهٔ خام
secret در فایل لاگ **نیست**.

### چرخش فایل

sink فایلی همیشه JSON است و همیشه چرخانده می‌شود (۱۰ مگ × ۵). فایل لاگ
بدون چرخش، بالاخره دیسک را پر می‌کند و پلتفرم معاملاتی را با خودش پایین
می‌آورد.

**۳۱ تست**

---

## ۵. یک هشدار واقعی که ruff گرفت

```
B039 Do not use mutable data structures for `ContextVar` defaults
```

`ContextVar("...", default={})` — آن dict بین **هر** context ای که مقدار
ست نکرده مشترک است. یک mutation درجا، فیلدها را بین عملیات‌های نامرتبط نشت
می‌داد. با `default=None` و کپی تازه در خواننده رفع شد.

نکتهٔ ظریفی بود که به‌راحتی از دست می‌رفت.

---

## ۶. کیفیت

```
black ✅  ruff ✅  mypy (279 files) ✅
pytest  1034 passed, 12 skipped        (قبلاً 932)
```

**۱۰۲ تست جدید:** ۲۹ پلاگین · ۴۲ پیکربندی · ۳۱ لاگینگ

---

## ۷. فایل‌ها

**جدید**
```
src/ShadBotTrader/core/plugins/registry.py
src/ShadBotTrader/core/plugins/manager.py
src/ShadBotTrader/infrastructure/configuration/layered.py
src/ShadBotTrader/infrastructure/logging/structured.py
tests/unit/core/test_plugin_registry.py
tests/unit/core/test_layered_config.py
tests/unit/core/test_structured_logging.py
PHASE_9_21_22_REPORT.md
```

**ویرایش‌شده:** سه `__init__.py`، `snapshot_builder.py`،
`docs/IMPLEMENTATION_STATUS.md`، `docs/WORKLOG.md`

---

## ۸. وضعیت نقشه

🎉 **هر ۲۸ فاز اصلی + سه فاز جدید (۲۹/۳۰/۳۱) کامل شدند.**

تنها انحراف آگاهانه: فاز ۲۰ با **SQLite** به‌جای SQL Server — تصمیم صریح خودت.

---

## ۹. صادقانه: چه چیزی هنوز نیست

- **لاگینگ جدید هنوز در کل کدبیس استفاده نشده.** ساخته و تست شده، ولی
  ماژول‌های موجود همچنان `logging_setup` قدیمی را صدا می‌زنند. مهاجرت
  تدریجی است، نه یک‌بارهٔ پرریسک.
- **رجیستری پلاگین هنوز پلاگین واقعی ندارد.** زیرساخت آماده است؛ تبدیل
  کامپوننت‌های موجود به پلاگین یک تصمیم معماری جداست.
- **مدل‌ها روی دیتای واقعی آموزش ندیده‌اند** — همچنان مهم‌ترین مورد باقی‌مانده.
