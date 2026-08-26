# آماده‌سازی دیتای واقعی MetaTrader 5 — گزارش

**قدم C از نقشه.** هدف: وقتی روی ویندوز اجرا کردی، اولین بار درست کار کند.

---

## ۱. آنچه باید روی ویندوز اجرا کنی

```powershell
# ۱) نصب پکیج MT5 (فقط ویندوز)
pip install -r requirements-mt5.txt

# ۲) اتصال را بررسی کن (MT5 باید باز و لاگین باشد)
shadbot-data mt5-check

# ۳) ببین بروکرت طلا را چه می‌نامد   ← دستور جدید
shadbot-data mt5-resolve --symbol XAUUSD

# ۴) اجرای کامل: دریافت دیتا → بک‌تست → بهینه‌سازی
python scripts\run_real_data.py --symbol XAUUSD --auto-symbol

# ۵) ریپلی همان دیتای واقعی
python scripts\run_replay.py --symbol XAUUSD.i --open
```

> نام نمادی که در مرحلهٔ ۳ می‌بینی را در مرحلهٔ ۵ بگذار.
> `--auto-symbol` در مرحلهٔ ۴ خودش نزدیک‌ترین را می‌پذیرد و چاپ می‌کند.

---

## ۲. 🐞 باگ مهمی که پیدا شد: دکمهٔ «Update features» هرگز کار نمی‌کرد

حین تست مسیر واقعی کشف شد. هندلر داشبورد متدی را صدا می‌زد که **وجود ندارد**:

```
FAILED: Feature computation failed
'FeatureComputationService' object has no attribute 'compute'
```

| صدا زده می‌شد | واقعیت |
|---|---|
| `service.compute(symbol, timeframe)` | `compute_set(feature_set=..., symbol=..., ...)` |
| `outcome.results` | `outcome.outcomes` |
| `result.definition` | از `feature_set.definitions` |
| `outcome.feature_set.name` | `outcome.set_name` |

**چرا تست‌ها نگرفتند:** تست موجود فقط حالت «کندلی ذخیره نشده» را می‌آزمود، که
*قبل* از رسیدن به کد خراب `return` می‌کند. نقطهٔ کور کلاسیک.

**حالا:** `Computed 109 features over 300 candles` ✅

سپس **هر ۷ دکمه** را با دیتای واقعی اجرا کردم تا مطمئن شوم جای دیگری این
مشکل نیست:

```
fetch_market_data      OK  succeeded   Ingested XAUUSD 5M (v1)
compute_features       OK  succeeded   Computed 109 features over 300 candles
run_backtest           OK  succeeded   Backtested 300 bars
record_replay          OK  succeeded   Recorded 300 bars
run_optimisation       OK  succeeded   Evaluated 6 candidate(s)
run_trading_cycle      OK  succeeded   Cycle complete
refresh_project_state  OK  succeeded   Project state regenerated
train_model            SKIPPED (کند، نیاز به TF در subprocess)
```

---

## ۳. آیا گپ آخر هفته دیتا را خراب می‌کند؟ **نه**

بزرگ‌ترین ریسک این بود: دیتای واقعی جمعه شب تا یکشنبه **گپ** دارد. اگر
pipeline آن را «خراب» تشخیص می‌داد، کل دیتاست قرنطینه می‌شد.

با ۳ هفته دیتای ۵ دقیقه‌ای واقعی‌شکل (۴۳۲۰ کندل، فقط دوشنبه تا جمعه):

```
raw rows      : 4320
candles       : 4320
QUARANTINED   : False        ← دیتا دور ریخته نمی‌شود
overall score : 99.99
  timeliness  : 99.95
issues:
  [warning] GAP_DETECTED: 2 gap(s) found in the candle sequence
```

رفتار درست: گپ **گزارش** می‌شود ولی باعث رد شدن نمی‌شود.

**۴ تست جدید** در `test_mt5_ingestion.py`:
- گپ آخر هفته گزارش می‌شود ولی قرنطینه نمی‌کند
- بک‌تست کامل روی سری گپ‌دار (ترتیب زمانی equity curve حفظ می‌ماند)
- اسپرد متغیر rollover حفظ می‌شود (۱۰ عادی، ۴۵ سر ساعت صفر)
- جهش قیمتی یکشنبه به‌عنوان داده واقعی پذیرفته می‌شود نه خرابی

---

## ۴. حل‌کنندهٔ نام نماد (تازه)

شایع‌ترین دلیل شکست اولین اجرا. بروکرها طلا را این‌طور می‌نامند:
`XAUUSD` · `XAUUSD.i` · `XAUUSDm` · `XAUUSD.raw` · `GOLD` · `GOLDmicro`

```
XAUUSD.i        → XAUUSD          GOLDmicro      → XAUUSD (alias)
XAUUSDm         → XAUUSD          XAUUSD.pro.ecn → XAUUSD
FX.EURUSD       → EURUSD          SILVER         → XAGUSD
USTEC           → USTEC  (دست‌نخورده)
US30 / NAS100   → دست‌نخورده
```

### سه محافظ در برابر فاجعه

۱. **`USTEC` به `UST` تبدیل نمی‌شود** — پسوند `C` کورکورانه کنده نمی‌شود
۲. **`GOLD` به `GOL` تبدیل نمی‌شود** — فهرست `_PROTECTED`
۳. **پسوند ناشناخته → نام دست‌نخورده می‌ماند**

> اصل حاکم: **بهتر است نماد پیدا نشود تا اینکه نماد اشتباه معامله شود.**

امتیازدهی عمداً ساده و شفاف است و هر پیشنهاد **دلیل** دارد:

| امتیاز | معنی |
|---|---|
| ۱۰۰ | دقیقاً همان نام |
| ۹۰ | همان ابزار، پسوند بروکر |
| ۸۰ | alias شناخته‌شده |
| ۶۰ / ۵۰ | نام درخواستی را در خود دارد |

خروجی واقعی:

```
=== Resolving 'XAUUSD' against 5 broker symbols ===

  -> XAUUSD.i                90  same instrument, broker suffix

  'XAUUSD' does not exist, but 'XAUUSD.i' looks like it.
      shadbot-data mt5-ingest --symbol XAUUSD.i --timeframe 5M --bars 5000
```

اگر هیچ نمادی نبود، راهنمای دقیق می‌دهد:

```
  The terminal reported no symbols at all.
  Open MetaTrader 5, then in Market Watch right-click -> Show All.
```

### جاهایی که وصل شد

- `shadbot-data mt5-resolve --symbol XAUUSD` — دستور جدید
- `mt5-ingest` هنگام شکست **خودش** پیشنهاد می‌دهد
- `run_real_data.py --auto-symbol` — می‌پذیرد ولی **هرگز بی‌صدا**:
  ```
  [!]  'XAUUSD' not found; using 'XAUUSD.i'
       reason : same instrument, broker suffix
  ```

---

## ۵. شبیه‌سازی کامل سفر ویندوز

با ترمینال ساختگی که طلا را `XAUUSD.i` می‌نامد:

```
account: {'login': 12345, 'server': 'Broker-Demo', 'balance': 10000.0, ...}
broker symbols: ['BTCUSD.raw', 'EURUSD.i', 'GBPUSD.i', 'USTEC', 'XAUUSD.i']

user asked XAUUSD -> XAUUSD.i (same instrument, broker suffix)

ingested 2880 real-shaped bars, quarantined=False, score=99.99
   [warning] GAP_DETECTED
```

---

## ۶. کیفیت

```
black --check .                   343 files unchanged ✅
ruff check .                      All checks passed ✅
mypy src --python-version 3.12    no issues in 253 files ✅
pytest                            697 passed, 6 skipped ✅   (قبلاً 672)
RUN_TF=1 pytest                   703 passed ✅              (قبلاً 678)
```

**۲۵ تست جدید:** ۱۸ تشخیص نماد · ۴ شکل واقعی بازار · ۳ رگرسیون دکمهٔ فیچرها

دموها دو بار اجرا شدند → خروجی بایت‌به‌بایت یکسان.

---

## ۷. فایل‌ها

**جدید**
```
src/ShadBotTrader/infrastructure/data/mt5_symbol_resolver.py
tests/unit/dataset/test_mt5_symbol_resolver.py
docs/IMPLEMENTATION_STATUS.md      ← ممیزی ۲۸ فاز
docs/WORKLOG.md                    ← دفترچهٔ کار
MT5_READINESS_REPORT.md
```

**ویرایش‌شده**
```
src/ShadBotTrader/presentation/commands/handlers.py   رفع باگ فیچرها
src/ShadBotTrader/data_cli.py                         mt5-resolve + پیشنهاد خودکار
scripts/run_real_data.py                              --auto-symbol
tests/integration/test_mt5_ingestion.py               ۴ تست شکل واقعی
tests/unit/presentation/test_commands.py              ۳ تست رگرسیون
src/ShadBotTrader/project/builders/snapshot_builder.py
docs/{PROJECT_STATE,CURRENT_STATE,Handoff,README}.md  اشاره‌گر وضعیت زنده
```

---

## ۸. قدم بعدی

منتظر خروجی این دستور از تو روی ویندوز هستم:

```powershell
shadbot-data mt5-check
shadbot-data mt5-resolve --symbol XAUUSD
```

با دیدن آن می‌فهمیم بروکرت چه نامی دارد و چه دیتایی در دسترس است. بعد از آن:
**A — وصل‌کردن WaveNet و ۱۰۹ فیچر به بک‌تست** روی دیتای واقعی.
