# گزارش Sprint P8 — Persistence

**تاریخ:** ۲۰۲۶-۰۸-۱۶
**فاز:** Phase 28 — Implementation Foundation
**مرجع معماری:** `docs/Phases/Phase20.md` + `docs/DATABASE_SCHEMA_SPECIFICATION.md`

---

## مسئله

هشت کامپوننت حالت پلتفرم را در حافظه نگه می‌داشتند و **با هر اجرا از بین می‌رفتند**:
پوزیشن‌ها، PnL، ردّ حسابرسی تصمیم‌ها، تاریخچه‌ی اجرا، حافظه‌ی یادگیری،
رجیستری مدل‌ها، اجراهای آموزش و کاتالوگ دیتاست.

یعنی نمی‌شد پرسید «هفته‌ی پیش چه کردیم؟» — و بهینه‌ساز هر بار همان بن‌بست‌ها
را از نو جستجو می‌کرد.

---

## تصمیم: SQLite به‌جای SQL Server

فاز ۲۰ مقصد نهایی را SQL Server گذاشته. برای این sprint **SQLite** انتخاب شد.

### چرا

SQLite داخل خود پایتون است — بدون سرور، بدون درایور، بدون رشته‌ی اتصال.
یعنی persistence از لحظه‌ی clone کار می‌کند.

### آیا قوانین فاز ۲۰ نقض شد؟

نه. هر چیزی که فاز ۲۰ واقعاً الزام کرده رعایت شده:

| الزام فاز ۲۰ | وضعیت |
|---|---|
| Migration شماره‌دار (§73) | ✅ `MIGRATIONS` لیست append-only |
| تغییر schema فقط با migration (§74) | ✅ CLI فقط `SELECT` می‌پذیرد |
| Migration تکرارپذیر | ✅ اجرای دوباره no-op است |
| تراکنش | ✅ `transaction()` با rollback |
| یکپارچگی ارجاعی | ✅ `PRAGMA foreign_keys = ON` |
| Audit / تاریخچه | ✅ ژورنال تصمیم و اجرا |
| نسخه‌ی schema قابل مشاهده | ✅ جدول `system_state` |
| Domain نباید دیتابیس را بشناسد | ✅ همه پشت پورت‌های موجود |
| تقسیم منطقی دامنه (§5) | ✅ پیشوند جدول: `market_`، `ai_`، `trading_`، `portfolio_`، `learning_` |

چون همه‌چیز پشت پورت‌های دامنه است، افزودن SQL Server در آینده **یک کلاس
خواهر است، نه بازنویسی**.

---

## چه چیزی ساخته شد

### `src/ShadBotTrader/infrastructure/persistence/`

| فایل | محتوا |
|---|---|
| `database.py` | `Database` — اتصال، migration، تراکنش، آمار |
| `sqlite_journals.py` | ژورنال تصمیم و اجرا |
| `sqlite_ledger.py` | دفتر پرتفوی + بازسازی از fillها |
| `sqlite_learning.py` | حافظه‌ی یادگیری و مخزن آزمایش |
| `sqlite_registries.py` | مدل، اجرای آموزش، دیتاست، فیچر |

### ۱۳ جدول در ۶ حوزه‌ی منطقی

```
system    : system_state, schema_migrations
market    : market_dataset
feature   : feature_definition
ai        : ai_model, ai_training_run
trading   : trading_decision, execution_attempt
portfolio : portfolio_fill, portfolio_transaction, portfolio_position
learning  : learning_candidate, learning_experiment
```

### جایگزین‌های پایدار

| پورت | حافظه‌ای | پایدار |
|---|---|---|
| `PortfolioLedger` | `InMemoryPortfolioLedger` | `SqlitePortfolioLedger` |
| `DecisionJournal` | `InMemoryDecisionJournal` | `SqliteDecisionJournal` |
| `ExecutionJournal` | `InMemoryExecutionJournal` | `SqliteExecutionJournal` |
| `LearningMemory` | `InMemoryLearningMemory` | `SqliteLearningMemory` |
| `ExperimentRepository` | `InMemoryExperimentRepository` | `SqliteExperimentRepository` |
| `ModelRegistry` | `InMemoryModelRegistry` | `SqliteModelRegistry` |
| `TrainingRunRepository` | `InMemoryTrainingRunRepository` | `SqliteTrainingRunRepository` |
| `DatasetRepository` | `InMemoryDatasetRepository` | `SqliteDatasetRepository` |
| `FeatureRegistry` | `InMemoryFeatureRegistry` | `SqliteFeatureRegistry` |

نسخه‌های حافظه‌ای **حذف نشدند** — برای تست‌های سریع مفیدند.

---

## دفترها بازسازی‌پذیرند

مهم‌ترین ویژگی حسابداری: `rebuild_from_fills()` هر پوزیشن را با **پخش
مجدد fillهای ذخیره‌شده** از نو محاسبه می‌کند.

```
Recomputing the position by replaying stored fills:
    stored state : 2 @ 2002
    rebuilt      : 2 @ 2002
[OK] the books are a consequence of recorded events, not a memory
```

یعنی وضعیت فعلی **نتیجه‌ی رویدادهای ثبت‌شده** است، نه عددی که کسی به یاد
داشته. اگر این دو با هم نخوانند، دفترها اشتباه‌اند — و حالا قابل تشخیص است.

---

## خروجی دمو

```
SESSION 1 - trade, then 'shut down'
  bar 0: decision=enter  -> filled
  bar 1: decision=hold   -> strategy signalled HOLD
  bar 2: decision=hold   -> already long; buy signal adds nothing

  position : XAUUSD_i LONG 2 @ 2002
  cash     : 99.5996 USD

  [process ended - every object destroyed]

SESSION 2 - reopen the database
  position : XAUUSD_i LONG 2 @ 2002
  cash     : 99.5996 USD
  [OK] the position came back from disk
```

---

## وضعیت کیفیت

| بررسی | نتیجه |
|---|---|
| `black --check .` | ✅ ۳۱۶ فایل |
| `ruff check .` | ✅ پاس |
| `mypy src` | ✅ ۲۳۵ فایل |
| `pytest` | ✅ **۵۶۴ passed, 6 skipped** |
| `RUN_TF=1 pytest` | ✅ **۵۷۰ passed** |

**رشد تست‌ها:** ۵۱۱ → **۵۷۰** (۵۹ تست جدید)

- ۲۱ تست هسته‌ی دیتابیس (migration، تراکنش، یکپارچگی، thread-safety)
- ۲۹ تست adapterها (بقای داده پس از restart)
- ۹ تست یکپارچگی (چرخه‌ی کامل معامله + restart)

### تست‌هایی که ارزش گفتن دارند

| تست | چه چیزی را می‌گیرد |
|---|---|
| `test_a_failed_transaction_rolls_back` | نیمه‌نوشتن نباید چیزی جا بگذارد |
| `test_foreign_keys_are_enabled` | SQLite پیش‌فرض خاموش دارد — باگ خاموش کلاسیک |
| `test_parameters_are_bound_not_interpolated` | تلاش SQL injection باید داده ذخیره شود نه اجرا |
| `test_row_count_rejects_unknown_tables` | محافظت از f-string داخل `row_count` |
| `test_connections_are_per_thread` | اشتراک یک اتصال بین thread‌ها داده را خراب می‌کند |
| `test_positions_are_rebuildable_from_stored_fills` | دفترها باید مشتق رویدادها باشند |
| `test_idempotency_guard_still_applies_with_persistence` | persistence نباید محافظ تکرار را ضعیف کند |

---

## دستورات جدید

```bash
python scripts/run_persistence.py           # دموی restart
python scripts/run_persistence.py --keep    # نگه داشتن فایل برای بررسی

shadbot-db init                              # ساخت/مهاجرت
shadbot-db status                            # نسخه + تعداد سطرها
shadbot-db sessions                          # جلسات ثبت‌شده
shadbot-db positions --session live-1
shadbot-db decisions --session live-1
shadbot-db executions --session live-1
shadbot-db candidates                        # کاندیداهای به‌خاطر مانده
shadbot-db query "SELECT * FROM portfolio_fill LIMIT 5"
shadbot-db vacuum
```

> `shadbot-db query` فقط `SELECT` می‌پذیرد. تغییر schema باید از مسیر
> migration برود (قانون §74).

---

## 🐞 اشتباهی که کردم (دوباره)

هنگام به‌روزرسانی `context_builder.py` و `snapshot_builder.py` از
`s.index(")")` برای پیدا کردن پایان بلوک استفاده کردم — که **اولین پرانتز
داخل رشته** را پیدا می‌کند، نه پایان عبارت را. هر دو فایل `SyntaxError` شدند.

این دقیقاً همان اشتباهی است که در Sprint P6 هم کردم. قبل از ساخت زیپ
گرفتمش، با پیدا کردن خط دقیق `)` درست کردم، و **همه‌ی فایل‌های `src/` را
با `ast.parse` بررسی کردم — صفر خطا**.

درسش: برای ویرایش کد، تطبیق خط‌به‌خط از جستجوی رشته‌ای امن‌تر است.

---

## آنچه عمداً انجام نشد

- **دموها و CLIهای موجود هنوز پیش‌فرض حافظه‌ای‌اند.** adapterهای پایدار
  ساخته و تست شده‌اند، ولی جایگزین کردنشان در همه‌جا یک تصمیم جداست
  (مثلاً بک‌تست نباید هر اجرا را در دیتابیس بریزد).
- **`SqliteDatasetRepository.get()` و `list_all()` خالی برمی‌گردانند** —
  بازسازی کامل `DatasetDescriptor` نیاز به schema و quality report دارد.
  ردیف‌ها به‌عنوان کاتالوگ ذخیره می‌شوند و با `stored_rows()` خوانده می‌شوند.
  **descriptor نیمه‌ساخته برنگرداندم** چون بدتر از هیچ است.
- **SQL Server adapter** — طبق درخواست ساخته نشد.

---

## مرحله‌ی بعدی

### گزینه A — اتصال persistence به دموها (کوچک)

adapterها آماده‌اند ولی استفاده نمی‌شوند. یک فلگ `--persist` به
`run_execution.py`، `run_backtest.py` و `run_optimisation.py` اضافه شود.

### گزینه B — Phase 19: GUI / API (بزرگ‌تر)

حالا که داده پایدار است، بالاخره می‌توان نمایشش داد: داشبورد فقط-خواندنی
روی پوزیشن‌ها، منحنی سرمایه، ردّ حسابرسی و تاریخچه‌ی یادگیری.

**پیشنهاد من A است** — کوچک، و بدون آن Sprint P8 نصفه می‌ماند: چیزی ساختیم
که هنوز در مسیر اصلی استفاده نمی‌شود.
