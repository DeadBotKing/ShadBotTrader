# فاز ۱۰۶ — بررسی کامل منابع TensorFlow/Algo-Trading و نقشهٔ استفاده در ShadBotTrader

تاریخ: 2026-09-07  
زبان گزارش: فارسی  
هدف: بررسی دقیق سه منبع معرفی‌شده توسط اپراتور، آوردن کد قابل بررسی به workspace، ثبت نکات لازم در Docs، و تعیین اینکه چه ویژگی‌ها/مدل‌ها/متدهایی را می‌توانیم در ShadBotTrader استفاده کنیم.

---

## 0) منابع بررسی‌شده

### 0.1 Alpaca — TensorFlow Market Forecasting

```text
https://alpaca.markets/learn/tensorflow-market-forecasting
```

نوع منبع: مقاله آموزشی + full script داخل مقاله.  
دسترسی: public.  
موضوع: MLP ساده برای classification جهت روز بعد بازار با RSI/Stochastic.

### 0.2 ari99/algorithmic_trading

```text
https://github.com/ari99/algorithmic_trading
```

Repo در workspace clone شد:

```text
/home/user/algorithmic_trading
commit: c8479f3
```

نوع منبع: repository کوچک ولی کامل‌تر از یک مقاله، شامل download data، feature engineering، RNN/LSTM، backtest با VectorBT Pro، paper trading با Alpaca.  
نکتهٔ مهم: license file در repo دیده نشد؛ بنابراین **کپی مستقیم کد به ShadBotTrader توصیه نمی‌شود** مگر license بعداً روشن شود. علاوه بر آن، dependency اصلی `vectorbtpro` proprietary است.

### 0.3 Onepagecode Substack — Algo Trading Framework Using TensorFlow and Alpha Vantage

```text
https://onepagecode.substack.com/p/an-algo-trading-framework-using-tensorflow
```

نوع منبع: مقاله Substack با بخش paid/paywall.  
دسترسی: فقط متن و snippets قابل مشاهده بررسی شد؛ دکمهٔ source code در انتهای مقاله پشت subscription/paywall است و کد کامل قابل download نبود.  
موضوع: pipeline با Alpha Vantage، MinMax scaling train-only، MLP regression برای next adjusted close.

---

## 1) بررسی منبع Alpaca — TensorFlow Market Forecasting

### 1.1 هدف مقاله

مقاله می‌خواهد جواب دهد:

```text
آیا می‌توان با TensorFlow و چند indicator استاندارد، جهت حرکت روز بعد بازار را پیش‌بینی کرد؟
```

مدل یک baseline آموزشی است، نه سیستم production. خود مقاله تأکید می‌کند نتیجه‌ها «less than spectacular» هستند و overfitting واضح دیده می‌شود.

---

### 1.2 Task / Target

مسئله تعریف‌شده:

```text
Binary classification
```

Target:

```text
اگر close[t+lookahead] - close[t] >= 0 → longOutput = 1, shortOutput = 0
اگر close[t+lookahead] - close[t] <  0 → longOutput = 0, shortOutput = 1
```

در script:

```python
targetLookaheadPeriod = 1
closeDifference = shiftedClose - closeList
longOutput[closeDifference >= 0] = 1
shortOutput[closeDifference < 0] = 1
```

یعنی مقاله جهت روز بعد را بر اساس close-to-close طبقه‌بندی می‌کند.

### ارزیابی برای ShadBotTrader

این شبیه مدل `gold_trend_1d` ماست، نه `trend_score` regression. اما target آن هنوز خیلی خام است، چون magnitude، spread، TP/SL و no-trade ندارد.

برای ما، نسخه بهتر:

```text
نه close[t+1] >= close[t]
بلکه first-hit ±ATR barrier / HOLD
```

یعنی همان `trend_signal`.

---

### 1.3 Input Features

مقاله فقط 4 feature دارد:

```text
RSI14
RSI50
STOCH14K
STOCH14D
```

دلیل انتخاب مقاله:

```text
این indicatorها خودشان بین 0 و 100 normalized هستند.
پس price level وارد مدل نمی‌شود و مدل قابلیت generalization بین stockها دارد.
```

مقاله صریحاً پیشنهاد می‌کند:

```text
از indicatorهای normalized استفاده کنید، یا indicatorها را price/volatility-normalized کنید.
```

### برای ShadBotTrader

این نکته با تغییر Phase 104 ما هم‌راستاست:

```text
trend_score input scale → [-1,+1]
range input scale       → [-2,+2]
```

اما مهم‌تر از scale این است که featureهای price-level باید stationary شوند. پروژه ما در `feature_matrix.py` همین را تا حدی انجام می‌دهد:

```text
open_rel/high_rel/low_rel/close_rel
price_scaled features / close - 1
```

کار پیشنهادی:

```text
برای مدل‌های جهت، featureهای raw قیمتی یا volume-scale باید audit شوند که هیچ مقدار مطلق price-level وارد مدل نشود.
```

---

### 1.4 Dataset Generation

مقاله:

```text
S&P500 stocks
Daily candles since 2015
train: Jan 2015 → Jun 2017
eval: Jun 2017 → Jun 2018
```

Script دو فولدر تولید می‌کند:

```text
./train/{symbol}.csv
./eval/{symbol}.csv
```

ویژگی خوب:

```text
Data generation و ML script جدا هستند؛ dataset فقط وقتی لازم است regenerate می‌شود.
```

### برای ShadBotTrader

ما این separation را بهتر داریم:

```text
datasets/processed
feature cache
model artifacts
scripts/run_dual_models.py
```

ولی می‌توانیم از مقاله یک نکته بگیریم:

```text
هر training run باید دقیقاً dataset snapshot و label rule خودش را ذخیره کند.
```

در پروژه ما model record این کار را تا حدی دارد؛ باید برای feature selection/threshold calibration هم کامل شود.

---

### 1.5 Model Architecture در Alpaca

تنظیمات script:

```python
trainingCycles = 500000
batchSize = 1000
summarySteps = 1000
dropout = 0.5
nodeLayout = [40, 30, 20, 10]
```

مدل:

```text
Input 4 features
Dense 40 tanh + dropout
Dense 30 tanh + dropout
Dense 20 tanh + dropout
Dense 10 tanh + dropout
Dense 2 softmax
```

Loss:

```python
softmax_cross_entropy_with_logits_v2
```

Optimizer:

```python
AdamOptimizer(0.0001)
```

Metrics:

```text
accuracy
```

Logging:

```text
TensorBoard scalar summaries
checkpoint every summarySteps
```

### مشکل فنی در script

در script، خروجی به شکل زیر ساخته شده:

```python
logits = tf.layers.dense(net, 2, activation=tf.nn.softmax)
cross_entropy = tf.nn.softmax_cross_entropy_with_logits_v2(labels=y, logits=logits)
```

در TensorFlow کلاسیک، `softmax_cross_entropy_with_logits` انتظار logits خام دارد، نه softmax شده. یعنی از نظر مدرن بهتر است:

```text
Dense(2, activation=None) + from_logits=True
یا Dense(2, softmax) + categorical_crossentropy بدون logits
```

پس کد مقاله آموزشی است و مستقیم نباید copy شود.

---

### 1.6 Training results

مقاله سه network layout را مقایسه می‌کند:

```text
Model 1: [40,30,20,10]
Model 2: [80,60,40,20]
Model 3: [160,120,80,40]
```

نتیجه:

```text
Overfitting واضح؛ هرچه network بزرگ‌تر، eval loss بیشتر واگرا می‌شود.
Training accuracy فقط چند درصد بالاتر از random است.
```

### درس برای ما

این دقیقاً با تجربه trend_score/trend روزانه ما سازگار است:

```text
مدل قوی‌تر الزاماً edge نمی‌سازد؛ اگر target noise باشد، capacity فقط overfit می‌کند.
```

پس تغییر معماری به تنهایی جواب نیست؛ target و evaluation باید عملیاتی‌تر شوند.

---

### 1.7 پیشنهادهای مقاله Alpaca

مقاله پیشنهاد می‌دهد:

1. Featureهای بیشتر اضافه شود.
2. Featureها normalized یا price/vol-normalized باشند.
3. به جای یک نقطه، آخرین 10 period به مدل داده شود.
4. architectureهای دیگر مثل convolution تست شوند.
5. Label threshold با median price change balance شود.
6. Neutral class اضافه شود.
7. Lookahead periodهای طولانی‌تر تست شوند.
8. مدل ML به عنوان **complementary indicator** در کنار rule-based strategy استفاده شود، نه standalone.

### mapping مستقیم به ShadBotTrader

| پیشنهاد Alpaca | وضعیت ما | اقدام پیشنهادی |
|---|---|---|
| normalized features | داریم، ولی باید برای direction audit شود | feature integrity audit برای signal/trend_signal |
| last 10 periods | ما window=150/288 داریم | کافی است؛ issue window نیست |
| neutral class | trend_signal HOLD دارد | باید serious شود با F1/class weights |
| median threshold | ما می‌توانیم quantile target بسازیم | event_quantile labels |
| complementary indicator | دقیقاً باید همین باشد | ML فقط یکی از licenseهای triple strategy |

---

## 2) بررسی منبع Onepagecode Substack

### 2.1 وضعیت دسترسی

مقاله به صورت public snippet در دسترس است، اما source code کامل در انتها پشت paywall/subscription است:

```text
Download source code using the button below
Continue reading this post for free / paid subscription
```

بنابراین فقط کد و توضیحاتی که در صفحه قابل مشاهده بود بررسی شد.

---

### 2.2 ساختار پروژه طبق مقاله

فایل‌های توضیح‌داده‌شده:

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

Pipeline:

```text
Alpha Vantage API → stock data + indicators → merge by date → fill missing → construct next-day label → chronological split → MinMaxScaler fit on train only → MLP train → MSE/relative error evaluation
```

---

### 2.3 constants.py

نمونه constants:

```python
BASEURL = 'https://www.alphavantage.co/query?'
API_KEY = '...'
INTERVAL = 'daily'
TIME_PERIOD = '10'
SERIES_TYPE = 'close'
TIME_SERIES_DAILY_ADJUSTED = 'TIME_SERIES_DAILY_ADJUSTED'
DATATYPE_JSON = 'json'
OUTPUTSIZE_FULL = 'full'
```

### نکته برای ما

نباید API key داخل code hard-code شود. برای ShadBotTrader اگر external macro data اضافه کنیم، باید:

```text
configs / env / credential store
```

استفاده شود، نه constant public.

---

### 2.4 fetch_stock.py

کار:

```text
دریافت TIME_SERIES_DAILY_ADJUSTED از Alpha Vantage
JSON → DataFrame transpose
پاک‌سازی column names مثل "1. open" → "open"
```

کد مهم:

```python
pattern = re.compile('[a-zA-Z]+')
dataframe.columns = dataframe.columns.map(lambda a: pattern.search(a).group())
```

### برای ShadBotTrader

برای XAUUSD ما منبع اصلی MT5/Alpari است، ولی برای macro features می‌شود مشابه این loader نوشت:

```text
DXY
US10Y
VIX
```

اما نه با Alpha Vantage hardcoded؛ بلکه با provider interface.

---

### 2.5 fetch_indicators.py / fetch_combined_data.py

`fetch_indicators.py` هر indicator را از Alpha Vantage می‌گیرد:

```python
function={indicator}
symbol={symbol}
interval=daily
time_period=10
series_type=close
```

`fetch_combined_data.py` برای هر stock:

```text
stock daily adjusted data
+ each technical indicator
outer merge on date
save CSV
```

rate limit:

```python
time.sleep(1)
```

### استفاده برای ما

ایده خوب:

```text
providerهای جدا برای data sourceهای مختلف، بعد merge علّی روی timestamp.
```

اما Alpha Vantage indicators برای ما اولویت پایین‌تر از feature catalogue داخلی است.

---

### 2.6 preprocess.py

#### fill_missing

```python
data.fillna(method='ffill')
data.fillna(method='bfill')
data.fillna(value=0)
```

#### split

```python
split_point = int(train_ratio * rows)
data_train = data.iloc[:split_point]
data_test = data.iloc[split_point:]
```

#### scale

```python
scaler = MinMaxScaler()
scaler.fit(train_data)
train = scaler.transform(train_data)
test = scaler.transform(test_data)
```

#### construct_label

```python
data['label'] = data['adjusted'].shift(-1)
drop last row
```

### نکته مثبت

```text
Scaler فقط روی train fit می‌شود و test فقط transform می‌شود.
```

این در مقایسه با scaling per-window ما متفاوت است. برای neural nets ما per-window scaling داریم، اما اگر feature selection یا tree/MLP روی tabular static اضافه کنیم، باید train-only scaler داشته باشیم.

### نکته منفی

```text
Target = next adjusted price regression
```

برای trading ضعیف‌تر از event target است.

---

### 2.7 neural_network.py

Architecture visible:

```text
Input p features
Dense 64 ReLU
Dense 32 ReLU
Dense 16 ReLU
Dense 1 linear output
```

Loss:

```text
MSE
```

Optimizer:

```text
Adam default
```

Training:

```text
epochs = 20
batch_size = 1
shuffle train data every epoch
print train MSE, test MSE, relative error
```

Evaluation:

```text
MSE
relative error = abs(mean((pred - y_test) / y_test))
```

### برای ShadBotTrader

این مدل برای ما مستقیماً جذاب نیست، چون regression price target است. اما به عنوان baseline ساده می‌شود بعداً داشت:

```text
MLP baseline for event classification
```

نه next price regression.

---

### 2.8 run.py

CLI pipeline:

```text
-f / --fetch
-p / --preprocess
-n / --neuralnetwork
--evalnn
```

ترتیب اجرا مستقل از order args رعایت می‌شود:

```text
fetch → preprocess → train → eval
```

### برای ShadBotTrader

ما dashboard و scripts داریم. ایده قابل استفاده:

```text
یک command برای اجرای pipeline کامل weekly/research:
fetch → feature audit → train → evaluate → backtest
```

ولی فعلاً اولویت با trend_signal metrics است.

---

## 3) بررسی repo ari99/algorithmic_trading

### 3.1 وضعیت repo

Clone path:

```text
/home/user/algorithmic_trading
commit c8479f3
```

README:

```text
Complete algorithmic trading project using machine learning.
Uses Python, Tensorflow, VectorBT, Polygon, Alpaca, AWS Sagemaker.
```

Wiki هم بررسی شد. Wiki features را این‌طور دسته‌بندی می‌کند:

```text
Download Historical Data
Create Features
Feature Correlation
Flipped Features
Create Model / AWS Sagemaker
Check Model Performance
Randomized Significance Checks
ML Model Performance Stats
Backtest Performance Stats
Paper Trade using Alpaca
```

### محدودیت مهم

- `vectorbtpro` استفاده شده که proprietary است.
- license file در repo دیده نشد.
- ساختار notebook-heavy و exploratory است.
- برخی decisionها برای production خطرناک‌اند، مثلاً threshold selection روی داده نزدیک live.

---

## 3.2 Data download

فایل:

```text
common/polygonDownloader.py
```

متدها:

```python
downloadData(symbols, startDate, endDate, timeFrame)
downloadMonthHourly(symbols)
```

روش:

```python
vbt.PolygonData.set_custom_settings(api_key=ConfigSecrets.POLYGON_API_KEY)
vbt.PolygonData.fetch(symbols, start, end, timeframe)
```

Config:

```text
Config.tickersDownload = ["X:BTCUSD"]
allDataStart = '2017-01-01 UTC'
allDataEnd   = '2023-01-01 UTC'
allDataTimeFrame = '1h'
```

### برای ShadBotTrader

ما MT5/Alpari provider داریم؛ Polygon مستقیم لازم نیست. اما ایدهٔ خوب:

```text
Data provider abstraction + checkpointed downloads
```

را داریم. برای macro features شاید provider جدید اضافه شود.

---

## 3.3 Checkpointing data

فایل:

```text
common/checkpointHandler.py
```

متدها:

```python
fetchOrCreateSave(dataPath, key=None)
fetchOrCreateSaveNumpy(dataPath)
fetchData(dataPath)
```

ایده:

```text
اگر HDF/npy هست بخوان؛ اگر نیست createData و ذخیره کن.
```

### برای ما

ما Parquet + model artifact store داریم. ایدهٔ checkpoint واضح است، اما کد لازم نیست.

---

## 3.4 Clean data

فایل:

```text
1_download_data/services/cleanDataHandler.py
```

کار:

```text
dropna برای هر symbol
```

### برای ما

ما gap policy و allow_gap داریم. dropna ساده کافی نیست، ولی می‌توانیم برای feature matrices همچنان fail-closed بمانیم.

---

## 3.5 Flipped data

فایل:

```text
1_download_data/services/flipBarData.py
```

متدها:

```python
flipBarData(df)
flipSeries(originalSeries, adjust)
```

ایده:

```text
series را با diff معکوس می‌کند تا مسیر قیمت آینه‌ای شود.
```

هدف در wiki:

```text
Also create flipped data and features to compare performance of algo with normal data.
```

### برای ShadBotTrader

این ایده برای **robustness test** جذاب است، نه لزوماً training augmentation. برای XAUUSD می‌توانیم بررسی کنیم:

```text
اگر قیمت را آینه کنیم، آیا مدل buy/sell symmetry دارد؟
آیا مدل فقط bias long/short یاد گرفته؟
```

اما نباید بی‌فکر وارد training شود، چون market microstructure و spread symmetric نیستند.

---

## 3.6 Feature engineering در ari99

فایل:

```text
common/featuresTargetsUnshiftedMaker.py
```

### createTAFeatures

کارها:

```python
taData = data.run("talib", periods=vbt.run_func_dict(mavp=14))
```

سپس چند ستون با inf حذف می‌کند:

```text
exp_real
cosh_real
sinh_real
```

بعد WQA101 alphaها را می‌سازد:

```python
for i in range(1, 102):
    if i not in noWQA:
        outWQA = vbt.wqa101(i).run(...).out
        taData = taData.join(outWQA)
```

لیست excluded WQA:

```text
48,58,59,63,67,69,70,76,79,80,82,84,87,89,90,91,93,97,100
```

### برای ما

ایدهٔ قابل استفاده:

```text
WorldQuant alpha-style features شاید برای XAUUSD مفید باشند.
```

اما مستقیم استفاده نمی‌کنیم:

```text
vectorbtpro لازم دارد.
باید هر alpha از نظر causality و stationarity audit شود.
```

برای فاز بعدی می‌شود یک proposal جدا برای چند alpha امن نوشت.

---

## 3.7 Target labels در ari99

فایل:

```text
common/featuresTargetsUnshiftedMaker.py
common/labelMaker.py
```

Periods:

```python
periods = [10, 20, 50, 100]
```

Target columns:

```text
longEntry10 / shortEntry10
longEntry20 / shortEntry20
longEntry50 / shortEntry50
longEntry100 / shortEntry100
```

روش ساخت:

```python
minmax = df.groupby(np.arange(len(df.index)) // period)['Close'].agg(['idxmin', 'idxmax'])
longEntry = idxmax > idxmin
shortEntry = idxmin > idxmax
```

بعد روی idxmin و idxmax merge می‌کند تا نقطه‌های entry label شوند.

### تحلیل فنی

این یعنی در هر block غیرهمپوشان period:

```text
اگر low قبل از high بیاید، low نقطه long و high نقطه exit/short می‌شود.
اگر high قبل از low بیاید، high نقطه short و low نقطه exit/long می‌شود.
```

این شبیه pivot/event target است.

### برای ShadBotTrader

قابل استفاده به عنوان ایده:

```text
event_pivot_block_labels(period=10/20/50/100)
```

اما باید مراقب باشیم:

```text
blockهای ثابت می‌توانند label artifacts ایجاد کنند.
برای trading ما first-passage ATR بهتر است.
```

پیشنهاد:

```text
از این فقط به عنوان target variant در research استفاده شود، نه target اصلی.
```

---

## 3.8 Feature shift برای جلوگیری از leakage

فایل:

```text
common/featurePreparer.py
```

متد مهم:

```python
shiftFeatures(targetColumns, featureDataShifted)
```

منطق:

```text
CurrentOpen و target columns را shift نمی‌کند.
بقیه featureها را shift(1) می‌کند.
اولین row بعد از shift حذف می‌شود.
```

هدف:

```text
مدل هنگام تصمیم‌گیری فقط featureهای کندل قبلی را ببیند، نه کندل جاری/آینده.
```

### برای ShadBotTrader

این بسیار مهم است. ما feature causality داریم، اما باید برای live decision دقیقاً روشن کنیم:

```text
در لحظه تصمیم آیا کندل جاری closed است یا نه؟
اگر کندل جاری هنوز بسته نشده، featureهای آن نباید مصرف شوند.
```

برای backtest/live ما باید حالت‌های زیر را جدا کنیم:

```text
closed-bar decision
open-bar decision
next-bar execution
```

---

## 3.9 Hourly returns branch

فایل:

```text
common/hourlyReturns.py
3_make_model/rnn/1_prepare_returns/services/dailyReturns.py
```

`HourlyReturns`:

```python
returnsPct = close.pct_change().sort_index(ascending=False)
windowSize = Config.hourlyReturnsWindowSize  # 120
```

خروجی:

```text
columns 1..120 as lagged returns
fwd_returns
fwd_returns_label = fwd_returns > 0
```

### برای ما

ایدهٔ خیلی خوب:

```text
مدل دو input داشته باشد:
1. raw/lagged returns window branch
2. engineered features branch
```

ما الان همه چیز را در یک matrix می‌دهیم. برای trend_signal ممکن است دو-branch architecture مفید باشد:

```text
returns branch: causal Conv/LSTM/GRU روی return sequence
features branch: dense روی آخرین feature vector یا feature window summary
concat → classifier
```

ولی این تغییر باید بعد از target/metric اصلاح شود، نه فوری.

---

## 3.10 Train/test split

Config:

```text
trainIndexEnd = '2021-06-01'
testIndexStart = '2021-06-02'
```

Train/test chronological است. این خوب است.

اما repo کامل roll-forward/purge مثل ما ندارد. پس روش ما بهتر است.

---

## 3.11 Model architecture در ari99

فایل:

```text
3_make_model/rnn/3_create_models/local/services/modelMaker.py
3_make_model/rnn/3_create_models/sagemaker/modelMaker.py
```

دو input دارد:

```python
returnsInput = Input(shape=(120, 1), name='Returns')
featuresInput = Input(shape=(trainFeaturesColumns,), name='Features')
```

LSTM branch:

```text
LSTM 200, dropout .2/.1, return_sequences=True
LSTM 100, dropout .2/.1
```

Merge:

```text
concatenate([lstm_model, featuresInput])
BatchNormalization
Dense 300
Dropout .2/.1
Dense 100
Dense 50
Dense output sigmoid
```

Loss:

```text
binary_crossentropy
```

Optimizer:

```text
local: SGD(lr=0.01)
sagemaker: RMSprop(lr=0.001, rho=0.9, decay=0.0001)
```

Metrics:

```text
TruePositives
FalsePositives
TrueNegatives
FalseNegatives
BinaryAccuracy
Precision
Recall
AUC
PR-AUC
```

Checkpoint/EarlyStopping:

```text
monitor='auc', mode='max'
```

### نقد مهم

در local/sagemaker monitor روی `auc` است، نه `val_auc`. این می‌تواند train-metric overfit را ذخیره کند. برای ما باید:

```text
monitor='val_auc' یا val_macro_f1 یا profit metric
```

### برای ShadBotTrader

مدل دو-branch قابل استفاده به عنوان **مدل جدید optional** است، اما نه اولویت اول. اول target و metrics.

---

## 3.12 Class imbalance در ari99

فایل:

```text
3_make_model/rnn/3_create_models/local/services/createModel.py
```

متدها:

```python
__createBias(trainTargets, key)
__createClassWeights(trainTargets, key)
```

فرمول:

```python
initial_bias = log(pos / neg)
weight_for_0 = (1 / neg) * (total / 2.0)
weight_for_1 = (1 / pos) * (total / 2.0)
class_weight = {0: weight_for_0, 1: weight_for_1}
```

### برای ShadBotTrader

این مستقیم برای `trend_signal` و POS/NEG models لازم است. برای 3-class باید generalize شود:

```text
weight_for_class_i = total / (num_classes * count_i)
```

---

## 3.13 Prediction و threshold sweep

فایل‌ها:

```text
common/predict.py
common/predictComparer.py
common/modelTester.py
```

`Predict` دو مدل می‌گیرد:

```text
longTargetKey
shortTargetKey
```

و دو prediction جدا می‌سازد:

```text
test_predict_long
test_predict_short
```

`PredictComparer.createAllComparisonDf` برای thresholdهای 0 تا 0.95 با step 0.05 ستون می‌سازد:

```python
for i in [x / 100.0 for x in range(0, 100, 5)]:
    predictedLongEntry_i = predictedLongEntry > i
    predictedShortEntry_i = predictedShortEntry > i
```

`ModelTester.createPortfolioComparisonDf` تمام ترکیب‌های LongMin/ShortMin را backtest می‌کند:

```text
LongMin = 0.00,0.05,...0.95
ShortMin = 0.00,0.05,...0.95
```

Stats:

```text
Trades
TotalReturn
MaxDrawdown
MaxDrawdownDuration
WinRate
```

### برای ShadBotTrader

این یکی از بهترین چیزهای repo است. باید برای ما اضافه شود:

```text
threshold grid search روی validation/backtest
BUY threshold × SELL threshold
heatmap برای TotalReturn/ProfitFactor/MaxDD/Trades
```

اما باید مراقب باشیم threshold انتخاب‌شده روی همان دادهٔ live/recent بهینه نشود.

---

## 3.14 Portfolio/backtest

فایل‌ها:

```text
common/portfolioMaker.py
common/cleanEntriesExits.py
common/modelTester.py
```

VectorBT config:

```python
vbt.Portfolio.from_signals(
    close=close,
    entries=longEntries,
    exits=longExits,
    short_entries=shortEntries,
    short_exits=shortExits,
    size=10000,
    size_type='value',
    init_cash='auto',
    tp_stop=0.3,
    sl_stop=0.03,
)
```

Random baseline:

```python
vbt.PF.from_random_signals(
    prob=.007,
    tp_stop=0.2,
    sl_stop=0.05,
    direction="both"
)
```

### برای ShadBotTrader

ما backtest engine داریم؛ VectorBT Pro لازم نیست. اما ایده‌ها:

```text
- threshold grid heatmap
- random signal baseline
- statistical significance check
```

باید به backtest ما اضافه شوند.

---

## 3.15 Monte Carlo و White's Reality Check

فایل‌ها:

```text
4_test_model/services/monteCarlo.py
4_test_model/services/whitesCheck.py
```

### MonteCarloCheck

کار:

```text
allocations = sign(portfolio allocations)
pctCloseDetrended = close.pct_change() - mean
randomly permute returns 20000 بار
مقایسه mean return واقعی با random distribution
pValue = count(random > meanReturn) / 10000
```

### WhitesCheck

کار مشابه:

```text
allocations * detrended close returns
random sampling indexes
sample means
compare originalMean با random distribution
```

### برای ShadBotTrader

این بسیار مهم است. چون ما با تعداد زیادی model/threshold تست می‌کنیم و data snooping خطرناک است. باید اضافه کنیم:

```text
random-strategy baseline
permutation/Monte Carlo p-value
White Reality-style check برای بهترین threshold/model
```

---

## 3.16 Paper trading با Alpaca در ari99

فایل‌ها:

```text
4_test_model/paper/process/alpacaProvider.py
4_test_model/paper/process/alpaca_process.py
4_test_model/paper/process/predictor.py
4_test_model/paper/process/trader.py
```

Schedule:

```python
schedule.every().hour.at(":15").do(job)
```

Process:

```text
download last month hourly data
build features
generate predictions
run threshold/backtest comparison on recent data
choose best LongMin/ShortMin by TotalReturn
if recent prediction > threshold → trade
```

Provider:

```text
Alpaca paper TradingClient
market orders
cancel/liquidate
stop orders
```

### نقد مهم

1. `Prediction.providerSymbol` و `providerOpenPositionSymbol` در shown code پر نمی‌شوند.
2. انتخاب threshold روی recent month و استفاده فوری برای trade می‌تواند online overfit باشد.
3. stop order برای short در code ممکن است side/order details مسئله داشته باشد.
4. برای ما MT5/Alpari است، نه Alpaca.

### برای ShadBotTrader

استفاده مستقیم ندارد. اما ایدهٔ audit مسیر live خوب است:

```text
هر تصمیم live باید log کند:
features timestamp
model versions
probabilities
thresholds
licenses passed/failed
intended order
broker response
```

---

## 4) مقایسه سه منبع

| موضوع | Alpaca article | Onepagecode | ari99 repo | نتیجه برای ما |
|---|---|---|---|---|
| Target | جهت روز بعد binary | next adjusted price regression | long/short event labels | event classification بر regression ارجح است |
| Features | 4 normalized indicators | Alpha Vantage indicators | TA-Lib + WQA101 + returns | normalized/causal/selected features |
| Window | اول فقط یک نقطه؛ پیشنهاد 10 period | tabular no real window | returns window 120 + features | ما window داریم؛ دو-branch ارزش تست دارد |
| Imbalance | پیشنهاد neutral/balancing | ندارد | class weights + bias | برای trend_signal ضروری |
| Metrics | accuracy + TensorBoard | MSE/relative error | precision/recall/AUC/PR-AUC | F1/PR-AUC/profit metrics لازم است |
| Threshold | پیشنهاد median/neutral | ندارد | grid thresholds | threshold calibration لازم است |
| Backtest | ندارد | ندارد | VectorBT + TP/SL + random checks | در engine خودمان پیاده شود |
| Live | theoretical | ندارد | Alpaca scheduled paper | فقط ایدهٔ decision audit |
| Code quality | آموزشی TF1 | paid snippets TF1 | exploratory/proprietary deps | ایده‌ها را بگیریم، کد را کپی نکنیم |

---

## 5) چیزهایی که واقعاً باید وارد ShadBotTrader شود

### 5.1 از Alpaca

قابل استفاده:

```text
- استفاده از normalized/price-normalized indicators
- neutral class / balanced target
- lookahead variants
- ML به عنوان complementary indicator نه decision maker تنها
```

غیرقابل استفاده مستقیم:

```text
- TF1 script
- softmax-before-logits loss bug
- فقط 4 feature و accuracy ساده
```

### 5.2 از Onepagecode

قابل استفاده:

```text
- train-only scaler برای مدل‌های tabular/MLP/tree آینده
- CLI pipeline orchestration ایده‌ای
- batch fetch/preprocess/train/evaluate structure
```

غیرقابل استفاده مستقیم:

```text
- next price regression
- hardcoded API key
- TF1 Session/Saver
- source کامل پشت paywall
```

### 5.3 از ari99

قابل استفاده:

```text
- long/short binary مدل جدا
- targetهای period-based/pivot-like برای research
- feature shift(1) برای جلوگیری از leakage در تصمیم کندل جاری
- returns branch + engineered features branch
- class weight + output bias
- threshold grid long/short
- portfolio heatmaps
- random portfolio baseline
- Monte Carlo / White Reality check
- decision/paper-trading audit idea
```

غیرقابل استفاده مستقیم:

```text
- vectorbtpro dependency
- code بدون license روشن
- WQA101 مستقیم بدون causality audit
- fixed thresholds/live threshold optimization روی recent month
- monitor train AUC به جای val AUC
- paper trading code برای Alpaca به جای MT5
```

---

## 6) روند کامل پیشنهادی تغییرات برای ShadBotTrader

این روند بدون redesign و در امتداد معماری فعلی است.

---

## Phase 107 — trend_signal audit کامل

### هدف

قبل از مدل جدید، target فعلی `trend_signal` را کامل audit کنیم.

### کارها

فایل جدید:

```text
scripts/evaluate_trend_signal_5m.py
```

گزارش:

```text
label distribution: SELL/HOLD/BUY
ambiguous samples count
barrier distance stats
first-hit bars stats
fold train/val label balance
majority baseline
always-HOLD baseline
```

Metrics بعد از مدل:

```text
confusion matrix
precision/recall/F1 per class
macro-F1
balanced accuracy
PR-AUC BUY
PR-AUC SELL
```

### فایل‌های درگیر

```text
src/ShadBotTrader/infrastructure/ai/target_builder.py
scripts/evaluate_trend_signal_5m.py
scripts/run_dual_models.py
```

---

## Phase 108 — class weights + F1/PR-AUC برای trend_signal

### هدف

مدل سه‌کلاسه BUY/HOLD/SELL زیر اکثریت HOLD دفن نشود.

### کارها

1. `WavenetTrainer` برای classification وزن کلاس بگیرد.
2. وزن هر fold فقط از train fold محاسبه شود:

```text
weight_i = total / (num_classes * count_i)
```

3. metricهای per-class ذخیره شوند:

```text
val_sell_precision/recall/f1
val_hold_precision/recall/f1
val_buy_precision/recall/f1
val_macro_f1
val_balanced_accuracy
```

4. برای `trend_signal` monitor پیش‌فرض:

```text
val_macro_f1 یا val_buy_sell_f1
```

نه صرفاً `val_loss`.

### فایل‌های درگیر

```text
src/ShadBotTrader/infrastructure/ai/wavenet/wavenet_trainer.py
src/ShadBotTrader/application/services/dual_model_service.py
src/ShadBotTrader/infrastructure/ai/training_progress.py
scripts/run_dual_models.py
```

---

## Phase 109 — threshold calibration و heatmap backtest

### الهام

ari99:

```text
LongMin × ShortMin threshold grid
```

### هدف

برای هر مدل و هر کلاس، threshold واقعی از validation/backtest پیدا شود.

### کارها

1. بعد از training، predictions روی validation fold ذخیره شود.
2. threshold grid:

```text
buy_threshold = 0.05..0.95
sell_threshold = 0.05..0.95
min_margin_vs_hold
min_margin_vs_opposite
```

3. برای هر ترکیب:

```text
trades
precision BUY/SELL
profit factor
expectancy
max drawdown
win rate
```

4. ذخیره در model record:

```json
"decision_thresholds": {
  "buy_prob": 0.74,
  "sell_prob": 0.72,
  "selected_by": "validation_profit_factor_with_precision_floor"
}
```

### فایل‌های درگیر

```text
src/ShadBotTrader/application/services/model_evaluation_service.py
src/ShadBotTrader/application/services/dual_model_backtest_service.py
src/ShadBotTrader/infrastructure/ai/model_catalogue.py
```

---

## Phase 110 — feature selection train-only

### الهام

Leci37 + ari99:

```text
correlation / tree importance / Spearman / redundant feature removal
```

### هدف

برای مدل‌های جهت، همه 180 فیچر را کورکورانه وارد نکنیم.

### کارها

فایل جدید:

```text
src/ShadBotTrader/infrastructure/ai/feature_selection.py
```

روش‌ها:

```text
spearman_to_target
pearson_to_target
mutual_info_classif optional
extra_trees_importance optional
remove pairwise corr > 0.90
hybrid_vote
```

CLI:

```text
--feature-select none|corr|tree|hybrid
--top-features 16|32|64|128
--max-feature-corr 0.90
```

Rule مهم:

```text
fit feature selection فقط روی train fold/prefix، نه کل تاریخچه.
```

---

## Phase 111 — binary POS/NEG event models

### الهام

Leci37 و ari99 هر دو long/short یا pos/neg جدا دارند.

### هدف

برای imbalance، BUY و SELL جدا یاد گرفته شوند.

### مدل‌های پیشنهادی

```text
gold_buy_event_5m
output sigmoid: BUY vs NOT_BUY

gold_sell_event_5m
output sigmoid: SELL vs NOT_SELL
```

یا به صورت option:

```text
--event-mode multiclass|buy|sell
```

Decision:

```text
اگر buy_prob بالا و sell_prob پایین → BUY
اگر sell_prob بالا و buy_prob پایین → SELL
اگر هر دو بالا → ambiguous/no-trade
اگر هر دو پایین → HOLD
```

---

## Phase 112 — two-branch model benchmark

### الهام

ari99:

```text
returnsInput LSTM branch + featuresInput dense branch
```

### هدف

برای trend_signal یک benchmark غیر-WaveNet بسازیم تا بفهمیم مشکل از معماری است یا target.

### معماری پیشنهادی ShadBotTrader

```text
Input A: return sequence window, shape [window, 1]
  → causal Conv/GRU/LSTM small

Input B: selected engineered features, shape [feature_count]
  → Dense/BatchNorm/Dropout

concat
→ Dense
→ output softmax 3-class یا sigmoid binary
```

### نکته

این فاز بعد از class weights/threshold/feature selection انجام شود، نه قبل.

---

## Phase 113 — random baseline / Monte Carlo / White Reality Check

### الهام

ari99:

```text
Random portfolios
Monte Carlo detrended returns
White's Reality Check
```

### هدف

جلوگیری از data snooping. وقتی چند مدل/threshold تست می‌کنیم، بهترین نتیجه ممکن است شانسی باشد.

### کارها

1. Random signal baseline با همان trade frequency.
2. Permutation test روی returns یا entries.
3. Monte Carlo distribution برای expectancy/return.
4. p-value گزارش شود:

```text
P(random_strategy_return >= model_return)
```

### فایل‌های درگیر

```text
src/ShadBotTrader/application/services/dual_model_backtest_service.py
scripts/backtest_significance_check.py
```

---

## Phase 114 — external/regime features مخصوص XAUUSD

### الهام

Alpaca/Onepagecode data provider idea + Leci37 news/fundamental suggestion.

### برای طلا، features مهم‌تر از stock news

```text
DXY trend/returns
US10Y yield
real yield proxy
VIX
CPI/FOMC/NFP calendar flag
London/NY session
day-of-week
weekly close location
volatility regime
```

### هدف

اگر جهت روزانه طلا با price-only feature حافظه ندارد، باید متغیرهای regime وارد شوند.

---

## Phase 115 — live/paper decision audit

### الهام

ari99 paper trading flow، ولی برای MT5/Alpari.

### هدف

هر تصمیم live کاملاً audit شود.

ثبت هر tick/decision:

```text
timestamp
symbol/timeframe
model_id/version
features fingerprint
probabilities/scores
thresholds
licenses pass/fail
predicted TP/SL
spread/slippage
order intent
broker result
```

---

## 7) اولویت اجرای پیشنهادی

ترتیب پیشنهادی من:

```text
1. Phase 107: trend_signal audit کامل
2. Phase 108: class weights + F1/PR-AUC
3. Phase 109: threshold calibration + heatmap backtest
4. Phase 110: feature selection train-only
5. Phase 111: POS/NEG binary event models
6. Phase 113: random/Monte Carlo/White Reality significance
7. Phase 112: دو-branch model benchmark
8. Phase 114: external/regime features
9. Phase 115: live decision audit
```

چرا این ترتیب؟

```text
اول باید target و metric درست شود.
بعد threshold و feature selection.
بعد مدل‌های جدید.
اگر اول معماری مدل را عوض کنیم، دوباره همان مشکل score تکرار می‌شود.
```

---

## 8) حکم نهایی برای ShadBotTrader

سه منبع همگی یک پیام مشترک دارند:

```text
مدل را مجبور نکن قیمت/score دقیق آینده را regression کند.
به جای آن، event/action target بساز، class imbalance را درست کن، threshold را کالیبره کن، و نتیجه را با backtest/statistical significance بسنج.
```

برای ShadBotTrader:

```text
trend_score بماند secondary/research.
trend_signal و event-based classifiers باید مسیر اصلی شوند.
range model برای TP/SL و bracket همچنان نقطهٔ قوت پروژه است.
edge باید از ترکیب event model + range bracket + session/regime filters + threshold calibration بیاید.
```
