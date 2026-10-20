# فاز ۱۰۵ — خلاصهٔ بررسی پروژهٔ Leci37 و تصمیم استفاده در ShadBotTrader

تاریخ: 2026-09-07

Repo مرجع:

```text
https://github.com/Leci37/TensorFlow-stocks-prediction-Machine-learning-RealTime
commit inspected: 7520351
```

این فایل برای رفع reference مستندات و نگه‌داشتن خلاصهٔ تصمیم فنی نوشته شد. Clone کامل پروژهٔ Leci37 بعد از استخراج نکات، برای خلوت‌کردن workspace حذف شد.

---

## نکات اصلی استخراج‌شده

### 1) Target عملیاتی به جای regression قیمت/score

پروژهٔ Leci37 روی ستون زیر بنا شده است:

```text
buy_sell_point / buy_seel_point
0      = do nothing
100    = buy point
-100   = sell point
101    = buy قوی‌تر
-101   = sell قوی‌تر
```

این برای ShadBotTrader یعنی مسیر `trend_signal`/event-classification مهم‌تر از `trend_score` regression است.

### 2) متدهای مهم در پروژهٔ Leci37

```text
Utils/Utils_buy_sell_points.py
  get_buy_sell_points_Roll
  get_buy_sell_points_HT_pp
  select_work_buy_or_sell_point
  rolling_get_sell_price_POS_next_value
  rolling_get_sell_price_NEG_next_value

Feature_selection_create_json.py
  get_best_columns_to_train
  generate_json_best_columns
  get_json_feature_selection

Utils/Utils_model_predict.py
  scaler_min_max_array
  scaler_split_TF_onbalance
  get_resampled_ds_onBalance

Model_TF_definitions.py
  get_dicts_models_multi_dimension
  get_dicts_models_One_dimension

Utils/Utils_scoring.py
  get_models_Multi_not_bads
```

### 3) ایده‌های قابل استفاده

```text
- event-based ground truth
- POS/NEG binary models
- feature selection per side/per model
- class weighting برای imbalance
- threshold calibration با percentileهای model score
- ensemble/consensus بین چند مدل
- profit-aware evaluation به جای accuracy تنها
```

### 4) چیزهایی که نباید مستقیم کپی شود

```text
- feature extraction خام، چون خود README هشدار داده بعضی indicators future data دارند
- SMOTETomek برای time-series production
- dependency stack قدیمی و سنگین
- real-time Telegram/Twitter code
- فایل‌های private/missing مثل Declaration.py و realtime_model_POOL_driver.py
```

---

## تصمیم برای ShadBotTrader

مسیر پیشنهادی:

```text
1. trend_score بماند research/secondary.
2. trend_signal محور شود.
3. class weights + F1/PR-AUC اضافه شود.
4. feature selection train-only اضافه شود.
5. POS/NEG binary event models تست شود.
6. consensus gate و profit-aware backtest معیار نهایی باشند.
```

این تصمیم با فاز ۱۰۶ هم‌راستاست و بدون redesign روی معماری فعلی قابل اجراست.
