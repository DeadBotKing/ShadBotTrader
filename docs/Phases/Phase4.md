\# SHADBOT ENTERPRISE AI TRADING PLATFORM

\# PHASE 04 — PROJECT TREE / PHYSICAL ARCHITECTURE



Document ID:

SHADBOT-ARCH-P04



Phase:

04 / 26



Status:

FINAL BASELINE



Architecture Style:

Enterprise

Clean Architecture

Domain-Driven Design

Dependency Inversion

Modular Monolith

Desktop Runtime

Framework Independent Core





\# 1. PURPOSE



این Phase ساختار فیزیکی نهایی Repository و محل قرارگیری هر Layer، Module، Package و Responsibility را مشخص می‌کند.



هدف این Phase:



&#x20;   1. تعیین Project Tree رسمی

&#x20;   2. تعیین مرز Layerها

&#x20;   3. تعیین محل هر Bounded Context

&#x20;   4. تعیین محل Engineها

&#x20;   5. تعیین محل Application Services

&#x20;   6. تعیین محل Infrastructure Adapters

&#x20;   7. تعیین محل Interfaces

&#x20;   8. تعیین محل Configuration

&#x20;   9. تعیین محل Tests

&#x20;   10. جلوگیری از ساختارهای موازی و تکراری

&#x20;   11. جلوگیری از Architecture Drift

&#x20;   12. ایجاد ساختار ثابت برای تمام Phaseهای بعدی





\# 2. ARCHITECTURAL DECISION



ShadBot یک:



&#x20;   Enterprise Modular Monolith



است.



در V1 سیستم به چند Microservice مستقل تقسیم نمی‌شود.



تمام سیستم در یک Python Application اجرا می‌شود، اما Module Boundaryها به‌صورت سخت‌گیرانه رعایت می‌شوند.



هدف:



&#x20;   Modular Architecture

&#x20;   Strong Boundaries

&#x20;   Independent Components

&#x20;   Future Extractability



است.





\# 3. RUNTIME MODEL



ShadBot یک Desktop Application است.



Web Dashboard:



&#x20;   NOT REQUIRED



Mobile Application:



&#x20;   NOT REQUIRED



Cloud-first Architecture:



&#x20;   NOT REQUIRED



Primary Runtime:



&#x20;   Local Windows Computer



Application باید بتواند بدون Browser و Mobile Client اجرا شود.





\# 4. TOP-LEVEL REPOSITORY



ساختار Root:



&#x20;   ShadBot/

&#x20;   │

&#x20;   ├── architecture/

&#x20;   ├── configs/

&#x20;   ├── datasets/

&#x20;   ├── docs/

&#x20;   ├── legacy/

&#x20;   ├── scripts/

&#x20;   ├── src/

&#x20;   ├── tests/

&#x20;   │

&#x20;   ├── .gitignore

&#x20;   ├── README.md

&#x20;   ├── pyproject.toml

&#x20;   └── ...





\# 5. ROOT DIRECTORY RESPONSIBILITIES



\## architecture/



اسناد Architecture رسمی پروژه.



شامل:



&#x20;   Architecture decisions

&#x20;   Phase specifications

&#x20;   Dependency rules

&#x20;   Architecture contracts



کد Runtime نباید داخل این Directory قرار بگیرد.





\## configs/



Configurationهای خارج از Source Code.



نمونه:



&#x20;   application configuration

&#x20;   trading configuration

&#x20;   data configuration

&#x20;   model configuration

&#x20;   logging configuration





\## datasets/



Storage مربوط به Datasetهای پروژه.



ساختار فعلی:



&#x20;   datasets/

&#x20;   ├── Raw/

&#x20;   ├── Processed/

&#x20;   └── Features/



Datasetهای حجیم نباید داخل Git Repository commit شوند.



.gitignore باید Datasetهای Runtime/Large Data را کنترل کند.





\## docs/



Documentation پروژه.



شامل:



&#x20;   Architecture.md

&#x20;   User Documentation

&#x20;   Operational Documentation

&#x20;   Development Documentation





\## legacy/



کدها و Artefactهای قدیمی.



Legacy نباید Dependency جدید به سیستم اصلی ایجاد کند.



کد جدید نباید برای اجرای عادی به Legacy وابسته باشد.





\## scripts/



Automation Scripts.



نمونه:



&#x20;   setup

&#x20;   dataset update

&#x20;   training

&#x20;   maintenance

&#x20;   validation

&#x20;   development utilities



Scripts نباید Business Logic اصلی را در خود نگه دارند.





\## src/



تمام Production Source Code.



تنها Source Code اصلی سیستم باید اینجا قرار بگیرد.





\## tests/



تمام Testها.



Tests باید خارج از Production Package نگهداری شوند مگر موارد بسیار خاص.





\# 6. PYTHON PACKAGE ROOT



Package اصلی:



&#x20;   src/ShadBot/





ساختار فعلی:



&#x20;   src/

&#x20;   └── ShadBot/

&#x20;       ├── \_\_init\_\_.py

&#x20;       ├── Application/

&#x20;       ├── Core/

&#x20;       ├── Domain/

&#x20;       ├── Engines/

&#x20;       ├── Exceptions/

&#x20;       ├── Infrastructure/

&#x20;       ├── Interfaces/

&#x20;       ├── Services/

&#x20;       └── Shared/





این ساختار Base رسمی پروژه است.





\# 7. CASE CONVENTION



نام‌گذاری فعلی Packageها:



&#x20;   Application

&#x20;   Core

&#x20;   Domain

&#x20;   Engines

&#x20;   Exceptions

&#x20;   Infrastructure

&#x20;   Interfaces

&#x20;   Services

&#x20;   Shared



در این Phase همین ساختار تثبیت می‌شود.



نباید در ادامه بخشی از پروژه با:



&#x20;   application

&#x20;   domain

&#x20;   infrastructure



و بخش دیگری با:



&#x20;   Application

&#x20;   Domain

&#x20;   Infrastructure



ساخته شود.



یک Convention باید در کل پروژه حفظ شود.





\# 8. DOMAIN



مسیر:



&#x20;   src/ShadBot/Domain/





مسئول:



&#x20;   Business Concepts

&#x20;   Entities

&#x20;   Value Objects

&#x20;   Aggregates

&#x20;   Domain Services

&#x20;   Domain Policies

&#x20;   Domain Events

&#x20;   Repository Contracts





\# 9. DOMAIN STRUCTURE



ساختار نهایی Domain:



&#x20;   Domain/

&#x20;   │

&#x20;   ├── \_\_init\_\_.py

&#x20;   │

&#x20;   ├── Common/

&#x20;   │

&#x20;   ├── Market/

&#x20;   │

&#x20;   ├── Dataset/

&#x20;   │

&#x20;   ├── Feature/

&#x20;   │

&#x20;   ├── News/

&#x20;   │

&#x20;   ├── Prediction/

&#x20;   │

&#x20;   ├── Trading/

&#x20;   │

&#x20;   ├── Portfolio/

&#x20;   │

&#x20;   ├── Simulation/

&#x20;   │

&#x20;   ├── AI/

&#x20;   │

&#x20;   ├── Optimization/

&#x20;   │

&#x20;   ├── SelfLearning/

&#x20;   │

&#x20;   └── ProjectIntelligence/





\# 10. DOMAIN COMMON



مسیر:



&#x20;   src/ShadBot/Domain/Common/





شامل مفاهیم مشترک واقعی:



&#x20;   identifiers

&#x20;   timestamps

&#x20;   timeframes

&#x20;   symbols

&#x20;   prices

&#x20;   quantities

&#x20;   percentages

&#x20;   money

&#x20;   ranges

&#x20;   domain events

&#x20;   common domain errors





\# 11. DOMAIN MARKET



مسیر:



&#x20;   src/ShadBot/Domain/Market/





مسئول:



&#x20;   Market

&#x20;   MarketSession

&#x20;   Candle

&#x20;   MarketContext

&#x20;   MarketData concepts

&#x20;   DataQuality

&#x20;   DataFreshness

&#x20;   DataGap





\# 12. DOMAIN DATASET



مسیر:



&#x20;   src/ShadBot/Domain/Dataset/





مسئول:



&#x20;   Dataset

&#x20;   DatasetVersion

&#x20;   DatasetMetadata

&#x20;   DatasetUpdate

&#x20;   DatasetSnapshot

&#x20;   HistoricalData concepts





Dataset Domain مسئول Storage implementation نیست.





\# 13. DOMAIN FEATURE



مسیر:



&#x20;   src/ShadBot/Domain/Feature/





مسئول:



&#x20;   Feature

&#x20;   FeatureDefinition

&#x20;   FeatureSet

&#x20;   FeatureSetVersion

&#x20;   FeatureDataset

&#x20;   FeatureCalculation concepts

&#x20;   CalculationWindow

&#x20;   InferenceWindow





\# 14. DOMAIN NEWS



مسیر:



&#x20;   src/ShadBot/Domain/News/





مسئول:



&#x20;   NewsArticle

&#x20;   NewsSource

&#x20;   Sentiment

&#x20;   NewsContext





\# 15. DOMAIN PREDICTION



مسیر:



&#x20;   src/ShadBot/Domain/Prediction/





مسئول:



&#x20;   Prediction

&#x20;   PredictionContext

&#x20;   PredictionHorizon

&#x20;   PredictionType

&#x20;   Confidence





\# 16. DOMAIN TRADING



مسیر:



&#x20;   src/ShadBot/Domain/Trading/





مسئول:



&#x20;   Strategy

&#x20;   Signal

&#x20;   TradingDecision

&#x20;   Risk

&#x20;   RiskPolicy

&#x20;   OrderIntent

&#x20;   Order

&#x20;   Execution





\# 17. DOMAIN PORTFOLIO



مسیر:



&#x20;   src/ShadBot/Domain/Portfolio/





مسئول:



&#x20;   Portfolio

&#x20;   Position

&#x20;   Cash

&#x20;   Equity

&#x20;   Exposure

&#x20;   PnL





\# 18. DOMAIN SIMULATION



مسیر:



&#x20;   src/ShadBot/Domain/Simulation/





مسئول:



&#x20;   Simulation

&#x20;   SimulationRun

&#x20;   Replay

&#x20;   Backtest

&#x20;   SimulatedExecution

&#x20;   SimulationResult





\# 19. DOMAIN AI



مسیر:



&#x20;   src/ShadBot/Domain/AI/





مسئول:



&#x20;   Model

&#x20;   ModelVersion

&#x20;   TrainingRun

&#x20;   ModelEvaluation

&#x20;   ModelPromotion

&#x20;   TrainingConfiguration





این Package نباید شامل TensorFlow/Keras implementation باشد.





\# 20. DOMAIN OPTIMIZATION



مسیر:



&#x20;   src/ShadBot/Domain/Optimization/





مسئول:



&#x20;   Optimization

&#x20;   Objective

&#x20;   SearchSpace

&#x20;   OptimizationResult

&#x20;   OptimizationConfiguration





\# 21. DOMAIN SELF-LEARNING



مسیر:



&#x20;   src/ShadBot/Domain/SelfLearning/





مسئول:



&#x20;   LearningCycle

&#x20;   LearningRun

&#x20;   DatasetUpdatePolicy

&#x20;   RetrainingPolicy

&#x20;   ModelPromotionPolicy





\# 22. DOMAIN PROJECT INTELLIGENCE



مسیر:



&#x20;   src/ShadBot/Domain/ProjectIntelligence/





مسئول:



&#x20;   ProjectSnapshot

&#x20;   ProjectKnowledge

&#x20;   ProjectInsight

&#x20;   Recommendation

&#x20;   Decision

&#x20;   AgentContext



Project Intelligence یک Domain Capability مستقل است.





\# 23. APPLICATION



مسیر:



&#x20;   src/ShadBot/Application/





Application Layer مسئول Orchestration است.



Application:



&#x20;   Use Cases

&#x20;   Commands

&#x20;   Queries

&#x20;   DTOs

&#x20;   Application Services

&#x20;   Workflow Coordination





\# 24. APPLICATION STRUCTURE



ساختار:



&#x20;   Application/

&#x20;   │

&#x20;   ├── \_\_init\_\_.py

&#x20;   │

&#x20;   ├── Market/

&#x20;   ├── Dataset/

&#x20;   ├── Feature/

&#x20;   ├── News/

&#x20;   ├── Prediction/

&#x20;   ├── Trading/

&#x20;   ├── Portfolio/

&#x20;   ├── Simulation/

&#x20;   ├── AI/

&#x20;   ├── Optimization/

&#x20;   ├── SelfLearning/

&#x20;   └── ProjectIntelligence/





هر Application Module Use Caseهای مربوط به همان Domain Context را مدیریت می‌کند.





\# 25. APPLICATION RULE



Application Layer نباید Business Rule عمیق را جایگزین Domain کند.



Application مسئول:



&#x20;   چه چیزی اجرا شود



است.



Domain مسئول:



&#x20;   چه چیزی از نظر Business مجاز است



است.





\# 26. CORE



مسیر:



&#x20;   src/ShadBot/Core/





Core شامل Primitiveهای فنی و قراردادهای بنیادی سیستم است که Domain Business-specific نیستند.



نمونه:



&#x20;   Result

&#x20;   Error Handling primitives

&#x20;   Dependency abstractions

&#x20;   Execution primitives

&#x20;   Clock abstraction

&#x20;   Identity primitives



Core نباید محل Business Logic باشد.





\# 27. ENGINES



مسیر:



&#x20;   src/ShadBot/Engines/





Engineها Runtime Processing Components هستند.



ساختار رسمی:



&#x20;   Engines/

&#x20;   │

&#x20;   ├── AIEngine/

&#x20;   ├── ContextEngine/

&#x20;   ├── DataEngine/

&#x20;   ├── DecisionEngine/

&#x20;   ├── ExecutionEngine/

&#x20;   ├── FeatureEngineeringEngine/

&#x20;   ├── GuiEngine/

&#x20;   ├── IntelligenceEngine/

&#x20;   ├── MarketEngine/

&#x20;   ├── NewsEngine/

&#x20;   ├── OptimizationEngine/

&#x20;   ├── PortfolioEngine/

&#x20;   ├── SimulationEngine/

&#x20;   └── StorageEngine/





\# 28. AI ENGINE



مسیر:



&#x20;   src/ShadBot/Engines/AIEngine/





مسئول:



&#x20;   Model Loading

&#x20;   Inference

&#x20;   Training Runtime

&#x20;   Model Execution

&#x20;   ML Runtime Coordination





AIEngine می‌تواند به:



&#x20;   TensorFlow

&#x20;   Keras

&#x20;   NumPy



وابسته باشد.



Domain AI نباید به آنها وابسته باشد.





\# 29. CONTEXT ENGINE



مسیر:



&#x20;   src/ShadBot/Engines/ContextEngine/





مسئول:



&#x20;   Market Context Construction

&#x20;   Prediction Context Construction

&#x20;   Trading Context Construction

&#x20;   Runtime Context Aggregation





\# 30. DATA ENGINE



مسیر:



&#x20;   src/ShadBot/Engines/DataEngine/





مسئول:



&#x20;   Historical Data Acquisition

&#x20;   Live Data Acquisition

&#x20;   Data Normalization

&#x20;   Data Validation

&#x20;   Data Update

&#x20;   Data Window Management





\# 31. FEATURE ENGINEERING ENGINE



مسیر:



&#x20;   src/ShadBot/Engines/FeatureEngineeringEngine/





مسئول:



&#x20;   Feature Calculation

&#x20;   Historical Feature Engineering

&#x20;   Live Feature Engineering

&#x20;   Feature Pipeline Execution

&#x20;   Calculation Window Management





دو مسیر اصلی:



&#x20;   Historical:



&#x20;       Raw Dataset

&#x20;           ↓

&#x20;       Feature Engineering

&#x20;           ↓

&#x20;       Feature Dataset





&#x20;   Live:



&#x20;       Live Data

&#x20;           ↓

&#x20;       Calculation Window

&#x20;           ↓

&#x20;       Feature Engineering

&#x20;           ↓

&#x20;       Inference Window





\# 32. MARKET ENGINE



مسیر:



&#x20;   src/ShadBot/Engines/MarketEngine/





مسئول:



&#x20;   Market State

&#x20;   Market Sessions

&#x20;   Market Context

&#x20;   Market Data Coordination





\# 33. NEWS ENGINE



مسیر:



&#x20;   src/ShadBot/Engines/NewsEngine/





مسئول:



&#x20;   News Acquisition

&#x20;   News Processing

&#x20;   Sentiment Processing

&#x20;   News Context





\# 34. DECISION ENGINE



مسیر:



&#x20;   src/ShadBot/Engines/DecisionEngine/





مسئول:



&#x20;   Prediction Interpretation

&#x20;   Strategy Execution

&#x20;   Signal Generation

&#x20;   Decision Construction

&#x20;   Risk Evaluation





DecisionEngine نباید مستقیماً Broker API را صدا بزند.





\# 35. EXECUTION ENGINE



مسیر:



&#x20;   src/ShadBot/Engines/ExecutionEngine/





مسئول:



&#x20;   Order Submission

&#x20;   Order Monitoring

&#x20;   Execution Tracking

&#x20;   Broker Execution Coordination





\# 36. PORTFOLIO ENGINE



مسیر:



&#x20;   src/ShadBot/Engines/PortfolioEngine/





مسئول:



&#x20;   Portfolio State

&#x20;   Position Management

&#x20;   PnL

&#x20;   Exposure

&#x20;   Equity

&#x20;   Portfolio Calculations





\# 37. SIMULATION ENGINE



مسیر:



&#x20;   src/ShadBot/Engines/SimulationEngine/





مسئول:



&#x20;   Backtest

&#x20;   Replay

&#x20;   Paper Trading

&#x20;   Historical Execution Simulation





\# 38. OPTIMIZATION ENGINE



مسیر:



&#x20;   src/ShadBot/Engines/OptimizationEngine/





مسئول:



&#x20;   Parameter Search

&#x20;   Strategy Optimization

&#x20;   Model Optimization

&#x20;   Objective Evaluation





\# 39. INTELLIGENCE ENGINE



مسیر:



&#x20;   src/ShadBot/Engines/IntelligenceEngine/





مسئول:



&#x20;   Project Intelligence Runtime

&#x20;   Workspace Analysis

&#x20;   Intelligence Pipeline

&#x20;   Agent Context Generation





\# 40. GUI ENGINE



مسیر:



&#x20;   src/ShadBot/Engines/GuiEngine/





این Engine فقط برای Desktop GUI است.



Web و Mobile وجود ندارند.



GUI باید فقط Visualization/Control انجام دهد.



Business Logic نباید داخل GUI Engine قرار گیرد.





\# 41. STORAGE ENGINE



مسیر:



&#x20;   src/ShadBot/Engines/StorageEngine/





مسئول:



&#x20;   Storage Coordination

&#x20;   Dataset Storage

&#x20;   Model Storage

&#x20;   Feature Storage

&#x20;   Metadata Storage





StorageEngine نباید Domain Rules را تعریف کند.





\# 42. SERVICES



مسیر:



&#x20;   src/ShadBot/Services/





Services برای سرویس‌های Application/Runtime سطح بالاتر استفاده می‌شوند.



نباید تبدیل به:



&#x20;   God Service

&#x20;   Generic Manager

&#x20;   Business Logic Dump



شوند.





\# 43. INTERFACES



مسیر:



&#x20;   src/ShadBot/Interfaces/





Interfaces محل Interfaceهای External/System Boundary است.



نمونه:



&#x20;   Broker Interface

&#x20;   Data Provider Interface

&#x20;   Model Provider Interface

&#x20;   Storage Interface

&#x20;   News Provider Interface

&#x20;   Clock Interface

&#x20;   Notification Interface





\# 44. INFRASTRUCTURE



مسیر:



&#x20;   src/ShadBot/Infrastructure/





Infrastructure محل Implementation واقعی Interfaceها است.



نمونه:



&#x20;   Broker adapters

&#x20;   Database adapters

&#x20;   File storage

&#x20;   Parquet storage

&#x20;   ML model storage

&#x20;   External APIs

&#x20;   Logging

&#x20;   Configuration providers





\# 45. INFRASTRUCTURE STRUCTURE



ساختار:



&#x20;   Infrastructure/

&#x20;   │

&#x20;   ├── \_\_init\_\_.py

&#x20;   ├── Broker/

&#x20;   ├── Data/

&#x20;   ├── Feature/

&#x20;   ├── Storage/

&#x20;   ├── Database/

&#x20;   ├── AI/

&#x20;   ├── News/

&#x20;   ├── Configuration/

&#x20;   ├── Logging/

&#x20;   └── System/





جزئیات Provider-specific بعداً در Phaseهای مربوطه مشخص می‌شوند.





\# 46. BROKER ADAPTER



Broker implementation باید در Infrastructure باشد.



مثلاً:



&#x20;   Infrastructure/

&#x20;   └── Broker/

&#x20;       └── <Provider>/





Broker SDK نباید وارد:



&#x20;   Domain

&#x20;   Application



شود.





\# 47. DATA PROVIDER ADAPTER



Historical و Live Data Providerها باید Adapter داشته باشند.



ساختار مفهومی:



&#x20;   Data Provider

&#x20;        ↓

&#x20;   Adapter

&#x20;        ↓

&#x20;   Normalization

&#x20;        ↓

&#x20;   Domain Market Data





\# 48. STORAGE



Storage implementation باید خارج از Domain باشد.



Datasetهای بزرگ می‌توانند در:



&#x20;   Parquet

&#x20;   Database

&#x20;   Columnar Storage

&#x20;   Object Storage



در آینده ذخیره شوند.



Domain نباید بداند کدام Storage استفاده می‌شود.





\# 49. DATASET STORAGE PRINCIPLE



Datasetهای حجیم نباید داخل:



&#x20;   src/

&#x20;   Domain/

&#x20;   Git Repository



قرار بگیرند.



مسیر Repository فعلی:



&#x20;   datasets/



برای Runtime Dataset Storage در نظر گرفته می‌شود.





\# 50. RAW DATA



مسیر:



&#x20;   datasets/Raw/





برای داده خام.



Raw Data نباید بعد از دریافت بدون Traceability overwrite شود.



Versioning/Metadata باید حفظ شود.





\# 51. PROCESSED DATA



مسیر:



&#x20;   datasets/Processed/





برای داده Normalize/Processed شده.



مثلاً:



&#x20;   cleaned

&#x20;   normalized

&#x20;   deduplicated

&#x20;   gap-checked





\# 52. FEATURE DATA



مسیر:



&#x20;   datasets/Features/





برای Feature-engineered Datasetهای بزرگ.



رابطه:



&#x20;   Raw

&#x20;     ↓

&#x20;   Processed

&#x20;     ↓

&#x20;   Features





\# 53. LIVE DATA



Live Data به صورت دائمی در datasets ذخیره نمی‌شود مگر اینکه Recording/Archival فعال شده باشد.



Runtime Live Buffer باید در Memory/Runtime Storage مدیریت شود.



مثلاً:



&#x20;   Calculation Window = 1000

&#x20;   Inference Window = 500





\# 54. CONFIGURATION



Configuration خارج از Domain قرار دارد.



مسیر:



&#x20;   configs/





و Configuration Runtime در Infrastructure/Application load می‌شود.



Domain فقط Configurationهای تبدیل‌شده به Policy/Value Object را دریافت می‌کند.





\# 55. EXCEPTIONS



مسیر:



&#x20;   src/ShadBot/Exceptions/





برای Exceptionهای سطح سیستم.



Domain-specific errors ترجیحاً در Domain همان Context قرار می‌گیرند.



Exceptionهای Infrastructure-specific نباید به Domain leak شوند.





\# 56. SHARED



مسیر:



&#x20;   src/ShadBot/Shared/





Shared فقط برای قابلیت‌های واقعاً cross-cutting است.



مثلاً:



&#x20;   constants

&#x20;   utility primitives

&#x20;   common helpers



اما:



&#x20;   Business Logic

&#x20;   Domain Entities



نباید در Shared قرار بگیرند.





\# 57. SHARED RULE



هر چیزی که در Shared قرار می‌گیرد باید ثابت کند که واقعاً:



&#x20;   Cross-Cutting



است.



Shared نباید تبدیل به Junk Drawer شود.





\# 58. TEST STRUCTURE



مسیر:



&#x20;   tests/





ساختار نهایی پیشنهادی:



&#x20;   tests/

&#x20;   │

&#x20;   ├── unit/

&#x20;   │   ├── domain/

&#x20;   │   ├── application/

&#x20;   │   ├── engines/

&#x20;   │   └── infrastructure/

&#x20;   │

&#x20;   ├── integration/

&#x20;   │   ├── data/

&#x20;   │   ├── broker/

&#x20;   │   ├── storage/

&#x20;   │   └── ai/

&#x20;   │

&#x20;   ├── system/

&#x20;   │

&#x20;   └── architecture/





\# 59. UNIT TESTS



Unit Test باید:



&#x20;   fast

&#x20;   deterministic

&#x20;   isolated



باشد.



Domain باید بیشترین Unit Test Coverage را داشته باشد.





\# 60. INTEGRATION TESTS



Integration Test برای:



&#x20;   Broker

&#x20;   Storage

&#x20;   Database

&#x20;   Data Provider

&#x20;   ML Runtime



استفاده می‌شود.





\# 61. SYSTEM TESTS



System Tests جریان‌های کامل را بررسی می‌کنند.



مثلاً:



&#x20;   Data

&#x20;     ↓

&#x20;   Feature

&#x20;     ↓

&#x20;   Prediction

&#x20;     ↓

&#x20;   Decision





یا:



&#x20;   Dataset Update

&#x20;     ↓

&#x20;   Feature Update

&#x20;     ↓

&#x20;   Training

&#x20;     ↓

&#x20;   Evaluation





\# 62. ARCHITECTURE TESTS



Architecture Tests باید Dependency Rules را enforce کنند.



مثلاً:



&#x20;   Domain

&#x20;       X→ Infrastructure



&#x20;   Domain

&#x20;       X→ TensorFlow



&#x20;   Domain

&#x20;       X→ Broker SDK



&#x20;   Domain

&#x20;       X→ GUI



این موارد باید ممنوع باشند.





\# 63. DEPENDENCY DIRECTION



Dependency Direction رسمی:



&#x20;   Interfaces

&#x20;        ↓

&#x20;   Application

&#x20;        ↓

&#x20;   Domain



Infrastructure:



&#x20;   implements contracts

&#x20;   defined by inner layers





به صورت مفهومی:



&#x20;   ┌──────────────────────────────┐

&#x20;   │       Infrastructure        │

&#x20;   │   External Systems / APIs    │

&#x20;   └──────────────┬───────────────┘

&#x20;                  │

&#x20;                  ▼

&#x20;   ┌──────────────────────────────┐

&#x20;   │         Application          │

&#x20;   │        Use Cases             │

&#x20;   └──────────────┬───────────────┘

&#x20;                  │

&#x20;                  ▼

&#x20;   ┌──────────────────────────────┐

&#x20;   │            Domain            │

&#x20;   │ Business Rules / Model       │

&#x20;   └──────────────────────────────┘





\# 64. ENGINE DEPENDENCY



Engineها می‌توانند Application/Domain را مصرف کنند.



اما Engine نباید Domain را با Frameworkهای خارجی آلوده کند.





\# 65. DOMAIN DEPENDENCY RULE



Domain:



&#x20;   MUST NOT depend on Infrastructure

&#x20;   MUST NOT depend on Broker SDK

&#x20;   MUST NOT depend on Database

&#x20;   MUST NOT depend on GUI Framework

&#x20;   MUST NOT depend on TensorFlow

&#x20;   MUST NOT depend on Keras

&#x20;   MUST NOT depend on pandas

&#x20;   MUST NOT depend on mplfinance





\# 66. APPLICATION DEPENDENCY RULE



Application:



&#x20;   MAY depend on Domain

&#x20;   MAY depend on Core



Application نباید مستقیماً Provider-specific implementation را embed کند.





\# 67. INFRASTRUCTURE DEPENDENCY RULE



Infrastructure:



&#x20;   MAY depend on external libraries

&#x20;   MAY depend on SDKs

&#x20;   MAY depend on Database drivers

&#x20;   MAY depend on ML frameworks



اما خروجی باید به Contract/Port مناسب Map شود.





\# 68. ENGINE DEPENDENCY RULE



Engine:



&#x20;   Domain-aware

&#x20;   Application-aware

&#x20;   Runtime-oriented



است.



Engine نباید جای Domain را بگیرد.





\# 69. DATA FLOW — HISTORICAL



جریان رسمی:



&#x20;   Broker / Data Provider

&#x20;            ↓

&#x20;      Data Adapter

&#x20;            ↓

&#x20;      Data Validation

&#x20;            ↓

&#x20;      Raw Dataset

&#x20;            ↓

&#x20;      Processing

&#x20;            ↓

&#x20;      Processed Dataset

&#x20;            ↓

&#x20;      Feature Engineering

&#x20;            ↓

&#x20;      Feature Dataset

&#x20;            ↓

&#x20;      Training





\# 70. DATA FLOW — LIVE



جریان رسمی:



&#x20;   Broker / Live Provider

&#x20;            ↓

&#x20;      Data Adapter

&#x20;            ↓

&#x20;      Live Market Data

&#x20;            ↓

&#x20;      Calculation Window

&#x20;            ↓

&#x20;      Feature Engineering

&#x20;            ↓

&#x20;      Live Feature State

&#x20;            ↓

&#x20;      Inference Window

&#x20;            ↓

&#x20;      Prediction

&#x20;            ↓

&#x20;      Decision

&#x20;            ↓

&#x20;      Risk

&#x20;            ↓

&#x20;      Order

&#x20;            ↓

&#x20;      Execution





\# 71. TRAINING FLOW



&#x20;   Dataset Version

&#x20;        ↓

&#x20;   Feature Set Version

&#x20;        ↓

&#x20;   Training Run

&#x20;        ↓

&#x20;   Model Candidate

&#x20;        ↓

&#x20;   Evaluation

&#x20;        ↓

&#x20;   Approval

&#x20;        ↓

&#x20;   Production Model





\# 72. DATA UPDATE FLOW



Update دوره‌ای:



&#x20;   New Market Data

&#x20;        ↓

&#x20;   Validation

&#x20;        ↓

&#x20;   Deduplication

&#x20;        ↓

&#x20;   Dataset Update

&#x20;        ↓

&#x20;   New Dataset Version

&#x20;        ↓

&#x20;   Feature Engineering

&#x20;        ↓

&#x20;   New Feature Dataset Version





Training نباید الزاماً بعد از هر Data Update اجرا شود.



Training Trigger می‌تواند:



&#x20;   Weekly

&#x20;   Manual

&#x20;   Threshold-based

&#x20;   Scheduled



باشد.





\# 73. LIVE WINDOW POLICY



سیستم باید امکان تعریف:



&#x20;   Calculation Window



و:



&#x20;   Inference Window



را مستقل داشته باشد.



نمونه:



&#x20;   Calculation Window = 1000

&#x20;   Inference Window = 500



این مقادیر Configuration هستند.





\# 74. TRAINING WINDOW POLICY



Training Sample Window باید ثابت و Configurable باشد.



مثلاً:



&#x20;   500 candles



تغییر این مقدار باید Configuration/Experiment Version ایجاد کند.



Training pipeline نباید بدون ثبت Configuration Window را تغییر دهد.





\# 75. LARGE DATA PRINCIPLE



سیستم باید برای Datasetهای بزرگ طراحی شود.



مثلاً:



&#x20;   1 year

&#x20;   5-minute candles

&#x20;   multiple symbols



نباید باعث شود کل Dataset به شکل یک Object در Memory load شود.



Processing باید:



&#x20;   Chunked

&#x20;   Streaming-friendly

&#x20;   Incremental



باشد.





\# 76. DATASET UPDATE FREQUENCY



Dataset Update باید بتواند:



&#x20;   Weekly

&#x20;   Daily

&#x20;   Manual

&#x20;   On Demand



اجرا شود.



Architecture نباید به یک Schedule ثابت وابسته باشد.





\# 77. MODEL TRAINING FREQUENCY



Training نیز مستقل از Dataset Update است.



مثلاً:



&#x20;   Dataset:

&#x20;       weekly update



&#x20;   Training:

&#x20;       manual



یا:



&#x20;   Dataset:

&#x20;       weekly



&#x20;   Training:

&#x20;       weekly



یا:



&#x20;   Dataset:

&#x20;       continuous



&#x20;   Training:

&#x20;       threshold-based





\# 78. PROJECT INTELLIGENCE HANDOFF



ShadBot باید بتواند وضعیت Architecture و Project را به شکل قابل انتقال ذخیره کند.



این قابلیت در مراحل بعدی به صورت رسمی پیاده‌سازی می‌شود.



هدف:



&#x20;   Project State

&#x20;      ↓

&#x20;   Snapshot

&#x20;      ↓

&#x20;   Handoff Document

&#x20;      ↓

&#x20;   Future Agent / ChatGPT





\# 79. ARCHITECTURE DOCUMENTATION



Architecture Documentation باید در:



&#x20;   architecture/



نگهداری شود.



Phaseهای معماری:



&#x20;   P01

&#x20;   P02

&#x20;   P03

&#x20;   P04

&#x20;   ...



باید قابل Trace باشند.





\# 80. NO PARALLEL ARCHITECTURE



ساختارهای زیر ممنوع هستند:



&#x20;   src/domain/

&#x20;   src/ShadBot/Domain/



همزمان نباید وجود داشته باشند.



همچنین:



&#x20;   src/application/

&#x20;   src/ShadBot/Application/



نباید همزمان ساخته شوند.





\# 81. CURRENT ROOT DOMAIN DIRECTORY



Root-level:



&#x20;   DOMAIN/



که در Workspace فعلی وجود دارد، نباید به عنوان Source Package اصلی استفاده شود.



Domain واقعی:



&#x20;   src/ShadBot/Domain/





Root-level DOMAIN صرفاً در صورت نیاز برای Documentation/Legacy باید باقی بماند.



Business Code جدید نباید در آن نوشته شود.





\# 82. CURRENT ROOT DIRECTORIES



Root فعلی:



&#x20;   ARCHITECTURE/

&#x20;   CONFIGS/

&#x20;   DATASETS/

&#x20;   DOCS/

&#x20;   LEGACY/

&#x20;   SCRIPTS/

&#x20;   SRC/

&#x20;   TESTS/



این Structure حفظ می‌شود.



نباید بدون Architecture Decision جدید حذف یا جابه‌جا شود.





\# 83. CURRENT SOURCE TREE



Current source structure:



&#x20;   src/ShadBot/

&#x20;   ├── Application/

&#x20;   ├── Core/

&#x20;   ├── Domain/

&#x20;   ├── Engines/

&#x20;   ├── Exceptions/

&#x20;   ├── Infrastructure/

&#x20;   ├── Interfaces/

&#x20;   ├── Services/

&#x20;   └── Shared/





این ساختار Base Architecture است.





\# 84. ENGINE TREE



Engineهای فعلی:



&#x20;   Engines/

&#x20;   ├── AIEngine/

&#x20;   ├── ContextEngine/

&#x20;   ├── DataEngine/

&#x20;   ├── DecisionEngine/

&#x20;   ├── ExecutionEngine/

&#x20;   ├── FeatureEngineeringEngine/

&#x20;   ├── GuiEngine/

&#x20;   ├── IntelligenceEngine/

&#x20;   ├── MarketEngine/

&#x20;   ├── NewsEngine/

&#x20;   ├── OptimizationEngine/

&#x20;   ├── PortfolioEngine/

&#x20;   ├── SimulationEngine/

&#x20;   └── StorageEngine/





این Engineها در Architecture نهایی حفظ می‌شوند.





\# 85. DOMAIN TREE FINAL



Domain نهایی:



&#x20;   Domain/

&#x20;   ├── Common/

&#x20;   ├── Market/

&#x20;   ├── Dataset/

&#x20;   ├── Feature/

&#x20;   ├── News/

&#x20;   ├── Prediction/

&#x20;   ├── Trading/

&#x20;   ├── Portfolio/

&#x20;   ├── Simulation/

&#x20;   ├── AI/

&#x20;   ├── Optimization/

&#x20;   ├── SelfLearning/

&#x20;   └── ProjectIntelligence/





این ساختار مبنای توسعه Domain خواهد بود.





\# 86. PHYSICAL ARCHITECTURE GRAPH



&#x20;   ShadBot/

&#x20;   │

&#x20;   ├── architecture/

&#x20;   │

&#x20;   ├── configs/

&#x20;   │

&#x20;   ├── datasets/

&#x20;   │   ├── Raw/

&#x20;   │   ├── Processed/

&#x20;   │   └── Features/

&#x20;   │

&#x20;   ├── docs/

&#x20;   │

&#x20;   ├── legacy/

&#x20;   │

&#x20;   ├── scripts/

&#x20;   │

&#x20;   ├── src/

&#x20;   │   └── ShadBot/

&#x20;   │       │

&#x20;   │       ├── Core/

&#x20;   │       │

&#x20;   │       ├── Domain/

&#x20;   │       │   ├── Common/

&#x20;   │       │   ├── Market/

&#x20;   │       │   ├── Dataset/

&#x20;   │       │   ├── Feature/

&#x20;   │       │   ├── News/

&#x20;   │       │   ├── Prediction/

&#x20;   │       │   ├── Trading/

&#x20;   │       │   ├── Portfolio/

&#x20;   │       │   ├── Simulation/

&#x20;   │       │   ├── AI/

&#x20;   │       │   ├── Optimization/

&#x20;   │       │   ├── SelfLearning/

&#x20;   │       │   └── ProjectIntelligence/

&#x20;   │       │

&#x20;   │       ├── Application/

&#x20;   │       │

&#x20;   │       ├── Engines/

&#x20;   │       │   ├── AIEngine/

&#x20;   │       │   ├── ContextEngine/

&#x20;   │       │   ├── DataEngine/

&#x20;   │       │   ├── DecisionEngine/

&#x20;   │       │   ├── ExecutionEngine/

&#x20;   │       │   ├── FeatureEngineeringEngine/

&#x20;   │       │   ├── GuiEngine/

&#x20;   │       │   ├── IntelligenceEngine/

&#x20;   │       │   ├── MarketEngine/

&#x20;   │       │   ├── NewsEngine/

&#x20;   │       │   ├── OptimizationEngine/

&#x20;   │       │   ├── PortfolioEngine/

&#x20;   │       │   ├── SimulationEngine/

&#x20;   │       │   └── StorageEngine/

&#x20;   │       │

&#x20;   │       ├── Exceptions/

&#x20;   │       ├── Infrastructure/

&#x20;   │       ├── Interfaces/

&#x20;   │       ├── Services/

&#x20;   │       └── Shared/

&#x20;   │

&#x20;   └── tests/

&#x20;       ├── unit/

&#x20;       ├── integration/

&#x20;       ├── system/

&#x20;       └── architecture/





\# 87. ARCHITECTURE FREEZE RULE



بعد از تأیید Phase 04:



&#x20;   Project Tree = FROZEN



تغییرات ساختاری فقط با:



&#x20;   Architecture Decision



مجاز هستند.



ساخت Folder جدید برای راحتی Developer بدون Architecture Decision ممنوع است.





\# 88. FILE CREATION RULE



هر فایل جدید باید:



&#x20;   یک Responsibility مشخص



داشته باشد.



فایل‌های Generic مانند:



&#x20;   utils.py

&#x20;   helpers.py

&#x20;   manager.py

&#x20;   common.py



بدون دلیل معماری مشخص ممنوع هستند.





\# 89. MODULE CREATION RULE



هر Module جدید باید حداقل یکی از این موارد را داشته باشد:



&#x20;   Domain Boundary

&#x20;   Application Use Case Boundary

&#x20;   Runtime Engine Boundary

&#x20;   Infrastructure Boundary

&#x20;   External Integration Boundary





\# 90. NO GOD MODULE



نباید Moduleهایی مانند:



&#x20;   DataManager

&#x20;   AIManager

&#x20;   TradingManager

&#x20;   SystemManager



ساخته شوند که چندین Responsibility را همزمان کنترل کنند.





\# 91. NO CIRCULAR DEPENDENCY



Circular dependency بین Moduleها ممنوع است.



Architecture Tests باید این موضوع را بررسی کنند.





\# 92. NO BUSINESS LOGIC IN INFRASTRUCTURE



Infrastructure:



&#x20;   fetches

&#x20;   stores

&#x20;   translates

&#x20;   connects



اما Business Decision نمی‌گیرد.





\# 93. NO BUSINESS LOGIC IN GUI



GUI:



&#x20;   displays

&#x20;   receives user input

&#x20;   triggers Application commands



اما:



&#x20;   trading strategy

&#x20;   risk calculation

&#x20;   prediction logic



را اجرا نمی‌کند.





\# 94. NO BUSINESS LOGIC IN SCRIPTS



Scripts فقط Application/Serviceها را invoke می‌کنند.



مثلاً:



&#x20;   update\_dataset.py



نباید خودش Data Engineering کامل را implement کند.



باید Use Case مربوطه را اجرا کند.





\# 95. NO DIRECT EXTERNAL ACCESS



Domain و Application نباید مستقیماً:



&#x20;   requests

&#x20;   broker SDK

&#x20;   filesystem

&#x20;   database driver



را برای Business Flow صدا بزنند.



External access باید از Boundaryهای مشخص عبور کند.





\# 96. PACKAGE INITIALIZATION



تمام Packageهای معماری باید \_\_init\_\_.py داشته باشند، مطابق Convention فعلی پروژه.



اما \_\_init\_\_.py نباید محل Business Logic باشد.





\# 97. PUBLIC API RULE



هر Module باید مشخص کند چه چیزی Public API آن است.



Internal implementation نباید بدون دلیل توسط Moduleهای دیگر مصرف شود.





\# 98. IMPORT RULE



ترجیح:



&#x20;   from ShadBot.Domain.Market import ...



به import کردن Implementationهای داخلی عمیق و شکننده.



Public APIها باید در آینده مشخص شوند.





\# 99. ARCHITECTURE VALIDATION



بعد از ساخت Structure باید موارد زیر بررسی شوند:



&#x20;   Python import validation

&#x20;   Package validation

&#x20;   Architecture dependency validation

&#x20;   Test discovery

&#x20;   Ruff

&#x20;   Black

&#x20;   Mypy

&#x20;   Pytest





\# 100. PHASE 04 ACCEPTANCE CRITERIA



\[x] Root Repository Structure defined.

\[x] src structure defined.

\[x] Domain structure defined.

\[x] Application structure defined.

\[x] Core responsibility defined.

\[x] Engine structure defined.

\[x] Infrastructure structure defined.

\[x] Interfaces defined.

\[x] Services defined.

\[x] Shared defined.

\[x] Exceptions defined.

\[x] Dataset storage structure defined.

\[x] Test structure defined.

\[x] Dependency direction defined.

\[x] Domain isolation defined.

\[x] Broker isolation defined.

\[x] ML framework isolation defined.

\[x] GUI isolation defined.

\[x] Database isolation defined.

\[x] Historical data architecture defined.

\[x] Live data architecture defined.

\[x] Calculation Window defined.

\[x] Inference Window defined.

\[x] Training data flow defined.

\[x] Dataset update flow defined.

\[x] Model training flow defined.

\[x] Project Intelligence location defined.

\[x] Desktop-only runtime defined.

\[x] No Web Dashboard dependency.

\[x] No Mobile dependency.

\[x] No parallel source architecture.

\[x] Root DOMAIN directory clarified.

\[x] Engine boundaries defined.

\[x] Domain boundaries defined.

\[x] Infrastructure boundary defined.

\[x] Testing boundaries defined.

\[x] Architecture Freeze rule defined.





\# 101. FINAL PROJECT TREE DECISION



Project Tree از این Phase به بعد به عنوان:



&#x20;   SHADB0T PHYSICAL ARCHITECTURE BASELINE



شناخته می‌شود.



ساختار جدید فقط در صورت وجود Architecture Decision جدید قابل اضافه شدن است.





\# 102. PHASE 04 FINAL STATUS



PHASE:

04 — PROJECT TREE / PHYSICAL ARCHITECTURE



STATUS:

FINAL BASELINE



PROJECT TREE:

FROZEN AFTER APPROVAL



NEXT PHASE:

05 — FRAMEWORK DESIGN



IMPORTANT:



Phase 05 باید Frameworkها، Libraryها، Runtime Technologyها، Adapterها و Technology Boundaryها را تعیین کند.



Domain Architecture نباید به خاطر انتخاب Framework تغییر کند.

