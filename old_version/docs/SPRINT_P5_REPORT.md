# گزارش Sprint P5 — Execution & Portfolio Platform

**تاریخ:** ۲۰۲۶-۰۸-۱۶
**فاز:** Phase 28 — Implementation Foundation
**مرجع معماری:** `docs/Phases/Phase14.md` §19-24، §51-53 و `docs/Phases/Phase15.md`

---

## چه چیزی ساخته شد

زنجیره‌ی اجرا و حسابداری، که اولین نقطه‌ایست که پلتفرم می‌تواند به سؤال
**«واقعاً چقدر سود یا ضرر کردیم؟»** جواب بدهد:

```
TradingIntent (تأییدشده توسط risk gate)
      |
IntentResolver    -> ResolvedOrder      سیاست‌ها به عدد تبدیل می‌شوند
      |
ExecutionVenue    -> ExecutionResult    فیل واقعی، احتمالاً جزئی
      |
PortfolioLedger   -> PositionState      حسابداری PnL بر پایه‌ی فیل
```

### دامنه — `src/ShadBotTrader/domain/execution/`

| فایل | محتوا |
|---|---|
| `execution_types.py` | ۵ enum: IntentStatus، ExecutionStatus، PositionSide، TransactionType، ExecutionRejectionReason |
| `money.py` | `Money` — مقدار مالی علامت‌دار با ارز (بر خلاف `Balance` می‌تواند منفی باشد) |
| `fill.py` | `Fill`، `ExecutionResult` — قرارداد نتیجه‌ی اجرا |
| `resolved_order.py` | `ResolvedOrder` — سفارش قابل اجرا |
| `position_state.py` | `PositionState` — حسابداری تغییرناپذیر پوزیشن و PnL |
| `market_view.py` | `MarketQuote`، `ExecutionContext` |
| `ports.py` | ۴ قرارداد: IntentResolver، ExecutionVenue، PortfolioLedger، ExecutionJournal |
| `events.py` | ۱۱ رویداد دامنه |

### زیرساخت — `src/ShadBotTrader/infrastructure/execution/`

| کلاس | نقش |
|---|---|
| `DefaultIntentResolver` | تبدیل `QuantityPolicy`/`PricePolicy` به عدد واقعی |
| `SimulatedExecutionVenue` | اجرای قطعی با spread، slippage، کارمزد و فیل جزئی |
| `InMemoryPortfolioLedger` | پوزیشن‌ها، PnL، کارمزدها، تراکنش‌ها، equity |
| `InMemoryExecutionJournal` | ردّ حسابرسی اجرا |

### اپلیکیشن

`application/services/execution_service.py` — نقطه‌ی ترکیب که محافظ‌های
انقضا و idempotency را قبل از رسیدن به venue اعمال می‌کند.

---

## قواعد حسابداری (طبق Phase 15)

| قاعده | بخش | پیاده‌سازی |
|---|---|---|
| میانگین قیمت ورود از **فیل واقعی**، نه از intent | §24 | `PositionState.apply_fill` |
| realized PnL هنگام کاهش/بستن پوزیشن | §25 | همان‌جا، فقط روی بخش بسته‌شده |
| unrealized PnL بر مبنای قیمت جاری بازار | §26 | `unrealized_pnl(price)` |
| کارمزد **جدا** از PnL ناخالص | §27-28 | `realized_pnl` در مقابل `net_realized_pnl` |
| فیل جزئی به‌صورت native | §23 | `remaining_quantity` |
| `Decimal` برای همه‌ی مقادیر مالی؛ float ممنوع | §15-16 | سراسر پکیج |

**بازگشت پوزیشن (reversal)** طبق Phase 14 §57 به بستن + باز کردن تجزیه می‌شود
و فقط بخش بسته‌شده PnL محقق می‌کند.

---

## محافظت‌هایی که با تست تضمین شده‌اند

| محافظ | مرجع | تست |
|---|---|---|
| intent منقضی هرگز اجرا نمی‌شود | §52 | `test_expired_intent_is_never_executed` |
| یک intent دو بار فیل نمی‌شود | §53 | `test_duplicate_intent_is_executed_only_once` |
| دفتر فقط مقدار واقعاً معامله‌شده را ثبت می‌کند | §21 | `test_ledger_only_ever_reflects_real_fills` |
| قیمت ورود از فیل می‌آید نه از intent | §24 | `test_entry_price_comes_from_fills_not_from_the_intent` |

---

## 🐞 باگ بحرانی که پیدا و رفع شد

### تداخل شناسه‌ی intent — پوزیشن بسته نمی‌شد

`decision_id` فقط از `signal_id` ساخته می‌شد:

```python
decision_id = f"decision:{signal.signal_id}"   # ❌
```

و `signal_id` هم از `strategy:version:symbol:timeframe:timestamp`.

نتیجه: در یک کندل، تصمیم **ENTER** و تصمیم **EXIT** شناسه‌ی **یکسان** می‌گرفتند.
پس `intent_id` هم یکسان می‌شد، و محافظ idempotency در `ExecutionService`
خروج قانونی را به‌عنوان «intent تکراری» رد می‌کرد.

**اثر واقعی:** پوزیشن باز می‌شد ولی **هرگز بسته نمی‌شد** — دقیقاً بدترین
حالت ممکن برای یک ربات معامله‌گر. محافظ ایمنی خودش تبدیل به منبع ضرر می‌شد.

**رفع:** نوع تصمیم بخشی از شناسه شد:

```python
return f"decision:{decision_type.value}:{signal.signal_id}"   # ✅
```

سه تست رگرسیون در `TestDecisionIdentity` اضافه شد.

> این باگ را تست یکپارچگی `test_full_round_trip_produces_realised_pnl` گرفت —
> نه تست واحد. به همین دلیل تست end-to-end نوشتن ارزش دارد.

### مسئولیت دوگانه‌ی liquidity

هم `DefaultIntentResolver` و هم `SimulatedExecutionVenue` سقف liquidity را
اعمال می‌کردند. resolver سفارش را از قبل کوچک می‌کرد، پس venue همیشه آن را
کامل پر می‌دید و **فیل جزئی هرگز ثبت نمی‌شد**.

**رفع:** resolver اندازه‌ی *مطلوب* را می‌سازد؛ اعمال واقعیت بازار فقط کار
venue است.

---

## وضعیت کیفیت

| بررسی | نتیجه |
|---|---|
| `black --check .` | ✅ ۲۵۵ فایل |
| `ruff check .` | ✅ پاس |
| `mypy src` | ✅ ۱۹۴ فایل |
| `pytest` | ✅ **۳۳۱ passed, 6 skipped** |
| `RUN_TF=1 pytest` | ✅ **۳۳۷ passed** |

**رشد تست‌ها:** ۲۶۱ → **۳۳۷** (۷۶ تست جدید)

- ۲۷ تست حسابداری پوزیشن و PnL (همه با عدد دستی‌محاسبه‌شده)
- ۳۲ تست کامپوننت‌های اجرا
- ۱۴ تست یکپارچگی end-to-end
- ۳ تست رگرسیون شناسه‌ی تصمیم

---

## دستورات جدید

```bash
python scripts/run_execution.py

shadbot-exec quote   --mid 2000 --spread 2
shadbot-exec pnl     --entry 2000 --exit 2100 --quantity 2 --fee 4
shadbot-exec execute --side buy --quantity 5 --liquidity 2 --commission 0.0001
```

### نمونه خروجی دمو

```
time   mid     signal  decision executed             position               realised
0      2000    buy     enter    buy 2 @ 2001.4002    LONG 2 @ 2001.4002     0.00
5      2020    buy     hold     -                    LONG 2 @ 2001.4002     0.00
10     2050    sell    exit     sell 2 @ 2048.5902   flat                   94.38
15     2040    sell    enter    sell 2 @ 2038.5922   SHORT 2 @ 2038.5922    94.38
20     2010    buy     exit     buy 2 @ 2011.4022    flat                   148.76

  realised PnL      : 148.76 USD
  fees              : 1.61999696 USD
  net realised PnL  : 147.14000304 USD
```

اعداد دستی بررسی شدند: long از 2001.4002 تا 2048.5902 → ۹۴.۳۸ ✓
و short از 2038.5922 تا 2011.4022 → ۵۴.۳۸ ✓

---

## آنچه عمداً ساخته نشد

- **بروکر واقعی** — فقط venue شبیه‌سازی‌شده. طبق اصل «Simulation اول».
- **چند ارزی** — دفتر تک‌ارزی است؛ تبدیل ارز در فاز بعد.
- **مدل volatility برای sizing** — `QuantityPolicyType.VOLATILITY` مقدار
  مطلق را می‌پذیرد و در docstring مستند شده که مدل ندارد. **پیاده‌سازی
  قلابی نساختم.**
- **`Order`/`Trade`/`Position` قدیمی** دست‌نخورده ماندند. `ResolvedOrder` و
  `PositionState` مکمل آن‌ها هستند نه جایگزین؛ ادغامشان یک تصمیم معماری
  جداست که باید صریح گرفته شود.

---

## مرحله‌ی بعدی — Sprint P6: Simulation & Backtesting

طبق `docs/Phases/Phase16.md`:

1. **`SimulationClock`** — زمان قطعی و کنترل‌شده
2. **`BacktestEngine`** — اجرای زنجیره روی کندل‌های تاریخی
3. **`EquityCurve`** — سری زمانی ارزش پرتفوی
4. **معیارهای عملکرد** — drawdown، hit rate، profit factor، Sharpe
5. **`ReplayRunner`** — بازپخش یک جلسه از روی ژورنال‌ها

`project_state/generated/ChatGPT_Context.md` به‌روز شد و همین را ثبت کرده.
