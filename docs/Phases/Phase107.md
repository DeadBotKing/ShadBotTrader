# فاز ۱۰۷ — پیشنهاد: audit کامل trend_signal

**وضعیت:** 🟡 پیشنهادی / آمادهٔ اجرا  
**نوع:** Research + tooling، بدون تغییر معماری  
**اولویت:** بسیار بالا

---

## هدف

قبل از retrain سنگین `gold_trend_signal_5m` باید بفهمیم target فعلی دقیقاً چه توزیعی دارد، چه مقدار ambiguous حذف می‌شود، baseline چیست و آیا validation folds نماینده هستند یا نه.

---

## فایل پیشنهادی جدید

```text
scripts/evaluate_trend_signal_5m.py
```

---

## ورودی‌ها

```text
--symbol XAUUSD
--timeframe 5M
--window 288
--label-horizon 288
--atr-mult 0.5
--storage-root datasets
--model-id gold_trend_signal_5m optional
```

---

## گزارش‌های لازم قبل از model prediction

```text
candles count
date range
feature matrix rows/features/dropped_warmup
label distribution: SELL/HOLD/BUY
ambiguous samples count
warmup skipped count
first-hit distance stats: min/p25/median/p75/max
barrier distance stats
class ratios
majority baseline
always-HOLD baseline
fold train/validation distribution
```

---

## گزارش‌های لازم بعد از model prediction

اگر model artifact موجود بود:

```text
confusion matrix
precision/recall/F1 per class
macro-F1
weighted-F1
balanced accuracy
PR-AUC BUY
PR-AUC SELL
prediction probability spread
collapse check: stdev(prob_buy), stdev(prob_sell), stdev(prob_hold)
```

---

## فایل‌های درگیر

```text
src/ShadBotTrader/infrastructure/ai/target_builder.py
src/ShadBotTrader/application/services/dual_model_service.py
scripts/evaluate_trend_signal_5m.py
```

---

## معیار پذیرش

```text
- بدون TensorFlow هم label audit کامل اجرا شود.
- اگر TensorFlow/model artifact موجود نبود، graceful skip کند.
- label distribution و fold distribution دقیق چاپ شود.
- هیچ آینده‌ای وارد feature نشود.
```

---

## دلیل اهمیت

مشکل score نشان داد قبل از train سنگین باید target را با عدد بشناسیم. این فاز اجازه می‌دهد قبل از هزینه training بفهمیم آیا `trend_signal` سالم و قابل یادگیری است یا باید target اصلاح شود.
