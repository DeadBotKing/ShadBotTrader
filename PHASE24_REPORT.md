# فاز ۲۴ — Deployment — گزارش

**تنها فازی که کاملاً صفر بود.** حالا پیاده شده است.

---

## ۱. چطور اجرا کنی

```powershell
# سلامت سیستم (exit code هم می‌دهد — برای زمان‌بند)
shadbot-deploy health

# بکاپ با تأیید بازیابی
shadbot-deploy backup --note "before migration"
shadbot-deploy backups
shadbot-deploy restore --file backups\shadbot-....db --yes

# دروازهٔ قبل از استقرار
shadbot-deploy preflight --environment production

# اجرای مداوم (Ctrl+C = توقف تمیز)
python scripts\run_service.py --demo --interval 300 --backup-every 12

# نگهداری هفتگی
python scripts\run_weekly_update.py --dry-run
python scripts\run_weekly_update.py

# ثبت در Task Scheduler ویندوز
.\deploy\install_service.ps1 -WhatIf
.\deploy\install_service.ps1
```

---

## ۲. خروجی واقعی

```
=== ShadBotTrader health ===
  live        : True
  ready       : True
  status: degraded
    [ok  ] python_runtime   (critical) 3.13.14
    [ok  ] database         (critical) 128 KB
    [ok  ] storage          (critical) datasets
    [ok  ] tensorflow       (optional) 2.21.0
    [FAIL] metatrader5      (optional) not installed
```

```
=== Pre-deployment checks ===  target: production
  [ok  ] latest backup   shadbot-20260816-203958.db
  [!] deploying pre-1.0 version 0.1.0 to production
  READY. production requires explicit confirmation to deploy.
```

```
service runner:
  [20:40:40] cycle_complete: {'status': 'no_trade'}
  [20:40:44] backup: {'path': '...', 'rows': 9}
  [20:40:47] cycle_complete: {'status': 'traded'}
  shutdown : stopped accepting new work -> in-flight work completed
             -> state persisted -> stopped
```

---

## ۳. چهار تصمیم که مهم‌اند

### ۳.۱ liveness ≠ readiness ≠ health

سه سؤال جدا که به‌راحتی قاطی می‌شوند:

| | سؤال | واکنش |
|---|---|---|
| **liveness** | پروسه زنده است؟ | اگر نه → restart |
| **readiness** | آمادهٔ کار است؟ | اگر نه → کار نده |
| **health** | همهٔ وابستگی‌ها سالم‌اند؟ | گزارش |

سیستمی که تازه بالا آمده **زنده است ولی آماده نیست**. جمع‌کردن این سه در یک
boolean دقیقاً همان چیزی است که باعث می‌شود پلتفرم روی سیستم نیمه‌آماده
معامله کند.

### ۳.۲ وابستگی بحرانی ≠ اختیاری

نبودن MT5 یا TensorFlow سیستم را `degraded` می‌کند، نه `unhealthy`. داشبورد
و بک‌تست باید کار کنند حتی وقتی بروکر در دسترس نیست.

### ۳.۳ بکاپی که هرگز بازیابی نشده، بکاپ نیست

بند ۸۰ سند همین را می‌گوید. هر بکاپ **بلافاصله** باز، integrity-check و
row-count می‌شود.

از **SQLite backup API** استفاده شد نه کپی فایل: کپی‌کردن دیتابیس وسط یک
تراکنش، فایلی می‌سازد که سالم به‌نظر می‌رسد و خراب restore می‌شود — بدترین
حالت ممکن، چون فقط وقتی کشف می‌شود که واقعاً به آن نیاز داری.

restore هم فایل را **قبل از** دست‌زدن به دیتابیس زنده تأیید می‌کند:

```
restore corrupt file -> refused | live database untouched ✓
restore without --yes -> refused ✓
```

### ۳.۴ Task Scheduler، نه Windows Service

سرویس واقعی ویندوز در **session 0** اجرا می‌شود، و آنجا ترمینال MT5 **در
دسترس نیست** — MT5 از طریق IPC محلی با ترمینالی حرف می‌زند که در session
تعاملی کاربر باز است.

این یک محدودیت واقعی است، نه میان‌بر. در خود `install_service.ps1` مستند شد
تا کسی بعداً فکر نکند فراموش شده.

---

## ۴. توقف امن (§۳۳-۳۵)

ترتیب اجباری است و کد آن را **تحمیل** می‌کند:

```
stop accepting work  →  finish in-flight  →  persist  →  stop
```

- `persist()` قبل از drain کردن **خطا می‌دهد** — وضعیتی که ذخیره شود
  از قبل کهنه است
- درخواست توقف وسط یک tick، آن tick را **قطع نمی‌کند**؛ صبر می‌کند
  (بند ۳۳: استقرار نباید معاملهٔ فعال را قطع کند)
- تستی هست که یک tick کند را وسط کار متوقف می‌کند و ثابت می‌کند تمام شد

**حالت پس از restart بازیابی می‌شود:** شمارنده‌ها ادامه پیدا می‌کنند.

---

## ۵. 🐞 دو مشکل واقعی

### باگ #۱۷ — ترتیب لیست بکاپ‌ها غلط بود

تست گرفتش. مرتب‌سازی بر اساس **نام فایل** بود، ولی دو بکاپ در یک ثانیه فقط
با پسوند عددی فرق دارند و `live-...-1.db` از `live-...db` **جلوتر** مرتب
می‌شود.

یعنی `latest()` بکاپ **قدیمی‌تر** را برمی‌گرداند — و یک restore می‌توانست
بی‌صدا دیتای اشتباه را برگرداند. رفع: مرتب‌سازی بر اساس زمان ثبت‌شده.

### نقض معماری که تست گرفت

`default_monitor` در لایهٔ **domain** بود ولی از `infrastructure.data`
import می‌کرد. `test_dependency_direction` شکست ✅ — دقیقاً کاری که باید
می‌کرد. به `infrastructure/deployment/health_checks.py` منتقل شد.

---

## ۶. کیفیت

```
black ✅  ruff ✅  mypy (275 files) ✅
pytest  932 passed, 12 skipped   (قبلاً 866)
```

**۶۶ تست جدید:** ۳۹ واحد (health، release، shutdown) · ۲۷ یکپارچه
(backup، restore، runner).

از جمله تست‌هایی برای: فایل خراب رد شود، restore دیتابیس زنده را خراب نکند،
runner با مدل خراب نمیرد، شکست پشت‌سرهم متوقفش کند، و بکاپ ناموفق معامله را
متوقف نکند.

---

## ۷. فایل‌ها

**جدید**
```
src/ShadBotTrader/domain/deployment/{__init__,health,release}.py
src/ShadBotTrader/infrastructure/deployment/{__init__,backup,health_checks}.py
src/ShadBotTrader/application/services/runner_service.py
src/ShadBotTrader/deploy_cli.py
deploy/install_service.ps1
scripts/run_service.py
scripts/run_weekly_update.py
tests/unit/deployment/{test_health,test_release}.py
tests/integration/test_deployment.py
PHASE24_REPORT.md
```

**ویرایش‌شده:** `pyproject.toml` (دستور `shadbot-deploy`)،
`snapshot_builder.py`، `docs/IMPLEMENTATION_STATUS.md`، `docs/WORKLOG.md`

---

## ۸. صادقانه: چه چیزی هنوز نیست

- **blue/green و canary** (§۳۱-۳۲) پیاده نشدند. برای یک نصب تک‌ماشینه روی
  ویندوز معنا ندارند؛ ساختنشان یعنی پیچیدگی بی‌مصرف.
- **rollback خودکار بر اساس متریک** (§۷۵) نیست. rollback دستی هست
  (`restore --yes`)، ولی تصمیم خودکار به برگشت نیازمند آستانه‌هایی است که
  هنوز داده‌ای برای تعیینشان نداریم.
- **مدیریت secret** (§۲۰-۲۱) فقط تا حد متغیر محیطی است — چیزی مثل Vault
  برای یک ماشین شخصی زیادی است.
- **runner هنوز `--demo` است.** ارسال سفارش واقعی به بروکر تصمیم جداگانه‌ای
  است که پول واقعی پشتش است.
