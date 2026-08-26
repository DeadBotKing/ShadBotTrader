# ریپلی زندهٔ بک‌تست — گزارش

**درخواست:** «اجرای بک‌تست رو یکاری کنی که به صورت لایو کندلا نمایش داده بشن و
نشون بده کجاها معامله کرده و نتیجه معامله چی بود؟»

**نتیجه:** ✅ انجام شد — هم پخش‌کنندهٔ گرافیکی در مرورگر، هم نسخهٔ ترمینال، هم
دکمه در داشبورد.

---

## ۱. چطور اجرا کنم؟

### سریع‌ترین راه

```powershell
python scripts\run_replay.py --open
```

یک فایل `replay.html` می‌سازد و در مرورگر باز می‌کند.

### همان چیز در ترمینال

```powershell
python scripts\run_replay.py --console                      # فقط کندل‌های مهم
python scripts\run_replay.py --console --all-bars           # همهٔ کندل‌ها
python scripts\run_replay.py --console --all-bars --delay 0.05   # واقعاً «لایو»
```

### از طریق CLI

```powershell
python -m ShadBotTrader.backtest_cli replay --out replay.html
python -m ShadBotTrader.backtest_cli replay --console --every 25
shadbot-backtest replay --spread 0 --capital 1000
```

### از داشبورد (دکمه)

```powershell
python -m ShadBotTrader.dashboard_cli --db shadbot.db serve
```

دکمهٔ **Record a replay** را بزنید → بعد `http://localhost:8080/replay`.
لینکش هم بالای خود داشبورد هست.

---

## ۲. داخل پخش‌کننده چه می‌بینید؟

| عنصر | معنی |
|---|---|
| شمع سبز/قرمز | کندل واقعی همان بار (OHLC) |
| مثلث آبی رو به بالا | ورود خرید (BUY) در آن قیمت |
| مثلث آبی رو به پایین | ورود فروش (SELL) |
| دایرهٔ سبز | خروج با **سود** |
| دایرهٔ قرمز | خروج با **ضرر** |
| خط پایین نمودار | equity؛ خط‌چین خاکستری = سرمایهٔ اولیه |
| جدول Trades | هر معامله همان لحظه‌ای که بسته می‌شود اضافه می‌شود |

نوار وضعیت زیر نمودار در هر لحظه نشان می‌دهد: شمارهٔ کندل، زمان، close،
**خروجی مدل (prediction)**، پوزیشن باز (LONG/SHORT/flat)، equity، سود و زیان
و تعداد معاملات بسته‌شده.

**کنترل‌ها:** Play/Pause (کلید Space)، یک کندل جلو/عقب (فلش چپ و راست)،
Restart، Jump to end، اسلایدر برای پریدن به هر نقطه، انتخاب سرعت
(Slow/Normal/Fast/Turbo) و تعداد کندل قابل مشاهده (۶۰ / ۱۲۰ / ۲۵۰ / همه).

فایل کاملاً **self-contained** است: بدون اینترنت، بدون CDN، بدون فونت خارجی.
می‌توانید آن را ایمیل کنید یا آفلاین باز کنید.

---

## ۳. نمونهٔ خروجی ترمینال

```
================================================================================
  REPLAY  XAUUSD_i 5M   session replay
  300 bars · starting equity 100.0 · price range 1995.10 - 2016.12
================================================================================
  bar  time                chart             close    pred     pos     equity
--------------------------------------------------------------------------------
   10  2024-01-02T08:50:00 ·····▮······    2004.90  1.0000   +0.01    99.9740
                        | OPEN  BUY  0.01 @ 2007.30
   14  2024-01-02T09:10:00 ···▯········    2001.52  0.3752    flat    99.9142
                        | CLOSE SELL 0.01 @ 1999.12  ->  LOSS net -0.0838
   15  2024-01-02T09:15:00 ····▮·······    2003.47  0.4391   -0.01    99.8882
                        | OPEN  SELL 0.01 @ 2001.07
```

و در پایان:

```
    #  side   entry bar      entry  exit bar       exit  bars          net  result
    1  long          10    2007.30        14    1999.12     4      -0.0838  LOSS
    ...
  Still open at the end: short 0.01 @ 2005.86 (bar #287) — no result yet, not counted.
--------------------------------------------------------------------------------
  closed trades : 51  (0 win / 51 loss)
  equity        : 100.0 -> 97.2054 (-2.7946)
```

> **دقت کنید:** این عدد **دقیقاً** همان چیزی است که `scripts/run_backtest.py`
> قبلاً می‌داد (۵۱ معامله، −2.7946). ضبط کردن، نتیجه را عوض نمی‌کند —
> یک تست جداگانه همین را اثبات می‌کند.

---

## ۴. چه چیزی ساخته شد

### دامنه (`domain/simulation/replay.py`)

| کلاس | کار |
|---|---|
| `TradeMarker` | یک fill واقعی: قیمت، حجم، سمت، نوع (entry/exit/adjust)، سود محقق‌شده |
| `ReplayBar` | یک کندل پردازش‌شده + equity، cash، پوزیشن و prediction همان لحظه |
| `ReplayTape` | کل ضبط؛ `round_trips()` هر ورود را با خروجش جفت می‌کند |
| `ReplayRecorder` | جمع‌کنندهٔ حین اجرا؛ خروجی‌اش یک `ReplayTape` تغییرناپذیر است |

**دو قاعدهٔ سخت‌گیرانه که رعایت شد:**

1. یک ورود **نتیجه ندارد** — `realized_pnl` آن `None` است، نه صفر. صفر یعنی
   «سربه‌سر بست» که دروغ است.
2. پوزیشنی که تا آخر دیتا باز مانده، **معامله شمرده نمی‌شود**. جداگانه با
   عنوان «Still open at the end» گزارش می‌شود.

### موتور (`infrastructure/simulation/backtest_engine.py`)

پارامتر جدید `record_replay: bool = False`. یک **ناظر منفعل** است:

- پیش‌فرض خاموش — یک sweep با صدها شبیه‌سازی، هزینهٔ نواری که کسی نمی‌خواند را نمی‌دهد.
- `engine.tape` وسط اجرا هم در دسترس است، برای وقتی با `step()` دستی جلو می‌روید.
- `_capture_trade` حالا `(realized_delta, fee_delta)` برمی‌گرداند تا marker
  بدون محاسبهٔ دوباره ساخته شود.

### نمایش

- `presentation/web/replay_renderer.py` — پخش‌کنندهٔ HTML؛ canvas + JS درون‌خطی، داده به‌صورت JSON جاسازی‌شده.
- `infrastructure/simulation/console_replay.py` — `ConsoleReplayPlayer` و `summarise_tape`.
- دستور `replay` در `backtest_cli.py` و اسکریپت `scripts/run_replay.py`.
- دکمهٔ `record_replay` در داشبورد + مسیر `GET /replay` + لینک در هدر.

اگر هنوز ریپلی‌ای ضبط نشده، `/replay` یک صفحهٔ راهنما نشان می‌دهد، نه خطای ۴۰۴.

---

## ۵. تست‌ها

**۶۷۲ passed / ۶ skipped** بدون TensorFlow · **۶۷۸ passed** با `RUN_TF=1`
(قبل از این کار: ۶۴۳).

۲۹ تست جدید:

`tests/unit/simulation/test_replay.py` (۱۲ تست)
- ورود نتیجه ندارد؛ `net_pnl` کارمزد را کم می‌کند
- جفت‌کردن ورود/خروج، برد و باخت
- پوزیشن باز → هیچ round trip تولید نمی‌کند
- نوار خالی به‌جای حدس زدن، خالی بودنش را اعلام می‌کند
- `to_dict()` قابل JSON شدن است و مقادیر نامعلوم `null` می‌مانند

`tests/integration/test_backtest_replay.py` (۱۶ تست)
- تعداد بارهای نوار = `bars_processed`، تعداد marker ها = `fills`
- **equity نوار بار به بار با equity curve یکی است**
- **تعداد round trip ها با `metrics.trade_count` یکی است**
- **مجموع سود round trip ها با سود گزارش‌شده یکی است**
- **ضبط کردن نتیجهٔ اجرا را تغییر نمی‌دهد** (همان return، همان تعداد معامله)
- بدون `record_replay=True` هیچ نواری ساخته نمی‌شود
- HTML خروجی هیچ `http://` یا `<script src=` ندارد
- اجرایی که هیچ معامله‌ای نکرد، صفحه را خراب نمی‌کند

`tests/integration/test_dashboard_server.py` (۴ تست) — مسیر `/replay`، صفحهٔ
راهنما وقتی ریپلی نیست، لینک در داشبورد، حضور `record_replay` در فهرست دستورها.

`tests/unit/presentation/test_commands.py` (۳ تست) — فرم دکمه، رد مؤدبانه وقتی
کندلی ذخیره نشده، و ساختن واقعی فایل player.

**Quality gate:**

```
black --check .                   341 files unchanged ✅
ruff check .                      All checks passed ✅
mypy src --python-version 3.12    no issues in 252 files ✅
pytest                            672 passed, 6 skipped ✅
RUN_TF=1 pytest                   678 passed ✅
```

هر دو اسکریپت دو بار اجرا شدند و خروجی بایت‌به‌بایت یکسان بود (idempotent).

---

## ۶. چیزی که ریپلی نشان می‌دهد و باید ببینید

روی دیتای نمونهٔ **تصادفی**، ۵۱ معامله انجام می‌شود و **هر ۵۱ تا ضرر می‌کنند**.
این باگ نیست — نتیجهٔ درست است: روی نویز، اسپرد ۴ واحدی و کارمزد، هیچ استراتژی
مومنتومی نمی‌تواند برنده باشد. حالا با ریپلی می‌توانید **ببینید** چرا: ورود
همیشه بعد از یک حرکت است و بازار بلافاصله برمی‌گردد.

این دقیقاً همان دلیلی است که قدم بعدی باید **دیتای واقعی MT5** باشد و بعد
**مدل بهتر** — بهبود مدل روی نویز بی‌معناست.

---

## ۷. فایل‌های تغییر یافته

**جدید**
```
src/ShadBotTrader/domain/simulation/replay.py
src/ShadBotTrader/infrastructure/simulation/console_replay.py
src/ShadBotTrader/presentation/web/replay_renderer.py
scripts/run_replay.py
tests/unit/simulation/test_replay.py
tests/integration/test_backtest_replay.py
```

**ویرایش‌شده**
```
src/ShadBotTrader/infrastructure/simulation/backtest_engine.py   record_replay + tape
src/ShadBotTrader/infrastructure/simulation/__init__.py
src/ShadBotTrader/domain/simulation/__init__.py
src/ShadBotTrader/application/services/backtest_service.py       پارامتر record_replay
src/ShadBotTrader/backtest_cli.py                                دستور replay
src/ShadBotTrader/dashboard_cli.py                               آپشن --replay
src/ShadBotTrader/presentation/commands/commands.py              CommandKind جدید
src/ShadBotTrader/presentation/commands/handlers.py              هندلر record_replay
src/ShadBotTrader/presentation/commands/bus.py
src/ShadBotTrader/presentation/web/server.py                     مسیر /replay
src/ShadBotTrader/presentation/web/renderer.py                   لینک ریپلی
src/ShadBotTrader/project/builders/{snapshot,context}_builder.py
HOW_TO_RUN.md
tests/integration/test_dashboard_server.py
tests/unit/presentation/test_commands.py
```

معماری منجمد دست‌نخورده ماند: `domain` هیچ وابستگی بیرونی نگرفت (تست
`test_dependency_direction` سبز است)، و لایهٔ presentation فقط رندر می‌کند —
هیچ محاسبه‌ای در مرورگر انجام نمی‌شود، JS فقط ضبط را جلو می‌برد.
