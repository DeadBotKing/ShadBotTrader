# فاز ۳۵ — دو دیتاست مجزا، فقط دیتای واقعی

**تاریخ:** 2026-08-17
**وضعیت:** ✅ کامل — Quality Gate سبز
**سؤالی که این فاز را شروع کرد:**

> «چرا Build training dataset براش تایم فریم فرقی نداره؟ مگه نباید دوتا
> دیتاست داشته باشیم برای آموزش یکی ۵ دقیقه یکی ۱ ساعته؟»

جواب کوتاه: **بله باید** — و در واقع داشتیم، ولی سه چیز خرابش می‌کرد.
این فاز هر سه را رفع کرد به‌علاوهٔ یک تصمیم چهارم که کاربر خواست.

---

## ۱. چه چیزی خراب بود

| # | مشکل | چرا خطرناک بود |
|---|---|---|
| **A** | `Fetch market data` فقط **یک** تایم‌فریم می‌گرفت (پیش‌فرض `5M`) | ولی `Build training dataset` **هر دو** را لازم داشت |
| **B** | وقتی تایم‌فریمی خالی بود، بی‌صدا **کندل نمونه (سینوسی)** می‌ساخت و ingest می‌کرد | مدل رنج روی دیتای جعلی آموزش می‌دید و **آموزش‌دیده به‌نظر می‌رسید**. یک اجرا بعد، هیچ‌کس نمی‌توانست تشخیص بدهد کدام کندل واقعی است |
| **C** | warm-up فیچرها می‌توانست سطر را از **وسط** سری هم حذف کند | سطر ۴٬۰۰۰ به سطر ۴٬۰۱۰ می‌چسبید و roll-forward از روی ده دقیقه بازاری که ندیده بود رد می‌شد |
| **D** | کندل‌ها زیر نام **بروکر** (`XAUUSD_i`) ذخیره می‌شدند، ولی بقیهٔ پلتفرم نام **canonical** (`XAUUSD`) را می‌خواند | یک نماد، دو دیتاست بی‌ارتباط. build چیزی پیدا نمی‌کرد و می‌رفت سراغ مورد B |

مورد B مستقیماً ناقض `docs/DEVELOPMENT_RULES.md` بود («پیاده‌سازی و دیتای
جعلی ممنوع»).

---

## ۲. چه چیزی حالا هست

### دو دیتاست، همیشه دوتایی

```
datasets/training/XAUUSD/
    5M_matrix.npz      ← مدل سیگنال   (BUY / SELL / HOLD)
    1H_matrix.npz      ← مدل رنج      (high / low آینده)
    manifest.json      ← هر دو slice، هرکدام digest خودش
```

اینها هرگز جای هم را نمی‌گیرند و هر کدام ۱۲۳ ستون خودش را دارد.
`run_training_dataset.py` حالا هر کدام را جداگانه گزارش می‌کند:

```
  5M dataset  (signal model — buy / sell / hold)
        1,000 candles -> 897 rows x 123 cols
        front rows removed (feature warm-up): 77
        tail rows removed (forward-looking columns): 26
        rows are consecutive candles: True
        stride-1 windows of (200 x 123): 693
        file: datasets/training/XAUUSD/5M_matrix.npz
  1H dataset  (range model — future high and low)
        ...
        file: datasets/training/XAUUSD/1H_matrix.npz
```

### دکمهٔ Fetch حالا لیست می‌گیرد

فیلد «Timeframes» پیش‌فرض `5M,1H` است و هر دو در **یک اجرا** گرفته می‌شوند.
هر تایم‌فریم مستقل merge می‌شود: اگر یکی به‌خاطر gap رد شود، دیتاست همان یکی
دست‌نخورده می‌ماند و بقیه ادامه می‌دهند.

```
--- 5M ---
stored before : 1,000
fetched       : 1,000
new candles   : 0
stored now    : 1,000
continuity    : OK — no gaps

--- 1H ---
...
```

### دیگر هیچ کندل ساختگی‌ای ذخیره نمی‌شود

| مسیر | رفتار قدیم | رفتار جدید |
|---|---|---|
| `Fetch market data` بدون MT5 | sample CSV می‌ساخت و ingest می‌کرد | **رد می‌کند** با پیام روشن |
| `run_training_dataset.py` با انبار خالی | sample می‌ساخت | `NoRealData` با دستور دقیق |
| `run_dual_models.py` با انبار خالی | sample می‌ساخت | `NoRealData` |
| `run_weekly_update.py` | همان | refuse — «نصف دیتاست را refresh نمی‌کنم» |
| `run_live_loop.py --demo` | sample را **روی دیسک** می‌نوشت | کندل دمو فقط **در حافظه**، هرگز ذخیره نمی‌شود |

دکمهٔ Build هم **قبل از شروع** بررسی می‌کند:

```
No stored candles for XAUUSD 1H. The platform builds one dataset per
timeframe — 5M for the signal model and 1H for the range model — and it
will not substitute generated data for either. Run 'Fetch market data'
with Timeframes = 5M,1H first.
```

پیام قبل از اجرا می‌آید، نه سه دقیقه وسط محاسبهٔ فیچرها.

### سطر فقط از **دو سر** حذف می‌شود

این دقیقاً همان چیزی است که کاربر خواست:

> «اون قسمتایی که دیتا ندارن رو حذف کنه مثلا ممکنه دیتاست از ۱۰۰۰ کندل بشه
> ۹۰۰ کندل، ولی این کار فقط برای ابتدای دیتاست، اونم بخاطر اندیکاتورایی
> مثل SMA»

سه حالت، سه رفتار متفاوت:

| کجای سری | مثال | کار |
|---|---|---|
| **ابتدا** | `SMA 200` تا کندل ۲۰۰ حرفی ندارد | سطرها حذف → `dropped_warmup` |
| **انتها** | `chikou`، `*_target_p1` (ستون‌های رو به آینده) | سطرها حذف → `dropped_tail` |
| **وسط** | یک فیچر وسط کار `NaN` می‌دهد | **ستون** حذف می‌شود، نه سطر → `holed_features` |

چرا وسط فرق دارد: حذف سطر از وسط، دو کندل غیرمجاور را به هم می‌چسباند و
`is_contiguous` دروغ می‌شود. یک ستون از دست‌رفته قابل قبول است؛ یک سری
ناپیوسته نه.

اندازه‌گیری واقعی روی ۱۰۰۰ کندل و کاتالوگ کامل:

```
1000 candles -> 897 rows x 123 cols
front cut 77 | tail cut 26 | contiguous True | holed 0
```

هر slice حالا `contiguous` را در manifest ثبت می‌کند و اگر False شد،
`warnings()` هشدار می‌دهد.

### یک نماد = یک دیتاست

قاعدهٔ جدید در یک خط:

> **زیر نام بروکر بگیر، زیر نام canonical ذخیره کن.**

```
fetched as    : XAUUSD_i
stored as     : XAUUSD (canonical)
symbols on disk: ['XAUUSD']
```

`fetch_and_update(..., store_as=...)` کندل‌ها را قبل از merge دوباره برچسب
می‌زند. backfill هنوز با نام بروکر از MT5 می‌پرسد (چون MT5 فقط آن را
می‌شناسد) ولی نتیجه‌اش canonical ذخیره می‌شود.

برای دیتای قدیمی که پیش از فاز ۳۵ زیر `XAUUSD_i` نوشته شده:
`infrastructure/data/symbol_scope.py` اول canonical را می‌گردد، بعد هر
alias را، و اگر از alias استفاده کرد **می‌گوید**:

```
[i] no candles under 'XAUUSD'; using the broker-named history stored as
    'XAUUSD_i' (written before Phase 35)
```

بی‌صدا سراغ alias نمی‌رود — پنهان‌کردنش همان اشتباهی است که فاز ۳۵ برای
رفعش آمده.

---

## ۳. فایل‌ها

### جدید

| فایل | نقش |
|---|---|
| `infrastructure/data/symbol_scope.py` | `StoredSymbol`، `alias_candidates`، `resolve_stored_symbol`، `stored_symbols` |
| `tests/integration/test_dual_timeframe_datasets.py` | ۲۰ تست رگرسیون برای هر چهار مشکل |
| `docs/Phases/Phase35.md` | سند فاز |
| `PHASE35_REPORT.md` | همین فایل |

### تغییر کرده

| فایل | تغییر |
|---|---|
| `infrastructure/ai/feature_matrix.py` | برش فقط از دو سر؛ `holed_features`، `dropped_tail`، `is_contiguous` |
| `domain/dataset/training_dataset.py` | `TimeframeSlice` حالا `contiguous`/`tail_dropped`/`holed_features` دارد؛ سه هشدار جدید |
| `application/services/training_data_service.py` | عبور فیلدهای جدید به slice |
| `application/services/dataset_update_service.py` | `store_as`، `_relabel`، backfill با نام بروکر |
| `presentation/commands/handlers.py` | `parse_timeframes`، `TRAINING_TIMEFRAMES`، fetch چند‌تایم‌فریمی، `missing_timeframes`، بدون fallback نمونه |
| `scripts/run_training_dataset.py` | `NoRealData`، resolve نماد، گزارش per-dataset، پیش‌فرض `XAUUSD` |
| `scripts/run_dual_models.py` | `NoRealData`، resolve نماد، پیش‌فرض `XAUUSD` |
| `scripts/run_weekly_update.py` | refuse وقتی یک تایم‌فریم دیتا ندارد |
| `scripts/run_live_loop.py` | کندل دمو فقط در حافظه |

---

## ۴. تأیید

### Quality Gate

```
black --check .                 ✅ 407 files unchanged
ruff check .                    ✅ All checks passed
mypy src --python-version 3.12  ✅ no issues in 288 source files
pytest                          ✅ 1202 passed, 12 skipped   (قبلاً 1182)
RUN_TF=1 (سه بخش)               ✅ 278 + 344 + 592 = 1214 passed
```

**۲۰ تست جدید.**

### اجرای دمو (دو بار، برای اثبات idempotency)

اجرای اول:
```
5M: added 1000, stored 1000, refused=False
1H: added 1000, stored 1000, refused=False
symbols on disk: ['XAUUSD']
5M: 897 rows x 123 cols | front 77 | tail 26 | contiguous True | digest a93bb562df75bf81
1H: 897 rows x 123 cols | front 77 | tail 26 | contiguous True | digest a93bb562df75bf81
```

اجرای دوم:
```
5M: added 0, stored 1000, refused=False      ← اضافه شد، جایگزین نشد
1H: added 0, stored 1000, refused=False
digest ها بایت‌به‌بایت یکسان
```

### اثبات refuse

```
$ python scripts/run_training_dataset.py --build --symbol XAUUSD --storage-root /tmp/empty

  [X] No stored candles for XAUUSD 5M.
    no stored candles for 5M under any of: XAUUSD
    symbols on disk: none
    Fix it from the dashboard: Data -> Fetch market data
    with Timeframes = 5M,1H. Sample data is deliberately not
    generated any more (Phase 35).
```

---

## ۵. ترتیب اجرا روی ویندوز

```powershell
python -m ShadBotTrader.dashboard_cli --db shadbot.db serve
# http://localhost:8080

#  Accounts → Add account          (53102853 / Alpari-MT5-Demo)
#  Accounts → Check account
#  Accounts → Detect symbol names  (XAUUSD → هرچه بروکر می‌گوید)
#  Data     → Fetch market data    Symbol=XAUUSD  Timeframes=5M,1H  Bars=100000
#  Data     → Build training dataset
#  AI       → Train both models
#  /data برای بازرسی
```

اگر `Fetch` را با `5M,1H` بزنی، `Build` دیگر هرگز چیزی نمی‌سازد — فقط
می‌خواند.

---

## ۶. آنچه هنوز باز است

- **مدل‌ها هنوز روی دیتای واقعی MT5 آموزش ندیده‌اند.** همهٔ ابزار آماده است
  و مسیرهای جعلی بسته شده‌اند؛ قدم بعد اجرای واقعی روی ویندوز است.
- `--demo` در `run_live_loop.py` هنوز کندل مصنوعی می‌سازد. عمدی است: وجودش
  برای آزمودن سیم‌کشی است، نه کیفیت مدل — ولی حالا روی دیسک نمی‌نشیند.
- سایر اسکریپت‌های دمو (`run_ai.py`، `run_backtest.py`، `run_features.py`،
  `run_optimisation.py`، `run_replay.py`، `run_data.py`) هنوز `generate_sample`
  را صدا می‌زنند. اینها مسیرهای «دمو/تست» هستند و در فاز ۳۵ عمداً دست‌نخورده
  ماندند — ولی همین‌ها هم زیر نماد واقعی می‌نویسند و باید در فاز بعد به یک
  نماد جداگانه (مثلاً `DEMOSYM`) منتقل شوند. **بدهی ثبت‌شده.**
