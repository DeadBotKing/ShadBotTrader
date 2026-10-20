\# SHADBOTTRADER ENTERPRISE AI TRADING PLATFORM

\# PHASE 02 — DEPENDENCY RULES



Document ID:

SHADBOTTRADER-ARCH-P02



Phase:

02 / 26



Status:

FINAL BASELINE



Architecture Style:

Enterprise

Domain-Driven

Dependency-Inverted

Layered

Plugin-Oriented

Event-Aware



Primary Language:

Python



Runtime:

Desktop / Local Computer



Web Dashboard:

NOT REQUIRED



Mobile Application:

NOT REQUIRED





\# 1. PURPOSE



این سند قوانین وابستگی ShadBotTrader را تعریف می‌کند.



Phase 01 مشخص کرد ShadBotTrader چه سیستمی است و چه اصولی باید رعایت شوند.



Phase 02 مشخص می‌کند:



\- چه لایه‌ای به چه لایه‌ای اجازه وابستگی دارد.

\- چه لایه‌ای نباید لایه دیگری را Import کند.

\- Domain چگونه از Infrastructure جدا می‌ماند.

\- Application چگونه Use Caseها را اجرا می‌کند.

\- Infrastructure چگونه Contractهای سیستم را پیاده‌سازی می‌کند.

\- Engineها چگونه با Domain و Application ارتباط برقرار می‌کنند.

\- Pluginها چگونه بدون آلوده کردن Core وارد سیستم می‌شوند.

\- GUI چگونه از Business Logic جدا می‌ماند.

\- Event Bus چگونه وابستگی مستقیم بین Subsystemها را کاهش می‌دهد.

\- Broker، Database، Filesystem، ML Framework و GUI Framework چگونه از Core جدا می‌شوند.



این سند پس از Freeze شدن، قانون Dependency Architecture پروژه است.



هیچ فایل یا کلاس جدیدی نباید Dependency Direction تعریف‌شده در این سند را نقض کند.





\# 2. FUNDAMENTAL DEPENDENCY RULE



قانون اصلی ShadBotTrader:



&#x20;   HIGH-LEVEL BUSINESS POLICY

&#x20;               ↓

&#x20;         DEPENDS ON

&#x20;               ↓

&#x20;          ABSTRACTIONS

&#x20;               ↑

&#x20;         IMPLEMENTED BY

&#x20;               ↑

&#x20;   LOW-LEVEL INFRASTRUCTURE



یعنی Business Logic نباید به Implementation جزئیات وابسته باشد.



به‌جای:



&#x20;   Domain → SQLAlchemy

&#x20;   Domain → MT5

&#x20;   Domain → Pandas

&#x20;   Domain → TensorFlow

&#x20;   Domain → mplfinance



باید داشته باشیم:



&#x20;   Domain

&#x20;      ↓

&#x20;   Contract / Port

&#x20;      ↑

&#x20;   Infrastructure Adapter





\# 3. DEPENDENCY DIRECTION



Dependency Direction استاندارد ShadBotTrader:



&#x20;   Domain

&#x20;     ↑

&#x20;   Application

&#x20;     ↑

&#x20;   Engines

&#x20;     ↑

&#x20;   Infrastructure

&#x20;     ↑

&#x20;   External Systems



اما این نمایش باید با یک اصل مهم خوانده شود:



&#x20;   Inner Layers

&#x20;        ↑

&#x20;   Outer Layers



لایه بیرونی می‌تواند به لایه داخلی وابسته باشد.



لایه داخلی نباید به لایه بیرونی وابسته باشد.





\# 4. ARCHITECTURAL LAYERS



ShadBotTrader از نظر Dependency دارای این حوزه‌های اصلی است:



&#x20;   1. Domain

&#x20;   2. Core

&#x20;   3. Application

&#x20;   4. Engines

&#x20;   5. Services

&#x20;   6. Interfaces

&#x20;   7. Infrastructure

&#x20;   8. Presentation / GUI

&#x20;   9. Plugins

&#x20;   10. External Systems



این لایه‌ها در مراحل بعدی دقیق‌تر به Package و Module تبدیل می‌شوند.





\# 5. DOMAIN LAYER



Domain داخلی‌ترین لایه Business Architecture است.



Domain شامل مفاهیم و قوانین بنیادی Business است.



نمونه:



&#x20;   Candle

&#x20;   Market

&#x20;   Symbol

&#x20;   TimeFrame

&#x20;   Dataset

&#x20;   Feature

&#x20;   Prediction

&#x20;   Model

&#x20;   Signal

&#x20;   Order

&#x20;   Position

&#x20;   Portfolio

&#x20;   Risk

&#x20;   Strategy

&#x20;   TrainingRun



Domain باید تا حد امکان Pure Python باشد.



Domain نباید به موارد زیر وابسته باشد:



&#x20;   Broker SDK

&#x20;   Database Driver

&#x20;   SQLAlchemy

&#x20;   Django

&#x20;   FastAPI

&#x20;   PyTorch

&#x20;   TensorFlow

&#x20;   Keras

&#x20;   Pandas

&#x20;   NumPy

&#x20;   mplfinance

&#x20;   Matplotlib

&#x20;   HTTP Client

&#x20;   Filesystem Implementation

&#x20;   GUI Framework

&#x20;   Operating System API



این موارد جزئیات بیرونی هستند.





\# 6. DOMAIN DEPENDENCY RULE



Domain فقط می‌تواند به:



&#x20;   Domain

&#x20;   Core-level primitives

&#x20;   Domain contracts

&#x20;   Standard Library abstractions در صورت نیاز



وابسته باشد.



Domain نباید به:



&#x20;   Application

&#x20;   Engines

&#x20;   Services

&#x20;   Infrastructure

&#x20;   GUI

&#x20;   Plugins



وابسته شود.





\# 7. DOMAIN IMPORT RULE



این Importها ممنوع هستند:



&#x20;   from ShadBotTrader.infrastructure import ...

&#x20;   from ShadBotTrader.application import ...

&#x20;   from ShadBotTrader.engines import ...

&#x20;   from ShadBotTrader.services import ...

&#x20;   from ShadBotTrader.gui import ...

&#x20;   from tensorflow import ...

&#x20;   from keras import ...

&#x20;   from sqlalchemy import ...

&#x20;   from mplfinance import ...

&#x20;   from broker\_sdk import ...



در Domain.



Domain باید از Implementation مستقل بماند.





\# 8. DOMAIN CONTRACTS



اگر Domain برای انجام یک عملیات خارجی به abstraction نیاز داشته باشد، Contract باید در لایه مناسب داخلی تعریف شود.



مثلاً:



&#x20;   MarketDataProvider

&#x20;   DatasetRepository

&#x20;   ModelRepository

&#x20;   EventPublisher

&#x20;   OrderExecutionPort

&#x20;   Clock



این Contractها نباید Implementation داشته باشند.



مثلاً:



&#x20;   interface / protocol / abstract contract



و Implementation در Infrastructure قرار می‌گیرد.





\# 9. CORE LAYER



Core شامل Primitiveها و قابلیت‌های بنیادی مشترک است.



Core نباید تبدیل به یک محل برای قرار دادن هر نوع Utility شود.



Core می‌تواند شامل مفاهیمی مانند:



&#x20;   Result

&#x20;   Error Model

&#x20;   Identifier

&#x20;   Value primitives

&#x20;   Common abstractions

&#x20;   Base contracts

&#x20;   Shared technical primitives



باشد.



اما Core نباید Business Logic مربوط به:



&#x20;   Trading

&#x20;   AI

&#x20;   Portfolio

&#x20;   Dataset

&#x20;   GUI



را در خود جمع کند.





\# 10. CORE DEPENDENCY RULE



Core باید از Domain و Infrastructure مستقل باشد.



Core نباید به:



&#x20;   Database

&#x20;   Broker

&#x20;   ML Framework

&#x20;   GUI

&#x20;   Filesystem

&#x20;   External API



وابسته باشد.



اگر Domain و Core هر دو به یک abstraction بنیادی نیاز دارند، آن abstraction باید در مناسب‌ترین لایه داخلی قرار گیرد.





\# 11. APPLICATION LAYER



Application مسئول اجرای Use Caseهای سیستم است.



Application باید Business Flow را Orchestrate کند، اما نباید جزئیات Infrastructure را پیاده‌سازی کند.



نمونه Use Caseها:



&#x20;   UpdateHistoricalDataset

&#x20;   GenerateFeatures

&#x20;   TrainModel

&#x20;   EvaluateModel

&#x20;   GeneratePrediction

&#x20;   ExecuteTradingDecision

&#x20;   RunBacktest

&#x20;   RunReplay

&#x20;   PromoteModel



Application می‌تواند:



&#x20;   Domain

&#x20;   Core

&#x20;   Contracts



را مصرف کند.



Application نباید مستقیماً به Implementationهای Infrastructure وابسته شود.





\# 12. APPLICATION DEPENDENCY RULE



Application مجاز است به:



&#x20;   Domain

&#x20;   Core

&#x20;   Application Contracts

&#x20;   Domain Contracts

&#x20;   Event Contracts



وابسته باشد.



Application نباید Business Logic را داخل:



&#x20;   GUI

&#x20;   Broker Adapter

&#x20;   Database Adapter

&#x20;   ML Framework Adapter



قرار دهد.





\# 13. ENGINE LAYER



Engineها مسئول اجرای قابلیت‌های بزرگ و تخصصی سیستم هستند.



Engineهای فعلی معماری:



&#x20;   AIEngine

&#x20;   ContextEngine

&#x20;   DataEngine

&#x20;   DecisionEngine

&#x20;   ExecutionEngine

&#x20;   FeatureEngineeringEngine

&#x20;   GuiEngine

&#x20;   IntelligenceEngine

&#x20;   MarketEngine

&#x20;   NewsEngine

&#x20;   OptimizationEngine

&#x20;   PortfolioEngine

&#x20;   SimulationEngine

&#x20;   StorageEngine



Engineها Application Flow و Domain Capability را به هم متصل می‌کنند.



Engine نباید به شکل یک God Object طراحی شود.





\# 14. ENGINE DEPENDENCY RULE



Engineها می‌توانند به:



&#x20;   Domain

&#x20;   Core

&#x20;   Application

&#x20;   Services

&#x20;   Contracts



وابسته باشند.



Engineها نباید Domain را به Infrastructure وابسته کنند.



Engine می‌تواند Infrastructure Adapter دریافت کند، اما باید آن را از طریق Contract مصرف کند.





\# 15. SERVICE LAYER



Serviceها برای عملیات تخصصی و قابل استفاده مجدد هستند.



Service نباید تبدیل به محل قرار دادن تمام Business Logic سیستم شود.



هر Service باید Responsibility مشخص داشته باشد.



مثلاً:



&#x20;   DatasetUpdateService

&#x20;   FeatureCalculationService

&#x20;   ModelTrainingService

&#x20;   PredictionService

&#x20;   RiskEvaluationService

&#x20;   PortfolioService



Service باید به Contract وابسته باشد، نه Implementation.





\# 16. SERVICE DEPENDENCY RULE



Service می‌تواند به:



&#x20;   Domain

&#x20;   Core

&#x20;   Contracts

&#x20;   Repository Interfaces

&#x20;   Provider Interfaces



وابسته باشد.



Service نباید مستقیماً به:



&#x20;   Broker SDK

&#x20;   Database Driver

&#x20;   GUI

&#x20;   External ML Runtime



وابسته شود مگر اینکه آن Dependency در Adapter/Infrastructure محصور شده باشد.





\# 17. INFRASTRUCTURE LAYER



Infrastructure مسئول اتصال ShadBotTrader به دنیای بیرون است.



نمونه:



&#x20;   SQL Server

&#x20;   Filesystem

&#x20;   Broker API

&#x20;   Market Data API

&#x20;   News API

&#x20;   TensorFlow

&#x20;   Keras

&#x20;   PyTorch

&#x20;   NumPy

&#x20;   Pandas

&#x20;   mplfinance

&#x20;   Matplotlib

&#x20;   OS Services



Infrastructure محل Implementation Contractها است.





\# 18. INFRASTRUCTURE DEPENDENCY RULE



Infrastructure می‌تواند به:



&#x20;   Domain

&#x20;   Core

&#x20;   Application Contracts

&#x20;   Service Contracts

&#x20;   Plugin Contracts



وابسته باشد.



Infrastructure می‌تواند Libraryهای خارجی را Import کند.



مثلاً:



&#x20;   SQLAlchemy

&#x20;   pyodbc

&#x20;   requests

&#x20;   broker SDK

&#x20;   tensorflow

&#x20;   keras

&#x20;   pandas

&#x20;   numpy

&#x20;   mplfinance



اما این Dependencyها نباید به لایه‌های داخلی منتقل شوند.





\# 19. EXTERNAL SYSTEM RULE



External Systems همیشه در بیرونی‌ترین مرز قرار می‌گیرند.



نمونه:



&#x20;   Broker

&#x20;   Market Data Provider

&#x20;   SQL Server

&#x20;   File System

&#x20;   Operating System

&#x20;   ML Runtime

&#x20;   News Provider



ShadBotTrader باید از طریق Adapter به آنها متصل شود.





\# 20. BROKER DEPENDENCY RULE



هیچ بخش داخلی ShadBotTrader نباید مستقیماً به SDK یک Broker خاص وابسته شود.



ممنوع:



&#x20;   Domain → Broker SDK



مجاز:



&#x20;   Domain

&#x20;      ↓

&#x20;   Broker Contract

&#x20;      ↑

&#x20;   Broker Adapter

&#x20;      ↓

&#x20;   Broker SDK





\# 21. MARKET DATA DEPENDENCY RULE



Market Data نیز باید از طریق Contract وارد سیستم شود.



مثلاً:



&#x20;   MarketDataProvider



Implementationها می‌توانند:



&#x20;   BrokerMarketDataProvider

&#x20;   ExchangeMarketDataProvider

&#x20;   FileMarketDataProvider

&#x20;   ReplayMarketDataProvider



باشند.



Market Engine نباید بداند داده دقیقاً از چه SDKای آمده است.





\# 22. DATABASE DEPENDENCY RULE



Domain نباید مستقیماً Database را بشناسد.



ممنوع:



&#x20;   Domain Entity

&#x20;      ↓

&#x20;   SQL Server



مجاز:



&#x20;   Domain

&#x20;      ↓

&#x20;   Repository Contract

&#x20;      ↑

&#x20;   SQL Repository

&#x20;      ↓

&#x20;   SQL Server





\# 23. FILESYSTEM DEPENDENCY RULE



Domain نباید مستقیماً با Filesystem کار کند.



ممنوع:



&#x20;   Domain

&#x20;      ↓

&#x20;   open()

&#x20;      ↓

&#x20;   local file



مجاز:



&#x20;   Domain/Application

&#x20;      ↓

&#x20;   Storage Contract

&#x20;      ↑

&#x20;   Filesystem Adapter





\# 24. AI FRAMEWORK DEPENDENCY RULE



Domain و Application نباید مستقیماً به Framework مدل وابسته باشند.



ممنوع:



&#x20;   Prediction Domain

&#x20;      ↓

&#x20;   TensorFlow



یا:



&#x20;   Application

&#x20;      ↓

&#x20;   Keras Model



مجاز:



&#x20;   AI Contract

&#x20;      ↑

&#x20;   TensorFlow/Keras Adapter





\# 25. FEATURE ENGINEERING DEPENDENCY RULE



Feature Definition باید از Infrastructure مستقل باشد.



Feature Business Semantics نباید به:



&#x20;   Database

&#x20;   Broker

&#x20;   GUI



وابسته باشد.



اگر برای محاسبات از:



&#x20;   NumPy

&#x20;   Pandas



استفاده شود، این وابستگی باید در مرز مناسب قرار گیرد و به Domain نشت نکند.





\# 26. GUI DEPENDENCY RULE



GUI یک لایه بیرونی است.



GUI می‌تواند به:



&#x20;   Application

&#x20;   Domain DTOs

&#x20;   Query Services

&#x20;   Visualization Services



وابسته باشد.



اما GUI نباید:



&#x20;   Broker

&#x20;   Database

&#x20;   Model Runtime

&#x20;   Trading Decision Logic



را مستقیماً کنترل کند.





\# 27. GUI MUST NOT CONTAIN BUSINESS LOGIC



این ساختار ممنوع است:



&#x20;   GUI Button

&#x20;      ↓

&#x20;   Broker.place\_order()



همچنین:



&#x20;   GUI

&#x20;      ↓

&#x20;   Model.predict()

&#x20;      ↓

&#x20;   Broker



ممنوع است.



ساختار صحیح:



&#x20;   GUI

&#x20;     ↓

&#x20;   Application Use Case

&#x20;     ↓

&#x20;   Domain / Engine

&#x20;     ↓

&#x20;   Risk

&#x20;     ↓

&#x20;   Execution Port

&#x20;     ↓

&#x20;   Broker Adapter





\# 28. ENGINE IS NOT AN INFRASTRUCTURE SHORTCUT



Engine نباید بهانه‌ای برای دور زدن Architecture شود.



ممنوع:



&#x20;   Engine

&#x20;      ↓

&#x20;   SQLAlchemy Session

&#x20;      ↓

&#x20;   SQL Server



اگر Repository Contract وجود دارد، Engine باید Contract را مصرف کند.





\# 29. PLUGIN DEPENDENCY RULE



Pluginها باید از طریق Contractهای مشخص وارد سیستم شوند.



ساختار مفهومی:



&#x20;   Core Contract

&#x20;        ↑

&#x20;        |

&#x20;     Plugin

&#x20;        |

&#x20;        ↓

&#x20;   External Library



Plugin نباید Core را به Implementation خودش وابسته کند.





\# 30. PLUGIN ISOLATION



یک Plugin نباید به Plugin دیگری وابسته شود مگر اینکه Dependency آن رسماً تعریف و مدیریت شده باشد.



مثلاً:



&#x20;   Broker Plugin A

&#x20;   Broker Plugin B



نباید برای کار کردن به یکدیگر وابسته باشند.





\# 31. EVENT BUS DEPENDENCY RULE



Event Publisher نباید Subscriberهای خودش را بشناسد.



ممنوع:



&#x20;   DatasetService

&#x20;      ↓

&#x20;   PredictionService



فقط برای اعلام:



&#x20;   DatasetUpdated



بهتر است:



&#x20;   DatasetService

&#x20;      ↓

&#x20;   EventBus

&#x20;      ↓

&#x20;   DatasetUpdated

&#x20;      ↓

&#x20;   Subscribers



Event Bus Coupling را کاهش می‌دهد.





\# 32. EVENT CONTRACT RULE



Eventها باید Contract مشخص داشته باشند.



Event باید شامل اطلاعات لازم برای مصرف‌کننده باشد.



Event نباید شامل Reference به Implementation داخلی باشد.



مثلاً:



&#x20;   DatasetUpdatedEvent



می‌تواند شامل:



&#x20;   dataset\_id

&#x20;   dataset\_version

&#x20;   symbol

&#x20;   timeframe

&#x20;   timestamp



باشد.



اما نباید شامل:



&#x20;   SQLAlchemy Session

&#x20;   Broker SDK Object

&#x20;   TensorFlow Model Object



باشد.





\# 33. DEPENDENCY INJECTION



Dependencies مهم باید Inject شوند.



ممنوع:



&#x20;   class PredictionService:



&#x20;       def \_\_init\_\_(self):

&#x20;           self.model = TensorFlowModel()



مجاز:



&#x20;   class PredictionService:



&#x20;       def \_\_init\_\_(self, model):

&#x20;           self.model = model



به این ترتیب:



&#x20;   Production

&#x20;       ↓

&#x20;   Real Implementation



و:



&#x20;   Testing

&#x20;       ↓

&#x20;   Mock / Fake Implementation



بدون تغییر Business Logic انجام می‌شود.





\# 34. NO HIDDEN GLOBAL DEPENDENCIES



Global Singletonهای پنهان نباید منبع اصلی Dependency باشند.



ممنوع:



&#x20;   global broker

&#x20;   global database

&#x20;   global model

&#x20;   global configuration



مگر اینکه در Architecture مشخصاً به عنوان یک Runtime Resource مدیریت شوند.



Dependency باید تا حد امکان قابل مشاهده و قابل Trace باشد.





\# 35. NO CIRCULAR DEPENDENCIES



Circular Dependency ممنوع است.



ممنوع:



&#x20;   Domain

&#x20;     ↓

&#x20;   Application

&#x20;     ↓

&#x20;   Domain



یا:



&#x20;   Engine A

&#x20;     ↓

&#x20;   Engine B

&#x20;     ↓

&#x20;   Engine A



همچنین Circular Import در Python باید از ابتدا جلوگیری شود.





\# 36. PACKAGE DEPENDENCY RULE



Package hierarchy باید Dependency hierarchy را منعکس کند.



ساختار فیزیکی نباید باعث شود یک Package برای دسترسی ساده به کلاس دیگر، Dependency غیرمجاز ایجاد کند.



قرار گرفتن دو فایل کنار هم به معنی مجاز بودن Import آنها نیست.





\# 37. MODULE RESPONSIBILITY RULE



هر Module باید Responsibility مشخص داشته باشد.



اگر یک Module مجبور شد:



&#x20;   Database

&#x20;   Broker

&#x20;   AI

&#x20;   Trading

&#x20;   GUI



را همزمان مدیریت کند، معماری آن Module باید بازبینی شود.





\# 38. DATA FLOW DEPENDENCY



Data Flow باید با Dependency Flow اشتباه گرفته نشود.



ممکن است:



&#x20;   Market Data

&#x20;      ↓

&#x20;   Data Engine

&#x20;      ↓

&#x20;   Feature Engine

&#x20;      ↓

&#x20;   AI Engine

&#x20;      ↓

&#x20;   Decision Engine



باشد.



اما این به معنی این نیست که:



&#x20;   Decision Engine

&#x20;      ↓

&#x20;   imports Data Engine internals



است.



Data Flow می‌تواند Forward باشد، در حالی که Dependency Direction به سمت Abstractionهای داخلی حفظ می‌شود.





\# 39. APPLICATION ORCHESTRATION RULE



Application مسئول Orchestration است.



مثلاً:



&#x20;   UpdateDatasetUseCase



می‌تواند:



&#x20;   MarketDataPort

&#x20;   DatasetRepository

&#x20;   FeatureService

&#x20;   EventPublisher



را دریافت کند.



اما نباید Implementation آنها را خودش بسازد.





\# 40. DOMAIN SERVICE RULE



اگر یک Business Rule متعلق به یک Entity خاص نیست، Domain Service می‌تواند آن Rule را نگهداری کند.



اما Domain Service نباید به:



&#x20;   SQL

&#x20;   Broker SDK

&#x20;   GUI

&#x20;   HTTP

&#x20;   OS



وابسته شود.





\# 41. REPOSITORY RULE



Repository یک Abstraction برای Persistence است.



Domain/Application باید Repository Contract را مصرف کنند.



Infrastructure Repository Implementation را ارائه می‌دهد.



ساختار:



&#x20;   Application

&#x20;       ↓

&#x20;   DatasetRepository

&#x20;       ↑

&#x20;   SQLDatasetRepository





\# 42. CLOCK DEPENDENCY RULE



زمان فعلی نباید در Business Logic به شکل uncontrolled مصرف شود.



به‌جای:



&#x20;   datetime.now()



در Business Logic، بهتر است Clock abstraction استفاده شود.



مثلاً:



&#x20;   Clock

&#x20;      ↑

&#x20;   SystemClock



در Production.



این موضوع برای:



&#x20;   Live Trading

&#x20;   Backtesting

&#x20;   Replay

&#x20;   Testing



اهمیت دارد.





\# 43. RANDOMNESS DEPENDENCY RULE



Randomness مهم نیز باید قابل کنترل باشد.



برای Training و Simulation باید امکان ثبت و کنترل Seed وجود داشته باشد.



هدف:



&#x20;   Reproducibility



است.





\# 44. CONFIGURATION DEPENDENCY RULE



Application و Domain نباید مستقیماً فایل Configuration را Parse کنند.



ساختار صحیح:



&#x20;   Configuration System

&#x20;         ↓

&#x20;   Validated Configuration

&#x20;         ↓

&#x20;   Application / Services



Configuration Parsing متعلق به لایه بیرونی است.





\# 45. LOGGING DEPENDENCY RULE



Business Logic نباید به Logger Framework خاص وابسته شود.



Logging باید از طریق abstraction یا استاندارد مناسب انجام شود.



Domain نباید بداند:



&#x20;   File Handler

&#x20;   Console Handler

&#x20;   Rotating File

&#x20;   External Logging Service



چگونه کار می‌کنند.





\# 46. ERROR DEPENDENCY RULE



External Exceptions نباید به Domain نشت کنند.



مثلاً:



&#x20;   BrokerSDKException



نباید مستقیماً در Domain مدیریت شود.



Infrastructure باید آن را به Error Contract مناسب تبدیل کند.



مثلاً:



&#x20;   BrokerConnectionError

&#x20;   MarketDataUnavailable

&#x20;   OrderRejected



سپس Application/Domain می‌تواند با این Contract کار کند.





\# 47. DTO BOUNDARY RULE



External DTOها نباید بدون کنترل وارد Domain شوند.



مثلاً:



&#x20;   Broker API Response



نباید مستقیماً به:



&#x20;   Domain Candle



تبدیل‌نشده منتقل شود.



Adapter مسئول Mapping است:



&#x20;   External DTO

&#x20;       ↓

&#x20;   Adapter

&#x20;       ↓

&#x20;   Domain Model





\# 48. DATAFRAME BOUNDARY RULE



DataFrame نباید به عنوان زبان مشترک کل معماری استفاده شود.



ممکن است در:



&#x20;   Feature Engineering

&#x20;   Data Processing

&#x20;   Analytics

&#x20;   Infrastructure



استفاده شود.



اما Domain نباید به DataFrame وابسته باشد.



Domain Model باید Semantic باشد.





\# 49. ML TENSOR BOUNDARY RULE



Tensor، NumPy Array یا Framework-specific Tensor نباید Contract اصلی Domain باشد.



ساختار:



&#x20;   Domain Context

&#x20;        ↓

&#x20;   AI Adapter Boundary

&#x20;        ↓

&#x20;   Tensor / NumPy / Framework Object



نه:



&#x20;   Domain

&#x20;      ↓

&#x20;   TensorFlow Tensor





\# 50. GUI DATA BOUNDARY



GUI نباید مستقیماً Domain Entity را برای همه عملیات mutate کند.



ترجیح:



&#x20;   Application Query

&#x20;        ↓

&#x20;   View Model / DTO

&#x20;        ↓

&#x20;   GUI



برای Command:



&#x20;   GUI

&#x20;     ↓

&#x20;   Application Command

&#x20;     ↓

&#x20;   Use Case





\# 51. TRADING DEPENDENCY CHAIN



Trading باید Dependency Chain زیر را حفظ کند:



&#x20;   Market Data

&#x20;       ↓

&#x20;   Context

&#x20;       ↓

&#x20;   Prediction

&#x20;       ↓

&#x20;   Decision

&#x20;       ↓

&#x20;   Risk

&#x20;       ↓

&#x20;   Order Intent

&#x20;       ↓

&#x20;   Execution Port

&#x20;       ↓

&#x20;   Broker Adapter

&#x20;       ↓

&#x20;   Broker





\# 52. DATASET DEPENDENCY CHAIN



Dataset باید:



&#x20;   Data Provider

&#x20;       ↓

&#x20;   Acquisition

&#x20;       ↓

&#x20;   Validation

&#x20;       ↓

&#x20;   Normalization

&#x20;       ↓

&#x20;   Deduplication

&#x20;       ↓

&#x20;   Dataset Repository

&#x20;       ↓

&#x20;   Dataset Version



را دنبال کند.



Dataset Domain نباید Broker SDK را بشناسد.





\# 53. FEATURE DEPENDENCY CHAIN



Historical:



&#x20;   Dataset

&#x20;      ↓

&#x20;   Feature Definition

&#x20;      ↓

&#x20;   Feature Engine

&#x20;      ↓

&#x20;   Feature Dataset

&#x20;      ↓

&#x20;   Storage



Live:



&#x20;   Market Data Buffer

&#x20;      ↓

&#x20;   Feature Engine

&#x20;      ↓

&#x20;   Live Feature Buffer

&#x20;      ↓

&#x20;   Inference Window

&#x20;      ↓

&#x20;   AI





\# 54. TRAINING DEPENDENCY CHAIN



Training:



&#x20;   Dataset Version

&#x20;       +

&#x20;   Feature Version

&#x20;       +

&#x20;   Training Configuration

&#x20;       +

&#x20;   Model Configuration

&#x20;             ↓

&#x20;         Training

&#x20;             ↓

&#x20;       Candidate Model

&#x20;             ↓

&#x20;        Evaluation

&#x20;             ↓

&#x20;         Promotion





\# 55. PROJECT INTELLIGENCE DEPENDENCY



Project Intelligence نباید با Business Trading Logic قاطی شود.



Project Intelligence می‌تواند:



&#x20;   Project Tree

&#x20;   Source Files

&#x20;   Architecture

&#x20;   Tests

&#x20;   Git State

&#x20;   Documentation



را مشاهده کند.



اما نباید تبدیل به بخشی از:



&#x20;   Trading Decision

&#x20;   Prediction

&#x20;   Broker Execution



شود.





\# 56. PROJECT HANDOFF DEPENDENCY



Project Snapshot باید از اطلاعات authoritative ساخته شود.



منابع احتمالی:



&#x20;   Project Structure

&#x20;   Source Code

&#x20;   Architecture Documents

&#x20;   Git

&#x20;   Test Results

&#x20;   Configuration Metadata



و خروجی:



&#x20;   Project Handoff Snapshot



است.



این Snapshot نباید تنها منبع حقیقت برای وضعیت واقعی پروژه باشد.





\# 57. TEST DEPENDENCY RULE



Tests می‌توانند به Implementation دسترسی داشته باشند، اما Production Code نباید به Tests وابسته باشد.



مجاز:



&#x20;   Tests

&#x20;      ↓

&#x20;   Production Code



ممنوع:



&#x20;   Production Code

&#x20;      ↓

&#x20;   Tests





\# 58. TEST DOUBLE RULE



Mock، Fake و Stub فقط برای Testing هستند.



نباید به Production Architecture راه پیدا کنند.



مثلاً:



&#x20;   FakeBroker



می‌تواند در Tests وجود داشته باشد، اما Production نباید برای اجرای واقعی به FakeBroker متکی باشد.





\# 59. EXTERNAL LIBRARY ISOLATION



هر External Library مهم باید تا حد امکان در مرز مشخصی قرار گیرد.



نمونه:



&#x20;   TensorFlow

&#x20;   Keras

&#x20;   Pandas

&#x20;   NumPy

&#x20;   SQLAlchemy

&#x20;   pyodbc

&#x20;   mplfinance

&#x20;   Matplotlib

&#x20;   Broker SDK



نباید بدون دلیل در کل پروژه پخش شوند.



هدف:



&#x20;   Controlled Dependency Surface





\# 60. DEPENDENCY OWNERSHIP



هر Dependency خارجی باید Owner مشخص داشته باشد.



مثلاً:



&#x20;   TensorFlow

&#x20;       → AI Infrastructure



&#x20;   SQLAlchemy

&#x20;       → Storage Infrastructure



&#x20;   Broker SDK

&#x20;       → Broker Adapter



&#x20;   mplfinance

&#x20;       → GUI / Visualization Infrastructure



این کار Dependency Surface را کنترل می‌کند.





\# 61. NO FRAMEWORK-DRIVEN DOMAIN



Framework نباید معماری Domain را تعیین کند.



نباید:



&#x20;   Database Framework

&#x20;   GUI Framework

&#x20;   ML Framework

&#x20;   Web Framework



باعث شوند Domain Entityها برای Framework طراحی شوند.



Architecture باید Framework-independent باقی بماند.





\# 62. NO DATABASE-DRIVEN DOMAIN



Schema Database نباید Business Domain را به شکل مستقیم تعریف کند.



Database Mapping باید Adapter/Infrastructure concern باشد.



Domain:



&#x20;   Candle



Database:



&#x20;   candle\_table



Mapping:



&#x20;   ORM / Repository Adapter



این سه مفهوم باید قابل تفکیک باشند.





\# 63. NO BROKER-DRIVEN TRADING DOMAIN



Trading Domain نباید بر اساس API یک Broker خاص طراحی شود.



مثلاً Domain Order نباید صرفاً مطابق ساختار یک Broker خاص باشد.



باید یک Trading Model مستقل وجود داشته باشد.



Broker Adapter مسئول Translation است.





\# 64. NO MODEL-DRIVEN ARCHITECTURE



کل معماری نباید بر اساس یک Model خاص طراحی شود.



مثلاً:



&#x20;   LSTM

&#x20;   Transformer

&#x20;   CNN

&#x20;   WaveNet

&#x20;   XGBoost



همگی باید بتوانند از طریق AI Contract وارد سیستم شوند.



Model قابل تعویض است.



Architecture نباید Model-specific باشد.





\# 65. NO STRATEGY-DRIVEN CORE



یک Strategy خاص نباید Core Trading Architecture را تعریف کند.



Strategy باید یک Capability قابل تعویض باشد.



مثلاً:



&#x20;   Strategy A

&#x20;   Strategy B

&#x20;   Strategy C



همگی باید بتوانند Contract مشترک را مصرف کنند.





\# 66. DEPENDENCY GRAPH TARGET



Dependency Graph هدف:



&#x20;   ┌──────────────────────────────────────┐

&#x20;   │              DOMAIN                  │

&#x20;   │                                      │

&#x20;   │ Entities / Value Objects / Rules     │

&#x20;   └───────────────────▲──────────────────┘

&#x20;                       │

&#x20;                       │

&#x20;   ┌───────────────────┴──────────────────┐

&#x20;   │               CORE                   │

&#x20;   │ Shared Primitives / Contracts        │

&#x20;   └───────────────────▲──────────────────┘

&#x20;                       │

&#x20;                       │

&#x20;   ┌───────────────────┴──────────────────┐

&#x20;   │            APPLICATION               │

&#x20;   │ Use Cases / Commands / Queries       │

&#x20;   └───────────────────▲──────────────────┘

&#x20;                       │

&#x20;                       │

&#x20;   ┌───────────────────┴──────────────────┐

&#x20;   │              ENGINES                 │

&#x20;   │ Specialized Orchestration            │

&#x20;   └───────────────────▲──────────────────┘

&#x20;                       │

&#x20;                       │

&#x20;   ┌───────────────────┴──────────────────┐

&#x20;   │          INFRASTRUCTURE              │

&#x20;   │ DB / Broker / AI / FS / GUI / APIs  │

&#x20;   └───────────────────▲──────────────────┘

&#x20;                       │

&#x20;                       │

&#x20;   ┌───────────────────┴──────────────────┐

&#x20;   │          EXTERNAL SYSTEMS            │

&#x20;   │ Broker / SQL / OS / Libraries        │

&#x20;   └──────────────────────────────────────┘





\# 67. ALLOWED DEPENDENCY MATRIX



Domain:



&#x20;   Core              ALLOWED

&#x20;   Application       FORBIDDEN

&#x20;   Engines           FORBIDDEN

&#x20;   Services          FORBIDDEN

&#x20;   Infrastructure    FORBIDDEN

&#x20;   GUI               FORBIDDEN

&#x20;   Plugins           FORBIDDEN

&#x20;   External Systems  FORBIDDEN



Core:



&#x20;   Domain            ALLOWED

&#x20;   Application       FORBIDDEN

&#x20;   Engines           FORBIDDEN

&#x20;   Infrastructure    FORBIDDEN

&#x20;   GUI               FORBIDDEN

&#x20;   External Systems  FORBIDDEN



Application:



&#x20;   Domain            ALLOWED

&#x20;   Core              ALLOWED

&#x20;   Contracts         ALLOWED

&#x20;   Engines           NOT REQUIRED / AVOID

&#x20;   Infrastructure    DIRECT IMPLEMENTATION FORBIDDEN

&#x20;   GUI               FORBIDDEN



Engines:



&#x20;   Domain            ALLOWED

&#x20;   Core              ALLOWED

&#x20;   Application       ALLOWED

&#x20;   Contracts         ALLOWED

&#x20;   Infrastructure    ONLY THROUGH CONTRACTS / DI

&#x20;   GUI               DIRECT DEPENDENCY FORBIDDEN



Infrastructure:



&#x20;   Domain            ALLOWED

&#x20;   Core              ALLOWED

&#x20;   Application       CONTRACTS ONLY

&#x20;   External Libraries ALLOWED

&#x20;   External Systems  ALLOWED



GUI:



&#x20;   Application       ALLOWED

&#x20;   Query/DTO Layer   ALLOWED

&#x20;   Domain Types      READ-ONLY / CONTROLLED

&#x20;   Infrastructure    THROUGH PRESENTATION ADAPTERS

&#x20;   Broker            DIRECT FORBIDDEN





\# 68. FORBIDDEN DEPENDENCY PATTERNS



Pattern 01:



&#x20;   Domain → Infrastructure



FORBIDDEN





Pattern 02:



&#x20;   Domain → Broker



FORBIDDEN





Pattern 03:



&#x20;   Domain → Database



FORBIDDEN





Pattern 04:



&#x20;   Domain → ML Framework



FORBIDDEN





Pattern 05:



&#x20;   GUI → Broker



FORBIDDEN





Pattern 06:



&#x20;   GUI → Database



FORBIDDEN





Pattern 07:



&#x20;   Model → Broker



FORBIDDEN





Pattern 08:



&#x20;   Prediction → Order Execution



DIRECTLY FORBIDDEN





Pattern 09:



&#x20;   Strategy → Broker SDK



FORBIDDEN





Pattern 10:



&#x20;   Application → Concrete Infrastructure



FORBIDDEN





Pattern 11:



&#x20;   Infrastructure → GUI Business Logic



FORBIDDEN





Pattern 12:



&#x20;   Plugin → Internal Implementation Details of Another Plugin



FORBIDDEN





\# 69. DEPENDENCY INJECTION TARGET



Runtime composition باید در لایه بیرونی انجام شود.



Conceptually:



&#x20;   Application

&#x20;        ↑

&#x20;   Receives Contracts

&#x20;        ↑

&#x20;   Composition Root

&#x20;        ↑

&#x20;   Concrete Implementations



مثلاً:



&#x20;   DatasetRepository

&#x20;          ↑

&#x20;   SQLDatasetRepository



&#x20;   MarketDataProvider

&#x20;          ↑

&#x20;   BrokerMarketDataProvider



&#x20;   ModelRunner

&#x20;          ↑

&#x20;   TensorFlowModelRunner



Composition Root این Implementationها را به Use Caseها تزریق می‌کند.





\# 70. COMPOSITION ROOT



Composition Root محل اصلی Wiring سیستم است.



مسئولیت آن:



&#x20;   Create Infrastructure

&#x20;   Create Services

&#x20;   Create Engines

&#x20;   Inject Dependencies

&#x20;   Register Plugins

&#x20;   Register Event Handlers

&#x20;   Start Runtime



است.



Composition Root نباید Business Logic داشته باشد.





\# 71. RUNTIME DEPENDENCY RULE



Runtime می‌تواند همه Componentهای لازم را Assemble کند.



اما Runtime نباید Domain Rules را اجرا کند.



Runtime:



&#x20;   Assemble

&#x20;   Configure

&#x20;   Start

&#x20;   Stop



می‌کند.



Business Logic جای دیگری قرار دارد.





\# 72. DEPENDENCY VALIDATION



Architecture باید در آینده امکان بررسی Dependencyها را داشته باشد.



حداقل موارد قابل بررسی:



&#x20;   Circular Imports

&#x20;   Forbidden Imports

&#x20;   Layer Violations

&#x20;   External Library Leakage

&#x20;   Infrastructure Leakage

&#x20;   Dependency Direction



این Validation باید بخشی از Quality Architecture آینده باشد.





\# 73. IMPORT DISCIPLINE



Importها باید حداقل Surface لازم را داشته باشند.



ممنوع:



&#x20;   from ShadBotTrader.infrastructure import \*



ممنوع:



&#x20;   wildcard imports



مگر در موارد بسیار محدود و رسمی که Architecture اجازه دهد.



ترجیح:



&#x20;   Explicit Imports





\# 74. PUBLIC API BOUNDARY



هر Package مهم باید Public API مشخص داشته باشد.



Internal Implementation نباید به صورت تصادفی توسط سایر Packages مصرف شود.



مثلاً:



&#x20;   public contract

&#x20;   internal adapter



باید قابل تفکیک باشند.





\# 75. INTERNAL IMPLEMENTATION RULE



اگر یک Component با `\_internal` یا ساختار داخلی مشخص شده باشد، سایر Packageها نباید برای راحتی مستقیماً آن را مصرف کنند.



Cross-package access باید از Public Contract انجام شود.





\# 76. DEPENDENCY STABILITY PRINCIPLE



هرچه یک Component:



&#x20;   مرکزی‌تر

&#x20;   پایدارتر

&#x20;   بنیادی‌تر



باشد، باید Dependency کمتری داشته باشد.



بنابراین:



&#x20;   Domain

&#x20;   Core



باید کمترین Dependency را داشته باشند.



Infrastructure می‌تواند Dependency بیشتری داشته باشد.





\# 77. DEPENDENCY RULE FOR DATASET PIPELINE



Dataset Pipeline باید به این شکل طراحی شود:



&#x20;   Provider

&#x20;      ↓

&#x20;   Acquisition Adapter

&#x20;      ↓

&#x20;   Validation

&#x20;      ↓

&#x20;   Normalization

&#x20;      ↓

&#x20;   Dataset Service

&#x20;      ↓

&#x20;   Repository

&#x20;      ↓

&#x20;   Storage



هر مرحله باید Contract خودش را داشته باشد.



Provider نباید Dataset Storage را کنترل کند.





\# 78. DEPENDENCY RULE FOR LIVE PIPELINE



Live Pipeline:



&#x20;   Broker / Market Provider

&#x20;          ↓

&#x20;   Market Data Adapter

&#x20;          ↓

&#x20;   Live Buffer

&#x20;          ↓

&#x20;   Feature Engine

&#x20;          ↓

&#x20;   Context

&#x20;          ↓

&#x20;   Prediction

&#x20;          ↓

&#x20;   Decision

&#x20;          ↓

&#x20;   Risk

&#x20;          ↓

&#x20;   Execution Port

&#x20;          ↓

&#x20;   Broker Adapter





\# 79. DEPENDENCY RULE FOR TRAINING PIPELINE



Training:



&#x20;   Dataset Repository

&#x20;          ↓

&#x20;   Feature Repository

&#x20;          ↓

&#x20;   Training Service

&#x20;          ↓

&#x20;   Model Adapter

&#x20;          ↓

&#x20;   Evaluation

&#x20;          ↓

&#x20;   Model Registry

&#x20;          ↓

&#x20;   Promotion





\# 80. DEPENDENCY RULE FOR VISUALIZATION



Visualization:



&#x20;   Application Query

&#x20;         ↓

&#x20;   View Model

&#x20;         ↓

&#x20;   Visualization Service

&#x20;         ↓

&#x20;   Chart Adapter

&#x20;         ↓

&#x20;   mplfinance / Matplotlib / Future Framework



GUI باید آخرین مصرف‌کننده باشد.



نه منبع Business Logic.





\# 81. DEPENDENCY RULE FOR BACKTEST



Backtest باید بتواند:



&#x20;   Historical Data

&#x20;       ↓

&#x20;   Replay

&#x20;       ↓

&#x20;   Feature

&#x20;       ↓

&#x20;   Model

&#x20;       ↓

&#x20;   Decision

&#x20;       ↓

&#x20;   Risk

&#x20;       ↓

&#x20;   Simulated Execution



را بدون Broker واقعی اجرا کند.



بنابراین Backtest نباید به Live Broker وابسته باشد.





\# 82. DEPENDENCY RULE FOR REPLAY



Replay باید بتواند یک Market Timeline را به سیستم تزریق کند.



بنابراین:



&#x20;   ReplayMarketDataProvider



باید بتواند همان Contractی را پیاده‌سازی کند که Live Provider پیاده می‌کند.



این باعث می‌شود Live و Replay از یک Market Data Contract استفاده کنند.





\# 83. DEPENDENCY RULE FOR SELF-LEARNING



Self Learning نباید مستقیم Model Production را mutate کند.



ساختار:



&#x20;   Training

&#x20;      ↓

&#x20;   Candidate

&#x20;      ↓

&#x20;   Evaluation

&#x20;      ↓

&#x20;   Promotion Service

&#x20;      ↓

&#x20;   Model Registry



Promotion تنها مسیر رسمی Production Model است.





\# 84. DEPENDENCY RULE FOR MODEL REGISTRY



Model Registry باید منبع رسمی Lifecycle مدل‌ها باشد.



Training نباید مستقیماً Production Model را overwrite کند.



ساختار:



&#x20;   Training

&#x20;      ↓

&#x20;   Candidate Artifact

&#x20;      ↓

&#x20;   Registry

&#x20;      ↓

&#x20;   Evaluation

&#x20;      ↓

&#x20;   Promotion

&#x20;      ↓

&#x20;   Production Version





\# 85. DEPENDENCY RULE FOR PORTFOLIO



Portfolio باید از:



&#x20;   Prediction



مستقل باشد.



Portfolio می‌تواند Decision/Order Intent را دریافت کند، اما نباید Model-specific شود.





\# 86. DEPENDENCY RULE FOR RISK



Risk باید مستقل از Broker Implementation باشد.



Risk می‌تواند:



&#x20;   Portfolio State

&#x20;   Market Context

&#x20;   Order Intent

&#x20;   Configuration



را بررسی کند.



اما نباید:



&#x20;   Broker SDK



را مستقیماً Import کند.





\# 87. DEPENDENCY RULE FOR ORDER



Order Domain Object باید Broker-independent باشد.



Broker Adapter مسئول Mapping:



&#x20;   Domain Order

&#x20;       ↓

&#x20;   Broker-specific Order

&#x20;       ↓

&#x20;   Broker API





\# 88. DEPENDENCY RULE FOR EXECUTION RESULT



External Broker Response باید در Adapter تبدیل شود.



مثلاً:



&#x20;   BrokerResponse

&#x20;       ↓

&#x20;   Adapter

&#x20;       ↓

&#x20;   ExecutionResult



Application و Domain فقط ExecutionResult را می‌بینند.





\# 89. DEPENDENCY RULE FOR NEWS



News Providerها Plugin/Infrastructure هستند.



News Domain نباید به Provider خاصی وابسته شود.



مثلاً:



&#x20;   NewsProvider Contract

&#x20;        ↑

&#x20;   Provider A

&#x20;   Provider B

&#x20;   Provider C





\# 90. DEPENDENCY RULE FOR OPTIMIZATION



Optimization باید Model/Strategy را از طریق Contract مصرف کند.



Optimizer نباید به Implementation خاص Model وابسته شود.



هدف:



&#x20;   Strategy

&#x20;   Model

&#x20;   Parameters



قابل Optimization باشند بدون Coupling مستقیم.





\# 91. DEPENDENCY RULE FOR INTELLIGENCE ENGINE



Intelligence Engine مسئول تحلیل سطح بالای سیستم است.



اما نباید اجازه داشته باشد Dependency Direction را بشکند.



مثلاً:



&#x20;   IntelligenceEngine

&#x20;       ↓

&#x20;   Project State Contract



مجاز است.



اما:



&#x20;   IntelligenceEngine

&#x20;       ↓

&#x20;   Direct arbitrary mutation of Domain/Infrastructure



مجاز نیست.





\# 92. ARCHITECTURE RULE FOR SHARED CODE



Shared نباید به Garbage Package تبدیل شود.



هر چیزی که در Shared قرار می‌گیرد باید:



&#x20;   Truly Shared

&#x20;   Stable

&#x20;   Generic

&#x20;   Low Dependency



باشد.



Business Logic خاص یک Subsystem نباید در Shared قرار گیرد.





\# 93. NO "UTILS" ESCAPE HATCH



ساختن:



&#x20;   utils.py



برای دور زدن Architecture ممنوع است.



اگر Function متعلق به:



&#x20;   Dataset

&#x20;   Feature

&#x20;   Trading

&#x20;   AI

&#x20;   Portfolio



است، باید در همان Boundary قرار گیرد.



Utility عمومی فقط زمانی مجاز است که واقعاً Generic باشد.





\# 94. DEPENDENCY OWNERSHIP SUMMARY



Domain owns:



&#x20;   Business Semantics



Core owns:



&#x20;   Fundamental Primitives / Contracts



Application owns:



&#x20;   Use Cases / Orchestration



Engines own:



&#x20;   Specialized System Coordination



Services own:



&#x20;   Focused Operations



Infrastructure owns:



&#x20;   External Technology Integration



Plugins own:



&#x20;   Replaceable Implementations



GUI owns:



&#x20;   Presentation / Visualization



External Systems own:



&#x20;   Their own APIs and behavior





\# 95. FINAL DEPENDENCY PRINCIPLE



هر Dependency باید بتواند به این سؤال پاسخ دهد:



&#x20;   "چرا این Component باید این Dependency را بشناسد؟"



اگر پاسخ فقط:



&#x20;   "چون راحت‌تر بود"



باشد، Dependency معماری معتبر نیست.



Dependency باید:



&#x20;   Explicit

&#x20;   Necessary

&#x20;   Directional

&#x20;   Testable

&#x20;   Replaceable

&#x20;   Traceable



باشد.





\# 96. PHASE 02 ACCEPTANCE CRITERIA



Phase 02 زمانی Complete محسوب می‌شود که:



\[x] Dependency Direction تعریف شده است.

\[x] Domain Boundary تعریف شده است.

\[x] Core Boundary تعریف شده است.

\[x] Application Boundary تعریف شده است.

\[x] Engine Boundary تعریف شده است.

\[x] Service Boundary تعریف شده است.

\[x] Infrastructure Boundary تعریف شده است.

\[x] GUI Boundary تعریف شده است.

\[x] Plugin Boundary تعریف شده است.

\[x] External System Boundary تعریف شده است.

\[x] Domain → Infrastructure ممنوع شده است.

\[x] Domain → Broker ممنوع شده است.

\[x] Domain → Database ممنوع شده است.

\[x] Domain → ML Framework ممنوع شده است.

\[x] GUI → Broker ممنوع شده است.

\[x] GUI → Database ممنوع شده است.

\[x] Model → Broker ممنوع شده است.

\[x] Application → Concrete Infrastructure ممنوع شده است.

\[x] Circular Dependency ممنوع شده است.

\[x] Dependency Injection تعریف شده است.

\[x] Composition Root تعریف شده است.

\[x] Repository Boundary تعریف شده است.

\[x] Broker Adapter Boundary تعریف شده است.

\[x] AI Adapter Boundary تعریف شده است.

\[x] Filesystem Boundary تعریف شده است.

\[x] Event Dependency تعریف شده است.

\[x] Plugin Isolation تعریف شده است.

\[x] DataFrame Boundary تعریف شده است.

\[x] Tensor Boundary تعریف شده است.

\[x] GUI Data Boundary تعریف شده است.

\[x] Testing Dependency Direction تعریف شده است.

\[x] External Library Isolation تعریف شده است.

\[x] Project Intelligence Boundary تعریف شده است.

\[x] Self-Learning Dependency Boundary تعریف شده است.

\[x] Model Registry Boundary تعریف شده است.

\[x] Architecture Dependency Validation requirement تعریف شده است.

\[x] Shared/Utils misuse prevention تعریف شده است.





\# 97. PHASE 02 FINAL STATUS



PHASE:

02 — DEPENDENCY RULES



STATUS:

FINAL BASELINE



ARCHITECTURE RULE:

FROZEN AFTER APPROVAL



NEXT PHASE:

03 — DOMAIN MODEL

