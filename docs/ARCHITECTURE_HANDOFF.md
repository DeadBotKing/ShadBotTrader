================================================================================

SHADBOT

ENTERPRISE AI TRADING PLATFORM

================================================================================



ARCHITECTURE HANDOFF

MASTER IMPLEMENTATION CONTRACT

VERSION: 1.0

ARCHITECTURE STATUS: FROZEN

IMPLEMENTATION STATUS: ACTIVE

================================================================================





DOCUMENT PURPOSE

================================================================================



این سند مرجع اصلی برای هر Developer / AI Agent / Coding Agent است که قرار است

روی ShadBot کار کند.



این سند باید به‌گونه‌ای باشد که یک عامل کاملاً جدید بتواند:



&#x20;   1. پروژه را از صفر درک کند.

&#x20;   2. Architecture را بفهمد.

&#x20;   3. Dependency Rules را بفهمد.

&#x20;   4. Domain Model را بفهمد.

&#x20;   5. Project Structure را بسازد.

&#x20;   6. Runtime را پیاده‌سازی کند.

&#x20;   7. تمام Platformها را پیاده‌سازی کند.

&#x20;   8. تست بنویسد.

&#x20;   9. Quality Gate را اجرا کند.

&#x20;   10. Architecture Drift را تشخیص دهد.

&#x20;   11. Project Intelligence را اجرا کند.

&#x20;   12. از وضعیت فعلی پروژه Snapshot بگیرد.

&#x20;   13. بدون سؤال‌های غیرضروری Phase بعدی را اجرا کند.

&#x20;   14. بدون Redesign کردن Architecture به توسعه ادامه دهد.





================================================================================

ABSOLUTE RULE

================================================================================



این فایل یک پیشنهاد نیست.



این فایل:



&#x20;   IMPLEMENTATION CONTRACT



است.



هر چیزی که در این سند مشخص شده باید رعایت شود.



Developer / Agent حق ندارد صرفاً به دلیل اینکه روش دیگری را ترجیح می‌دهد

Architecture را تغییر دهد.





================================================================================

CRITICAL IMPLEMENTATION RULES

================================================================================



RULE 001

\--------

Architecture را دوباره طراحی نکن.



RULE 002

\--------

اگر چیزی در Architecture تعریف شده ولی هنوز وجود ندارد:



&#x20;   IMPLEMENT IT.



نه اینکه Architecture را حذف یا ساده کنی.



RULE 003

\--------

اگر Implementation موجود با Architecture مغایرت دارد:



&#x20;   FIX IMPLEMENTATION.



RULE 004

\--------

کد Placeholder ممنوع است.



ممنوع:



&#x20;   pass

&#x20;   TODO implementation

&#x20;   fake service

&#x20;   dummy production implementation

&#x20;   hard-coded fake data

&#x20;   temporary architecture



RULE 005

\--------

Mock فقط برای Test مجاز است.



RULE 006

\--------

Domain نباید به Infrastructure وابسته شود.



RULE 007

\--------

Infrastructure نباید Business Logic را مالک شود.



RULE 008

\--------

Application مسئول orchestration است.



RULE 009

\--------

Core باید مستقل از Domain باشد.



RULE 010

\--------

هر Feature جدید باید از Contract عبور کند.



RULE 011

\--------

هر تغییر باید Test داشته باشد.



RULE 012

\--------

هر تغییر باید Quality Gate را Pass کند.



RULE 013

\--------

هر تغییر مهم باید Git Commit داشته باشد.



RULE 014

\--------

Project Intelligence باید وضعیت واقعی پروژه را ثبت کند.



RULE 015

\--------

هر Chat جدید باید بتواند با Project State وضعیت پروژه را reconstruct کند.





================================================================================

1\. PROJECT IDENTITY

================================================================================



PROJECT NAME:



&#x20;   ShadBot



PROJECT TYPE:



&#x20;   Enterprise AI Trading Platform



PRIMARY LANGUAGE:



&#x20;   Python



PRIMARY OBJECTIVES:



&#x20;   Market Data

&#x20;   Feature Engineering

&#x20;   AI / ML

&#x20;   Prediction

&#x20;   Signal Generation

&#x20;   Risk Management

&#x20;   Trading

&#x20;   Portfolio Management

&#x20;   Simulation

&#x20;   Backtesting

&#x20;   Optimization

&#x20;   Self Learning

&#x20;   Project Intelligence

&#x20;   Autonomous Development





================================================================================

2\. HIGH LEVEL SYSTEM

================================================================================



ShadBot از چند Platform مستقل ولی متصل تشکیل می‌شود:



&#x20;   Core Platform

&#x20;   Domain Platform

&#x20;   Application Platform

&#x20;   Infrastructure Platform

&#x20;   Data Platform

&#x20;   Feature Platform

&#x20;   AI Platform

&#x20;   Trading Platform

&#x20;   Portfolio Platform

&#x20;   Simulation Platform

&#x20;   Optimization Platform

&#x20;   Self Learning Platform

&#x20;   Project Intelligence Platform

&#x20;   Plugin Platform

&#x20;   Event Platform

&#x20;   GUI Platform

&#x20;   Agent Platform





================================================================================

3\. ARCHITECTURE STYLE

================================================================================



Architecture ترکیبی است از:



&#x20;   Clean Architecture

&#x20;   Domain Driven Design

&#x20;   Modular Architecture

&#x20;   Dependency Inversion

&#x20;   Plugin Architecture

&#x20;   Event Driven Architecture

&#x20;   Service Oriented Application Layer





اصل:



&#x20;   Business Logic must remain independent from Infrastructure.





================================================================================

4\. ARCHITECTURE LAYERS

================================================================================



Dependency Direction:



&#x20;   Core

&#x20;     ↑

&#x20;   Domain

&#x20;     ↑

&#x20;   Application

&#x20;     ↑

&#x20;   Infrastructure



به صورت منطقی:



&#x20;   Core

&#x20;     ↓

&#x20;   Domain

&#x20;     ↓

&#x20;   Application

&#x20;     ↓

&#x20;   Infrastructure



اما Dependency باید فقط در جهت مجاز Architecture باشد.



هیچ Layer نباید Dependency Cycle ایجاد کند.





================================================================================

5\. CORE PLATFORM

================================================================================



LOCATION:



&#x20;   src/ShadBot/core/





RESPONSIBILITY:



Core Primitiveهای کل سیستم را تعریف می‌کند.





CURRENT COMPONENTS:



&#x20;   dependency/

&#x20;       container.py



&#x20;   events/

&#x20;       event.py

&#x20;       eventBus.py



&#x20;   lifecycle/

&#x20;       lifecycleManager.py



&#x20;   plugins/

&#x20;       plugin.py



&#x20;   services/

&#x20;       baseService.py





CORE MUST CONTAIN:



&#x20;   Entity primitives

&#x20;   Result primitives

&#x20;   Error primitives

&#x20;   Event primitives

&#x20;   Lifecycle primitives

&#x20;   Dependency primitives

&#x20;   Service primitives

&#x20;   Plugin primitives





CORE MUST NOT CONTAIN:



&#x20;   Trading Logic

&#x20;   AI Logic

&#x20;   Database Logic

&#x20;   Broker Logic

&#x20;   Market Strategy

&#x20;   GUI Logic





================================================================================

6\. DOMAIN PLATFORM

================================================================================



LOCATION:



&#x20;   src/ShadBot/domain/





DOMAIN AREAS:



&#x20;   common/

&#x20;   market/

&#x20;   trading/

&#x20;   portfolio/

&#x20;   prediction/

&#x20;   risk/

&#x20;   news/





CURRENT MODELS:



&#x20;   common/

&#x20;       entity.py

&#x20;       valueObject.py



&#x20;   market/

&#x20;       candle.py

&#x20;       symbol.py

&#x20;       timefram.py



&#x20;   portfolio/

&#x20;       account.py

&#x20;       balance.py



&#x20;   prediction/

&#x20;       prediction.py

&#x20;       signal.py



&#x20;   risk/

&#x20;       riskModel.py



&#x20;   trading/

&#x20;       oerder.py

&#x20;       position.py

&#x20;       trade.py





IMPORTANT:



&#x20;   File names فعلی ممکن است بعداً با استاندارد Naming اصلاح شوند.



مثلاً:



&#x20;   timefram.py → timeframe.py

&#x20;   oerder.py   → order.py



این اصلاح مجاز است زیرا Architecture را تغییر نمی‌دهد.





================================================================================

7\. DOMAIN RULES

================================================================================



Domain باید:



&#x20;   Framework Independent

&#x20;   Infrastructure Independent

&#x20;   Database Independent

&#x20;   Broker Independent

&#x20;   AI Provider Independent





Domain می‌تواند:



&#x20;   Value Objects

&#x20;   Entities

&#x20;   Aggregates

&#x20;   Domain Services

&#x20;   Domain Events

&#x20;   Business Rules



داشته باشد.





================================================================================

8\. VALUE OBJECT

================================================================================



Value Object:



&#x20;   identity ندارد.



برابری:



&#x20;   by value



است.



در صورت امکان:



&#x20;   immutable





================================================================================

9\. ENTITY

================================================================================



Entity:



&#x20;   identity دارد.



Identity باید deterministic و قابل تست باشد.





================================================================================

10\. MARKET DOMAIN

================================================================================



MARKET COMPONENTS:



&#x20;   Symbol

&#x20;   TimeFrame

&#x20;   Candle





CANDLE:



&#x20;   timestamp

&#x20;   open

&#x20;   high

&#x20;   low

&#x20;   close

&#x20;   volume





INVARIANTS:



&#x20;   high >= open

&#x20;   high >= close

&#x20;   high >= low



&#x20;   low <= open

&#x20;   low <= close





Invalid Candle:



&#x20;   MUST FAIL VALIDATION





================================================================================

11\. TRADING DOMAIN

================================================================================



COMPONENTS:



&#x20;   Order

&#x20;   Position

&#x20;   Trade





ORDER LIFECYCLE:



&#x20;   CREATED

&#x20;   SUBMITTED

&#x20;   ACCEPTED

&#x20;   REJECTED

&#x20;   PARTIALLY\_FILLED

&#x20;   FILLED

&#x20;   CANCELLED





ORDER MUST CONTAIN:



&#x20;   order\_id

&#x20;   symbol

&#x20;   side

&#x20;   quantity

&#x20;   order\_type

&#x20;   status

&#x20;   timestamps





================================================================================

12\. POSITION

================================================================================



Position باید حداقل:



&#x20;   symbol

&#x20;   quantity

&#x20;   average\_price

&#x20;   side

&#x20;   opened\_at





را مدیریت کند.





================================================================================

13\. TRADE

================================================================================



Trade باید:



&#x20;   entry

&#x20;   exit

&#x20;   quantity

&#x20;   pnl

&#x20;   timestamps





را نگهداری کند.





================================================================================

14\. PORTFOLIO DOMAIN

================================================================================



COMPONENTS:



&#x20;   Account

&#x20;   Balance

&#x20;   Position

&#x20;   Exposure

&#x20;   Allocation

&#x20;   Performance





Portfolio باید:



&#x20;   balance

&#x20;   equity

&#x20;   exposure

&#x20;   PnL





را قابل محاسبه کند.





================================================================================

15\. PREDICTION DOMAIN

================================================================================



Prediction:



&#x20;   model\_id

&#x20;   model\_version

&#x20;   timestamp

&#x20;   value

&#x20;   confidence





Signal:



&#x20;   BUY

&#x20;   SELL

&#x20;   HOLD





Prediction و Signal نباید وابسته به TensorFlow / Keras / PyTorch باشند.





================================================================================

16\. RISK DOMAIN

================================================================================



Risk مسئول:



&#x20;   Position Risk

&#x20;   Exposure Risk

&#x20;   Drawdown

&#x20;   Order Risk

&#x20;   Portfolio Risk





Risk باید قبل از Execution اعمال شود.





================================================================================

17\. APPLICATION PLATFORM

================================================================================



LOCATION:



&#x20;   src/ShadBot/application/





CURRENT FILES:



&#x20;   app.py

&#x20;   applicationState.py

&#x20;   bootstrap.py

&#x20;   runtime.py

&#x20;   serviceRegistry.py

&#x20;   startup.py

&#x20;   shutdown.py





RESPONSIBILITY:



&#x20;   Use Case Orchestration

&#x20;   Runtime Coordination

&#x20;   Service Coordination

&#x20;   Dependency Composition





Application نباید:



&#x20;   Database Implementation



را مالک شود.





================================================================================

18\. APPLICATION LIFECYCLE

================================================================================



START:



&#x20;   CREATED

&#x20;      ↓

&#x20;   INITIALIZING

&#x20;      ↓

&#x20;   READY

&#x20;      ↓

&#x20;   RUNNING





STOP:



&#x20;   RUNNING

&#x20;      ↓

&#x20;   STOPPING

&#x20;      ↓

&#x20;   STOPPED





FAILURE:



&#x20;   Any State

&#x20;      ↓

&#x20;   FAILED





Invalid State Transition:



&#x20;   MUST FAIL





================================================================================

19\. BOOTSTRAP

================================================================================



Bootstrap:



&#x20;   Load Config

&#x20;      ↓

&#x20;   Create Container

&#x20;      ↓

&#x20;   Register Infrastructure

&#x20;      ↓

&#x20;   Register Services

&#x20;      ↓

&#x20;   Register Engines

&#x20;      ↓

&#x20;   Register Plugins

&#x20;      ↓

&#x20;   Start Runtime





Bootstrap is the Composition Root.





================================================================================

20\. DEPENDENCY INJECTION

================================================================================



Dependency Injection باید:



&#x20;   Explicit

&#x20;   Testable

&#x20;   Deterministic





SUPPORTED LIFETIMES:



&#x20;   Singleton

&#x20;   Transient



Future:



&#x20;   Scoped





DOMAIN MUST NEVER:



&#x20;   resolve dependencies from global container.





================================================================================

21\. SERVICE REGISTRY

================================================================================



Service Registry:



&#x20;   register

&#x20;   resolve

&#x20;   contains





Service Registry نباید جایگزین Domain Dependency Injection شود.





================================================================================

22\. EVENT PLATFORM

================================================================================



Event:



&#x20;   event\_id

&#x20;   event\_type

&#x20;   occurred\_at

&#x20;   payload





EventBus:



&#x20;   publish()

&#x20;   subscribe()

&#x20;   unsubscribe()





Initial implementation:



&#x20;   synchronous

&#x20;   deterministic





Future extension:



&#x20;   async event dispatch





================================================================================

23\. EVENT ERROR POLICY

================================================================================



Supported conceptual policies:



&#x20;   FAIL\_FAST

&#x20;   CONTINUE

&#x20;   COLLECT\_ERRORS





Policy باید configurable باشد.





================================================================================

24\. PLUGIN PLATFORM

================================================================================



Plugin Contract:



&#x20;   name

&#x20;   version

&#x20;   initialize()

&#x20;   start()

&#x20;   stop()





PLUGIN LIFECYCLE:



&#x20;   DISCOVER

&#x20;      ↓

&#x20;   VALIDATE

&#x20;      ↓

&#x20;   LOAD

&#x20;      ↓

&#x20;   INITIALIZE

&#x20;      ↓

&#x20;   START

&#x20;      ↓

&#x20;   STOP





================================================================================

25\. INFRASTRUCTURE PLATFORM

================================================================================



LOCATION:



&#x20;   src/ShadBot/infrastructure/





TARGET STRUCTURE:



&#x20;   configuration/

&#x20;   logging/

&#x20;   persistence/

&#x20;   filesystem/

&#x20;   external/

&#x20;   serialization/

&#x20;   time/





Infrastructure مسئول:



&#x20;   External Systems

&#x20;   Database

&#x20;   Filesystem

&#x20;   APIs

&#x20;   Providers

&#x20;   Serialization

&#x20;   Logging

&#x20;   Configuration





================================================================================

26\. CONFIGURATION

================================================================================



Configuration must be:



&#x20;   typed

&#x20;   validated

&#x20;   environment-aware





ENVIRONMENTS:



&#x20;   development

&#x20;   test

&#x20;   staging

&#x20;   production





INVALID CONFIG:



&#x20;   MUST PREVENT STARTUP





================================================================================

27\. LOGGING

================================================================================



Logging must be structured.



MINIMUM:



&#x20;   timestamp

&#x20;   level

&#x20;   logger

&#x20;   message





RUNTIME CONTEXT:



&#x20;   correlation\_id

&#x20;   component

&#x20;   operation





================================================================================

28\. ERROR SYSTEM

================================================================================



BASE:



&#x20;   ShadBotError





CHILDREN:



&#x20;   DomainError

&#x20;   ApplicationError

&#x20;   InfrastructureError

&#x20;   ConfigurationError

&#x20;   ValidationError

&#x20;   RuntimeError





ERROR SHOULD SUPPORT:



&#x20;   code

&#x20;   message

&#x20;   details

&#x20;   cause





================================================================================

29\. RESULT SYSTEM

================================================================================



Result:



&#x20;   Success\[T]

&#x20;   Failure\[E]





Purpose:



&#x20;   Explicit operation outcome.





Exceptions:



&#x20;   Exceptional Conditions





Result:



&#x20;   Expected Failure Conditions





================================================================================

30\. ENGINE PLATFORM

================================================================================



LOCATION:



&#x20;   src/ShadBot/engines/





ENGINES:



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





ENGINE RULE:



&#x20;   Each Engine owns one capability boundary.





Engine نباید تبدیل به God Object شود.





================================================================================

31\. DATA PLATFORM

================================================================================



DATA FLOW:



&#x20;   Provider

&#x20;      ↓

&#x20;   Acquisition

&#x20;      ↓

&#x20;   Validation

&#x20;      ↓

&#x20;   Normalization

&#x20;      ↓

&#x20;   Storage

&#x20;      ↓

&#x20;   Retrieval





DATA SOURCES:



&#x20;   Market Data

&#x20;   News Data

&#x20;   Alternative Data

&#x20;   External APIs

&#x20;   Historical Data





================================================================================

32\. DATA PROVIDER

================================================================================



Interface:



&#x20;   DataProvider





Implementations:



&#x20;   ForexProvider

&#x20;   CryptoProvider

&#x20;   StockProvider

&#x20;   CommodityProvider

&#x20;   etc.





Domain باید فقط Contract را بشناسد.





================================================================================

33\. DATASETS

================================================================================



Current:



&#x20;   datasets/

&#x20;       Raw/

&#x20;       Processed/

&#x20;       Features/





RULE:



&#x20;   Raw Data must remain immutable.





Processed:



&#x20;   Derived from Raw.





Features:



&#x20;   Derived from Processed / validated inputs.





================================================================================

34\. FEATURE PLATFORM

================================================================================



PIPELINE:



&#x20;   Raw

&#x20;     ↓

&#x20;   Clean

&#x20;     ↓

&#x20;   Normalize

&#x20;     ↓

&#x20;   Transform

&#x20;     ↓

&#x20;   Feature Calculation

&#x20;     ↓

&#x20;   Validation

&#x20;     ↓

&#x20;   Feature Store





FEATURE MUST TRACK:



&#x20;   name

&#x20;   version

&#x20;   source

&#x20;   parameters

&#x20;   timestamp





================================================================================

35\. AI PLATFORM

================================================================================



AI PIPELINE:



&#x20;   Dataset

&#x20;      ↓

&#x20;   Preprocessing

&#x20;      ↓

&#x20;   Training

&#x20;      ↓

&#x20;   Validation

&#x20;      ↓

&#x20;   Evaluation

&#x20;      ↓

&#x20;   Registry

&#x20;      ↓

&#x20;   Inference





SUPPORTED FUTURE TECHNOLOGIES:



&#x20;   TensorFlow

&#x20;   Keras

&#x20;   PyTorch

&#x20;   other providers





AI Provider must be replaceable.





================================================================================

36\. MODEL REGISTRY

================================================================================



MODEL METADATA:



&#x20;   model\_id

&#x20;   version

&#x20;   dataset\_version

&#x20;   training\_config

&#x20;   metrics

&#x20;   created\_at

&#x20;   status





MODEL STATUS:



&#x20;   CREATED

&#x20;   TRAINING

&#x20;   VALIDATED

&#x20;   ACTIVE

&#x20;   DEPRECATED





================================================================================

37\. AI INFERENCE

================================================================================



Inference:



&#x20;   Input

&#x20;      ↓

&#x20;   Preprocessing

&#x20;      ↓

&#x20;   Model

&#x20;      ↓

&#x20;   Prediction

&#x20;      ↓

&#x20;   Validation

&#x20;      ↓

&#x20;   Signal





Inference must be deterministic when configured for reproducibility.





================================================================================

38\. TRADING PLATFORM

================================================================================



TRADING FLOW:



&#x20;   Market Data

&#x20;      ↓

&#x20;   Features

&#x20;      ↓

&#x20;   Prediction

&#x20;      ↓

&#x20;   Signal

&#x20;      ↓

&#x20;   Risk

&#x20;      ↓

&#x20;   Decision

&#x20;      ↓

&#x20;   Order

&#x20;      ↓

&#x20;   Execution

&#x20;      ↓

&#x20;   Position

&#x20;      ↓

&#x20;   Portfolio





================================================================================

39\. DECISION ENGINE

================================================================================



Decision combines:



&#x20;   Signal

&#x20;   Risk

&#x20;   Portfolio State

&#x20;   Market Context

&#x20;   Strategy Rules





Output:



&#x20;   Trading Decision





Possible:



&#x20;   BUY

&#x20;   SELL

&#x20;   HOLD

&#x20;   REJECT





================================================================================

40\. EXECUTION ENGINE

================================================================================



Execution is responsible for:



&#x20;   Order Submission

&#x20;   Order Tracking

&#x20;   Fill Processing

&#x20;   Reconciliation





Execution must use:



&#x20;   Broker Adapter





Never directly call broker SDK from Domain.





================================================================================

41\. BROKER ABSTRACTION

================================================================================



Contract:



&#x20;   Broker





Operations:



&#x20;   submit\_order

&#x20;   cancel\_order

&#x20;   get\_order

&#x20;   get\_position

&#x20;   get\_balance





Future implementations:



&#x20;   PaperBroker

&#x20;   BacktestBroker

&#x20;   LiveBroker





================================================================================

42\. LIVE TRADING SAFETY

================================================================================



Default:



&#x20;   LIVE TRADING OFF





Explicit configuration required.





No accidental live execution.





================================================================================

43\. PORTFOLIO PLATFORM

================================================================================



Portfolio calculates:



&#x20;   Balance

&#x20;   Equity

&#x20;   Exposure

&#x20;   PnL

&#x20;   Drawdown

&#x20;   Allocation

&#x20;   Performance





Portfolio must reconcile with execution results.





================================================================================

44\. SIMULATION PLATFORM

================================================================================



Simulation provides:



&#x20;   Backtesting

&#x20;   Replay

&#x20;   Paper Trading

&#x20;   Historical Simulation





ARCHITECTURAL PRINCIPLE:



&#x20;   Simulation should reuse Trading Contracts.





Only execution implementation changes.





================================================================================

45\. BACKTESTING

================================================================================



FLOW:



&#x20;   Historical Data

&#x20;      ↓

&#x20;   Replay

&#x20;      ↓

&#x20;   Strategy

&#x20;      ↓

&#x20;   Signal

&#x20;      ↓

&#x20;   Risk

&#x20;      ↓

&#x20;   Simulated Execution

&#x20;      ↓

&#x20;   Portfolio

&#x20;      ↓

&#x20;   Metrics





================================================================================

46\. OPTIMIZATION PLATFORM

================================================================================



Optimization:



&#x20;   Strategy Parameters

&#x20;      ↓

&#x20;   Experiment

&#x20;      ↓

&#x20;   Simulation

&#x20;      ↓

&#x20;   Metrics

&#x20;      ↓

&#x20;   Comparison

&#x20;      ↓

&#x20;   Best Candidate





Must support:



&#x20;   reproducibility

&#x20;   experiment tracking





================================================================================

47\. SELF LEARNING PLATFORM

================================================================================



FLOW:



&#x20;   Production Outcome

&#x20;      ↓

&#x20;   Evaluation

&#x20;      ↓

&#x20;   Feedback

&#x20;      ↓

&#x20;   Experiment

&#x20;      ↓

&#x20;   Training

&#x20;      ↓

&#x20;   Validation

&#x20;      ↓

&#x20;   Model Candidate

&#x20;      ↓

&#x20;   Promotion





No automatic model promotion without validation.





================================================================================

48\. PROJECT INTELLIGENCE PLATFORM

================================================================================



PURPOSE:



&#x20;   ShadBot must understand itself.





LOCATION:



&#x20;   src/ShadBot/project/





CURRENT STRUCTURE:



&#x20;   project/

&#x20;       core/

&#x20;       models/

&#x20;       builders/

&#x20;       exporters/

&#x20;       runtime/





CORE SCANNERS:



&#x20;   projectScanner.py

&#x20;   astScanner.py

&#x20;   gitScanner.py

&#x20;   configScanner.py

&#x20;   dependencyScanner.py

&#x20;   packageScanner.py

&#x20;   statisticsScanner.py

&#x20;   roadmapScanner.py

&#x20;   decisionScanner.py

&#x20;   todoScanner.py





================================================================================

49\. PROJECT MODELS

================================================================================



MODELS:



&#x20;   ProjectSnapshot

&#x20;   ProjectStatistics

&#x20;   ProjectContext

&#x20;   Roadmap

&#x20;   Decision





================================================================================

50\. PROJECT BUILDERS

================================================================================



BUILDERS:



&#x20;   SnapshotBuilder

&#x20;   ContextBuilder

&#x20;   RoadmapBuilder

&#x20;   StatisticsBuilder

&#x20;   DocumentationBuilder





================================================================================

51\. PROJECT EXPORTERS

================================================================================



EXPORTERS:



&#x20;   MarkdownExporter

&#x20;   JsonExporter

&#x20;   HtmlExporter

&#x20;   PdfExporter





================================================================================

52\. PROJECT RUNTIME

================================================================================



CURRENT:



&#x20;   intelligenceRuntime.py





RESPONSIBILITY:



&#x20;   Run Project Intelligence pipeline.





================================================================================

53\. PROJECT INTELLIGENCE PIPELINE

================================================================================



PIPELINE:



&#x20;   Snapshot

&#x20;      ↓

&#x20;   Analysis

&#x20;      ↓

&#x20;   Evolution

&#x20;      ↓

&#x20;   Insight

&#x20;      ↓

&#x20;   Recommendation

&#x20;      ↓

&#x20;   Decision





At minimum initial implementation must support:



&#x20;   Scan

&#x20;   Snapshot

&#x20;   Context

&#x20;   Statistics

&#x20;   Git

&#x20;   Roadmap





================================================================================

54\. PROJECT SCANNER

================================================================================



Must detect:



&#x20;   directories

&#x20;   files

&#x20;   Python modules

&#x20;   packages

&#x20;   tests

&#x20;   configuration

&#x20;   documentation





Must ignore:



&#x20;   .git

&#x20;   .venv

&#x20;   \_\_pycache\_\_

&#x20;   generated cache

&#x20;   temporary files





================================================================================

55\. AST SCANNER

================================================================================



AST scanner must detect:



&#x20;   classes

&#x20;   functions

&#x20;   imports

&#x20;   decorators

&#x20;   inheritance

&#x20;   module dependencies





Purpose:



&#x20;   Structural understanding.





================================================================================

56\. GIT SCANNER

================================================================================



Must detect:



&#x20;   branch

&#x20;   current commit

&#x20;   recent commits

&#x20;   dirty state

&#x20;   tracked files





================================================================================

57\. DEPENDENCY SCANNER

================================================================================



Must detect:



&#x20;   internal dependencies

&#x20;   external dependencies

&#x20;   import relationships





Output:



&#x20;   DependencyGraph





================================================================================

58\. STATISTICS

================================================================================



Statistics should include:



&#x20;   source file count

&#x20;   test file count

&#x20;   line count

&#x20;   module count

&#x20;   class count

&#x20;   function count

&#x20;   dependency count





================================================================================

59\. PROJECT STATE

================================================================================



LOCATION:



&#x20;   project\_state/





STRUCTURE:



&#x20;   generated/

&#x20;   archive/





GENERATED:



&#x20;   ProjectSnapshot.md

&#x20;   ProjectSnapshot.json

&#x20;   ChatGPT\_Context.md

&#x20;   Architecture.md

&#x20;   Roadmap.md

&#x20;   Decisions.md

&#x20;   Todo.md

&#x20;   Statistics.json

&#x20;   DependencyGraph.json





================================================================================

60\. PROJECT SNAPSHOT

================================================================================



Snapshot must contain:



&#x20;   project\_name

&#x20;   project\_version

&#x20;   architecture\_version

&#x20;   current\_phase

&#x20;   git\_branch

&#x20;   git\_commit

&#x20;   dirty\_state

&#x20;   python\_version

&#x20;   source\_statistics

&#x20;   modules

&#x20;   dependencies

&#x20;   architecture\_status

&#x20;   implementation\_status





================================================================================

61\. CHATGPT CONTEXT

================================================================================



ChatGPT\_Context.md is the primary handoff artifact.



It must answer:



&#x20;   What is ShadBot?

&#x20;   What Architecture does it use?

&#x20;   Which Phase is complete?

&#x20;   What is implemented?

&#x20;   What is missing?

&#x20;   What decisions were made?

&#x20;   What is the current Git commit?

&#x20;   What tests pass?

&#x20;   What is the next task?





================================================================================

62\. ROADMAP

================================================================================



Roadmap must contain:



&#x20;   Completed

&#x20;   Current

&#x20;   Next

&#x20;   Future





Every item should have:



&#x20;   ID

&#x20;   Status

&#x20;   Description

&#x20;   Dependencies





================================================================================

63\. DECISION LOG

================================================================================



Decision:



&#x20;   ID

&#x20;   Title

&#x20;   Context

&#x20;   Decision

&#x20;   Reason

&#x20;   Date

&#x20;   Status





Important architecture decisions must NEVER disappear.





================================================================================

64\. TODO SYSTEM

================================================================================



TODO must distinguish:



&#x20;   BLOCKER

&#x20;   HIGH

&#x20;   MEDIUM

&#x20;   LOW





TODO should be generated from:



&#x20;   Architecture

&#x20;   Implementation

&#x20;   Tests

&#x20;   Git

&#x20;   Project Intelligence





================================================================================

65\. ARCHITECTURE VALIDATOR

================================================================================



Validator checks:



&#x20;   Directory Structure

&#x20;   Package Structure

&#x20;   Import Rules

&#x20;   Dependency Direction

&#x20;   Required Modules

&#x20;   Forbidden Dependencies





Example:



&#x20;   Domain → Infrastructure



MUST FAIL.





================================================================================

66\. ARCHITECTURE DRIFT

================================================================================



Drift examples:



&#x20;   Missing required module

&#x20;   Unauthorized import

&#x20;   Unexpected dependency

&#x20;   Wrong package ownership

&#x20;   Missing contract

&#x20;   Architecture version mismatch





Drift must be reported.





================================================================================

67\. IMPLEMENTATION STATUS

================================================================================



Each component:



&#x20;   PLANNED

&#x20;   SCAFFOLDED

&#x20;   IMPLEMENTED

&#x20;   TESTED

&#x20;   VALIDATED

&#x20;   PRODUCTION\_READY





================================================================================

68\. IMPLEMENTATION MATRIX

================================================================================



For every architecture component:



&#x20;   Architecture Component

&#x20;       ↓

&#x20;   Source File

&#x20;       ↓

&#x20;   Contract

&#x20;       ↓

&#x20;   Implementation

&#x20;       ↓

&#x20;   Tests

&#x20;       ↓

&#x20;   Validation

&#x20;       ↓

&#x20;   Status





================================================================================

69\. GUI PLATFORM

================================================================================



GUI must NOT access:



&#x20;   Database directly

&#x20;   Domain internals directly

&#x20;   Broker SDK directly





GUI uses:



&#x20;   Application APIs

&#x20;   Query Services

&#x20;   Event Streams





Potential future UI:



&#x20;   Dashboard

&#x20;   Market View

&#x20;   Portfolio View

&#x20;   AI View

&#x20;   Backtest View

&#x20;   Project Intelligence View

&#x20;   Agent View





================================================================================

70\. AGENT PLATFORM

================================================================================



Future Agent Architecture:



&#x20;   EYES

&#x20;   BRAIN

&#x20;   HANDS

&#x20;   QUALITY GATE





================================================================================

71\. AGENT EYES

================================================================================



Eyes:



&#x20;   Workspace Inspection

&#x20;   File Reading

&#x20;   AST

&#x20;   Git

&#x20;   Project Intelligence





Agent must observe before modifying.





================================================================================

72\. AGENT BRAIN

================================================================================



Brain:



&#x20;   LLM

&#x20;   Reasoning

&#x20;   Planning

&#x20;   Decision Making





Potential provider:



&#x20;   Ollama





Potential models:



&#x20;   Qwen Coder





Provider must remain replaceable.





================================================================================

73\. AGENT HANDS

================================================================================



Hands:



&#x20;   File Create

&#x20;   File Read

&#x20;   File Modify

&#x20;   Command Execute

&#x20;   Test Execute





All actions must be auditable.





================================================================================

74\. AGENT QUALITY GATE

================================================================================



Agent must execute:



&#x20;   Ruff

&#x20;   Black

&#x20;   Mypy

&#x20;   Pytest





If failure:



&#x20;   Analyze

&#x20;      ↓

&#x20;   Fix

&#x20;      ↓

&#x20;   Re-run





Until:



&#x20;   GREEN



or:



&#x20;   Explicitly blocked.





================================================================================

75\. AGENT SAFETY

================================================================================



Agent must not:



&#x20;   silently delete architecture

&#x20;   silently rewrite large subsystems

&#x20;   change architecture without approval

&#x20;   bypass tests

&#x20;   ignore quality failures

&#x20;   enable live trading automatically





================================================================================

76\. TESTING ARCHITECTURE

================================================================================



TEST TYPES:



&#x20;   Unit

&#x20;   Integration

&#x20;   Contract

&#x20;   Architecture

&#x20;   End-to-End

&#x20;   Simulation





================================================================================

77\. UNIT TESTS

================================================================================



Every Core / Domain component must have Unit Tests.





================================================================================

78\. INTEGRATION TESTS

================================================================================



Integration verifies:



&#x20;   Infrastructure

&#x20;   Application

&#x20;   Engines

&#x20;   Providers





================================================================================

79\. CONTRACT TESTS

================================================================================



Provider implementations must satisfy Provider Contracts.





================================================================================

80\. ARCHITECTURE TESTS

================================================================================



Architecture Tests enforce:



&#x20;   Dependency Rules

&#x20;   Module Boundaries

&#x20;   Forbidden Imports





================================================================================

81\. E2E TESTS

================================================================================



E2E should verify:



&#x20;   Application Startup

&#x20;   Data Flow

&#x20;   Prediction Flow

&#x20;   Trading Flow

&#x20;   Shutdown





================================================================================

82\. QUALITY GATE

================================================================================



MANDATORY:



&#x20;   python -m ruff check .

&#x20;   python -m black --check .

&#x20;   python -m mypy src

&#x20;   python -m pytest





No Phase is complete until all pass.





================================================================================

83\. FORMAT

================================================================================



Black is authoritative.





================================================================================

84\. TYPE CHECKING

================================================================================



Mypy is authoritative.



Production code should be strongly typed.





================================================================================

85\. GIT

================================================================================



Git is the source-control authority.





Workflow:



&#x20;   Implement

&#x20;      ↓

&#x20;   Test

&#x20;      ↓

&#x20;   Quality Gate

&#x20;      ↓

&#x20;   Commit





================================================================================

86\. COMMIT RULE

================================================================================



Commit should represent one logical change.





Example:



&#x20;   Implement Phase 28 Core Foundation



Do not mix:



&#x20;   unrelated refactoring

&#x20;   feature work

&#x20;   documentation

&#x20;   dependency changes



unless necessary.





================================================================================

87\. VERSIONING

================================================================================



Architecture Version:



&#x20;   1.0





Architecture changes require:



&#x20;   Architecture Change Record





Implementation phases do not automatically change Architecture Version.





================================================================================

88\. PHASE ROADMAP

================================================================================



PHASE 1

&#x20;   Architecture Principles



PHASE 2

&#x20;   Dependency Rules



PHASE 3

&#x20;   Domain Model



PHASE 4

&#x20;   Project Tree



PHASE 5

&#x20;   Framework Design



PHASE 6

&#x20;   Pipeline Design



PHASE 7

&#x20;   Engine Design



PHASE 8

&#x20;   Service Design



PHASE 9

&#x20;   Plugin Architecture



PHASE 10

&#x20;   Event Bus



PHASE 11

&#x20;   Data Platform



PHASE 12

&#x20;   Feature Platform



PHASE 13

&#x20;   AI Platform



PHASE 14

&#x20;   Trading Platform



PHASE 15

&#x20;   Portfolio Platform



PHASE 16

&#x20;   Simulation Platform



PHASE 17

&#x20;   Self Learning Platform



PHASE 18

&#x20;   Project Intelligence Platform



PHASE 19

&#x20;   GUI Architecture



PHASE 20

&#x20;   SQL Server Schema



PHASE 21

&#x20;   Configuration System



PHASE 22

&#x20;   Logging System



PHASE 23

&#x20;   Testing Architecture



PHASE 24

&#x20;   Deployment Architecture



PHASE 25

&#x20;   PowerShell Project Generator



PHASE 26

&#x20;   Architecture Validation / Integration



PHASE 27

&#x20;   Architecture → Implementation Contract



PHASE 28

&#x20;   Implementation Foundation



PHASE 29+

&#x20;   Platform Implementation





================================================================================

89\. PHASE 28 IMPLEMENTATION

================================================================================



Phase 28 establishes:



&#x20;   Core

&#x20;   Domain

&#x20;   Application

&#x20;   Infrastructure

&#x20;   DI

&#x20;   Configuration

&#x20;   Logging

&#x20;   Error

&#x20;   Result

&#x20;   Events

&#x20;   Lifecycle

&#x20;   Architecture Validation

&#x20;   Testing

&#x20;   Project Intelligence Foundation





================================================================================

90\. FUTURE IMPLEMENTATION ORDER

================================================================================



Recommended:



&#x20;   Phase 29

&#x20;       Data Platform



&#x20;   Phase 30

&#x20;       Feature Platform



&#x20;   Phase 31

&#x20;       AI Platform



&#x20;   Phase 32

&#x20;       Trading Platform



&#x20;   Phase 33

&#x20;       Portfolio Platform



&#x20;   Phase 34

&#x20;       Simulation Platform



&#x20;   Phase 35

&#x20;       Optimization Platform



&#x20;   Phase 36

&#x20;       Self Learning Platform



&#x20;   Phase 37

&#x20;       Project Intelligence Expansion



&#x20;   Phase 38

&#x20;       GUI



&#x20;   Phase 39

&#x20;       Agent Platform



&#x20;   Phase 40

&#x20;       Integration



&#x20;   Phase 41

&#x20;       Production Hardening



&#x20;   Phase 42

&#x20;       Deployment



&#x20;   Phase 43

&#x20;       Production Validation



&#x20;   Phase 44

&#x20;       V1.0 Release





These numbers are implementation roadmap identifiers.



They do NOT redefine the frozen Architecture.





================================================================================

91\. DATA FLOW

================================================================================



MARKET:



&#x20;   Provider

&#x20;      ↓

&#x20;   Data Engine

&#x20;      ↓

&#x20;   Validation

&#x20;      ↓

&#x20;   Storage

&#x20;      ↓

&#x20;   Feature Engine

&#x20;      ↓

&#x20;   AI Engine

&#x20;      ↓

&#x20;   Prediction

&#x20;      ↓

&#x20;   Signal

&#x20;      ↓

&#x20;   Risk

&#x20;      ↓

&#x20;   Decision

&#x20;      ↓

&#x20;   Execution

&#x20;      ↓

&#x20;   Portfolio





================================================================================

92\. AI FLOW

================================================================================



&#x20;   Dataset

&#x20;      ↓

&#x20;   Preprocessing

&#x20;      ↓

&#x20;   Features

&#x20;      ↓

&#x20;   Training

&#x20;      ↓

&#x20;   Evaluation

&#x20;      ↓

&#x20;   Registry

&#x20;      ↓

&#x20;   Inference

&#x20;      ↓

&#x20;   Prediction

&#x20;      ↓

&#x20;   Signal





================================================================================

93\. PROJECT INTELLIGENCE FLOW

================================================================================



&#x20;   Workspace

&#x20;      ↓

&#x20;   Scanner

&#x20;      ↓

&#x20;   Snapshot

&#x20;      ↓

&#x20;   Analysis

&#x20;      ↓

&#x20;   Context

&#x20;      ↓

&#x20;   Insight

&#x20;      ↓

&#x20;   Recommendation

&#x20;      ↓

&#x20;   Decision

&#x20;      ↓

&#x20;   Roadmap

&#x20;      ↓

&#x20;   Export

&#x20;      ↓

&#x20;   Project State





================================================================================

94\. COMPLETE SYSTEM GRAPH

================================================================================



&#x20;                          SHADBOT

&#x20;                             |

&#x20;         +-------------------+-------------------+

&#x20;         |                   |                   |

&#x20;        CORE              DOMAIN            INFRASTRUCTURE

&#x20;         |                   |                   |

&#x20;         +-------------------+-------------------+

&#x20;                             |

&#x20;                       APPLICATION

&#x20;                             |

&#x20;         +-------------------+-------------------+

&#x20;         |                   |                   |

&#x20;       EVENTS            SERVICES            PLUGINS

&#x20;                             |

&#x20;                          ENGINES

&#x20;                             |

&#x20;      +----------+-----------+-----------+---------+

&#x20;      |          |           |           |         |

&#x20;     DATA     FEATURE       AI       TRADING   PORTFOLIO

&#x20;      |          |           |           |         |

&#x20;      +----------+-----------+-----------+---------+

&#x20;                             |

&#x20;                       SIMULATION

&#x20;                             |

&#x20;                       OPTIMIZATION

&#x20;                             |

&#x20;                      SELF LEARNING

&#x20;                             |

&#x20;                 PROJECT INTELLIGENCE

&#x20;                             |

&#x20;                          AGENTS

&#x20;                             |

&#x20;                           GUI





================================================================================

95\. DEVELOPMENT LOOP

================================================================================



Every Feature:



&#x20;   Requirement

&#x20;      ↓

&#x20;   Architecture Check

&#x20;      ↓

&#x20;   Contract

&#x20;      ↓

&#x20;   Implementation

&#x20;      ↓

&#x20;   Unit Test

&#x20;      ↓

&#x20;   Integration Test

&#x20;      ↓

&#x20;   Architecture Test

&#x20;      ↓

&#x20;   Quality Gate

&#x20;      ↓

&#x20;   Project Intelligence Scan

&#x20;      ↓

&#x20;   Snapshot Update

&#x20;      ↓

&#x20;   Documentation Update

&#x20;      ↓

&#x20;   Git Commit





================================================================================

96\. REQUIREMENT TRACEABILITY

================================================================================



Every major requirement must map to:



&#x20;   Requirement ID

&#x20;      ↓

&#x20;   Architecture Component

&#x20;      ↓

&#x20;   Implementation

&#x20;      ↓

&#x20;   Test

&#x20;      ↓

&#x20;   Validation





Nothing important should exist only in Chat history.





================================================================================

97\. CHANGE MANAGEMENT

================================================================================



If developer wants to change Architecture:



&#x20;   STOP.



Create:



&#x20;   Architecture Change Proposal





Include:



&#x20;   Current Rule

&#x20;   Problem

&#x20;   Proposed Change

&#x20;   Impact

&#x20;   Dependencies

&#x20;   Migration

&#x20;   Risks

&#x20;   Tests





Only after approval:



&#x20;   Architecture Version changes.





================================================================================

98\. DATABASE

================================================================================



Primary future persistence target:



&#x20;   SQL Server





Database access must be isolated inside Infrastructure.





Domain must never import:



&#x20;   SQLAlchemy

&#x20;   pyodbc

&#x20;   pymssql

&#x20;   SQL Server SDK



directly.





================================================================================

99\. SERIALIZATION

================================================================================



Internal models should not depend on serialization format.



Adapters may provide:



&#x20;   JSON

&#x20;   YAML

&#x20;   CSV

&#x20;   Parquet

&#x20;   Database





================================================================================

100\. EXTERNAL API

================================================================================



External APIs must use:



&#x20;   Adapter / Gateway





Never:



&#x20;   Domain → HTTP





================================================================================

101\. TIME

================================================================================



Time should be abstractable for tests.



Production:



&#x20;   Real Clock





Tests:



&#x20;   Fake Clock





================================================================================

102\. FILESYSTEM

================================================================================



Filesystem operations must be isolated.



Never scatter:



&#x20;   open()

&#x20;   pathlib

&#x20;   shutil



through Domain logic.





================================================================================

103\. CONCURRENCY

================================================================================



Concurrency must be introduced only where required.



Default:



&#x20;   deterministic execution





Async must not be introduced merely for style.





================================================================================

104\. PERFORMANCE

================================================================================



Optimize only after:



&#x20;   Correctness

&#x20;   Testability

&#x20;   Architecture





are established.





================================================================================

105\. SECURITY

================================================================================



Never hard-code:



&#x20;   API Keys

&#x20;   Passwords

&#x20;   Tokens

&#x20;   Secrets





Never commit:



&#x20;   .env





================================================================================

106\. DATA SECURITY

================================================================================



Sensitive data must not appear in:



&#x20;   Logs

&#x20;   Git

&#x20;   Generated Context





================================================================================

107\. OBSERVABILITY

================================================================================



Every important subsystem should eventually expose:



&#x20;   Health

&#x20;   Metrics

&#x20;   Logs

&#x20;   Diagnostics





================================================================================

108\. RECOVERY

================================================================================



Where applicable:



&#x20;   Retry

&#x20;   Timeout

&#x20;   Circuit Breaker

&#x20;   Recovery





must be implemented at Infrastructure / Application level.





================================================================================

109\. IDEMPOTENCY

================================================================================



Operations such as:



&#x20;   Initialization

&#x20;   Snapshot Generation

&#x20;   Export

&#x20;   Migration





should be idempotent where possible.





================================================================================

110\. REPRODUCIBILITY

================================================================================



AI and Trading experiments must record:



&#x20;   Code Version

&#x20;   Dataset Version

&#x20;   Configuration

&#x20;   Model Version

&#x20;   Parameters

&#x20;   Random Seed

&#x20;   Metrics





================================================================================

111\. LIVE TRADING PROTECTION

================================================================================



NO LIVE TRADING BY DEFAULT.



Required:



&#x20;   Explicit Environment

&#x20;   Explicit Configuration

&#x20;   Explicit Broker

&#x20;   Explicit User Activation





================================================================================

112\. PROJECT SELF-AWARENESS

================================================================================



ShadBot should eventually be capable of answering:



&#x20;   What am I?

&#x20;   What modules do I have?

&#x20;   What version am I?

&#x20;   What changed?

&#x20;   What is broken?

&#x20;   What is incomplete?

&#x20;   What should be implemented next?

&#x20;   Which architecture rule is violated?

&#x20;   Which tests fail?





This is the purpose of Project Intelligence.





================================================================================

113\. SELF-DOCUMENTATION

================================================================================



Project Intelligence should automatically generate:



&#x20;   Architecture.md

&#x20;   Roadmap.md

&#x20;   Decisions.md

&#x20;   Todo.md

&#x20;   Statistics.json

&#x20;   DependencyGraph.json

&#x20;   ProjectSnapshot.json

&#x20;   ChatGPT\_Context.md





================================================================================

114\. CHAT HANDOFF

================================================================================



At any point a new Chat can be started.



User should provide:



&#x20;   project\_state/generated/ChatGPT\_Context.md





Optionally:



&#x20;   Architecture.md

&#x20;   Roadmap.md

&#x20;   Decisions.md

&#x20;   Todo.md

&#x20;   ProjectSnapshot.json





The new Agent must reconstruct the project state from these artifacts.





================================================================================

115\. CHAT HANDOFF RULE

================================================================================



New Agent MUST NOT:



&#x20;   redesign architecture

&#x20;   restart from Phase 1

&#x20;   assume implementation status

&#x20;   invent files

&#x20;   invent completed features





Agent must inspect:



&#x20;   Current Project State

&#x20;   Git

&#x20;   Source Tree

&#x20;   Tests





Then continue from:



&#x20;   CURRENT\_PHASE





================================================================================

116\. CURRENT IMPLEMENTATION BASELINE

================================================================================



At the beginning of implementation:



&#x20;   Git Repository:

&#x20;       initialized



&#x20;   Main Branch:

&#x20;       architecture-v1 work is being implemented



&#x20;   Core Foundation:

&#x20;       implemented



&#x20;   Domain Foundation:

&#x20;       implemented



&#x20;   Application Runtime:

&#x20;       implemented



&#x20;   Project Intelligence:

&#x20;       scaffolded and under active implementation





Known existing commits include:



&#x20;   Initial commit

&#x20;   Implement ShadBot Core Foundation

&#x20;   Implement ShadBot Domain Core

&#x20;   Implement application runtime layer





Do not assume these commits represent the final implementation state.



Always inspect Git and filesystem.





================================================================================

117\. CURRENT SOURCE BASELINE

================================================================================



Existing important files include:



&#x20;   src/ShadBot/core/dependency/container.py

&#x20;   src/ShadBot/core/events/event.py

&#x20;   src/ShadBot/core/events/eventBus.py

&#x20;   src/ShadBot/core/lifecycle/lifecycleManager.py

&#x20;   src/ShadBot/core/plugins/plugin.py

&#x20;   src/ShadBot/core/services/baseService.py



&#x20;   src/ShadBot/application/app.py

&#x20;   src/ShadBot/application/applicationState.py

&#x20;   src/ShadBot/application/bootstrap.py

&#x20;   src/ShadBot/application/runtime.py

&#x20;   src/ShadBot/application/serviceRegistry.py

&#x20;   src/ShadBot/application/startup.py

&#x20;   src/ShadBot/application/shutdown.py



&#x20;   src/ShadBot/domain/common/entity.py

&#x20;   src/ShadBot/domain/common/valueObject.py

&#x20;   src/ShadBot/domain/market/candle.py

&#x20;   src/ShadBot/domain/market/symbol.py

&#x20;   src/ShadBot/domain/market/timefram.py

&#x20;   src/ShadBot/domain/portfolio/account.py

&#x20;   src/ShadBot/domain/portfolio/balance.py

&#x20;   src/ShadBot/domain/prediction/prediction.py

&#x20;   src/ShadBot/domain/prediction/signal.py

&#x20;   src/ShadBot/domain/risk/riskModel.py

&#x20;   src/ShadBot/domain/trading/oerder.py

&#x20;   src/ShadBot/domain/trading/position.py

&#x20;   src/ShadBot/domain/trading/trade.py





================================================================================

118\. CURRENT PROJECT INTELLIGENCE BASELINE

================================================================================



Existing structure:



&#x20;   src/ShadBot/project/



&#x20;       core/

&#x20;           projectScanner.py

&#x20;           astScanner.py

&#x20;           gitScanner.py

&#x20;           configScanner.py

&#x20;           dependencyScanner.py

&#x20;           packageScanner.py

&#x20;           statisticsScanner.py

&#x20;           roadmapScanner.py

&#x20;           decisionScanner.py

&#x20;           todoScanner.py



&#x20;       models/

&#x20;           projectSnapshot.py

&#x20;           projectStatistics.py

&#x20;           projectContext.py

&#x20;           roadmap.py

&#x20;           decision.py



&#x20;       builders/

&#x20;           snapshotBuilder.py

&#x20;           contextBuilder.py

&#x20;           roadmapBuilder.py

&#x20;           statisticsBuilder.py

&#x20;           documentationBuilder.py



&#x20;       exporters/

&#x20;           markdownExporter.py

&#x20;           jsonExporter.py

&#x20;           htmlExporter.py

&#x20;           pdfExporter.py



&#x20;       runtime/

&#x20;           intelligenceRuntime.py





================================================================================

119\. IMPORTANT IMPLEMENTATION NOTE

================================================================================



وجود فایل به معنی:



&#x20;   IMPLEMENTED



نیست.



هر Agent باید وضعیت واقعی فایل را بررسی کند.



Possible statuses:



&#x20;   EMPTY

&#x20;   SCAFFOLDED

&#x20;   PARTIAL

&#x20;   IMPLEMENTED

&#x20;   TESTED

&#x20;   VALIDATED





================================================================================

120\. FIRST ACTION FOR ANY NEW AGENT

================================================================================



قبل از هر تغییر:



&#x20;   1. Inspect Git Status

&#x20;   2. Inspect Git Log

&#x20;   3. Inspect Project Tree

&#x20;   4. Inspect Current Phase

&#x20;   5. Inspect Project State

&#x20;   6. Inspect Relevant Source Files

&#x20;   7. Inspect Tests

&#x20;   8. Run Quality Gate if appropriate





NEVER assume.





================================================================================

121\. SECOND ACTION

================================================================================



Determine:



&#x20;   CURRENT IMPLEMENTATION STATE





Then compare:



&#x20;   Architecture Contract

&#x20;       VS

&#x20;   Actual Implementation





================================================================================

122\. THIRD ACTION

================================================================================



Create implementation plan only for:



&#x20;   missing

&#x20;   incorrect

&#x20;   incomplete





Do not rewrite correct code.





================================================================================

123\. CODING STANDARD

================================================================================



Code must be:



&#x20;   readable

&#x20;   typed

&#x20;   deterministic

&#x20;   testable

&#x20;   modular

&#x20;   production-grade





Avoid:



&#x20;   clever abstractions

&#x20;   unnecessary generics

&#x20;   premature optimization

&#x20;   magic globals





================================================================================

124\. NAMING

================================================================================



Preferred Python naming:



&#x20;   snake\_case



Classes:



&#x20;   PascalCase



Constants:



&#x20;   UPPER\_SNAKE\_CASE





Existing legacy names may be migrated carefully.





================================================================================

125\. IMPORT POLICY

================================================================================



Prefer:



&#x20;   absolute imports





Avoid:



&#x20;   circular imports





Architecture tests must detect violations.





================================================================================

126\. FILE SIZE

================================================================================



Do not create giant files.



If a module becomes too large:



&#x20;   extract cohesive responsibility.





================================================================================

127\. SINGLE RESPONSIBILITY

================================================================================



Each:



&#x20;   Class

&#x20;   Module

&#x20;   Service

&#x20;   Engine



must have clear responsibility.





================================================================================

128\. NO GOD OBJECT

================================================================================



Forbidden:



&#x20;   UniversalManager

&#x20;   MegaService

&#x20;   GodEngine

&#x20;   EverythingController





================================================================================

129\. NO GLOBAL STATE

================================================================================



Avoid:



&#x20;   global mutable singleton state





Use:



&#x20;   Dependency Injection

&#x20;   Application Lifecycle





================================================================================

130\. TESTABILITY

================================================================================



Any external dependency must be injectable.





================================================================================

131\. DOCUMENTATION STANDARD

================================================================================



Public classes and services should document:



&#x20;   Responsibility

&#x20;   Inputs

&#x20;   Outputs

&#x20;   Errors

&#x20;   Lifecycle





================================================================================

132\. FINAL QUALITY GATE

================================================================================



Before declaring ANY Phase complete:



&#x20;   python -m ruff check .

&#x20;   python -m black --check .

&#x20;   python -m mypy src

&#x20;   python -m pytest





Expected:



&#x20;   ALL GREEN





================================================================================

133\. PHASE COMPLETION

================================================================================



Phase is complete only when:



&#x20;   Implementation

&#x20;   Tests

&#x20;   Architecture Validation

&#x20;   Documentation

&#x20;   Project State

&#x20;   Git





are consistent.





================================================================================

134\. GIT CLEAN STATE

================================================================================



Before Phase completion:



&#x20;   git status





must be:



&#x20;   clean





unless explicitly documented.





================================================================================

135\. PROJECT STATE UPDATE

================================================================================



After successful Phase:



&#x20;   Scan Project

&#x20;      ↓

&#x20;   Generate Snapshot

&#x20;      ↓

&#x20;   Generate Context

&#x20;      ↓

&#x20;   Update Roadmap

&#x20;      ↓

&#x20;   Update Todo

&#x20;      ↓

&#x20;   Update Decisions

&#x20;      ↓

&#x20;   Commit





================================================================================

136\. FINAL PROJECT DELIVERY

================================================================================



Final ShadBot must provide:



&#x20;   Market Data

&#x20;   Feature Engineering

&#x20;   AI

&#x20;   Prediction

&#x20;   Trading

&#x20;   Risk

&#x20;   Portfolio

&#x20;   Backtesting

&#x20;   Simulation

&#x20;   Optimization

&#x20;   Self Learning

&#x20;   Project Intelligence

&#x20;   GUI

&#x20;   Agent Platform

&#x20;   Production Deployment





================================================================================

137\. PRODUCTION REQUIREMENT

================================================================================



Production system must be:



&#x20;   tested

&#x20;   observable

&#x20;   recoverable

&#x20;   secure

&#x20;   configurable

&#x20;   reproducible

&#x20;   auditable

&#x20;   extensible





================================================================================

138\. FINAL ARCHITECTURE PRINCIPLE

================================================================================



The system must remain:



&#x20;   MODULAR

&#x20;   TESTABLE

&#x20;   EXTENSIBLE

&#x20;   DOMAIN-CENTRIC

&#x20;   PROVIDER-INDEPENDENT

&#x20;   OBSERVABLE

&#x20;   REPRODUCIBLE





================================================================================

139\. ABSOLUTE PROHIBITIONS

================================================================================



NEVER:



&#x20;   redesign architecture without approval

&#x20;   bypass Domain boundaries

&#x20;   access DB from Domain

&#x20;   access Broker from Domain

&#x20;   hard-code secrets

&#x20;   enable live trading by default

&#x20;   ignore failing tests

&#x20;   ignore mypy

&#x20;   ignore architecture violations

&#x20;   commit broken code

&#x20;   delete working modules without analysis

&#x20;   replace real implementation with placeholders

&#x20;   invent implementation status

&#x20;   claim tests pass without running them





================================================================================

140\. FINAL EXECUTION MODEL

================================================================================



FOR EVERY TASK:



&#x20;   READ CONTEXT

&#x20;        ↓

&#x20;   INSPECT WORKSPACE

&#x20;        ↓

&#x20;   UNDERSTAND ARCHITECTURE

&#x20;        ↓

&#x20;   IDENTIFY GAP

&#x20;        ↓

&#x20;   IMPLEMENT

&#x20;        ↓

&#x20;   TEST

&#x20;        ↓

&#x20;   FIX

&#x20;        ↓

&#x20;   QUALITY GATE

&#x20;        ↓

&#x20;   ARCHITECTURE VALIDATION

&#x20;        ↓

&#x20;   UPDATE PROJECT INTELLIGENCE

&#x20;        ↓

&#x20;   UPDATE DOCUMENTATION

&#x20;        ↓

&#x20;   COMMIT

&#x20;        ↓

&#x20;   REPORT





================================================================================

141\. AGENT REPORT FORMAT

================================================================================



After each task report:



&#x20;   TASK

&#x20;   FILES CREATED

&#x20;   FILES MODIFIED

&#x20;   ARCHITECTURE IMPACT

&#x20;   IMPLEMENTATION STATUS

&#x20;   TEST RESULTS

&#x20;   QUALITY GATE

&#x20;   GIT COMMIT

&#x20;   PROJECT STATE UPDATE

&#x20;   NEXT TASK





================================================================================

142\. ZERO-ASSUMPTION RULE

================================================================================



If the actual repository differs from this document:



&#x20;   Repository State is the source of truth for CURRENT IMPLEMENTATION.



Architecture Contract remains the source of truth for:



&#x20;   INTENDED ARCHITECTURE.





Therefore:



&#x20;   Repository

&#x20;       =

&#x20;   What exists



&#x20;   Architecture Handoff

&#x20;       =

&#x20;   What must exist



&#x20;   Project State

&#x20;       =

&#x20;   Current reconstructed state





================================================================================

143\. FINAL AUTHORITY ORDER

================================================================================



For Architecture:



&#x20;   Approved Architecture

&#x20;       >

&#x20;   ARCHITECTURE\_HANDOFF.md

&#x20;       >

&#x20;   Implementation





For Current Implementation:



&#x20;   Actual Repository

&#x20;       >

&#x20;   Git

&#x20;       >

&#x20;   Project State

&#x20;       >

&#x20;   Documentation





For Requirements:



&#x20;   Explicit Approved Requirement

&#x20;       >

&#x20;   Roadmap

&#x20;       >

&#x20;   Agent Assumption





================================================================================

144\. FINAL OBJECTIVE

================================================================================



هدف نهایی ShadBot ساخت یک Enterprise AI Trading Platform است که:



&#x20;   داده را دریافت کند،

&#x20;   داده را validate و normalize کند،

&#x20;   Feature تولید کند،

&#x20;   Modelهای AI را آموزش دهد،

&#x20;   Prediction تولید کند،

&#x20;   Signal تولید کند،

&#x20;   Risk را محاسبه کند،

&#x20;   Decision بگیرد،

&#x20;   Order ایجاد کند،

&#x20;   Order را اجرا کند،

&#x20;   Portfolio را مدیریت کند،

&#x20;   سیستم را در Simulation و Backtest آزمایش کند،

&#x20;   Strategy و Model را Optimize کند،

&#x20;   از نتایج خود Learning انجام دهد،

&#x20;   وضعیت خودش را بفهمد،

&#x20;   Architecture خودش را بررسی کند،

&#x20;   وضعیت پروژه را Snapshot کند،

&#x20;   Context قابل انتقال تولید کند،

&#x20;   و در آینده بتواند با Agentهای Autonomous خودش توسعه پیدا کند.





================================================================================

145\. FINAL SYSTEM LOOP

================================================================================



&#x20;                        MARKET

&#x20;                          |

&#x20;                          v

&#x20;                        DATA

&#x20;                          |

&#x20;                          v

&#x20;                       FEATURES

&#x20;                          |

&#x20;                          v

&#x20;                          AI

&#x20;                          |

&#x20;                          v

&#x20;                      PREDICTION

&#x20;                          |

&#x20;                          v

&#x20;                        SIGNAL

&#x20;                          |

&#x20;                          v

&#x20;                         RISK

&#x20;                          |

&#x20;                          v

&#x20;                      DECISION

&#x20;                          |

&#x20;                          v

&#x20;                        ORDER

&#x20;                          |

&#x20;                          v

&#x20;                     EXECUTION

&#x20;                          |

&#x20;                          v

&#x20;                      POSITION

&#x20;                          |

&#x20;                          v

&#x20;                      PORTFOLIO

&#x20;                          |

&#x20;                          v

&#x20;                      OUTCOME

&#x20;                          |

&#x20;                          v

&#x20;                   SELF LEARNING

&#x20;                          |

&#x20;                          v

&#x20;                   MODEL IMPROVEMENT

&#x20;                          |

&#x20;                          +------------------+

&#x20;                                             |

&#x20;                                             v

&#x20;                                          FUTURE





================================================================================

146\. SELF-AWARE DEVELOPMENT LOOP

================================================================================



&#x20;                      SOURCE CODE

&#x20;                          |

&#x20;                          v

&#x20;                   PROJECT INTELLIGENCE

&#x20;                          |

&#x20;                          v

&#x20;                      SNAPSHOT

&#x20;                          |

&#x20;                          v

&#x20;                      ANALYSIS

&#x20;                          |

&#x20;                          v

&#x20;                       INSIGHT

&#x20;                          |

&#x20;                          v

&#x20;                   RECOMMENDATION

&#x20;                          |

&#x20;                          v

&#x20;                       DECISION

&#x20;                          |

&#x20;                          v

&#x20;                       ROADMAP

&#x20;                          |

&#x20;                          v

&#x20;                        AGENT

&#x20;                          |

&#x20;                          v

&#x20;                      CODE CHANGE

&#x20;                          |

&#x20;                          +---------------------> SOURCE CODE





================================================================================

147\. FINAL DEFINITION

================================================================================



ShadBot is NOT merely:



&#x20;   Trading Bot



ShadBot is:



&#x20;   Enterprise AI Trading Platform

&#x20;   +

&#x20;   Simulation Platform

&#x20;   +

&#x20;   Machine Learning Platform

&#x20;   +

&#x20;   Project Intelligence Platform

&#x20;   +

&#x20;   Autonomous Engineering Platform





================================================================================

148\. END STATE

================================================================================



ARCHITECTURE:



&#x20;   FROZEN



IMPLEMENTATION:



&#x20;   COMPLETE



TESTS:



&#x20;   GREEN



QUALITY:



&#x20;   VALIDATED



PROJECT INTELLIGENCE:



&#x20;   SELF-AWARE



AGENT PLATFORM:



&#x20;   OPERATIONAL



TRADING:



&#x20;   SAFE



DEPLOYMENT:



&#x20;   PRODUCTION READY





================================================================================

END OF ARCHITECTURE HANDOFF

================================================================================

