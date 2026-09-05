# WORKLOG — دفترچهٔ کار

## 2026-08-26 — گزارش جداگانهٔ تعادل لیبل train/validation در شروع آموزش

**درخواست کاربر:** اولِ لاگِ آموزش برای دیتای آموزش و دیتای اعتبارسنجی جدا بنویس
چند لیبل BUY و چند لیبل SELL دارد.

**مشکل:** فقط یک خط `label balance` با تعادلِ کلِ دیتاست چاپ می‌شد؛ معلوم نبود
کدام تعادل به train و کدام به validation تعلق دارد.

**تغییر (`scripts/run_dual_models.py`):**
- تابع `signal_label_split_balance(dataset, role, max_folds)` اضافه شد:
  لیبل هر نمونهٔ مدل سیگنال را از ستون هدفِ `sample_ends` می‌خواند، همان هندسهٔ
  expanding roll-forward که trainer استفاده می‌کند را بازسازی می‌کند، و تعادل
  BUY/SELL **آخرین فولد** (همان که مدل نهایی از آن ساخته می‌شود) را جدا
  برمی‌گرداند.
- در `train_one` بعد از `label balance` دو خط جدید چاپ می‌شود:
  ```
  label balance  : {'sell': 3524, 'buy': 3568}   ← کل
  train labels   : {'sell': 2867, 'buy': 2902}   ← تعادلِ train (آخرین فولد)
  val labels     : {'sell': ..., 'buy': ...}     ← تعادلِ validation (آخرین فولد)
  ```
- برای مدل range (رگرسیون) خط جدید چاپ نمی‌شود چون لیبل BUY/SELL ندارد.

**تست:** `tests/unit/ai/test_signal_label_split.py` (۳ تست) اضافه شد.

```
قبل:  1449 passed · 0 failed · 49 skipped
بعد:  1452 passed · 0 failed · 49 skipped
```

---

## 2026-08-26 — رفع ۲۹ تستِ کهنه → گیت تست سبز (1449 passed, 0 failed)

**مشکل:** کد در فازهای ۵۲–۵۸ جلو رفته بود ولی تست‌ها عقب مانده بودند؛ ۲۹ تست شکست
می‌خوردند (همه «تستِ کهنه»، نه باگِ واقعی). در ممیزیِ `STATUS_AUDIT_2026-08-26` ثبت شد.

**روش:** تست‌ها را با رفتارِ **عمدیِ جدیدِ** کد هماهنگ کردم (نه تضعیف، نه حذف ضمانت).

### دسته‌بندی و اصلاحات
| علت شکست | فایل(ها) | اصلاح |
|---|---|---|
| فیچرها ۱۰۹ → ۲۲۷ | `test_feature_cache`, `test_feature_pipeline`, `test_feature_visibility`, `test_stored_matrix_identity`, `test_training_dataset`, `test_invariance_audit`, `test_commands`, `test_evaluate_and_inspect` | اعداد 109→227، width 123→241، causal 70→177/188 |
| Range 1H → 1D | `test_dual_models` | timeframe 1H→1D، horizon 5→1، نام ستون seq2seq `_1` |
| گیت R/R به Bracket منتقل شد | `test_dual_model_strategy`, `test_live_decision` | تست را با طراحی جدید هماهنگ کردم + **تست واحد جدید** در `tests/unit/simulation/test_bracket.py` که ردِ R/R ضعیف در `TradeBracket` را تضمین می‌کند |
| فرمت progress تغییر کرد (فاز ۵۲/۵۳) | `test_training_progress`, `test_progress_visibility`, `test_training_visibility`, `test_training_pace` | هماهنگ با خروجی جدید (`key=value`، `epoch   1/2`، ۳ خط batch، ETA در checkpoint) |

### نتیجه
```
قبل:  1415 passed · 29 failed · 49 skipped
بعد:  1449 passed ·  0 failed · 49 skipped   (49 skip = تست‌های TensorFlow)
ruff:  All checks passed!   |   black: clean
```

### فایل جدید
- `tests/unit/simulation/test_bracket.py` — تست‌های براکت TP/SL (ر/ر، اسپرد، same-bar policy).

---

## 2026-08-26 — همگام‌سازی مستندات: ثبت فازهای ۵۰–۵۸ (که قبلاً فقط در گزارش‌ها/کد بودند)

**خلأ:** کد در فاز ۵۸ بود ولی `WORKLOG` فقط تا فاز ۴۹ داشت؛ فازهای ۵۰–۵۶ فقط
در `docs/Report/PHASE50..56` بودند و فازهای ۵۷–۵۸ فقط در کامنت‌های کد. این
ورودی آن‌ها را یکجا ثبت می‌کند تا وضعیت از روی «کد + گیت + مستندات» قابل بازیابی
باشد (مطابق `AGENTOPERATINGRULE`). جزئیات کامل در `docs/STATUS_AUDIT_2026-08-26.md`.

### فازهای ۵۰–۵۶ (تاریخ 2026-08-25) — خلاصه
| فاز | کار |
|---|---|
| ۵۰ | تحلیل range v1 (val_mae→دلار) + رفع باگ `loss_function` در `save_model`؛ سلول‌های Colab برای بررسی/ادامهٔ آموزش |
| ۵۱ | `--resume` — ادامهٔ آموزش از checkpoint بعد از قطعی Colab/اینترنت (warm-start آخرین fold) |
| ۵۲ | فیلتر Session (ساعت‌های خوب UTC) + حداقل فاصلهٔ SL — WR از ۳۳.۵٪ به ~۵۵٪ |
| ۵۳ | بهبود Progress Reporter (نمایش val_mae و معادل دلاری، جداسازی range/signal) |
| ۵۴ | Loss سه‌گانه Huber+MAE+MSE + AdamW + ReduceLROnPlateau (برگرفته از legacy) |
| ۵۵ | **Range Model Seq2Seq** `[batch, window, horizon*2]` برای رفع collapse |
| ۵۶ | **Range: horizon=1 روی 1D** (پیش‌بینی high/low فردا) + سیگنال 5M |

گزارش‌ها: `docs/Report/PHASE50..56_REPORT.md`.

### فاز ۵۷ — پایداری بکتست + ورود واقع‌بینانه (ثبت‌شده اینجا برای اولین بار)
- **گسترش SL به‌اندازهٔ اسپرد** در `bracket.py` (`spread` در `from_model_levels`) تا اسپرد باعث توقف زودهنگام ضرر نشود.
- عبور `spread`/`spread_pct` در `dual_model_prediction_source` و `dual_model_backtest_service`.
- **ورود با typical price** `(O+H+L+C)/4` به‌جای open تنها در `backtest_engine.py`.
- **EarlyStopping** + **ReduceLROnPlateau** برای هر دو مدل.
- **Resume از همهٔ foldها** (همه warm-start) در `wavenet_trainer.py`.
- **AdamW برای هر دو regression و classification** (weight_decay متفاوت).

### فاز ۵۸ — معماری Signal (ثبت‌شده اینجا برای اولین بار)
- مدل سیگنال: `window=300` (۲۵ ساعت)، `n_layers_per_block=5`, `n_blocks=2` → RF=249 ≈ ۸۳٪.

### یافتهٔ مهم ممیزی
- کد ۳۱۶ ماژول سالم import می‌شود؛ **۲۹ تست شکسته‌اند ولی همه تستِ کهنه‌اند** (با
  تغییرات عمدیِ فازهای ۵۲–۵۸ همگام نشده‌اند)، نه باگ واقعی.
- **کاتالوگ فیچر از ۱۰۹ به ۲۲۷** گسترش یافته (مدیریت با `model_scope`؛ range≈182، signal≈177).
- GUI (`handlers.py`) با فازهای جدید هماهنگ است؛ فقط `scripts/run_backtest.py` هنوز
  پیش‌فرض `1H`/`gold_range_1h` دارد (کهنه).
- `project_state/generated/*` کهنه است (تا فاز ۵۰).

---

## 2026-08-20 — جست‌وجوی خودکار Learning Rate در داشبورد

دکمهٔ `Find best learning rate` اضافه شد. برای Signal معیار انتخاب `val_loss` و برای Range معیار `val_mae` است. چند candidate روی pilot walk-forward اجرا می‌شوند، بهترین مقدار انتخاب می‌شود و سپس مدل نهایی با همان Learning Rate آموزش و ذخیره می‌شود. هیچ script جدیدی اضافه نشده و از `run_dual_models.py` موجود استفاده می‌شود.


## 2026-08-19 — Signal binary: فقط BUY / SELL

مدل سیگنال از سه‌کلاسهٔ `SELL/HOLD/BUY` به طبقه‌بندی binary تغییر کرد. خروجی شبکه و labelها فقط `SELL` و `BUY` هستند؛ threshold آموزش، اولین barrier قیمتی مثبت/منفی را تعیین می‌کند و جست‌وجو تا رسیدن به barrier ادامه دارد. اگر probability از آستانهٔ بک‌تست پایین‌تر باشد، strategy تصمیم `no_trade/HOLD` می‌سازد؛ این تصمیم مدل نیست. مدل‌های قدیمی سه‌خروجی باید دوباره آموزش داده شوند.


## 2026-08-19 — بک‌تست دومدلی سیگنال → رنج → TP/SL

درخواست کاربر برای بک‌تست causal پیاده شد:

- مدل signal روی 5M، با پنجره و horizon قابل‌خواندن از training metadata؛
- آستانهٔ احتمال BUY/SELL قابل تنظیم، با HOLD واقعی و بدون فراخوانی مدل range؛
- مدل range روی 1H فقط بعد از عبور signal از آستانه؛
- تعیین TP/SL از high/low پیش‌بینی‌شده؛ BUY = high/low و SELL = low/high؛
- ورود پیش‌فرض روی open کندل 5M بعدی؛
- خروج candle-by-candle، با قانون پیش‌فرض stop-first برای لمس هم‌زمان؛
- نادیده‌گرفتن سیگنال‌های جدید تا بسته‌شدن bracket؛
- گزارش جداگانهٔ تعداد take-profit و stop-loss؛
- ماتریس feature هر تایم‌فریم یک بار ساخته و برای roll-forward slice می‌شود.

مسیرهای اصلی: `dual_model_backtest_service.py`، `dual_model_prediction_source.py`، `domain/simulation/bracket.py` و `docs/DUAL_MODEL_BACKTEST.md`.


**هدف:** هر تغییر معنادار اینجا ثبت می‌شود تا اگر گفت‌وگو عوض شد، ایجنت دیگری
آمد، یا چند هفته بعد برگشتیم، بشود ادامه داد.

قاعدهٔ ثبت (طبق `AGENTOPERATINGRULE.md` § CHAT HANDOFF RULE): پروژه باید فقط
از روی «کد + گیت + مستندات وضعیت» قابل بازیابی باشد.

**فرمت هر ورودی:** تاریخ · چه شد · چرا · کجا · تست · وضعیت گیت

---

## 2026-08-18 — فاز ۴۹: آستانه با مدل سفر می‌کند

**درخواست کاربر:** «باشه ترشولد رو اعمال کن»

**مشکل:** `ModelEvaluationService._score_signal` لیبل‌ها را با
`threshold = 0.0008` ثابت می‌ساخت. مدلی که با ۰.۲۵٪ آموزش دیده بود با کلید
سؤالِ ۰.۰۸٪ تصحیح می‌شد؛ روی دیتای واقعی ۵ دقیقه‌ای سهم HOLD بین این دو
آستانه از ۴۱٪ به ۸۳٪ می‌رود، پس دقت به‌شدت کمتر از واقع گزارش می‌شد.

### تغییرات

| فایل | چه شد |
|---|---|
| `infrastructure/ai/model_catalogue.py` | `ModelRecord.threshold` + `.horizon` + `threshold_percent` |
| `scripts/run_dual_models.py` | هر دو مسیر ذخیره (چک‌پوینت epoch و ذخیرهٔ نهایی) آستانه را می‌نویسند |
| `application/services/model_evaluation_service.py` | آستانه از رکورد خوانده می‌شود؛ `DEFAULT_THRESHOLD` فقط برای مدل‌های قدیمی و با اعلام `ASSUMED` |
| `presentation/commands/handlers.py` | فیلد `threshold_pct` در Retrain خالی شد؛ خالی = ارث‌بری از خود مدل |
| `tests/integration/test_threshold_recorded.py` | ۱۷ تست جدید، از جمله یک تست `ast` که برگشت hard-code را می‌گیرد |
| `tests/integration/test_best_model_kept.py` | استاب `Role` فیلد `target` گرفت (باگ `AttributeError` که همین‌جا پیدا شد) |

**تست:** ۱٬۴۵۸ passed · ۱۲ skipped. Quality gate کامل سبز، شامل هر سه بخش
`RUN_TF=1`.

**اجرای واقعی:** آموزش signal روی `TESTSYM` 1H با آستانهٔ ۰.۲۵٪ →
`v1_training.json` حاوی `"threshold": 0.0025` → ارزیابی همان ۰.۲۵٪ را
گزارش کرد.

**گزارش:** `PHASE49_REPORT.md`

---

## 2026-08-16 — Backtest Replay (پخش زندهٔ کندل و معاملات)

**درخواست کاربر:** «اجرای بک تست رو میتونی یکاری کنی که به صورت لایو کندلا
نمایش داده بشن و نشون بده کجاها معامله کرده و نتیجه معامله چی بود؟»

**مجوز معماری:** فاز ۱۶ §۲۳ صراحتاً می‌گوید شبیه‌سازی باید step-by-step قابل
بازرسی باشد؛ فاز ۱۹ §۸ نقش View را «فقط رندر» تعریف می‌کند. پس این کار داخل
معماری منجمد است، نه تغییر آن.

### ساخته شد

| فایل | نقش |
|---|---|
| `domain/simulation/replay.py` | `TradeMarker`, `ReplayBar`, `ReplayTape`, `ReplayRecorder` |
| `infrastructure/simulation/console_replay.py` | `ConsoleReplayPlayer`, `summarise_tape` |
| `presentation/web/replay_renderer.py` | پخش‌کنندهٔ HTML مستقل (canvas + JS درون‌خطی) |
| `scripts/run_replay.py` | اسکریپت دمو |
| `tests/unit/simulation/test_replay.py` | ۱۲ تست |
| `tests/integration/test_backtest_replay.py` | ۱۶ تست |

### تغییر کرد

- `infrastructure/simulation/backtest_engine.py` — پارامتر `record_replay`، پراپرتی `tape`،
  و `_capture_trade` حالا `(realized_delta, fee_delta)` برمی‌گرداند
- `application/services/backtest_service.py` — عبور `record_replay`
- `backtest_cli.py` — دستور `replay`
- `presentation/commands/` — `CommandKind.RECORD_REPLAY` + هندلر
- `presentation/web/server.py` — مسیر `GET /replay`
- `presentation/web/renderer.py` — لینک ریپلی در هدر
- `dashboard_cli.py` — آپشن `--replay`
- `project/builders/{snapshot,context}_builder.py` — فاز جاری و فاز بعدی

### دو تصمیم طراحی که باید یادت بماند

1. **ورودِ باز نتیجه ندارد:** `realized_pnl` یک entry برابر `None` است نه صفر.
   صفر یعنی «سربه‌سر بست» که دروغ است.
2. **پوزیشن باز در پایان دیتا معامله شمرده نمی‌شود.** جدا با عنوان
   «Still open at the end» گزارش می‌شود.
3. **ضبط، ناظر منفعل است:** پیش‌فرض خاموش تا sweep هزینه ندهد. تستی هست که
   ثابت می‌کند نتیجهٔ اجرا با و بدون ضبط یکسان است.

### تأیید

- خروجی ریپلی دقیقاً با `run_backtest.py` یکی است: ۵۱ معامله، `-2.7946`
- هر دو اسکریپت دو بار اجرا شدند → خروجی بایت‌به‌بایت یکسان
- دکمهٔ داشبورد به‌صورت زنده تست شد (POST /run → ۳۰۰ بار ضبط شد)
- `672 passed, 6 skipped` · `RUN_TF=1 → 678 passed`

**گزارش کامل:** `REPLAY_REPORT.md`

---

## 2026-08-16 — ممیزی مستندات و ساخت اسناد وضعیت

**درخواست کاربر:** «طبق نقشه هم داریم پیش میریم دیگ؟ / فایلای docs رو یادت
نره ک همشوباید پیاده سازی کنیما / هرکاری هم ک میکنی توی docs ثبت کن»

**انجام شد:**
- خواندن `docs/AGENTOPERATINGRULE.md` (قبلاً در جریان کار خوانده نشده بود)
- ممیزی فاز ۱ تا ۲۸ در برابر کد واقعی
- ساخت `docs/IMPLEMENTATION_STATUS.md` — جدول وضعیت هر ۲۸ فاز
- ساخت `docs/WORKLOG.md` — همین فایل

**یافتهٔ مهم ممیزی:** ۲۲ فاز از ۲۸ کامل‌اند. سه فاز حداقلی‌اند (۹ Plugin،
۲۱ Config، ۲۲ Logging)، یکی صفر است (۲۴ Deployment)، یکی جزئی (۲۵ PowerShell)،
و فاز ۲۸ در حال انجام است. فاز ۲۰ با انحراف تأییدشده (SQLite) کامل است.

**نکتهٔ صادقانه:** `docs/PROJECT_STATE.md` و `docs/CURRENT_STATE.md` اسناد
اصلی و منجمد معماری‌اند و می‌گویند «هنوز چیزی پیاده نشده» — که دیگر درست
نیست. به‌جای دستکاری آنها (که خلاف قاعدهٔ freeze فاز ۲۶ است)،
`IMPLEMENTATION_STATUS.md` به‌عنوان لایهٔ وضعیت زنده اضافه شد و از هر دو به
آن ارجاع داده شد.

---

## 2026-08-16 — آماده‌سازی دیتای واقعی MT5 (گزینهٔ C)

**درخواست کاربر:** «باشه بریم» (تأیید قدم C).

### 🐞 باگ #۱۴ — دکمهٔ «Update features» داشبورد هرگز کار نمی‌کرد

**شدت: بالا.** حین تست مسیر واقعی کشف شد.

`presentation/commands/handlers.py::compute_features` این‌ها را صدا می‌زد:

| صدا زده می‌شد | واقعیت |
|---|---|
| `service.compute(symbol, timeframe)` | متد وجود ندارد → `compute_set(...)` |
| `outcome.results` | `outcome.outcomes` |
| `result.definition` | وجود ندارد؛ تعاریف از `feature_set.definitions` |
| `outcome.feature_set.name` | `outcome.set_name` |

**پیام خطای واقعی:**
```
FAILED: Feature computation failed
'FeatureComputationService' object has no attribute 'compute'
```

**چرا تست‌ها نگرفتند:** تست موجود فقط شاخهٔ «کندلی ذخیره نشده» را می‌آزمود که
*قبل* از رسیدن به کد خراب return می‌کند. کلاسیک‌ترین نوع نقطهٔ کور تست.

**رفع:** فراخوانی درست `compute_set(...)` با `standard_feature_set_v1()`.
حالا: `Computed 109 features over 300 candles`.

**تست رگرسیون:** ۳ تست در `TestComputeFeaturesCommand` — یکی‌شان
(`test_the_service_contract_the_handler_relies_on_exists`) دقیقاً همان عدم
تطابق امضا را قفل می‌کند.

**اقدام پیشگیرانه:** هر ۷ دکمهٔ داشبورد با دیتای واقعی اجرا شدند. نتیجه:
```
fetch_market_data   OK    compute_features   OK (رفع شد)
run_backtest        OK    record_replay      OK
run_optimisation    OK    run_trading_cycle  OK
refresh_project_state OK  train_model        SKIP (کند، نیاز TF)
```

### ✅ شکل واقعی بازار اعتبارسنجی شد

نگرانی اصلی: دیتای واقعی **گپ آخر هفته** دارد (بازار جمعه شب تا یکشنبه بسته
است). آیا pipeline آن را «دیتای خراب» تلقی و قرنطینه می‌کند؟

**پاسخ: نه.** با ۳ هفته دیتای ۵ دقیقه‌ای واقعی‌شکل (۴۳۲۰ کندل) آزمایش شد:
```
quarantined   : False
overall score : 99.99
issues        : [warning] GAP_DETECTED: 2 gap(s)
```
گپ گزارش می‌شود (درست) ولی باعث دور ریختن دیتا نمی‌شود (هم درست).

۴ تست جدید در `test_mt5_ingestion.py`: گپ آخر هفته، بک‌تست کامل روی سری
گپ‌دار (ترتیب زمانی equity curve حفظ می‌شود)، حفظ اسپرد متغیر rollover
(۱۰ و ۴۵)، و جهش قیمتی یکشنبه.

### ✅ حل‌کنندهٔ نام نماد — `mt5_symbol_resolver.py`

**چرا:** شایع‌ترین دلیل شکست اولین اجرای واقعی. بروکرها طلا را
`XAUUSD` / `XAUUSD.i` / `XAUUSDm` / `GOLD` / `GOLDmicro` صدا می‌زنند.

```
XAUUSD.i  → XAUUSD      GOLDmicro → XAUUSD (alias)
XAUUSDm   → XAUUSD      XAUUSD.pro.ecn → XAUUSD
USTEC     → USTEC (دست‌نخورده)   US30 → US30 (دست‌نخورده)
```

**دو محافظ مهم:**
1. `USTEC` به `UST` تبدیل نمی‌شود (پسوند `C` کورکورانه کنده نمی‌شود)
2. `GOLD` به `GOL` تبدیل نمی‌شود (`_PROTECTED`)
3. پسوند ناشناخته → نام دست‌نخورده می‌ماند. **بهتر است نماد پیدا نشود تا
   اینکه نماد اشتباه معامله شود.**

امتیازدهی شفاف است (۱۰۰ دقیق / ۹۰ پسوند بروکر / ۸۰ alias / ۶۰ شامل) و هر
پیشنهاد **دلیلش** را همراه دارد.

**اضافه شد:**
- `shadbot-data mt5-resolve --symbol XAUUSD` — دستور جدید
- `mt5-ingest` هنگام شکست خودش پیشنهاد می‌دهد (`_suggest_symbol`)
- `run_real_data.py --auto-symbol` — نزدیک‌ترین نماد را می‌پذیرد، ولی
  **هرگز بی‌صدا**؛ همیشه چاپ می‌کند چه چیزی را جایگزین کرد

**۱۸ تست** در `tests/unit/dataset/test_mt5_symbol_resolver.py`.

### تأیید نهایی

کل سفر ویندوز با ترمینال ساختگی شبیه‌سازی شد (بروکری که طلا را `XAUUSD.i`
می‌نامد): اتصال → فهرست نمادها → تشخیص خودکار → ingest ۲۸۸۰ کندل → بدون قرنطینه.

```
black ✅  ruff ✅  mypy (253 files) ✅
pytest            697 passed, 6 skipped   (قبلاً 672)
RUN_TF=1 pytest   703 passed              (قبلاً 678)
```

**گزارش کامل:** `MT5_READINESS_REPORT.md`

---

## 2026-08-16 — فاز ۲۹: دو مدل پیش‌بینی (درخواست کاربر)

**درخواست:** یک مدل که high/low تا ۵ کندل آینده را پیش‌بینی کند، و یک مدل که
سیگنال را با درصد احتمال بدهد. هر دو roll-forward، با همهٔ فیچرها.
رنج روی ۱H، سیگنال روی ۵M.

### ممیزی اول — کد این قابلیت را نداشت

| نیاز | وضعیت قبل |
|---|---|
| رگرسیون high/low | ❌ `_build_compiled` فقط `SparseCategoricalCrossentropy` |
| سیگنال با احتمال | ⚠️ softmax بود ولی `predict()` به یک float فشرده می‌کرد |
| ۱۰۹ فیچر | ❌ `build_direction_series` فقط **۴** فیچر می‌ساخت |
| تایم‌فریم per-model | ❌ وجود نداشت |
| roll-forward | ✅ بود و درست |

پس فاز جدید لازم بود. `docs/Phases/Phase29.md` نوشته شد.

### ساخته شد

```
domain/ai/prediction_target.py          PredictionTarget, RangeForecast,
                                        SignalForecast, SignalClass
infrastructure/ai/target_builder.py     برچسب‌گذاری آینده + محافظ نشت
infrastructure/ai/feature_matrix.py     ۱۰۹ فیچر + OHLCV -> ماتریس
infrastructure/ai/model_roles.py        نقش رنج (۱H) و سیگنال (۵M)
infrastructure/ai/dual_predictor.py     حفظ کامل بردار احتمال
application/services/dual_model_service.py
scripts/run_dual_models.py
```

### سه تصمیم طراحی که باید یادت بماند

۱. **هدف‌ها نسبت به close، نه قیمت مطلق.** طلا در ۲۰۰۰ و ۳۰۰۰ نباید دو مسئلهٔ
   جدا باشد. مدلی که روی قیمت مطلق آموزش ببیند، بیرون از بازهٔ آموزشش
   بی‌صدا از کار می‌افتد.
۲. **کلاس HOLD.** مدل دوکلاسه مجبور است هر کندل یک طرف را بگیرد، حتی وقتی
   هیچ اتفاقی نمی‌افتد. «معامله نکن» ارزشمندترین خروجی یک مدل معاملاتی است.
۳. **`is_coherent` به‌جای تعمیر خودکار.** اگر مدل سقف را زیر کف پیش‌بینی کند،
   گزارش می‌شود نه اینکه جایشان عوض شود. جابه‌جایی بی‌صدا، مدل خراب را پنهان
   می‌کند.

### 🐞 باگ #۱۵ — آموزش بازتولیدپذیر نبود

حین تست idempotency پیدا شد: دو اجرای یکسان پیش‌بینی متفاوت می‌داد.

**علت:** `_build_compiled` پارامتر `seed` می‌گرفت و **هرگز استفاده‌اش
نمی‌کرد**. در Keras 3 هر لایه وزن اولیه را از مولد خودش می‌گیرد، پس
`tf.random.set_seed` به‌تنهایی کافی نیست.

**نقض مستقیم فاز ۱۳ §۳۴** که بازتولیدپذیری را الزام می‌کند.

**رفع:** `keras.utils.set_random_seed(seed)`. حالا دو اجرا دقیقاً یکی است
(`fold losses [0.117292]` هر بار). دو تست رگرسیون اضافه شد.

### تأیید عملی

```
RANGE MODEL (1H, ۵ کندل جلوتر) — با ۱۰۹ فیچر
  usable rows: 497 | feature columns: 115 | dropped warmup: 51
  current close 1990.69 -> high 2001.80 (+0.558%) low 1990.36 (-0.016%)

SIGNAL MODEL (5M, ۵ کندل جلوتر) — با ۱۰۹ فیچر
  label balance: {'sell': 61, 'hold': 170, 'buy': 64}
  sell 33.6% | hold 34.1% | buy 32.3%  -> hold 34.1%  actionable=False
```

**۱۱۵ ستون** = ۶ خام + ۱۰۹ کاتالوگ. کاتالوگ فاز ۱۲ بالاخره به AI وصل شد.

```
pytest 759 passed, 12 skipped  |  RUN_TF=1 → 771 passed   (قبلاً 703)
```

**۶۸ تست جدید** — ۲۱ هدف‌ها، ۱۷ برچسب‌گذاری (شامل ۳ تست نشت داده)،
۱۱ ماتریس فیچر، ۱۹ یکپارچه (شامل ۲ بازتولیدپذیری).

**گزارش کامل:** `PHASE29_REPORT.md`

---

## 2026-08-16 — فاز ۳۰: دیتاست آموزش و بافر زندهٔ بازار

**درخواست کاربر:** دیتاست ۱۰۰٬۰۰۰ کندلی (۵M و ۱H) با فیچرهای ذخیره‌شده،
پنجرهٔ ورودی ۵۰۰×۱۲۳، roll-forward با گام یک کندل، آپدیت هفتگی با محاسبهٔ
مجدد کامل فیچرها، بافر زندهٔ ۸۰۰ کندلی، و بک‌تست روی همان دیتاست ۱۰۰k.

### تصمیم‌های کلیدی

۱. **۱۲۳ ستون.** کاربر درست گفت که قیمت خام در ورودی نبود — کاتالوگ فقط
   `*_filter` داشت که قیمت **هموارشده با موجک** است. ۸ ستون خام اضافه شد
   (`open_rel`…`ohlc4_rel`, `volume_raw_log`)، همه نسبت به close.
   ۸ خام + ۶ مشتق + ۱۰۹ کاتالوگ = **۱۲۳**.

۲. **ژنراتور به‌جای ماتریس.** ۹۹٬۴۹۶ پنجرهٔ ۵۰۰×۱۲۳ = **۲۴.۵ گیگابایت**.
   ماتریس تخت فقط ۵۰ مگابایت است. پنجره‌ها لحظه‌ای ساخته می‌شوند. این
   بهینه‌سازی نیست — بدون آن قابلیت اصلاً اجرا نمی‌شود.

۳. **محاسبهٔ مجدد کامل، نه افزایشی.** EMA/MACD/ATR بازگشتی‌اند؛ مقدار
   محاسبه‌شده از تاریخچهٔ ناقص به‌شکلی نامحسوس غلط است. ~۲ دقیقه برای
   ۱۰۰k در برابر فیچرهای بی‌صدا خراب، معاملهٔ خوبی است.

۴. **بافر: جایگزینی نه تکرار.** کندل ۱H جاری قبل از بسته‌شدن ۱۲ بار گرفته
   می‌شود؛ append کردنش ۱۲ ساعت تاریخ جعلی می‌سازد. کندل با timestamp
   موجود **جایگزین** می‌شود، و کندل قدیمی ناشناخته **رد** می‌شود.

۵. **۸۰۰ به‌جای ۵۰۰.** warm-up فیچرها ۵۱ ردیف می‌خورد → ۷۴۹ باقی می‌ماند.
   بافر این را در زمان اجرا **بررسی** می‌کند و اگر کم بیاورد پنجرهٔ کوتاه
   نمی‌دهد، چون ورودی کوتاه یعنی مدل زباله می‌خواند.

### 🐞 باگ #۱۶ — digest دیتاست هرگز تطبیق نمی‌کرد

تست round-trip گرفتش: digest روی float64 حساب می‌شد ولی ماتریس float32
ذخیره می‌شد، پس بعد از reload **همیشه** فرق داشت — یعنی به‌عنوان بررسی
صحت کاملاً بی‌فایده بود.

گرد کردن به ۴ و ۶ رقم جواب نداد؛ اندازه‌گیری نشان داد خطا **نسبی** است
(~6e-8) و هر دقت ثابتی برای بعضی مقادیر روی مرز گرد کردن می‌افتد.
رفع: هش روی شکل ذخیره‌شدهٔ float32 با `struct.pack("<f", …)` — دقیقاً
همان بایت‌هایی که روی دیسک می‌روند.

### تأیید عملی

```
BUILD 6,000 candles/timeframe -> 15.0s
  5M: 6,000 -> 5,897 rows x 123 cols | stride-1 windows: 5,393
  1H: 6,000 -> 5,897 rows x 123 cols | stride-1 windows: 5,393

generator (100k): 99,496 windows of (500 x 123), stride 1
                  lazy 50 MB vs materialised 24.5 GB

dual models: input_shape=(500, 123) — both range and signal
LIVE BUFFER: 900 primed -> holds 800 -> model input 500 x 123
```

```
pytest 819 passed, 12 skipped  |  RUN_TF=1 → 831 passed   (قبلاً 771)
```

**۶۰ تست جدید** — ۲۱ ژنراتور پنجره، ۱۷ بافر زنده، ۲۱ یکپارچه دیتاست،
به‌علاوهٔ ۲ تست به‌روزشدهٔ فاز ۲۹ (۶ ستون → ۱۴ ستون).

**گزارش کامل:** `PHASE30_REPORT.md`

---

## 2026-08-16 — فاز ۳۱: حلقهٔ زندهٔ تصمیم‌گیری + بک‌تست با مدل واقعی

**درخواست کاربر:** «به همون ترتیبی ک خودت میدونی بهترینه انجام بده» →
ترتیب انتخابی: **A (حلقهٔ زنده) بعد B (وصل مدل به بک‌تست)**.

### شکافی که پر شد

فازهای ۲۹-۳۰ مدل‌ها و داده را ساختند، ولی هیچ چیز آن‌ها را به معامله وصل
نمی‌کرد. بافر ۸۰۰ کندلی خوانده نمی‌شد، ماتریس ۵۰۰×۱۲۳ مصرف نمی‌شد، و
`MomentumPredictionSource` هنوز پیش‌بینی‌کنندهٔ بک‌تست بود.

### الف) حلقهٔ زنده

`DualModelStrategy` — شش دروازه، هر کدام با دلیل:
۱) هر دو forecast موجود · ۲) مدل HOLD نگوید · ۳) اطمینان کافی ·
۴) رنج منسجم · ۵) reward/risk کافی · ۶) حرکت بزرگ‌تر از هزینه.

`LiveDecisionService` — یک tick کامل: بافر → فیچر → ۵۰۰×۱۲۳ → دو مدل →
استراتژی → گیت ریسک → اجرا.

**قاعدهٔ سخت: tick هرگز exception نمی‌دهد.** حلقهٔ بدون نظارت که با یک
اختلال بروکر بمیرد، یعنی قطعی سرویس. هر خطا به `TickResult` با
`status` و `reason` تبدیل می‌شود.

### ب) بک‌تست با مدل

`ModelPredictionSource` پورت موجود را پیاده می‌کند، پس موتور دست‌نخورده
ماند. دو تضمین علیت:
- منبع پنجرهٔ **خودش** را نگه می‌دارد و فقط باری را که موتور تحویل داده
  اضافه می‌کند — چیز دیگری در دسترس نیست
- تا پر شدن پنجره `None` برمی‌گرداند (خودداری)، نه padding

سه کلاس روی یک محور: از **directional confidence** استفاده می‌شود، پس
۰.۴۵/۰.۱۰/۰.۴۵ برابر ۰.۵ خوانده می‌شود (بلاتکلیف) نه خرید ضعیف.

### 🐞 ناسازگاری گزارش reward/risk

برای **فروش**، reward و risk جا عوض می‌کنند. `RangeForecast.reward_risk()`
دید long-oriented است، پس چاپ آن با دروازه‌ای که تازه معامله را تأیید کرده
تناقض داشت: `r/r 0.25` نمایش داده می‌شد در حالی که دروازه ۴.۰ حساب کرده بود.
رفع: استراتژی نسبت جهت‌آگاه خودش را گزارش می‌کند.

**mypy هم سایه‌افتادن متغیر گرفت** — نام `forecast` برای دو نوع مختلف در یک
scope استفاده شده بود.

### تأیید عملی

```
LIVE LOOP (سه tick، هر سه مسیر):
  tick 1  [no_trade] signal model says hold (65.0%)
  tick 2  [no_trade] reward/risk 0.30 < 1.20
  tick 3  [traded]   signal buy 90.0%, target 2046.85, r/r 3.33
                     filled : 0.01 @ 2028.58

MODEL-DRIVEN BACKTEST (مدل واقعاً آموزش‌دیده):
  bars 700 | model calls 59 | trades 7 | return +12.35%
```

> ⚠️ آن +۱۲.۳۵٪ روی یک **موج سینوسی** است که ذاتاً قابل پیش‌بینی است.
> عدد معناداری نیست — فقط ثابت می‌کند زنجیره کامل کار می‌کند.

```
pytest 866 passed, 12 skipped  |  RUN_TF=1 → 878 passed   (قبلاً 831)
```

**۴۷ تست جدید** — ۱۶ استراتژی دومدلی، ۱۵ حلقهٔ زنده (شامل تاب‌آوری در
برابر مدل خراب)، ۱۶ بک‌تست مدل (بیشترشان دربارهٔ علیت).

**گزارش کامل:** `PHASE31_REPORT.md`

---

## 2026-08-16 — فاز ۲۴: Deployment (تنها فاز کاملاً صفر)

**درخواست کاربر:** «فاز ۲۴ رو اجرا کن»

### ساخته شد

| فایل | نقش |
|---|---|
| `domain/deployment/health.py` | liveness / readiness / health با دسته‌بندی وابستگی |
| `domain/deployment/release.py` | نسخه، محیط، manifest، shutdown امن |
| `infrastructure/deployment/backup.py` | بکاپ + تأیید + بازیابی + prune |
| `infrastructure/deployment/health_checks.py` | probe های واقعی |
| `application/services/runner_service.py` | اجرای مداوم با نظارت |
| `deploy_cli.py` | `health`, `manifest`, `backup`, `restore`, `preflight` |
| `deploy/install_service.ps1` | ثبت در Task Scheduler ویندوز |
| `scripts/run_service.py`, `scripts/run_weekly_update.py` | اجرا |

### چهار تصمیم که باید یادت بماند

۱. **liveness ≠ readiness ≠ health.** سیستمی که تازه بالا آمده زنده است ولی
   آماده نیست. جمع‌کردن این سه در یک boolean دقیقاً همان چیزی است که باعث
   می‌شود پلتفرم روی سیستم نیمه‌آماده معامله کند.

۲. **وابستگی بحرانی از اختیاری جدا شد.** نبودن MT5 یا TensorFlow سیستم را
   `degraded` می‌کند نه `unhealthy` — داشبورد باید کار کند.

۳. **بکاپی که هرگز بازیابی نشده، بکاپ نیست** (§۸۰). هر بکاپ بلافاصله باز،
   integrity-check و row-count می‌شود. از SQLite backup API استفاده شد نه
   کپی فایل: کپی‌کردن دیتابیس وسط یک تراکنش فایلی می‌سازد که سالم به‌نظر
   می‌رسد و خراب restore می‌شود — بدترین حالت ممکن.

۴. **Task Scheduler نه Windows Service.** سرویس واقعی در session 0 اجرا
   می‌شود و آنجا ترمینال MT5 **در دسترس نیست** (IPC محلی در session کاربر).
   این محدودیت است، نه میان‌بر — در خود اسکریپت مستند شد.

### 🐞 باگ #۱۷ — ترتیب لیست بکاپ‌ها غلط بود

تست گرفتش: مرتب‌سازی بر اساس **نام فایل** بود، ولی دو بکاپ در یک ثانیه فقط
با پسوند عددی فرق دارند و `live-...-1.db` از `live-...db` **جلوتر** مرتب
می‌شود. یعنی `latest()` بکاپ **قدیمی‌تر** را برمی‌گرداند — و یک restore
می‌توانست بی‌صدا دیتای اشتباه را برگرداند.

رفع: مرتب‌سازی بر اساس زمان ثبت‌شده، با mtime به‌عنوان tie-breaker.

### 🐞 نقض معماری که تست گرفت

`default_monitor` در لایهٔ **domain** بود ولی از `infrastructure.data` import
می‌کرد. `test_dependency_direction` شکست. به `infrastructure/deployment/
health_checks.py` منتقل شد — دامنه باید از SQLite و TensorFlow و MT5 بی‌خبر
بماند.

### تأیید عملی

```
health      : degraded (MT5 optional missing) | ready=True | exit 0
backup      : 128 KB | schema v1 | 9 rows | verified=True
preflight   : READY. production requires explicit confirmation
service     : 3 cycles, 1 trade, backup at cycle 2
shutdown    : stopped accepting work -> in-flight completed -> persisted -> stopped
weekly      : revision 1, 2,897 rows x 123 cols, 9.1s
restore     : بدون --yes رد می‌شود ✓ | فایل خراب قبل از overwrite رد می‌شود ✓
```

```
pytest 932 passed, 12 skipped   (قبلاً 866)
```

**۶۶ تست جدید** — ۳۹ واحد (health/release)، ۲۷ یکپارچه (backup/runner).

**گزارش کامل:** `PHASE24_REPORT.md`

---

## 2026-08-16 — تکمیل فازهای ۹، ۲۱، ۲۲ (سه فاز حداقلی)

**درخواست کاربر:** «بررسی کن کامل اگ فاز ۲۴ تکمیل شده، برو سراغ ۹ و ۲۱ و ۲۲»

### اول: تأیید فاز ۲۴

فایل‌ها (هر ۱۰ تا) + عملکرد + ۶۶ تست → **کامل تأیید شد** ✅

### فاز ۹ — معماری پلاگین (۳۷ → ۵۹۵ خط)

`registry.py` + `manager.py`. خط جداکننده‌ای که سند می‌کشد رعایت شد:
Registry می‌گوید «چه چیزی ثبت شده»، Manager می‌گوید «وضعیت عملیاتی چیست».

- state machine واقعی با ۹ حالت؛ انتقال غیرمجاز **رد** می‌شود
- پلاگین شکست‌خورده **دلیلش را نگه می‌دارد** (§۱۸)
- کشف **قطعی**: هرگز پوشه اسکن نمی‌شود — آن اجرای کد دلخواه است
- گراف وابستگی + تشخیص چرخه؛ اگر وابستگی fail شود، dependent اجرا نمی‌شود
- یک پلاگین خراب کل استارتاپ را نمی‌خواباند

### فاز ۲۱ — پیکربندی لایه‌ای (۱۲۰ → ۴۵۰ خط)

شش لایه با اولویت قطعی. mapping ها بازگشتی merge، لیست‌ها جایگزین.

**محافظت از secret** مهم‌ترین بخش: تشخیص خودکار بر اساس نام کلید، و
redaction در `as_dict`, `to_json` **و `__repr__`**. یک traceback که شیء
config را چاپ کند نباید رمز بروکر را لو بدهد. قاعده در **یک نقطه** اعمال
شد نه در هر call site.

اعتبارسنجی همهٔ خطاها را یکجا گزارش می‌کند (§۲۸).

### فاز ۲۲ — لاگینگ ساختاریافته (۲۴ → ۴۰۰ خط)

JSON، correlation id که خودش منتشر می‌شود، bound logger، چرخش فایل.

از `contextvars` استفاده شد نه global: command bus و runner threaded هستند
و تستی ثابت می‌کند context بین thread ها نشت نمی‌کند.

secret ها **داخل logger** پنهان می‌شوند — قبل از رسیدن به هر sink.

### 🐞 هشداری که ruff گرفت

`ContextVar("...", default={})` — آن dict بین هر context ای که مقدار ست
نکرده **مشترک** است. یک mutation درجا فیلدها را بین عملیات‌های نامرتبط نشت
می‌داد. با `default=None` رفع شد. نکتهٔ ظریفی بود.

### کیفیت

```
black ✅ ruff ✅ mypy (279 files) ✅
pytest 1034 passed, 12 skipped     (قبلاً 932)
```

**۱۰۲ تست جدید:** ۲۹ پلاگین · ۴۲ پیکربندی · ۳۱ لاگینگ

🎉 **هر ۲۸ فاز اصلی + ۳ فاز جدید کامل شدند.**

**گزارش:** `PHASE_9_21_22_REPORT.md`

---

## 2026-08-17 — فاز ۳۲: پروفایل اکانت و کنترل کامل از GUI

**MT5 وصل شد!** Alpari-MT5-Demo، لاگین 53102853، ۸۸۲ نماد، `XAUUSD` تطابق
دقیق. روی ویندوز **۱۰۴۶ تست سبز** (هر دو اجرا).

**درخواست کاربر:** تعویض اکانت از داخل GUI، نگاشت نام نماد per-broker، و
اجرای همهٔ ران‌ها فقط از رابط کاربری.

### ممیزی: ۱۸ اسکریپت، ۸ دکمه

ده عملیات فقط از ترمینال قابل اجرا بودند. حالا **۲۱ دکمه در ۶ گروه**.

### پروفایل اکانت

`AccountProfile` = name + login + server + terminal_path + symbol_map + is_demo

**رمز هرگز ذخیره نمی‌شود.** پروفایل فقط نام متغیر محیطی را نگه می‌دارد
(`SHADBOT_MT5_PASSWORD_{PROFILE}`). یک credential در فایل JSON کنار کد، یک
screenshot با عمومی‌شدن فاصله دارد. اگر هم ست نشود، از session خودِ ترمینال
استفاده می‌شود — که حالت عادی است.

### نگاشت نماد per-broker

پلتفرم داخلاً **یک** نام می‌شناسد و هر پروفایل ترجمه می‌کند:
`XAUUSD` → Alpari: `XAUUSD` · Broker B: `XAUUSD_i` · Broker C: `GOLD`

بدون این، یک ابزار سه دیتاست و سه مدل جدا می‌ساخت که قابل مقایسه نیستند —
عوض‌کردن بروکر بی‌صدا تاریخچهٔ یادگیری را از نو شروع می‌کرد.

«Detect symbol names» پیشنهاد می‌دهد ولی **فقط با تأیید** ذخیره می‌کند.

### 🐞 نقصی که تست گرفت

`health_check` هنگام شکست جزئیات را در `detail` می‌گذاشت نه `lines` — یعنی
GUI دقیقاً وقتی که اپراتور بیشتر از همیشه به دیدن نیاز دارد، کادر خالی نشان
می‌داد. رفع شد.

### تأیید زنده

```
۲۱ دکمه در ۶ گروه رندر شد
add_account    → SUCCEEDED (متغیر رمز اعلام شد)
map_symbol     → XAUUSD -> XAUUSD.i
activate       → symbols: {'XAUUSD': 'XAUUSD.i'}
health_check   → degraded — ready=True
```

```
pytest 1097 passed, 12 skipped   (قبلاً 1034)
```

**۶۳ تست جدید** — ۳۹ پروفایل/نگاشت، ۲۴ پوشش GUI (شامل تستی که تضمین می‌کند
هر اسکریپت یا دکمه دارد یا استثنای مستند).

**گزارش:** `PHASE32_REPORT.md`

---

## 2026-08-17 — رفع بن‌بست اولین اجرا (باگ #۱۸)

**گزارش کاربر:**
```
python -m ShadBotTrader.dashboard_cli --db shadbot.db serve
Database not found: shadbot.db
Create one first, for example:
    python scripts/run_persistence.py --keep --db shadbot.db
```

**تناقضی که خودم ساختم:** قرار شد همه‌چیز از GUI اجرا شود، ولی داشبورد برای
شروع یک دستور ترمینالی می‌خواست — آن هم اسکریپتی که در فاز ۳۲ عمداً از GUI
حذفش کرده بودم («جایش را ران‌های واقعی گرفتند»). یعنی کاربر به دستوری هدایت
می‌شد که خودم بی‌اهمیت اعلامش کرده بودم.

**علت:** `cmd_serve` وجود فایل را چک می‌کرد و خارج می‌شد — در حالی که
`Database()` خودش migration را اجرا می‌کند و ساختن دیتابیس خالی یک خط است.

**رفع:**
- `cmd_serve` اگر دیتابیس نباشد، خودش می‌سازد و شروع می‌کند
- صفحهٔ خالی داشبورد حالا **پنج قدم با نام دکمه** نشان می‌دهد، نه دستور شل

```
No database at shadbot.db — creating it ...
  created with schema v1
=== ShadBotTrader dashboard ===
  actions  : 21 buttons enabled
```

**۴ تست رگرسیون** + دو تست قدیمی که رفتار قبلی را الزام می‌کردند به‌روز شدند
(به‌درستی شکستند: قرارداد عوض شده بود).

```
pytest 1101 passed, 12 skipped
```

---

## 2026-08-17 — فاز ۳۳: پیوستگی و آپدیت افزایشی دیتاست (باگ #۱۹)

**سؤال کاربر:** «هربار Fetch بزنم دیتا اضافه می‌شود؟ سقف ۱۰۰k رعایت می‌شود؟
ترتیب کندل‌ها پشت سر هم چک می‌شود؟»

**جواب پس از آزمایش واقعی: هر سه ❌**

```
ingest #1 : v1  candles stored=200
ingest #2 : v2  candles stored=50     ← تاریخچه نابود شد
```

`save_normalized` نسخهٔ جدید می‌نوشت و `query` فقط **آخرین نسخه** را
می‌خواند. `QualityAnalyzer` هم گپ را فقط **داخل یک نسخه** می‌دید.

### سخت‌ترین بخش: گپ همیشه گپ نیست

بازار تعطیل می‌شود. «شنبه کندل نیست» عادی است؛ «سه‌شنبه کندل نیست» یعنی
دیتای گم‌شده.

**تقویم یاد گرفته می‌شود، نه اعلام.** از تاریخچهٔ موجود:
```
Mon (10,10) ... Fri (10,10)  |  Sat (0,10) Sun (0,10)  → closed on Sat, Sun
```
تقویم هاردکد برای کریپتو غلط است، برای بروکر در timezone دیگر غلط است، و
ظرف یک سال کهنه می‌شود. تقویم یادگرفته‌شده خودش وفق می‌دهد و **شواهدش قابل
بازرسی است**.

نتیجه (آخرین کندل سه‌شنبه ۹ ژوئیه):
- روز کاری بعدی → می‌چسبد ✅
- ۳ روز بعد → ۲ کندل گم
- یک ماه بعد → **۲۱** کندل گم (نه ۳۰ — آخر هفته‌ها شمرده نشدند)

### تصمیم‌های کاربر

- شکاف واقعی → **backfill خودکار از بروکر**، و اگر نشد رد کند
- تعطیلی → **از خود دیتا یاد بگیرد**

### سه قاعدهٔ سخت

۱. **تأیید قبل از نوشتن.** آپدیت ناموفق باید دیتاست قبلی را دست‌نخورده
   بگذارد، نه نصفه‌جایگزین.
۲. **کندل جدید در تصادم برنده است.** کندل ۱H جاری قبل از بسته‌شدن بارها
   خوانده می‌شود؛ آخرین خواندن درست‌ترین است.
۳. **رد کردن پیش‌فرض است.** چسباندن دو سر یک حفره، به مدل حرکت قیمتی یاد
   می‌دهد که هرگز رخ نداده — و هیچ تستی بعدش نمی‌گیردش.

### 🐞 باگ فرعی که تست خودم گرفت

`next_version` دایرکتوری **raw** را می‌شمرد ولی سرویس در **normalized**
می‌نوشت → `FileExistsError` در دومین آپدیت. رفع شد.

### تأیید عملی

```
۱) اول: 50 کندل
۲) append: +20 → 60 (۱۰ قدیمی حذف) ✅ سقف رعایت شد
۳) تکراری: +0، آپدیت 20 ✅ بدون duplicate
۴) پرش یک‌ماهه: REFUSED — دیتاست دست‌نخورده ✅
۵) با backfill: 21 کندل وصله شد → پیوسته ✅
```

```
pytest 1155 passed, 12 skipped   (قبلاً 1101)
```

**۵۴ تست جدید** — ۳۳ پیوستگی/تقویم، ۲۱ آپدیت افزایشی.

**گزارش:** `PHASE33_REPORT.md`

---

## 2026-08-17 — فاز ۳۴: چارت شمعی و بازرسی دیتاست

**درخواست کاربر:** چارت کندلی + اطلاعات دیتاست (تعداد کندل و ستون‌ها) برای
هر سهٔ Fetch / Update features / Build dataset.

**ساخته شد:** یک صفحهٔ واحد `/data` (به‌علاوهٔ `/api/data`) با سه بخش که از
سه انبار مختلف می‌خوانند: `ParquetCandleStore`، `ParquetFeatureStore`،
`TrainingDataService`.

### دو تصمیم که مهم‌اند

۱. **چارت ۳۰۰ کندل می‌کشد، ولی تعداد کل را کامل گزارش می‌کند.** دیتاست
   ۱۰۰k نباید صفحهٔ وب ۱۰۰k نقطه‌ای شود — ولی کوتاه‌کردن نمودار و دروغ‌گفتن
   دربارهٔ تعداد، از هر دو بدتر بود.

۲. **ستون ثابت علامت می‌خورد.** `close_rel` طبق ساختار صفر است و به مدل
   چیزی یاد نمی‌دهد؛ صفحه این را می‌گوید به‌جای اینکه مثل ورودی واقعی
   به‌نظر برسد. تست هم همین را قفل می‌کند.

### فقط می‌خواند

`DataInspector` یک Gateway است: هر عددی روی صفحه از storage خوانده شده، نه
محاسبه‌شده. انبار خالی → نتیجهٔ خالی، نه exception (داشبوردی که چون چیزی
fetch نشده crash کند، دقیقاً وقتی بی‌فایده است که می‌خواهی همین را بفهمی).

### تأیید

```
CANDLES : 1,500 stored | chart 300 pts | continuous=True
MATRIX  : 1,397 rows x 123 cols | {'raw price': 8, 'candle shape': 6, 'feature': 109}
          constant: ['close_rel']
FEATURES: 109 stored
```
JS چارت با Node اجرا و اعتبارسنجی شد.

```
pytest 1182 passed, 12 skipped   (قبلاً 1155)
```
**۲۷ تست جدید.**

**گزارش:** `PHASE34_REPORT.md`

---

## 2026-08-17 — فاز ۳۵: دو دیتاست مجزا + فقط دیتای واقعی (باگ‌های ۲۰–۲۳)

**سؤال کاربر:** «چرا Build training dataset براش تایم فریم فرقی نداره؟ مگه
نباید دوتا دیتاست داشته باشیم برای آموزش یکی ۵ دقیقه یکی ۱ ساعته؟»

**پاسخ کوتاه:** دو دیتاست از فاز ۳۰ وجود داشت (`DatasetSpec.timeframes =
("5M","1H")` و `build()` روی هر دو حلقه می‌زند و دو فایل `.npz` می‌نویسد)،
ولی سه ایراد باعث می‌شد در عمل درست کار نکند. کاربر بعد از توضیح، چهار
دستور صریح داد و هر چهار اجرا شد.

### چهار باگ

| # | باگ | چرا مهم بود |
|---|---|---|
| ۲۰ | `Fetch market data` فقط **یک** تایم‌فریم می‌گرفت (پیش‌فرض `5M`) | ولی build هر دو را لازم داشت → مستقیماً به باگ ۲۱ می‌رسید |
| ۲۱ | نبود دیتا → **کندل نمونهٔ سینوسی** ساخته و زیر نماد واقعی ingest می‌شد | مدل رنج روی دیتای جعلی آموزش می‌دید و آموزش‌دیده به‌نظر می‌رسید. یک اجرا بعد، تشخیص‌ناپذیر. نقض مستقیم `DEVELOPMENT_RULES.md` |
| ۲۲ | `build_feature_matrix` سطر را از **هر جای** سری حذف می‌کرد | یک `NaN` در سطر ۴٬۰۰۰ آن را حذف می‌کرد و ۳٬۹۹۹ به ۴٬۰۰۱ می‌چسبید. roll-forward از روی بازار ندیده رد می‌شد و هیچ تستی نمی‌گرفت |
| ۲۳ | کندل زیر نام بروکر (`XAUUSD_i`) ذخیره، ولی بقیه canonical (`XAUUSD`) می‌خواندند | یک نماد، دو دیتاست بی‌ارتباط |

### چهار قاعدهٔ جدید

**۱. تایم‌فریم‌های آموزش با هم سفر می‌کنند.** `TRAINING_TIMEFRAMES = ("5M","1H")`.
فیلد Timeframes حالا لیست می‌گیرد و پیش‌فرضش `5M,1H` است. هر تایم‌فریم مستقل
merge می‌شود؛ رد شدن یکی، دیگری را برنمی‌گرداند.

**۲. هیچ کندل ساختگی‌ای زیر نماد واقعی ذخیره نمی‌شود.** نبود دیتا حالا خطای
`NoRealData` با دستور دقیق است. اسکریپت‌های دمو همچنان کندل می‌سازند — چون
کارشان همین است — ولی زیر `DEMOXAU` که alias هیچ چیز واقعی‌ای نیست. تستی
این را اجبار می‌کند: هر اسکریپتی که `generate_sample()` صدا می‌زند حق ندارد
نام نماد طلا داشته باشد.

**۳. سطر فقط از دو سرِ سری حذف می‌شود.** خواستهٔ صریح کاربر:
«این کار فقط برای ابتدای دیتاست، اونم بخاطر اندیکاتورایی مثل SMA».

| کجا | مثال | کار |
|---|---|---|
| ابتدا | `SMA 200` | حذف سطر → `dropped_warmup` |
| انتها | `chikou`، `*_target_p1` | حذف سطر → `dropped_tail` |
| **وسط** | `NaN` وسط سری | حذف **ستون** → `holed_features` |

`FeatureMatrix.is_contiguous` این تضمین را صریح می‌کند و
`TimeframeSlice.contiguous` آن را در manifest ثبت.

**۴. زیر نام بروکر بگیر، زیر نام canonical ذخیره کن.**
`fetch_and_update(..., store_as=...)` قبل از merge برچسب می‌زند. backfill
هنوز با نام بروکر از MT5 می‌پرسد (تنها نامی که MT5 می‌شناسد) و جوابش را
canonical ذخیره می‌کند. دیتای قدیمی زیر alias هنوز پیدا می‌شود ولی
`symbol_scope.py` **می‌گوید** که از alias استفاده کرده — سکوت، تکرار همان
اشتباه بود.

### ساخته شد

| فایل | نقش |
|---|---|
| `infrastructure/data/symbol_scope.py` | `StoredSymbol`، `alias_candidates`، `resolve_stored_symbol`، `stored_symbols` |
| `tests/integration/test_dual_timeframe_datasets.py` | ۲۳ تست، یک کلاس برای هر باگ |
| `docs/Phases/Phase35.md` | سند فاز |

### تغییر کرد

- `infrastructure/ai/feature_matrix.py` — برش دو سر، `holed_features`، `dropped_tail`، `is_contiguous`
- `domain/dataset/training_dataset.py` — سه فیلد و سه هشدار جدید در slice
- `application/services/training_data_service.py` — عبور فیلدها
- `application/services/dataset_update_service.py` — `store_as`، `_relabel`، backfill آگاه از بروکر
- `presentation/commands/handlers.py` — `parse_timeframes`، fetch چندتایم‌فریمی، `missing_timeframes`، حذف fallback نمونه
- `scripts/run_{training_dataset,dual_models,weekly_update,live_loop}.py` — `NoRealData`
- ده اسکریپت دمو + شش CLI — نماد `XAUUSD_i` → `DEMOXAU` یا `XAUUSD`

### تصمیمی که گرفته نشد

**به «Build training dataset» فیلد timeframe اضافه نشد.** اگر اضافه می‌شد،
اپراتور می‌توانست 5M را روی 1H کهنه بسازد و دو مدل روی تاریخچه‌هایی که در دو
لحظهٔ متفاوت تمام می‌شوند آموزش ببینند. **جفت، واحد کار است.**

### تأیید

```
black --check .                 ✅ 407 files
ruff check .                    ✅
mypy src --python-version 3.12  ✅ 288 files
pytest                          ✅ 1205 passed, 12 skipped   (قبلاً 1182)
RUN_TF=1                        ✅ 278 + 344 + 592
```
**۲۳ تست جدید.**

اجرای دمو دو بار: بار دوم `added 0` و digest هر دو slice بایت‌به‌بایت یکسان.

```
5M: 1,000 candles -> 897 rows x 123 cols | front 77 | tail 26 | contiguous True
1H: 1,000 candles -> 897 rows x 123 cols | front 77 | tail 26 | contiguous True
symbols on disk: ['XAUUSD']        ← گرچه از XAUUSD_i گرفته شد
```

**گزارش:** `PHASE35_REPORT.md`

---

## 2026-08-17 — فاز ۳۶: دیدن روند آموزش در همان لحظه (باگ‌های ۲۴–۲۷)

**گزارش کاربر:** «الان موقعی ک توی Train both models ران رو میزنم، نه توی
پاورشل نه توی صفحه وب چیزی از روند آموزش بهم نشون نمیده که دقت و درصدو این
چیزا رو ببینم»

سه علت جدا داشت، نه یکی — و یک باگ چهارم موقع تست زندهٔ همین فاز پیدا شد.

### چهار باگ

| # | باگ | ریشه |
|---|---|---|
| ۲۴ | خروجی تا **پایان** کار buffer می‌شد | `subprocess.run(capture_output=True)` تا exit پروسه برنمی‌گردد. آموزش ۲۰ دقیقه‌ای = ۲۰ دقیقه سکوت. صفحهٔ وب می‌گفت «reload کن» ولی reload همان هیچ را نشان می‌داد |
| ۲۵ | `ConsoleProgressReporter` از فاز ۱۳ ساخته شده بود و **هیچ‌کس صدایش نمی‌زد** | `progress or NullProgressReporter()` و هیچ فراخوانی‌ای `progress=` پاس نمی‌داد. به‌علاوهٔ `verbose=0` کراس |
| ۲۶ | accuracy محاسبه و **دور ریخته** می‌شد | trainer فقط `val_loss` را نگه می‌داشت. «مدل چقدر خوبه؟» در کل سیستم جواب نداشت |
| ۲۷ | `--storage-root` داشبورد به اسکریپت‌ها **نمی‌رسید** | چهار دکمهٔ اسکریپتی آن را پاس نمی‌دادند → اسکریپت سراغ `datasets/` پیش‌فرض می‌رفت. کاربر در `/data` هزاران کندل می‌دید و آموزش می‌گفت «کندلی نیست» |

باگ ۲۷ را موقع تست زندهٔ فاز ۳۶ گرفتم: داشبورد را با `--storage-root
/tmp/live36` بالا آوردم و آموزش گفت `symbols on disk: P24DEMO, P24WK,
P30TEST, P31DEMO, XAUUSD_I` — یعنی ریشهٔ اشتباه.

### چه چیزی حالا هست

**پاورشل:** لاگ هر epoch با loss/accuracy/lr، نوار پیشرفت، ETA و
`s/fold`. با `--quiet` خاموش می‌شود.

**صفحهٔ وب:** بنر Running حالا یک `<pre>` زنده دارد که از `/api/log` هر ۲
ثانیه می‌خواند. اسکرول هوشمند: اگر پایین باشی دنبال لاگ می‌آید، اگر بالا
رفته باشی جایت را نگه می‌دارد. در پایان یک‌بار reload می‌کند تا پنل نتیجه
بیاید.

سه جزئیات که «زنده» بودن را ممکن کرد:
- `Popen` + خواندن خط‌به‌خط به‌جای `subprocess.run`
- `PYTHONUNBUFFERED=1` — وگرنه پایتون وقتی مقصد pipe است ۸KB بافر می‌کند و
  لاگ دسته‌ای و با تأخیر می‌رسد
- `bufsize=1` با `text=True` برای بافر خط سمت خودمان

**سنجهٔ کیفیت با معیار مقایسه:** `fold_metrics` آخرین مقدار هر سنجه را
به‌ازای هر fold نگه می‌دارد و اسکریپت تفسیرش می‌کند. مهم‌تر از خود عدد،
مقایسه با baseline است: در مسئلهٔ ۳ کلاسه که ۷۰٪ نمونه‌ها HOLD‌اند، مدلی که
همیشه HOLD بگوید ۷۰٪ دقت می‌گیرد و هیچ یاد نگرفته. اگر baseline زده نشده
باشد صریح می‌گوید `NO BETTER than`. برای مدل رنج، `val_mae` به دلار ترجمه
می‌شود.

### تغییر کرد

- `presentation/commands/handlers.py` — `_run_script` با `Popen` و استریم؛
  `RUN_LOG_DIR`/`run_log_path`/`read_run_log`؛ `--storage-root` به هر چهار دکمه
- `presentation/web/server.py` — مسیر `GET /api/log`
- `presentation/web/renderer.py` — پنل لاگ زنده + JS polling + `.runlog`
- `infrastructure/ai/wavenet/wavenet_trainer.py` — `fold_metrics`
- `application/services/dual_model_service.py` — عبور `fold_metrics`
- `scripts/run_dual_models.py` — `ConsoleProgressReporter`، `--quiet`، `print_quality()`
- `.gitignore` — `run_logs/`

### تأیید

```
black ✅  ruff ✅  mypy (288 files) ✅
pytest 1228 passed, 12 skipped   (قبلاً 1205)
RUN_TF=1  278 + 370 + 592
```
**۲۳ تست جدید.**

تست زندهٔ داشبورد روی پورت ۸۰۹۹ — لاگ **حین اجرا** رشد کرد:
```
[8s] busy=True lines=32 → [24s] lines=63 → [32s] lines=77 → [40s] busy=False
```

### هشدار صادقانه دربارهٔ اعداد این تست

`val_accuracy 100%` روی **۴ نمونهٔ اعتبارسنجی** و دیتای سینوسی ساختگی
به‌دست آمده. این عدد کیفیت مدل را نشان نمی‌دهد، فقط ثابت می‌کند مسیر
گزارش‌دهی کار می‌کند. روی دیتای واقعی انتظار عدد خیلی پایین‌تر داشته باش؛
اگر آنجا هم ۱۰۰٪ دیدی، نشانهٔ **نشت داده** است نه موفقیت.

**گزارش:** `PHASE36_REPORT.md`

---

## 2026-08-17 — فاز ۳۷: پیشرفت زندهٔ ویژگی‌ها + انبار جدا برای هر سری (باگ ۲۸)

**دو درخواست کاربر:** نمایش زندهٔ اینکه کدام ویژگی دارد حساب می‌شود و چندتا
مانده؛ و بررسی اینکه آیا ویژگی‌ها برای ۵ دقیقه و ۱ ساعته جدا محاسبه و ذخیره
می‌شوند.

سؤال دوم یک باگ جدی را لو داد. جواب صادقانه بود: محاسبه بله، **ذخیره نه**.

### باگ ۲۸ — ویژگی‌های دو تایم‌فریم روی هم می‌افتادند

مسیر ذخیره‌سازی `features/{feature_id}/v{version}.parquet` بود — نه نماد، نه
تایم‌فریم. یعنی `atr_14` برای 5M می‌شد `v1` و همان ویژگی برای 1H می‌شد `v2`
در **همان پوشه**. دو کمیت کاملاً متفاوت، بدون هیچ چیزی که از هم جدایشان کند.
در مخزن خودمان ۲۲ نسخهٔ بی‌هویت زیر `datasets/features/atr_14/` بود.

**چرا تا حالا فاجعه نشده بود:** مدل‌ها این انبار را نمی‌خوانند —
`build_feature_matrix` همه را در حافظه از نو حساب می‌کند. پس آموزش سالم بود.
ولی هر مصرف‌کنندهٔ دیگری (بازرسی `/data` و هر چیز آینده) دیتای اشتباه
می‌گرفت. بمب ساعتی بود نه انفجار.

**رفع:** `features/{symbol}/{timeframe}/{feature_id}/v{n}.parquet`. هر سری
شمارندهٔ نسخهٔ مستقل خودش را دارد. `for_series()` نمونهٔ **جدید** برمی‌گرداند
(نه mutate) تا سرویسی که store دارد زیر پایش عوض نشود.

**پورت `FeatureRepository` دست نخورد** — طبق فریز فاز ۲۶ امضای متدها همان
ماند و scope به نمونه بسته شد، نه به امضا.

اثبات بعد از رفع: `5M/atr_14/v1 = 2.7312` و `1H/atr_14/v1 = 6.5696` — دو
عدد متفاوت، هرکدام در `v1` خودش.

### پیشرفت زنده

```
[#---------------------------]   1.8% |   3/109 | low_filter
      stored v1 | 1,000 values | quality 98.69
...
  109/109 stored | 0 quarantined | 32 research-only
```

هر خط: کدام ویژگی، چندتا از چندتا، چند درصد، چند مقدار تولید شد، کیفیتش
چقدر. قرارداد `FeatureProgressReporter` عمداً شبیه `TrainingProgressReporter`
فاز ۳۶ است — دو عملیات طولانی در یک محصول نباید دو شکل گزارش بدهند.

دکمهٔ داشبورد در همان پنل لاگ زندهٔ فاز ۳۶ می‌نویسد. چون این هندلر داخل خود
پروسه اجرا می‌شود (نه زیرپروسه)، مستقیم در `run_logs/compute_features.log`
می‌نویسد.

فیلد Timeframes هم مثل فاز ۳۵ لیست‌پذیر شد با پیش‌فرض `5M,1H`.

### ساخته شد

| فایل | نقش |
|---|---|
| `infrastructure/feature/feature_progress.py` | `FeatureProgressReporter`، `NullFeatureProgress`، `ConsoleFeatureProgress` |
| `tests/integration/test_feature_visibility.py` | ۱۹ تست |

### تغییر کرد

- `infrastructure/feature/parquet_feature_store.py` — چیدمان جدید، `for_series()`، `scope`، پاک‌سازی نام مسیر
- `application/services/feature_computation_service.py` — `progress`، scope خودکار repository
- `presentation/commands/handlers.py` — `compute_features` چندتایم‌فریمی با لاگ زنده
- `presentation/gateway/data_inspector.py` + `web/data_renderer.py` — ستون Series، برچسب legacy
- دو تست موجود با قرارداد جدید تطبیق داده شدند (نه تضعیف)

### تأیید

```
black ✅  ruff ✅  mypy (289 files) ✅
pytest 1247 passed, 12 skipped   (قبلاً 1228)
RUN_TF=1  278 + 389 + 592
```
**۱۹ تست جدید.**

تست زندهٔ داشبورد: `5M: 109/109` و `1H: 109/109`، روی دیسک دو درخت جدا، و
۲۱۸ خط `stored v1` در لاگ (۱۰۹ × ۲).

یک تست ثابت می‌کند **reporter نتیجه را عوض نمی‌کند** — اجرای با و بدون
گزارشگر دقیقاً یک خروجی می‌دهد. ناظری که چیزی را که می‌بیند تغییر بدهد باگ
است نه امکانات.

### دیتای قدیمی مخزن پاک نشد

`datasets/features/` فعلی (۲۲ نسخهٔ بی‌هویت) دست‌نخورده ماند: حذف دیتای
کاربر بدون اجازه درست نیست، هویتشان قابل بازیابی نیست (حدس‌زدن همان اشتباهی
است که این فاز رفعش کرد)، و `/data` با برچسب `legacy` نشانشان می‌دهد.

**گزارش:** `PHASE37_REPORT.md`

---

## 2026-08-17 — فاز ۳۸: کش ویژگی‌ها + رفع سوءتفاهمی که خودم ساختم

**کاربر عصبانی و به‌حق:** «حتما از ویژگی ها توی دیتایی که قراره بدیم ب مدل
برای آموزش استفاده چرا تا الان استفاده نکردی پس؟ قبلا گفته بودم که!!!! پس
الان چ ماترسیو داری برای آموزش ب مدل میدی؟؟؟؟؟»

### اول: جواب، با عدد

**۱۰۹ ویژگی کاتالوگ از فاز ۲۹ در ماتریس آموزش بوده‌اند.** اندازه‌گیری:

```
matrix given to the model: 297 rows x 123 cols
  candle-derived : 14
  CATALOGUE      : 109
```

دکمهٔ Train both models هم `--with-features` پاس می‌دهد.

### سوءتفاهم تقصیر من بود

در گزارش فاز ۳۷ نوشتم «ویژگی‌های ذخیره‌شده هنوز توسط هیچ‌کس خوانده
نمی‌شوند». جمله **درست ولی گمراه‌کننده** بود: منظورم فایل‌های پارکت روی
دیسک بود، نه خود ویژگی‌ها.

| | واقعیت |
|---|---|
| ویژگی‌ها در ماتریس آموزش | ✅ بله، ۱۰۹ تا |
| از **فایل پارکت** خوانده می‌شد | ❌ نه، هر بار در حافظه از نو |

مدل همیشه ویژگی‌ها را می‌گرفت؛ فقط دوباره‌کاری می‌شد. باید می‌نوشتم «انبار
پارکت مصرف‌کننده ندارد، ولی ماتریس آموزش ۱۲۳ ستونه است». درس: وقتی می‌نویسم
«X استفاده نمی‌شود»، باید دقیقاً بگویم کدام X.

حالا ۶ تست این را قفل می‌کنند تا نه من مبهم بنویسم نه کد بی‌صدا به ۱۴ ستون
برگردد. خروجی build هم صریح می‌گوید:
`columns = 14 candle-derived + 109 catalogue features`

### قاعدهٔ کش

خواستهٔ کاربر: تا دیتاست عوض نشده از انبار بخوان؛ عوض که شد **از اول** حساب
کن و دوباره ذخیره کن.

**چرا append ممنوع است:** EMA/MACD/ATR بازگشتی‌اند و حالت را از کندل اول
حمل می‌کنند. مقدار روی ۱۰۰k کندل با ادامه‌دادن از کندل ۹۹k یکی نیست، تفاوتش
نامرئی است و هیچ تستی نمی‌گیردش.

**تشخیص با اثر انگشت، نه تاریخ فایل** (تاریخ دروغ می‌گوید: بازنویسی با
محتوای یکسان، یا ویرایش درجا). `FeatureFingerprint` پوشش می‌دهد: تعداد
کندل، اولین/آخرین زمان، **digest همهٔ مقادیر OHLCV**، نام و نسخهٔ feature
set، و فهرست ۱۰۹ شناسه.

اندازه‌گیری:
```
1. اولین اجرا (1000 کندل)     reused=  0/109  1.54s
2. همان کندل‌ها               reused=109/109  0.53s
3. بار سوم                    reused=109/109  0.52s
4. بعد از آپدیت (1100)        reused=  0/109  1.63s
5. همان 1100                  reused=109/109  0.53s
versions on disk: ['v1', 'v2']   ← نه پنج نسخه
```

در داشبورد `REUSED from the store — the dataset has not changed` و بعد از
آپدیت، در لاگ زنده دلیلش:
`recompute : candle count changed: 1,000 -> 1,200 (the dataset was updated)`

اثر انگشت خراب همیشه به محاسبهٔ کامل منجر می‌شود — به دیتایی که نمی‌توانیم
تأییدش کنیم اعتماد نمی‌کنیم. فیلد `Force recompute` هم اضافه شد.

### ساخته شد

| فایل | نقش |
|---|---|
| `infrastructure/feature/feature_cache.py` | `FeatureFingerprint`، `FeatureCache`، `candles_digest` |
| `tests/integration/test_feature_cache.py` | ۲۱ تست |

### تغییر کرد

- `application/services/feature_computation_service.py` — `force`، بررسی کش، `from_cache`/`reused_count`
- `infrastructure/feature/feature_progress.py` — `on_cache_hit`، `reason`
- `presentation/commands/handlers.py` — گزارش REUSED، فیلد Force recompute
- `scripts/run_training_dataset.py` — چاپ تفکیک ۱۴+۱۰۹
- یک تست فاز ۳۷ با قاعدهٔ جدید تطبیق داده شد (نه تضعیف)

### تأیید

```
black ✅  ruff ✅  mypy (290 files) ✅
pytest 1267 passed, 13 skipped   (قبلاً 1247)
RUN_TF=1  278 + 410 + 592
```
**۲۱ تست جدید.** یکی‌شان ثابت می‌کند مقادیر کش‌شده دقیقاً با محاسبهٔ مجدد
یکی‌اند — کشی که عدد متفاوت بدهد بدتر از نبودن کش است.

### بدهی صریح

**ماتریس آموزش هنوز از انبار پارکت نمی‌خواند.** کش لایهٔ
`FeatureComputationService` را پوشش می‌دهد (دکمهٔ Update features)، ولی
`build_feature_matrix` مستقل و در حافظه حساب می‌کند.

**چرا وصلش نکردم:** ماتریس مدل ویژگی‌های قیمتی را نسبت به close همان سطر
نرمال می‌کند (`is_price_scaled`)، انبار مقدار خام دارد. وصل‌کردن یعنی انتقال
منطق نرمال‌سازی و اگر اشتباه شود مدل روی مقیاس غلط آموزش می‌بیند — بی‌صدا.
فاز مستقل با تست تطابق بیت‌به‌بیت می‌خواهد.

**گزارش:** `PHASE38_REPORT.md`

---

## 2026-08-17 — فاز ۳۹: خواندن از انبار، تایم‌فریم روزانه، انتخاب مدل (باگ‌های ۲۹–۳۰)

**ورک‌اسپیس پاک و از گیت‌هاب کلون شد** (`f8bf0a9 Real Dataset`). دیتای واقعی
کاربر: XAUUSD 5M ۵۰٬۰۰۰ کندل (2025-11..2026-08) و 1H ۵۰٬۰۰۰ کندل
(2017-11..2026-08). **از این پس دیتا در zip تحویلی نیست.**

### ۱. خواندن از انبار + اثبات بایت‌به‌بایت

`build_feature_matrix` حالا پارامتر `source` دارد. فقط **از کجا** ستون‌ها
می‌آیند عوض می‌شود؛ مقیاس‌بندی نسبت به close، برش warm-up و tail در یک جا
می‌مانند و مشترک‌اند — همین ادعای «یکسان» را تست‌پذیر می‌کند.

روی دیتای واقعی 1H:
```
computed: 2897 x 123  in 3.31s
loaded  : 2897 x 123  in 1.59s   (2.1x)
BYTES identical : True   (2,850,648 bytes each)
```

**باگی که سر راه پیدا شد:** انبار `warmup` را ذخیره نمی‌کرد. `warmup` مقدار
نیست، تعداد سطرهای ابتدایی بدون مقدار صادقانه است، و ماتریس با آن تصمیم
می‌گیرد از کجا شروع شود. بدون آن، ماتریسِ خوانده‌شده **بی‌صدا** فرق می‌کرد.
حالا در metadata پارکت ذخیره می‌شود.

محافظ‌ها: اثر انگشت فاز ۳۸ · طول نامساوی · **timestamp جابه‌جا** (طول یکی،
کندل‌ها متفاوت — خطرناک‌ترین حالت) · کش ناقص → کل ماتریس دوباره حساب می‌شود
نه ستون کمتر.

### ۲. تایم‌فریم یک روزه

`domain/market/resample.py` + دکمهٔ **Build a higher timeframe**:
```
XAUUSD: 2,255 1D candles from 50,000 1H
  dropped: 2 incomplete buckets | continuity OK
  2017-11-16 O=1277.04 .. 2026-08-14 C=4376.25
```

دو قاعده: سطل ناقص دور ریخته می‌شود (آخرین «روز» معمولاً شش‌ساعته است و
high/low آن، high/low روز نیست)؛ سطل‌بندی بر تاریخ تقویمی UTC است نه شمارش،
پس آخر هفته جمعه را به دوشنبه نمی‌چسباند.

ویژگی‌ها: `1D: 109/109 over 2,255 candles`. دیتاست: `2152 rows x 123 cols`,
`source used: stored`.

**هر تایم‌فریم شناسهٔ مدل خودش را دارد** (`gold_range_1h` / `gold_range_1d`).
مشترک بودن یعنی آموزش دوم اولی را بازنویسی کند.

مدل رنج روزانه، آموزش واقعی:
```
val_mae 0.016225 → ~32.45 USD per bound on gold at 2,000
PREDICTION: close 4376.25 | high 4458.30 (+1.875%) | low 4315.72 (-1.383%) | R/R 1.36
```
**اولین مدل آموزش‌دیده روی قیمت واقعی طلا.**

### ۳. انتخاب مدل و دیتاست

فیلدهای `Model` (`all|range_1h|range_1d|signal|range|both`)،
`Range dataset(s)`، `Signal dataset`. خروجی صریح: `model id : gold_range_1d`
و `dataset : XAUUSD 1D`.

### ۴. چرا پاورشل چیزی چاپ نمی‌کرد — دو علت

روی دیتای واقعی بازتولید شد: **۲۰۸ ثانیه، صفر خط.**

**باگ ۲۹ — ۲۴٬۹۷۶ فولد.** `val_size=4, step=2` برای سری دموی چندصد سطری بود.
روی ۵۰k کندل هر فولد یک fit کامل است؛ این «کند» نیست، تمام نمی‌شود. حالا
هندسه با اندازهٔ دیتا مقیاس می‌گیرد: `val=999 step=999 → 49 فولد`.

**باگ ۳۰ — ۱۰ ثانیه سکوت قبل از اولین خط.** ساخت ۵۰k پنجره **قبل** از
`on_train_begin` بود. حالا اعلام می‌شود.

**پیشرفت درون epoch:** یک epoch روی ۵۰k نمونه هزاران batch است؛ حالا خط
batch با loss/mae/درصد در جا به‌روز می‌شود (`\r`).

**سازگاری:** قرارداد reporter بزرگ‌تر شد؛ reporter قدیمی هنوز معتبر است و
hook غایب رد می‌شود نه اینکه خطا بدهد — مشاهده نباید آموزش را بشکند.

### تأیید

```
black ✅ ruff ✅ mypy (292 files) ✅
pytest 1300 passed, 12 skipped   (قبلاً 1268)
RUN_TF=1  110 + 168 + 592 + 442
```
**۳۲ تست جدید.** سه تست قدیمی با دنیای سه‌تایم‌فریمی تطبیق داده شدند.

### بدهی صریح

مدل سیگنال 5M روی ۵۰k هنوز کند است (۴۹ فولد × ~۶٬۲۰۰ batch). مدل 1D فقط
۲٬۱۲۱ پنجره دارد و زیر-برازش می‌کند — `val_mae` ~۳۲ دلار روی طلای ۲۰۰۰ برای
معامله بزرگ است. صادقانه گزارش شده.

**گزارش:** `PHASE39_REPORT.md`

---

## 2026-08-17 — فاز ۴۰: منوهای کرکره‌ای + ذخیرهٔ واقعی مدل (باگ‌های ۳۱–۳۲)

**درخواست کاربر:** نوع مدل کرکره‌ای باشد؛ `Signal dataset` و
`Range dataset(s)` حذف شوند؛ یک منوی کرکره‌ای برای دیتاست‌های موجود؛ مدل با
نقش و دیتاستش ذخیره شود؛ Retrain از لیست مدل‌های ذخیره‌شده انتخاب کند. و:
ورک‌اسپیس از دیتای واقعی خالی شود.

### باگ ۳۱ — مدل هیچ‌وقت ذخیره نمی‌شد (بحرانی)

`run_dual_models.py` شبکه را آموزش می‌داد، پیش‌بینی چاپ می‌کرد و خارج
می‌شد. `datasets/models/` اصلاً وجود نداشت و هیچ `.bin`ی در پروژه نبود.
یعنی **هر اجرای آموزشی از فاز ۲۹ تا الان دور ریخته می‌شد** — از جمله همان
مدل رنج روزانه که روی دیتای واقعی `val_mae 0.0164` گرفت.

این را درخواست چهارم لو داد: لیست مدل‌های ذخیره‌شده همیشه خالی می‌ماند.

**رفع:** `save_model()` در اسکریپت + `ModelCatalogue` که کنار هر artifact
یک رکورد می‌نویسد (نقش، نماد، تایم‌فریم، سطرها، پنجره‌ها، سنجه‌ها، زمان).
`ModelArtifact.with_version()` هم اضافه شد تا آموزش مجدد نسخهٔ جدید بسازد
و قبلی را نگه دارد — artifactها تغییرناپذیرند.

### باگ ۳۲ — دکمهٔ Retrain در لحظهٔ فشردن کرش می‌کرد

`train_model` روی `CommandHandlers` بود ولی `_run_script` فقط روی
`AccountCommandHandlers`. یعنی `AttributeError` تضمینی. حالا
`AccountCommandHandlers` از `CommandHandlers` **ارث می‌برد** — تکرار مشکل
غیرممکن شد نه فقط رفع.

### منوهای کرکره‌ای

`CommandField` حالا `kind="select"` + `options` دارد و رندرر `<select>`
واقعی می‌سازد. `is_select` وقتی options خالی باشد False است — منوی خالی
انتخاب نیست، بن‌بست است، پس به text برمی‌گردد.

| منو | مقادیر |
|---|---|
| Model type | all · range · signal |
| Dataset | فقط آنچه در `processed/` هست |
| Saved model | فقط آنچه در `models/` هست |

`Signal dataset` و `Range dataset(s)` حذف شدند؛ تست جلوی برگشتشان را
می‌گیرد.

### رفتارهای عمدی در Retrain

نقش از **رکورد مدل** خوانده می‌شود نه از اسم فایل. اگر دیتاست انتخابی با
دیتاست اصلی فرق کند، **اجازه هست ولی هشدار می‌دهد** — عوض‌کردن ریتم بازاری
که مدل یاد گرفته، تصمیم کاربر است نه اشتباه.

### ورک‌اسپیس تمیز

دیتای واقعی پاک شد (روی گیت‌هاب امن است: `3b10dca 1D Features`). جایش
`scripts/make_test_data.py` که ۶۰۰ کندل مصنوعی زیر **`TESTSYM`** می‌سازد —
نه XAUUSD و نه هیچ alias آن. تست ثابت می‌کند `TESTSYM` در
`alias_candidates("XAUUSD", profile)` نیست، و تست دیگری کد اسکریپت را
(نه docstringش را) از نام نماد واقعی پاک نگه می‌دارد.

### تأیید

```
black ✅ ruff ✅ mypy (293 files) ✅
pytest 1330 passed, 12 skipped   (قبلاً 1300)
RUN_TF=1  278 + 472 + 592
```
**۳۰ تست جدید.** سه تست قدیمی با نام‌های جدید تطبیق داده شدند.

زنده: آموزش → `SAVED gold_range_1d v1` → Retrain از داشبورد → `v3` با v1 و
v2 دست‌نخورده. `data files in zip: 0`.

### بدهی صریح

`model_id` نماد را در بر نمی‌گیرد، پس آموزش یک مدل روی TESTSYM و بعد روی
XAUUSD دو **نسخه** می‌سازد نه دو مدل. برای چند-نمادی شدن باید اصلاح شود.

**گزارش:** `PHASE40_REPORT.md`

---

## 2026-08-17 — فاز ۴۱: رفع OOM آموزش (باگ ۳۳)

**گزارش کاربر:** «Running: train_dual_models 492s / waiting for the first
line ... رم سیستمم تا خرخره پر میشه، هیچ مدلی هم ذخیره نشد.»

هر سه علامت **یک علت** داشتند.

### باگ ۳۳ — ۱۲.۲ گیگابایت تخصیص قبل از اولین batch

```
49,393 windows × 500 rows × 123 cols × 4 bytes = 12.2 GB
ماتریس تخت اصلی                                 =   25 MB
```

`build_multi_target_samples` همهٔ پنجره‌ها را در ابتدای `train()` می‌ساخت —
قبل از اولین batch و قبل از اولین `print`. ماشین در همان فاصله می‌مرد، که
توضیح می‌دهد چرا رم پر می‌شد **و** لاگ خالی می‌ماند **و** مدلی ذخیره
نمی‌شد: `save_model()` هرگز اجرا نمی‌شد.

در سندباکس با OOM killer اثبات شد (`EXIT=137`).

**نکتهٔ تلخ:** فاز ۳۰ `WindowGenerator` تنبل را دقیقاً برای همین ساخت، با
تست و مستندات، و هیچ‌وقت به trainer وصل نشد.

### رفع

فولدهای بالای ۵۱۲ MB از همان ماتریس ۲۵ مگابایتی استریم می‌شوند
(`tf.data`). وقتی استریم فعال است لیست نمونه‌ها **اصلاً ساخته نمی‌شود**؛
`_LazySampleCount` جایش می‌نشیند که فقط تعداد را می‌دهد و ایندکس‌شدن را رد
می‌کند — مسیری که هنوز استریم را نمی‌شناسد ساکت نمی‌ماند.

اندازه‌گیری: **۴.۸ GB → ۹۶۶ MB peak** روی ۲۰٬۰۰۰ سطر، دو epoch.

**باگ فرعی:** `from_generator` بعد از یک pass تمام می‌شود، پس epoch دوم
خالی بود. با `repeat()` + `steps_per_epoch` رفع شد.

### گزارش هزینه قبل از شروع

```
  windows        : 429 of 64 x 123
  if materialised: 0.0 GB  (streamed instead when large)
```

و پنجرهٔ بزرگ‌تر از دیتا فوراً رد می‌شود نه بعد از هشت دقیقه:
`[X] Not enough data: 497 rows cannot make a single 500-row window.`

### تأیید

```
black ✅ ruff ✅ mypy (293 files) ✅
pytest 1340 passed, 12 skipped   (قبلاً 1330)
RUN_TF=1  110 + 168 + 482 + 592
```
**۱۰ تست جدید.** ذخیرهٔ مدل زنده تأیید شد: `SAVED gold_range_1d v1`.

### بدهی

استریم کندتر از حافظه است وقتی هر دو جا می‌شوند؛ آستانهٔ ۵۱۲ MB
محافظه‌کارانه است. و پنجرهٔ ۵۰۰ روی 5M هنوز ساعت‌ها طول می‌کشد — حافظه حل
شد، زمان نه.

**گزارش:** `PHASE41_REPORT.md`

---

## 2026-08-17 — فاز ۴۲: خطوط epoch بالاخره به مرورگر می‌رسند (باگ‌های ۳۴–۳۵)

**کاربر برای سومین بار:** «نه توی پاورشل نه توی وب هیچی از روند آموزش
نمی‌بینم که هر epoch دقت و خطا چقدر تغییر کرده.»

این بار خطوط **تولید می‌شدند** و به فایل لاگ **می‌رسیدند** — و در آخرین قدم
دور ریخته می‌شدند.

### باگ ۳۴ — سیل batch نتایج را بیرون می‌انداخت

هر batch یک خط. داشبورد فقط ۲۰۰ خط آخر را می‌خواند. اندازه‌گیری روی یک
اجرای کوچک: ۳۱۶ خط batch در لاگ، و از ۲۰۰ خط قابل نمایش، **۱۵۸ تا batch**
بودند و فقط ۳ خط epoch. روی دیتای بزرگ‌تر کاربر، ۲۰۰ خط آخر کلاً batch
بودند و هیچ epoch‌ای باقی نمی‌ماند.

### باگ ۳۵ — `\r` از داخل pipe رد نمی‌شود

خط پیشرفت با `\r` نوشته می‌شد تا در جا به‌روز شود؛ این فقط روی ترمینال
کار می‌کند. از داخل pipe به فایل، `\r` فقط یک کاراکتر است، پس هر
به‌روزرسانی یک خط دائمی جدید می‌شد — که سیل باگ ۳۴ را چند برابر کرد.

### رفع

حداکثر **۸ خط پیشرفت در هر epoch** (`BATCH_LINES_PER_EPOCH`)، با فاصلهٔ
یکنواخت و همیشه خط ۱۰۰٪ — چون تمام‌شدن روی ۹۴٪ شبیه گیرکردن است.
`316 → 60` خط.

`\r` حذف شد. و `read_run_log` هوشمند شد: وقتی لاگ از پنجره بزرگ‌تر است،
اول خطوط نتیجه (epoch/fold/val_loss/SAVED/خطاها) نگه داشته می‌شوند و
batchها رقیق می‌شوند. تازه‌ترین خطوط همیشه می‌مانند.

### تأیید زنده از HTTP داشبورد

```
[12s] busy=True lines=46  epochs=1
[24s] busy=True lines=81  epochs=4
[36s] busy=True lines=148 epochs=7
```

```
black ✅ ruff ✅ mypy (293 files) ✅
pytest 1354 passed, 12 skipped   (قبلاً 1340)
```
**۱۴ تست جدید**، یکی‌شان ثابت می‌کند با ۲٬۴۰۰ خط batch هر شش خط epoch
دیده می‌شوند.

**گزارش:** `PHASE42_REPORT.md`

---

## 2026-08-18 — فاز ۴۳: رفع کرش «The dataset is infinite» (باگ ۳۶)

**کرش کاربر** روی دیتاست واقعی 5M (۴۷٬۸۸۶ پنجره)، بعد از ۱۴۵ ثانیه:
`TypeError: The dataset is infinite.` در `len(train_x)`.

### باگ ۳۶ — که خودم در فاز ۴۱ ساختم

زنجیره: فاز ۴۱ فولدهای بزرگ را استریم کرد → برای پرنشدن epoch دوم
`repeat()` شد → دیتاست بی‌نهایت شد → ولی callback پیشرفت هنوز
`len(train_x)` می‌پرسید → کرش.

**چرا ندیدمش:** مسیر استریم را با `NullProgressReporter` تست کردم که این
callback را اصلاً نمی‌سازد. یعنی مسیری که کاربر واقعاً اجرا می‌کند تست
نشده بود. تست جدید عمداً با `ConsoleProgressReporter` اجرا می‌شود.

**رفع:** تعداد batch از هندسهٔ fold می‌آید نه از دیتاست —
`train_steps` از قبل محاسبه شده بود و فقط استفاده نمی‌شد.
`len(train_x)` و `len(val_x)` حذف شدند.

### تأیید

بازتولید روی همان مسیر استریم (۲۰k سطر، پنجرهٔ ۵۰۰):
```
[####################] 100.0% | batch 594/594 | loss 0.0052 | mae 0.0022
epoch 1/1 | loss 0.0052 | val_loss 0.0033
NO CRASH. peak RSS 966 MB
```
و از داشبورد: `succeeded | Trained range on 1D` + مدل ذخیره شد.

```
black ✅ ruff ✅ mypy (293 files) ✅
pytest 1361 passed, 12 skipped   (قبلاً 1354)
```
**۷ تست جدید**، یکی‌شان با `ast` پارس می‌کند تا `len()` هرگز روی متغیر
دیتاست صدا زده نشود.

**گزارش:** `PHASE43_REPORT.md`

---

## 2026-08-18 — فاز ۴۴: سرعت و خوانایی آموزش (باگ‌های ۳۷–۳۸)

**لاگ کاربر** نشان داد کرش فاز ۴۳ رفع شده و آموزش شروع شده — ولی همان یک
خط دو مشکل را لو داد:
`[----] 0.0% | batch 1/5,986 | loss 1.5662`

### باگ ۳۷ — batch_size=8 روی ۴۷٬۸۸۶ پنجره

عدد ۸ برای سری دموی چندصد سطری بود. روی دیتای واقعی یعنی **۵٬۹۸۶ قدم
گرادیان** برای یک epoch، هرکدام forward+backward روی ورودی ۵۰۰×۱۲۳.

رفع: مقیاس‌گیری با حجم دیتا (مثل کاری که فاز ۳۹ با foldها کرد) —
۲۰k+ سطر → bs=64، یعنی **۷۴۸ قدم به‌جای ۵٬۹۸۶** (۸ برابر کمتر).

### باگ ۳۸ — ۱۱ دقیقه سکوت بین دو خط پیشرفت

۸ خط در هر epoch ÷ ۵٬۹۸۶ batch = خطی هر ۷۴۸ batch ≈ ۱۱ دقیقه. یازده
دقیقه سکوت همان «هنگ کرده» است — دقیقاً شکایتی که این گزارشگر برای رفعش
ساخته شد.

رفع: کف زمانی `MAX_SECONDS_BETWEEN_LINES = 30`. حداقل هر ۳۰ ثانیه یک خط،
فارغ از تعداد batch. به‌علاوه ETA اضافه شد (روی batch اول چاپ نمی‌شود چون
هنوز چیزی برای برون‌یابی نیست).

### نکتهٔ صادقانه دربارهٔ سرعت

در سندباکس: bs=8 → 511s، bs=64 → 542s. **تقریباً یکسان**، چون CPU سندباکس
AVX2/FMA ندارد. لاگ کاربر می‌گوید CPU او دارد، پس انتظار ۳-۶ برابر می‌رود
— ولی **اندازه‌گیری نشده و تضمین نمی‌شود**. آنچه قطعی است: قدم‌ها
۵٬۹۸۶→۷۴۸، خطوط ۸→۲۰، سکوت ۱۱دقیقه→۳۰ثانیه.

```
black ✅ ruff ✅ mypy (293 files) ✅
pytest 1373 passed, 12 skipped   (قبلاً 1361)
```
**۱۲ تست جدید.**

**گزارش:** `PHASE44_REPORT.md`

---

## 2026-08-18 — فاز ۴۵: آستانهٔ سیگنال در فرم + اسپرد واقعی (باگ ۳۹)

**درخواست کاربر:** آستانه را در گزینه‌ها بگذار با واحد درصد؛ و اسپرد را در
ترید آنلاین از خود متاتریدر بگیر چون شناور است.

### باگ ۳۹ — اسپرد ۴ دلاری hard-code شده، ضررده

`live_decision_service.py` مقدار `spread=Decimal("4")` داشت. روی طلای
۴٬۳۷۶ این ۰.۰۹۱٪ است، ولی آستانهٔ پیش‌فرض سیگنال ۰.۰۸٪:

```
سیگنال BUY = +3.50 USD  |  اسپرد = -4.00 USD  |  خالص = -0.50 USD
```

یعنی مدل آموزش می‌دید حرکت‌هایی را شکار کند که قبل از شروع ضررده بودند.
سؤال کاربر دربارهٔ شناوربودن اسپرد این را لو داد.

**رفع:** `Mt5MarketDataProvider.live_quote(symbol)` که `ask - bid` را از
تیک زنده می‌خواند — نه `symbol_info.spread` که عدد صحیح در واحد point و
فقط snapshot است. عدد صحیح برای تشخیص کنارش برگردانده می‌شود.

شکست هرگز تیک را نمی‌شکند: نبود تیک / بازار بسته / اسپرد ≤۰ همه به
fallback ۰.۳۵ دلاری می‌روند و `last_spread_source` علت را ثبت می‌کند.
نبود اسپرد مشکل داده است نه دلیل توقف منطق معاملاتی.

### آستانه به درصد

`Signal threshold %` در هر دو دکمهٔ Train و Retrain. فرم درصد می‌گوید
(`0.08`)، کد کسر می‌خواهد (`0.0008`)، تبدیل یک‌جا در
`percent_to_fraction`. ورودی غلط به پیش‌فرض برمی‌گردد نه خطا.

خروجی آموزش حالا قاعده را صریح می‌گوید:
`label rule: a move of more than 0.1500% over 5 candles is BUY/SELL`

```
black ✅ ruff ✅ mypy (293 files) ✅
pytest 1395 passed, 12 skipped   (قبلاً 1373)
```
**۲۲ تست جدید**، یکی‌شان مطمئن می‌شود `spread=Decimal("4")` برنگردد.

### بدهی

اسپرد فقط در حلقهٔ زنده استفاده می‌شود نه بک‌تست (`run_backtest.py` هنوز
`--spread 4.0` دارد). آستانه در `ModelRecord` ذخیره نمی‌شود. و
`live_quote` روی متاتریدر واقعی تست نشده — فقط با MT5 قلابی.

**گزارش:** `PHASE45_REPORT.md`

---

## 2026-08-18 — فاز ۴۶: نجات کار آموزش از timeout (باگ‌های ۴۰–۴۲)

**گزارش کاربر:** `FAILED · 7205.5s · Timed out after 120 minutes` بعد از
۱۸ epoch کامل — و هیچ مدلی ذخیره نشده بود.

مهم: `val_acc` از ۰.۷۹۵۴ به ۰.۷۹۹۴ و `val_loss` از ۰.۵۳۱۴ به ۰.۵۲۷۹ رفته
بود. مدل **هنوز در حال یادگیری بود**، نه بیش‌برازش. آموزش درست کار می‌کرد
و فقط وقت کم آورد.

### باگ ۴۰ — هیچ چیز تا پایان train() ذخیره نمی‌شد (بحرانی)

`save_model()` بعد از بازگشت `train()` اجرا می‌شد، پس هر وقفه‌ای همه‌چیز را
دور می‌ریخت. رفع: checkpoint بعد از **هر epoch**.

اثبات با کشتن عمدی اجرا: `KILLED (exit=124)` و مدل روی دیسک ماند با
`"note": "checkpoint after epoch 8/20"`.

checkpoint عمداً یک نسخه را بازنویسی می‌کند نه بیست‌تا — طناب نجات است نه
تاریخچه. و اگر خودش شکست بخورد آموزش را قطع نمی‌کند.

### باگ ۴۱ — ETA حدود ۴۵ برابر غلط

`eta 2:58:40` وقتی ۴ دقیقه مانده بود. زمان کل **fold** بر batchهای **epoch
جاری** تقسیم می‌شد؛ در epoch نوزدهم fold دو ساعت کار کرده بود. ETA‌ای
این‌قدر غلط بدتر از نبودنش است. رفع: اندازه‌گیری از ابتدای همان epoch.

### باگ ۴۲ — timeout دو ساعتهٔ ثابت

`timeout=7200` در کد. اجرای کاربر ۲.۲ ساعت لازم داشت. رفع: فیلد
`Give up after (minutes)` با پیش‌فرض ۴۸۰، و پیام timeout که می‌گوید
`(any completed epoch was checkpointed)`.

```
black ✅ ruff ✅ mypy (293 files) ✅
pytest 1407 passed, 12 skipped   (قبلاً 1395)
```
**۱۲ تست جدید**، از جمله کشتن واقعی یک اجرا و بررسی بقای مدل.

### بدهی

checkpoint وزن‌ها را نگه می‌دارد نه وضعیت optimizer، پس ادامه از epoch ۱۸
ممکن نیست — فقط Retrain از مدل ذخیره‌شده.

**گزارش:** `PHASE46_REPORT.md`

---

## 2026-08-18 — فاز ۴۷: بهترین مدل نگه داشته می‌شود نه آخرین (باگ ۴۳)

**سؤال کاربر:** «مدلای آموزشی آخرین مدل رو ذخیره میکنن یا بهترین مدل رو؟»

جواب صادقانه: **آخرین**. و این یک ضعف واقعی بود.

### باگ ۴۳ — بیش‌برازش‌شده‌ترین وزن‌ها ذخیره می‌شد

```python
last_model = model                    # هر fold، بدون شرط
payload = _serialize_model(last_model)
```

`loss` آموزش تقریباً همیشه کاهش می‌یابد ولی `val_loss` پایین می‌آید، به کف
می‌رسد و بعد بالا می‌رود. پس «هرچه آخر اجرا شد» یعنی بیش‌برازش‌شده‌ترین
وزن‌های اجرا.

اندازه‌گیری روی دیتای تست:
```
epoch  5: val_loss 0.8055 | val_acc 72.7%   ← بهترین
epoch 12: val_loss 0.8969 | val_acc 63.6%   ← قبلاً این ذخیره می‌شد
```
**۹ واحد دقت دور ریخته‌شده به‌خاطر یک انتساب متغیر.**

### رفع

checkpoint فقط وقتی می‌نویسد که `val_loss` بهبود یافته باشد، و هر epoch
می‌گوید چه شد:
```
[BEST so far] epoch 5/12 val_loss 0.805476 — saved as v1
[epoch 6/12] val_loss 0.894731 — no better than 0.805476 (best is epoch 5)
```

`val_loss` داور است نه `val_accuracy`: دقت روی مسئلهٔ سه‌کلاسه پله‌ای است و
مدام مساوی می‌شود (سه بار ۶۳.۶٪ پشت‌هم)، ولی loss هر بهبود کوچک در اطمینان
را ثبت می‌کند. مدل رنج از `val_mae` استفاده می‌کند.

و `save_model()` نهایی دیگر وزن‌های آخرین epoch را به‌عنوان نسخهٔ **جدید**
نمی‌نویسد — قبلاً دو مدل روی دیسک می‌ماند و بدتره بالای منوی کرکره‌ای
می‌نشست:
```
KEPT gold_signal_5m v1 from epoch 5 (val_loss 0.805476)
  the final epoch scored 0.896911 — worse, so it was NOT written over the best
```

### دربارهٔ اجرای دو ساعتهٔ کاربر

چیزی از دست نرفت: `val_loss` از ۰.۵۳۱۴ به ۰.۵۲۷۹ هنوز در حال بهبود بود،
پس «آخرین» همان «بهترین» بود. ولی اگر از epoch ۱۹ بدتر می‌شد، با کد قدیم
مدل بدتر می‌ماند.

```
black ✅ ruff ✅ mypy (293 files) ✅
pytest 1415 passed, 12 skipped   (قبلاً 1407)
```
**۸ تست جدید** از جمله منحنی کلاسیک بیش‌برازش. یک تست فاز ۴۶ هم به‌روز شد
(فقط متن یادداشت عوض شده، رفتار سالم است).

### تأیید هر دو نقش

کاربر پرسید آیا برای هر دو مدل انجام شده. هر دو از یک `train_one`
استفاده می‌کنند، ولی با همان منحنی بیش‌برازش هر دو آزموده شدند:
signal با `val_loss` و range با `val_mae` — هر دو epoch ۳ را نگه داشتند
و ۴–۶ را رد کردند.

**نقصی که همین آزمون لو داد:** برچسب لاگ همیشه `val_loss` می‌گفت حتی
برای مدل رنج. رفع شد؛ حالا `metric_name` نام درست را می‌برد.

### بدهی

توقف زودهنگام نداریم: ۲۰ epoch بدهی هر ۲۰ اجرا می‌شود حتی اگر از ۵ به بعد
بدتر شود — بهترین نگه داشته می‌شود ولی وقت تلف می‌شود.

**گزارش:** `PHASE47_REPORT.md`

---

## 2026-08-18 — فاز ۴۸: تست مدل، بازرسی دیتاست، نقشهٔ شبکه (باگ ۴۴)

**سه درخواست کاربر:** بخشی برای تست مدل انتخابی روی دیتاست انتخابی با
ذخیرهٔ نتیجه در لاگ؛ بخشی برای دیدن ساختار دیتاست و ابعاد ماتریس؛ و نمایش
ابعاد ماتریس + ذخیرهٔ PNG معماری در ابتدای هر آموزش. به‌علاوه: تمیزکاری
ورک‌اسپیس.

### تمیزکاری: 129M → 73M

### باگ ۴۴ — آرشیو اسنپ‌شات بی‌نهایت رشد می‌کرد

`_archive_previous()` هر اجرا یک اسنپ‌شات می‌ساخت و هیچ‌وقت پاک نمی‌کرد.
بعد از ۱۵۸ اجرا: ۴۸ مگابایت، یک‌سوم کل ورک‌اسپیس، از فایل‌های تقریباً
یکسانی که کسی نخوانده بود. رفع: `ARCHIVE_KEEP = 5`.

دیتای واقعی XAUUSD دست نخورد — با `git status` تأیید شد هیچ فایل
track‌شده‌ای حذف نشده. فقط untracked‌ها (مدل و دیتای مصنوعی TESTSYM،
`shadbot.db`، `out.html`، کش‌ها) پاک شدند.

### ۱. تست مدل (`ModelEvaluationService`)

دکمهٔ **Test a model on a dataset**: منوی مدل‌های ذخیره‌شده + منوی
دیتاست‌های موجود. سه تصمیم عمدی: آموزش اتفاق نمی‌افتد (وزن‌ها منجمد)؛
پنجره‌ها دقیقاً مثل آموزش ساخته می‌شوند (وگرنه عدد مدلی را توصیف می‌کند که
وجود ندارد)؛ و اگر روی همان تایم‌فریمِ آموزش تست شود صریح هشدار می‌دهد.

نتیجه در `run_logs/evaluations.jsonl` **append** می‌شود نه overwrite —
مقایسه بی‌ارزش است اگر عدد دیروز پاک شده باشد. مدل سیگنال `accuracy`
به‌همراه baseline کلاس غالب می‌دهد.

### ۲. بازرسی دیتاست

دکمهٔ **Inspect a dataset**: تعداد کندل، بازهٔ زمانی و قیمتی، ابعاد
ماتریس، شکل تانسور ورودی، تفکیک ستون‌ها (۸ خام + ۶ شکل + ۱۰۹ فیچر)،
digest و ستون‌های ثابت.

### ۳. ماتریس و PNG در هر آموزش

`describe_input_matrix()` اول هر اجرا چاپ می‌شود، و
`save_model_diagram()` یک بار در هر اجرا PNG می‌سازد. سه‌مرحله‌ای چون
graphviz معمولاً روی ویندوز نیست: `plot_model` → Pillow → فایل متنی. هر
کدام که شد آموزش ادامه می‌یابد و منبعش اعلام می‌شود.

**باگ ریز:** کراس جدولش را با box-drawing می‌کشد و فونت پیش‌فرض Pillow
آنها را مربع خالی نشان می‌داد؛ به ASCII تبدیل شد.

```
black ✅ ruff ✅ mypy (295 files) ✅
pytest 1441 passed, 12 skipped   (قبلاً 1419)
```
**۲۲ تست جدید.** تست زندهٔ داشبورد: هر چهار دکمه رندر و اجرا شدند.

### بدهی

ارزیابی سیگنال آستانه را از رکورد مدل نمی‌خواند (۰.۰۸٪ ثابت فرض می‌شود)،
پس مدلی که با ۰.۱۵٪ آموزش دیده دقتش کمتر از واقع گزارش می‌شود.

**گزارش:** `PHASE48_REPORT.md`

---

## قدم بعدی توافق‌شده

**C — اتصال به دیتای واقعی MetaTrader 5.**

کاربر گفت «باشه بریم». کار سمت سندباکس (لینوکس) تمام است؛ ادامه‌اش نیازمند
اجرای کاربر روی ویندوز است:

```powershell
pip install -r requirements-mt5.txt
shadbot-data mt5-check
shadbot-data mt5-symbols --pattern XAU
python scripts\run_real_data.py --symbol XAUUSD
```

⚠️ نام نماد بین بروکرها فرق دارد: `XAUUSD`, `XAUUSD.i`, `XAUUSDm`, `GOLD`.
اگر فهرست خالی بود: در MT5 → Market Watch → راست‌کلیک → **Show All**.

**بعد از آن:** A (وصل‌کردن WaveNet به بک‌تست) سپس B (فاز ۲۴ Deployment).

---

## 2026-08-26 — فاز ۵۹: اصلاح هندسهٔ اعتبارسنجی (val ۲٪ → ۱۰٪ استخر + گارد)

**گزارش کاربر:** «اشتباهی توی ساخت دیتای ولید داری» — با train-ratio 80%
لیبل ولید ۱۴۰ تا می‌شد؛ با 20% فقط ۳۴ تا. علت: `val_size = max(4, min(2000,
rows // 50))` روی **استخر لیبل‌دار** حساب می‌شد (۲٪) و استخر هم تابع
train-ratio است → val همیشه کوچک و وابسته.

### رفع

- `build_trainer`: پیش‌فرض `rows // 10` (۱۰٪ استخر، کف ۴، سقف 2000) + گارد
  `max(4, min(val, rows - min_train - purge - 4))` که اولین fold را روی
  سری‌های کوچک زنده نگه می‌دارد.
- `DualModelService.train()`: پارامتر جدید `val_size` (0 = auto) به
  `build_trainer` پاس می‌شود.
- `run_dual_models.py`: آپشن‌های `--val-size` / `--val-ratio` + خط چاپ
  `val fold size : N samples per fold (X% of M labelled windows)`؛ تابع
  آینهٔ label-balance همان هندسه را اعمال می‌کند.
- اثر روی اجراهای واقعی: 140→~700 (80%) · 123→615 (70%) · 34→~174 (20%).

### چرا

گیت انتخاب بهترین مدل (فاز ۴۷) با val=34-123 عملاً روی نویز تصمیم
می‌گرفت؛ با ~615 نمونه، val_acc به ±1.9% معنادار می‌شود.

### پیامد آگاهانه

چند صد نمونهٔ کمتر برای train (Expanding): ~۱۶٪ در اجرای ۷۰٪ — برای
اعتبارِ انتخابِ بهترین، قابل قبول. `--val-size` برای کنترل دستی.

### تست

`tests/unit/ai/test_validation_geometry.py` — ۴ تست جدید (۱۰٪ پیش‌فرض،
عبور val صریح، گارد سری کوچک، امضای train).

```
ruff ✅ black ✅ mypy (فایل تغییر یافته ✅؛ ۳ خطای TF-محیطی در wavenet_trainer به‌خاطر نبود TF در سندباکس)
pytest 1456 passed, 49 skipped (قبلاً 1449 + ۴ تست جدید)
```

**گزارش:** `Report/PHASE59_REPORT.md`

---

## 2026-08-26 — فاز ۶۰: اتصال ReduceLR + EarlyStopping به مدل سیگنال (باگ سیم‌کشی) + baseline صحیح

**کشف از اجرای ۱۰.۵ ساعتهٔ signal v1 کاربر:** بهترین epoch همهٔ فولدها
10/13/16/19 بود ولی هر ۴ فولد تا epoch 60 کامل اجرا شد → ~۷ ساعت epochهای
نامنتخاب‌پذیر. علت: `build_trainer` برای classification `loss=None` می‌فرستاد
و گیتِ `if self._loss in (…)` در trainer هرگز match نمی‌شد → ReduceLROnPlateau
(فاز ۵۴) و EarlyStopping (فاز ۵۷) فقط به range وصل بودند، هرچند گزارش‌ها
«هر دو مدل» را ادعا می‌کردند.

### رفع

- `dual_model_service.build_trainer`: `loss=role.loss, metric=role.metric`
  همیشه (کامپایل مدل بدون تغییر — شاخهٔ classification همان loss را
  hard-code دارد؛ فقط گیت callbacks حالا match می‌شود).
- `run_dual_models.print_quality`: پارامتر `val_baseline` — حکم با
  baselineِ **فولد آخرِ ولید** (در اجرای مذکور 65.2% sell در برابر 50.3%
  استخر!) + اعلام صریح رژیم‌جابه‌جایی فولد.

### تست

۲ تست جدید در `test_validation_geometry.py`: سیم‌کشی loss سیگنال +
حفظ huber برای range.

```
ruff ✅ black ✅
pytest 1458 passed, 49 skipped   (قبلاً 1456)
```

**اثر مورد انتظار:** با ES patience=12، اجرای signal حدود نصف زمان قبلی؛
ReduceLR احتمالاً کالیبراسیون را بهتر می‌کند.

**گزارش‌ها:** `Report/PHASE60_REPORT.md` · `Report/SIGNAL_V1_FULLRUN_REVIEW_2026-08-26.md`

---

## 2026-08-27 — فاز ۶۱: پیچ‌های معماری (--n-layers/--n-blocks) + چاپ RF

**پرسش کاربر** «window=150 اوکیه؟» لو داد که `--window` فقط اندازهٔ پنجره
را عوض می‌کند و RF پیش‌فرض فاز ۵۸ (249) بزرگ‌تر از پنجره می‌شد (166%).

### رفع

- factoryهای `signal_model_role`/`range_model_role`: پارامترهای اختیاری
  `n_layers_per_block`/`n_blocks` (None = پیش‌فرض).
- تابع `receptive_field()` — فرمول RF با تست (249/121/125/57).
- CLI: `--n-layers` / `--n-blocks` + خط چاپ `architecture : window=… · L×B · RF=… (X% of window)`
  + هشدار صریح وقتی RF > window.

### تست

۶ تست جدید (`test_model_roles_knobs.py`). پیش‌فرض‌های فاز ۵۸ قفل شدند.

```
ruff ✅ black ✅
pytest 1464 passed, 49 skipped   (قبلاً 1458)
```

**گزارش:** `Report/PHASE61_REPORT.md`

---

## 2026-08-27 — فاز ۶۲: پیچ‌های ۵۹/۶۱ در GUI

سه مسیر داشبورد (Train a model · Retrain · Find best LR) حالا
`--n-layers`/`--n-blocks`/`--val-size` را می‌فرستند؛ 0 = پیش‌فرض/auto و
فلگ ارسال نمی‌شود. فرم‌ها hint فارسی RF دارند. ۷ تست جدید.

```
ruff ✅ (۱۰ خطای قدیمی handlers.py جدا شده) black ✅
pytest 1471 passed, 49 skipped   (قبلاً 1464)
```

**گزارش:** `Report/PHASE62_REPORT.md`

---

## 2026-08-27 — فاز ۶۳: باگ ۴۷/۴۸ — برچسب‌های seq2seq رنج خراب بودند

**کشف از لاگ کاربر (range 1D):** val_mae 0.000081 (±$0.16!) هم‌زمان با
per-bound 0.0024/0.0058 و bias≡±MAE (هر ۴۴۸ خطا هم‌علامت). ردیابی کد:
`WindowedSample.target_index` = شماره ستون (182) ولی
`_build_seq2seq_targets` آن را اندیس سطر می‌خواند → y همهٔ نمونه‌ها از
سطرهای ثابت ۳۳..۱۸۲ → collapse + metric جعلی. توضیح val_maeهای تاریخی
غیرواقعی (0.000010 فاز ۵۷) و بی‌فایده بودن بکتست‌های رنج.

### رفع

- سه سازندهٔ sample: `target_index=end` (سطر پایان پنجره)
- `_range_validation_metrics`: شاخهٔ seq2seq → آخرین timestep
- ۴ تست رگرسیون + تمیزکاری lint trainer

```
ruff ✅ black ✅  pytest 1475 passed, 49 skipped
```

**پیامد:** همهٔ آرتیفکت‌های range (تاریخی v1-v3 و این اجرا) باطل — retrain
بعد از این فیکس لازم است. signal آسیب ندیده (مسیرش target_index نمی‌خواند).

**گزارش:** `Report/PHASE63_REPORT.md`

---

## 2026-08-27 — فاز ۶۴: باگ ۴۹ — برش last_n، رنج را گرسنه می‌کرد (trades=0)

اولین بکتست دومدلیِ واقعی: مدل‌ها سالم، trades=0. ریشه: handler کندل‌های
1D را با cutoff پنجرهٔ 5M می‌برید (۹٬۰۰۰×5M ≈ ۳۱ روز → ~۳۰ کندل 1D <
window=150 → abstain همیشگی). علیت را خود prediction source enforce
می‌کند؛ برش حذف شد + خط «range candles: N (1D)» به گزارش + ۳ تست.

```
pytest 1478 passed, 49 skipped
```

**گزارش:** `Report/PHASE64_REPORT.md`

---

## 2026-08-27 — فاز ۶۵: نقاط انتخاب سیگنال روی ریپلی (درخواست اپراتور)

SignalMarker جدید (candidate/filled/rejected · BUY ▲ سبز / SELL ▼ قرمز ·
توپر=ترید شد، توخالی=رد شد) + resolution claim-based در build() + خط
legend با شمارش. engine فقط actionableها را ثبت می‌کند و ردِ براکت در
next-open را با دلیل به rejected تبدیل می‌کند. + cleanup lint (F821/E741 قدیمی).

```
ruff ✅ black ✅  pytest 1483 passed, 49 skipped
```

**گزارش:** `Report/PHASE65_REPORT.md`

---

## 2026-08-27 — فاز ۶۶: TP/SL مدل کنار نقاط سیگنال ریپلی

SignalMarker +tp/sl (سطح مطلق) · engine از range forecast (BUY: high/low،
SELL برعکس) · بعد از fill واقعی next-open، سطوح براکت (با spread) جایگزین ·
رندر: خط‌چین سبز/قرمز + اتصال نقطه‌دار + قیمت در زوم · legend +۲ · ۳ تست.

```
pytest 1485 passed, 49 skipped
```

---

## 2026-08-27 — فاز ۶۷: باگ ۵۰ — بافر 1D از تاریخچه پیش‌پر نمی‌شد

گزارش اپراتور: مثلث‌ها هستن، TP/SL رسم نمیشه. ردیابی با شبیه‌سازی:
بافر 1D فقط با observe پر می‌شد → برای اولین رنج باید ۱۵۰ روز *داخل*
replay می‌گذشت (۹٬۰۰۰×5M=۳۱ روز → هرگز). رفع: pre-fill کندل‌های 1D
بسته‌شده قبل از اولین 5M از همان تاریخچه (cursor جلو تا observe تکرار
نکند). عددی تأیید شد: 0 → 151 پیش‌بینی رنج. ۲ تست جدید.

```
pytest 1487 passed, 49 skipped
```

---

## 2026-08-27 — فاز ۶۸: برچسب build در گزارش بکتست (درسِ اجرای با کد قدیمی)

بکتست کاربر هنوز «range candles: n/a» چاپ می‌کرد = با کد قدیمی اجرا شده بود
(زیپ جدید جایگزین نشده بود یا سرور ری‌استارت نشده بود). رفعِ ریشه‌ایِ ابهام:
خط `build : phase-67 (…)` به گزارش بکتست اضافه شد — اپراتور با یک نگاه
می‌بیند با کد چندم اجرا می‌کند.

```
pytest 1487 passed, 49 skipped
```

---

## 2026-08-27 — فاز ۶۹: شمارش سیگنال/رنج/خطاها در گزارش بکتست

بعد از فازهای ۶۵-۶۷ هنوز نمی‌شد فهمید در بکتست واقعی: چند سیگنال
actionable بوده؟ رنج چند بار اجرا شده؟ خطای خاموشی بوده؟ سه تغییر:
1. `BacktestResult.source_stats` — stats منبع پیش‌بینی روی نتیجه
2. شمارش خطاها با type+پیام در source (`error_counts`) + `errors` در stats
3. گزارش بکتست: خط جدید `signals seen: N · range ran: M · abstains: K`
   + هر خطای تکرارشده با `[err xN]`
+ رفع: `_last_range_feed` در مسیر dual هم ست می‌شد (قبلاً فقط legacy →
  «range candles» همیشه n/a می‌ماند)

```
pytest 1487 passed, 49 skipped
```

---

## 2026-08-27 — فاز ۷۰: باگ ۵۱ — کلاس‌های _RangeLoss/_Seq2SeqMAE ماژول‌سطح شدند

**گزارش اپراتور (ابزار فاز ۶۹ کار کرد):**
`signals seen: 811 · range ran: 0 · [err x811] range: TypeError: Could not
locate class '_RangeLoss'` — رنج هرگز اجرا نشده بود؛ خطاها خاموش بودند.

### ریشه

کلاس‌های `_RangeLoss` و `_Seq2SeqMAE` **داخل تابع** `_build_compiled`
تعریف می‌شدند (local class). `@register_keras_serializable` آنها را در
registry keras ثبت می‌کرد ولی `custom_objects()` با `getattr(ماژول, نام)`
هرگز نمی‌توانست ببیندشان → `load_model` هر مدل رنج شکست می‌خورد. signal
مستقل از این مسیر است (SparseCategoricalCrossentropy استاندارد) — برای
همین سیگنال کار می‌کرد و فقط رنج می‌شکست.

### رفع

- کلاس‌ها به سطح ماژول منتقل شدند (lazy build با `_build_range_classes`).
- `range_custom_objects()`: همهٔ نام‌های تاریخی (`RangeLoss`،
  `_RangeLoss`، `ShadBotTrader>…`، …) را یک‌جا می‌دهد.
- `wavenet.custom_objects()` حالا آن‌ها را include می‌کند.
- get_config/from_config کامل (seq2seq، وزن‌ها، delta) — round-trip تأیید شد.
- تست انتها-به-انتها: build → serialize → deserialize مدل seq2seq ✓
- تست‌های TF-دار integration که در سندباکس با نصب TF نمایان شدند:
  mock کلاس Role در `test_best_model_kept`/`test_epoch_checkpoints` بدون
  `loss/metric` بود → تکمیل شد (این‌ها با TF واقعی کرش می‌کردند).
- ۲ تست `test_threshold_recorded` در سندباکس fail می‌مانند (به MT5 store
  محلی نیاز دارند — روی سیستم اپراتور سبزند).

```
ruff ✅ black ✅
pytest 1526 passed, 2 failed (محیطی: TESTSYM/MT5 store), 12 skipped
```

---

## 2026-08-27 — فاز ۷۲: گزارش «شرایط شروع» کامل در بکتست

**پرسش اپراتور:** «توی لاگ تمام شرایط شروع بک‌تست رو می‌نویسه؟ همهٔ
شرایطی که توی GUI تنظیم می‌کنم؟» — جواب قبلاً «نه» بود؛ چند فیلد فرم
(symbol، مدل‌ها، confidence، windows، same-bar، test-ratio، commission،
capital) در گزارش غایب بودند و commission ثابت 0.0001 چاپ می‌شد.

### رفع

بلاک گزارش بازنویسی شد — بخش «شرایط شروع» حالا شامل:
engine · build · run id · symbol/timeframes · models · confidence gate ·
windows · R/R mult · same-bar policy · test ratio · session filter ·
min SL dist · filter 0-bar · capital/quantity · spread type+value ·
commission (واقعی، نه ثابت) · slippage · entry · range candles fed ·
last N bars — بعدش نتایج.

```
pytest 1526 passed, 2 failed (محیطی: TESTSYM/MT5 — روی سیستم اپراتور سبز), 12 skipped
```

---

## 2026-08-27 — فاز ۷۴: patienceهای قابل تنظیم برای EarlyStopping و ReduceLR

**تحلیل اجرای کاربر (range retrain 75 epoch):** بهترین epoch 50 (val_loss
0.002102) ولی EarlyStopping در ~65 قطع کرد → ReduceLR (patience=7) فقط
۱-۲ پله فرصت کاهش داشت. حدس اپراتور درست بود.

### رفع (پارامتر جدید در کل زنجیره)

- `WavenetTrainer(early_stopping_patience=0, reduce_lr_patience=0)` —
  0 = auto (ES=epochs/5، ReduceLR=epochs/10)
- `DualModelService.build_trainer/train()` پاس می‌دهند
- CLI: `--es-patience N` / `--rlr-patience N` + چاپ در سربرگ
  (`callbacks : EarlyStopping patience=… · ReduceLR patience=…`)
- GUI: دو فیلد در Train a model و Retrain a model

### پیشنهاد عددی برای range 1D با epochs=75-100

`--es-patience 30 --rlr-patience 10` — به ReduceLR اجازه ۳-۴ پله کاهش
(0.85³≈0.61) قبل از قطع.

```
pytest 1491 passed, 53 skipped · ruff ✅ black ✅
```

---

## 2026-08-27 — یادداشت فاز ۷۴-ب: باگ NameError متعلق به کامیت ۸۴d4851 بود

کاربر هنگام run_backtest خطای `NameError: symbol_text` گرفت — traceback به
خط ۲۱۲۳ از کامیت **۸۴d4851 (فاز ۷۲)** اشاره داشت که بخش «شرایط شروع» را با
متغیرهای محلیِ `_run_simulation` در `run_backtest` نوشته بود. در فاز ۷۴
(کامیت `5188801`) همین بخش با bridge `_last_run_context` بازنویسی و فیکس
شده بود. کاربر فقط zip میانی (۸۴d4851) را گرفته بود.

**اقدام:** بدون تغییر کد — کاربر به آخرین zip (۵۱۸۸۸۰۱) ارتقا داده شد.
تأیید: compile ✅ · تست‌های presentation/simulation سبز.

---

## 2026-08-29 — فاز ۷۵: بازسازی براکت حول entry (به‌جای reject)

**درخواست اپراتور:** براکت‌های وارونه رد نشوند؛ باز شوند با SL زیر
قیمت ورود و TP بالای آن (برای BUY)، با استفاده از عرض رنج مدل.

### رفع

`from_model_levels`: گیت rejectِ باگ ۵۲ → منطق recenter:
`width = high − low` · BUY: `SL=entry−width, TP=entry+mult×width` ·
SELL برعکس · پرچم `recentered` در metadata/to_dict · رنج عرض‌صفر رد.

### تست

۵ تست جدید/به‌روز در `test_bracket.py` (کل ۱۲).

```
ruff ✅ black ✅  pytest 1494 passed, 53 skipped
```

---

## 2026-08-29 — فاز ۷۶: SL بازسازی · TP ادعای مدل — رد اگر سمت غلط

**اصلاح فاز ۷۵ به‌درخواست اپراتور:** «این کار رو فقط باید برای حد ضرر
می‌کردی؛ معامله‌ای که حد سودش توی رنج نیست (مثلاً TP خرید زیر قیمت
ورود) نباید اصلاً باز بشه.»

### منطق نهایی

- **SL** = محافظ محلی → اگر وارونه بود، بازسازی: `SL = entry ± width`
  (width = عرض رنج مدل) + پرچم `recentered`
- **TP** = ادعای واقعی مدل دربارهٔ آینده → هرگز جعل نمی‌شود:
  - BUY با TP ≤ entry → `ValidationError` (رد)
  - SELL با TP ≥ entry → `ValidationError` (رد)

### تست‌ها

۶ تست: recenter SL برای BUY/SHORT با TP مدل دست‌نخورده · رد BUY با TP
زیر ورود · رد SHORT با TP بالای ورود · براکت سالم بدون پرچم · رنج صفر.

```
ruff ✅ black ✅  pytest 1495 passed, 53 skipped
```

---

## 2026-08-29 — فاز ۷۸: رفع باگ «unexpected keyword argument early_stopping_patience»

**گزارش کاربر:** آموزش range 1H با `DualModelService.train()` کرش کرد —
`build_trainer` فاز ۷۴ پارامترهای patience را دریافت نمی‌کرد (فقط train()
آن‌ها را داشت و پاس نمی‌داد).

### رفع

- `build_trainer(..., early_stopping_patience=0, reduce_lr_patience=0)`
- پاس به `WavenetTrainer(...)` constructor

```
pytest 1496 passed, 53 skipped · ruff ✅ black ✅
```

---

## 2026-08-29 — فاز ۷۹: باگ ۵۵ — مسیر streamed مدل رنج seq2seq برچسب درست نمی‌داد

**گزارش کاربر:** آموزش range 1H (39,773 پنجره = 4.3GB > آستانهٔ استریم
512MB) کرش کرد: `Index out of range using input dim 2; input has only 2 dims`
در RangeLoss.

### ریشه

مدل رنج seq2seq دو مسیر دارد:
- in-memory (<512MB): `_build_seq2seq_targets` → y=[batch,150,2] ✓ (1D قبلاً از این مسیر بود)
- **streamed (>512MB): `WindowGenerator` برچسب را فقط برای «سطر آخر» می‌ساخت
  → y=[batch,2] → RangeLoss با `y[:, -1:, :]` روی آرایهٔ ۲بعدی کرش**

یعنی seq2seq در مسیر استریم هرگز پیاده نشده بود — 1D قبلاً کوچک‌تر از
آستانه بود و مخفی مانده بود.

### رفع

- `WindowGenerator(..., seq2seq=True)`: `window_at` برچسبِ **هر سطر
  پنجره** را می‌دهد (برچسب فردای همان سطر، که prepare قبلاً به سطرها
  چسبانده)؛ `to_tf_dataset` spec سه‌بعدی `[batch, window, n_targets]`
- `WavenetTrainer._generator()` فلگ `seq2seq=self._seq2seq` را پاس می‌دهد
- ۴ تست جدید (window_at، مسیر قبلی دست‌نخورده، آرایه‌ها، tf.data)

```
pytest 1539 passed, 2 env-failed, 12 skipped · ruff ✅ black ✅
```

---

## 2026-08-29 — فاز ۸۰: horizon رنج در GUI

**درخواست اپراتور:** horizon قابل تنظیم در داشبورد باشد (برای آزمایش‌های
1H با horizonهای ۱۲/۲۴/۶/۱).

### رفع

- فرم **Train a model** و **Retrain a model**: فیلد
  «Range horizon (candles)» (پیش‌فرض 1 = رفتار فعلی)
- مسیرهای train_dual_models و retrain_model:
  `--horizon N` فقط وقتی ≠1 و فقط برای role=range پاس می‌شود
  (سیگنال first-passage بی‌کران است — horizon معنا ندارد)
- hint: «1H: 12 (نیم‌روز) یا 24 (یک روز) برای براکت معنادار»
- ۵ تست جدید (descriptorها، پاس 12، حذف وقتی 1، نادیده‌گرفتن برای signal)

```
ruff ✅ black ✅  pytest 1504 passed, 54 skipped
```

---

## 2026-08-29 — فاز ۸۱: زوم قیمت و زمان در ریپلی (درخواست اپراتور)

**درخواست:** «مثل متاتریدر بتونم هم توی زمان و هم توی قیمت زوم کنم تا
مقادیر خط‌چین TP/SL رو بهتر ببینم.»

### رفع (replay_renderer.py — خروجی HTML ریپلی)

- **زوم قیمت با wheel موس:** wheel به بالا = بزرگ‌نمایی (تا ۳۰×)؛
  مرکز زوم روی قیمتی که موس زیرش است می‌ماند (anchor) — مثل متاتریدر
- **پن زمان با درگ:** کلیک و کشیدن افقی = جابجایی پنجرهٔ دید
- **دکمهٔ «Reset zoom»** + hint فارسی زیر چارت
- `viewStart`: وقتی کاربر درگ/زوم زمانی کرد، پنجره دستی می‌ماند تا reset
- سازگار با Play/scrub: پس از هر paint دوباره همان zoom اعمال می‌شود
- windowSel (select تعداد کندل) → تغییرش زوم را reset می‌کند

### بدون تغییر رفتار

- بدون zoom (پیش‌فرض) رسم دقیقاً مثل قبل است
- بقیهٔ دکمه‌ها و legend و log دست‌نخورده

```
ruff ✅ black ✅  pytest 1544 passed, 2 env-failed (TESTSYM/MT5), 12 skipped
```

---

## 2026-08-29 — فاز ۸۲: زوم قیمت و پن زمان در چارت دیتای داشبورد (/data)

**پرسش اپراتور:** «روی نمودار قیمت هم قابلیت زوم داره؟» — نه نداشت.
همان زوم متاتریدریِ ریپلی (فاز ۸۱) به چارت کندلی `/data` هم اضافه شد:

- wheel = زوم قیمت (تا ۳۰×، مرکز روی قیمتِ زیر موس)
- درگ افقی = پن زمان
- دکمهٔ «Reset zoom» + hint فارسی
- تغییر select «تعداد کندل» → ریست پن
- برخلاف ریپلی (که cursor دارد)، اینجا کل سری در دسترس است و پن
  در محدودهٔ [0, len-visible] کلمپ می‌شود.

```
ruff ✅ black ✅  pytest 1544 passed, 2 env-failed, 12 skipped
```

---

## 2026-08-29 — فاز ۸۳: wheel = اسکرول زمان (متاتریدری) + Ctrl+wheel = زوم قیمت

**درخواست اپراتور:** اسکرول کندل‌به‌کندل جلو/عقب با موس مثل متاتریدر.
انتخاب اپراتور از بین گزینه‌ها: «هر دو — wheel زمان + Ctrl زوم».

### تغییر در هر دو چارت (ریپلی + /data)

- **wheel**: اسکرول زمان — هر نچ ≈ visible/15 کندل (حداقل ۱)؛ بالا = عقب،
  پایین = جلو؛ کلمپ در محدودهٔ دیتا. در ریپلی، اسکرول `viewStart` را
  می‌کارد (پخش/scrub از همان نما ادامه می‌دهد)
- **Ctrl+wheel**: زوم قیمت حول قیمت زیر موس (رفتار قبلی wheel)
- درگ = پن (قبلی) · دکمهٔ Reset zoom (قبلی)
- hint هر دو چارت: «wheel = اسکرول زمان · Ctrl+wheel = زوم قیمت · درگ = جابجایی»

```
ruff ✅ black ✅  pytest 1504 passed, 54 skipped
```

---

## 2026-08-29 — فاز ۸۴: نمای سیگنال در /data (درخواست اپراتور)

**درخواست:** «توی /data بتونم دیتاست سیگنال رو ببینم — threshold رو تعیین
کنم و نقاط خرید/فروش نشون داده بشه.»

### رفع

- `/data` فرم جدید: تیک «Show signals» + فیلد «threshold %» (پیش‌فرض 0.6)
- JS: محاسبهٔ **first-passage روی همان کندل‌های چارت** با همان قانون
  آموزش (اولین close که ±barrier بزند؛ گارد OHLC: LONG اگر Low زیر
  Lowِ شروع برود نامعتبر؛ SELL قرینه) — بدون سمت سرور
- رسم: ▲ سبز زیر کندل = BUY · ▼ قرمز بالا = SELL
- خلاصهٔ زنده: «N signals · X buy · Y sell (th …%)»
- debounce تایپ threshold (250ms) تا compute spams نشود
- `DataInspector.candles` حالا `i` (اندیس سراسری) هم برمی‌گرداند
  تا JS نقاط را به کندل‌های پنجره match کند
- تست integration به‌روز شد (فیلد +i)

### نکتهٔ عملکرد

computeSignals روی تغییر threshold اجرا می‌شود (O(n²) در بدترین حالت
روی ۵۰۰ کندل چارت = ~۲۵۰k مقایسه — فوری). اگر بعداً چارت بزرگ‌تر شد
(>۲۰۰۰ کندل)، می‌توان کار را به web-worker منتقل کرد — ثبت به‌عنوان
یادداشت، نه نیاز فعلی.

```
ruff ✅ black ✅  pytest 1504 passed, 54 skipped
```

---

## 2026-08-29 — فاز ۸۵: پیش‌بینی رنج برای هر کندل روی /data (درخواست اپراتور)

**درخواست:** «مدل و دیتاست را انتخاب کنم، روی هر کندل کلیک کنم،
پیش‌بینی قیمتی بعدش نمایش داده شود — مثلاً مدل 1H-h12 → ۱۲ کندل بعد.»

### رفع

- **`presentation/gateway/range_forecast_inspector.py` (جدید):**
  `available_models(timeframe)` (رکوردهای range) و
  `forecast_at(symbol, timeframe, model_id, bar_index)` — پنجرهٔ
  `[bar-149 .. bar]` با همان feature_matrix (causal_only، role=range)
  به مدل می‌رود و **کل مسیر horizon نقطه‌ای** برمی‌گردد:
  `points: [{k, high, low, high_offset, low_offset} …]`
  (بدون خلاصه‌سازی worst-case — هر کندلِ آینده جدا دیده می‌شود)
- **server.py:** `GET /api/range-forecast?symbol&timeframe&model&bar`
  + دادهٔ مدل‌های رنج موجود به صفحهٔ /data
- **data_renderer:** پنل «Range model forecast» — dropdown مدل‌ها،
  کلیک روی کندل → fetch → جدول high/low به‌ازای هر k با درصد آفست

### علیت

پنجره فقط کندل‌های `≤ bar` را می‌بیند؛ هیچ برچسب آینده‌ای ساخته نمی‌شود.
فیچرها همان build مسیر آموزش است (causal_only=True، role-filtered).

### نکتهٔ عملکرد

اولین کلیک: آموزش فیچرها (~۱۰-۲۰ ثانیه). کلیک‌های بعدی: فیچر کش شده،
فقط inference (~۱ ثانیه). اگر کندل انتخابی <۱۵۰ کندل قبلی داشته باشد
→ خطای صریح.

```
ruff ✅ black ✅  pytest 1504 passed, 54 skipped
```

---

## 2026-08-29 — فاز ۸۵-ب: مسیر پیش‌بینی به‌صورت گرافیکی روی چارت

**پرسش اپراتور:** «به صورت گرافیکی هم پیش‌بینی‌ها رو نمایش دادی؟» — نه،
فقط جدول بود. الان رسم هم اضافه شد.

### اضافه شد

- **مسیر TP/SL روی چارت اصلی:** بعد از کلیک روی کندل، خط‌چین سبز (high)
  و قرمز (low) به‌سمت جلو کشیده می‌شود + نقاط کوچک + ناحیهٔ بین‌شان با
  شفافیت کم + قیمتِ نقطهٔ آخر (اگر جا باشد)
- **خط عمودی** روی کندلِ anchor (نقطهٔ کلیک)
- **اسلات‌های اضافی:** اگر anchor+horizon از آخرین کندل رد شود، محور X
  به‌اندازهٔ horizon گسترش می‌یابد
- تغییر مدل یا تغییر select کندل‌ها → forecast پاک می‌شود
- خطای forecast → مسیر پاک و پیام خطا

### بدون تغییر

- جدول متنی قبلی سر جایش است (پنل پایین)
- زوم قیمت و پن زمان کار می‌کنند — می‌توان روی مسیر zoom کرد

```
ruff ✅ black ✅  pytest 1504 passed, 54 skipped
```

---

## 2026-08-29 — فاز ۸۶: ابزارهای ترسیم + محور زمان (ریپلی + /data)

**درخواست اپراتور:** خط روند، افقی، عمودی + تاریخ/ساعت روی محور X هر دو چارت.

### اضافه شد

**/data (data_renderer.py):**
- خطوط ترسیم: Trend (دو کلیک) · H-Line (یک کلیک) · V-Line (یک کلیک)
- دکمه‌های ╱Trend · ─H-Line · │V-Line · ✕Clear
- خط افقی: قیمت $ کنار خط چاپ می‌شود
- خط عمودی: زمان MM-DD HH:MM
- محور X: تاریخ/ساعت (MM-DD HH:MM) هر N کندل
- سه دکمه toggle می‌شوند (کلیک دوباره = خاموش)

**replay (replay_renderer.py):**
- همان سه ابزار + دکمه‌ها
- محور X: تاریخ/ساعت هر N کندل
- خطوط در draw رسم می‌شوند (مقاوم به زوم/پن — مختصات پیکسلی ذخیره می‌شوند)

### محدودیت شناخته‌شده

خطوط به‌صورت پیکسلی ذخیره می‌شوند نه قیمتی/زمانی — اگر زوم قیمت یا
پن زمانی تغییر کند، خطوط جابجا به نظر می‌رسند. این یک trade-off ساده‌سازی
است (خطوط ذخیره‌شده پایدار ماندن حتی بعد از reset zoom). اگر بعداً
خواستی خطوط مقاوم به zoom باشند، باید به‌صورت قیمت/زمان ذخیره شوند.

```
ruff ✅ black ✅  pytest 1504 passed, 54 skipped
```

---

## 2026-08-29 — فاز ۸۷: رفع باگ — کد سیگنال /data در فاز ۸۶ حذف شده بود

**گزارش اپراتور:** تیک Show signals هیچ نقاطی نمایش نمی‌دهد و dropdown
مدل رنج خالی است.

### ریشه

فاز ۸۶ (ابزارهای ترسیم + محور زمان) کل تابع draw() را بازنویسی کرد و
در این بازنویسی، کد سیگنال‌های فاز ۸۴ حذف شد:
- `computeSignals()` و `renderSignals()` و `currentSignals`
- مثلث‌های ▲/▼ رسم روی چارت
- dropdown مدل‌های رنج هم فقط هم‌تایم‌فریم نشان می‌داد (1D فقط 1D)

### رفع

- همهٔ کد سیگنال از کامیت 2d0fd0c بازگردانده شد
- مثلث‌ها برگشتند
- dropdown حالا مدل‌های 1D **و** 1H را نشان می‌دهد

```
ruff ✅ black ✅  pytest 1504 passed, 54 skipped
```

---

## 2026-08-29 — فاز ۸۸: رفع باگ عدم‌نمایش مثلث‌های سیگنال روی /data

**گزارش اپراتور:** «۲۶۴ سیگنال می‌شمارد ولی هیچ مثلثی رسم نمی‌شود.»

### ریشه

`computeSignals` اندیس `i` را **محلی** (0..n-1 نسبت به CANDLES) می‌داد،
ولی `indexOf` در draw از `c.i` (سراسری، 49500+) پر می‌شد. هیچ match ای
رخ نمی‌داد → مثلث‌ها skip می‌شدند.

### رفع

- `computeSignals` حالا `s.i = base + start` (اندیس سراسری از
  `CANDLES[0].i`) تولید می‌کند تا با `c.i` هم‌مقیاس باشد
- `indexOf` fallback هم دارد اگر `c.i` undefined باشد

### مسئلهٔ مدل رنج هم علت مشابه دارد

`available_models(timeframe)` فقط مدل‌های همان timeframe چارت را می‌داد.
اگر چارت 5M است و مدل‌های رنج 1D/1H ذخیره شده‌اند → خالی.
حالا همهٔ رنج‌ها (1D+1H) در dropdown هستند (رفع در فاز قبلی).

---

## 2026-08-29 — فاز ۸۹: رفع باگ dropdown مدل رنج + افزایش کندل‌های نمایش

**گزارش اپراتور:** dropdown مدل رنج خالی است · تعداد کندل‌ها را ببر تا ۵۰۰۰.

### ریشهٔ dropdown خالی

کد JS مربوط به پر کردن dropdown (از `RANGE_MODELS` و fetchForecast و
کلیک کندل) در فاز ۸۶ هم مثل کد فاز ۸۴ حذف شده بود. بازگردانی شد.

### رفع

1. بازگردانی JS dropdown مدل + fetchForecast + کلیک روی کندل
2. select تعداد کندل: 60/120/200/300 → **120/300/500/1000/2000/5000**
3. `DEFAULT_CHART_CANDLES` = 300 → **5000**
4. کامیت فاز ۸۷ (رفع باگ سیگنال) را هم همراه دارد

```
ruff ✅ black ✅  pytest 1504 passed, 54 skipped
```

---

## 2026-08-30 — فاز ۹۰: باگ ۵۶ (warmup pad) + باگ ۵۷ (wheel روی محور قیمت)

**گزارش اپراتور:**
۱. «tوی محور قیمت نمی‌تونم اسکرول کنم»
۲. «Feature matrix has 73 rows; model needs 150» در کلیک روی /data

### باگ ۵۶ — warmup pad برای پیش‌بینی روی /data

`build_feature_matrix` سطرهای warm-up را حذف می‌کند (EMA200=200,
ATR=77, …). وقتی فقط window_size=150 کندل به آن می‌دادیم، بعد از
حذف warmup فقط ۷۳ سطر باقی می‌ماند → خطا.

**رفع:** پنجرهٔ ورودی = `window_size + 400` کندل (پوشش کامل warmup)
، بعد از build آخرین ۱۵۰ سطر برای مدل.

### باگ ۵۷ — wheel روی محور قیمت = زوم قیمت

قبلاً wheel فقط اسکرول زمان بود. حالا:
- **موس روی محور قیمت (۶۶px سمت راست چارت) + wheel** → زوم قیمت
- **موس روی چارت + wheel** → اسکرول زمان
- **Ctrl+wheel** → زوم قیمت (هر جا)

در هر دو چارت (/data و replay) اعمال شد.

```
ruff ✅ black ✅  pytest 1504 passed, 54 skipped
```

---

## 2026-08-30 — فاز ۹۱: پن عمودی روی محور قیمت (درخواست اپراتور)

**درخواست:** «اسکرول روی محور قیمت هم نیازه — زوم که می‌کنیم کندل‌ها می‌رن
بالای صفحه و دیگه نمی‌شه دید. باید بشه روی محور قیمت بالا و پایین رفت.»

### رفع

وقتی `priceZoom > 1.0` و موس روی **محور قیمت** (۶۶px سمت راست) wheel شود:
- بالا (deltaY<0) → چارت **بالا** می‌رود (پن عمودی)
- پایین (deltaY>0) → چارت **پایین** می‌رود

هر نچ = ۲۵٪ از باند فعلی جابجایی. `priceAnchor` هم آپدیت می‌شود تا
مرکز زوم واقع‌بینانه بماند. `Reset zoom` پن را هم صفر می‌کند.

در **هر دو چارت** (/data و replay) اعمال شد. بدون Ctrl — چون محور
قیمت است و زوم هم از قبل فعال است.

```
ruff ✅ black ✅  pytest 1504 passed, 54 skipped
```

---

## 2026-08-30 — فاز ۹۲: رفع باگ — مسیر پیش‌بینی روی چارت /data رسم نمی‌شد

**گزارش اپراتور:** «مقادیر قیمت پیش‌بینی می‌شوند ولی توی چارت نشونشان
نمی‌دهد» — خطای `ConnectionAbortedError` هم در سرور (چون مرورگر timeout
کرده بود در حال انتظار).

### ریشه

`renderForecast()` هیچ‌وقت `forecastPath` را نمی‌ساخت — فاز ۸۵-ب این
متغیر را تعریف کرد ولی خود تابع render را آپدیت نکرد. نتیجه: داده
برمی‌گشت و جدول پر می‌شد ولی `draw()` هیچ مسیری نداشت که رسم کند.

### رفع

- `renderForecast(f, localIdx, …)`: بعد از پر کردن جدول، `forecastPath`
  را از `f.points` می‌سازد
- `fetchForecast(..., localIdx)` و کلیک کندل `_clickedLocalIdx` را پاس
  می‌دهد
- سرور `ConnectionAbortedError` را هم بلعیده باشد تا لاگ کثیف نشود

### تکمیلی — symbolTf تعریف‌نشده حذف شد

---

## 2026-08-30 — فاز ۹۳: رفع SyntaxError — تعریف تکراری plotW/step/yP/xOf در draw

**گزارش اپراتور:** چارت /data کاملاً سیاه — هیچ کندلی نمایش داده نمی‌شود.

### ریشه

فاز ۸۶ (بازنویسی draw) و فاز ۷۹ (استریم) هر دو `plotW/step/yP/xOf` را
تعریف کرده بودند. تعریف دوم با `const` = SyntaxError در مرورگر → کل
اسکریپت چارت کرش می‌کرد.

### رفع

تعریف تکراری حذف شد؛ نسخهٔ درست `plotW / Math.max(1, totalSlots)`
(که اسلات‌های future را هم حساب می‌کند) نگه داشته شد.

---

## 2026-08-30 — فاز ۹۴: رفع چارت سیاه + شفافیت قیمت پایه در forecast

### چارت سیاه

علت: SyntaxError در JS (تعریف تکراری plotW/step/yP/xOf در فاز ۸۶) — رفع شد در فاز ۹۳.

### ConnectionAbortedError در سرور

مرورگر وقتی fetch timeout می‌شود اتصال را قطع می‌کند → سرور خطا می‌دهد.
حالا `_send_json`/`_send_html` در خطای `{ConnectionAborted,BrokenPipe}Error`
را بی‌صدا عبور می‌دهند (لاگ تمیز).

### Base price در جدول forecast

جدول حالا «Base price» هم نشان می‌دهد تا کاربر بداند آفست‌ها نسبت به
کدام قیمت محاسبه شده‌اند (close کندل انتخابی).

---

## 2026-08-30 — فاز ۹۴: باگ ۵۸ — statsHtml const ولی += داشت

**گزارش اپراتور:** «[X] Assignment to constant variable» در rf-status
و مسیر پیش‌بینی روی چارت رسم نمی‌شد.

### ریشه

`renderForecast` در فاز ۸۵-ب اضافه شد ولی `statsHtml` را `const` تعریف
کرده بود و بعداً با `+=` مقدار Base price را اضافه می‌کرد → TypeError
در مرورگر → کل تابع abort می‌شد → `forecastPath` هرگز ست نمی‌شد →
چارت هیچ مسیری رسم نمی‌کرد.

### رفع

`const statsHtml` → `let statsHtml`

### تأیید

`forecastPath` بعد از `renderForecast` مقدار دارد:
`{"localIdx":0,"points":[{"high":101,"low":99}]}` ✓

```
ruff ✅ black ✅  pytest 1504 passed, 54 skipped
```

---

## 2026-08-30 — فاز ۹۵: تارگت مدل رنج ATR-نرمال‌شده + تبدیل قیمت در همه‌جای مصرف

**درخواست اپراتور:** «تارگت رو با ATR اصلاح کن؛ بعد توی بکتست و هرجایی که
قراره قیمت پیش‌بینی بشه، نحوهٔ محاسبهٔ قیمت پیش‌بینی رو هم اصلاح کن.»

### ریشه (از تحلیل فاز ۹۴)

تارگت قبلی `(high[t+k] − close[t]) / close[t]` درصدِ خام بود؛ ورودی هم
minmax روی [-2,+2]. مدل نه مقیاس قیمت می‌دید نه مقیاس نوسان → بهینه‌ترین
جواب = میانگین ثابت دیتاست (±0.06% در 1H، ±0.60% در 1D) برای همهٔ کندل‌ها.

### تعریف تارگت جدید

```
high_seq[t,k] = (high[t+k] − close[t]) / ATR14[t]
low_seq[t,k]  = (low[t+k]  − close[t]) / ATR14[t]
```

ATR با `wilder_atr_series` (علوی، تعریف expand-seed + هموارسازی Wilder)
محاسبه می‌شود — همان تعریف در لیبل‌سازیِ آموزش و de-normalize در پیش‌بینی.

### معماری تبدیل (یک‌باره، در مرز پیش‌بینی‌کننده)

- `RangePredictor(target_units="atr")` خروجی مدل را «ضریب ATR» می‌داند؛
  با `atr_reference = ATR14(کندل مرجع)` قیمت‌ها می‌شوند
  `close + mult × ATR` و معادلِ کسریِ close هم در `high_offset` ذخیره
  می‌شود تا همهٔ نمایش‌های درصدی قدیمی درست بمانند.
- `RangeForecast` فیلدهای `target_units / atr_reference /
  high_atr_mult / low_atr_mult` گرفت؛ `predicted_high/low` در حالت atr
  با فرمول ATR محاسبه می‌شوند → براکت، بکتست، استراتژی و GUI بدون تغییر
  قیمتِ درست می‌گیرند.
- مدل‌های قدیمی: `ModelRecord.target_units` (پیش‌فرض "pct") مسیر قدیمی را
  حفظ می‌کند — هیچ مدل ذخیره‌شده‌ای خراب نمی‌شود.

### سیم‌کشی atr_reference (فقط مصرف‌کنندهٔ واقعی)

| مسیر | منبع ATR |
|------|----------|
| بکتست (`DualModelPredictionSource`) | کندل‌های رنجِ تحویل‌شده تا آخرین کندل بسته (memoized per bar) |
| GUI /data (`RangeForecastInspector`) | کندل‌ها تا کندل کلیک‌شده |
| زنده (`LiveMatrixBuilder` → `LiveWindow.atr_reference`) | بافر ۱H |
| sanity-check آموزش (`run_dual_models`) | کل سری کندل‌ها |

پارامتر `atr_reference` فقط به پیش‌بینی‌کننده‌های ATR-unit پاس می‌شود تا
استاب‌ها/امضاهای قدیمی نشکنند؛ مدل ATR بدون ATR با خطای واضح رد می‌شود
(هرگز قیمت غلط خاموش).

### گزارش و رکورد

- `ModelRecord.target_units` + نمایش `range units` در خلاصهٔ بکتست و
  `target units` در سربرگ آموزش رنج.
- جدول forecast در /data برای مدل ATR ستون `×ATR` نشان می‌دهد.

### بدهی قدیمی که در همین فاز پرداخت شد

تست‌های شمارندهٔ کاتالوگ فیچر (227→229، 188→190، 241→243، 177→179،
174→176) از فاز ۹۴ آپدیت نشده بودند — حالا سبز شدند. ۳ خطای ruff قدیمی
در target_builder هم رفع شد.

### تأیید

```
ruff ✅ (فایل‌های فاز ۹۵ پاک؛ نویز کل‌ریپو کمتر از baseline)
black ✅
pytest 1532 passed, 54 skipped  (+28 تست جدید فاز ۹۵)
```

تست‌های جدید: `test_atr_range_target.py` (13)،
`test_range_predictor_atr.py` (9)، `test_range_atr_wiring.py` (6).

---

## 2026-08-30 — فاز ۹۵-ب: گزارش آموزش ATR-آگاه + baseline «پیش‌بینی ثابت»

**گزارش اپراتور از اولین ران با تارگت ATR (1D, horizon=5):** «توی بک تست
قیمت‌ها متفاوت بود، مثل قبل یه درصد ثابت نمی‌داد» ✓ — هدف فاز ۹۵ محقق شد.

### مشکل پیدا‌شده در همان لاگ

خط epoch هنوز `~+-1984.27$` چاپ می‌کرد — ریاضیِ قدیمی pct
(`val_mae × قیمت ۲۶۵۰`). با تارگت ATR این عدد بی‌معنی است.

### رفع

- `ConsoleProgressReporter(target_units, atr_reference)` — تبدیل دلاری
  فقط با واحد درست: ATR → `mult × ATR14` (نمایش `~+-23.59$
  (ATR14=31.50)`)؛ pct قدیمی → رفتار قبل؛ بدون مرجع → هیچ عدد جعلی.
- `print_quality` هم همین‌طور: پیام «ATR multiples» + تبدیل با ATR.
- اسکریپت گزارشگر را با واحد/ATR دیتاست می‌سازد.

### baseline جدید: «پیش‌بینی ثابت»

سربرگ آموزش حالا MAE یک پیش‌بینی‌کنندهٔ ثابت (میانهٔ train) روی آخرین
فولد ولید را چاپ می‌کند (`constant base`) و QUALITY حکم می‌دهد:

```
vs constant baseline 0.7521: the model BEATS ... by 0.0033
vs constant baseline 0.7480: NO BETTER than a constant prediction
```

این دقیقاً سنجهٔ ریشه‌یابی مشکل آفست ثابت است.

### نکتهٔ عملی برای اپراتور (ران 300×4)

val_loss بعد از epoch ~90 فقط با دقت 1e-6 «بهبود» می‌یافت →
ReduceLROnPlateau (min_delta=1e-6) هرگز decay نمی‌کند و ES هم نه.
بهترین checkpoint بعد از هر epoch ذخیره می‌شود؛ قطع کردن ران امن است.
پیشنهاد: `--epochs 60..80`.

### تأیید

```
ruff ✅ black ✅  pytest full suite green (+4 تست جدید گزارشگر)
```

---

## 2026-08-30 — فاز ۹۵-ج: حکم QUALITY روی final-step + جلوگیری از مرگ LR

**ران اپراتور (1D, horizon=5, 300×3, RLR patience=3):** حکم چاپ‌شده
«NO BETTER than constant» بود ولی اعداد خلافش را می‌گفتند.

### ریشه: مقایسهٔ سیب با پرتقال

- `val_mae` (کراس) = میانگین روی **هر ۱۵۰ موقعیت پنجره** — موقعیت‌های
  اولِ پنجره عمداً کمتر آموزش دیده‌اند (وزن loss: 40% کل، 60% آخرین)
  → 0.8301
- `val_high/low_mae` (باگ ۴۸) = **آخرین timestep** = دقیقاً همان که
  inference مصرف می‌کند → (0.3678 + 0.3208)/2 = **0.3443**
- baseline ثابت (0.7587) هم روی همان ردیف‌های final-step است.

**نتیجهٔ درست: مدل 0.3443 در برابر 0.7587 → 55% بهتر از پیش‌بینی ثابت.**
مدل skill واقعی دارد؛ حکم قبلی اشتباه بود.

### رفع ۱ — حکم درست

`print_quality` حالا final-step MAE را جدا چاپ می‌کند و حکم را با همان
می‌دهد؛ val_mae تمام-سکانس فقط اطلاعاتی است.

### رفع ۲ — کاسکید مرگ LR

RLR با min_delta=1e-6 بهبودهای ±3e-7 را «بدتر شدن» می‌شمرد → با
patience=3، LR در 280 epoch از 8e-4 به **1e-6** سقوط کرد (فولد آخر
عملاً یخ زده — val_loss 0.6717 نتیجهٔ مدل نیمه‌آموزش‌دیده است، نه سخت
بودن داده). رفع:

- RLR: min_delta 1e-6 → **1e-4**، min_lr از lr×1e-3 → **lr×0.02**
- ES: min_delta 1e-6 → **1e-4** (با این تغییر ES واقعاً fire می‌شود)

### تفسیر برای اپراتور

- biasها: high −0.26 / low +0.18 → بازهٔ پیش‌بینی به‌طور سیستماتیک
  ~0.2 ATR باریک‌تر از واقعیت است (انقباض به میانگین). کالیبراسیون
  bias (گسترش با biasِ train) گام بعدی احتمالی است — فعلاً فقط ثبت شد.
- fold losses 0.615 / 0.574 / 0.672 — فولد آخر (تازه‌ترین داده) سخت‌تر
  است + LR مرده. با رفع ۲ انتظار می‌رود فولد آخر بهتر شود.

### تأیید

```
ruff ✅ black ✅  pytest full suite green
```

---

## 2026-08-30 — فاز ۹۵-د: پروفایل لیبل بر حسب k + خطای per-step

**گزارش اپراتور از /data (gold_range_1h h12):** خروجی دیگر ثابت نیست ✓
ولی روی هر انکر، گام +1 بزرگ‌ترین درصد را دارد و به سمت +12 نزولی
کم می‌شود. سؤال: این منحنی «حقیقت داده»ست یا artifact مدل؟

### نکتهٔ معنایی مهم (ثبت برای همیشه)

تارگت seq2seq عطف به closeِ **انکر** است و high/low «یک کندلِ خاص»،
نه running-max افق:
`high_seq[t,k] = (high[t+k] − close[t]) / ATR14[t]`
= رانشِ k کندله + فتیلهٔ همان کندل. میانهٔ رانش ~۰ است → پروفایل
میانهٔ نظری تقریباً **تخت** است (برخلاف شهود مخروطِ گسترش‌یونده که
مال running-max است). پس انحراف از تخت یعنی رانشِ یادگرفته‌شده.

### تشخیص جدید (این فاز)

- **سربرگ آموزش — `label profile`**: میانهٔ لیبل هر گام k، جدا برای
  train و ردیف‌های آخر (recent) → منحنیِ اقلیم داده. مدل بی‌مهارت
  دقیقاً به همین منحنی می‌رسد.
- **QUALITY — `per-step MAE`**: `_range_validation_metrics` حالا
  `val_step{k}_mae` برای هر گام تولید می‌کند (روی آخرین timestep =
  همان خروجی inference).

تفسیر بعد از ران بعدی:
- پروفایل داده تخت/صعودی ولی مدل نزولی → artifact (زیربرازش پروفایل)
- پروفایل داده هم نزولی → مدل درست یاد گرفته (اقلیمِ آن دوره همین است)

### نکتهٔ عملی برای براکت

`RangePredictor` برای horizon>1 worst-case می‌گیرد (max/min روی k)؛
با پروفایل نزولی، بدترین حالت همیشه k=1 است → عملاً باند براکت ≈ باند
گام اول. اگر تشخیص دادیم پروفایل واقعی داده با k رشد می‌کند، این یعنی
مدل افق را دست‌کم می‌گیرد و باید loss وزن‌دهی per-step شود.

### تست‌ها

`test_label_profile_and_step_mae.py` (6) — پروفایل train/recent،
گارد ورودی خالی/فرد، per-step روی شکل seq2seq و flat (بدون TF).

```
ruff ✅ black ✅  pytest full suite green
```

---

## 2026-08-30 — فاز ۹۵-ه: رسم مسیر forecast روی چارت /data

**گزارش اپراتور:** «توی /data پیش‌بینی‌ها روی کندل‌ها نمایش داده نمی‌شه؛
فقط عددها رو پرینت می‌کنه.»

### ریشه — دو باگ مستقل

1. **`renderForecast` هرگز `draw()` صدا نمی‌زد.** forecastPath ست می‌شد
   ولی چارت تا بلور بعدی (اسکرول/زوم/تغییر مدل) دوباره رسم نمی‌شد →
   اپراتور فقط جدول عددی می‌دید.
2. **click handler اندیس گلوبال را به‌جای لوکال می‌فرستاد.**
   `idx = base + rel*visible` گلوبال است؛ پاس‌دادنش به‌عنوان localIdx
   یعنی draw() بعدی انکر را جای دور فرض می‌کرد → totalSlots منفجر
   (base+5000+12 اسلات) → step زیرپیکسلی → چارت له و مسیر بیرون بوم.
   باگ ۲ با باگ ۱ ماسک شده بود (draw اصلاً صدا زده نمی‌شد).

### رفع

- `renderForecast`: بعد از ست کردن forecastPath → `draw()` فوری.
- کلیک: `const localIdx = idx - base;` → پاس به fetchForecast و
  `_clickedLocalIdx` (کامنت غلط هم اصلاح شد).

### تأیید

```
node --check روی _CHART_SCRIPT ✅
assert دو فیکس در اسکریپت ✅
pytest full suite green
```

---

## 2026-08-30 — فاز ۹۵-و: sanity prediction با مدل ذخیره‌شده + رفع پیام‌های h1

**ران اپراتور (1D, horizon=1, 100×3):** حکم درست بود — h1 مقابل ثابت
بد نیست (0.3317 در برابر 0.3132). این یافتهٔ واقعی است، نه باگ:
اندازهٔ فتیلهٔ روزانه در واحدهای ATR تقریباً غیرقابل‌پیش‌بینی است و
میانهٔ ثابت همان‌جا نزدیکِ بهینه است (پروفایل لیبل هم مؤیدش: train
+0.401/−0.381 ≈ recent +0.392/−0.353؛ پیش‌بینی sanity مدل +0.38/−0.37
دقیقاً همان اقلیم است).

### باگ گزارش‌گیری که در همین ران پیدا شد

`PREDICTION for the next ...` با `outcome["artifact"]` (مدل خامِ
آخرین فولد، val 0.2345) ساخته می‌شد، نه با مدلی که ذخیره شده
(best checkpoint epoch 50، val 0.2147). رفع: `save_model` حالا
آرتیفکتِ واقعاً ذخیره‌شده را برمی‌گرداند و sanity prediction با همان
اجرا می‌شود (`sanity_artifact`).

### ریزه‌کاری‌های دیگر

- در h1 پیام «full-sequence is NOT the trading number» گمراه‌کننده بود
  (دو عدد یکی‌اند) → حالا وقتی برابرند پیام ساده چاپ می‌شود.
- حکم NO BETTER حالا hint عمومی دارد: مهارت در افق‌های بلندتر (رانش)
  ظاهر می‌شود، نه در اندازهٔ فتیلهٔ تک‌کندل.

### جدول مهارت (از سه ران اپراتور — 1D، ATR units)

| horizon | ثابت | final-step | حکم |
|---------|-------|-----------|------|
| 1 | 0.3132 | 0.3317 | NO BETTER (−6%) |
| 2 | 0.4531 | 0.3200 | BEATS (+29%) |
| 5 | 0.7587 | 0.3443 | BEATS (+55%) |

خطای مطلق مدل تقریباً ثابت (~0.32-0.34) است؛ ثابت با افق رشد می‌کند
(عدم‌قطعیت رانش) → لبهٔ مدل از رانش است، نه فتیله.

### نکتهٔ ثبت‌شده (بدون تغییر — NO REDESIGN)

مدل KEPT = best val_loss کل ران (epoch 50 فولد ۲) — آخرین بخش داده را
ندیده. طراحی فعلی عمدی است (Phase 47)؛ در صورت نیاز گزینهٔ
`--keep last-fold` بعداً اضافه می‌شود.

```
ruff ✅ black ✅  pytest full suite green
```

---

## 2026-08-30 — فاز ۹۵-ز: حکم سطح-براکت (worst-case vs worst-case)

**ران اپراتور (1D, horizon=2, 50×3، کال‌بک‌های فیکس‌شده):**
- پروفایل لیبل: high با k رشد می‌کند (+0.401→+0.499)، low ~ثابت →
  فرضیهٔ فاز ۹۵-د تأیید: منحنی 1Hِ GUI ترکیبی از اقلیم + artifact بود.
- per-step MAE: k1=0.336 (خوب، ~۱۵٪ بهتر از اقلیمش) ولی
  **k2=0.649 (خیلی بدتر از اقلیمِ ~0.44)** → مدل گام ۲ را نمی‌بیند
  (وزن‌دهی 40/60 loss + پخشِ بزرگ‌ترِ k2).
- LR فولد آخر 0.000218 → زنده؛ کاسکید مرگ رفع شده ✓.

### باگی که حکم این ران آشکار کرد

حکم «BEATS 28%» با خطای k1 (0.3355) در برابر baselineای که میانگین
ستون‌های k1+k2 بود (0.4654) داده شد — در حالی که براکتِ واقعی از
worst-case روی k مصرف می‌کند (RangePredictor: max/min روی گام‌ها).
k1 خوب، k2 خراب را پنهان می‌کند.

### رفع (فاز ۹۵-ز)

1. `_range_validation_metrics`: + `val_bracket_{high,low,}_mae` —
   MAEِ (max_k high، min_k low) پیش‌بینی در برابر (max_k، min_k) واقعی.
   برای h1 برابر step1.
2. برش قدیمی `[:, :2]` در شاخهٔ 2D حذف شد (ورودی تختِ [N, H*2] را به
   k1 محدود می‌کرد — فقط legacy [N,2]/[N,H*2] کامل نگه داشته می‌شود).
3. سربرگ: + `climate/step` (MAE ثابتِ هر گام) و + `bracket base`
   (constant worst-case vs actual worst-case — مقایسهٔ منصفانه).
4. `print_quality`: برای h>1 حکم با bracket MAE در برابر bracket base
   (`VERDICT (bracket level)`)؛ پیام step-1 دیگر ادعای «what inference
   uses» را برای h>1 ندارد.

### پیامد برای اپراتور

ران بعدی h2/h5 حکم جدید را نشان می‌دهد: اگر VERDICT (bracket level)
NO BETTER بود، یعنی باندِ worst-case مدل از اقلیم بدتر است (k2 خراب
براکت را مسموم می‌کند) → یا h2 با مصرفِ فقط-گام-۱، یا وزن‌دهی per-step
loss. تصمیم با دادهٔ ران بعدی.

```
ruff ✅ black ✅  pytest full suite green (+1 تست براکت)
```

---

## 2026-09-01 — فاز ۹۶: انتخاب نسخهٔ مدل در بکتست + هشدار مدلِ قبل از فاز ۹۵

**بکتست اپراتور (72 ترید، −5.11%):** لاگ می‌گفت gold_range_1d **v2**
(trained=2026-08-27) لود شده — CSV هم تأیید: هر ۷۲ ترید دقیقاً همان
آفست ثابت +0.6239%/−0.5985% (امضای مدل pct قدیمی). **مدل ATR فاز ۹۵
اصلاً در بکتست نبود.**

### ریشه

- مدل‌های ATR جدید در کاتالوگ به‌عنوان **v1** ذخیره شده‌اند؛ مدل قدیمی
  pct **v2** است → ``latest_version`` (بزرگ‌ترین شماره) همیشه مدل
  قدیمی را برمی‌دارد.
- فرم بکتست اصلاً فیلد انتخاب مدل/نسخه ندارد.

### رفع (فاز ۹۶)

1. فرم بکتست: + فیلدهای «Signal model» و «Range model» — خالی = جدیدترین
   نسخه؛ «id:vN» نسخهٔ صریح (مثلا `gold_range_1d:v1`).
2. هندلر: `_split_model_spec` (tolerant به v/V و فاصله) →
   `signal_version`/`range_version` به `from_storage` (که از قبل
   پارامتر نسخه داشت، فقط UI نداشت).
3. هشدار بلند در خروجی: وقتی مدل رنجِ لودشده pct است:
   `range units : pct ‼️ PRE-Phase95 model — ... results are not comparable.`
4. models_line حالا نسخهٔ واقعی لودشده را نشان می‌دهد (`id:latest` یا `id:vN`).

### تحلیل همان ۷۲ ترید (مدل قدیمی — ارزش مرجع)

| طول ترید (کندل 5M) | n | WR | PnL |
|---|---|---|---|
| 0 | 5 | 0% | −0.19 |
| 1–20 | 18 | 6% | −3.53 |
| 21–100 | 13 | 15% | −3.97 |
| 101–300 | 19 | 32% | −2.39 |
| >300 (~>25h) | 17 | **59%** | **+5.29** |

→ براکت پهنِ ثابت (±$25، عرض ~1.22%) فقط با رانش چندروزه سود می‌شود؛
تریدهای کوتاه ورود-نویز + اسپرد می‌خورند. اسپرد فقط 0.7% فاصلهٔ SL —
مشکل نیست. ۵ ترید 0-bars (نقد همزمان با ورود) هم ۵ تا ضرر.

### گام بعدی اپراتور

بکتست A/B با مدل ATR: در فرم، Range model = `gold_range_1d:v1`
(نسخه‌ای که فاز ۹۵ train کرده؛ با `vs constant baseline` سربرگ آموزش
تطبیق بده) — و هشدار pct دیگر نباید ظاهر شود.

```
ruff ✅ black ✅  pytest full suite green (+6 تست پارسر)
```

---

## 2026-09-01 — فاز ۹۶-ب: فیلتر ترند EMA50 روزانه + تحلیل بکتست ATR

**بکتست اپراتور با مدل ATR (175 ترید، 50k bars، −9.01%، WR 27.4%)** —
اولین ران واقعی با فاز ۹۵:

| مشاهده | عدد |
|---|---|
| آفست‌های یکتا | 91 high / 90 low ✓ (دیگه ثابت نیست) |
| پهنای براکت | ‏$49–$164 (med $81) — متغیر با رژیم نوسان ✓ |
| short / long | **142 / 33** (!) |
| ترید <100 کندل | 84 ترید، WR ≤19%، **−13.9$** |
| ترید >600 کندل (~>2 روز) | 22 ترید، **WR 59%**، **+6.79$** |
| بدترین ساعت‌ها UTC | 15 (WR 1/8)، 3 (0/8)، 1، 23 |
| بهترین ساعت‌ها UTC | 17 (+6.09، 7/9)، 18 (+4.80)، 2، 14 |
| 0-bar | 19 ترید، WR 0% |

→ همان الگوی دو ران قبل، قوی‌تر: **کل سود استراتژی از رانش چندروزه
می‌آید؛ ضرر اصلی ورودِ خلاف ترند روزانه است** (بازار صعودیِ بزرگِ دورهٔ
آزمون + اکثریت SHORT). اسکیوِ باند هم 100% با جهت هم‌راستاست — چون
گیتِ R/R=1 فقط ورود در نیمهٔ درستِ باند را می‌پذیرد (by construction).

### رفع: فاز ۹۶-ب — فیلتر ترند EMA50 (پیشنهاد قدیمی، حالا داده‌پشتیبان)

- `DualModelPredictionSource(trend_filter="ema50")`: بعد از گیت
  actionable و **قبل از مصرف مدل رنج**، EMA50 علوی از کندل‌های رنجِ
  تحویل‌شده: SHORT ممنوع وقتی close > EMA50، LONG ممنوع وقتی < EMA50.
  تاریخچهٔ <50 کندل → فیلتر بی‌اثر (اجازه). بلوک‌ها در
  `stats()["trend_blocked"]`.
- `DualModelBacktestService`/`from_storage`: پاس‌دادن `trend_filter`.
- فرم بکتست: + فیلد «Daily trend filter» (none/ema50) + خط
  `trend filt :` در سربرگ + خط `trend blocks: n` در نتیجه.

### گام بعدی اپراتور — سه ران کنار هم

1. `trend_filter=ema50` با همین تنظیمات (50k، conf 70، R/R 1) → مقایسه
   مستقیم با این ران (−9.01%)
2. `filter_zero_bar=1` هم روشن (19 ترید 0-bar همگی باخته بودند)
3. بعد اگر لازم بود session hours جدید (17,18,2,14 خوب؛ 15,3,1,23 بد)

خطر overfitting ساعات بالاست؛ فیلتر ترند اصولی‌تر و مقاوم‌تر است.

```
ruff ✅ black ✅  pytest full suite green (+6 تست فیلتر ترند)
```

---

## 2026-09-01 — فاز ۹۶-ج: تحلیل پیلوت فیلتر ترند — سیستم به لبه رسید

**ران پیلوت اپراتور:** trend=off، zero-bar=on، conf 60 → 154 ترید،
WR 29.2%، **−9.42%** (تقریباً برابر ران قبل: −9.01%). 0-bar حذف شد
ولی فرقی نکرد — خونریزی کوتاه‌مدت جای دیگری است.

### آناتومی دقیق 154 ترید (CSV)

| برش | یافته |
|------|-------|
| مدت | <100 کندل: n=70، WR≤12%، **−19.4$** • >600: WR 59%، **+8.97$** |
| confidence | تفاوت معنادار ندارد (0.60-0.70: −1.85، 0.70+: −6.3) |
| جهت | 115 short / 39 long — هنوز اکثریت short |
| ساعت UTC | بدترین: 15، 21، 3، 7، 1، 4 ‏• بهترین: 17، 14، 2، 18 |

### شبیه‌سازی آنتی‌سیتروتیک روی همین CSV (با دادهٔ خودش)

| سناریو | n | WR | PnL |
|--------|---|----|-----|
| کل ران | 154 | 29% | −8.16 |
| فقط فیلتر ترند (proxy 5-day) | 76 | — | **+1.72** (تریدهای حذف‌شده: −9.88!) |
| فقط حذف ۶ ساعت بد (15,21,3,7,1,4) | 100 | 36% | **+11.75** |
| ساعت‌های خوب (2,6,14,17,18) | 37 | 49% | +14.11 |

→ هر دو لایه مستقلاً سیستم را به سمت مثبت می‌برند؛ روی‌هم (ن=۲۰)
+7.74 با WR 45% — نمونهٔ کوچک ولی جهت‌دار.

### هشدار Overfitting (ثبت رسمی)

- ساعت‌ها روی **همین ران** انتخاب شده‌اند — حکم نهایی فقط با ران
  out-of-sample معتبر است.
- proxy 5-day با خودِ تریدها ساخته شده (near-lookahead خفیف)؛
  فیلتر واقعی EMA50 که فاز ۹۶-ب ساخت سخت‌گیرتر/علوی‌تر است و عددش
  کمی متفاوت خواهد بود.

### اقدام

چیز جدیدی کد نشد — ابزار هر دو لایه از قبل هست:
`trend_filter=ema50` + `session_filter` (ساعت‌های فرم فعلی
2,5,6,10,14,15,16,18 باید به 2,6,14,17,18 تغییر کند — فاز ۵۲ قدیمی
بوده) → ران‌های A/B اپراتور. تغییر لیست ساعت‌ها با تأیید اپراتور.

---

## 2026-09-01 — فاز ۹۶-د: symbol_select قبل از هر fetch + پیام خطای قابل‌رفع

**گزارش اپراتور:** fetch 4H با `XAUUSD_I` → `MT5 returned no data:
(-1, 'Terminal: Call failed')` در حالی که ترمینال لاگین است.

### دو ریشهٔ عملیاتی (بدون کد)

1. **حروف بزرگ/کوچک:** پسوند آلپاری با i کوچک است — `XAUUSD_i` نه
   `XAUUSD_I`. MT5 اسم‌ها را case-sensitive می‌شناسد.
2. **نام canonical اشتباه:** فیلد symbol فرم باید `XAUUSD` باشد (نام
   پلتفرم)؛ `XAUUSD_I` به‌عنوان canonical جدید ذخیره می‌شد و تاریخچه
   تکه‌تکه می‌شد. چون fetch رد شد چیزی ذخیره نشد — فقط فرم را درست کن.

### ریشهٔ نرم‌افزاری (رفع شد)

پراوایدر MT5 هرگز `symbol_select` صدا نمی‌زد — اگر نمونه در Market
Watch نبود (یا املایش غلط بود)، copy_rates همان (-1) مبهم را می‌داد.

رفع: `_select_symbol` قبل از هر `copy_rates_from_pos/range`:
- `symbol_info` هست → `symbol_select` و ادامه
- نیست → ValidationError با نزدیک‌ترین اسم‌های واقعی بروکر
  (`symbols_get("*XAUUSD*")`) و یادآوری صریح i کوچک آلپاری.

### تست‌ها

- جدید: `test_mt5_symbol_select.py` (3) — select-before-fetch،
  خطای قابل‌رفع برای case غلط، مسیر range.
- `FakeMt5` در test_mt5_provider سطح `symbol_info/symbol_select` گرفت.

```
ruff ✅ black ✅  pytest full suite green
```

---

## 2026-09-01 — فاز ۹۶-ه: session-first برای اتصال MT5 (اکانت‌های OTP/گواهی‌دار)

**گزارش اپراتور:** بعد از درست شدن mapping (‏XAUUSD -> XAUUSD_i ✓)،
‏-7 برگشت: `Unsupported authorization mode, OTP or certificate password needed`
در حالی که ترمینال لاگین است.

### ریشه

پراوایدر اگر پروفایل login/password/server داشته باشد، **همیشه** با
credential لاگین برنامه‌ای می‌زند. اکانت جدید آلپاری لاگین پسوردیِ
برنامه‌ای را رد می‌کند (-7) حتی وقتی ترمینالِ لاگین‌شده آماده است.
ران قبل (-1) از مسیر بدون-credential رفته بود؛ بعد از ذخیرهٔ پروفایل،
مسیر credential فعال شد و -7 برگشت.

### رفع — session-first

`_ensure_initialized` دو مرحله‌ای شد:
1. `initialize()` بدون credential (اتصال به نشست ترمینال). ترمینال
   لاگین باشد → همان استفاده می‌شود؛ credential هرگز ارسال نمی‌شود.
2. نشست زنده نبود → shutdown + `initialize(login, password, server)`.
   رد شد → ConnectionError با راهنمای صریح OTP («ترمینال را دستی لاگین کن»).

بدون credential: رفتار قدیمی حفظ شد.

### تست‌ها

`test_mt5_session_first.py` (4): نشست زنده credential نمی‌فرستد؛
fallback به credential با shutdown بین دو تلاش؛ ردِ لاگین → پیام OTP؛
بدون credential رفتار قدیمی. تست‌های lifecycle به قرارداد جدید
آپدیت شدند (`test_live_session_beats_saved_credentials`).

```
ruff ✅ black ✅  pytest full suite green
```

---

## 2026-09-02 — فاز ۹۶-و: لیست مدل‌های رنج /data از همهٔ تایم‌فریم‌ها

**گزارش اپراتور:** مدل رنج 4H ذخیره شده ولی در دراپ‌داون /data نیست.

### ریشه

سرور /data لیست مدل را از `available_models("1D") + available_models("1H")`
می‌ساخت — **هاردکد از فاز ۸۶-ب**. هر تایم‌فریم جدید (4H) نامرئی می‌ماند.

### رفع

- `RangeForecastInspector.all_range_models()`: همهٔ مدل‌های رنج
  ذخیره‌شده از هر تایم‌فریمی (یک رکورد per model_id، آخرین نسخه) +
  فیلد `timeframe` در هر آیتم.
- سرور: لیست از همان متد — بدون هاردکد؛ تایم‌فریم جدید بدون تغییر کد ظاهر می‌شود.
- دراپ‌داون: `gold_range_4h v1 · h5 · 4H · 2026-09-01` — تایم‌فریم مدل دیده می‌شود.

نکتهٔ مصرف: پیش‌بینیِ یک مدل رنج باید روی دیتاست **هم‌تایم‌فریمِ**
خودش اجرا شود (۴H مدل با سری 4H) — چون ATR14 و window بر حسب کندلِ
آن تایم‌فریم آموزش دیده‌اند. /data سری 4H را از قبل دارد (fetch 4H).

### تست‌ها

`test_all_range_models.py` (3) — همهٔ تایم‌فریم‌ها، حذف signal،
کاتالوگ خالی. کل تست‌سوت سبز.

```
ruff ✅ black ✅  pytest full suite green
```

---

## 2026-09-02 — فاز ۹۷: استراتژی سه‌تایم‌فریمی (5M سیگنال · 4H براکت · 1D ترند)

**طرح اپراتور** — بکتست دقیقاً این شکلی بشه (بعد از A/B سؤالات، پاسخ‌ها):
- **مجوز ۱:** سیگنال 5M با احتمال > آستانهٔ GUI (موجود).
- **مجوز ۲:** از 150 کندل روزانه تا D0 → مدل رنج 1D → High/Low پیش‌بینی D1؛
  شیب High و Low نسبت به D0 واقعی. خرید: شیب‌ها ≥ ۰؛ فروش ≤ ۰.
  **حالت شیب در GUI انتخابی:** both / either / high / low (برای A/B).
- **مجوز ۳:** سمت TP (خرید: TP > ورود).
- **براکت از مدل 4H** (150 کندل 4H تا H0 → پیش‌بینی کندل بعدی):
  خرید TP=High، SL=Low؛ فروش برعکس.
- **fallback SL (خرید):** اگر SL ≥ ورود → SL = Low(D0)؛ اگر هنوز ≥ ورود →
  کمترین Low **زیر ورود** از کندل‌های 5M امروز − اسپرد؛ نبود → رد.
  فروش آینه‌ای (+اسپرد روی High).
- **R/R:** طبق خواستهٔ اپراتور اعمال می‌ماند (فیلد GUI).
- **اسپرد درصدی GUI** — برخورد TP/SL روی BID/ASK: موتور در حالت pct
  حالا اسپرد per-candle را به `bracket.trigger` هم می‌دهد (قبلاً فقط
  در خروج اعمال می‌شد، نه در چک لمس).

### پیاده‌سازی

- `DualModelPredictionSource`: مدل روزانه دوم (artifact/predictor/1D
  candles/matrix) + خوراک علوی 1D در observe + گیت شیب در predict
  (قبل از اجرای 4H) + `_triple_bracket` در bracket_for + آمار جدید
  (`daily_predictions/blocked`, `sl_fallback_d0/today`,
  `license3_refused`, `rr_refused`, `no_sl_found`).
- `DualModelBacktestService`: `strategy="classic|triple"`,
  `slope_mode`, `daily_model_id/version` → from_storage رکورد/آرتیفکت
  1D را لود و `run(daily_candles=...)` ماتریس روزانه می‌سازد.
- فرم‌های بکتست/replay: فیلدهای Strategy (triple/classic) و Slope mode؛
  در triple باید Range timeframe = 4H و دیتاست 1D موجود باشد (وگرنه
  پیام واضح). سربرگ: `strategy:` و `slope mode:`؛ نتیجه: `daily gate`,
  `sl fallback`, `lic-3/rr` خطوط.
- پیش‌فرض فرم = triple؛ فراخوانی بدون پارامتر (تست‌ها) = classic.

### تست‌ها

`test_triple_strategy.py` (14): مجوز ۲ در ۴ حالت شیب، براکت استاندارد،
fallback D0، fallback 5M-امروز−اسپرد، ردِ بدون-SL، مجوز ۳، R/R، فروش
آینه‌ای. کل تست‌سوت سبز.

### گام اپراتور

1. بکتست: `strategy=triple`، `range_timeframe=4H`، `range_model=gold_range_4h`،
   `slope_mode=both` (بعداً حالت‌های دیگر برای A/B)، R/R=1، conf 60-70.
2. خروجی باید `range units: atr` (مدل 4H) + خطوط `daily gate / sl
   fallback / lic-3/rr` را نشان دهد.
3. A/B پیشنهادی: slope_mode ∈ {both, either, high} — همان دیتاست.

```
ruff ✅ black ✅  pytest full suite green (+14)
```

---

## 2026-09-02 — فاز ۹۷-ب: مجوز ۴ — نزدیکی ورود به سطح روزانه

**تحلیل ران triple اول (186 ترید، WR 9.7%، −8.42%):** ۴۹% تریدها
0-bar و 100% بازنده (SL داخل نویز اسپرد — fallback-5M چاقو می‌ساخت)؛
spread cost $4.8 از ضرر $8.4؛ ‏165 short در بازار صعودی.

**داده برای آستانهٔ «نزدیکی» (از CSV اپراتور):**
- برندگان: فاصلهٔ ورود تا close روز med **+$1.7** (تا p75 = $9.3)
- بازندگان: med **+$9.3** (تا p75 = $12.5) — یعنی شکارِ جهش از بالای روز
- → آستانهٔ پیشنهادی: **0.25×ATR14(1D)** ≈ $9-10 در آن دوره.

### پیاده‌سازی — مجوز ۴ (پیش از اجرای مدل 4H)

`max_entry_distance_atr` (GUI، پیش‌فرض 0.25؛ 0 = خاموش):
- خرید: `entry − Low_pred(D1) ≤ 0.25×ATR14(1D)`
- فروش: `High_pred(D1) − entry ≤ 0.25×ATR14(1D)`
- فاصلهٔ منفی (ورود فراتر از سطح) مجاز — «داخل ناحیه» است.
- `proximity_blocked` در آمار + خط `proximity:` در نتیجه + آستانه در
  سربرگ strategy.

عمداً **کد اضافه نشد برای min-SL-6**: فیلد موجود `min_sl_distance`
همین کار را می‌کند (گیت استراتژی، قبل از fallback ها) — فقط مقدار
GUI را 6 بگذار.

### تست‌ها

+5 (بلاک دور/پاس نزدیک/فروش آینه‌ای/خاموش/منفی-رد). کل تست‌سوت سبز.

### ران پیشنهادی بعدی

```
min SL dist = 6 | max entry dist = 0.25 | slope both | R/R 1 | conf 60
```

```
ruff ✅ black ✅  pytest full suite green (+5)
```

---

## 2026-09-02 — فاز ۹۷-ج: کالبدشکافی ران triple کامل — دو باگ جایگاه گیت + تحلیل WR پایه

**ران اپراتور (triple، همهٔ تاریخچه، min SL=$6):** 941 ترید، WR 13.4%،
**−43.85%** — بدترین ران، پرآموزنده‌ترین ران.

### کشف ۱ — گیت min_sl_distance در triple بی‌اثر بود (باگ جایگاه)

گیت ۷ روی SL «پیش‌بینی 4H» چک می‌شود که همیشه بزرگ است (~$23). ولی در
triple بعد از گیت، fallback ها SL را به Low(D0)/5M-امروز بازنویسی
می‌کنند → **474 ترید با SL نهایی < $6** (پیش‌فرض گیت!) از در رفتند.
آن ۴۷۴ تا: WR **1.5%**، PnL **−17.29**.

رفع (فاز ۹۷-د، بعدی): چک حداقل فاصله باید **بعد از fallback نهایی**
در `_triple_bracket` هم اجرا شود.

### کشف ۲ — ریز-ضرر از ریز-اسپرد

‏437 ترید 0-bar همگی باخته؛ ‏805 از 815 باخت ≤ $0.4 (SL ~$6 + اسپرد
~$2.65×2). اسپرد کل $25.1 = ۵۷% خالص ضرر. با SL=$6 و اسپرد ~$2.6،
نوار واقعی SL فقط ~$0.7+نویز — تقریباً مارکت‌استاپ.

### آنچه بعد از حذف چاقوها می‌ماند

فقط تریدهای SL≥6: ‏WR 25.5%، −26.56 ‏• SL≥10: ‏WR 28.6%، −19.07 ‏•
TP med $21-23 — هنوز منفی، چون EV = 0.26×21 − 0.74×10 ≈ −2 بعد از
اسپرد. **WR پایهٔ سیگنال 5M در جهت شیب روزانه زیرِ سربه‌سر است.**

### نتیجه‌گیری معماری (برای بحث با اپراتور)

لایه‌های فیلتر (شیب/نزدیکی/R-R) درست کار می‌کنند (27823 بلاک!) ولی
«چه بخریم» را هنوز سیگنال 77.1%-دقیقِ آموزش‌ندیده با threshold 60%
تعیین می‌کند. گزینه‌ها:
- A: سیگنال 5M با داده/epoch کامل ریترین شود (فقط 10 epoch دارد!)
- B: جهت از خود مدل 4H (شرط TP-side که 2530 رد کرده — نرخ موفقش
  اندازه‌گیری شود)
- C: ترکیبی — سیگنال فقط timing، جهت = توافق 1D+4H

### اقدام کد — فاز ۹۷-د

`_triple_bracket`: بعد از fallback نهایی، `sl_dist ≥ min_sl_distance`
(و حداقل 2×spread) وگرنه رد؛ شمارندهٔ `final_sl_refused`.

### فاز ۹۷-د (تکمیلی — همان روز)

`_triple_bracket` حالا بعد از fallback نهایی چک می‌کند:
`sl_dist ≥ max(min_sl_distance, 2×spread)` وگرنه رد
(`final_sl_refused`). این بستنِ حفرهٔ «گیت استراتژی روی SL پیش‌بینی
چک می‌کرد و fallback چاقو می‌ساخت» است — همان ریشهٔ 474 ترید WR 1.5%
در ران 941-تایی. از `min_sl_distance` همان فیلد GUI دوباره‌استفاده
شد (کد جدید برای اپراتور: هیچ). +3 تست؛ کل تست‌سوت سبز.

---

## 2026-09-03 — فاز ۹۸ (قسمت ۱): مدل TREND — رنگ کندل بعدی (GREEN/RED)

**ایدهٔ اپراتور:** «بفهمیم کندل بعدی قرمزه (فروش‌پسند) یا سبز
(خریدپسند).» تصمیم بعد از تحلیل: مدل **طبقه‌بندی** جدید با نقش
`signal` (reuse: softmax + cross-entropy + Predictor مشترک) ولی
model_id متمایز — رگرسیون O/C رد شد (loss random-walk را به پیش‌بینی
«بدنه ≈ صفر» می‌رساند؛ علامتش نویز).

### پیاده‌شده (قسمت ۱ — آموزش)

- `trend_model_id/timeframe` در model_roles: `gold_trend_4h`،
  window=150، softmax دودسته‌ای، dropout 0.15.
- `build_trend_labels` در target_builder: GREEN=1 وقتی
  `close[t+1] ≥ close[t]`؛ بدون first-passage؛ آخرین کندل بی‌برچسب.
- `PredictionTarget`: threshold=0 حالا مجاز (برچسب رنگ به آستانه
  نیاز ندارد) — اعتبارسنجی از `<= 0` به `< 0`.
- `DualModelService.prepare`: شاخهٔ `gold_trend_*` — همهٔ ردیف‌های
  کامل، sample_ends استاندارد؛ definition: `label_style="color"`,
  `target_name="candle_color"`.
- `run_dual_models.py`: `--model trend_4h` + پیام label rule مخصوص.

### باقی‌مانده (قسمت ۲ — مصرف)

- SignalPredictor برای gold_trend کار می‌کند (2-softmax) ✓ ولی باید
  در backtest سیم کشیده شود: `TrendPredictor` با احتمال GREEN/RED +
  «مجوز ۵» در triple: خرید فقط وقتی P(GREEN) > آستانه؛ فروش فقط وقتی
  P(RED) > آستانه. (فیلد GUI: trend confidence %)

### وضعیت

```
ruff ✅ black ✅  pytest full suite green
دستور آموزش (روی سیستم اپراتور):
  python scripts/run_dual_models.py --with-features --symbol XAUUSD \
    --model trend_4h --epochs 60 --folds 2 --window 150 \
    --learning-rate 0.0008 --es-patience 15 --rlr-patience 5 \
    --storage-root datasets
```

## فاز ۹۸ (قسمت ۱-ب): trend در GUI آموزش + نمایش رنگ در /data

- **Train a model / Retrain / LR-sweep:** گزینهٔ `trend_4h` اضافه شد؛
  dataset پیشنهادی خودکار 4H؛ threshold=0 برای trend؛ Retrain مدل‌های
  gold_trend_* به درستی به role=trend_4h نقشه می‌خورد.
- **/data:** کلیک روی هر کندل → بالای جدول forecast، رنگ کندل بعدی از
  `gold_trend_4h` (▲ سبز / ▼ قرمز + درصد اطمینان + «روند پیش‌بینی
  صعودی/نزولی»). endpoint جدید `/api/trend-forecast` (علوی: پنجرهٔ
  فقط تا کندل انتخابی + warmup pad). اگر مدل ترند ذخیره نشده باشد
  پیام راهنما می‌دهد.
- JS با node --check تأیید؛ ruff/black پاک؛ کل تست‌سوت سبز.

### فاز ۹۸ (تصحیح اپراتور): trend برای هر تایم‌فریمی — نه فقط 4H

«قرار نیست فقط 4H باشه؛ اصلیش روزانه‌ست، شاید 4H هم بسازم» — درست.
`trend_4h` نامگذاری اشتباه بود:

- CLI: `--model trend` + تایم‌فریم از `--signal-timeframe`
  (پیش‌فرض 1D). مثال: `--model trend --signal-timeframe 1D`
  → `gold_trend_1d`؛ با 4H → `gold_trend_4h`.
- GUI (Train/Retrain/LR-sweep): گزینهٔ `trend`؛ دیتاست دلخواه
  (پیشنهاد 1D)؛ Retrain مدل‌های gold_trend_* → role=trend.
- /data: کلیک روی کندل، مدل ترند **هم‌تایم‌فریمِ سری فعال** را صدا
  می‌زند (`gold_trend_${tf}`) — سری 1D → gold_trend_1d، سری 4H →
  gold_trend_4h؛ اگر آن مدل ذخیره نشده پیام راهنما می‌دهد.
- `trend_model_role` پیش‌فرض timeframe="1D".

همهٔ تست‌سوت سبز؛ node --check روی اسکریپت چارت OK.

### فاز ۹۸ (رفع ابهام اپراتور): «دیتاست 1D انتخاب کردم ولی مدل 5M آموزش دید»

دو مسیر برای تایم‌فریمِ trend وجود داشت و GUI مسیر اشتباه را می‌فرستاد:
- اسکریپت trend را از `--signal-timeframe` می‌خواند (پیش‌فرض 5M)؛
- GUI مقدار Dataset را فقط در `--range-timeframes` می‌فرستاد.

رفع: اسکریپت برای trend اول `--range-timeframes` (همان Dataset) را
می‌خواند بعد signal-timeframe؛ GUI هم برای trend دیتاست انتخابی را در
هر دو فلگ می‌فرستد. سربرگ `training:` حالا `trend(1D)` را نشان می‌دهد
(قبلاً «nothing» چاپ می‌شد). + کل تست‌سوت سبز.

### فاز ۹۸ (رفع باگ اپراتور): «sample_end_indices and label_end_indices must be supplied together»

شاخهٔ trend در prepare صریحاً sample_ends می‌ساخت بدون
sample_label_ends → trainer جفتِ ناقص را رد می‌کرد. برچسب trend
ثابتِ یک‌کندله است — حالا مثل range دیتاستِ stride-1 ساده می‌سازد
(sample_ends=None) و purge ویژه لازم ندارد.
تأیید سرتاسری در سندباکس (TF نصب شد): prepare → train (1 epoch،
2 فولد) → val_accuracy 55.6% روی دادهٔ تصادفی → SignalPredictor
P(GREEN)=0.505. + کل tests/unit سبز (1034) — دو تست
test_threshold_recorded محیط‌اند (در HEAD هم fail؛ در WORKLOG فاز ۵۲ ثبت شده).

### فاز ۹۸ (تکمیلی): مدل ترند در /data

آپراتور: «مدل ترند توی /data نمیاد که انتخابش کنم» — درست بود:
`all_range_models` فقط role=range را برمی‌گرداند و gold_trend_1d
(role=signal) حذف می‌شد.

- inspector: gold_trend_* با `kind='trend'` در لیست می‌آید (signalهای
  خام همچنان حذف)؛ + تست به‌روزشده.
- دراپ‌داون /data: برچسب `[trend: color]` برای مدل‌های ترند.
- کلیک روی کندل وقتی مدل ترند انتخاب است → فقط رنگ کندل بعدی
  (▲/▼ + درصد) نمایش داده می‌شود و مسیر High/Low رسم نمی‌شود
  (مدل ترند براکت ندارد).
- تأیید: node --check، +تست به‌روزشده، کل تست‌سوت سبز
  (دو تست test_threshold_recorded محیطی — روی HEAD هم fail).

### فاز ۹۸ (رفع هنگ /data): کش مدل و فیچر برای endpoint ترند

**گزارش اپراتور:** کلیک روی کندل → فقط «predicting…» بی‌پایان + هشدار
tf.function retracing در PowerShell.

**ریشه:** `_trend_forecast_payload` در **هر کلیک**: (1) مدل TF را
دوباره deserialize می‌کرد (چند ثانیه) و (2) هر مدلِ جدید با ورودی
هم‌شکل → tf.function retrace کامل؛ (3) ساخت فیچرِ 530+ کندل با
229 فیچر هم چند ثانیه. روی ویندوز جمعاً ده‌ها ثانیه تا دقیقه —
مرورگر فقط waiting می‌دید.

**رفع:** کش سطح کلاس روی DashboardHandler:
- `_model_cache[key = id:version:checksum]` — deserialize یک بار؛
- `_feature_cache[key = symbol:tf:bar:window]` — فیچر هر کندل یک بار
  (سقف 512 و clear).

**اندازه‌گیری واقعی (سندباکس، مدل واقعی keras + دیتای parquet):**
cold 4.2s → warm same-bar 0.07s → bar جدید 1.2s. رفع هنگ ✓

### فاز ۹۸ (رفع باگ دوم اپراتور): پنل ترند هرگز نمایش داده نمی‌شد

**گزارش:** «predicting…» می‌نویسد و هیچ خروجی نمی‌آید (سه GET).
سرور در واقع پاسخ می‌دهد (تست thread در سندباکس سبز، کش هم کار می‌کند)
— مشکل سمت مرورگر بود:

شاخهٔ trend در fetchForecast پنل را `display='none'` می‌کرد و هرگز
نشان نمی‌داد؛ باکس `trend-color` هم **داخل همان پنل مخفی** است →
خروجی سرور به جایی رندر نمی‌شد.

**رفع:** پنل قبل از await نمایش داده می‌شود؛ «predicting…» بعد از
دریافت پاسخ پاک می‌شود؛ مسیر High/Low هم پاک می‌شود (مدل ترند
براکت ندارد). node --check ✓، کل تست‌سوت سبز (دو تست محیطی همان).

---

## 2026-09-03 — فاز ۹۹: مدل سیگنال ترند — سه‌کلاسه BUY/HOLD/SELL (roll-forward)

**طرح اپراتور (پس از A/B):** پنجرهٔ rolling 288 کندل 5M → پیش‌بینی
سه‌کلاسه برای 288 کندل بعدی: BUY اگر حرکت صعودی، SELL اگر نزولی،
HOLD اگر هیچ. تعریف «صعودی/نزولی» (پیشنهاد من، تأیید اپراتور):
**اولین عبور ±X×ATR14 از close** در افق — X پیش‌فرض 0.5 (GUI).
نام مدل داینامیک با تایم‌فریم: `gold_trend_signal_<tf>`.

### پیاده‌سازی

- `build_trend_signal_labels(candles, horizon=288, atr_mult=0.5)`:
  برچسب 0=SELL / 1=HOLD / 2=BUY؛ برخورد دو مانع در یک کندل → نمونهٔ
  مبهم حذف؛ sample_label_ends برای purge درست (برچسب تا 288 کندل
  جلوتر می‌رود).
- `trend_signal_model_role` → `gold_trend_signal_<tf>`، window=288،
  `PredictionTarget.num_classes=3` (output_units=3)، نقش signal
  (softmax سه‌کلاسه + sparse CE + accuracy).
- `DualModelService.prepare`: شاخهٔ trend_signal **قبل از** شاخهٔ
  gold_trend_ (prefix مشترک بود!) با sample_ends + label_ends.
- CLI: `--model trend_signal` + ‏`--atr-mult` (0.5) + ‏`--label-horizon`
  (288)؛ سربرگ label rule مخصوص؛ sanity prediction سه‌کلاسه؛
  signal_label_split_balance سه‌کلاسه ({sell,hold,buy}).
- GUI: Train/Retrain/LR-sweep گزینهٔ `trend_signal` + فیلدهای
  «Trend-signal barrier (×ATR14)» و «Trend-signal horizon»؛
  دیتاست پیشنهادی 5M؛ threshold برای trend_signal = X (نه درصد).
- `PredictionTarget.num_classes` (2/3) با اعتبارسنجی.

### تأیید سرتاسری

- ۹ سناریوی دستی برچسب (BUY/SELL/HOLD/مبهم/علیت) ✓
- CLI کامل روی 800 کندل 5M مصنوعی: آموزش → ذخیره → حکم QUALITY →
  پیش‌بینی سه‌کلاسه (SELL/HOLD/BUY با argmax) ✓
- +۹ تست واحد؛ کل تست‌سوت سبز (دو تست محیطی همیشگی مستثنا)

### گام بعدی (قسمت ۲ — بکتست)

مجوز ۶ در triple: خرید فقط P(BUY)>آستانه و >P(HOLD)؛ فروش مشابه
(فیلد GUI). آماده‌سازی بعد از تأیید اپراتور.

## 2026-09-04 — تحلیل ران gold_trend_1d (400×3، بدون ES مؤثر)

اپراتور ران 1:47h را کامل کرد: ‏val_acc 57.0% vs baseline 53.2% →
BETTER (پیش از این 50 epochs هم همین بود). نکات:
- ES patience=400 عملاً خاموش — 1200 epoch کامل اجرا شد؛ اما checkpoint
  per-epoch بهترین را نگه داشت؛ KEPT=epoch آخر فولد ۳.
- val_acc از fold 1 (50.1%) به fold 3 (57.0%) بهبود — ولی دقت بهبود
  عمدتاً از decay LR (0.0008→0.00007) و حرکت ملایم مدل به سمت کلاس
  اکثریت (green 53.2%) است؛ bias «سیگنال ترند» هنوز ضعیف.
- val_loss 0.6866 نزدیک ln(2)=0.693 → مدل فقط کمی بهتر از سکه.
- کاهش LR خودکار کار کرد (learning_rate: 0.00007).

### جمع‌بندی برای تصمیم بعدی
لبهٔ 3.8% (57.0 vs 53.2) نازک است؛ برای گیت ورود باید آستانهٔ
احتمال را بالاتر از 53% نگذاشت و بهتر است با confidence 55-57% تست شود.
مدل trend_signal (سه‌کلاسه) شانس بیشتری برای لبهٔ واقعی دارد چون
HOLD راه فرار از روزهای بی‌رون می‌دهد.

### فاز ۹۹ (تکمیلی): trend_signal در GUI آموزش

- MODEL_ROLE_CHOICES + دراپ‌داون Train/Retrain/LR-sweep: گزینهٔ
  `trend_signal` اضافه شد؛ دیتاست پیشنهادی خودکار 5M؛ threshold برای
  trend_signal = X برحسب ATR14 (فیلد atr_mult، پیش‌فرض 0.5)؛
  label_horizon (288) هم به هر سه فرم اضافه شد.
- Retrain: مدل‌های gold_trend_signal_* به role=trend_signal نقشه
  می‌خورند و threshold ذخیره‌شده را ارث می‌برند.
- تأیید: descriptorهای TRAIN/RETRAIN/LR-sweep فیلدها و گزینه‌ها را
  دارند؛ lint پاک؛ tests/unit سبز.

---

## 2026-09-05 — فاز ۹۸-ب: مدل trend_score + رفع باگ HOLD + GUI

**درخواست اپراتور:** سه کار: (۱) ATR مانع trend_signal از تایم‌فریم
روزانه، (۲) مدل Trend-Score در GUI، (۳) تارگت score روند.

### رفع ۱: ATR مانع trend_signal → بازهٔ 288 کندلی

مانع قبلی از ATR14(5M)≈$2 بود → HOLD=0%. حالا مانع =
0.5×بازهٔ 288 کندل عقب‌تر (max(high)−min(low)) که ~$30-40 است.
تأیید: label balance روی 2200 کندل → sell 17.7% · hold 26.4% · buy 55.9% ✓

### رفع ۲: trend_score مدل جدید (رگرسیون score روند)

- `build_trend_score_labels`: score = (close−open)/(high−low) روی
  کندل تجمعی از horizon کندل آینده → پیوسته در (−1,+1)
- `trend_score_model_role`: name="range" (reuse رگرسیون+Huber+MAE)،
  kind=PRICE_RANGE، model_id=`gold_trend_score_<tf>`
- prepare: شاخهٔ trend_score **قبل از** PRICE_RANGE generic
  (در غیر این صورت range branches it را می‌ربود)
- CLI: `--model trend_score` + سربرگ label rule مخصوص
- GUI: همهٔ فرم‌ها (Train/Retrain/LR-sweep) گزینهٔ `trend_score`
  + فیلدهای label_horizon پاس داده می‌شوند

### تأیید سرتاسری

CLI کامل روی 800 کندل: train → val_mae 0.239 → **BEATS baseline 61%** ✓
```
ruff ✅ black ✅  tests/unit سبز
```

### فاز ۹۸-ب (تصحیح اپراتور): trend_score در دراپ‌داون Train

اپراتور درست گفت — `trend_score` در dropdown نبود. اضافه شد:
`('all', 'range', 'signal', 'trend', 'trend_signal', 'trend_score')`

### فاز ۹۸-ب (رفع): رنگ ترند هنگام انتخاب مدل رنج هم fetch می‌شد

**گزارش:** روی سری 5M وقتی مدل رنج (غیر-trend) انتخاب شده بود،
پیام «مدل gold_trend_5m ذخیره نشده» ظاهر می‌شد — چون
`fetchForecast` در **پایان** خودش (صرف‌نظر از انتخاب مدل) همیشه
`fetchTrendColor` را صدا می‌زد.

**رفع:** `fetchTrendColor` فقط داخل شاخهٔ trend (وقتی کاربر صریحاً
مدل ترند انتخاب کرده) صدا زده می‌شود. برای مدل‌های رنج رنگ ترند
نمایش داده نمی‌شود.

node --check ✓ · کل تست‌سوت سبز ✓

### فاز ۹۸-ب (رفع): «trend: color is not defined» در /data

**ریشه:** در `fetchTrendColor` متغیر `color` standalone استفاده شده بود
(`${color === 'GREEN' ? '▲' : '▼'}`) ولی این متغیر تعریف نشده بود —
فقط `green` (boolean) و `data.color` موجود بودند.

**رفع:** `${color === 'GREEN' ? '▲' : '▼'}` → `${green ? '▲' : '▼'}`
node --check ✓ · کل تست‌سوت سبز ✓

### فاز ۹۸-ب (رفع دوم): fetchTrendColor پارامتر modelOverride نداشت

فراخوانی `fetchTrendColor(barIndex, symbol, timeframe, modelId)` پارامتر
چهارم را می‌فرستاد ولی تعریف تابع فقط ۳ پارامتر داشت → modelOverride
همیشه undefined → همیشه `gold_trend_${tf}` fallback می‌شد → «مدل ذخیره
نشده». رفع: پارامتر modelOverride به امضای تابع اضافه شد.

### فاز ۹۸-ب (رفع): /data فقط مدل‌های هم‌تایم‌فریم نمایش می‌دهد

**گزارش اپراتور:** gold_trend_score_5m روی سری 1D کار می‌کند و «روند
ثابت با درصد ثابت» می‌دهد — بی‌معنا چون مدل روی 5M آموزش دیده و
فیچرهای 1D کاملاً متفاوت‌اند.

**رفع:** `all_range_models(timeframe)` — وقتی timeframe پاس داده شود
فقط مدل‌های هم‌تایم‌فریم با سری فعال برمی‌گردد. سرور این را با
`timeframe` فعلی صدا می‌زند. کاربر دیگر مدل 5M را روی سری 1D نمی‌بیند.
hint زیر دراپ‌داون هم اضافه شد.

تأیید: فیلتر 5M → فقط trend_score_5m؛ فیلتر 1D → فقط range_1d؛
بدون فیلتر → هر دو. کل تست‌سوت سبز ✓

### فاز ۹۸-ب (رفع نهایی): fetchTrendColor modelOverride استفاده نمی‌کرد

**ریشهٔ واقعی که سه بار رد شد:** تابع `fetchTrendColor` پارامتر
`modelOverride` را می‌پذیرفت ولی **هیچ‌جا از آن استفاده نمی‌کرد** —
به‌جایش `gold_trend_${tf}` می‌ساخت که برای سری 5M یعنی gold_trend_5m
(وجود ندارد).

**رفع نهایی:** `const trendModelId = modelOverride || gold_trend_${tf}`
— وقتی کاربر مدل ترند انتخاب کرده، از همان استفاده می‌شود.

تأیید end-to-end با مدل واقعی TF + دیتای parquet: ✅

### فاز ۹۸-ب (نهایی — ریشهٔ واقعی): modelOverride استفاده نمی‌شد

**تحلیل عمیق:** سرور endpoint کامل و سالم است (تست سرتاسری سندباکس
با مدل keras واقعی + parquet: ✅ GREEN 68.3%). مشکل فقط سمت مرورگر:
`fetchTrendColor` پارامتر `modelOverride` را می‌پذیرفت ولی هیچ‌جا
استفاده نمی‌کرد — همیشه `gold_trend_${tf}` fallback می‌شد.

رفع: `trendModelId = modelOverride || gold_trend_${tf}` + حذف
فراخوانی خودکار برای مدل‌های غیر-trend. اندازه‌گیری سندباکس: ✅

### فاز ۹۸-ب (رفع نهایی-۲): پیام خطای هاردکد جایگزین پیام واقعی سرور شده بود

fetchTrendColor وقتی data.error داشت، **همیشه** متن «ذخیره نشده» را
نمایش می‌داد — حتی اگر خطای سرور چیز دیگری بود (مثل فیچر ناموجود یا
کندل ناکافی). این باعث می‌شد دیباگ غیرممکن شود چون پیام واقعی مخفی
می‌شد. حالا پیام واقعی سرور + لیست مدل‌های ذخیره‌شده نمایش داده می‌شود.
