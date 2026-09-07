# فاز ۱۰۹ — پیشنهاد: threshold calibration و heatmap backtest

**وضعیت:** 🟡 پیشنهادی / آمادهٔ اجرا
**نوع:** Evaluation + trading decision calibration
**اولویت:** بالا

---

## هدف

احتمال خروجی مدل مستقیم نباید با threshold ثابت مثل 60% معامله شود. باید روی validation/backtest threshold مناسب پیدا شود.

---

## ایده الهام‌گرفته

از `ari99/algorithmic_trading`:

```text
LongMin × ShortMin grid
0.00, 0.05, ..., 0.95
```

برای ShadBotTrader:

```text
BUY threshold × SELL threshold
```

---

## پارامترهای grid

```text
buy_prob_threshold: 0.05..0.95 step 0.05
sell_prob_threshold: 0.05..0.95 step 0.05
min_margin_vs_hold: 0.00..0.30
min_margin_vs_opposite: 0.00..0.30
```

---

## معیار انتخاب

برای هر ترکیب threshold:

```text
trade_count
win_rate
profit_factor
expectancy
net_return
max_drawdown
avg_R
buy_precision
sell_precision
false_positive_cost
```

انتخاب فقط اگر:

```text
min_trades پاس شود
precision floor پاس شود
drawdown سقف را رد نکند
profit factor یا expectancy مثبت باشد
```

---

## خروجی ذخیره‌شده در ModelRecord

```json
"decision_thresholds": {
  "buy_prob": 0.74,
  "sell_prob": 0.72,
  "min_margin_vs_hold": 0.12,
  "min_margin_vs_opposite": 0.18,
  "selected_by": "validation_profit_factor_with_precision_floor",
  "validation_trades": 82,
  "validation_profit_factor": 1.23
}
```

---

## فایل‌های پیشنهادی

```text
scripts/calibrate_trend_signal_thresholds.py
src/ShadBotTrader/application/services/threshold_calibration_service.py
```

---

## فایل‌های درگیر موجود

```text
src/ShadBotTrader/application/services/model_evaluation_service.py
src/ShadBotTrader/application/services/dual_model_backtest_service.py
src/ShadBotTrader/infrastructure/ai/model_catalogue.py
```

---

## معیار پذیرش

```text
- threshold روی train انتخاب نشود؛ validation/holdout لازم است.
- heatmap خروجی CSV/HTML تولید شود.
- مدل بدون threshold calibrated همچنان با default کار کند ولی warning بدهد.
```
