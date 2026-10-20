# فاز ۱۰۹ — threshold calibration و heatmap برای trend_signal

**تاریخ:** 2026-09-07
**وضعیت کد:** ✅ کامل — ابزار کالیبراسیون، GUI، ذخیره threshold و تست پیاده‌سازی شد

**وضعیت عملیاتی:** ⏳ منتظر پایان training واقعی فاز ۱۰۸ روی سیستم اپراتور؛ تا وقتی مدل `gold_trend_signal_5m` جدید ذخیره نشود، calibration را اجرا نکن.
**گزارش:** `docs/Report/PHASE109_TREND_SIGNAL_THRESHOLD_CALIBRATION_REPORT.md`

---

## هدف

بعد از training مدل `trend_signal`، thresholdهای BUY و SELL نباید حدسی باشند. این فاز ابزار می‌دهد تا thresholdها با grid search روی validation/holdout کالیبره شوند.

---

## فایل جدید

```text
scripts/calibrate_trend_signal_thresholds.py
```

---

## GUI جدید

Command:

```text
Calibrate trend-signal thresholds
```

Action:

```text
calibrate_trend_signal
```

---

## ورودی‌های اصلی

```text
model_id optional
window
label_horizon
atr_mult
train_ratio
scope auto|holdout|last-fold|all
threshold_min/max/step
min_margin
min_trades
precision_floor
max_windows
save_record
```

---

## decision rule

```text
BUY اگر buy_prob از threshold بگذرد و از sell/hold حداقل min_margin بالاتر باشد.
SELL اگر sell_prob از threshold بگذرد و از buy/hold حداقل min_margin بالاتر باشد.
بقیه NO_TRADE.
```

---

## خروجی

```text
run_logs/trend_signal_thresholds/latest.csv
run_logs/trend_signal_thresholds/latest.html
run_logs/trend_signal_thresholds/latest.json
```

و نسخه timestamped برای هر اجرا.

---

## ذخیره در model record

به `ModelRecord` اضافه شد:

```python
decision_thresholds: Dict[str, Any]
```

اگر `save_record=1` باشد، بهترین threshold در `v*_training.json` ذخیره می‌شود.

---

## تست‌ها

```text
tests/unit/ai/test_threshold_calibration.py
tests/integration/test_trend_signal_calibration_gui.py
```

Targeted ruff/black/pytest سبز شد.

---

## محدودیت

این فاز فعلاً label/probability calibration است، نه full PnL backtest با TP/SL. برای profit-aware calibration کامل باید thresholdها به triple backtest وصل شوند.

---

## اجرای پیشنهادی بعد از train

```powershell
python -u scripts/calibrate_trend_signal_thresholds.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --window 288 `
  --label-horizon 288 `
  --atr-mult 0.5 `
  --train-ratio 80 `
  --scope auto `
  --threshold-min 0.35 `
  --threshold-max 0.95 `
  --threshold-step 0.05 `
  --min-margin 0 `
  --min-trades 50 `
  --precision-floor 0 `
  --max-windows 8000 `
  --save-record 1 `
  --storage-root datasets
```

---

## گام بعد

بعد از دریافت خروجی train و calibration، برویم سراغ:

```text
Phase110 — feature selection train-only
```

یا اگر خروجی مدل ضعیف بود، اول threshold/target را اصلاح کنیم.
