# راهنمای Parquet و اتصال به داده‌ی واقعی (MetaTrader 5)

---

# بخش ۱ — چرا فایل‌های parquet ناخوانا هستند؟

## جواب کوتاه

Parquet یک فرمت **باینری ستونی و فشرده** است — مثل `.zip` یا `.jpg`.
با Notepad باز نمی‌شود و نباید هم بشود.

اگر با ادیتور متنی بازش کنی، چیزی شبیه این می‌بینی:

```
PAR1 ... XAUUSD_i ... 5M ... (کاراکترهای نامفهوم) ... PAR1
```

آن `PAR1` اول و آخر فایل، امضای فرمت است.

## چرا این فرمت انتخاب شده؟

| ویژگی | CSV | Parquet |
|---|---|---|
| حجم | ۱۰۰٪ | حدود **۱۰–۲۰٪** |
| خواندن یک ستون | کل فایل خوانده می‌شود | فقط همان ستون |
| نوع داده | همه چیز رشته است | نوع‌ها حفظ می‌شوند |
| سرعت | کند | بسیار سریع‌تر |
| خواندن با چشم | ✅ | ❌ |

برای ۳۰۰ کندل تفاوت محسوس نیست، ولی برای **۵۰۰٬۰۰۰ کندل** روی ۱۰۹ فیچر،
CSV غیرقابل استفاده می‌شود.

## چطور اعداد را ببینم؟

ابزارش را ساختم: `scripts/parquet_view.py`

### دیدن اعداد

```powershell
python scripts\parquet_view.py show datasets\raw\XAUUSD_I\5M\v1.parquet
```

```
File   : datasets/raw/XAUUSD_I/5M/v1.parquet
Shape  : 300 rows x 8 columns
Columns: symbol, timeframe, timestamp, open, high, low, close, volume

     symbol timeframe            timestamp     open     high      low    close volume
0  XAUUSD_i        5M  2024-01-02 08:00:00  2000.00  2000.79  1999.44  2000.56    151
1  XAUUSD_i        5M  2024-01-02 08:05:00  2000.56  2002.58  1999.20  2001.50    107
2  XAUUSD_i        5M  2024-01-02 08:10:00  2001.50  2001.74  2000.71  2001.19    241
```

### دستورهای دیگر

```powershell
# فهرست همه‌ی فایل‌های parquet با تعداد سطر و حجم
python scripts\parquet_view.py list

# ۵۰ سطر آخر
python scripts\parquet_view.py show <file> --rows 50 --tail

# فقط چند ستون خاص
python scripts\parquet_view.py show <file> --columns timestamp,close

# ساختار + آمار توصیفی (میانگین، انحراف معیار، min/max)
python scripts\parquet_view.py info datasets\features\sma_20\v1.parquet

# تبدیل به CSV (قابل باز شدن در Notepad و Excel)
python scripts\parquet_view.py csv <file> --out prices.csv

# تبدیل به Excel واقعی
python scripts\parquet_view.py excel <file> --out prices.xlsx

# تبدیل همه‌ی فایل‌ها یکجا
python scripts\parquet_view.py convert-all --out-dir exported_csv
```

### روش دستی با pandas

```python
import pandas as pd
df = pd.read_parquet("datasets/raw/XAUUSD_I/5M/v1.parquet")
print(df.head(20))
df.to_csv("prices.csv", index=False)
```

### ابزار گرافیکی

اگر ترجیح می‌دهی کلیک کنی:

- **Tad** — رایگان، سبک، مخصوص همین کار: <https://www.tadviewer.com/>
- **DBeaver** — رایگان، سنگین‌تر، parquet را هم باز می‌کند
- **VS Code** — افزونه‌ی «Parquet Viewer»

> ⚠️ فایل‌های parquet را **دستی ویرایش نکن**. لایه‌ی ذخیره‌سازی پروژه
> تغییرناپذیر (immutable) است: هر بار ingest، نسخه‌ی جدید می‌سازد.
> ویرایش دستی، checksum و نسخه‌بندی را خراب می‌کند.

---

# بخش ۲ — اتصال به داده‌ی واقعی بازار (MetaTrader 5)

## چه چیزی ساخته شد

`Mt5MarketDataProvider` — پیاده‌سازی **همان** پورت `MarketDataProvider` که
CSV هم از آن استفاده می‌کند.

```
MetaTrader 5  ─┐
               ├─> MarketDataProvider ─> Data Platform ─> Feature ─> AI
CSV file      ─┘                              ─> Backtest ─> Optimiser
```

یعنی هیچ‌جای دیگر پروژه **حتی یک خط** تغییر نکرد. این ثمره‌ی مرزبندی
port/adapter فاز ۱۱ است.

## پیش‌نیازها

| مورد | توضیح |
|---|---|
| ویندوز | پکیج `MetaTrader5` فقط روی ویندوز کار می‌کند |
| ترمینال MT5 | باید **نصب، اجرا و لاگین** باشد |
| پکیج پایتون | `pip install MetaTrader5` |

> پکیج از طریق یک کانال IPC محلی با ترمینال حرف می‌زند. اگر ترمینال بسته
> باشد، اتصال برقرار نمی‌شود.

## نصب

```powershell
.\.venv\Scripts\Activate.ps1
pip install MetaTrader5
```

## ساده‌ترین راه: یک دستور برای همه‌چیز

اسکریپت راهنما همه‌ی مراحل را پشت سر هم اجرا می‌کند و در **اولین** جایی که
آماده نباشد، با پیام واضح متوقف می‌شود:

```powershell
python scripts\run_real_data.py --symbol XAUUSD
```

مراحل: بررسی اتصال → یافتن نماد → دریافت داده → بک‌تست → بهینه‌سازی

```powershell
# با تنظیمات دلخواه
python scripts\run_real_data.py --symbol XAUUSD --timeframe 15M --bars 20000

# فقط تا بک‌تست
python scripts\run_real_data.py --symbol XAUUSD --skip-optimise

# بدون دانلود مجدد (از داده‌ی ذخیره‌شده)
python scripts\run_real_data.py --symbol XAUUSD --skip-ingest
```

اگر ترجیح می‌دهی مرحله‌به‌مرحله جلو بروی، ادامه را بخوان.

---

## گام ۱ — بررسی اتصال

```powershell
shadbot-data mt5-check
```

خروجی موفق:

```
=== MetaTrader 5 connection check ===
  package        : installed
  terminal       : connected
  login          : 12345678
  server         : YourBroker-Demo
  currency       : USD
  balance        : 10000.0
  equity         : 10000.0
  leverage       : 100
```

اگر خطا داد، جدول عیب‌یابی پایین را ببین.

## گام ۲ — پیدا کردن نام دقیق نماد

نام نمادها بین بروکرها فرق دارد: `XAUUSD`، `XAUUSD.i`، `XAUUSDm`، `GOLD`، ...

```powershell
shadbot-data mt5-symbols --pattern XAU
shadbot-data mt5-symbols --pattern EUR --limit 20
shadbot-data mt5-symbols                    # همه
```

## گام ۳ — دریافت داده‌ی واقعی

```powershell
shadbot-data mt5-ingest --symbol XAUUSD --timeframe 5M --bars 5000
```

```
Fetching 5000 bars of XAUUSD 5M from MT5 ...

Ingested XAUUSD 5M (v1)
  provider      : mt5 (real broker data)
  raw rows      : 5000
  valid candles : 5000
  quality score : 99.87
  quarantined   : False
```

### با اطلاعات ورود (اختیاری)

اگر ترمینال از قبل لاگین باشد، **نیازی به پسورد نیست** — همان سشن استفاده
می‌شود. ولی اگر لازم شد:

```powershell
shadbot-data mt5-ingest --symbol XAUUSD --timeframe 5M --bars 5000 `
  --login 12345678 --password "yourpass" --server "YourBroker-Demo"
```

> 🔒 پسورد را در فایل یا اسکریپت ذخیره نکن. روش امن‌تر: ترمینال را دستی
> لاگین کن و بدون `--password` اجرا کن.

### تایم‌فریم‌های پشتیبانی‌شده

```powershell
shadbot-data mt5-timeframes
```

```
1M 2M 3M 4M 5M 6M 10M 12M 15M 20M 30M
1H 2H 3H 4H 6H 8H 12H
1D (D1)  1W (W1)  1MN (MN1)
```

## گام ۴ — استفاده از داده‌ی واقعی

از اینجا به بعد **همه‌چیز مثل قبل** است:

```powershell
# فیچرها
shadbot-feature compute --symbol XAUUSD --timeframe 5M

# بک‌تست روی داده‌ی واقعی
shadbot-backtest run --symbol XAUUSD --timeframe 5M --capital 100 --spread 4

# بهینه‌سازی روی داده‌ی واقعی
shadbot-learn optimise --symbol XAUUSD --timeframe 5M --folds 3
```

**حالا نتایج معنا دارند** — چون روی قیمت واقعی طلا محاسبه می‌شوند، نه
داده‌ی تصادفی.

---

## چه چیزی از بروکر ذخیره می‌شود

هیچ اطلاعاتی دور ریخته نمی‌شود:

| فیلد | جای ذخیره |
|---|---|
| `time` → timestamp UTC | ستون اصلی |
| `open` / `high` / `low` / `close` | ستون اصلی |
| `tick_volume` | ستون `volume` |
| `spread` | ستون `extra` |
| `real_volume` | ستون `extra` |
| نام provider | ستون `extra` |

> **نکته درباره‌ی volume:** در فارکس خرده‌فروشی، `real_volume` معمولاً صفر
> است چون بروکر حجم واقعی بازار را نمی‌بیند. آنچه استفاده می‌شود
> `tick_volume` است (تعداد تغییرات قیمت). این استاندارد صنعت است.

---

## عیب‌یابی

| پیام | علت و راه‌حل |
|---|---|
| `The MetaTrader5 package is required` | `pip install MetaTrader5` |
| `ModuleNotFoundError: MetaTrader5` روی لینوکس/مک | این پکیج فقط ویندوزی است؛ از CSV یا WSL+ویندوز استفاده کن |
| `Could not connect to the MetaTrader 5 terminal` | ترمینال باز نیست یا لاگین نشده. بازش کن و صبر کن تا وصل شود |
| `MT5 returned zero bars` | نماد در **Market Watch** مخفی است. در MT5 راست‌کلیک → Show All |
| `Unsupported timeframe` | `shadbot-data mt5-timeframes` را ببین |
| نماد پیدا نمی‌شود | `shadbot-data mt5-symbols --pattern XAU` — نام دقیق بروکر را بگیر |
| کیفیت پایین / quarantined | معمولاً به‌خاطر گپ آخر هفته است. طبیعی است؛ گزارش issues را بخوان |
| ترمینال ۳۲ بیتی | پایتون و MT5 باید هر دو ۶۴ بیتی باشند |

---

## چرا داده‌ی واقعی مهم است

تا الان همه‌ی بک‌تست‌ها روی داده‌ی **تصادفی تولیدشده** اجرا می‌شدند.
نتیجه‌اش این بود:

```
trades: 51 | return: -2.79% | hit rate: 0.000
promoted: 0
```

این ضرر **درست** بود — روی نویز، هیچ استراتژی‌ای نباید سود بدهد. ولی هیچ
چیز هم درباره‌ی استراتژی یاد نمی‌گرفتیم.

با داده‌ی واقعی:

- بک‌تست معنا پیدا می‌کند
- بهینه‌ساز روی الگوی واقعی جستجو می‌کند
- دروازه‌ی ارتقا (promotion gate) بالاخره می‌تواند چیزی را تأیید کند
- و اگر باز هم چیزی ارتقا نیافت، **آن هم یک یافته‌ی واقعی است**

⚠️ اما یک هشدار صادقانه: داده‌ی واقعی، سودآوری را تضمین نمی‌کند.
استراتژی momentum فعلی یک خط پایه‌ی ساده است. احتمال زیادی هست که روی
داده‌ی واقعی هم ضرر بدهد — و اگر چنین شد، دروازه باید آن را رد کند.
**سیستمی که همیشه یک برنده پیدا می‌کند، خراب است.**
