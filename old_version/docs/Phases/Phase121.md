# فاز ۱۲۱ — Tabular Booster Branch برای trend_signal

**وضعیت:** ✅ زیرساخت پیاده‌سازی شد / اجرای واقعی نیازمند نصب optional booster backend  
**نوع:** Model branch benchmark  
**تاریخ:** 2026-09-08

---

## هدف

بعد از اینکه WaveNet برای `trend_signal` چند بار collapse کرد، باید یک branch متفاوت بسازیم که با دیتای مهندسی‌شده بهتر کار کند:

```text
179 feature causal
+ خلاصهٔ causal از پنجرهٔ 288 کندلی
+ LightGBM / XGBoost / CatBoost
```

این branch جایگزین فوری WaveNet نیست؛ benchmark مستقل است. اگر بهتر بود بعداً در فاز ۱۱۶ به decision engine وصل می‌شود.

---

## فایل جدید

```text
scripts/train_trend_signal_boosters.py
src/ShadBotTrader/infrastructure/ai/tabular_window_summary.py
requirements-boosters.txt
```

---

## GUI جدید

Command جدید:

```text
Train trend-signal booster
```

Action:

```text
train_trend_signal_booster
```

مسیر GUI:

```text
Dashboard → AI → Train trend-signal booster
```

---

## مدل‌های پشتیبانی‌شده

```text
--booster auto|lightgbm|xgboost|catboost
```

`auto` به ترتیب تلاش می‌کند:

```text
LightGBM → XGBoost → CatBoost
```

اگر هیچ‌کدام نصب نباشد، پیام واضح می‌دهد:

```text
pip install -r requirements-boosters.txt
```

---

## خروجی‌های branch

### multiclass

```text
SELL/HOLD/BUY
model_id نمونه: gold_trend_signal_lightgbm_basic_5m
```

### buy specialist

```text
BUY vs NOT_BUY
model_id نمونه: gold_buy_lightgbm_basic_5m
```

### sell specialist

```text
SELL vs NOT_SELL
model_id نمونه: gold_sell_lightgbm_basic_5m
```

---

## Window summary

چون boosterها tensor سه‌بعدی نمی‌گیرند، هر پنجرهٔ 288 کندلی به یک ردیف tabular تبدیل می‌شود.

گزینه‌ها:

```text
last        : فقط آخرین مقدار هر feature
basic       : last + delta_1 + mean/std/delta برای scaleهای 12/48/288
multi_scale : basic + min/max/slope برای scaleهای 12/48/144/288
```

پیشنهاد اولیه:

```text
summary_mode = basic
```

---

## دستور پیشنهادی برای تست اول

```powershell
python -u scripts/train_trend_signal_boosters.py `
  --symbol XAUUSD `
  --timeframe 5M `
  --booster auto `
  --output-mode multiclass `
  --summary-mode basic `
  --window 288 `
  --label-horizon 288 `
  --atr-mult 0.5 `
  --train-ratio 80 `
  --folds 3 `
  --val-size 2000 `
  --class-weight auto `
  --n-estimators 400 `
  --learning-rate 0.03 `
  --storage-root datasets
```

اگر خواستیم specialist بسازیم:

```text
--output-mode buy
--output-mode sell
```

---

## معیار پذیرش

برای multiclass فقط accuracy کافی نیست. باید ضد-collapse باشد:

```text
val_action_collapse = 0
val_action_min_f1_supported > 0
val_predicted_class_count >= 2
sell_f1 > 0 و buy_f1 > 0 وقتی هر دو در validation support دارند
```

برای specialist:

```text
val_event_f1
val_event_recall
val_event_precision
Average Precision
```

---

## ذخیره artifact

مدل با فرمت pickle داخل ModelArtifact ذخیره می‌شود:

```text
datasets/models/{model_id}/vN.bin
datasets/models/{model_id}/vN.json
datasets/models/{model_id}/vN_training.json
```

گزارش آخرین اجرا:

```text
run_logs/trend_signal_boosters/latest.json
```

---

## ارتباط با فاز ۱۱۶

اگر booster branch بهتر از WaveNet بود، در فاز ۱۱۶ این خروجی‌ها کنار range modelها قرار می‌گیرند:

```text
booster_probabilities
+ gold_range_1d daily envelope
+ gold_range_4h TP/SL bracket
+ meta/no-trade gate
```
