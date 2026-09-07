# فاز ۱۰۵ — بررسی کد پروژهٔ Leci37 و نقشهٔ استفاده در ShadBotTrader

تاریخ: 2026-09-07  
Reference repo cloned at:

```text
/home/user/TensorFlow-stocks-prediction-Machine-learning-RealTime
```

Repo / commit inspected:

```text
https://github.com/Leci37/TensorFlow-stocks-prediction-Machine-learning-RealTime
commit: 7520351
```

> نکتهٔ حقوقی/عملی: README پروژه مجوز معمول MIT/Apache ندارد و صراحتاً می‌گوید استفاده و تغییر آزاد است، اما commercialization بدون اجازه ندارد و improvementهای major باید به author اطلاع داده شوند. پس پیشنهاد عملی این گزارش **کپی مستقیم کد** نیست؛ استفاده از ایده‌ها، متدولوژی و الگوهاست، مگر بعداً license دقیقاً بررسی/تأیید شود.

---

## 1) وضعیت واقعی پروژهٔ clone‌شده

### فایل‌های کلیدی دیده‌شده

```text
README.md
_KEYS_DICT.py
Tutorial/RUN_buy_sell_Tutorial_3W_5min_RT.py
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
Model_predictions_handle_Nrows.py
Model_predictions_Multi_N_eval_profits.py
Utils/Utils_scoring.py
5_predict_POOL_enque_Thread.py
features_W3_old/v3.py
technical_indicators/talib_technical_class_object.py
news_sentiment/*
Reinforcement_Learning/*
```

### محدودیت‌های مهم پروژهٔ Leci37

1. همهٔ کد لازم public نیست. README و کد به فایل‌های خصوصی/غایب اشاره می‌کنند:
   - `Declaration.py`
   - `realtime_model_POOL_driver.py`
   - branch خصوصی/غیرموجود `stocks-prediction-multi`
   - در tutorial هم import از `utilW3` دیده می‌شود که در repo فعلی به همین نام موجود نیست.
2. dependencyها قدیمی و سنگین‌اند:
   - Python 3.8 توصیه شده
   - `tensorflow-gpu~=2.10.1`
   - `pandas~=1.3.5`
   - `ta-lib`
   - `xgboost`, `imblearn`, `flair`, `transformers`, `selenium`, `mitmproxy`, ...
3. خود README هشدار داده بعضی indicators از future data استفاده می‌کنند.
4. بعضی بخش‌ها برای research/experiment هستند، نه production-grade Clean Architecture.

بنابراین برای ShadBotTrader باید **الگوها را استخراج کنیم**، نه اینکه ساختار پروژه را وارد production کنیم.

---

## 2) هستهٔ ایدهٔ پروژه Leci37

پروژهٔ Leci37 برخلاف مدل score ما، دنبال regression مستقیم نیست. فلسفهٔ اصلی:

```text
OHLCV → technical indicators → Ground Truth عملیاتی → مدل‌های متعدد → انتخاب مدل‌های قابل اعتماد → real-time alert فقط در confidence بالا
```

Target اصلی:

```text
buy_sell_point / buy_seel_point
0      = do nothing
100    = buy point
-100   = sell point
گاهی 101 / -101 برای نقاط قوی‌تر
```

این یعنی پروژه روی **event/action classification** بنا شده، نه پیش‌بینی عددی قیمت یا score آینده.

---

## 3) کدام بخش‌ها برای ما قابل استفاده‌اند؟

### 3.1 Ground Truth / target construction — بسیار مهم و قابل استفاده

فایل:

```text
Utils/Utils_buy_sell_points.py
```

متدهای کلیدی:

```python
get_buy_sell_points_Roll(df_stock, delete_aux_rows=True)
get_buy_sell_points_HT_pp(df_l, LEN_RIGHT, LEN_LEFT)
select_work_buy_or_sell_point(cleaned_df, opcion, Y_TARGET='buy_sell_point')
rolling_get_sell_price_POS_next_value(...)
rolling_get_sell_price_NEG_next_value(...)
check_buy_points_prediction(...)
```

#### ایدهٔ قابل استفاده

- به جای regression روی score کندل فردا، target را عملیاتی تعریف کنیم:

```text
BUY / SELL / HOLD
```

- روش `get_buy_sell_points_Roll` آیندهٔ محدود را بررسی می‌کند و بهترین rise/fallها را label می‌زند.
- روش `get_buy_sell_points_HT_pp` pivot high/low را با آیندهٔ محدود پیدا می‌کند.
- `select_work_buy_or_sell_point` مدل‌های POS و NEG جدا می‌سازد:
  - POS: buy true/false
  - NEG: sell true/false

#### استفادهٔ پیشنهادی در ShadBotTrader

ما نباید کد را مستقیم کپی کنیم، ولی باید targetهای زیر را بسازیم:

```text
1. event_atr_v1:
   برای هر کندل t، در horizon آینده اولین برخورد با +X×ATR یا -X×ATR:
   BUY / SELL / HOLD

2. event_quantile_v1:
   مشابه Leci37، top N% حرکت‌های مثبت و top N% حرکت‌های منفی آینده را label بزنیم.
   برای طلا می‌تواند روی 5M/15M/1H تست شود.

3. event_pivot_v1:
   pivot low = BUY candidate، pivot high = SELL candidate.
   فقط برای training label مجاز است، نه feature live.
```

در پروژهٔ ما نزدیک‌ترین پایهٔ فعلی:

```text
src/ShadBotTrader/infrastructure/ai/target_builder.py
build_trend_signal_labels(...)
```

پس بهترین مسیر: **تقویت trend_signal**، نه ادامه دادن به score regression.

---

### 3.2 Feature selection — قابل استفاده با بازنویسی تمیز

فایل‌ها:

```text
Feature_selection_create_json.py
Feature_selection_json_columns.py
```

متدهای کلیدی:

```python
get_best_columns_to_train(...)
generate_json_best_columns(...)
get_json_feature_selection(...)
JsonColumns(...)
```

روش‌های feature ranking در Leci37:

```text
SelectKBest chi2
SelectKBest f_regression
ExtraTreesClassifier.feature_importances_
corrwith(Y_TARGET)
```

همچنین در README پیشنهاد کرده:

```text
Remove columns with correlation > 0.9
```

#### استفادهٔ پیشنهادی در ShadBotTrader

در پروژهٔ ما feature catalogue فعلاً عمومی است. باید یک لایهٔ اختیاری feature selection اضافه شود:

```text
FeatureMatrix → FeatureSelector → SelectedFeatureMatrix → Trainer
```

بدون redesign، فقط به عنوان گزینهٔ train:

```text
--feature-select none|corr|tree|mutual_info|hybrid
--top-features 16|32|64|128
--max-feature-corr 0.90
```

خروجی باید همراه model ذخیره شود:

```json
"selected_features": [...],
"feature_selection_method": "hybrid",
"feature_selection_fit_range": "train_only"
```

نکتهٔ حیاتی: feature selection باید فقط روی train fold/prefix انجام شود، نه کل history؛ وگرنه leakage انتخاب feature داریم.

---

### 3.3 POS/NEG binary models — برای طلا ارزشمند

در Leci37 مدل‌ها معمولاً binary هستند:

```text
POS model: آیا buy point هست؟
NEG model: آیا sell point هست؟
```

فایل‌ها:

```text
Utils/Utils_buy_sell_points.py -> select_work_buy_or_sell_point
3_Model_creation_models_for_a_stock.py -> train_MULTI_model_with_custom_columns
```

#### استفادهٔ پیشنهادی در ShadBotTrader

ما الان `trend_signal` سه‌کلاسه داریم:

```text
SELL / HOLD / BUY
```

اما برای imbalance شدید، دو مدل binary گاهی بهتر است:

```text
gold_buy_event_5m:  BUY vs NOT_BUY
gold_sell_event_5m: SELL vs NOT_SELL
```

سپس تصمیم:

```text
اگر buy_prob بالا و sell_prob پایین → BUY candidate
اگر sell_prob بالا و buy_prob پایین → SELL candidate
اگر هر دو بالا → volatility/ambiguous → no trade
اگر هر دو پایین → HOLD
```

این دقیقاً شبیه منطق Leci37 است که POS/NEG جدا دارد و اگر هر دو strong باشند، volatility/ambiguous تلقی می‌شود.

---

### 3.4 Multi-dimensional windows — ما نسخهٔ تمیزترش را داریم

فایل‌ها:

```text
Data_multidimension.py
Utils/Utils_model_predict.py
```

متدها:

```python
df_to_df_multidimension_array_2D(...)
df_to_df_multidimension_array_3D(...)
scaler_split_TF_onbalance(...)
Data_multidimension.load_split_data_multidimension(...)
```

در Leci37:

```text
BACHT_SIZE_LOOKBACK = 10
هر sample شامل چند ردیف گذشته است.
```

ما در ShadBotTrader همین ایده را بهتر داریم:

```text
window_size=150 یا 288
WaveNet / causal window
WindowGenerator streamed
purged roll-forward
```

#### استفادهٔ پیشنهادی

کد windowing آن‌ها را استفاده نکنیم؛ اما ایدهٔ **چند تایم‌فریم** مهم است:

```text
5M + 15M + 1H + 4H + 1D context
```

راه تمیز در ShadBotTrader:

```text
نه چسباندن خام dataframe؛
بلکه FeatureCatalogue/FeatureMatrix چندتایم‌فریم با alignment علّی.
```

در فاز اول لازم نیست چندتایم‌فریم را اضافه کنیم. اول target/metrics/selection را درست کنیم.

---

### 3.5 Class imbalance handling — بسیار قابل استفاده

فایل‌ها:

```text
Tutorial/RUN_buy_sell_Tutorial_3W_5min_RT.py
Model_train_TF_onBalance.py
Model_train_TF_multi_onBalance.py
Utils/Utils_model_predict.py
```

روش‌ها:

```python
compute_class_weight('balanced', ...)
class_weight=dict_class_weight در model.fit
get_resampled_ds_onBalance(...)
SMOTETomek فقط روی train
initial_bias = log(pos / neg)
```

#### استفادهٔ پیشنهادی در ShadBotTrader

برای `trend_signal` حتماً باید اضافه شود:

```text
class_weight برای SELL/HOLD/BUY
یا focal loss برای کلاس‌های کم‌نمونه
یا sample_weight در tf.data
```

اما SMOTETomek برای time-series خطرناک است؛ چون synthetic sample می‌سازد و ساختار زمانی را خراب می‌کند. برای ما بهتر:

```text
class_weight / focal loss / threshold tuning
```

نه SMOTE.

---

### 3.6 Metrics — باید حتماً استفاده شود

فایل‌ها:

```text
Tutorial/RUN_buy_sell_Tutorial_3W_5min_RT.py -> get_metrics
Utils/Utils_model_predict.py -> METRICS_ALL
```

Metrics مورد استفاده:

```text
BinaryAccuracy
Precision
Recall
AUC
PR-AUC
```

README هم صریحاً F1-score را برای imbalance پیشنهاد کرده.

#### استفادهٔ پیشنهادی در ShadBotTrader

برای trend_signal باید فقط accuracy را کنار بگذاریم و این‌ها را ذخیره کنیم:

```text
val_precision_sell
val_recall_sell
val_f1_sell
val_precision_buy
val_recall_buy
val_f1_buy
macro_f1
balanced_accuracy
PR-AUC BUY
PR-AUC SELL
confusion matrix
```

و مدل را نه صرفاً با `val_loss` یا `val_accuracy`، بلکه با یکی از این‌ها انتخاب کنیم:

```text
monitor = val_macro_f1
یا monitor = expected_value / profit metric
```

---

### 3.7 Model zoo / ensemble — ایدهٔ قابل استفاده، نه کد مستقیم

فایل‌ها:

```text
Model_TF_definitions.py
3_Model_creation_models_for_a_stock.py
4_Model_creation_scoring_multi.py
Utils/Utils_scoring.py
```

مدل‌های Leci37:

```text
SIMP_DENSE28
SIMP_DENSE64
SIMP_DENSE128
SIMP_CONV
SIMP_CONV2
SIMP_CORDO / LSTM stack
MULT_LINEAR
MULT_DENSE2
MULT_LSTM
MULT_GRU
RandomForest
XGBoost
GradientBoostingRegressor
```

برای هر stock چند نوع feature subset دارد:

```text
_vgood16_
_good9_
_reg4_
_low1_
```

و برای هر سمت:

```text
pos
neg
```

#### استفادهٔ پیشنهادی در ShadBotTrader

ما نباید همهٔ معماری‌هایشان را کپی کنیم. اولویت ما:

```text
1. حفظ WaveNet فعلی برای baseline
2. train چند variant با feature subsetهای مختلف
3. اگر لازم شد اضافه‌کردن مدل MLP ساده و/یا TCN کوچک به عنوان optional model family
4. فقط بعد از اثبات، RandomForest/XGBoost optional اضافه شود
```

مدل‌هایی که مستقیم برای ما جذاب‌اند:

```text
- Binary POS/NEG classifiers
- Dense 64/128 روی windows flattened یا last timestep as baseline
- GRU/LSTM فقط به عنوان benchmark، نه ستون اصلی
- Tree models برای feature importance، نه الزاماً live trading
```

---

### 3.8 Threshold scoring / percentile gates — بسیار مفید

فایل‌ها:

```text
Model_train_TF_multi_onBalance.py
Model_predictions_handle_Multi_Nrows.py
Model_predictions_handle.py
Utils/Utils_scoring.py
```

الگو:

1. خروجی مدل روی test/validation گرفته می‌شود.
2. distribution خروجی مدل با percentileها محاسبه می‌شود:

```text
25%, 50%, 60%, 70%, ..., 93%, 94%, 95%, 96%, 97%, 98%
```

3. برای هر percentile بررسی می‌شود وقتی model score از آن threshold بالاتر است، چند تا درست بوده:

```text
per_acert
predict_
acert_
```

4. در real-time اگر خروجی مدل از threshold قوی مثل 93% عبور کند، alert candidate می‌شود.

#### استفادهٔ پیشنهادی در ShadBotTrader

برای `trend_signal` باید به جای threshold ثابت 60%، thresholdهای calibration بسازیم:

```text
BUY threshold = quantile/probability threshold که precision را در validation بیشینه می‌کند
SELL threshold = جداگانه
HOLD threshold یا ambiguity gate
```

و در model record ذخیره کنیم:

```json
"decision_thresholds": {
  "buy_prob": 0.73,
  "sell_prob": 0.71,
  "min_margin_vs_hold": 0.12,
  "min_margin_vs_opposite": 0.18
}
```

---

### 3.9 Profit-aware evaluation — بسیار مهم

فایل‌ها:

```text
Model_predictions_Multi_N_eval_profits.py
Model_predictions_handle.py -> how_much_each_entry_point_earns
Utils/Utils_scoring.py
```

ایدهٔ اصلی:

```text
مدل فقط با accuracy انتخاب نمی‌شود؛ بررسی می‌شود اگر نقاط انتخابی trade شوند، سود/واحد چقدر است.
```

#### استفادهٔ پیشنهادی در ShadBotTrader

ما باید evaluation را به Triple Strategy وصل کنیم:

```text
model output → entry candidate → range bracket TP/SL → spread/slippage → trade result
```

Metrics نهایی:

```text
expectancy
profit factor
net return
max drawdown
win rate
trades count
avg R
precision BUY/SELL
false positive cost
session-specific result
```

---

### 3.10 Real-time producer/consumer — ایده قابل استفاده، نه کد

فایل:

```text
5_predict_POOL_enque_Thread.py
```

الگو:

```text
Producer: OHLCV real-time را جمع می‌کند و queue می‌گذارد.
Consumer: فیچر می‌سازد، مدل‌ها را predict می‌کند، result ثبت می‌کند، alert می‌فرستد.
```

#### برای ShadBotTrader

ما live loop و dashboard داریم؛ نیازی به thread architecture آن‌ها نداریم. اما یک ایده مهم است:

```text
هر alert/trade باید همراه با snapshot کامل مدل‌ها و scoreها ثبت شود.
```

برای ما:

```text
run_logs/live_decisions.jsonl
یا shadbot.db decision_audit table
```

---

### 3.11 News sentiment / fundamentals — برای طلا باید متفاوت پیاده شود

فایل‌ها:

```text
news_sentiment/news_get_data_NUTS.py
news_sentiment/news_sentiment_va_and_txtBlod.py
news_sentiment/news_sentiment_flair.py
news_sentiment/news_sentiment_t5.py
```

برای stock مفید است، اما برای XAUUSD بهتر است به جای stock news:

```text
DXY
US10Y yield
real yields
VIX
CPI/FOMC/NFP calendar
session/time-of-day
day-of-week
```

این همان چیزی است که برای score/trend احتمالاً edge می‌آورد.

---

## 4) چه چیزهایی را مستقیم استفاده نکنیم؟

### 4.1 کپی مستقیم feature extraction

مسیر:

```text
features_W3_old/v3.py
technical_indicators/*
```

چرا نه؟

```text
- خودش هشدار داده بعضی indicators future data می‌گیرند.
- dependency سنگین TA-Lib/pandas-ta/py_ti دارد.
- ShadBotTrader خودش causality audit و feature catalogue دارد.
```

پس فقط feature ideaها را بررسی کنیم، نه کد خام.

### 4.2 SMOTETomek برای time-series

مسیر:

```text
Utils/Utils_model_predict.prepare_to_split_SMOTETomek_01
Data_multidimension.load_split_data_multidimension
```

مشکل:

```text
SMOTE synthetic sample می‌سازد و ممکن است structure زمانی را خراب کند.
```

برای ما class_weight/focal loss امن‌تر است.

### 4.3 split با shuffle=True

در `Data_multidimension`:

```python
will_shuffle = True
train_test_split(..., shuffle=True)
```

برای trading time-series این خطرناک است. ما باید roll-forward/purge را نگه داریم.

### 4.4 old dependencies

کپی dependency stack آن‌ها پروژه را می‌شکند. ما نباید Python 3.8/TensorFlow 2.10/TA-Lib را وارد core کنیم.

### 4.5 real-time Telegram/Twitter implementation

از نظر architecture با ShadBotTrader فرق دارد؛ فقط ایدهٔ alert audit/threshold useful است.

---

## 5) نقشهٔ کامل تغییرات پیشنهادی برای ShadBotTrader

### هدف کلان

از این مسیر:

```text
trend_score regression → تلاش برای پیش‌بینی عدد score فردا
```

به این مسیر عملیاتی برویم:

```text
event-based trend_signal / POS-NEG classifiers / feature selection / ensemble / profit-aware validation
```

بدون redesign، با توسعهٔ همان Clean Architecture.

---

## Phase 106 — ارزیابی و قفل‌کردن integrity قبل از مدل جدید

### کارها

1. برای `trend_signal` یک audit script مثل `evaluate_trend_score_1d.py` بسازیم:

```text
scripts/evaluate_trend_signal_5m.py
```

2. این‌ها را گزارش کند:

```text
label distribution: SELL/HOLD/BUY
train/val distribution per fold
ambiguous samples count
barrier distance stats
first-hit distance stats
baseline: always HOLD / dominant class
```

3. metricهای classification را اضافه کند:

```text
confusion matrix
precision/recall/F1 per class
macro-F1
balanced accuracy
```

### فایل‌های درگیر

```text
src/ShadBotTrader/infrastructure/ai/target_builder.py
scripts/evaluate_trend_signal_5m.py
scripts/run_dual_models.py
```

### خروجی مورد انتظار

قبل از training بدانیم target سالم است یا نه.

---

## Phase 107 — Class weights و F1 برای trend_signal

### کارها

1. `WavenetTrainer` برای classification class_weight یا sample_weight بگیرد.
2. وزن‌ها per fold و فقط از train labels حساب شوند.
3. برای 3-class:

```text
SELL / HOLD / BUY
```

وزن‌ها طوری باشند که BUY/SELL زیر اکثریت HOLD دفن نشوند.

4. metricهای زیر ذخیره شوند:

```text
val_sell_precision
val_sell_recall
val_sell_f1
val_hold_precision
val_hold_recall
val_hold_f1
val_buy_precision
val_buy_recall
val_buy_f1
val_macro_f1
val_balanced_accuracy
```

5. برای `trend_signal` monitor پیش‌فرض شود:

```text
val_macro_f1 یا val_buy_sell_f1
```

نه صرفاً `val_loss`.

### فایل‌های درگیر

```text
src/ShadBotTrader/infrastructure/ai/wavenet/wavenet_trainer.py
src/ShadBotTrader/application/services/dual_model_service.py
scripts/run_dual_models.py
src/ShadBotTrader/infrastructure/ai/training_progress.py
```

---

## Phase 108 — Feature selection role-specific

### کارها

1. یک سرویس جدید در infrastructure AI:

```text
src/ShadBotTrader/infrastructure/ai/feature_selection.py
```

2. روش‌ها:

```text
correlation_to_target
mutual_info_classif optional
tree_importance optional
remove_pairwise_corr_gt_0_90
hybrid_vote
```

3. فقط روی train prefix/fold fit شود.
4. خروجی:

```text
selected_feature_names
removed_correlated_features
selection_scores
```

5. به `run_dual_models.py` فلگ اضافه شود:

```text
--feature-select none|corr|hybrid
--top-features 16|32|64|128
--max-feature-corr 0.90
```

### نکته معماری

این تغییر redesign نیست؛ فقط یک transformation بین FeatureMatrix و Trainer است.

---

## Phase 109 — POS/NEG binary event models

### کارها

1. دو model role اضافه شود:

```text
gold_buy_event_5m
gold_sell_event_5m
```

یا اگر نخواهیم role جدید زیاد شود، داخل `trend_signal` یک option اضافه کنیم:

```text
--event-mode multiclass|pos|neg
```

2. Target binary:

```text
BUY_EVENT = 1 اگر BUY first-passage / pivot low / quantile up
NOT_BUY = 0 بقیه

SELL_EVENT = 1 اگر SELL first-passage / pivot high / quantile down
NOT_SELL = 0 بقیه
```

3. output:

```text
Dense(1, sigmoid)
loss: binary_crossentropy or focal
metrics: precision/recall/F1/PR-AUC
```

4. decision logic:

```text
if buy_prob >= buy_threshold and sell_prob < sell_block_threshold → BUY
if sell_prob >= sell_threshold and buy_prob < buy_block_threshold → SELL
if both high → ambiguous/no-trade
else HOLD
```

### چرا مهم است؟

برای imbalance، binary POS/NEG معمولاً بهتر از یک softmax سه‌کلاسه یاد می‌گیرد.

---

## Phase 110 — Threshold calibration شبیه Leci37

### کارها

برای هر مدل بعد از training:

1. روی validation predictions بگیر.
2. برای هر کلاس و هر threshold:

```text
precision
recall
F1
trades count
expected value if traded
```

3. threshold مناسب را انتخاب و ذخیره کن:

```json
"decision_thresholds": {
  "buy": 0.74,
  "sell": 0.72,
  "min_trades": 50,
  "selected_by": "max_profit_factor_with_precision_floor"
}
```

### فایل‌های درگیر

```text
src/ShadBotTrader/application/services/model_evaluation_service.py
scripts/evaluate_trend_signal_5m.py
src/ShadBotTrader/infrastructure/ai/model_catalogue.py
```

---

## Phase 111 — Ensemble / consensus gate در backtest

### کارها

1. Triple strategy را به این مجوزها مجهز کنیم:

```text
License 1: 5M signal model probability
License 2: range slope 1D
License 3: TP side
License 4: entry proximity to daily level
License 5: trend color
License 6: trend_signal or POS/NEG event model
License 7: consensus gate / no ambiguous
```

2. مدل‌های event چندگانه را ترکیب کنیم:

```text
trend_signal_5m
buy_event_5m
sell_event_5m
trend_1d
range_4h bracket
session filter
EMA/regime filter
```

3. منطق no-trade را سخت‌گیر کنیم:

```text
اگر disagreement → no trade
اگر both buy/sell high → no trade
اگر confidence پایین → no trade
```

### فایل‌های درگیر

```text
src/ShadBotTrader/application/services/dual_model_backtest_service.py
src/ShadBotTrader/infrastructure/simulation/dual_model_prediction_source.py
src/ShadBotTrader/domain/simulation/strategy/rules or equivalent
```

---

## Phase 112 — Profit-aware model selection

### کارها

برای هر candidate model/threshold:

```text
run backtest on validation period
record trades
calculate expectancy/profit factor/max drawdown
select top models
```

خروجی مشابه Leci37:

```text
run_logs/model_selection_profit.csv
run_logs/model_selection_thresholds.json
```

ولی با معیارهای ما:

```text
spread 0.06%
slippage
session
TP/SL from range_4h
same-bar policy
```

---

## Phase 113 — Regime features برای XAUUSD

Leci37 برای stocks news/fundamentals پیشنهاد می‌دهد. برای gold بهتر:

```text
DXY trend
US10Y yield
real yield proxy
VIX
FOMC/CPI/NFP calendar flag
London/NY session
day of week
weekly position / close location
volatility regime
```

بدون این‌ها، جهت روزانهٔ طلا از price-only features خیلی سخت است.

---

## 6) اولویت اجرایی پیشنهادی

### اولویت 1 — همین الان ارزشمندترین

```text
trend_signal را با class weights + F1 + threshold calibration جدی کنیم.
```

دلیل:

```text
به فلسفهٔ Leci37 نزدیک است و در معماری فعلی ما تقریباً آماده است.
```

### اولویت 2

```text
feature selection برای trend_signal و trend_score
```

دلیل:

```text
شاید همهٔ 180 فیچر برای جهت مفید نیستند و redundancy/noise زیاد است.
```

### اولویت 3

```text
POS/NEG binary event models
```

دلیل:

```text
برای imbalance و no-trade زیاد، binary side-specific مدل‌ها می‌توانند بهتر از softmax یاد بگیرند.
```

### اولویت 4

```text
ensemble/consensus gate در backtest
```

دلیل:

```text
edge احتمالاً از ترکیب فیلترها می‌آید، نه از یک مدل تنها.
```

---

## 7) دقیقاً کدام کدهای Leci37 را به عنوان reference نگه داریم؟

| کاربرد | فایل/متد Leci37 | استفاده برای ما |
|---|---|---|
| ساخت GT event | `Utils/Utils_buy_sell_points.py::get_buy_sell_points_Roll` | ایدهٔ event/quantile label؛ بازنویسی در `target_builder.py` |
| pivot target | `get_buy_sell_points_HT_pp` | ایدهٔ pivot high/low label؛ با تست leakage فقط target، نه feature |
| POS/NEG split | `select_work_buy_or_sell_point` | مدل‌های buy_event/sell_event یا mode در trend_signal |
| feature ranking | `Feature_selection_create_json.py` | ساخت `feature_selection.py` با train-only fit |
| ذخیره scaler | `scaler_min_max_array(... path_to_save/load)` | ما `input_scale_range` را داریم؛ در feature selector هم metadata ذخیره شود |
| class imbalance | `compute_class_weight`, `get_resampled_ds_onBalance` | class_weight/focal؛ نه SMOTE در production |
| metrics | `get_metrics`, `METRICS_ALL` | precision/recall/F1/PR-AUC برای trend_signal |
| model zoo | `Model_TF_definitions.py` | فقط برای benchmark؛ core ما WaveNet بماند |
| threshold scoring | `__manage_get_per_results_stadistic_from_predit_result`, `fill_df_eval_r_with_values` | threshold calibration per class |
| model selection | `Utils_scoring.get_models_Multi_not_bads` | انتخاب مدل بر اساس spread/std/precision/profit، ولی با معیارهای خودمان |
| profit eval | `how_much_each_entry_point_earns` | اتصال مدل به backtest واقعی ما با spread/TP/SL |
| real-time queue | `5_predict_POOL_enque_Thread.py` | ایدهٔ audit/log/alert، نه کپی معماری |

---

## 8) حکم نهایی

پروژهٔ Leci37 برای ما بیشتر یک پیام دارد:

```text
score regression را مرکز پروژه نکن.
trade event classification + no-trade + threshold + ensemble را مرکز کن.
```

مسیر پیشنهادی واقعی برای ShadBotTrader:

```text
1. trend_score بماند research/secondary.
2. trend_signal_5m را با class weights و F1 اصلاح کن.
3. feature selection و threshold calibration اضافه کن.
4. POS/NEG binary event models را تست کن.
5. خروجی را فقط با profit-aware backtest قبول کن.
6. consensus gate را به triple strategy وصل کن.
```

این تغییرها با معماری فعلی قابل انجام‌اند و نیاز به redesign ندارند، اما باید مرحله‌ای و با quality gate انجام شوند.
