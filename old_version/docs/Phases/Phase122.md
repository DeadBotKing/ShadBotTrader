# فاز ۱۲۲ — Calibration برای BUY/SELL Booster Specialists

**وضعیت:** ✅ پیاده‌سازی شد  
**نوع:** Threshold calibration / decision gate  
**تاریخ:** 2026-09-08

---

## دلیل

بعد از فاز ۱۲۱، branchهای جدا برای BUY و SELL ساخته شدند:

```text
gold_buy_lightgbm_basic_5m
gold_sell_lightgbm_basic_5m
```

نتیجهٔ اپراتور نشان داد specialistها بهتر از WaveNet collapse‌شده هستند، اما خروجی raw probability هنوز مستقیم قابل معامله نیست. باید threshold جدا برای BUY و SELL پیدا شود.

---

## فایل جدید

```text
scripts/calibrate_trend_signal_boosters.py
```

---

## GUI جدید

Command:

```text
Calibrate booster specialists
```

Action:

```text
calibrate_trend_signal_boosters
```

---

## منطق تصمیم

برای هر window:

```text
buy_prob  = احتمال positive از مدل BUY specialist
sell_prob = احتمال positive از مدل SELL specialist
```

قانون:

```text
BUY اگر buy_prob >= buy_threshold و buy_prob - sell_prob >= min_margin
SELL اگر sell_prob >= sell_threshold و sell_prob - buy_prob >= min_margin
اگر هر دو true → ambiguous / no trade
اگر هیچکدام true → no trade
```

---

## Grid search

```text
BUY threshold × SELL threshold
```

پارامترها:

```text
threshold_min
threshold_max
threshold_step
min_margin
min_trades
min_side_trades
precision_floor
max_windows
```

`min_side_trades` مهم است چون نمی‌خواهیم بهترین threshold فقط BUY یا فقط SELL بدهد.

---

## خروجی

```text
run_logs/trend_signal_booster_thresholds/latest.csv
run_logs/trend_signal_booster_thresholds/latest.html
run_logs/trend_signal_booster_thresholds/latest.json
```

و نسخه timestamped برای هر اجرا.

---

## ذخیره در model record

اگر `save_record=1` باشد، threshold انتخاب‌شده داخل هر دو مدل BUY و SELL ذخیره می‌شود:

```json
"decision_thresholds": {
  "buy_prob": 0.55,
  "sell_prob": 0.60,
  "min_margin": 0.05,
  "selected_by": "phase122_booster_specialist_grid_action_f1",
  "action_precision": 0.0,
  "action_recall": 0.0,
  "action_f1": 0.0,
  "coverage": 0.0,
  "trades": 0
}
```

---

## دستور پیشنهادی

```powershell
python -u scripts/calibrate_trend_signal_boosters.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --booster lightgbm `
  --summary-mode basic `
  --window 288 `
  --label-horizon 288 `
  --atr-mult 0.5 `
  --train-ratio 80 `
  --scope holdout `
  --threshold-min 0.35 `
  --threshold-max 0.95 `
  --threshold-step 0.05 `
  --min-margin 0 `
  --min-trades 50 `
  --min-side-trades 10 `
  --precision-floor 0 `
  --max-windows 8000 `
  --save-record 1 `
  --storage-root datasets
```

---

## معیار پذیرش

```text
- هر دو سمت BUY و SELL باید حداقل min_side_trades داشته باشند.
- action_precision/action_recall/action_f1 گزارش شود.
- اگر هیچ threshold معتبر نبود، script با پیام واضح شکست بخورد.
- calibration باید روی holdout/last-fold/all قابل انتخاب باشد.
- هیچ training جدید انجام نشود؛ فقط مدل‌های ذخیره‌شده score شوند.
```

---

## ارتباط با فاز ۱۱۶

خروجی این فاز ورودی فاز ۱۱۶ است:

```text
buy_prob/sell_prob calibrated gate
+ gold_range_1d daily envelope
+ gold_range_4h TP/SL bracket
=> final BUY/SELL/NO_TRADE
```
