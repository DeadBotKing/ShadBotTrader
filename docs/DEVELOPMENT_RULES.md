\# SHADBOTTRADER — DEVELOPMENT RULES



Version: 1.0

Status: AUTHORITATIVE

Project: ShadBotTrader

Platform: Enterprise AI Trading Platform

Architecture: Clean Architecture + Domain-Driven Design + Modular Enterprise Architecture

Language: Python

Primary Runtime: Python 3.x

Repository: Git

Quality Standard: Enterprise / Production Grade



===============================================================================

0\. PURPOSE

===============================================================================



این سند قوانین قطعی توسعه ShadBotTrader است.



هر Developer، AI Agent، Coding Agent، Engineer یا Automation System که روی

ShadBotTrader کار می‌کند باید این قوانین را رعایت کند.



این سند فقط پیشنهاد نیست.



این سند Development Contract پروژه است.



هیچ کدی نباید صرفاً به دلیل اینکه "کار می‌کند" وارد پروژه شود.



کد باید:



\- از معماری پیروی کند.

\- از Dependency Rules پیروی کند.

\- قابل تست باشد.

\- قابل نگهداری باشد.

\- قابل توسعه باشد.

\- قابل مشاهده و قابل دیباگ باشد.

\- از Domain Logic محافظت کند.

\- با سیستم‌های آینده پروژه سازگار باشد.

\- با تصمیمات معماری قبلی تناقض نداشته باشد.



===============================================================================

1\. GOLDEN RULE

===============================================================================



اصل شماره یک:



DO NOT REDESIGN THE ARCHITECTURE WITHOUT EXPLICIT AUTHORIZATION.



Developer نباید:



\- معماری را ساده کند.

\- لایه‌ها را حذف کند.

\- Domain را با Infrastructure ترکیب کند.

\- Business Logic را داخل UI قرار دهد.

\- Business Logic را داخل Database قرار دهد.

\- AI Logic را مستقیماً داخل Trading Execution قرار دهد.

\- Pluginها را مستقیماً به Core متصل کند.

\- Dependency Injection را حذف کند.

\- Event Bus را با direct coupling جایگزین کند.

\- Engineها را مستقیماً به یکدیگر متصل کند.

\- برای "سریع‌تر شدن توسعه" boundaryها را بشکند.



اگر طراحی موجود مشکل دارد:



1\. مشکل را شناسایی کن.

2\. Impact را بررسی کن.

3\. راه‌حل را پیشنهاد بده.

4\. بدون تأیید معماری را تغییر نده.



===============================================================================

2\. PROJECT MISSION

===============================================================================



ShadBotTrader یک Enterprise AI Trading Platform است.



هدف پروژه ایجاد یک سیستم modular، autonomous، intelligent و extensible برای:



\- دریافت Market Data

\- ذخیره‌سازی Data

\- پردازش Data

\- Feature Engineering

\- AI/ML

\- Prediction

\- Signal Generation

\- Risk Management

\- Decision Making

\- Trading

\- Portfolio Management

\- Backtesting

\- Simulation

\- Replay

\- Optimization

\- Self Learning

\- Project Intelligence

\- GUI

\- Monitoring

\- Logging

\- Configuration

\- Plugin Management

\- Event-driven orchestration



است.



سیستم باید بتواند در آینده بدون بازنویسی هسته:



\- Provider جدید اضافه کند.

\- Broker جدید اضافه کند.

\- Exchange جدید اضافه کند.

\- Model جدید اضافه کند.

\- Strategy جدید اضافه کند.

\- Dataset جدید اضافه کند.

\- Feature جدید اضافه کند.

\- AI Agent جدید اضافه کند.

\- GUI جدید اضافه کند.

\- Storage جدید اضافه کند.



===============================================================================

3\. ARCHITECTURAL FOUNDATION

===============================================================================



معماری اصلی پروژه بر پایه موارد زیر است:



\- Clean Architecture

\- Domain-Driven Design

\- Dependency Inversion

\- Separation of Concerns

\- Modular Architecture

\- Event-Driven Architecture

\- Plugin Architecture

\- Dependency Injection

\- Pipeline Architecture

\- Engine-Based Architecture



Architecture باید به صورت Layered + Modular + Event Driven پیاده‌سازی شود.



===============================================================================

4\. ARCHITECTURE PHASES

===============================================================================



ShadBotTrader دارای roadmap معماری 28 مرحله‌ای است.



Phase 1

Architecture Principles



Phase 2

Dependency Rules



Phase 3

Domain Model



Phase 4

Project Tree



Phase 5

Framework Design



Phase 6

Pipeline Design



Phase 7

Engine Design



Phase 8

Service Design



Phase 9

Plugin Architecture



Phase 10

Event Bus



Phase 11

Data Platform



Phase 12

Feature Platform



Phase 13

AI Platform



Phase 14

Trading Platform



Phase 15

Portfolio Platform



Phase 16

Simulation Platform



Phase 17

Self Learning Platform



Phase 18

Project Intelligence Platform



Phase 19

GUI Architecture



Phase 20

SQL Server Schema



Phase 21

Configuration System



Phase 22

Logging System



Phase 23

Testing Architecture



Phase 24

Deployment Architecture



Phase 25

PowerShell Project Generator



Phase 26

Freeze v1.0



Phase 27

Enterprise Integration / Final Architecture Completion



Phase 28

Implementation / Runtime Foundation



Phase 28.x

Implementation sub-phases for turning the frozen architecture into executable

production-grade code.



Important:



Phase 1-27 define the architectural contract.



Phase 28 implements that contract.



Developer must not treat Phase 28 as permission to redesign Phases 1-27.



===============================================================================

5\. PLANNED IMPLEMENTATION STRUCTURE (NOT YET IMPLEMENTED)

===============================================================================



The repository currently contains only architecture documentation

(docs/) and legacy reference code. No new-platform implementation

exists yet.



The following structure is the PLANNED target for Phase 28 (not yet

implemented):



Core Foundation:



src/ShadBotTrader/core/

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



Application Runtime:



src/ShadBotTrader/application/

&#x20;   app.py

&#x20;   applicationState.py

&#x20;   bootstrap.py

&#x20;   runtime.py

&#x20;   serviceRegistry.py

&#x20;   shutdown.py

&#x20;   startup.py



Domain Core:



src/ShadBotTrader/domain/

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



Project Intelligence foundation:



src/ShadBotTrader/project/



&#x20;   core/

&#x20;       projectScanner.py

&#x20;       astScanner.py

&#x20;       gitScanner.py

&#x20;       configScanner.py

&#x20;       dependencyScanner.py

&#x20;       packageScanner.py

&#x20;       statisticsScanner.py

&#x20;       roadmapScanner.py

&#x20;       decisionScanner.py

&#x20;       todoScanner.py



&#x20;   models/

&#x20;       projectSnapshot.py

&#x20;       projectStatistics.py

&#x20;       projectContext.py

&#x20;       roadmap.py

&#x20;       decision.py



&#x20;   builders/

&#x20;       snapshotBuilder.py

&#x20;       contextBuilder.py

&#x20;       roadmapBuilder.py

&#x20;       statisticsBuilder.py

&#x20;       documentationBuilder.py



&#x20;   exporters/

&#x20;       markdownExporter.py

&#x20;       jsonExporter.py

&#x20;       htmlExporter.py

&#x20;       pdfExporter.py



&#x20;   runtime/

&#x20;       intelligenceRuntime.py



Project state:



project\_state/

&#x20;   generated/

&#x20;       ProjectSnapshot.md

&#x20;       ProjectSnapshot.json

&#x20;       ChatGPT\_Context.md

&#x20;       Architecture.md

&#x20;       Roadmap.md

&#x20;       Decisions.md

&#x20;       Todo.md

&#x20;       Statistics.json

&#x20;       DependencyGraph.json



&#x20;   archive/



IMPORTANT:



این ساختار هنوز پیاده‌سازی نشده است و هیچ یک از این فایل‌ها

وجود ندارد.



Empty file ≠ implemented feature.



Scaffold ≠ implementation.



Placeholder ≠ production code.Empty file ≠ implemented feature.



Scaffold ≠ implementation.



Placeholder ≠ production code.



===============================================================================

6\. PACKAGE NAMING RULE

===============================================================================



Python package باید consistently با ساختار پروژه استفاده شود.



Canonical package:



ShadBotTrader



از ایجاد packageهای موازی مانند:



shadbottrader

projectintelligence

tradingbot

core2

new\_core



بدون تصمیم معماری ممنوع است.



Case sensitivity و naming باید consistent باشد.



===============================================================================

7\. CLEAN ARCHITECTURE RULES

===============================================================================



Dependency direction باید به سمت داخل باشد.



Domain:



&#x20;   Domain

&#x20;      ↑

Application

&#x20;      ↑

Infrastructure / Presentation



Domain نباید به:



\- Database

\- HTTP

\- FastAPI

\- Django

\- SQLAlchemy

\- TensorFlow

\- PyTorch

\- Broker SDK

\- Exchange SDK

\- File System

\- GUI



وابسته باشد.



Domain باید framework independent باشد.



===============================================================================

8\. DOMAIN LAYER RULES

===============================================================================



Domain شامل Business Concepts است.



Domain باید شامل:



\- Entity

\- Value Object

\- Aggregate

\- Domain Service

\- Domain Event

\- Domain Rule

\- Domain Exception



باشد.



Domain نباید شامل:



\- API client

\- SQL query

\- filesystem access

\- HTTP request

\- logging implementation

\- configuration loading

\- model loading

\- GUI code



باشد.



===============================================================================

9\. ENTITY RULES

===============================================================================



Entity دارای identity است.



Entity باید:



\- identity مشخص داشته باشد.

\- invariantهای خودش را حفظ کند.

\- behavior داشته باشد.

\- mutable بودن آن فقط در صورت نیاز business مجاز است.



Entity نباید صرفاً یک data container بی‌منطق باشد.



===============================================================================

10\. VALUE OBJECT RULES

===============================================================================



Value Object:



\- identity مستقل ندارد.

\- بر اساس value مقایسه می‌شود.

\- immutable ترجیحاً باشد.

\- validation داخلی داشته باشد.



نمونه:



Symbol

TimeFrame

Money

Price

Quantity

Percentage



Business validation نباید در controller انجام شود.



===============================================================================

11\. AGGREGATE RULES

===============================================================================



Aggregate باید boundary مشخص داشته باشد.



External code نباید مستقیماً internal state aggregate را mutate کند.



Aggregate Root مسئول:



\- invariant

\- state transition

\- business consistency



است.



===============================================================================

12\. APPLICATION LAYER

===============================================================================



Application مسئول orchestration است.



Application باید:



\- Use Caseها را اجرا کند.

\- Domain را orchestrate کند.

\- Serviceها را هماهنگ کند.

\- transaction boundary را مدیریت کند.

\- event publishing را orchestrate کند.

\- dependencyها را از abstraction دریافت کند.



Application نباید Business Rule اصلی را duplicate کند.



===============================================================================

13\. APPLICATION SERVICE RULE

===============================================================================



Application Service باید:



1\. Request دریافت کند.

2\. dependencyهای لازم را دریافت کند.

3\. domain operation را اجرا کند.

4\. نتیجه را تولید کند.

5\. event / side effect را orchestrate کند.



Application Service نباید:



\- SQL مستقیم بنویسد.

\- HTTP client مستقیم بسازد.

\- singleton global بسازد.

\- model را hard-code کند.



===============================================================================

14\. CORE LAYER

===============================================================================



Core شامل primitiveهای معماری سیستم است.



Core باید تا حد ممکن:



\- کوچک

\- پایدار

\- مستقل

\- reusable



باشد.



Core شامل foundationهایی مانند:



\- Dependency Container

\- Event

\- Event Bus

\- Lifecycle

\- Plugin abstraction

\- Base Service



است.



Core نباید به Domainهای خاص Trading وابسته شود.



===============================================================================

15\. DEPENDENCY INJECTION

===============================================================================



Dependency Injection اجباری است.



Bad:



service = Service(Database())



Good:



service = Service(database)



Composition Root مسئول ساخت dependencyها است.



Service نباید dependencyهای خودش را instantiate کند.



===============================================================================

16\. SERVICE LOCATOR

===============================================================================



Service Locator نباید جایگزین Dependency Injection شود.



Registry صرفاً برای:



\- registration

\- lookup

\- lifecycle management



است.



Business code نباید به global registry وابسته شود.



===============================================================================

17\. ENGINE RULES

===============================================================================



Engineها subsystem-level components هستند.



Engineهای اصلی معماری:



\- AIEngine

\- ContextEngine

\- DataEngine

\- DecisionEngine

\- ExecutionEngine

\- FeatureEngineeringEngine

\- GuiEngine

\- IntelligenceEngine

\- MarketEngine

\- NewsEngine

\- OptimizationEngine

\- PortfolioEngine

\- SimulationEngine

\- StorageEngine



Engine نباید business domain را مالک شود.



Engine باید orchestration / execution responsibility داشته باشد.



===============================================================================

18\. ENGINE COUPLING RULE

===============================================================================



Engine A نباید به implementation داخلی Engine B وابسته شود.



به جای:



EngineA -> EngineBImplementation



استفاده شود از:



EngineA -> Interface / Contract

&#x20;            ↑

&#x20;       EngineB Adapter



برای communication پیچیده از Event Bus استفاده شود.



===============================================================================

19\. PIPELINE RULES

===============================================================================



Pipeline باید deterministic و قابل مشاهده باشد.



Pipeline stage باید:



\- input مشخص

\- output مشخص

\- error behavior مشخص

\- lifecycle مشخص

\- observability مشخص



داشته باشد.



Pipeline نباید stageهای implicit داشته باشد.



هر stage باید مسئولیت مشخص داشته باشد.



===============================================================================

20\. PIPELINE EXECUTION

===============================================================================



Pipelineهای اصلی می‌توانند شامل:



Data Pipeline

Feature Pipeline

AI Pipeline

Prediction Pipeline

Decision Pipeline

Trading Pipeline

Backtesting Pipeline

Simulation Pipeline

Project Intelligence Pipeline



باشند.



Pipeline باید قابل:



\- start

\- stop

\- pause

\- resume

\- retry

\- inspect



باشد، در صورت نیاز به domain آن.



===============================================================================

21\. EVENT BUS

===============================================================================



Event Bus برای decoupled communication استفاده می‌شود.



Event باید:



\- immutable ترجیحاً باشد.

\- event type مشخص داشته باشد.

\- timestamp داشته باشد.

\- metadata داشته باشد.

\- correlation ID داشته باشد.

\- causation ID در صورت نیاز داشته باشد.



Event handler نباید state global ایجاد کند.



===============================================================================

22\. EVENT NAMING

===============================================================================



Eventها باید past-tense باشند.



نمونه:



MarketDataReceived

CandleClosed

PredictionGenerated

SignalGenerated

TradeExecuted

PositionOpened

PositionClosed

RiskLimitBreached



نام event باید نشان دهد چه اتفاقی افتاده است.



===============================================================================

23\. COMMAND VS EVENT

===============================================================================



Command:



"کاری انجام بده."



Event:



"کاری انجام شد."



این دو نباید با هم قاطی شوند.



===============================================================================

24\. PLUGIN ARCHITECTURE

===============================================================================



هر قابلیت قابل تعویض باید در صورت امکان Plugin-based باشد.



Pluginها می‌توانند شامل:



\- Data Provider

\- Broker

\- Exchange

\- AI Model

\- Strategy

\- Feature Provider

\- News Provider

\- Storage Provider

\- Exporter



باشند.



Plugin باید:



\- lifecycle مشخص

\- metadata

\- configuration

\- capability declaration



داشته باشد.



Plugin نباید مستقیماً Core داخلی را manipulate کند.



===============================================================================

25\. DATA PLATFORM

===============================================================================



Data Platform مسئول:



\- ingestion

\- normalization

\- validation

\- storage

\- retrieval

\- update

\- versioning

\- quality



است.



Raw Data نباید بدون validation وارد processed layer شود.



===============================================================================

26\. DATA LAYERS

===============================================================================



حداقل مفهومی:



RAW

PROCESSED

FEATURES



باید از یکدیگر جدا باشند.



نمونه repository:



datasets/

&#x20;   Raw/

&#x20;   Processed/

&#x20;   Features/



نام‌گذاری واقعی باید consistent شود.



===============================================================================

27\. DATA INTEGRITY

===============================================================================



Data باید:



\- timestamp معتبر

\- symbol معتبر

\- timeframe معتبر

\- ordering مشخص

\- duplicate handling

\- missing data handling



داشته باشد.



Lookahead bias ممنوع است.



Data leakage ممنوع است.



===============================================================================

28\. FEATURE PLATFORM

===============================================================================



Feature Engineering باید:



\- deterministic

\- reproducible

\- versioned

\- testable



باشد.



Feature نباید از future information استفاده کند.



هر Feature باید metadata داشته باشد:



\- name

\- version

\- input

\- output

\- parameters

\- timeframe

\- dependencies



===============================================================================

29\. AI PLATFORM

===============================================================================



AI Platform باید Model lifecycle را مدیریت کند:



\- model registration

\- training

\- validation

\- evaluation

\- versioning

\- loading

\- inference

\- monitoring



Model نباید مستقیماً به Trading Execution متصل شود.



AI Prediction یک input برای Decision System است، نه دستور مستقیم معامله.



===============================================================================

30\. PREDICTION RULE

===============================================================================



Prediction:



&#x20;   Model -> Prediction



Signal:



&#x20;   Prediction + Context + Rules -> Signal



Decision:



&#x20;   Signal + Risk + Portfolio + Strategy -> Decision



Execution:



&#x20;   Approved Decision -> Execution



این chain نباید شکسته شود.



===============================================================================

31\. TRADING PLATFORM

===============================================================================



Trading باید separation زیر را حفظ کند:



Market Data

&#x20;   ↓

Feature

&#x20;   ↓

Prediction

&#x20;   ↓

Signal

&#x20;   ↓

Decision

&#x20;   ↓

Risk

&#x20;   ↓

Order

&#x20;   ↓

Execution

&#x20;   ↓

Trade

&#x20;   ↓

Position

&#x20;   ↓

Portfolio



AI نباید مستقیماً Order ارسال کند.



===============================================================================

32\. RISK MANAGEMENT

===============================================================================



Risk باید قبل از Execution بررسی شود.



Risk system باید بتواند:



\- position size

\- exposure

\- leverage

\- drawdown

\- daily loss

\- maximum risk

\- instrument limits

\- portfolio limits



را کنترل کند.



Risk rule باید قابل تست و deterministic باشد.



===============================================================================

33\. PORTFOLIO PLATFORM

===============================================================================



Portfolio مسئول:



\- account

\- balance

\- positions

\- exposure

\- PnL

\- allocation

\- performance



است.



Portfolio نباید مسئول data ingestion یا model training باشد.



===============================================================================

34\. SIMULATION PLATFORM

===============================================================================



Simulation باید بتواند trading system را بدون broker واقعی اجرا کند.



Simulation باید:



\- deterministic

\- reproducible

\- configurable



باشد.



Backtest نباید به production execution وابسته باشد.



===============================================================================

35\. BACKTESTING RULE

===============================================================================



Backtest باید از:



\- historical data

\- historical state

\- historical execution assumptions



استفاده کند.



Future data نباید وارد گذشته شود.



Lookahead bias باید تست شود.



Slippage و fees در صورت نیاز باید مدل شوند.



===============================================================================

36\. SELF LEARNING

===============================================================================



Self Learning نباید مستقیماً production strategy را تغییر دهد.



هر learning cycle باید:



1\. data

2\. training

3\. evaluation

4\. validation

5\. approval

6\. deployment



را طی کند.



هیچ model جدیدی نباید بدون validation وارد production شود.



===============================================================================

37\. PROJECT INTELLIGENCE

===============================================================================



Project Intelligence وظیفه دارد خود پروژه ShadBotTrader را بفهمد.



این subsystem باید بتواند:



\- workspace scan

\- source scan

\- AST analysis

\- dependency analysis

\- git analysis

\- configuration analysis

\- package analysis

\- statistics

\- roadmap

\- decisions

\- TODO

\- architecture



را استخراج کند.



Pipeline مفهومی:



Snapshot

&#x20;   ↓

Analysis

&#x20;   ↓

Evolution

&#x20;   ↓

Insight

&#x20;   ↓

Recommendation

&#x20;   ↓

Decision



===============================================================================

38\. PROJECT INTELLIGENCE MUST BE SELF-AWARE

===============================================================================



Project Intelligence نباید فقط یک documentation generator باشد.



باید بتواند وضعیت واقعی repository را با وضعیت مورد انتظار مقایسه کند.



مثلاً:



Expected:

&#x20;   Trading Engine exists



Actual:

&#x20;   Trading Engine missing



نتیجه:



Gap detected.



همچنین:



Expected:

&#x20;   X dependency



Actual:

&#x20;   X missing



باید گزارش شود.



===============================================================================

39\. PROJECT STATE

===============================================================================



Project state باید در:



project\_state/



نگهداری شود.



Generated artifacts باید قابل بازسازی باشند.



Generated state نباید منبع حقیقت business logic باشد.



Source code منبع حقیقت implementation است.



Architecture specification منبع حقیقت architecture است.



Git منبع حقیقت history است.



===============================================================================

40\. GENERATED FILES

===============================================================================



فایل‌های generated:



ProjectSnapshot.md

ProjectSnapshot.json

ChatGPT\_Context.md

Architecture.md

Roadmap.md

Decisions.md

Todo.md

Statistics.json

DependencyGraph.json



باید توسط runtime تولید شوند.



Developer نباید آنها را به صورت دستی به عنوان source of truth تغییر دهد.



===============================================================================

41\. CHATGPT CONTEXT

===============================================================================



ChatGPT\_Context.md باید خلاصه قابل حمل پروژه باشد.



باید شامل:



\- Project identity

\- Current architecture

\- Current phase

\- Completed phases

\- Current implementation

\- Active decisions

\- Pending work

\- Known issues

\- Roadmap

\- Repository statistics

\- Dependency graph

\- Important architectural constraints



باشد.



هدف:



وقتی یک Chat جدید باز شد، با ارسال این فایل، Agent بتواند context پروژه را

سریعاً بازیابی کند.



===============================================================================

42\. ARCHITECTURE DOCUMENTATION

===============================================================================



Architecture documentation باید architecture را توضیح دهد، نه implementation

تصادفی فعلی را.



اگر implementation با architecture conflict دارد:



Architecture Contract اولویت دارد.



Developer باید conflict را گزارش کند.



===============================================================================

43\. CONFIGURATION

===============================================================================



Configuration باید centralized و typed باشد.



Configuration نباید:



\- hard-coded

\- scattered

\- duplicated



باشد.



Secretها نباید داخل Git commit شوند.



نمونه:



API keys

Passwords

Tokens

Private credentials



نباید commit شوند.



===============================================================================

44\. ENVIRONMENT VARIABLES

===============================================================================



Environment-specific configuration باید از environment دریافت شود.



نمونه:



DATABASE\_URL

BROKER\_API\_KEY

BROKER\_API\_SECRET

MODEL\_PATH



نباید در source code hard-code شوند.



===============================================================================

45\. LOGGING

===============================================================================



Logging باید structured و centralized باشد.



حداقل levelها:



DEBUG

INFO

WARNING

ERROR

CRITICAL



استفاده از:



print()



برای production diagnostics ممنوع است.



===============================================================================

46\. ERROR HANDLING

===============================================================================



Exception handling باید explicit باشد.



Bad:



except Exception:

&#x20;   pass



ممنوع.



Error باید:



\- logged

\- classified

\- contextualized



باشد.



Domain Exception و Infrastructure Exception نباید بی‌دلیل یکی باشند.



===============================================================================

47\. RESULT HANDLING

===============================================================================



در جایی که مناسب است از Result abstraction استفاده شود.



Result باید بتواند:



Success

Failure



را نمایش دهد.



Exception نباید برای control flow معمولی استفاده شود.



===============================================================================

48\. TESTING

===============================================================================



هر production feature باید test داشته باشد.



حداقل:



Unit Test

Integration Test

در صورت نیاز:

End-to-End Test



===============================================================================

49\. TEST PYRAMID

===============================================================================



تعداد Unit Testها باید بیشتر از Integration Testها باشد.



ساختار:



&#x20;       E2E

&#x20;      /   \\

&#x20;Integration

&#x20;  /       \\

&#x20;Unit Tests



===============================================================================

50\. DOMAIN TESTS

===============================================================================



Domain testها باید بدون:



\- Database

\- Network

\- File system

\- external API



قابل اجرا باشند.



Domain logic باید سریع و deterministic تست شود.



===============================================================================

51\. QUALITY GATE

===============================================================================



قبل از هر commit مهم باید اجرا شود:



pytest

ruff

black

mypy



حداقل:



python -m pytest

python -m ruff check .

python -m black .

python -m mypy src



همه باید green باشند.



===============================================================================

52\. NO BROKEN BUILD

===============================================================================



Developer نباید پروژه را در وضعیت نیمه‌شکسته رها کند.



ممنوع:



\- import broken

\- syntax error

\- failing tests

\- unresolved type errors

\- missing dependency

\- dead module registration

\- broken bootstrap



===============================================================================

53\. TYPE SAFETY

===============================================================================



Type hints باید برای public APIها وجود داشته باشند.



مخصوصاً:



\- service

\- repository

\- engine

\- domain operation

\- pipeline

\- event

\- plugin

\- configuration



Mypy errors نباید نادیده گرفته شوند.



===============================================================================

54\. FORMATTING

===============================================================================



Black formatter استاندارد formatting است.



Ruff استاندارد linting است.



Developer نباید برای formatting دستی با tooling مبارزه کند.



===============================================================================

55\. NAMING

===============================================================================



نام‌گذاری باید:



\- واضح

\- semantic

\- consistent



باشد.



از نام‌هایی مانند:



x

tmp

data2

manager2

newService

helper

misc



برای production abstractionهای مهم استفاده نشود.



===============================================================================

56\. FILE NAMING

===============================================================================



نام فایل‌ها باید با convention پروژه consistent باشند.



بهتر است Python modules به صورت:



snake\_case.py



باشند.



اما اگر repository فعلی convention دیگری دارد، بدون تصمیم migration ناگهانی

rename گسترده انجام نشود.



Consistency مهم‌تر از preference شخصی است.



===============================================================================

57\. IMPORT RULES

===============================================================================



Importها باید:



\- explicit

\- stable

\- predictable



باشند.



Circular dependency ممنوع است.



اگر circular dependency ایجاد شد:



1\. dependency graph بررسی شود.

2\. abstraction استخراج شود.

3\. boundary اصلاح شود.



Import hack ممنوع است.



===============================================================================

58\. GLOBAL STATE

===============================================================================



Global mutable state ممنوع است.



Singleton فقط در موارد infrastructure/lifecycle که معماری صراحتاً نیاز دارد

مجاز است.



Business state نباید global باشد.



===============================================================================

59\. DATABASE RULES

===============================================================================



Domain نباید SQL بداند.



Repository abstraction در Application/Domain boundary تعریف شود.



Implementation repository در Infrastructure قرار گیرد.



Database schema باید versioned و migration-based باشد.



===============================================================================

60\. SQL SERVER

===============================================================================



SQL Server یکی از storage targets معماری است.



Database-specific implementation نباید وارد Domain شود.



ORM یا driver باید در Infrastructure encapsulate شود.



===============================================================================

61\. API RULES

===============================================================================



API layer فقط transport concern دارد.



Controller نباید:



\- business rule

\- model inference

\- risk calculation

\- trading logic



را مستقیماً انجام دهد.



Controller:



Request

&#x20;   ↓

Application Use Case

&#x20;   ↓

Domain

&#x20;   ↓

Result

&#x20;   ↓

Response



===============================================================================

62\. GUI RULES

===============================================================================



GUI نباید مستقیماً Domain internals را تغییر دهد.



GUI باید از Application API / ViewModel / Command layer استفاده کند.



===============================================================================

63\. AI AGENT RULES

===============================================================================



هر Agent باید دو capability اصلی داشته باشد:



BRAIN

&#x20;   reasoning / planning / decision capability



EYES

&#x20;   workspace observation / inspection capability



Agent بدون observation کامل نیست.



Agent نباید بر اساس حدس درباره repository کد بنویسد.



===============================================================================

64\. AGENT OBSERVATION

===============================================================================



Agent باید بتواند:



\- list files

\- inspect files

\- inspect directories

\- inspect git state

\- inspect configuration

\- inspect dependencies

\- inspect tests

\- inspect architecture

\- inspect project state



را انجام دهد.



README به تنهایی source of truth برای workspace نیست.



===============================================================================

65\. AGENT CODING

===============================================================================



Agent قبل از تغییر باید:



1\. Workspace را inspect کند.

2\. Architecture را بخواند.

3\. Relevant modules را بخواند.

4\. Dependency graph را بررسی کند.

5\. Tests را بررسی کند.

6\. Change plan بسازد.

7\. Implementation انجام دهد.

8\. Quality Gate اجرا کند.

9\. نتیجه را گزارش کند.



===============================================================================

66\. NO BLIND CODING

===============================================================================



Agent نباید:



\- فایل را بدون خواندن overwrite کند.

\- architecture را حدس بزند.

\- implementation را حدس بزند.

\- dependency را حدس بزند.

\- test را حدس بزند.



Blind coding ممنوع است.



===============================================================================

67\. NO PLACEHOLDER CODE

===============================================================================



کدهایی مانند:



pass

TODO

NotImplementedError



نباید برای قابلیت‌های مورد انتظار production استفاده شوند.



استثنا:



اگر abstraction عمداً implementation ندارد و قرارداد معماری آن را مجاز کرده

باشد.



اما حتی در این حالت باید دلیل مشخص باشد.



===============================================================================

68\. NO THROWAWAY IMPLEMENTATION

===============================================================================



کدی که قرار است "بعداً درستش کنیم" نباید به عنوان implementation اصلی وارد شود.



هر implementation باید از ابتدا:



\- maintainable

\- typed

\- testable

\- architecturally compliant



باشد.



===============================================================================

69\. DOCUMENTATION

===============================================================================



هر subsystem مهم باید documentation داشته باشد.



Documentation باید شامل:



\- Purpose

\- Responsibility

\- Dependencies

\- Inputs

\- Outputs

\- Lifecycle

\- Failure modes

\- Extension points



باشد.



===============================================================================

70\. DECISION RECORDING

===============================================================================



تصمیمات معماری مهم باید ثبت شوند.



نمونه:



\- چرا SQL Server؟

\- چرا Event Bus؟

\- چرا Plugin Architecture؟

\- چرا Dependency Injection؟

\- چرا مدل خاص؟

\- چرا Pipeline خاص؟



Decision باید قابل trace باشد.



===============================================================================

71\. GIT RULES

===============================================================================



Git بخشی از engineering workflow است.



هر تغییر منطقی باید commit مستقل یا logically grouped داشته باشد.



Commit باید semantic باشد.



نمونه:



Implement ShadBotTrader Core Foundation



Implement ShadBotTrader Domain Core



Implement application runtime layer



Bad:



changes

fix

test

update

stuff



===============================================================================

72\. COMMIT RULE

===============================================================================



قبل از commit:



1\. git status

2\. quality gate

3\. review diff

4\. git add

5\. commit



انجام شود.



===============================================================================

73\. BRANCHING

===============================================================================



Branchها باید بر اساس feature / architecture stage باشند.



نمونه:



main



یا:



feature/data-platform

feature/ai-platform

feature/trading-engine



Branch naming باید consistent باشد.



===============================================================================

74\. NO UNRELATED CHANGES

===============================================================================



هنگام پیاده‌سازی feature X نباید بدون دلیل:



\- rename گسترده

\- refactor unrelated

\- dependency migration

\- architecture change



انجام شود.



===============================================================================

75\. DEPENDENCY MANAGEMENT

===============================================================================



هر dependency جدید باید دلیل داشته باشد.



قبل از اضافه کردن package:



1\. آیا واقعاً لازم است؟

2\. آیا functionality داخلی قابل پیاده‌سازی است؟

3\. آیا package stable است؟

4\. آیا license مناسب است؟

5\. آیا maintenance مناسب دارد؟

6\. آیا با architecture conflict دارد؟



بررسی شود.



===============================================================================

76\. LIBRARY BOUNDARIES

===============================================================================



Third-party libraries باید در boundary مناسب قرار بگیرند.



مثلاً:



TensorFlow

PyTorch

Broker SDK

Database driver



نباید در Domain منتشر شوند.



===============================================================================

77\. PERFORMANCE

===============================================================================



Performance optimization فقط بعد از مشخص شدن bottleneck انجام شود.



Premature optimization ممنوع.



اما architecture باید از ابتدا قابلیت scale شدن داشته باشد.



===============================================================================

78\. CONCURRENCY

===============================================================================



Concurrency باید explicit باشد.



Thread

Process

Async

Task Queue



نباید بدون architecture decision مخلوط شوند.



State shared باید thread-safe یا isolated باشد.



===============================================================================

79\. ASYNC RULE

===============================================================================



اگر subsystem async است، باید تا boundary مشخص async بماند.



Async/sync mixing بدون دلیل ممنوع.



===============================================================================

80\. OBSERVABILITY

===============================================================================



Subsystemهای مهم باید قابل مشاهده باشند.



حداقل:



\- execution ID

\- correlation ID

\- timestamps

\- status

\- duration

\- error

\- result



در runtimeهای مهم باید قابل ثبت باشد.



===============================================================================

81\. LIFECYCLE

===============================================================================



Componentهای مهم باید lifecycle مشخص داشته باشند.



Typical:



CREATED

INITIALIZING

READY

RUNNING

STOPPING

STOPPED

FAILED



Lifecycle transition باید معتبر باشد.



===============================================================================

82\. STARTUP

===============================================================================



Application startup باید deterministic باشد.



ترتیب مفهومی:



Configuration

&#x20;   ↓

Logging

&#x20;   ↓

Dependency Container

&#x20;   ↓

Infrastructure

&#x20;   ↓

Services

&#x20;   ↓

Engines

&#x20;   ↓

Plugins

&#x20;   ↓

Application

&#x20;   ↓

Runtime



ترتیب واقعی باید با dependency graph منطبق باشد.



===============================================================================

83\. SHUTDOWN

===============================================================================



Shutdown باید graceful باشد.



ترتیب:



Stop intake

&#x20;   ↓

Stop pipelines

&#x20;   ↓

Flush state

&#x20;   ↓

Close services

&#x20;   ↓

Close infrastructure

&#x20;   ↓

Release resources



Crash shutdown نباید state را بی‌دلیل corrupt کند.



===============================================================================

84\. RESOURCE MANAGEMENT

===============================================================================



هر resource باید lifecycle داشته باشد.



مثلاً:



\- database connection

\- file

\- network connection

\- broker connection

\- model instance



Resource leak ممنوع.



===============================================================================

85\. SECURITY

===============================================================================



Secrets:



NEVER COMMIT.



Credentials:



NEVER HARDCODE.



Logs نباید secrets را چاپ کنند.



User input باید validate شود.



External input باید untrusted فرض شود.



===============================================================================

86\. TRADING SAFETY

===============================================================================



Production trading باید fail-safe باشد.



اگر:



\- model unavailable

\- data stale

\- risk unavailable

\- broker unavailable

\- configuration invalid

\- clock invalid

\- state inconsistent



باشد، سیستم نباید کورکورانه order ارسال کند.



Default باید safe failure باشد.



===============================================================================

87\. EXECUTION SAFETY

===============================================================================



Execution engine باید قبل از order:



\- decision validation

\- risk validation

\- account validation

\- market validation

\- quantity validation



را انجام دهد.



===============================================================================

88\. TIME

===============================================================================



Trading system باید timezone-aware باشد.



UTC باید canonical storage/reference time باشد، مگر architecture مشخصاً خلاف آن

را تعیین کند.



Naive datetime در بخش‌های حساس ممنوع.



===============================================================================

89\. MONEY

===============================================================================



Floating point نباید بدون دلیل برای monetary calculations استفاده شود.



برای monetary precision باید abstraction مناسب استفاده شود.



===============================================================================

90\. REPRODUCIBILITY

===============================================================================



AI training و backtesting باید تا حد ممکن reproducible باشند.



ثبت شود:



\- dataset version

\- feature version

\- model version

\- configuration

\- random seed

\- strategy version



===============================================================================

91\. VERSIONING

===============================================================================



قابلیت‌های مهم باید version داشته باشند.



مثلاً:



Model v1

FeatureSet v3

Strategy v2

Schema v4



Version باید قابل trace باشد.



===============================================================================

92\. MIGRATION

===============================================================================



Migration نباید breaking change پنهان داشته باشد.



قبل از migration:



\- impact

\- backward compatibility

\- data migration

\- rollback



بررسی شود.



===============================================================================

93\. BACKWARD COMPATIBILITY

===============================================================================



اگر API یا contract قبلی استفاده می‌شود، بدون دلیل شکسته نشود.



اگر breaking change لازم است:



1\. identify

2\. document

3\. migrate

4\. test



===============================================================================

94\. CONTRACTS

===============================================================================



Interfaceها باید stable باشند.



Contract شامل:



\- input

\- output

\- errors

\- lifecycle

\- invariants



است.



Implementation نباید contract را secretly تغییر دهد.



===============================================================================

95\. CODE REVIEW

===============================================================================



هر تغییر مهم باید از نظر:



Architecture

Correctness

Testing

Security

Performance

Maintainability



بررسی شود.



===============================================================================

96\. REFACTORING

===============================================================================



Refactoring باید behavior-preserving باشد مگر اینکه تغییر behavior هدف رسمی

باشد.



Refactoring نباید با feature development مخلوط شود مگر ضروری باشد.



===============================================================================

97\. DELETION

===============================================================================



قبل از حذف فایل/module:



\- search usages

\- inspect imports

\- inspect tests

\- inspect plugin registration

\- inspect configuration

\- inspect documentation



انجام شود.



===============================================================================

98\. DEAD CODE

===============================================================================



Dead code باید حذف شود، اما فقط پس از اثبات اینکه استفاده نمی‌شود.



===============================================================================

99\. CYCLIC DEPENDENCY

===============================================================================



Cyclic dependency architectural defect محسوب می‌شود.



راه‌حل:



\- abstraction

\- event

\- interface

\- dependency inversion

\- module extraction



نه import hack.



===============================================================================

100\. SOURCE OF TRUTH

===============================================================================



ترتیب Source of Truth:



1\. Architecture specification

2\. Explicit architectural decisions

3\. Domain contracts

4\. Current source code

5\. Tests

6\. Generated project state

7\. Documentation summaries



Generated files نباید architecture را override کنند.



===============================================================================

101\. PROJECT INTELLIGENCE UPDATE RULE

===============================================================================



پس از تغییر مهم در پروژه باید Project Intelligence بتواند state جدید را capture کند.



هدف:



Chat جدید بتواند فقط با دریافت:



ChatGPT\_Context.md



و در صورت نیاز:



Architecture.md

Roadmap.md

Decisions.md

Todo.md



دوباره project context را بازیابی کند.



===============================================================================

102\. AUTOMATIC PROJECT MEMORY

===============================================================================



Project Intelligence باید در آینده بتواند به صورت خودکار:



\- snapshot بگیرد.

\- تغییرات Git را تشخیص دهد.

\- architecture changes را تشخیص دهد.

\- roadmap را update کند.

\- TODO را update کند.

\- statistics را update کند.

\- dependency graph را update کند.

\- ChatGPT Context را regenerate کند.

\- نسخه قبلی state را archive کند.



===============================================================================

103\. STATE ARCHIVING

===============================================================================



قبل از overwrite کردن state مهم:



نسخه قبلی باید در:



project\_state/archive/



قابل نگهداری باشد.



هدف:



Historical project state



باید قابل بازیابی باشد.



===============================================================================

104\. PROJECT SNAPSHOT

===============================================================================



Snapshot باید حداقل شامل:



\- commit

\- branch

\- timestamp

\- Python version

\- package list

\- source files

\- file count

\- line count

\- modules

\- dependencies

\- architecture markers

\- tests

\- TODOs

\- decisions



باشد.



===============================================================================

105\. ROADMAP RULE

===============================================================================



Roadmap باید distinction زیر را حفظ کند:



COMPLETED

IN PROGRESS

PLANNED

BLOCKED

DEFERRED



Developer نباید feature ناقص را COMPLETED علامت بزند.



===============================================================================

106\. TODO RULE

===============================================================================



TODO باید actionable باشد.



Bad:



TODO: fix this



Good:



TODO:

Implement repository adapter for SQL Server persistence.



TODO باید در صورت امکان:



\- owner

\- priority

\- phase

\- dependency

\- status



داشته باشد.



===============================================================================

107\. ARCHITECTURE PHASE IMPLEMENTATION

===============================================================================



هر Phase باید قبل از implementation دارای:



1\. Goal

2\. Scope

3\. Responsibilities

4\. Components

5\. Dependencies

6\. Interfaces

7\. Data flow

8\. Error model

9\. Testing strategy

10\. Acceptance criteria



باشد.



===============================================================================

108\. PHASE COMPLETION RULE

===============================================================================



Phase فقط زمانی COMPLETE است که:



\- architecture implemented

\- tests implemented

\- quality gate green

\- documentation updated

\- project state updated

\- git commit created



باشد.



===============================================================================

109\. SUB-PHASE RULE

===============================================================================



Phase 28 دارای sub-phaseها است.



مثلاً:



28.1

28.2

28.3

28.4

28.5

...



هر sub-phase باید:



\- scope محدود

\- implementation مشخص

\- tests

\- verification

\- commit



داشته باشد.



===============================================================================

110\. CURRENT IMPLEMENTATION PHILOSOPHY

===============================================================================



ShadBotTrader از صفر ساخته می‌شود.



کدهای قدیمی موجود در repository در صورت conflict با architecture جدید الزاماً

قابل حفظ نیستند.



در صورت نیاز:



\- rewrite

\- restructure

\- rename

\- delete



مجاز است.



اما تصمیم باید deliberate باشد.



===============================================================================

111\. NO LEGACY CONTAMINATION

===============================================================================



Legacy code نباید صرفاً به دلیل وجود داشتن وارد architecture جدید شود.



LEGACY/



به عنوان historical/reference area در نظر گرفته می‌شود.



Legacy dependency باید explicit باشد.



===============================================================================

112\. IMPLEMENTATION ORDER

===============================================================================



پیاده‌سازی باید dependency-aware باشد.



ترتیب کلی:



Architecture Foundation

&#x20;       ↓

Core

&#x20;       ↓

Domain

&#x20;       ↓

Application

&#x20;       ↓

Infrastructure

&#x20;       ↓

Services

&#x20;       ↓

Engines

&#x20;       ↓

Pipelines

&#x20;       ↓

Platforms

&#x20;       ↓

Integration

&#x20;       ↓

GUI

&#x20;       ↓

Deployment



هر مرحله باید prerequisites خود را داشته باشد.



===============================================================================

113\. MINIMUM IMPLEMENTATION STANDARD

===============================================================================



هر class production باید:



\- clear responsibility

\- type hints

\- docstring در public APIهای مهم

\- testability

\- dependency isolation



داشته باشد.



===============================================================================

114\. CLASS SIZE

===============================================================================



Classهای بزرگ و God Object ممنوع.



اگر class چند مسئولیت مستقل دارد:



Extract شود.



===============================================================================

115\. FUNCTION SIZE

===============================================================================



Function باید یک responsibility واضح داشته باشد.



Functionهای بسیار طولانی باید بررسی شوند.



اما artificial fragmentation نیز ممنوع است.



===============================================================================

116\. GOD OBJECT

===============================================================================



کلاس‌هایی مانند:



MegaManager

SystemManager

EverythingService

UniversalEngine



ممنوع هستند مگر architecture صراحتاً دلیل داشته باشد.



===============================================================================

117\. UTILITY MODULES

===============================================================================



Utility dumping ground ممنوع.



ساخت:



utils.py



برای جمع کردن logic نامرتبط ممنوع.



هر utility باید ownership مشخص داشته باشد.



===============================================================================

118\. COMMENTS

===============================================================================



Comment باید دلیل تصمیم را توضیح دهد، نه syntax را.



Bad:



\# add one to x

x += 1



Good:



\# Broker requires quantities to be rounded to the configured lot size.

quantity = round\_to\_lot\_size(quantity)



===============================================================================

119\. DOCSTRINGS

===============================================================================



Public interfaces باید documentation کافی داشته باشند.



Documentation باید:



\- purpose

\- input

\- output

\- errors

\- invariants



را در صورت نیاز توضیح دهد.



===============================================================================

120\. TEST NAMING

===============================================================================



Test name باید behavior را توضیح دهد.



Bad:



test\_service



Good:



test\_rejects\_order\_when\_risk\_limit\_is\_exceeded



===============================================================================

121\. DETERMINISTIC TESTS

===============================================================================



Test نباید به:



\- internet

\- current time

\- random state

\- external broker

\- external API



وابسته باشد مگر Integration/E2E test باشد.



===============================================================================

122\. MOCKING

===============================================================================



Mock باید در boundary استفاده شود.



Over-mocking ممنوع.



Domain logic را با mockهای زیاد تست نکنید.



===============================================================================

123\. INTEGRATION TEST

===============================================================================



Integration test باید integration واقعی boundary را بررسی کند.



مثلاً:



Application

\+

Repository adapter



===============================================================================

124\. E2E

===============================================================================



E2E باید flow کامل را بررسی کند.



مثلاً:



Market Data

→ Feature

→ Prediction

→ Decision

→ Risk

→ Execution Simulation



===============================================================================

125\. TEST DATA

===============================================================================



Test data باید:



\- deterministic

\- versioned

\- isolated



باشد.



===============================================================================

126\. FAILURE TESTING

===============================================================================



فقط happy path کافی نیست.



باید test شود:



\- invalid input

\- unavailable dependency

\- stale data

\- timeout

\- duplicate event

\- invalid state

\- risk violation

\- execution failure



===============================================================================

127\. EVENT TESTING

===============================================================================



Event Bus باید test شود:



\- registration

\- dispatch

\- multiple handlers

\- handler failure

\- ordering در صورت نیاز

\- correlation



===============================================================================

128\. PLUGIN TESTING

===============================================================================



هر Plugin باید:



\- registration

\- lifecycle

\- capability

\- configuration

\- failure



را test کند.



===============================================================================

129\. SECURITY TESTING

===============================================================================



باید بررسی شود:



\- secret leakage

\- unsafe input

\- unauthorized execution

\- invalid configuration

\- dangerous defaults



===============================================================================

130\. CONFIGURATION TESTING

===============================================================================



Configuration باید برای:



\- missing value

\- invalid value

\- default

\- environment override

\- type conversion



test شود.



===============================================================================

131\. LOGGING TESTING

===============================================================================



Logs نباید:



\- password

\- API key

\- secret

\- token



را expose کنند.



===============================================================================

132\. PERFORMANCE TESTING

===============================================================================



Subsystemهای performance-sensitive باید benchmark شوند.



به‌خصوص:



\- data ingestion

\- feature generation

\- inference

\- backtesting

\- event dispatch



===============================================================================

133\. DATA QUALITY

===============================================================================



Data quality باید measurable باشد.



Metrics می‌تواند شامل:



\- missing rate

\- duplicate rate

\- invalid rate

\- timestamp gaps

\- outliers



باشد.



===============================================================================

134\. MODEL QUALITY

===============================================================================



AI model فقط بر اساس accuracy ارزیابی نمی‌شود.



بسته به مسئله:



\- precision

\- recall

\- F1

\- MAE

\- RMSE

\- Sharpe

\- drawdown

\- profit factor

\- calibration



می‌تواند استفاده شود.



===============================================================================

135\. TRADING MODEL SAFETY

===============================================================================



Backtest profitability به تنهایی دلیل deploy کردن model نیست.



باید:



\- out-of-sample validation

\- walk-forward validation

\- robustness

\- risk analysis



بررسی شود.



===============================================================================

136\. NO DATA LEAKAGE

===============================================================================



هر training feature باید ثابت کند که در زمان prediction قابل دسترس بوده است.



Future information ممنوع.



===============================================================================

137\. STRATEGY ISOLATION

===============================================================================



Strategy نباید broker implementation را بشناسد.



Strategy:



Market Context

\+

Features

\+

Prediction

\+

Portfolio Context

\+

Risk Context



را دریافت می‌کند.



===============================================================================

138\. BROKER ABSTRACTION

===============================================================================



Broker interface باید عملیات استاندارد مانند:



\- submit order

\- cancel order

\- get order

\- get account

\- get positions



را abstract کند.



Implementation provider-specific در Infrastructure/Plugin قرار می‌گیرد.



===============================================================================

139\. MARKET DATA PROVIDER

===============================================================================



Market Data provider باید interface استاندارد داشته باشد.



Provider-specific schema نباید به Domain leak شود.



Normalization باید قبل از Domain consumption انجام شود.



===============================================================================

140\. NEWS PROVIDER

===============================================================================



News data باید normalize شود.



News provider-specific object نباید مستقیماً وارد Domain شود.



===============================================================================

141\. STORAGE

===============================================================================



Storage implementation باید قابل تعویض باشد.



Domain نباید بداند:



SQL Server

PostgreSQL

SQLite

File

Object Storage



کدام backend است.



===============================================================================

142\. EXPORTERS

===============================================================================



Exporterها باید abstraction داشته باشند.



نمونه:



Markdown

JSON

HTML

PDF



نباید logic تولید snapshot را duplicate کنند.



===============================================================================

143\. PROJECT INTELLIGENCE EXPORT

===============================================================================



Exporter فقط presentation format را تغییر می‌دهد.



Data gathering باید توسط scanner/builder انجام شود.



===============================================================================

144\. SCANNER RULE

===============================================================================



Scanner فقط observation انجام می‌دهد.



Scanner نباید:



\- state mutation

\- business decision

\- documentation formatting



را انجام دهد.



===============================================================================

145\. BUILDER RULE

===============================================================================



Builder داده‌های خام را به modelهای project intelligence تبدیل می‌کند.



Builder نباید مستقیماً filesystem را scan کند مگر abstraction مشخصی وجود داشته باشد.



===============================================================================

146\. MODEL RULE

===============================================================================



Project Intelligence models باید:



\- serializable

\- typed

\- stable



باشند.



===============================================================================

147\. RUNTIME RULE

===============================================================================



IntelligenceRuntime مسئول orchestration است.



نباید همه logic را در یک class قرار دهد.



Runtime:



Scanner

→ Builder

→ Analyzer

→ Exporter



را orchestrate می‌کند.



===============================================================================

148\. GENERATED STATE VALIDATION

===============================================================================



Generated state باید از نظر consistency بررسی شود.



مثلاً:



Statistics.json

باید با snapshot فعلی سازگار باشد.



DependencyGraph.json

نباید moduleهای حذف‌شده را به عنوان active نشان دهد.



===============================================================================

149\. ARCHIVE RULE

===============================================================================



Archive immutable تاریخی محسوب شود.



نباید historical state بدون دلیل overwrite شود.



===============================================================================

150\. CHANGE IMPACT ANALYSIS

===============================================================================



قبل از تغییر architecture-sensitive component باید impact analysis انجام شود.



بررسی:



\- imports

\- dependencies

\- events

\- plugins

\- tests

\- runtime registration

\- generated state



===============================================================================

151\. SAFE CHANGE WORKFLOW

===============================================================================



Workflow استاندارد:



READ

↓

UNDERSTAND

↓

PLAN

↓

IMPLEMENT

↓

TEST

↓

LINT

↓

TYPE CHECK

↓

FORMAT

↓

REVIEW

↓

UPDATE DOCUMENTATION

↓

UPDATE PROJECT STATE

↓

COMMIT



===============================================================================

152\. AI CODING AGENT WORKFLOW

===============================================================================



Agent باید:



STEP 1

Read architecture.



STEP 2

Read development rules.



STEP 3

Inspect workspace.



STEP 4

Read relevant source files.



STEP 5

Read project state.



STEP 6

Determine current phase.



STEP 7

Identify required changes.



STEP 8

Implement.



STEP 9

Run tests.



STEP 10

Run Ruff.



STEP 11

Run Black.



STEP 12

Run Mypy.



STEP 13

Fix all failures.



STEP 14

Re-run complete quality gate.



STEP 15

Update project intelligence.



STEP 16

Report exact changes.



===============================================================================

153\. AGENT MUST NOT ASK USER TO MANUALLY EDIT CODE

===============================================================================



اگر task coding است، Agent باید implementation کامل را تولید کند.



User نباید مجبور شود برای implementation معمول:



\- خط به خط کد بنویسد.

\- import اضافه کند.

\- فایل بسازد.



Agent باید دستورهای اجرایی دقیق یا patch/code کامل ارائه دهد.



===============================================================================

154\. POWERSHELL AUTOMATION

===============================================================================



در محیط Windows، ساختارهای بزرگ پروژه باید در صورت امکان با PowerShell

automation ساخته شوند.



اما script generator باید:



\- deterministic

\- idempotent

\- safe



باشد.



===============================================================================

155\. IDE INDEPENDENCE

===============================================================================



Architecture نباید به VS Code یا IDE خاصی وابسته باشد.



===============================================================================

156\. OPERATING SYSTEM

===============================================================================



Development environment فعلی Windows است.



اما architecture باید تا حد امکان OS-independent باشد.



===============================================================================

157\. PATH RULE

===============================================================================



File pathها باید portable باشند.



Hard-coded Windows path ممنوع.



===============================================================================

158\. ENCODING

===============================================================================



UTF-8 باید standard باشد.



===============================================================================

159\. TIMEOUTS

===============================================================================



External operations باید timeout داشته باشند.



Network call بدون timeout ممنوع.



===============================================================================

160\. RETRIES

===============================================================================



Retry باید فقط برای failureهای transient انجام شود.



Retry باید:



\- bounded

\- observable

\- configurable



باشد.



===============================================================================

161\. IDEMPOTENCY

===============================================================================



Operationهای حساس به retry باید در صورت امکان idempotent باشند.



مثلاً ingestion نباید با retry داده duplicate ایجاد کند.



===============================================================================

162\. TRANSACTION

===============================================================================



State transitionهای حساس باید transactional باشند.



===============================================================================

163\. CONSISTENCY

===============================================================================



Distributed consistency باید explicit باشد.



Eventual consistency نباید accidental باشد.



===============================================================================

164\. EVENT DUPLICATION

===============================================================================



Handlerها در صورت نیاز باید idempotent باشند.



Duplicate event نباید transaction را خراب کند.



===============================================================================

165\. CORRELATION

===============================================================================



Flowهای چندمرحله‌ای باید correlation ID داشته باشند.



مثلاً:



Market Data Event

→ Prediction

→ Decision

→ Order



باید قابل trace باشد.



===============================================================================

166\. TRACEABILITY

===============================================================================



هر trade مهم باید بتواند trace شود به:



\- strategy

\- model

\- prediction

\- signal

\- decision

\- risk evaluation

\- order

\- execution



===============================================================================

167\. AUDIT

===============================================================================



تصمیمات مهم trading باید audit trail داشته باشند.



===============================================================================

168\. IMMUTABILITY

===============================================================================



Historical records مانند:



Trade

Prediction

Decision

Event



در صورت نیاز باید immutable باشند.



===============================================================================

169\. CLOCK

===============================================================================



Time source باید injectable باشد.



Testing نباید به system clock وابسته باشد.



===============================================================================

170\. RANDOMNESS

===============================================================================



Random generator باید injectable/seedable باشد.



===============================================================================

171\. CONFIGURATION IMMUTABILITY

===============================================================================



پس از startup، configuration مهم نباید بدون lifecycle مشخص mutate شود.



===============================================================================

172\. HOT RELOAD

===============================================================================



Hot reload فقط در subsystemهایی که architecture اجازه می‌دهد.



===============================================================================

173\. MODEL DEPLOYMENT

===============================================================================



Model deployment باید versioned باشد.



Rollback باید ممکن باشد.



===============================================================================

174\. FEATURE VERSION COMPATIBILITY

===============================================================================



Model باید با Feature version compatible باشد.



Model نباید silently با feature schema ناسازگار اجرا شود.



===============================================================================

175\. SCHEMA VALIDATION

===============================================================================



External data باید قبل از consumption validate شود.



===============================================================================

176\. SERIALIZATION

===============================================================================



Serialization format باید stable و versionable باشد.



===============================================================================

177\. JSON

===============================================================================



JSON برای interchange و generated project state مناسب است.



اما نباید به عنوان Domain model اصلی استفاده شود.



===============================================================================

178\. MARKDOWN

===============================================================================



Markdown برای human-readable documentation/context مناسب است.



===============================================================================

179\. HTML/PDF

===============================================================================



HTML/PDF presentation formats هستند.



Business logic نباید در exporterها باشد.



===============================================================================

180\. PROJECT STATISTICS

===============================================================================



Statistics باید derived باشند.



مثلاً:



file\_count

line\_count

class\_count

function\_count

test\_count



باید از repository scan شوند.



نباید دستی نگهداری شوند.



===============================================================================

181\. DEPENDENCY GRAPH

===============================================================================



Dependency graph باید از actual imports/dependencies استخراج شود.



Graph نباید manually maintained باشد مگر metadata خاصی نیاز باشد.



===============================================================================

182\. ARCHITECTURE DRIFT

===============================================================================



Project Intelligence باید در آینده architecture drift را detect کند.



مثلاً:



Domain → Infrastructure



اگر forbidden باشد:



ARCHITECTURE VIOLATION



گزارش شود.



===============================================================================

183\. QUALITY LEVELS

===============================================================================



هر feature یکی از وضعیت‌های زیر دارد:



DRAFT

IMPLEMENTED

TESTED

VERIFIED

PRODUCTION\_READY



IMPLEMENTED به معنی PRODUCTION\_READY نیست.



===============================================================================

184\. PRODUCTION READY

===============================================================================



Feature فقط زمانی production-ready است که:



\- implementation

\- tests

\- type safety

\- lint

\- documentation

\- error handling

\- observability

\- security

\- architecture compliance



تکمیل شده باشد.



===============================================================================

185\. NO SHORTCUTS

===============================================================================



ممنوع:



\- bypass کردن tests

\- disable کردن Ruff rule بدون دلیل

\- ignore کردن Mypy error

\- حذف test برای green شدن

\- catch-all exception

\- hard-code secret

\- direct database access from Domain

\- direct broker access from Strategy

\- direct AI-to-order execution

\- architecture bypass



===============================================================================

186\. TEMPORARY EXCEPTIONS

===============================================================================



اگر exception موقتاً ضروری است:



باید:



\- documented

\- tracked

\- assigned

\- دارای removal plan



باشد.



Temporary code بدون removal plan ممنوع.



===============================================================================

187\. ARCHITECTURAL CHANGE PROCESS

===============================================================================



برای تغییر architecture:



1\. Problem Statement

2\. Current State

3\. Proposed State

4\. Alternatives

5\. Impact

6\. Migration Plan

7\. Risks

8\. Approval



سپس implementation.



===============================================================================

188\. NO ARCHITECTURE DRIFT

===============================================================================



هر implementation جدید باید با architecture specification تطبیق داده شود.



اگر implementation مجبور است architecture را بشکند:



implementation متوقف شود.



===============================================================================

189\. PHASE DISCIPLINE

===============================================================================



Developer نباید بدون تکمیل prerequisites وارد Phase بعدی شود.



اما Phaseها می‌توانند parallelize شوند فقط در صورتی که dependency graph اجازه دهد.



===============================================================================

190\. COMPLETION REPORT

===============================================================================



پس از هر Phase/Sub-phase گزارش باید شامل:



\- Implemented

\- Added files

\- Modified files

\- Deleted files

\- Tests

\- Quality Gate

\- Known Issues

\- Remaining Work

\- Commit Hash



باشد.



===============================================================================

191\. CURRENT ROADMAP PRINCIPLE

===============================================================================



بعد از تکمیل foundationهای فعلی، implementation باید به ترتیب dependency ادامه یابد.



Project Intelligence باید به صورت incremental توسعه پیدا کند.



Trading Platform نباید قبل از foundationهای لازم به صورت uncontrolled پیاده‌سازی شود.



===============================================================================

192\. ARCHITECTURAL PRIORITY

===============================================================================



اولویت تصمیم‌گیری:



1\. Correctness

2\. Architecture

3\. Safety

4\. Testability

5\. Maintainability

6\. Observability

7\. Performance

8\. Convenience



Convenience هیچ‌وقت نباید Architecture را override کند.



===============================================================================

193\. FINAL AUTHORITY

===============================================================================



اگر بین دو implementation اختلاف وجود داشت:



Architecture Contract

برنده است.



اگر بین convenience و correctness اختلاف بود:



Correctness برنده است.



اگر بین speed و safety اختلاف بود:



Safety برنده است.



اگر بین temporary solution و production solution اختلاف بود:



Production solution برنده است.



===============================================================================

194\. DEVELOPER CHECKLIST

===============================================================================



قبل از شروع:



\[ ] Architecture خوانده شد

\[ ] Current phase مشخص شد

\[ ] Project state خوانده شد

\[ ] Workspace inspect شد

\[ ] Dependencies بررسی شد

\[ ] Existing implementation بررسی شد



حین توسعه:



\[ ] Dependency rules رعایت شد

\[ ] Domain isolation حفظ شد

\[ ] DI رعایت شد

\[ ] Interfaces مشخص شدند

\[ ] Error handling وجود دارد

\[ ] Logging مناسب است

\[ ] Tests نوشته شدند

\[ ] No placeholder code

\[ ] No unrelated changes



قبل از commit:



\[ ] pytest green

\[ ] ruff green

\[ ] black clean

\[ ] mypy green

\[ ] diff reviewed

\[ ] documentation updated

\[ ] project state updated



بعد از commit:



\[ ] commit hash ثبت شد

\[ ] roadmap updated

\[ ] todo updated

\[ ] decisions updated در صورت نیاز

\[ ] ChatGPT\_Context regenerated



===============================================================================

195\. AI AGENT FINAL CHECKLIST

===============================================================================



Agent قبل از اعلام completion باید بتواند پاسخ دهد:



1\. What did I change?

2\. Why did I change it?

3\. Which architecture rule allows it?

4\. Which files changed?

5\. Which dependencies changed?

6\. Which tests were added?

7\. Did all tests pass?

8\. Did Ruff pass?

9\. Did Black pass?

10\. Did Mypy pass?

11\. Did I introduce architecture drift?

12\. Did I update project state?

13\. What remains?

14\. What is the next phase/sub-phase?



اگر پاسخ هر مورد مشخص نیست:



Task هنوز complete نیست.



===============================================================================

196\. FINAL PROJECT PRINCIPLE

===============================================================================



ShadBotTrader نباید به یک collection of scripts تبدیل شود.



ShadBotTrader باید یک:



ENTERPRISE AI TRADING PLATFORM



باقی بماند.



تمام subsystemها باید:



\- modular

\- replaceable

\- testable

\- observable

\- extensible

\- maintainable

\- production-grade



باشند.



===============================================================================

197\. NON-NEGOTIABLE RULE

===============================================================================



هیچ Developer یا AI Agent حق ندارد صرفاً برای سریع‌تر شدن کار:



Architecture

Domain Boundaries

Dependency Rules

Testing Standards

Security

Trading Safety

Data Integrity

Project Intelligence

یا Quality Gate



را دور بزند.



اگر راه‌حل فعلی ممکن نیست:



STOP.



Problem را گزارش کن.



Architecture را بررسی کن.



راه‌حل درست را طراحی کن.



سپس implementation کن.



===============================================================================

END OF DEVELOPMENT RULES

===============================================================================

