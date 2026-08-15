\# SHADBOT ENTERPRISE AI TRADING PLATFORM

\# PHASE 03 — DOMAIN MODEL



Document ID:

SHADBOT-ARCH-P03



Phase:

03 / 26



Status:

FINAL BASELINE



Architecture Style:

Enterprise

Domain-Driven Design

Clean Architecture

Dependency-Inverted

Framework-Independent



Primary Runtime:

Desktop / Local Computer



Web Dashboard:

NOT REQUIRED



Mobile Application:

NOT REQUIRED





\# 1. PURPOSE



Phase 03 مدل دامنه رسمی ShadBot را تعریف می‌کند.



این Phase مشخص می‌کند ShadBot از نظر Business چه مفاهیمی دارد، هر مفهوم چه مسئولیتی دارد، چه چیزهایی Entity هستند، چه چیزهایی Value Object هستند، چه چیزهایی Aggregate هستند، چه Domain Serviceهایی لازم هستند و ارتباط بین Bounded Contextها چگونه است.



هدف این Phase این است که قبل از ساخت Application، Engine، Infrastructure و GUI، یک زبان مشترک و پایدار برای کل سیستم داشته باشیم.



Domain Model نباید بر اساس:



&#x20;   Broker API

&#x20;   Database Schema

&#x20;   Pandas DataFrame

&#x20;   TensorFlow

&#x20;   Keras

&#x20;   NumPy

&#x20;   mplfinance

&#x20;   Matplotlib

&#x20;   GUI Framework



طراحی شود.



Domain باید Business-first باشد.





\# 2. DOMAIN MODELING PRINCIPLE



مدل اصلی ShadBot بر اساس این زنجیره مفهومی ساخته می‌شود:



&#x20;   MARKET

&#x20;      ↓

&#x20;   MARKET DATA

&#x20;      ↓

&#x20;   FEATURES

&#x20;      ↓

&#x20;   CONTEXT

&#x20;      ↓

&#x20;   PREDICTION

&#x20;      ↓

&#x20;   DECISION

&#x20;      ↓

&#x20;   RISK

&#x20;      ↓

&#x20;   ORDER

&#x20;      ↓

&#x20;   EXECUTION

&#x20;      ↓

&#x20;   PORTFOLIO



در کنار این زنجیره، سیستم‌های پشتیبان وجود دارند:



&#x20;   DATASET

&#x20;   TRAINING

&#x20;   MODEL

&#x20;   NEWS

&#x20;   SIMULATION

&#x20;   OPTIMIZATION

&#x20;   SELF-LEARNING

&#x20;   PROJECT INTELLIGENCE

&#x20;   SYSTEM CONFIGURATION





\# 3. BOUNDED CONTEXTS



Domain ShadBot به Bounded Contextهای زیر تقسیم می‌شود:



&#x20;   1. Common

&#x20;   2. Market

&#x20;   3. Dataset

&#x20;   4. Feature

&#x20;   5. News

&#x20;   6. Prediction

&#x20;   7. Trading

&#x20;   8. Portfolio

&#x20;   9. Simulation

&#x20;   10. AI / Training

&#x20;   11. Optimization

&#x20;   12. Self-Learning

&#x20;   13. Project Intelligence



هر Context باید زبان و مدل خودش را داشته باشد.



نباید یک Model عمومی برای همه سیستم‌ها ساخته شود.





\# 4. CURRENT PHYSICAL DOMAIN STRUCTURE



ساختار فعلی Repository:



&#x20;   src/

&#x20;   └── ShadBot/

&#x20;       └── Domain/

&#x20;           ├── \_\_init\_\_.py

&#x20;           ├── Common/

&#x20;           │   └── \_\_init\_\_.py

&#x20;           ├── Market/

&#x20;           │   └── \_\_init\_\_.py

&#x20;           ├── News/

&#x20;           │   └── \_\_init\_\_.py

&#x20;           ├── Prediction/

&#x20;           │   └── \_\_init\_\_.py

&#x20;           └── Trading/

&#x20;               └── \_\_init\_\_.py



این ساختار مبنای فعلی Domain است.



در ادامه معماری، Contextهای جدید مانند Dataset، Feature، Portfolio، Simulation و AI باید طبق همین اصول اضافه شوند.



هیچ Context جدیدی نباید صرفاً برای راحتی ساختاری ایجاد شود.





\# 5. COMMON DOMAIN



Common شامل مفاهیمی است که واقعاً بین چند Bounded Context مشترک هستند.



Common نباید تبدیل به محل نگهداری Business Logic عمومی شود.



Common می‌تواند شامل:



&#x20;   Identifier

&#x20;   Timestamp

&#x20;   TimeRange

&#x20;   TimeFrame

&#x20;   Symbol

&#x20;   Currency

&#x20;   Quantity

&#x20;   Price

&#x20;   Percentage

&#x20;   DecimalValue

&#x20;   DomainError

&#x20;   DomainEvent



باشد.





\# 6. VALUE OBJECT PRINCIPLE



Value Object هویت مستقل ندارد.



برابری آن بر اساس مقدار است.



نمونه:



&#x20;   Symbol("XAUUSD")

&#x20;   TimeFrame("5m")

&#x20;   Price(...)

&#x20;   Quantity(...)

&#x20;   Percentage(...)



Value Objectها باید:



&#x20;   Immutable

&#x20;   Validated

&#x20;   Side-effect free



باشند.





\# 7. IDENTIFIER



هر Entity باید Identifier پایدار داشته باشد.



نمونه:



&#x20;   MarketId

&#x20;   DatasetId

&#x20;   DatasetVersionId

&#x20;   FeatureSetId

&#x20;   PredictionId

&#x20;   OrderId

&#x20;   PositionId

&#x20;   PortfolioId

&#x20;   ModelId

&#x20;   TrainingRunId



Identifier نباید وابسته به Database auto-increment باشد.



Database می‌تواند Identifier را ذخیره کند، اما Domain نباید هویت خود را به Database واگذار کند.





\# 8. SYMBOL



Symbol یک Value Object است.



نمونه:



&#x20;   XAUUSD

&#x20;   BTCUSD

&#x20;   EURUSD



Symbol باید:



&#x20;   Normalized

&#x20;   Validated

&#x20;   Immutable



باشد.



Broker-specific symbol naming نباید مستقیماً Domain Symbol را آلوده کند.





\# 9. TIMEFRAME



TimeFrame یک Value Object است.



نمونه:



&#x20;   1m

&#x20;   5m

&#x20;   15m

&#x20;   1h

&#x20;   4h

&#x20;   1d



TimeFrame باید مفهوم مدت یک Candle را مشخص کند.



Broker API representation نباید بخشی از Domain Model باشد.





\# 10. TIMESTAMP



Timestamp باید:



&#x20;   timezone-aware

&#x20;   precise

&#x20;   comparable



باشد.



برای Market Data استفاده از UTC به عنوان canonical representation الزامی است.



نمایش Local Time صرفاً Presentation concern است.





\# 11. TIME RANGE



TimeRange یک Value Object است:



&#x20;   start

&#x20;   end



با قوانین:



&#x20;   start <= end



و هر دو Timestamp باید معتبر باشند.





\# 12. PRICE



Price یک Value Object است.



Price باید برای محاسبات مالی از precision مناسب استفاده کند.



استفاده از float برای Monetary/Financial semantics در Domain باید اجتناب شود.



Representation دقیق عددی باید در Domain مشخص باشد.



Implementation می‌تواند در Infrastructure/Analytics متفاوت باشد، اما Domain semantics باید deterministic باشد.





\# 13. QUANTITY



Quantity یک Value Object است.



برای:



&#x20;   Position Size

&#x20;   Order Quantity

&#x20;   Portfolio Holdings



استفاده می‌شود.



Quantity نباید منفی باشد مگر اینکه مفهوم خاص Domain آن را صریحاً اجازه دهد.





\# 14. PERCENTAGE



Percentage برای مفاهیمی مانند:



&#x20;   Return

&#x20;   Confidence

&#x20;   Risk

&#x20;   Allocation



استفاده می‌شود.



Range آن باید بر اساس semantics مشخص باشد.



مثلاً Confidence معمولاً:



&#x20;   0 <= confidence <= 1



است.





\# 15. MARKET CONTEXT



Market Context نمایانگر محیط بازاری در یک لحظه مشخص است.



Market Context می‌تواند شامل:



&#x20;   Symbol

&#x20;   TimeFrame

&#x20;   Timestamp

&#x20;   Current Price

&#x20;   Recent Market State

&#x20;   Volatility

&#x20;   Trend State

&#x20;   Liquidity Information

&#x20;   Feature References



باشد.



Market Context نباید به Broker Object وابسته باشد.





\# 16. CANDLE



Candle یکی از مهم‌ترین Domain Models است.



Candle شامل:



&#x20;   timestamp

&#x20;   open

&#x20;   high

&#x20;   low

&#x20;   close

&#x20;   volume



است.



در صورت نیاز می‌تواند شامل:



&#x20;   spread

&#x20;   tick\_volume

&#x20;   trade\_count



نیز باشد.



اما این موارد باید بر اساس Provider availability مدل شوند.





\# 17. CANDLE INVARIANTS



Candle باید قوانین زیر را حفظ کند:



&#x20;   high >= open

&#x20;   high >= close

&#x20;   high >= low



&#x20;   low <= open

&#x20;   low <= close



&#x20;   volume >= 0



Timestamp باید معتبر باشد.



Open/High/Low/Close باید Price معتبر باشند.





\# 18. CANDLE IDENTITY



Candle به صورت پیش‌فرض Value-like Market Data Record است.



برای شناسایی یک Candle در Dataset می‌توان ترکیب:



&#x20;   Symbol

&#x20;   TimeFrame

&#x20;   Timestamp



را استفاده کرد.



این ترکیب باید در Dataset uniqueness rule رعایت شود.





\# 19. MARKET



Market نمایانگر یک بازار قابل معامله است.



Market می‌تواند شامل:



&#x20;   MarketId

&#x20;   Name

&#x20;   Type

&#x20;   Currency

&#x20;   Trading Schedule

&#x20;   Supported Symbols



باشد.



Market نباید Broker-specific باشد.





\# 20. MARKET SESSION



MarketSession بیانگر وضعیت یک Market در یک بازه زمانی است.



نمونه:



&#x20;   Open

&#x20;   Closed

&#x20;   PreOpen

&#x20;   PostClose



این Model برای Live Trading و Historical Simulation اهمیت دارد.





\# 21. MARKET DATA SET



MarketDataSet مجموعه‌ای از Market Data با Metadata مشخص است.



Dataset باید حداقل Metadata زیر را داشته باشد:



&#x20;   DatasetId

&#x20;   Symbol

&#x20;   TimeFrame

&#x20;   StartTimestamp

&#x20;   EndTimestamp

&#x20;   Version

&#x20;   Source

&#x20;   CreatedAt



Dataset باید قابل Versioning باشد.





\# 22. DATASET VERSION



DatasetVersion نشان‌دهنده یک وضعیت immutable از Dataset است.



هر Update مهم باید بتواند Version جدید ایجاد کند.



نمونه:



&#x20;   Dataset v1

&#x20;   Dataset v2

&#x20;   Dataset v3



Dataset Version برای:



&#x20;   Training

&#x20;   Reproducibility

&#x20;   Backtesting

&#x20;   Audit



ضروری است.





\# 23. DATASET UPDATE



Dataset Update یک عملیات Domain/Application-level برای افزودن داده جدید است.



قوانین:



&#x20;   Duplicate Candle نباید ایجاد شود.

&#x20;   Timestampهای معتبر باید حفظ شوند.

&#x20;   Data Gap باید قابل تشخیص باشد.

&#x20;   Data Source باید ثبت شود.

&#x20;   Version باید قابل Trace باشد.





\# 24. HISTORICAL DATA



Historical Dataset برای:



&#x20;   Training

&#x20;   Validation

&#x20;   Backtesting

&#x20;   Analysis

&#x20;   Feature Engineering



استفاده می‌شود.



Historical Dataset می‌تواند بسیار بزرگ باشد.



این داده با Live Window یک مفهوم متفاوت دارد.





\# 25. LIVE DATA WINDOW



Live Data Window مجموعه‌ای از آخرین Candleهای دریافت‌شده برای تصمیم‌گیری لحظه‌ای است.



مثلاً:



&#x20;   500 candles



می‌تواند Window اصلی Prediction باشد.



اما این عدد نباید به صورت Hardcoded در Domain Model باشد.



Window Size باید Configuration/Policy باشد.





\# 26. CALCULATION WINDOW VS INFERENCE WINDOW



ShadBot دو مفهوم متفاوت دارد:



&#x20;   Calculation Window

&#x20;   Inference Window



مثلاً:



&#x20;   Calculation Window = 1000 candles

&#x20;   Inference Window = 500 candles



Calculation Window برای محاسبه Featureها استفاده می‌شود.



Inference Window داده‌ای است که در نهایت به Model داده می‌شود.



این دو نباید یکی فرض شوند.





\# 27. FEATURE



Feature یک مقدار مشتق‌شده از Market Data است.



نمونه:



&#x20;   SMA

&#x20;   EMA

&#x20;   RSI

&#x20;   MACD

&#x20;   ATR

&#x20;   Volatility

&#x20;   Momentum



Feature باید دارای Metadata باشد:



&#x20;   FeatureName

&#x20;   FeatureVersion

&#x20;   Timestamp

&#x20;   Value

&#x20;   Source Window





\# 28. FEATURE DEFINITION



FeatureDefinition مشخص می‌کند یک Feature چگونه محاسبه می‌شود.



مثلاً:



&#x20;   RSI(14)



یا:



&#x20;   SMA(50)



FeatureDefinition باید قابل Versioning باشد.



تغییر فرمول Feature باید بتواند Version جدید ایجاد کند.





\# 29. FEATURE SET



FeatureSet مجموعه‌ای از Featureهای مشخص برای یک Task است.



مثلاً:



&#x20;   TradingFeatureSet

&#x20;   PredictionFeatureSet

&#x20;   TrainingFeatureSet



FeatureSet باید Version داشته باشد.





\# 30. FEATURE DATASET



FeatureDataset نسخه Feature-engineered شده Dataset است.



رابطه:



&#x20;   Raw Dataset

&#x20;       ↓

&#x20;   Feature Engineering

&#x20;       ↓

&#x20;   Feature Dataset



Feature Dataset باید بتواند به:



&#x20;   DatasetVersion

&#x20;   FeatureSetVersion



اشاره کند.





\# 31. LIVE FEATURE STATE



Live Feature State مجموعه Featureهای محاسبه‌شده برای Live Market Window است.



ساختار مفهومی:



&#x20;   Live Candles

&#x20;       ↓

&#x20;   Calculation Window

&#x20;       ↓

&#x20;   Feature Calculation

&#x20;       ↓

&#x20;   Live Feature State

&#x20;       ↓

&#x20;   Inference Window





\# 32. PREDICTION CONTEXT



Prediction Context داده‌ای است که Model برای Prediction دریافت می‌کند.



Prediction Context می‌تواند شامل:



&#x20;   Symbol

&#x20;   TimeFrame

&#x20;   Timestamp

&#x20;   Feature Window

&#x20;   Market Context

&#x20;   Model Version

&#x20;   Feature Version



باشد.





\# 33. PREDICTION



Prediction نتیجه Model Inference است.



Prediction باید شامل:



&#x20;   PredictionId

&#x20;   Timestamp

&#x20;   Symbol

&#x20;   ModelId

&#x20;   ModelVersion

&#x20;   PredictionType

&#x20;   Value

&#x20;   Confidence



باشد.





\# 34. PREDICTION TYPE



PredictionType مشخص می‌کند Prediction چه چیزی را پیش‌بینی می‌کند.



نمونه:



&#x20;   FuturePrice

&#x20;   PriceChange

&#x20;   Return

&#x20;   Direction

&#x20;   Probability

&#x20;   SignalScore



Architecture نباید به یک نوع Prediction محدود شود.





\# 35. PREDICTION HORIZON



Prediction باید Horizon داشته باشد.



مثلاً:



&#x20;   next 1 candle

&#x20;   next 3 candles

&#x20;   next 12 candles



Horizon باید explicit باشد.



Prediction بدون Horizon در Contextهای Time-Series ناقص است.





\# 36. CONFIDENCE



Prediction Confidence میزان اطمینان Model نسبت به Prediction است.



Confidence باید:



&#x20;   normalized

&#x20;   bounded

&#x20;   traceable



باشد.



Confidence نباید مستقیماً به Trading Action تبدیل شود.





\# 37. MODEL



Model یک Domain Concept است.



Model شامل:



&#x20;   ModelId

&#x20;   Version

&#x20;   ModelType

&#x20;   FeatureSetVersion

&#x20;   TrainingDatasetVersion

&#x20;   CreatedAt

&#x20;   Status



است.



Model Domain نباید TensorFlow/Keras-specific باشد.





\# 38. MODEL VERSION



هر Model باید Version داشته باشد.



مثلاً:



&#x20;   model-v1

&#x20;   model-v2

&#x20;   model-v3



Model Version باید قابل Trace به:



&#x20;   Dataset Version

&#x20;   Feature Version

&#x20;   Training Configuration

&#x20;   Evaluation Result



باشد.





\# 39. MODEL STATUS



Model Status می‌تواند شامل:



&#x20;   Candidate

&#x20;   Evaluated

&#x20;   Approved

&#x20;   Production

&#x20;   Archived

&#x20;   Rejected



باشد.



Promotion باید Lifecycle رسمی داشته باشد.





\# 40. TRAINING RUN



TrainingRun نمایانگر یک اجرای Training است.



TrainingRun باید شامل:



&#x20;   TrainingRunId

&#x20;   DatasetVersion

&#x20;   FeatureSetVersion

&#x20;   ModelConfiguration

&#x20;   StartedAt

&#x20;   FinishedAt

&#x20;   Metrics

&#x20;   Result

&#x20;   ProducedModelVersion



باشد.





\# 41. TRAINING REPRODUCIBILITY



TrainingRun باید بتواند مشخص کند:



&#x20;   چه Datasetی استفاده شد.

&#x20;   چه Feature Versionی استفاده شد.

&#x20;   چه Configurationی استفاده شد.

&#x20;   چه Model Architectureی استفاده شد.

&#x20;   چه Seedی استفاده شد.

&#x20;   چه نسخه‌ای از Model ایجاد شد.



هدف:



&#x20;   Reproducible Training





\# 42. MODEL EVALUATION



ModelEvaluation نتیجه ارزیابی Model است.



می‌تواند شامل:



&#x20;   Accuracy

&#x20;   MAE

&#x20;   RMSE

&#x20;   Directional Accuracy

&#x20;   Precision

&#x20;   Recall

&#x20;   F1

&#x20;   Profitability Metrics



باشد.



Metricها باید Task-specific باشند.





\# 43. MODEL PROMOTION



ModelPromotion عملیاتی است که یک Candidate Model را به Production منتقل می‌کند.



قانون:



&#x20;   Training

&#x20;       ≠

&#x20;   Production



Promotion باید پس از Evaluation انجام شود.





\# 44. TRADING CONTEXT



Trading Context وضعیت لازم برای تصمیم‌گیری Trading را فراهم می‌کند.



می‌تواند شامل:



&#x20;   Market Context

&#x20;   Prediction

&#x20;   Portfolio State

&#x20;   Risk State

&#x20;   Strategy State



باشد.





\# 45. TRADING SIGNAL



TradingSignal خروجی Strategy/Decision Logic است.



مثلاً:



&#x20;   BUY

&#x20;   SELL

&#x20;   HOLD



اما Signal به معنی Order نیست.





\# 46. SIGNAL STRENGTH



Signal می‌تواند Strength داشته باشد.



مثلاً:



&#x20;   score

&#x20;   confidence

&#x20;   expected\_return



Signal باید مستقل از Broker Order باشد.





\# 47. TRADING DECISION



TradingDecision تصمیم رسمی سیستم برای اقدام یا عدم اقدام است.



می‌تواند شامل:



&#x20;   Signal

&#x20;   Confidence

&#x20;   Expected Price

&#x20;   Target

&#x20;   Stop

&#x20;   Position Intent

&#x20;   Risk Constraints



باشد.





\# 48. ORDER INTENT



OrderIntent بیان می‌کند سیستم قصد چه عملی را دارد.



مثلاً:



&#x20;   Buy

&#x20;   Sell

&#x20;   Close

&#x20;   Reduce

&#x20;   Increase



OrderIntent هنوز Broker Order نیست.





\# 49. ORDER



Order یک Trading Domain Entity است.



Order می‌تواند شامل:



&#x20;   OrderId

&#x20;   Symbol

&#x20;   Side

&#x20;   Quantity

&#x20;   OrderType

&#x20;   Price

&#x20;   StopLoss

&#x20;   TakeProfit

&#x20;   TimeInForce

&#x20;   Status



باشد.





\# 50. ORDER TYPE



OrderType می‌تواند شامل:



&#x20;   Market

&#x20;   Limit

&#x20;   Stop

&#x20;   StopLimit



باشد.



Broker-specific Order Types باید در Adapter Mapping شوند.





\# 51. ORDER SIDE



OrderSide:



&#x20;   Buy

&#x20;   Sell



است.



این مفهوم Domain-level است.





\# 52. ORDER STATUS



OrderStatus:



&#x20;   Pending

&#x20;   Submitted

&#x20;   PartiallyFilled

&#x20;   Filled

&#x20;   Cancelled

&#x20;   Rejected

&#x20;   Expired



می‌تواند باشد.





\# 53. EXECUTION



Execution نتیجه اجرای Order است.



Execution شامل:



&#x20;   ExecutionId

&#x20;   OrderId

&#x20;   Timestamp

&#x20;   Quantity

&#x20;   Price

&#x20;   Fees



می‌تواند باشد.





\# 54. POSITION



Position وضعیت مالکیت یک Asset/Symbol است.



Position می‌تواند شامل:



&#x20;   PositionId

&#x20;   Symbol

&#x20;   Quantity

&#x20;   AveragePrice

&#x20;   UnrealizedPnL

&#x20;   RealizedPnL



باشد.





\# 55. PORTFOLIO



Portfolio مجموعه Positionها و وضعیت سرمایه است.



Portfolio می‌تواند شامل:



&#x20;   PortfolioId

&#x20;   Cash

&#x20;   Positions

&#x20;   Equity

&#x20;   Margin

&#x20;   Exposure

&#x20;   PnL



باشد.



Portfolio نباید Broker-specific باشد.





\# 56. RISK STATE



RiskState وضعیت فعلی Risk سیستم است.



می‌تواند شامل:



&#x20;   Exposure

&#x20;   Drawdown

&#x20;   Position Limits

&#x20;   Daily Loss

&#x20;   Risk Score



باشد.





\# 57. RISK POLICY



RiskPolicy قوانین قابل اعمال روی Trading Decision است.



نمونه:



&#x20;   Maximum Position Size

&#x20;   Maximum Exposure

&#x20;   Maximum Drawdown

&#x20;   Daily Loss Limit



RiskPolicy نباید به Broker SDK وابسته باشد.





\# 58. STRATEGY



Strategy تعریف می‌کند سیستم چگونه از Context به Signal/Decision می‌رسد.



Strategy می‌تواند:



&#x20;   Prediction-driven

&#x20;   Rule-based

&#x20;   Hybrid

&#x20;   Optimization-based



باشد.



Strategy نباید Broker-specific باشد.





\# 59. NEWS



News Domain برای اطلاعات خبری است.



NewsArticle می‌تواند شامل:



&#x20;   NewsId

&#x20;   Source

&#x20;   Title

&#x20;   PublishedAt

&#x20;   Content Reference

&#x20;   Sentiment

&#x20;   Related Symbols



باشد.



News Provider Implementation خارج از Domain است.





\# 60. NEWS SENTIMENT



Sentiment می‌تواند:



&#x20;   Positive

&#x20;   Negative

&#x20;   Neutral



یا یک Score نرمال‌شده باشد.



Sentiment باید مستقل از NLP Framework باشد.





\# 61. SIMULATION



Simulation Domain برای:



&#x20;   Backtesting

&#x20;   Replay

&#x20;   Paper Trading

&#x20;   Historical Simulation



استفاده می‌شود.



Simulation باید بتواند بدون Broker واقعی اجرا شود.





\# 62. SIMULATION RUN



SimulationRun شامل:



&#x20;   SimulationId

&#x20;   DatasetVersion

&#x20;   FeatureSetVersion

&#x20;   ModelVersion

&#x20;   StrategyVersion

&#x20;   Configuration

&#x20;   Start

&#x20;   End

&#x20;   Results



است.





\# 63. BACKTEST



Backtest یک نوع Simulation است.



Backtest باید deterministic تا حد امکان باشد.



ورودی‌ها باید versioned باشند.





\# 64. REPLAY



Replay اجرای Timeline تاریخی به صورت sequential است.



Replay باید بتواند:



&#x20;   Candle

&#x20;      ↓

&#x20;   Context

&#x20;      ↓

&#x20;   Feature

&#x20;      ↓

&#x20;   Prediction

&#x20;      ↓

&#x20;   Decision



را در ترتیب زمانی بازسازی کند.





\# 65. OPTIMIZATION



Optimization برای یافتن Parameter Configuration مناسب است.



Optimization باید:



&#x20;   Objective

&#x20;   Search Space

&#x20;   Constraints

&#x20;   Candidate

&#x20;   Result



داشته باشد.



Optimizer نباید به یک Model خاص وابسته باشد.





\# 66. SELF-LEARNING



Self-Learning چرخه به‌روزرسانی Modelها است.



چرخه:



&#x20;   New Data

&#x20;      ↓

&#x20;   Dataset Update

&#x20;      ↓

&#x20;   Feature Update

&#x20;      ↓

&#x20;   Training

&#x20;      ↓

&#x20;   Evaluation

&#x20;      ↓

&#x20;   Promotion





\# 67. SELF-LEARNING RULE



Self-Learning نباید:



&#x20;   blindly overwrite production model



کند.



هر Model جدید باید:



&#x20;   versioned

&#x20;   evaluated

&#x20;   traceable



باشد.





\# 68. DATA FRESHNESS



Domain باید مفهوم Freshness را در جاهایی که لازم است پشتیبانی کند.



Market Data می‌تواند:



&#x20;   Fresh

&#x20;   Delayed

&#x20;   Stale

&#x20;   Invalid



باشد.



Live Trading نباید بر اساس داده‌ای که از Freshness Policy خارج شده تصمیم بگیرد.





\# 69. DATA QUALITY



Market Data باید قابلیت ثبت Quality Status داشته باشد.



مثلاً:



&#x20;   Valid

&#x20;   Invalid

&#x20;   Suspicious

&#x20;   Incomplete



Data Quality نباید صرفاً به Database Validation محدود شود.





\# 70. DATA GAP



DataGap زمانی رخ می‌دهد که انتظار می‌رود Candle وجود داشته باشد ولی وجود ندارد.



DataGap باید قابل شناسایی باشد.



این موضوع برای:



&#x20;   Feature Engineering

&#x20;   Training

&#x20;   Backtest

&#x20;   Live Trading



اهمیت دارد.





\# 71. DOMAIN EVENTS



Domain Eventها تغییرات مهم Domain را اعلام می‌کنند.



نمونه:



&#x20;   CandleReceived

&#x20;   DatasetUpdated

&#x20;   FeatureSetGenerated

&#x20;   PredictionGenerated

&#x20;   TradingDecisionCreated

&#x20;   OrderSubmitted

&#x20;   OrderFilled

&#x20;   ModelTrained

&#x20;   ModelPromoted

&#x20;   SimulationCompleted





\# 72. DOMAIN EVENT RULE



Event باید:



&#x20;   Immutable

&#x20;   Serializable

&#x20;   Versioned



باشد.



Event نباید Reference مستقیم به Objectهای Runtime داشته باشد.





\# 73. AGGREGATE PRINCIPLE



Aggregate مرز Consistency است.



Aggregate باید کوچک نگه داشته شود.



نباید کل Trading System را یک Aggregate در نظر گرفت.





\# 74. MARKET AGGREGATE



Market می‌تواند Aggregate Root مربوط به Market Configuration باشد.



اما Historical Candleهای بزرگ نباید داخل یک Market Aggregate نگهداری شوند.



Market Data باید خارج از Aggregate lifecycle اصلی مدیریت شود.





\# 75. DATASET AGGREGATE



DatasetVersion می‌تواند Aggregate Root مربوط به Dataset Versioning باشد.



Aggregate باید Metadata و Invariants را کنترل کند.



Storage واقعی داده‌های حجیم در Infrastructure انجام می‌شود.





\# 76. MODEL AGGREGATE



ModelVersion می‌تواند Aggregate Root برای Model Lifecycle باشد.



Model:



&#x20;   Candidate

&#x20;   Evaluated

&#x20;   Approved

&#x20;   Production

&#x20;   Archived



را کنترل می‌کند.





\# 77. TRADING AGGREGATE



Order می‌تواند Aggregate Root مستقل باشد.



Order lifecycle:



&#x20;   Created

&#x20;      ↓

&#x20;   Submitted

&#x20;      ↓

&#x20;   PartiallyFilled / Filled

&#x20;      ↓

&#x20;   Closed / Cancelled / Rejected





\# 78. PORTFOLIO AGGREGATE



Portfolio می‌تواند Aggregate Root باشد.



Positionها بخشی از Portfolio state هستند.



Portfolio باید Invariantهای مربوط به:



&#x20;   Exposure

&#x20;   Cash

&#x20;   Position



را حفظ کند.





\# 79. AGGREGATE BOUNDARY RULE



Aggregateها نباید برای هر تغییر کوچک Aggregate دیگر را مستقیماً mutate کنند.



Cross-Aggregate communication ترجیحاً از طریق:



&#x20;   Application Service

&#x20;   Domain Event

&#x20;   Explicit Command



انجام شود.





\# 80. DOMAIN SERVICES



Domain Service زمانی استفاده می‌شود که:



&#x20;   Business Rule

&#x20;   به یک Entity خاص تعلق ندارد.



نمونه:



&#x20;   PositionSizingService

&#x20;   RiskEvaluationService

&#x20;   SignalEvaluationService



اما Domain Service نباید Infrastructure Service باشد.





\# 81. DOMAIN POLICIES



Policy برای Business Rule قابل تغییر مناسب است.



نمونه:



&#x20;   RiskPolicy

&#x20;   PositionSizingPolicy

&#x20;   MarketSessionPolicy

&#x20;   ModelPromotionPolicy



Policy باید قابل تست باشد.





\# 82. DOMAIN FACTORIES



Factory برای ساخت Objectهای پیچیده استفاده می‌شود.



مثلاً:



&#x20;   PredictionFactory

&#x20;   OrderFactory

&#x20;   DatasetVersionFactory

&#x20;   TrainingRunFactory



Factory نباید Infrastructure Object بسازد.





\# 83. DOMAIN REPOSITORY CONTRACTS



Repository Contractهای اصلی می‌توانند شامل:



&#x20;   MarketRepository

&#x20;   DatasetRepository

&#x20;   FeatureRepository

&#x20;   ModelRepository

&#x20;   PortfolioRepository

&#x20;   OrderRepository



باشند.



Implementation آنها در Infrastructure قرار می‌گیرد.





\# 84. DOMAIN INVARIANTS



Invariant یعنی قانونی که Object نباید نقض کند.



نمونه:



&#x20;   Candle:

&#x20;       high >= max(open, close)

&#x20;       low <= min(open, close)



&#x20;   Quantity:

&#x20;       valid domain range



&#x20;   Percentage:

&#x20;       valid domain range



&#x20;   Order:

&#x20;       quantity > 0



&#x20;   TimeRange:

&#x20;       start <= end



&#x20;   Prediction:

&#x20;       valid horizon



Invariant باید در نزدیک‌ترین Domain Boundary enforce شود.





\# 85. DOMAIN DOES NOT GUARANTEE EXTERNAL TRUTH



Domain Model مسئول تضمین حقیقت External System نیست.



مثلاً:



&#x20;   Broker says order filled



این External Fact است.



Adapter آن را به Domain Event/Execution تبدیل می‌کند.



Domain سپس State خود را به‌روزرسانی می‌کند.





\# 86. LIVE VS HISTORICAL DOMAIN



Historical Data و Live Data باید Semantic مشترک داشته باشند، اما Lifecycle متفاوت دارند.



Historical:



&#x20;   Persistent

&#x20;   Versioned

&#x20;   Large

&#x20;   Training-oriented



Live:



&#x20;   Ephemeral

&#x20;   Time-sensitive

&#x20;   Windowed

&#x20;   Decision-oriented



نباید این دو را یک Storage Concept واحد فرض کرد.





\# 87. FIXED TRAINING WINDOW



Training Window یک Policy است.



مثلاً:



&#x20;   500 candles



اگر Architecture Training نیاز به Window ثابت داشته باشد، این باید به عنوان Training Configuration ثبت شود.



Training Dataset نباید به شکل uncontrolled با Windowهای متغیر ساخته شود.





\# 88. ONLINE CALCULATION WINDOW



Online Feature Calculation Window می‌تواند بزرگ‌تر از Inference Window باشد.



مثلاً:



&#x20;   Calculation:

&#x20;       1000 candles



&#x20;   Inference:

&#x20;       500 candles



این تفاوت باید در Domain/Configuration قابل بیان باشد.





\# 89. INFERENCE WINDOW



Inference Window ورودی نهایی Model است.



مثلاً:



&#x20;   500 candles



Inference Window باید:



&#x20;   Symbol

&#x20;   TimeFrame

&#x20;   FeatureSet

&#x20;   Timestamp



را به صورت قابل Trace همراه خود داشته باشد.





\# 90. DATA VERSION TRACEABILITY



هر Prediction مهم باید بتواند مشخص کند از چه اطلاعاتی ساخته شده است.



حداقل:



&#x20;   Model Version

&#x20;   Feature Version

&#x20;   Timestamp

&#x20;   Symbol

&#x20;   TimeFrame



و در صورت امکان:



&#x20;   Dataset/Data Snapshot Reference



باید قابل Trace باشد.





\# 91. TRADING DECISION TRACEABILITY



هر Trading Decision باید بتواند به:



&#x20;   Prediction

&#x20;   Strategy

&#x20;   Risk Evaluation

&#x20;   Portfolio State



ردیابی شود.



هدف:



&#x20;   Explainability

&#x20;   Auditability

&#x20;   Debuggability





\# 92. ORDER TRACEABILITY



Order باید بتواند به:



&#x20;   TradingDecision

&#x20;   Signal

&#x20;   RiskEvaluation



ردیابی شود.



Execution نیز باید بتواند به Order متصل شود.





\# 93. MODEL TRACEABILITY



Production Model باید بتواند به:



&#x20;   TrainingRun

&#x20;   DatasetVersion

&#x20;   FeatureSetVersion

&#x20;   Evaluation



ردیابی شود.





\# 94. DOMAIN MODEL RELATIONSHIP GRAPH



مدل مفهومی اصلی:



&#x20;   Market

&#x20;     │

&#x20;     └── MarketData

&#x20;            │

&#x20;            └── Candle

&#x20;                   │

&#x20;                   ├── Feature

&#x20;                   │      │

&#x20;                   │      └── FeatureSet

&#x20;                   │

&#x20;                   └── MarketContext

&#x20;                          │

&#x20;                          └── PredictionContext

&#x20;                                 │

&#x20;                                 └── Prediction

&#x20;                                        │

&#x20;                                        └── TradingDecision

&#x20;                                               │

&#x20;                                               ├── RiskEvaluation

&#x20;                                               │

&#x20;                                               └── OrderIntent

&#x20;                                                      │

&#x20;                                                      └── Order

&#x20;                                                             │

&#x20;                                                             └── Execution

&#x20;                                                                    │

&#x20;                                                                    └── Position

&#x20;                                                                           │

&#x20;                                                                           └── Portfolio





\# 95. TRAINING DOMAIN GRAPH



&#x20;   Raw Dataset

&#x20;        │

&#x20;        └── DatasetVersion

&#x20;               │

&#x20;               └── Feature Engineering

&#x20;                      │

&#x20;                      └── FeatureDataset

&#x20;                             │

&#x20;                             └── FeatureSetVersion

&#x20;                                    │

&#x20;                                    └── TrainingRun

&#x20;                                           │

&#x20;                                           └── ModelVersion

&#x20;                                                  │

&#x20;                                                  └── Evaluation

&#x20;                                                         │

&#x20;                                                         └── Promotion

&#x20;                                                                │

&#x20;                                                                └── Production Model





\# 96. LIVE TRADING DOMAIN GRAPH



&#x20;   Market Provider

&#x20;        │

&#x20;        └── Live Candles

&#x20;               │

&#x20;               └── Calculation Window

&#x20;                      │

&#x20;                      └── Feature Calculation

&#x20;                             │

&#x20;                             └── Live Feature State

&#x20;                                    │

&#x20;                                    └── Inference Window

&#x20;                                           │

&#x20;                                           └── Prediction

&#x20;                                                  │

&#x20;                                                  └── Decision

&#x20;                                                         │

&#x20;                                                         └── Risk

&#x20;                                                                │

&#x20;                                                                └── Order Intent

&#x20;                                                                       │

&#x20;                                                                       └── Order

&#x20;                                                                              │

&#x20;                                                                              └── Execution





\# 97. BACKTEST DOMAIN GRAPH



&#x20;   DatasetVersion

&#x20;        │

&#x20;        └── Replay

&#x20;               │

&#x20;               └── Historical Timeline

&#x20;                      │

&#x20;                      └── Feature Calculation

&#x20;                             │

&#x20;                             └── Prediction

&#x20;                                    │

&#x20;                                    └── Decision

&#x20;                                           │

&#x20;                                           └── Simulated Risk

&#x20;                                                  │

&#x20;                                                  └── Simulated Execution

&#x20;                                                         │

&#x20;                                                         └── Simulation Result





\# 98. DOMAIN MODEL RULE FOR GUI



GUI visualization is not part of Domain.



مثلاً:



&#x20;   Candlestick Chart

&#x20;   Prediction Line

&#x20;   Buy Marker

&#x20;   Sell Marker

&#x20;   Stop Loss Line

&#x20;   Take Profit Line



همگی Presentation/Visualization concepts هستند.



Domain فقط داده و معنای Business را فراهم می‌کند.





\# 99. DOMAIN MODEL RULE FOR MPLFINANCE



mplfinance یک Visualization Technology است.



Domain نباید آن را بشناسد.



صحیح:



&#x20;   Domain Candle

&#x20;       ↓

&#x20;   Visualization DTO

&#x20;       ↓

&#x20;   Chart Adapter

&#x20;       ↓

&#x20;   mplfinance



غلط:



&#x20;   Domain Candle

&#x20;       ↓

&#x20;   mplfinance object





\# 100. DOMAIN MODEL RULE FOR DESKTOP EXECUTION



ShadBot Desktop Application است.



Domain باید مستقل از:



&#x20;   Windows

&#x20;   PowerShell

&#x20;   Desktop GUI Toolkit



باقی بماند.



Desktop Runtime فقط Composition و Presentation را مدیریت می‌کند.





\# 101. DOMAIN MODEL RULE FOR CONFIGURATION



Domain Entityها نباید Configuration File را مستقیماً بخوانند.



مثلاً:



&#x20;   Order



نباید بداند config.yaml کجاست.



Configuration باید توسط Application/Runtime به Policy یا Value Object تبدیل شود.





\# 102. DOMAIN MODEL RULE FOR PERSISTENCE



Domain Object نباید:



&#x20;   save()

&#x20;   delete()

&#x20;   query\_database()



به شکل Persistence-aware داشته باشد.



Persistence مسئولیت Repository/Infrastructure است.





\# 103. DOMAIN MODEL RULE FOR SERIALIZATION



Domain Object نباید برای JSON، ORM یا Database Schema بیش از حد طراحی شود.



Serialization Mapping باید خارج از Core Business Model انجام شود.





\# 104. DOMAIN MODEL RULE FOR EXTERNAL DATA



External Data باید قبل از ورود به Domain:



&#x20;   Validate

&#x20;   Normalize

&#x20;   Map



شود.



ساختار:



&#x20;   External DTO

&#x20;       ↓

&#x20;   Adapter

&#x20;       ↓

&#x20;   Validation

&#x20;       ↓

&#x20;   Domain Model





\# 105. DOMAIN MODEL RULE FOR MACHINE LEARNING



ML Model خروجی Business Domain نیست.



ML یک Capability است.



Domain باید:



&#x20;   Prediction



را بشناسد.



اما نباید:



&#x20;   Tensor

&#x20;   Layer

&#x20;   Optimizer

&#x20;   Loss Function



را به عنوان Business Entity بشناسد.





\# 106. DOMAIN MODEL RULE FOR FEATURES



Feature محاسبه‌شده Business-relevant است.



اما Algorithm محاسبه Feature، Domain Entity نیست.



مثلاً:



&#x20;   RSI



می‌تواند Domain Concept باشد.



اما:



&#x20;   pandas\_ta.rsi()



جزئیات Implementation است.





\# 107. DOMAIN MODEL RULE FOR BROKER SYMBOL MAPPING



Broker ممکن است:



&#x20;   XAUUSD

&#x20;   GOLD

&#x20;   XAU/USD



را برای یک مفهوم مشابه استفاده کند.



Domain Symbol باید Canonical باشد.



Mapping:



&#x20;   Canonical Symbol

&#x20;         ↓

&#x20;   Broker Adapter

&#x20;         ↓

&#x20;   Broker Symbol





\# 108. DOMAIN MODEL RULE FOR CURRENCY



Currency یک Value Object است.



Domain باید Currency را به شکل استاندارد و مستقل از Broker نگه دارد.





\# 109. DOMAIN MODEL RULE FOR FEES



Fees بخشی از Trading/Execution Domain است.



Fee می‌تواند شامل:



&#x20;   amount

&#x20;   currency

&#x20;   type



باشد.



Broker-specific Fee Representation باید در Adapter تبدیل شود.





\# 110. DOMAIN MODEL RULE FOR PNL



PnL باید قابلیت تفکیک داشته باشد:



&#x20;   RealizedPnL

&#x20;   UnrealizedPnL



و در صورت نیاز:



&#x20;   GrossPnL

&#x20;   NetPnL



Fees و Costs باید در محاسبات مشخص باشند.





\# 111. DOMAIN MODEL RULE FOR EXPOSURE



Exposure یک Domain Concept است.



می‌تواند برای:



&#x20;   Position

&#x20;   Portfolio

&#x20;   Symbol

&#x20;   Market



محاسبه شود.



Exposure نباید به Database یا Broker API وابسته باشد.





\# 112. DOMAIN MODEL RULE FOR CAPITAL



Capital / Cash / Equity باید Domain semantics مشخص داشته باشند.



نباید صرفاً floatهای پراکنده در کل سیستم باشند.





\# 113. DOMAIN MODEL RULE FOR DECIMAL PRECISION



مقادیر مالی و معاملاتی حساس باید precision مشخص داشته باشند.



Implementation باید deterministic باشد.



Floating-point استفاده‌شده در Analytics نباید بدون کنترل وارد Monetary Domain شود.





\# 114. DOMAIN MODEL RULE FOR ENUMS



Enumهای Domain باید فقط مفاهیم Business را تعریف کنند.



مثلاً:



&#x20;   OrderSide

&#x20;   OrderType

&#x20;   OrderStatus

&#x20;   SignalType

&#x20;   ModelStatus



اما Enum مربوط به:



&#x20;   SQL Dialect

&#x20;   GUI Theme

&#x20;   Tensor Device



متعلق به Domain نیست.





\# 115. DOMAIN MODEL RULE FOR AGGREGATE REFERENCES



Aggregateها نباید Object Graphهای عظیم بسازند.



ترجیح:



&#x20;   Aggregate A

&#x20;      ↓

&#x20;   Identifier of Aggregate B



به‌جای:



&#x20;   Aggregate A

&#x20;      ↓

&#x20;   Full Aggregate B

&#x20;      ↓

&#x20;   Full Aggregate C





\# 116. DOMAIN MODEL RULE FOR LARGE DATA



Candleهای یک Dataset بزرگ نباید به شکل یک Python List عظیم داخل یک Domain Aggregate نگهداری شوند.



Domain مسئول:



&#x20;   Semantics

&#x20;   Metadata

&#x20;   Invariants

&#x20;   Version



است.



Infrastructure مسئول:



&#x20;   Efficient Storage

&#x20;   Chunking

&#x20;   Query

&#x20;   Compression



است.





\# 117. DOMAIN MODEL RULE FOR ONLINE BUFFER



Live Buffer یک Runtime/Domain-support concept است.



باید بتواند:



&#x20;   Append

&#x20;   Deduplicate

&#x20;   Trim

&#x20;   Query Window



کند.



اما Storage دائمی نیست.





\# 118. DOMAIN MODEL RULE FOR WINDOW



Window باید مفهوم مشخص داشته باشد:



&#x20;   size

&#x20;   timeframe

&#x20;   end timestamp



و در صورت نیاز:



&#x20;   start timestamp



داشته باشد.





\# 119. DOMAIN MODEL RULE FOR DATA QUALITY



هر داده‌ای که وارد Decision Pipeline می‌شود باید امکان مشخص کردن:



&#x20;   validity

&#x20;   freshness

&#x20;   completeness



را داشته باشد.





\# 120. DOMAIN MODEL RULE FOR DECISION SAFETY



Prediction به تنهایی مجوز Trading نیست.



Chain رسمی:



&#x20;   Prediction

&#x20;       ↓

&#x20;   Decision

&#x20;       ↓

&#x20;   Risk Evaluation

&#x20;       ↓

&#x20;   Execution Eligibility

&#x20;       ↓

&#x20;   Order



است.





\# 121. DOMAIN MODEL RULE FOR NO DIRECT PREDICTION → ORDER



این Rule قطعی است:



&#x20;   Prediction

&#x20;      ↓

&#x20;   Order



ممنوع.



باید:



&#x20;   Prediction

&#x20;      ↓

&#x20;   Strategy / Decision

&#x20;      ↓

&#x20;   Risk

&#x20;      ↓

&#x20;   Order Intent

&#x20;      ↓

&#x20;   Order



باشد.





\# 122. DOMAIN MODEL RULE FOR NO DIRECT DATA → ORDER



این نیز ممنوع است:



&#x20;   Market Data

&#x20;      ↓

&#x20;   Order



Market Data باید ابتدا Context و Decision را طی کند.





\# 123. DOMAIN MODEL RULE FOR MODEL → ORDER



Model نباید Order ایجاد کند.



Model فقط:



&#x20;   Prediction



تولید می‌کند.



Trading Domain تصمیم می‌گیرد.





\# 124. DOMAIN MODEL RULE FOR EXPLAINABILITY



هر Decision مهم باید قابلیت توضیح داشته باشد.



حداقل:



&#x20;   Prediction Reference

&#x20;   Strategy Reference

&#x20;   Risk Result

&#x20;   Decision Reason



باید قابل ثبت باشد.





\# 125. DOMAIN MODEL RULE FOR AUDIT



Critical Domain Events باید قابل Audit باشند.



نمونه:



&#x20;   ModelPromoted

&#x20;   TradingDecisionCreated

&#x20;   OrderSubmitted

&#x20;   OrderFilled

&#x20;   OrderRejected



Audit باید Immutable و Traceable باشد.





\# 126. DOMAIN MODEL RULE FOR VERSIONING



موارد زیر باید Version-aware باشند:



&#x20;   Dataset

&#x20;   Feature Definition

&#x20;   Feature Set

&#x20;   Model

&#x20;   Strategy

&#x20;   Training Configuration

&#x20;   Simulation Configuration



هدف:



&#x20;   Reproducibility

&#x20;   Auditability

&#x20;   Rollback

&#x20;   Comparison





\# 127. DOMAIN LANGUAGE



زبان رسمی Domain باید از اصطلاحات زیر استفاده کند:



&#x20;   Market

&#x20;   Symbol

&#x20;   TimeFrame

&#x20;   Candle

&#x20;   MarketContext

&#x20;   Dataset

&#x20;   DatasetVersion

&#x20;   Feature

&#x20;   FeatureDefinition

&#x20;   FeatureSet

&#x20;   FeatureSetVersion

&#x20;   Prediction

&#x20;   PredictionContext

&#x20;   PredictionHorizon

&#x20;   Model

&#x20;   ModelVersion

&#x20;   TrainingRun

&#x20;   Evaluation

&#x20;   Strategy

&#x20;   Signal

&#x20;   TradingDecision

&#x20;   Risk

&#x20;   OrderIntent

&#x20;   Order

&#x20;   Execution

&#x20;   Position

&#x20;   Portfolio

&#x20;   Simulation

&#x20;   Replay

&#x20;   Backtest

&#x20;   News

&#x20;   Event



استفاده از نام‌های مبهم مانند:



&#x20;   DataManager

&#x20;   AIManager

&#x20;   TradingManager

&#x20;   UtilsManager



برای Domain Model ممنوع است.





\# 128. DOMAIN MODEL NAMING



نام‌ها باید:



&#x20;   Explicit

&#x20;   Business-oriented

&#x20;   Stable

&#x20;   Framework-independent



باشند.



مثلاً:



&#x20;   Candle



بهتر از:



&#x20;   OHLCVDataFrame



است.



و:



&#x20;   Prediction



بهتر از:



&#x20;   ModelOutput



است.





\# 129. DOMAIN MODEL EVOLUTION



Domain Model باید قابلیت Evolution داشته باشد.



تغییرات آینده باید با:



&#x20;   Versioning

&#x20;   Migration

&#x20;   Compatibility Rules



مدیریت شوند.



اما نباید برای آینده‌ای نامعلوم Abstractionهای بی‌دلیل ساخته شوند.





\# 130. DOMAIN MODEL TESTABILITY



هر Domain Entity و Value Object مهم باید بدون:



&#x20;   Database

&#x20;   Broker

&#x20;   Network

&#x20;   GUI

&#x20;   ML Runtime



قابل Unit Test باشد.





\# 131. DOMAIN MODEL DETERMINISM



Domain Logic باید تا حد امکان deterministic باشد.



نتیجه Domain Rule نباید به:



&#x20;   Current System Time

&#x20;   Randomness

&#x20;   Network State

&#x20;   GUI State



وابسته باشد مگر اینکه Dependency صریحاً وارد مدل شده باشد.





\# 132. DOMAIN MODEL COMPLEXITY RULE



Domain باید فقط Complexity واقعی Business را مدل کند.



Overengineering ممنوع است.



نباید برای هر primitive یک Abstraction بدون دلیل ساخته شود.



هر Model باید:



&#x20;   Responsibility

&#x20;   Invariant

&#x20;   Business Meaning



داشته باشد.





\# 133. DOMAIN MODEL BOUNDARY SUMMARY



&#x20;                   SHADB0T DOMAIN



&#x20;   ┌─────────────────────────────────────────────┐

&#x20;   │                  COMMON                     │

&#x20;   │ IDs / Time / Symbol / Price / Quantity      │

&#x20;   └─────────────────────────────────────────────┘



&#x20;   ┌───────────────┐     ┌──────────────────────┐

&#x20;   │    MARKET     │────▶│       DATASET        │

&#x20;   │ Candle/Market │     │ Version/Quality      │

&#x20;   └───────┬───────┘     └──────────┬───────────┘

&#x20;           │                         │

&#x20;           ▼                         ▼

&#x20;   ┌─────────────────────────────────────────────┐

&#x20;   │                  FEATURE                    │

&#x20;   │ Feature / Definition / FeatureSet           │

&#x20;   └──────────────────────┬──────────────────────┘

&#x20;                          │

&#x20;                          ▼

&#x20;   ┌─────────────────────────────────────────────┐

&#x20;   │                PREDICTION                   │

&#x20;   │ Context / Prediction / Model Reference      │

&#x20;   └──────────────────────┬──────────────────────┘

&#x20;                          │

&#x20;                          ▼

&#x20;   ┌─────────────────────────────────────────────┐

&#x20;   │                  TRADING                    │

&#x20;   │ Signal / Decision / Risk / Order / Execution│

&#x20;   └──────────────────────┬──────────────────────┘

&#x20;                          │

&#x20;                          ▼

&#x20;   ┌─────────────────────────────────────────────┐

&#x20;   │                 PORTFOLIO                   │

&#x20;   │ Position / Equity / Exposure / PnL          │

&#x20;   └─────────────────────────────────────────────┘



&#x20;   Supporting Contexts:



&#x20;   AI / Training

&#x20;   News

&#x20;   Simulation

&#x20;   Optimization

&#x20;   Self-Learning

&#x20;   Project Intelligence





\# 134. PHASE 03 ACCEPTANCE CRITERIA



\[x] Domain purpose defined.

\[x] Bounded Contexts defined.

\[x] Common Domain concepts defined.

\[x] Value Object principles defined.

\[x] Entity principles defined.

\[x] Aggregate principles defined.

\[x] Candle defined.

\[x] Market defined.

\[x] Market Session defined.

\[x] Dataset defined.

\[x] Dataset Version defined.

\[x] Historical Data defined.

\[x] Live Data Window defined.

\[x] Calculation Window defined.

\[x] Inference Window defined.

\[x] Feature defined.

\[x] Feature Definition defined.

\[x] Feature Set defined.

\[x] Feature Dataset defined.

\[x] Prediction Context defined.

\[x] Prediction defined.

\[x] Prediction Horizon defined.

\[x] Model defined.

\[x] Model Version defined.

\[x] Training Run defined.

\[x] Model Evaluation defined.

\[x] Trading Signal defined.

\[x] Trading Decision defined.

\[x] Risk defined.

\[x] Order Intent defined.

\[x] Order defined.

\[x] Execution defined.

\[x] Position defined.

\[x] Portfolio defined.

\[x] News defined.

\[x] Simulation defined.

\[x] Replay defined.

\[x] Backtest defined.

\[x] Optimization defined.

\[x] Self-Learning defined.

\[x] Domain Events defined.

\[x] Repository Contracts defined.

\[x] Domain Services defined.

\[x] Domain Policies defined.

\[x] Domain Factories defined.

\[x] Domain Invariants defined.

\[x] Version Traceability defined.

\[x] Training Traceability defined.

\[x] Prediction Traceability defined.

\[x] Trading Decision Traceability defined.

\[x] Order Traceability defined.

\[x] Model Traceability defined.

\[x] Historical/Live separation defined.

\[x] Fixed Training Window concept defined.

\[x] Calculation Window / Inference Window separation defined.

\[x] GUI excluded from Domain.

\[x] mplfinance excluded from Domain.

\[x] Broker excluded from Domain.

\[x] Database excluded from Domain.

\[x] ML Framework excluded from Domain.

\[x] Large Dataset storage excluded from Domain Aggregate.

\[x] Prediction → Order direct dependency prohibited.

\[x] Model → Order direct dependency prohibited.

\[x] Market Data → Order direct dependency prohibited.

\[x] Domain testability defined.

\[x] Domain naming language defined.





\# 135. PHASE 03 FINAL STATUS



PHASE:

03 — DOMAIN MODEL



STATUS:

FINAL BASELINE



DOMAIN MODEL:

FROZEN AFTER APPROVAL



NEXT PHASE:

04 — PROJECT TREE / PHYSICAL ARCHITECTURE

