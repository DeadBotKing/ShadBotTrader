# فاز ۱۰۵ — بررسی پروژهٔ Leci37 و استخراج الگوهای قابل استفاده

**تاریخ:** 2026-09-07
**وضعیت:** ✅ کامل — گزارش مستند شد
**گزارش:** `docs/Report/PHASE105_LECI37_CODE_REVIEW_AND_ADOPTION_PLAN.md`

---

## منبع

```text
https://github.com/Leci37/TensorFlow-stocks-prediction-Machine-learning-RealTime
commit inspected: 7520351
```

Repo موقتاً clone شد، کدهای لازم بررسی شد، سپس برای خلوت‌کردن workspace حذف شد. خلاصه و تصمیم فنی در Docs باقی ماند.

---

## فایل‌های مهم بررسی‌شده

```text
Utils/Utils_buy_sell_points.py
Utils/Utils_model_predict.py
Feature_selection_create_json.py
Feature_selection_json_columns.py
Data_multidimension.py
Model_TF_definitions.py
Model_train_TF_multi_onBalance.py
Model_train_TF_onBalance.py
Model_train_sklearn_XGB.py
Model_predictions_handle.py
Model_predictions_handle_Multi_Nrows.py
Model_predictions_Multi_N_eval_profits.py
Utils/Utils_scoring.py
5_predict_POOL_enque_Thread.py
features_W3_old/v3.py
technical_indicators/talib_technical_class_object.py
```

---

## ایدهٔ اصلی Leci37

به جای regression قیمت یا score:

```text
OHLCV → technical patterns → Ground Truth عملیاتی → مدل‌های متعدد → threshold/ensemble → real-time alert
```

Target:

```text
buy_sell_point
0      = do nothing
100    = buy
-100   = sell
101/-101 = نقاط قوی‌تر
```

---

## چیزهایی که برای ShadBotTrader ارزش دارند

```text
- event-based ground truth
- POS/NEG binary models
- feature selection per side/per symbol
- class weighting برای imbalance
- threshold calibration
- ensemble/consensus بین چند مدل
- profit-aware evaluation
```

---

## چیزهایی که نباید مستقیم کپی شود

```text
- feature extraction خام؛ README هشدار داده بعضی indicators future data دارند
- SMOTETomek برای production time-series
- dependency stack قدیمی و سنگین
- فایل‌های private/missing مثل Declaration.py و realtime_model_POOL_driver.py
- Telegram/Twitter real-time code
```

---

## نتیجه تصمیم

برای ShadBotTrader:

```text
trend_score = research/secondary
trend_signal/event classification = مسیر اصلی‌تر
range model = براکت TP/SL و نقطهٔ قوت سیستم
```

اولویت بعدی:

```text
تقویت trend_signal با class weights، F1/PR-AUC، threshold calibration و feature selection
```
