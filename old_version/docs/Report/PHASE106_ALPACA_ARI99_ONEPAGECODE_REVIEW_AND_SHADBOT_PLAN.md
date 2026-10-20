# فاز ۱۰۶ — بررسی منابع Alpaca / ari99 / Onepagecode و نقشهٔ استفاده در ShadBotTrader

تاریخ: 2026-09-07  
درخواست: بررسی دقیق منابع معرفی‌شده، آوردن کد لازم به workspace، ثبت اطلاعات لازم در Docs، و خلوت‌کردن workspace بعد از استخراج اطلاعات.

---

## 0) وضعیت workspace و منابع

### منابع بررسی‌شده

1. Alpaca article:
   ```text
   https://alpaca.markets/learn/tensorflow-market-forecasting
   ```
2. GitHub repo:
   ```text
   https://github.com/ari99/algorithmic_trading
   ```
3. Onepagecode/Substack:
   ```text
   https://onepagecode.substack.com/p/an-algo-trading-framework-using-tensorflow
   ```

### کدی که برای بررسی وارد workspace شد

Repo زیر موقتاً clone شد و کد آن بررسی شد:

```text
/home/user/algorithmic_trading
commit: c8479f3
```

بعد از استخراج نکات، برای خلوت نگه داشتن workspace، clone کامل حذف شد؛ اطلاعات لازم در همین گزارش ثبت شده است.

### نکتهٔ حقوقی/فنی

- repo `ari99/algorithmic_trading` در بررسی workspace فاقد license روشن بود و به `vectorbtpro` وابسته است؛ بنابراین **کپی مستقیم کد به ShadBotTrader توصیه نمی‌شود**.
- مقاله Alpaca آموزشی و مبتنی بر TensorFlow 1 style است.
- مقاله Onepagecode فقط snippets public داشت؛ source کامل پشت paywall/subscription بود.

---

## 1) بررسی Alpaca — `tensorflow-market-forecasting`

### 1.1 هدف مقاله

مقاله یک baseline آموزشی می‌سازد برای سؤال زیر:

```text
آیا می‌شود با چند اندیکاتور تکنیکال و TensorFlow جهت روز بعد بازار را پیش‌بینی کرد؟
```

خود مقاله نتیجه را بسیار محتاطانه می‌داند و می‌گوید نتایج «less than spectacular» هستند.

---

### 1.2 Target / label

مسئله به صورت binary classification تعریف شده:

```text
longOutput  = 1 اگر close[t+lookahead] - close[t] >= 0
shortOutput = 1 اگر close[t+lookahead] - close[t] < 0
```

پارامتر:

```text
targetLookaheadPeriod = 1
```

یعنی پیش‌بینی جهت close روز بعد.

### ارزیابی برای ما

این از نظر فلسفه شبیه مدل زیر در ShadBotTrader است:

```text
gold_trend_1d
```

نه `trend_score`. اما target آن خام است، چون no-trade، spread، ATR barrier، TP/SL یا magnitude ندارد. برای ShadBotTrader بهتر است target عملیاتی‌تر باشد:

```text
first hit +X*ATR → BUY
first hit -X*ATR → SELL
none → HOLD
```

یعنی همان مسیر `trend_signal`.

---

### 1.3 Featureها

مقاله فقط 4 feature دارد:

```text
RSI14
RSI50
STOCH14K
STOCH14D
```

دلیل انتخاب:

```text
این‌ها ذاتاً بین 0 و 100 normalized هستند و price level را حذف می‌کنند.
```

نکتهٔ مهم مقاله:

```text
برای generalization بین چند symbol، featureها باید normalized یا price/volatility-normalized باشند.
```

### استفاده برای ShadBotTrader

ما در فاز ۱۰۴ scale مدل score را `[-1,+1]` کردیم و raw priceها را relative نگه می‌داریم. اما برای مدل‌های جهت باید audit جدا انجام شود:

```text
هیچ absolute price level نباید وارد مدل‌های جهت شود، مگر عمداً و با normalization.
```

---

### 1.4 Dataset generation

مقاله:

```text
S&P 500 daily candles since 2015
train: 2015-01-01 تا 2017-06-01
eval : 2017-06-01 تا 2018-06-01
```

فایل‌ها را جدا می‌سازد:

```text
./train/{symbol}.csv
./eval/{symbol}.csv
```

مزیت:

```text
Data generation از training جداست.
```

ما این separation را با `datasets/processed`, feature cache و model artifacts داریم.

---

### 1.5 معماری مدل Alpaca

تنظیمات:

```text
trainingCycles = 500000
batchSize = 1000
summarySteps = 1000
dropout = 0.5
nodeLayout = [40, 30, 20, 10]
```

معماری:

```text
Input 4
Dense 40 tanh + dropout
Dense 30 tanh + dropout
Dense 20 tanh + dropout
Dense 10 tanh + dropout
Dense 2 softmax
```

Loss:

```text
softmax_cross_entropy_with_logits_v2
```

Optimizer:

```text
AdamOptimizer(0.0001)
```

Metric:

```text
accuracy
```

### نکتهٔ کدنویسی مهم

در script مقاله `softmax` روی خروجی اعمال شده و همان خروجی به `softmax_cross_entropy_with_logits_v2` داده شده است. در طراحی صحیح، یا باید logits خام به cross entropy داده شود یا اگر output softmax است از categorical crossentropy مناسب استفاده شود. پس کد مقاله را نباید مستقیم کپی کرد.

---

### 1.6 نتیجهٔ آموزش در مقاله

سه اندازه مدل تست شده:

```text
[40,30,20,10]
[80,60,40,20]
[160,120,80,40]
```

نتیجه:

```text
overfitting واضح
شبکه‌های بزرگ‌تر سریع‌تر از evaluation منحرف شدند
train accuracy فقط چند درصد بالاتر از random بود
```

این نتیجه با تجربهٔ ما دربارهٔ `trend_score` سازگار است: اگر target جهت روزانه noise-heavy باشد، مدل بزرگ‌تر الزاماً edge نمی‌سازد.

---

### 1.7 پیشنهادهای مقاله که برای ما ارزش دارد

```text
1. featureهای بیشتر ولی normalized اضافه شود.
2. به جای یک نقطه، آخرین N period به مدل داده شود.
3. neutral class اضافه شود.
4. threshold label با median/volatility تنظیم شود.
5. lookaheadهای مختلف تست شود.
6. ML فقط complementary indicator باشد، نه تصمیم‌گیرنده تنها.
```

برای ما:

```text
trend_signal + HOLD + ATR barrier + threshold calibration
```

از direction خام بهتر است.

---

## 2) بررسی Onepagecode/Substack

### 2.1 وضعیت دسترسی

مقاله بخشی از کد را public نشان می‌دهد، اما source کامل پشت paywall است. بنابراین فقط snippets قابل مشاهده بررسی شد.

فایل‌های معرفی‌شده:

```text
constants.py
evaluate_neural_network.py
fetch_combined_data.py
fetch_indicators.py
fetch_stock.py
neural_network.py
plot.py
preprocess.py
run.py
```

---

### 2.2 Pipeline کلی

```text
Alpha Vantage API
→ fetch stock data
→ fetch technical indicators
→ merge by date
→ fill missing
→ construct next-day adjusted-close label
→ chronological split
→ MinMaxScaler fit on train only
→ MLP regression
→ MSE / relative error evaluation
```

---

### 2.3 fetch modules

`fetch_stock.py`:

```text
TIME_SERIES_DAILY_ADJUSTED از Alpha Vantage
JSON → DataFrame transpose
clean column names مثل "1. open" → "open"
```

`fetch_indicators.py`:

```text
indicator function + symbol + interval + time_period + series_type
```

`fetch_combined_data.py`:

```text
stock data + همه indicators
outer merge on date
save CSV per symbol
rate limit با sleep(1)
```

### استفاده برای ما

برای XAUUSD منبع اصلی MT5/Alpari است، اما همین الگو برای external/regime features مفید است:

```text
DXY, US10Y, VIX, calendar flags
```

باید با provider interface خودمان پیاده شود، نه hardcoded API key.

---

### 2.4 preprocessing

`fill_missing`:

```text
ffill → bfill → fill 0
```

`construct_label`:

```text
label = adjusted close shifted -1
last row dropped
```

`split`:

```text
chronological split
```

`scale`:

```text
MinMaxScaler فقط روی train fit می‌شود
همان scaler روی test transform می‌شود
```

### درس برای ShadBotTrader

برای window-based neural network فعلی، per-window scaling داریم. اما اگر مدل tabular/MLP/tree یا feature selection اضافه شود، باید حتماً scaler روی train fit شود و به test/live فقط transform بخورد.

---

### 2.5 neural_network.py

معماری public snippet:

```text
Input p
Dense 64 ReLU
Dense 32 ReLU
Dense 16 ReLU
Dense 1 output
```

Loss:

```text
MSE
```

Optimizer:

```text
Adam
```

Training:

```text
epochs = 20
batch_size = 1
shuffle train هر epoch
```

Evaluation:

```text
MSE
relative error
```

### ارزیابی برای ما

این regression قیمت آینده است؛ برای trading XAUUSD مسیر مناسبی نیست. اما MLP ساده می‌تواند فقط به عنوان benchmark برای event classification استفاده شود، نه price regression.

---

## 3) بررسی repo ari99/algorithmic_trading

### 3.1 ساختار repo

فولدرها:

```text
1_download_data
2_data_prepare
3_make_model/rnn
4_test_model
5_model_ml_stats
6_model_bt_stats
common
configs
```

README/Wiki ادعا می‌کند پروژه شامل:

```text
historical data download
feature engineering
model building
performance verification
paper trading with Alpaca
```

وابستگی مهم:

```text
vectorbtpro
Polygon
Alpaca
TensorFlow
AWS Sagemaker
```

---

### 3.2 download/checkpoint

فایل‌ها:

```text
common/polygonDownloader.py
common/checkpointHandler.py
1_download_data/services/cleanDataHandler.py
```

الگو:

```text
اگر HDF/Numpy checkpoint موجود است → load
اگر نیست → create و save
```

برای ما کد مستقیم لازم نیست؛ ShadBotTrader خودش Parquet/model artifact store دارد.

---

### 3.3 flipped data

فایل:

```text
1_download_data/services/flipBarData.py
```

ایده:

```text
مسیر قیمت را با diffهای معکوس آینه می‌کند.
```

کاربرد پیشنهادی برای ما:

```text
robustness test: آیا مدل فقط long-bias/short-bias یاد گرفته؟
```

نه training augmentation پیش‌فرض.

---

### 3.4 feature engineering

فایل:

```text
common/featuresTargetsUnshiftedMaker.py
```

ویژگی‌ها:

```text
TA-Lib indicators via vectorbtpro
WorldQuant Alpha 101 (WQA101) برای بیشتر alphaها
حذف exp/cosh/sinh به خاطر inf
```

WQAهای حذف‌شده:

```text
48, 58, 59, 63, 67, 69, 70, 76, 79, 80, 82, 84, 87, 89, 90, 91, 93, 97, 100
```

### برای ما

ایدهٔ WQA/alpha features جالب است، ولی مستقیم قابل ورود نیست:

```text
vectorbtpro proprietary است
هر alpha باید causality/stationarity audit شود
```

---

### 3.5 labels / targets

فایل‌ها:

```text
common/featuresTargetsUnshiftedMaker.py
common/labelMaker.py
```

periods:

```text
10, 20, 50, 100
```

target columns:

```text
longEntry10 / shortEntry10
longEntry20 / shortEntry20
longEntry50 / shortEntry50
longEntry100 / shortEntry100
```

منطق:

```text
در هر block با طول period، idxmin و idxmax close محاسبه می‌شود.
اگر idxmax بعد از idxmin باشد → longEntry
اگر idxmin بعد از idxmax باشد → shortEntry
```

### برای ما

این یک variant از event/pivot labels است. برای production ما first-passage ATR target بهتر است، اما برای research می‌توانیم target زیر را تست کنیم:

```text
pivot_block_event(period=10/20/50/100)
```

---

### 3.6 feature shift برای جلوگیری از leakage

فایل:

```text
common/featurePreparer.py
```

متد:

```text
shiftFeatures(...)
```

منطق:

```text
CurrentOpen و targets shift نمی‌شوند.
همه featureهای دیگر shift(1) می‌شوند.
اولین row حذف می‌شود.
```

### اهمیت برای ما

در ShadBotTrader باید دقیقاً مشخص باشد:

```text
closed-bar decision یا open-bar decision؟
```

اگر decision در ابتدای کندل است، featureهای همان کندل نباید وارد مدل شوند. ما باید این را در live/backtest audit کنیم.

---

### 3.7 hourly returns / lagged return branch

فایل‌ها:

```text
common/hourlyReturns.py
3_make_model/rnn/1_prepare_returns/services/dailyReturns.py
```

برای hourly:

```text
windowSize = 120
columns 1..120 = lagged returns
fwd_returns_label = fwd_returns > 0
```

### ایده برای ShadBotTrader

مدل دو-branch:

```text
Branch A: returns sequence
Branch B: engineered features
concat → classifier
```

این می‌تواند بعداً benchmark خوبی برای `trend_signal` باشد.

---

### 3.8 model architecture

فایل:

```text
3_make_model/rnn/3_create_models/local/services/modelMaker.py
```

دو ورودی:

```text
Returns input: shape (120, 1)
Features input: shape (trainFeaturesColumns,)
```

معماری:

```text
Returns → LSTM(200, return_sequences=True, dropout=.2)
        → LSTM(100, dropout=.2)
concat with features
BatchNormalization
Dense 300
Dropout .2
Dense 100
Dense 50
Dense sigmoid
```

Loss:

```text
binary_crossentropy
```

Metrics:

```text
tp/fp/tn/fn
accuracy
precision
recall
AUC
PR-AUC
```

Callbacks:

```text
ModelCheckpoint monitor='auc'
EarlyStopping monitor='auc'
```

### نقد

monitor روی train `auc` است، نه `val_auc`. برای ما باید `val_auc`، `val_macro_f1` یا profit metric باشد.

---

### 3.9 class weights و bias

فایل:

```text
3_make_model/rnn/3_create_models/local/services/createModel.py
```

فرمول:

```text
initial_bias = log(pos/neg)
weight_0 = total / (2 * neg)
weight_1 = total / (2 * pos)
```

### برای ما

برای 3-class trend_signal:

```text
weight_i = total / (num_classes * count_i)
```

باید per fold و فقط روی train fold محاسبه شود.

---

### 3.10 threshold grid / prediction comparison

فایل‌ها:

```text
common/predict.py
common/predictComparer.py
common/modelTester.py
```

دو مدل جدا:

```text
longTargetKey
shortTargetKey
```

برای هر threshold:

```text
0.00, 0.05, ..., 0.95
```

ستون‌های binary می‌سازد:

```text
predictedLongEntry_0.75
predictedShortEntry_0.65
```

سپس تمام ترکیب‌های LongMin/ShortMin را backtest می‌کند و stats می‌گیرد:

```text
Trades
TotalReturn
MaxDrawdown
MaxDrawdownDuration
WinRate
```

### برای ما

این باید وارد roadmap شود:

```text
BUY threshold × SELL threshold heatmap
```

اما threshold باید روی validation/holdout انتخاب شود، نه روی همان بازهٔ live.

---

### 3.11 backtest / portfolio

فایل‌ها:

```text
common/portfolioMaker.py
common/cleanEntriesExits.py
common/modelTester.py
```

VectorBT config:

```text
size = 10000
tp_stop = 0.3
sl_stop = 0.03
```

برای ما کد مستقیم لازم نیست، چون backtest engine خودمان spread/TP/SL/range دارد. اما ایدهٔ heatmap و threshold optimization مهم است.

---

### 3.12 random / Monte Carlo / White Reality Check

فایل‌ها:

```text
4_test_model/services/monteCarlo.py
4_test_model/services/whitesCheck.py
```

روش:

```text
portfolio allocations را با detrended returns ترکیب می‌کند.
returns را random/permutation می‌کند.
mean return مدل را با random distribution مقایسه می‌کند.
p-value می‌دهد.
```

### برای ما

این برای جلوگیری از data snooping حیاتی است. وقتی thresholdهای زیاد تست می‌کنیم، باید بپرسیم:

```text
آیا بهترین نتیجه واقعاً معنادار است یا شانسی؟
```

---

### 3.13 paper trading با Alpaca

فایل‌ها:

```text
4_test_model/paper/process/alpacaProvider.py
4_test_model/paper/process/alpaca_process.py
4_test_model/paper/process/predictor.py
4_test_model/paper/process/trader.py
```

فرآیند:

```text
هر ساعت در دقیقه :15 اجرا می‌شود.
آخرین دیتای hourly را می‌گیرد.
features می‌سازد.
prediction می‌زند.
threshold/backtest را روی recent data optimize می‌کند.
اگر recent prediction از threshold بگذرد trade می‌کند.
```

### نقد برای ما

- برای MT5/Alpari مستقیم کاربرد ندارد.
- threshold optimization روی recent data و استفاده فوری می‌تواند overfit باشد.
- اما ایدهٔ decision audit و paper execution loop مهم است.

---

## 4) نتیجه‌های قابل تبدیل به ShadBotTrader

### باید استفاده کنیم

```text
1. trend_signal event classification را محور کنیم.
2. class weights + output bias + F1/PR-AUC اضافه کنیم.
3. long/buy و short/sell binary مدل جدا را تست کنیم.
4. feature shift/closed-bar audit را صریح کنیم.
5. threshold grid و heatmap backtest بسازیم.
6. random baseline و Monte Carlo/White checks اضافه کنیم.
7. دو-branch returns+features model را به عنوان benchmark بعدی تست کنیم.
8. external/regime features برای طلا اضافه کنیم.
```

### نباید مستقیم استفاده کنیم

```text
1. کد TF1 Alpaca و Onepagecode.
2. price regression target.
3. vectorbtpro-dependent code.
4. WQA101 بدون causality audit.
5. monitor train AUC به جای validation metric.
6. threshold optimization روی همان بازهٔ live.
7. Alpaca paper trading code برای MT5.
```

---

## 5) روند پیشنهادی تغییرات بعدی

### Phase 107 — audit کامل trend_signal

فایل پیشنهادی:

```text
scripts/evaluate_trend_signal_5m.py
```

گزارش:

```text
SELL/HOLD/BUY distribution
ambiguous samples
barrier distance stats
first-hit distance stats
fold train/val balance
majority baseline
confusion matrix
precision/recall/F1 per class
macro-F1
balanced accuracy
PR-AUC BUY/SELL
```

---

### Phase 108 — class weights + metrics برای trend_signal

اضافه شود:

```text
class_weight per fold
val_sell_precision/recall/f1
val_hold_precision/recall/f1
val_buy_precision/recall/f1
val_macro_f1
val_balanced_accuracy
```

monitor پیش‌فرض برای trend_signal:

```text
val_macro_f1 یا val_buy_sell_f1
```

---

### Phase 109 — threshold calibration / heatmap

برای هر مدل:

```text
buy_threshold × sell_threshold
min_margin_vs_hold
min_margin_vs_opposite
```

با معیار:

```text
profit factor
expectancy
max drawdown
trades count
precision floor
```

---

### Phase 110 — feature selection train-only

فلگ‌ها:

```text
--feature-select none|corr|tree|hybrid
--top-features 16|32|64|128
--max-feature-corr 0.90
```

فقط روی train fold/prefix fit شود.

---

### Phase 111 — POS/NEG binary event models

مدل‌ها:

```text
gold_buy_event_5m
gold_sell_event_5m
```

قانون:

```text
buy_prob بالا و sell_prob پایین → BUY
sell_prob بالا و buy_prob پایین → SELL
هر دو بالا → ambiguous/no trade
هر دو پایین → HOLD
```

---

### Phase 112 — two-branch model benchmark

معماری پیشنهادی:

```text
returns sequence branch → causal Conv/GRU/LSTM
engineered features branch → Dense
concat → classifier
```

---

### Phase 113 — statistical significance checks

اضافه شود:

```text
random strategy baseline
permutation test
Monte Carlo p-value
White Reality-style check
```

---

### Phase 114 — external/regime features برای XAUUSD

اولویت‌ها:

```text
DXY
US10Y yield
real yield proxy
VIX
CPI/FOMC/NFP calendar flag
London/NY session
day-of-week
weekly close location
volatility regime
```

---

### Phase 115 — live decision audit

هر تصمیم live ثبت کند:

```text
model versions
features fingerprint
probabilities
thresholds
licenses passed/failed
TP/SL
spread/slippage
order intent
broker result
```

---

## 6) اولویت نهایی

بهترین قدم بعدی:

```text
Phase 107 + 108:
trend_signal audit + class weights + F1/PR-AUC
```

دلیل:

```text
هر سه منبع تأیید می‌کنند event/action classification با no-trade، وزن کلاس و threshold calibration مسیر عملی‌تر از regression score/price است.
```
