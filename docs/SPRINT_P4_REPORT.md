# گزارش Sprint P4 — Trading Platform

**تاریخ:** ۲۰۲۶-۰۸-۱۶
**فاز:** Phase 28 — Implementation Foundation
**مرجع معماری:** `docs/Phases/Phase14.md` (Trading Platform Architecture)

---

## بخش ۱ — شفاف‌سازی آموزش مدل

### مشکل
`run_ai.py` هیچ خروجی‌ای در حین آموزش نمی‌داد. کاربر نمی‌دانست learning rate چقدر است،
چند epoch مانده، در کدام فولد است، یا اصلاً برنامه هنگ کرده یا نه. روی CPU بیش از
۱۵ دقیقه طول می‌کشید بدون یک خط خروجی.

**علت کندی:** `min_train_size=16, step=4` روی ~۳۹۰ نمونه یعنی **~۹۳ فولد**،
و roll-forward برای هر فولد یک مدل کامل از صفر می‌سازد.

### راه‌حل

فایل جدید: `src/ShadBotTrader/infrastructure/ai/training_progress.py`

یک قرارداد observer مستقل از فریم‌ورک:

| کلاس | نقش |
|---|---|
| `TrainingProgressReporter` | پروتکل observer (۵ متد چرخه‌عمر) |
| `TrainingPlanInfo` | توصیف ایستای اجرا (folds، epochs، lr، ...) |
| `FoldInfo` | مشخصات یک فولد (بازه‌های train/val) |
| `EpochMetrics` | متریک‌های پایان هر epoch |
| `ConsoleProgressReporter` | پیاده‌سازی کنسولی با نوار پیشرفت و ETA |
| `NullProgressReporter` | پیش‌فرض (کاملاً ساکت — رفتار قبلی حفظ می‌شود) |

خروجی الان:

```
==========================================================================
  TRAINING  gold_direction v1
==========================================================================
  framework      : tensorflow 2.21.0
  learning rate  : 0.00015
  epochs / fold  : 2
  folds          : 5  (roll-forward)
  total epochs   : 10
  batch size     : 16
  window x feats : 8 x 4
  samples        : 292
  seed           : 42
--------------------------------------------------------------------------
fold   1/5 | train[0:128] (128 samples) -> val[128:136] (8 samples)
  epoch 1/2 | loss 0.7198 | val_loss 0.7046 | acc 0.4453 | lr 1.50e-04
  epoch 2/2 | loss 0.7132 | val_loss 0.7047 | acc 0.4844 | lr 1.50e-04
[######----------------------]  20.0% | fold 1/5 | 3.5s/fold | eta 13s
...
--------------------------------------------------------------------------
  folds 5 | val_loss best 0.7047 / mean 0.7126 / worst 0.7280
  total training time: 15s
==========================================================================
```

### گزینه‌های جدید `run_ai.py`

```bash
python scripts/run_ai.py --quick          # اجرای سریع (~۳۰ ثانیه)
python scripts/run_ai.py --folds 10       # محدود کردن تعداد فولد
python scripts/run_ai.py --epochs 5 --learning-rate 1e-3
python scripts/run_ai.py --no-epoch-lines # فقط نوار فولد
python scripts/run_ai.py --no-progress    # خاموش کردن کامل
python scripts/run_ai.py --skip-evaluation
```

`--folds N` آخرین N فولد را نگه می‌دارد (جدیدترین داده) — هم در trainer و هم در
evaluator، تا ارزیابی با آموزش هماهنگ بماند.

> نکته: reporter هیچ اثری روی وزن‌ها، ترتیب یا determinism ندارد. پیش‌فرض
> `NullProgressReporter` است، پس رفتار کدهای موجود تغییر نکرده.

---

## بخش ۲ — Sprint P4: Trading Platform

### خط لوله‌ی پیاده‌سازی‌شده

```
StrategyContext -> Strategy -> TradingSignal
                                   |
                              SignalValidator      (schema، تازگی)
                                   |
                              DecisionEngine  -> TradingDecision
                                   |
                                RISK GATE          (اجباری)
                                   |
                              IntentFactory   -> TradingIntent
                                   |
                          Execution Platform (Sprint P5)
```

### دامنه — `src/ShadBotTrader/domain/strategy/`

| فایل | محتوا |
|---|---|
| `strategy_identity.py` | `StrategyId`، `StrategyVersion` (immutable) |
| `strategy_types.py` | ۹ enum: SignalType، DecisionType، IntentType، RejectionReason، ... |
| `signal.py` | `TradingSignal` — خروجی استراتژی، هرگز order |
| `strategy_context.py` | `StrategyContext`، `PredictionView`، `PortfolioView` |
| `decision.py` | `TradingDecision` — نتیجه‌ی تصمیم، هرگز order |
| `trading_intent.py` | `TradingIntent`، `QuantityPolicy`، `PricePolicy` |
| `risk_policy.py` | `RiskPolicy`، `RiskVerdict` |
| `ports.py` | ۷ قرارداد انتزاعی |
| `events.py` | ۷ رویداد دامنه |

### زیرساخت — `src/ShadBotTrader/infrastructure/trading/`

| کلاس | نقش |
|---|---|
| `AiDirectionalStrategy` | prediction → signal با اعتبارسنجی سن/اطمینان |
| `DefaultSignalValidator` | بررسی symbol/timeframe/تازگی |
| `ConfidenceWeightedAggregator` | ترکیب چند استراتژی (تساوی → HOLD) |
| `PositionAwareDecisionEngine` | signal + پوزیشن فعلی → decision |
| `PolicyRiskGate` | دروازه‌ی اجباری ریسک |
| `DefaultIntentFactory` | decision تأییدشده → intent |
| `InMemoryDecisionJournal` | ردّ حسابرسی |

### اپلیکیشن

`application/services/trading_decision_service.py` — تنها نقطه‌ای که مجاز است
`TradingIntent` تولید کند، و فقط برای تصمیم‌هایی که risk gate تأیید کرده.

---

## سه Invariant که با تست تضمین شده‌اند

| Invariant | مرجع | تست |
|---|---|---|
| استراتژی **signal** می‌دهد، نه order | §12 | `test_strategy_output_is_never_an_order` |
| `TradingDecision` **یک `Order` نیست** | §18 | `test_decision_is_never_an_order` |
| **هیچ intent بدون تأیید ریسک وجود ندارد** | §34 | `test_no_intent_is_ever_produced_without_an_approving_verdict` |

تست سوم مهم‌ترین است: ۷ سناریو × ۴ سیاست ریسک = ۲۸ ترکیب را می‌آزماید و
تأیید می‌کند در هیچ‌کدام intent بدون verdict تأییدشده ساخته نمی‌شود.

### تصمیم طراحی: خروج همیشه مجاز است

اگر drawdown از حد گذشته باشد، **ورود** مسدود می‌شود ولی **خروج** نه.
جلوگیری از بستن پوزیشن خودش یک ریسک است.

---

## 🐞 باگی که در حین کار پیدا و رفع شد

**`QuantityPolicy._value` روی متد `ValueObject._value()` سایه انداخته بود.**

```python
self._value = value          # ❌ فیلد Decimal روی متد را می‌پوشاند
```

نتیجه: `TypeError: 'decimal.Decimal' object is not callable` هنگام مقایسه‌ی
دو intent. تست determinism این را گرفت. فیلد به `_quantity` تغییر نام یافت.

> کل `src/` را برای همین الگو بررسی کردم: دو مورد مشابه در `Confidence` و
> `PredictionView` هست ولی **بی‌خطرند** چون از `ValueObject` ارث نمی‌برند.

---

## وضعیت کیفیت

| بررسی | نتیجه |
|---|---|
| `black --check .` | ✅ ۲۳۳ فایل |
| `ruff check .` | ✅ پاس |
| `mypy src` | ✅ ۱۷۸ فایل |
| `pytest` | ✅ **۲۵۵ passed, 6 skipped** |
| `RUN_TF=1 pytest` | ✅ **۲۶۱ passed** |

**رشد تست‌ها:** ۱۷۸ → **۲۶۱** (۸۳ تست جدید)

- ۱۷ تست دامنه‌ی استراتژی
- ۴۰ تست کامپوننت‌های trading
- ۱۹ تست یکپارچگی خط لوله
- ۷ تست گزارش پیشرفت آموزش

---

## دستورات جدید

```bash
python scripts/run_trading.py                  # دمو کامل خط لوله
shadbot-trading policy                         # نمایش سیاست ریسک
shadbot-trading evaluate --value 0.9 --confidence 0.85
shadbot-trading evaluate --value 0.9 --confidence 0.85 --drawdown 40 --max-drawdown 10
```

---

## آنچه عمداً ساخته نشد (طبق §3 فاز ۱۴)

Trading Platform مسئول این‌ها **نیست** و پیاده نشد:

- ارتباط با بروکر / صرافی
- اجرای فیزیکی order
- حسابداری portfolio
- موتور backtesting

این‌ها در Sprint P5 (Execution Platform) و بعد می‌آیند.

---

## مرحله‌ی بعدی — Sprint P5: Execution Platform

طبق `docs/Phases/Phase14.md` §19 و نقشه‌ی فازها:

1. **`ExecutionPort`** — قرارداد انتزاعی اجرا
2. **`IntentResolver`** — تبدیل `QuantityPolicy`/`PricePolicy` به مقادیر واقعی
3. **`SimulatedExecutor`** — اجرای شبیه‌سازی‌شده (اول این، طبق §7 اصول)
4. **`Order` lifecycle** — اتصال به `domain/trading/order.py` موجود
5. **Portfolio accounting** — ثبت `Trade` و `Position` واقعی

فایل `project_state/generated/ChatGPT_Context.md` هم به‌روز شد و
همین را به‌عنوان فاز بعدی ثبت کرده.
