# فاز ۱۱۹ — GUI cleanup: جمع‌کردن پارامترهای پیشرفته زیر Advanced options

**وضعیت:** ✅ کامل  
**نوع:** UX / operator safety  
**تاریخ:** 2026-09-08

---

## مسئله

Dashboard برای commandهای آموزشی و بکتست تعداد زیادی پارامتر نشان می‌داد. این باعث می‌شد فرم‌های زیر برای کار روزانه گیج‌کننده شوند:

```text
Train a model
Retrain a saved model
Find best learning rate
Run a backtest
Record a replay
Audit trend-signal labels
Calibrate trend-signal thresholds
```

اما حذف کامل پارامترها هم درست نبود، چون operator هنوز باید در مواقع خاص به knobهای حرفه‌ای دسترسی داشته باشد.

---

## تصمیم

پارامترها حذف نشدند. فقط موارد کم‌مصرف یا پرریسک زیر یک بخش collapsed رفتند:

```text
Advanced options
```

یعنی:

```text
Basic fields = چیزهایی که معمولاً تغییر می‌دهیم
Advanced fields = knobهای معماری، patience، threshold جزئی، cost/backtest جزئی، timeout و model override
```

---

## تغییر فنی

### `CommandField`

فیلد جدید اضافه شد:

```python
advanced: bool = False
```

مسیر:

```text
src/ShadBotTrader/presentation/commands/commands.py
```

### descriptorها

در handlerها mapping مرکزی ساخته شد:

```text
_ADVANCED_COMMAND_FIELDS
```

مسیر:

```text
src/ShadBotTrader/presentation/commands/handlers.py
```

### renderer

`render_actions` حالا fieldهای `advanced=True` را داخل `<details>` نشان می‌دهد:

```text
<details class="advanced-inputs">
  <summary>Advanced options (...)</summary>
  ...
</details>
```

مسیر:

```text
src/ShadBotTrader/presentation/web/renderer.py
```

---

## رفتار حفظ‌شده

```text
- هیچ command حذف نشد.
- هیچ پارامتری حذف نشد.
- همهٔ inputها همچنان در form هستند و defaultشان submit می‌شود.
- handlerها و script arguments مثل قبل کار می‌کنند.
```

---

## فرم‌های خلوت‌شده

### Train a model

Basic:

```text
symbol, model, dataset, atr_mult, class_weight, label_horizon,
epochs, folds, window, learning_rate, train_ratio
```

Advanced:

```text
range_horizon, threshold_pct, trend_score_loss, monitor_metric,
es_patience, rlr_patience, n_layers, n_blocks, val_size, timeout_minutes
```

### Run a backtest / Record a replay

Basic:

```text
symbol, timeframe, range_timeframe, strategy
```

Advanced:

```text
model overrides, windows, spread/slippage/commission,
capital/quantity, session filter, slope/range filters, min SL, last N candles
```

### Calibration

Basic:

```text
symbol, dataset, window, label_horizon, atr_mult, train_ratio
```

Advanced:

```text
threshold grid, min_margin, min_trades, precision_floor, max_windows, save_record, timeout
```

---

## معیار پذیرش

```text
- dashboard هنوز تمام commandها را render می‌کند.
- advanced fields مثل n_layers/n_blocks هنوز در HTML وجود دارند.
- تست GUI برای collapsed advanced options اضافه شد.
```
