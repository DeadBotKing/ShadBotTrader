# گزارش — بستن حلقه‌ی persistence

**تاریخ:** ۲۰۲۶-۰۸-۱۶

---

## مسئله

Sprint P8 لایه‌ی ذخیره‌سازی پایدار را ساخت و Phase 19 داشبورد را. ولی
**دموهای اصلی هنوز حافظه‌ای بودند**:

```
scripts/run_backtest.py       IN-MEMORY only
scripts/run_optimisation.py   IN-MEMORY only
scripts/run_execution.py      IN-MEMORY only
scripts/run_trading.py        IN-MEMORY only
```

یعنی اگر بک‌تست اجرا می‌کردی، نتیجه‌اش هیچ‌وقت روی داشبورد ظاهر نمی‌شد.
فقط دکمه‌های داشبورد در دیتابیس می‌نوشتند. این ناهماهنگی گیج‌کننده بود:
چیزی ساخته بودیم که در مسیر اصلی استفاده نمی‌شد.

---

## راه‌حل

### `application/persistence_context.py`

یک نقطه‌ی واحد که تصمیم می‌گیرد کدام پیاده‌سازی استفاده شود:

```python
context = PersistenceContext.for_run(persist=True, database="shadbot.db")
ledger  = context.portfolio_ledger(starting_cash=Decimal("100"))
journal = context.decision_journal()
```

متدها **نوع پورت** برمی‌گردانند، نه کلاس بتنی — پس هیچ اسکریپتی نمی‌داند
کدام پیاده‌سازی را گرفته است.

### فلگ یکسان در هر چهار اسکریپت

```bash
python scripts/run_backtest.py     --persist
python scripts/run_optimisation.py --persist --db shadbot.db
python scripts/run_execution.py    --persist --session my-run
python scripts/run_trading.py      --persist
```

- بدون `--persist`: هیچ چیز نوشته نمی‌شود و **دیتابیس حتی باز نمی‌شود**
- با `--persist`: هر اجرا جلسه‌ی خودش را می‌گیرد (`backtest-20260816-1623`)
- در پایان هر اجرا، مسیر مشاهده‌ی نتیجه چاپ می‌شود

---

## نتیجه

```
$ for s in trading execution backtest optimisation; do
      python scripts/run_$s.py --persist --db loop.db; done

$ shadbot-db --db loop.db sessions
session                   decisions  approved
trading-20260816-162355           8         3
execution-20260816-162355         5         4
backtest-20260816-162355        290       103

$ shadbot-db --db loop.db status
  trading_decision      303
  execution_attempt     107
  portfolio_fill        107
  portfolio_transaction 160
  learning_candidate     10
  learning_experiment     1
```

و همه‌ی این‌ها بلافاصله روی داشبورد دیده می‌شوند. **حلقه بسته شد.**

---

## 🐞 سه باگ که در مسیر پیدا شدند

### ۱. موتور بک‌تست به کلاس بتنی وابسته بود

```python
def __init__(self, ledger: InMemoryPortfolioLedger)   # ❌
```

این دقیقاً همان چیزی است که persistence باید حلش کند: نمی‌شد دفتر پایدار
را جایگزین کرد.

**علت ریشه‌ای:** پورت `PortfolioLedger` فقط `apply`/`position`/`positions`
دارد، ولی موتور به `cash`، `equity`، `realized_pnl` و `total_fees` هم نیاز
داشت — که در قرارداد نبودند.

**رفع:** پورت جدید `ReportingLedger` که این نیازها را **صریح** می‌کند.
هر دو پیاده‌سازی آن را برآورده می‌کنند.

### ۲. ناسازگاری API بین دو دفتر

```python
InMemoryPortfolioLedger.transactions   # property
SqlitePortfolioLedger.transactions()   # method  ❌
```

کدی که با یکی نوشته می‌شد، با دیگری می‌شکست — و دقیقاً همین اتفاق افتاد
(`TypeError: 'method' object is not iterable`).

**رفع:** هر دو حالا property هستند. سه تست parity اضافه شد که تضمین
می‌کنند سطح API یکسان بماند.

### ۳. تداخل نام متغیر

در `run_trading.py` حلقه‌ی `for title, context in scenarios` متغیر
`context` مربوط به persistence را بازنویسی می‌کرد:

```
AttributeError: 'StrategyContext' object has no attribute 'summary_lines'
```

**رفع:** نام به `storage` تغییر کرد.

> هر سه باگ را **اجرای واقعی** پیدا کرد، نه بازبینی کد. به همین دلیل
> بعد از هر تغییر دموها را اجرا می‌کنم.

---

## وضعیت کیفیت

| بررسی | نتیجه |
|---|---|
| `black --check .` | ✅ ۳۳۵ فایل |
| `ruff check .` | ✅ پاس |
| `mypy src` | ✅ ۲۴۹ فایل |
| `pytest` | ✅ ۶۳۷ passed |
| `RUN_TF=1 pytest` | ✅ **۶۴۳ passed** |
| دموها × ۲ بار (با و بدون `--persist`) | ✅ همه OK |

**رشد تست‌ها:** ۶۳۴ → **۶۴۳** (۹ تست جدید)

- ۶ تست حلقه‌ی persistence (پیش‌فرض حافظه‌ای، نوشتن واقعی، جدایی جلسات)
- ۳ تست parity بین دو دفتر

---

## مرحله‌ی بعدی

سه گزینه باقی است:

**A — کیفیت مدل.** بک‌تست هنوز از `MomentumPredictionSource` استفاده
می‌کند که یک خط پایه‌ی عمداً ساده است. اتصال WaveNet آموزش‌دیده و
کاتالوگ ۱۰۹ فیچری به شبیه‌سازی، **تنها مسیر باقی‌مانده به سمت استراتژی
سودده** است — بدون هیچ تضمینی.

**B — Phase 24: Deployment.** اجرای مداوم، سرویس ویندوز، بکاپ دیتابیس.

**C — داده‌ی واقعی.** هنوز همه‌چیز روی داده‌ی تصادفی اجرا می‌شود. اتصال
MT5 روی ویندوز، همه‌ی اعداد را معنادار می‌کند.

پیشنهاد من **C سپس A** است: بدون داده‌ی واقعی، بهبود مدل روی نویز
سنجیده می‌شود.
