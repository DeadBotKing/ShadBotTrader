# فاز ۱۲۵ — Hybrid Head Calibration + Range TP/SL Backtest

**وضعیت:** ✅ زیرساخت CLI/GUI پیاده‌سازی شد  
**نوع:** Trading-aware calibration/backtest  
**تاریخ:** 2026-09-09

---

## هدف

فاز ۱۲۴ فقط کیفیت classification مدل hybrid head را سنجید. فاز ۱۲۵ خروجی همان مدل را تبدیل به تصمیم معاملاتی می‌کند و با TP/SL واقعی‌تر تست می‌کند:

```text
hybrid head probabilities
+ BUY/SELL thresholds
+ range_1d room filter
+ range_4h TP/SL bracket
+ spread/slippage
→ simulated trades
```

---

## فایل جدید

```text
scripts/backtest_hybrid_xgboost_head.py
```

---

## GUI جدید

Command:

```text
Backtest hybrid XGBoost head
```

Action:

```text
backtest_hybrid_xgboost_head
```

---

## ورودی اصلی

مدل:

```text
gold_hybrid_lightgbm_head_5m
```

ماتریس پیش‌فرض:

```text
datasets/processed/XAUUSD/5M/hybrid_xgboost_matrix_latest.parquet
```

کندل واقعی 5M از storage خوانده می‌شود تا برخورد TP/SL با مسیر آینده بررسی شود.

---

## منطق تصمیم

برای هر ردیف evaluation:

```text
probs = hybrid_head.predict_proba(row_features)
```

قانون:

```text
BUY اگر buy_prob >= buy_threshold و buy_prob از sell/hold حداقل min_margin بالاتر باشد
SELL اگر sell_prob >= sell_threshold و sell_prob از buy/hold حداقل min_margin بالاتر باشد
وگرنه NO_TRADE
```

---

## فیلتر Range

قبل از باز کردن trade:

```text
BUY  نیاز دارد range_4h_up_room و range_1d_up_room کافی باشند
SELL نیاز دارد range_4h_down_room و range_1d_down_room کافی باشند
```

پارامترها:

```text
--min-4h-room
--min-1d-room
```

---

## TP/SL

برای BUY:

```text
TP = min(range_4h_high_price, range_1d_high_price)
SL = range_4h_low_price
```

برای SELL:

```text
TP = max(range_4h_low_price, range_1d_low_price)
SL = range_4h_high_price
```

اگر TP/SL نسبت به entry معتبر نباشد، trade رد می‌شود.

---

## Entry و هزینه‌ها

entry روی کندل بعدی انجام می‌شود:

```text
entry_index = source_index + 1
entry_price = next_open ± half_spread ± slippage
```

spread:

```text
--spread-mode pct   با --spread-value 0.06 یعنی 0.06%
--spread-mode fixed با --spread-value 1.80 یعنی 1.80 دلار
```

---

## خروجی

```text
run_logs/hybrid_head_backtest/latest.csv
run_logs/hybrid_head_backtest/latest.json
```

اگر `--save-record 1` باشد، threshold انتخاب‌شده در رکورد مدل hybrid ذخیره می‌شود:

```text
datasets/models/gold_hybrid_lightgbm_head_5m/vN_training.json
```

---

## دستور پیشنهادی

```powershell
python -u scripts/backtest_hybrid_xgboost_head.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --model-id gold_hybrid_lightgbm_head_5m `
  --eval-frac 0.30 `
  --threshold-min 0.35 `
  --threshold-max 0.95 `
  --threshold-step 0.05 `
  --min-margin 0 `
  --min-trades 30 `
  --score-metric total_pnl `
  --max-hold-bars 48 `
  --min-4h-room 0 `
  --min-1d-room 0 `
  --min-tp-distance 1 `
  --min-sl-distance 1 `
  --spread-mode pct `
  --spread-value 0.06 `
  --slippage 0 `
  --same-bar-policy stop_first `
  --save-record 1 `
  --storage-root datasets
```

---

## معیارهای مهم

```text
trades
coverage
win_rate
label_precision
total_pnl
avg_pnl
profit_factor
max_drawdown
TP/SL/timeout counts
```

اگر نتیجه مثبت بود، فاز بعدی significance check است.

---

## محدودیت

این backtest هنوز execution کامل production نیست؛ اما از classification-only جلوتر است، چون TP/SL و مسیر قیمت آینده را لحاظ می‌کند.
