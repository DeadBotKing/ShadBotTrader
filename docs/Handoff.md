====================================================================

SHADBOT

ENTERPRISE AI TRADING PLATFORM

MASTER HANDOFF DOCUMENT

====================================================================



Document:

&#x20;   Handoff



Version:

&#x20;   1.0



Status:

&#x20;   MASTER PROJECT HANDOFF



Purpose:

&#x20;   انتقال کامل دانش پروژه بین Developer / Coding Agent / Chat Session



Project:

&#x20;   ShadBot



Primary Goal:

&#x20;   ساخت یک Enterprise AI Trading Platform ماژولار، قابل توسعه،

&#x20;   قابل تست، قابل شبیه‌سازی، قابل استقرار و دارای Project Intelligence

&#x20;   داخلی برای درک خودکار وضعیت پروژه.



====================================================================

0\. CRITICAL INSTRUCTION

====================================================================



این فایل یک فایل توضیحی ساده نیست.



این فایل Project Contract است.



هر Developer یا Coding Agent که وارد پروژه می‌شود باید قبل از

هرگونه تغییر جدی موارد زیر را بخواند:



&#x20;   1. Handoff

&#x20;   2. ARCHITECTURE\_HANDOFF

&#x20;   3. DATA\_FLOW\_DOCUMENTATION

&#x20;   4. DEVELOPMENT\_RULES

&#x20;   5. EXECUTION\_GUIDE

&#x20;   6. project\_state/generated/ChatGPT\_Context.md

&#x20;   7. project\_state/generated/Architecture.md

&#x20;   8. project\_state/generated/Roadmap.md

&#x20;   9. project\_state/generated/Decisions.md

&#x20;   10. project\_state/generated/Todo.md



نباید بدون بررسی این اسناد معماری جدید طراحی شود.



نباید فرض شود پروژه از صفر است.



نباید implementation موجود بدون بررسی حذف یا بازنویسی شود.



اگر بین implementation و Architecture Contract اختلاف وجود داشت:



&#x20;   Architecture Contract اولویت دارد.



اگر بین implementation قدیمی و Decision ثبت‌شده اختلاف وجود داشت:



&#x20;   Decision ثبت‌شده اولویت دارد.



اگر Project State جدیدتر از این سند باشد:



&#x20;   Project State جدیدتر اولویت دارد.



====================================================================

1\. PROJECT IDENTITY

====================================================================



Project Name:

&#x20;   ShadBot



Project Type:

&#x20;   Enterprise AI Trading Platform



Primary Language:

&#x20;   Python



Architecture Style:

&#x20;   Clean Architecture

&#x20;   Domain-Driven Design

&#x20;   Modular Architecture

&#x20;   Dependency Inversion

&#x20;   Event-Driven Architecture

&#x20;   Plugin Architecture

&#x20;   Pipeline Architecture



Primary Objectives:



&#x20;   - Market Data Processing

&#x20;   - Feature Engineering

&#x20;   - AI / ML

&#x20;   - Market Analysis

&#x20;   - Signal Generation

&#x20;   - Risk Management

&#x20;   - Trading

&#x20;   - Portfolio Management

&#x20;   - Backtesting

&#x20;   - Simulation

&#x20;   - Optimization

&#x20;   - Self Learning

&#x20;   - Project Intelligence

&#x20;   - GUI

&#x20;   - Persistent Storage

&#x20;   - Enterprise Configuration

&#x20;   - Logging

&#x20;   - Testing

&#x20;   - Deployment



Secondary Objective:



&#x20;   ShadBot باید بتواند خودش ساختار، کد، dependency،

&#x20;   architecture، roadmap، تصمیمات و وضعیت توسعه پروژه را

&#x20;   تحلیل کند و یک Project Context قابل انتقال تولید کند.



====================================================================

2\. PRODUCT VISION

====================================================================



ShadBot قرار نیست فقط یک Trading Bot ساده باشد.



هدف نهایی یک Platform است.



Platform باید بتواند:



&#x20;   داده بازار را دریافت کند

&#x20;   داده را validate کند

&#x20;   داده را normalize کند

&#x20;   feature تولید کند

&#x20;   مدل AI آموزش دهد

&#x20;   مدل AI را ارزیابی کند

&#x20;   prediction تولید کند

&#x20;   trading signal تولید کند

&#x20;   risk را بررسی کند

&#x20;   order تولید کند

&#x20;   order را اجرا کند

&#x20;   trade ثبت کند

&#x20;   position مدیریت کند

&#x20;   portfolio مدیریت کند

&#x20;   performance را اندازه‌گیری کند

&#x20;   historical simulation اجرا کند

&#x20;   strategy را backtest کند

&#x20;   مدل‌ها را optimize کند

&#x20;   از نتایج گذشته یاد بگیرد

&#x20;   وضعیت پروژه خودش را بفهمد

&#x20;   وضعیت پروژه را مستندسازی کند

&#x20;   و در نهایت به‌صورت production system اجرا شود.



====================================================================

3\. ARCHITECTURAL PHILOSOPHY

====================================================================



اصل اول:



&#x20;   Domain نباید به Infrastructure وابسته باشد.



اصل دوم:



&#x20;   Business Logic نباید داخل GUI باشد.



اصل سوم:



&#x20;   Business Logic نباید داخل Database باشد.



اصل چهارم:



&#x20;   Framework نباید معماری را کنترل کند.



اصل پنجم:



&#x20;   Infrastructure باید implementation contractهای

&#x20;   Application / Domain را فراهم کند.



اصل ششم:



&#x20;   Engines نباید تبدیل به God Object شوند.



اصل هفتم:



&#x20;   Services نباید جای Domain را بگیرند.



اصل هشتم:



&#x20;   Event Bus باید coupling بین subsystemها را کاهش دهد.



اصل نهم:



&#x20;   Plugin باید از طریق contract وارد سیستم شود.



اصل دهم:



&#x20;   Simulation و Live Trading باید تا حد ممکن از

&#x20;   contractهای مشترک استفاده کنند.



اصل یازدهم:



&#x20;   AI Model بدون metadata معتبر نیست.



اصل دوازدهم:



&#x20;   هر تغییر مهم باید test شود.



اصل سیزدهم:



&#x20;   هیچ Phase بدون Quality Gate کامل نیست.



اصل چهاردهم:



&#x20;   هیچ Agent نباید architecture را از روی حدس تغییر دهد.



====================================================================

4\. MASTER ARCHITECTURE

====================================================================



Architecture کلی:



&#x20;   Core

&#x20;       ↓

&#x20;   Domain

&#x20;       ↓

&#x20;   Application

&#x20;       ↓

&#x20;   Infrastructure



و در سطح orchestration:



&#x20;   Application

&#x20;       ↓

&#x20;   Pipelines

&#x20;       ↓

&#x20;   Engines

&#x20;       ↓

&#x20;   Services

&#x20;       ↓

&#x20;   Plugins / Events / Infrastructure



Subsystemهای اصلی:



&#x20;   Core

&#x20;   Domain

&#x20;   Application

&#x20;   Infrastructure

&#x20;   Interfaces

&#x20;   Shared

&#x20;   Exceptions

&#x20;   Pipelines

&#x20;   Engines

&#x20;   Services

&#x20;   Plugins

&#x20;   Event Bus

&#x20;   Data Platform

&#x20;   Feature Platform

&#x20;   AI Platform

&#x20;   Trading Platform

&#x20;   Portfolio Platform

&#x20;   Simulation Platform

&#x20;   Self Learning Platform

&#x20;   Project Intelligence Platform

&#x20;   GUI

&#x20;   Storage

&#x20;   Configuration

&#x20;   Logging

&#x20;   Testing

&#x20;   Deployment



====================================================================

5\. 28-PHASE MASTER ROADMAP

====================================================================



Phase 01

&#x20;   Architecture Principles



Phase 02

&#x20;   Dependency Rules



Phase 03

&#x20;   Domain Model



Phase 04

&#x20;   Project Tree



Phase 05

&#x20;   Framework Design



Phase 06

&#x20;   Pipeline Design



Phase 07

&#x20;   Engine Design



Phase 08

&#x20;   Service Design



Phase 09

&#x20;   Plugin Architecture



Phase 10

&#x20;   Event Bus



Phase 11

&#x20;   Data Platform



Phase 12

&#x20;   Feature Platform



Phase 13

&#x20;   AI Platform



Phase 14

&#x20;   Trading Platform



Phase 15

&#x20;   Portfolio Platform



Phase 16

&#x20;   Simulation Platform



Phase 17

&#x20;   Self Learning Platform



Phase 18

&#x20;   Project Intelligence Platform



Phase 19

&#x20;   GUI Architecture



Phase 20

&#x20;   SQL Server Schema



Phase 21

&#x20;   Configuration System



Phase 22

&#x20;   Logging System



Phase 23

&#x20;   Testing Architecture



Phase 24

&#x20;   Deployment Architecture



Phase 25

&#x20;   PowerShell Project Generator



Phase 26

&#x20;   Integration Hardening



Phase 27

&#x20;   Production Readiness



Phase 28

&#x20;   Architecture Freeze



====================================================================

6\. PHASE STATUS

====================================================================



Architecture Design:

&#x20;   Completed through Phase 28



Implementation:

&#x20;   Foundation implementation started.



Important:



&#x20;   Architecture phases and implementation phases are NOT identical.



&#x20;   Architecture has been designed.



&#x20;   Production implementation is being built incrementally.



====================================================================

7\. CURRENT GIT STATE

====================================================================



Repository:

&#x20;   ShadBot



Initial repository commit:



&#x20;   401817a

&#x20;   Initial commit



Important implementation commits:



&#x20;   d085a92

&#x20;   Implement ShadBot Core Foundation



&#x20;   5fed9b8

&#x20;   Implement ShadBot Domain Core



&#x20;   f96557b

&#x20;   Implement application runtime layer



Current development branch used during architecture implementation:



&#x20;   architecture-v1



Git must be used continuously.



Every completed implementation milestone must have a dedicated commit.



====================================================================

8\. CURRENT IMPLEMENTED CORE

====================================================================



Core Foundation has been implemented.



Files:



&#x20;   src/ShadBot/core/dependency/container.py



&#x20;   src/ShadBot/core/events/event.py



&#x20;   src/ShadBot/core/events/eventBus.py



&#x20;   src/ShadBot/core/lifecycle/lifecycleManager.py



&#x20;   src/ShadBot/core/plugins/plugin.py



&#x20;   src/ShadBot/core/services/baseService.py



Purpose:



&#x20;   Dependency management

&#x20;   Event abstraction

&#x20;   Event bus

&#x20;   Lifecycle management

&#x20;   Plugin abstraction

&#x20;   Base service abstraction



This layer is foundational.



Do not place trading business logic here.



====================================================================

9\. CURRENT DOMAIN IMPLEMENTATION

====================================================================



Domain Core has been implemented.



Common:



&#x20;   src/ShadBot/domain/common/entity.py

&#x20;   src/ShadBot/domain/common/valueObject.py



Market:



&#x20;   src/ShadBot/domain/market/candle.py

&#x20;   src/ShadBot/domain/market/symbol.py

&#x20;   src/ShadBot/domain/market/timefram.py



Portfolio:



&#x20;   src/ShadBot/domain/portfolio/account.py

&#x20;   src/ShadBot/domain/portfolio/balance.py



Prediction:



&#x20;   src/ShadBot/domain/prediction/prediction.py

&#x20;   src/ShadBot/domain/prediction/signal.py



Risk:



&#x20;   src/ShadBot/domain/risk/riskModel.py



Trading:



&#x20;   src/ShadBot/domain/trading/oerder.py

&#x20;   src/ShadBot/domain/trading/position.py

&#x20;   src/ShadBot/domain/trading/trade.py



IMPORTANT:



&#x20;   Existing filenames contain historical naming mistakes such as:



&#x20;       timefram.py

&#x20;       oerder.py



Do not blindly propagate these names.



During refactoring use:



&#x20;       timeframe.py

&#x20;       order.py



but only after checking imports and tests.



====================================================================

10\. DOMAIN RULE

====================================================================



Domain contains business concepts.



Domain examples:



&#x20;   Symbol

&#x20;   TimeFrame

&#x20;   Candle

&#x20;   Account

&#x20;   Balance

&#x20;   Prediction

&#x20;   Signal

&#x20;   Risk Model

&#x20;   Order

&#x20;   Position

&#x20;   Trade



Domain must remain framework-independent.



Do not import:



&#x20;   FastAPI

&#x20;   Django

&#x20;   Flask

&#x20;   SQLAlchemy

&#x20;   database drivers

&#x20;   GUI frameworks

&#x20;   HTTP clients

&#x20;   broker SDKs



directly into Domain.



====================================================================

11\. APPLICATION RUNTIME

====================================================================



Application Runtime has been implemented.



Files:



&#x20;   src/ShadBot/application/app.py

&#x20;   src/ShadBot/application/applicationState.py

&#x20;   src/ShadBot/application/bootstrap.py

&#x20;   src/ShadBot/application/runtime.py

&#x20;   src/ShadBot/application/serviceRegistry.py

&#x20;   src/ShadBot/application/shutdown.py

&#x20;   src/ShadBot/application/startup.py



Responsibilities:



&#x20;   Startup

&#x20;   Shutdown

&#x20;   Runtime lifecycle

&#x20;   Application state

&#x20;   Service registration

&#x20;   Bootstrap



Application Runtime must not become the place where all business

logic is stored.



====================================================================

12\. MAIN ENTRYPOINT

====================================================================



The project has been executed successfully through:



&#x20;   python -m src.shadbot.main



Previously verified output included:



&#x20;   ShadBot Core Started



and later:



&#x20;   Starting



and infrastructure/domain verification output.



The main entrypoint should remain lightweight.



Main should bootstrap the application.



It should not contain business logic.



====================================================================

13\. INFRASTRUCTURE

====================================================================



Infrastructure is responsible for external-world implementation.



Examples:



&#x20;   Database

&#x20;   SQL Server

&#x20;   Filesystem

&#x20;   HTTP

&#x20;   External APIs

&#x20;   Market Providers

&#x20;   Broker APIs

&#x20;   Model Storage

&#x20;   Message Transport

&#x20;   External Services



Infrastructure implementations must satisfy interfaces/contracts.



Domain must not depend on them directly.



====================================================================

14\. PIPELINE ARCHITECTURE

====================================================================



General pipeline:



&#x20;   Input

&#x20;       ↓

&#x20;   Validation

&#x20;       ↓

&#x20;   Normalization

&#x20;       ↓

&#x20;   Processing

&#x20;       ↓

&#x20;   Analysis

&#x20;       ↓

&#x20;   Decision

&#x20;       ↓

&#x20;   Output



Pipeline is orchestration.



Pipeline must not contain large amounts of business logic.



Pipeline should compose existing capabilities.



====================================================================

15\. ENGINE ARCHITECTURE

====================================================================



Core engines:



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



Each Engine must have:



&#x20;   Contract

&#x20;   Input

&#x20;   Output

&#x20;   Dependencies

&#x20;   Lifecycle

&#x20;   Error Handling

&#x20;   Tests



No Engine should become a God Object.



====================================================================

16\. SERVICE ARCHITECTURE

====================================================================



Services coordinate application operations.



Generic flow:



&#x20;   Request

&#x20;       ↓

&#x20;   Validation

&#x20;       ↓

&#x20;   Load Domain

&#x20;       ↓

&#x20;   Execute Domain Operation

&#x20;       ↓

&#x20;   Persist

&#x20;       ↓

&#x20;   Publish Event

&#x20;       ↓

&#x20;   Response



Services should be cohesive.



A service should not contain unrelated responsibilities.



====================================================================

17\. PLUGIN ARCHITECTURE

====================================================================



Plugins must support extensibility.



Plugin lifecycle:



&#x20;   Discovery

&#x20;       ↓

&#x20;   Validation

&#x20;       ↓

&#x20;   Registration

&#x20;       ↓

&#x20;   Initialization

&#x20;       ↓

&#x20;   Execution

&#x20;       ↓

&#x20;   Shutdown



Plugin should expose metadata.



Metadata should identify:



&#x20;   Plugin ID

&#x20;   Name

&#x20;   Version

&#x20;   Dependencies

&#x20;   Capabilities

&#x20;   Configuration

&#x20;   Compatibility



====================================================================

18\. EVENT BUS

====================================================================



Event Bus enables decoupled communication.



Flow:



&#x20;   Publisher

&#x20;       ↓

&#x20;   Event Bus

&#x20;       ↓

&#x20;   Subscribers



Event should contain at least:



&#x20;   event\_id

&#x20;   event\_type

&#x20;   timestamp

&#x20;   source

&#x20;   payload

&#x20;   metadata



Events should be immutable where practical.



Subscribers must not create hidden coupling.



====================================================================

19\. DATA PLATFORM

====================================================================



Data lifecycle:



&#x20;   External Provider

&#x20;       ↓

&#x20;   Collector

&#x20;       ↓

&#x20;   Raw Data

&#x20;       ↓

&#x20;   Validation

&#x20;       ↓

&#x20;   Normalization

&#x20;       ↓

&#x20;   Processed Data

&#x20;       ↓

&#x20;   Storage

&#x20;       ↓

&#x20;   Query



Raw data must remain immutable.



Processed datasets should be reproducible.



Data lineage should be traceable.



====================================================================

20\. FEATURE PLATFORM

====================================================================



Feature lifecycle:



&#x20;   Raw Data

&#x20;       ↓

&#x20;   Feature Definition

&#x20;       ↓

&#x20;   Feature Calculation

&#x20;       ↓

&#x20;   Validation

&#x20;       ↓

&#x20;   Versioning

&#x20;       ↓

&#x20;   Storage

&#x20;       ↓

&#x20;   Retrieval



Feature definitions must be versioned.



Training and inference should use consistent feature definitions.



Avoid training/inference feature skew.



====================================================================

21\. AI PLATFORM

====================================================================



AI lifecycle:



&#x20;   Dataset

&#x20;       ↓

&#x20;   Preprocessing

&#x20;       ↓

&#x20;   Feature Selection

&#x20;       ↓

&#x20;   Model

&#x20;       ↓

&#x20;   Training

&#x20;       ↓

&#x20;   Validation

&#x20;       ↓

&#x20;   Evaluation

&#x20;       ↓

&#x20;   Registry

&#x20;       ↓

&#x20;   Inference



Model metadata must contain:



&#x20;   model\_id

&#x20;   version

&#x20;   training\_dataset

&#x20;   features

&#x20;   target

&#x20;   algorithm

&#x20;   hyperparameters

&#x20;   metrics

&#x20;   created\_at



No unregistered model should silently enter production.



====================================================================

22\. TRADING PLATFORM

====================================================================



Trading flow:



&#x20;   Market Data

&#x20;       ↓

&#x20;   Analysis

&#x20;       ↓

&#x20;   Prediction

&#x20;       ↓

&#x20;   Signal

&#x20;       ↓

&#x20;   Strategy

&#x20;       ↓

&#x20;   Risk Check

&#x20;       ↓

&#x20;   Order

&#x20;       ↓

&#x20;   Execution

&#x20;       ↓

&#x20;   Trade

&#x20;       ↓

&#x20;   Position

&#x20;       ↓

&#x20;   Portfolio



CRITICAL:



&#x20;   Risk validation must occur before execution.



No direct:



&#x20;   Signal → Broker



flow is allowed.



====================================================================

23\. PORTFOLIO PLATFORM

====================================================================



Portfolio must manage:



&#x20;   Account

&#x20;   Balance

&#x20;   Position

&#x20;   Exposure

&#x20;   Allocation

&#x20;   PnL

&#x20;   Risk

&#x20;   Performance



Portfolio state should support historical reconstruction.



====================================================================

24\. SIMULATION PLATFORM

====================================================================



Simulation flow:



&#x20;   Historical Data

&#x20;       ↓

&#x20;   Market Simulation

&#x20;       ↓

&#x20;   Strategy

&#x20;       ↓

&#x20;   Risk

&#x20;       ↓

&#x20;   Order Simulation

&#x20;       ↓

&#x20;   Execution Simulation

&#x20;       ↓

&#x20;   Portfolio

&#x20;       ↓

&#x20;   Metrics



Simulation should use the same contracts as live trading wherever

architecturally possible.



Avoid maintaining two completely separate trading implementations.



====================================================================

25\. SELF LEARNING PLATFORM

====================================================================



Self Learning flow:



&#x20;   Performance

&#x20;       ↓

&#x20;   Error Analysis

&#x20;       ↓

&#x20;   Model Evaluation

&#x20;       ↓

&#x20;   Knowledge Extraction

&#x20;       ↓

&#x20;   Experiment

&#x20;       ↓

&#x20;   Optimization

&#x20;       ↓

&#x20;   Validation

&#x20;       ↓

&#x20;   Promotion



No automatic promotion to production without validation.



====================================================================

26\. PROJECT INTELLIGENCE PLATFORM

====================================================================



This is the internal project-awareness subsystem.



Goal:



&#x20;   ShadBot must understand itself.



It should inspect:



&#x20;   Files

&#x20;   Directories

&#x20;   Python packages

&#x20;   AST

&#x20;   Imports

&#x20;   Dependencies

&#x20;   Git

&#x20;   Configuration

&#x20;   Statistics

&#x20;   Roadmap

&#x20;   Decisions

&#x20;   TODOs

&#x20;   Architecture

&#x20;   Project evolution



Pipeline:



&#x20;   Workspace

&#x20;       ↓

&#x20;   Snapshot

&#x20;       ↓

&#x20;   Analysis

&#x20;       ↓

&#x20;   Evolution

&#x20;       ↓

&#x20;   Insight

&#x20;       ↓

&#x20;   Recommendation

&#x20;       ↓

&#x20;   Decision



====================================================================

27\. PROJECT INTELLIGENCE STRUCTURE

====================================================================



Current skeleton:



&#x20;   src/ShadBot/project/



&#x20;       \_\_init\_\_.py



&#x20;       core/

&#x20;           \_\_init\_\_.py

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

&#x20;           \_\_init\_\_.py

&#x20;           projectSnapshot.py

&#x20;           projectStatistics.py

&#x20;           projectContext.py

&#x20;           roadmap.py

&#x20;           decision.py



&#x20;       builders/

&#x20;           \_\_init\_\_.py

&#x20;           snapshotBuilder.py

&#x20;           contextBuilder.py

&#x20;           roadmapBuilder.py

&#x20;           statisticsBuilder.py

&#x20;           documentationBuilder.py



&#x20;       exporters/

&#x20;           \_\_init\_\_.py

&#x20;           markdownExporter.py

&#x20;           jsonExporter.py

&#x20;           htmlExporter.py

&#x20;           pdfExporter.py



&#x20;       runtime/

&#x20;           \_\_init\_\_.py

&#x20;           intelligenceRuntime.py



====================================================================

28\. PROJECT STATE

====================================================================



Persistent state directory:



&#x20;   project\_state/



&#x20;       generated/



&#x20;       archive/



Generated artifacts:



&#x20;   ProjectSnapshot.md

&#x20;   ProjectSnapshot.json

&#x20;   ChatGPT\_Context.md

&#x20;   Architecture.md

&#x20;   Roadmap.md

&#x20;   Decisions.md

&#x20;   Todo.md

&#x20;   Statistics.json

&#x20;   DependencyGraph.json



These files are not random documentation.



They are machine-readable / human-readable project state.



====================================================================

29\. CHATGPT\_CONTEXT

====================================================================



ChatGPT\_Context.md is the primary handoff artifact.



It must communicate:



&#x20;   Project Identity

&#x20;   Current Phase

&#x20;   Completed Phases

&#x20;   Architecture

&#x20;   Current Structure

&#x20;   Implemented Code

&#x20;   Dependencies

&#x20;   Decisions

&#x20;   Constraints

&#x20;   Known Issues

&#x20;   Current Work

&#x20;   Next Work

&#x20;   Roadmap

&#x20;   Tests

&#x20;   Git State



When a new chat starts:



&#x20;   ChatGPT\_Context.md



should be supplied first.



====================================================================

30\. PROJECT SNAPSHOT

====================================================================



ProjectSnapshot represents the observed state of the workspace.



It should eventually contain information such as:



&#x20;   project identity

&#x20;   timestamp

&#x20;   files

&#x20;   directories

&#x20;   packages

&#x20;   modules

&#x20;   dependencies

&#x20;   git status

&#x20;   branch

&#x20;   commits

&#x20;   statistics

&#x20;   architecture

&#x20;   roadmap

&#x20;   decisions

&#x20;   TODOs

&#x20;   warnings

&#x20;   errors



Snapshot should represent observed reality.



It must not invent information.



====================================================================

31\. AST ANALYSIS

====================================================================



ASTScanner must inspect Python source using Python AST facilities.



It should identify:



&#x20;   Modules

&#x20;   Classes

&#x20;   Functions

&#x20;   Imports

&#x20;   Decorators

&#x20;   Base classes

&#x20;   Signatures

&#x20;   Type annotations

&#x20;   Relationships



AST analysis should not execute arbitrary project code.



====================================================================

32\. DEPENDENCY ANALYSIS

====================================================================



DependencyScanner should determine:



&#x20;   package dependencies

&#x20;   module dependencies

&#x20;   import relationships

&#x20;   internal dependency graph

&#x20;   external dependencies



Output should support:



&#x20;   DependencyGraph.json



Dependency graph is useful for detecting architecture violations.



====================================================================

33\. GIT ANALYSIS

====================================================================



GitScanner should inspect:



&#x20;   Current branch

&#x20;   Current commit

&#x20;   Recent commits

&#x20;   Working tree

&#x20;   Modified files

&#x20;   Untracked files

&#x20;   Repository state



It should never modify Git state merely by scanning.



====================================================================

34\. ROADMAP

====================================================================



Roadmap represents:



&#x20;   Completed

&#x20;   In Progress

&#x20;   Planned

&#x20;   Blocked



Each item should have:



&#x20;   ID

&#x20;   Name

&#x20;   Status

&#x20;   Description

&#x20;   Dependencies

&#x20;   Priority

&#x20;   Notes



====================================================================

35\. DECISION SYSTEM

====================================================================



Architecture decisions must be recorded.



A Decision should contain:



&#x20;   Decision ID

&#x20;   Title

&#x20;   Context

&#x20;   Decision

&#x20;   Reason

&#x20;   Consequences

&#x20;   Status

&#x20;   Date



Do not silently replace architectural decisions.



====================================================================

36\. TODO SYSTEM

====================================================================



TODO scanner should identify unresolved work.



But TODOs must be classified.



Examples:



&#x20;   Technical Debt

&#x20;   Missing Implementation

&#x20;   Refactoring

&#x20;   Documentation

&#x20;   Testing

&#x20;   Architecture

&#x20;   Bug

&#x20;   Enhancement



====================================================================

37\. EXPORTERS

====================================================================



Required exporters:



&#x20;   Markdown

&#x20;   JSON

&#x20;   HTML

&#x20;   PDF



JSON should prioritize machine consumption.



Markdown should prioritize human / ChatGPT handoff.



HTML should prioritize visual inspection.



PDF should prioritize archival / reporting.



====================================================================

38\. GUI

====================================================================



GUI is presentation.



GUI should expose:



&#x20;   Dashboard

&#x20;   Market Data

&#x20;   Charts

&#x20;   Signals

&#x20;   Portfolio

&#x20;   Trades

&#x20;   Positions

&#x20;   Models

&#x20;   Backtests

&#x20;   Simulation

&#x20;   Project Intelligence

&#x20;   Logs

&#x20;   Configuration

&#x20;   System Health



GUI must communicate with Application layer.



GUI must not directly access Domain internals or database internals.



====================================================================

39\. SQL SERVER

====================================================================



Database is persistence infrastructure.



Major conceptual areas:



&#x20;   Market

&#x20;   Features

&#x20;   Models

&#x20;   Predictions

&#x20;   Signals

&#x20;   Orders

&#x20;   Trades

&#x20;   Positions

&#x20;   Portfolio

&#x20;   Simulation

&#x20;   Experiments

&#x20;   Events

&#x20;   Audit

&#x20;   Configuration



Database schema must preserve domain boundaries.



====================================================================

40\. CONFIGURATION

====================================================================



Configuration hierarchy:



&#x20;   Defaults

&#x20;       ↓

&#x20;   Configuration Files

&#x20;       ↓

&#x20;   Environment Variables

&#x20;       ↓

&#x20;   Runtime Overrides



Secrets:



&#x20;   NEVER commit to Git.



Examples:



&#x20;   API Keys

&#x20;   Database Passwords

&#x20;   Broker Credentials

&#x20;   Tokens

&#x20;   Encryption Keys



====================================================================

41\. LOGGING

====================================================================



Logging must be structured.



Levels:



&#x20;   DEBUG

&#x20;   INFO

&#x20;   WARNING

&#x20;   ERROR

&#x20;   CRITICAL



Important contextual fields:



&#x20;   timestamp

&#x20;   component

&#x20;   operation

&#x20;   request\_id

&#x20;   event\_id

&#x20;   error

&#x20;   duration



Logs should support debugging distributed workflows.



====================================================================

42\. TESTING

====================================================================



Required test categories:



&#x20;   Unit

&#x20;   Integration

&#x20;   Contract

&#x20;   Pipeline

&#x20;   Engine

&#x20;   Service

&#x20;   End-to-End

&#x20;   Simulation

&#x20;   Architecture

&#x20;   Project Intelligence



Tests are part of implementation.



Tests are not optional documentation.



====================================================================

43\. QUALITY GATE

====================================================================



Before every important commit:



&#x20;   python -m ruff check .



&#x20;   python -m black .



&#x20;   python -m mypy src



&#x20;   python -m pytest



All must pass.



Expected result:



&#x20;   Ruff       GREEN

&#x20;   Black      GREEN

&#x20;   Mypy       GREEN

&#x20;   Pytest     GREEN



If any fails:



&#x20;   Fix

&#x20;   Re-run

&#x20;   Repeat



Do not commit known failures.



====================================================================

44\. DEPENDENCY MANAGEMENT

====================================================================



Python environment:



&#x20;   .venv



Virtual environment must not be committed.



Python cache must not be committed.



Generated runtime cache must not be committed unless explicitly

required as project state.



Dependencies must be explicitly declared.



Do not install random packages merely to solve implementation problems.



Every dependency must have a reason.



====================================================================

45\. GITIGNORE

====================================================================



Must exclude at minimum:



&#x20;   .venv/

&#x20;   \_\_pycache\_\_/

&#x20;   \*.pyc

&#x20;   \*.pyo

&#x20;   .pytest\_cache/

&#x20;   .mypy\_cache/

&#x20;   .ruff\_cache/

&#x20;   .coverage

&#x20;   htmlcov/

&#x20;   .env

&#x20;   .env.\*

&#x20;   IDE metadata

&#x20;   OS metadata



Do not exclude important source code.



Do not exclude architecture documentation.



Do not exclude intentional project state.



====================================================================

46\. NAMING

====================================================================



Python filenames should use:



&#x20;   snake\_case.py



Classes:



&#x20;   PascalCase



Functions:



&#x20;   snake\_case



Variables:



&#x20;   snake\_case



Constants:



&#x20;   UPPER\_SNAKE\_CASE



Avoid:



&#x20;   timefram.py

&#x20;   oerder.py



Prefer:



&#x20;   timeframe.py

&#x20;   order.py



Renaming must account for imports and Git history.



====================================================================

47\. ERROR HANDLING

====================================================================



Errors must be explicit.



Do not silently swallow exceptions.



Avoid:



&#x20;   except Exception:

&#x20;       pass



Errors should be:



&#x20;   logged

&#x20;   classified

&#x20;   propagated or handled intentionally



Domain errors should be represented independently of infrastructure.



====================================================================

48\. TYPE SYSTEM

====================================================================



Use type annotations.



Public APIs should be strongly typed.



Avoid unnecessary:



&#x20;   Any



Avoid type-ignore unless justified.



Mypy must remain green.



====================================================================

49\. DOCUMENTATION

====================================================================



Documentation must evolve with implementation.



Important documents:



&#x20;   README.md

&#x20;   Architecture.md

&#x20;   ARCHITECTURE\_HANDOFF

&#x20;   DATA\_FLOW\_DOCUMENTATION

&#x20;   DEVELOPMENT\_RULES

&#x20;   EXECUTION\_GUIDE

&#x20;   Handoff

&#x20;   ProjectSnapshot

&#x20;   ChatGPT\_Context

&#x20;   Roadmap

&#x20;   Decisions

&#x20;   Todo



Documentation must not describe imaginary features as implemented.



====================================================================

50\. AGENT DEVELOPMENT PROTOCOL

====================================================================



Any Coding Agent must follow this protocol.



STEP 1:



&#x20;   Read project\_state/generated/ChatGPT\_Context.md



STEP 2:



&#x20;   Read Architecture documentation.



STEP 3:



&#x20;   Read current Roadmap.



STEP 4:



&#x20;   Read Decisions.



STEP 5:



&#x20;   Inspect actual workspace.



STEP 6:



&#x20;   Inspect tests.



STEP 7:



&#x20;   Identify current implementation phase.



STEP 8:



&#x20;   Define exact scope.



STEP 9:



&#x20;   Implement.



STEP 10:



&#x20;   Run tests.



STEP 11:



&#x20;   Run Ruff.



STEP 12:



&#x20;   Run Black.



STEP 13:



&#x20;   Run Mypy.



STEP 14:



&#x20;   Fix all failures.



STEP 15:



&#x20;   Update Project Intelligence state.



STEP 16:



&#x20;   Commit.



STEP 17:



&#x20;   Continue to next approved task.



====================================================================

51\. AGENT OBSERVATION REQUIREMENT

====================================================================



Agent must have two conceptual capabilities:



&#x20;   BRAIN

&#x20;       Reasoning / LLM



&#x20;   EYES

&#x20;       Workspace observation



Brain without Eyes is incomplete.



Agent must be able to inspect:



&#x20;   Files

&#x20;   Directories

&#x20;   Source

&#x20;   Tests

&#x20;   Git

&#x20;   Configuration

&#x20;   Project State



Agent must not generate architecture from conversation context alone

when actual workspace information is available.



====================================================================

52\. AGENT QUALITY GATE

====================================================================



Future Agent Platform must be able to automatically:



&#x20;   run pytest

&#x20;   run ruff

&#x20;   run black

&#x20;   run mypy



and when failures occur:



&#x20;   inspect failure

&#x20;   determine cause

&#x20;   modify code

&#x20;   re-run checks



until:



&#x20;   Quality Gate = GREEN



provided the task and retry policy permit it.



====================================================================

53\. DEVELOPMENT LOOP

====================================================================



Every implementation task:



&#x20;   Understand

&#x20;       ↓

&#x20;   Observe

&#x20;       ↓

&#x20;   Plan

&#x20;       ↓

&#x20;   Implement

&#x20;       ↓

&#x20;   Test

&#x20;       ↓

&#x20;   Analyze Failures

&#x20;       ↓

&#x20;   Fix

&#x20;       ↓

&#x20;   Verify

&#x20;       ↓

&#x20;   Update State

&#x20;       ↓

&#x20;   Commit



====================================================================

54\. ARCHITECTURE VIOLATION DETECTION

====================================================================



Project Intelligence should eventually detect:



&#x20;   Domain → Infrastructure imports



&#x20;   Domain → GUI imports



&#x20;   Domain → Database imports



&#x20;   Circular dependencies



&#x20;   Unused modules



&#x20;   Dead code



&#x20;   Missing tests



&#x20;   Missing type annotations



&#x20;   Broken package boundaries



&#x20;   Unexpected dependency direction



&#x20;   Stale documentation



&#x20;   TODO accumulation



====================================================================

55\. PERFORMANCE

====================================================================



Performance must not be optimized prematurely.



Priority:



&#x20;   Correctness

&#x20;       ↓

&#x20;   Architecture

&#x20;       ↓

&#x20;   Testability

&#x20;       ↓

&#x20;   Observability

&#x20;       ↓

&#x20;   Performance



When optimization is needed:



&#x20;   Measure

&#x20;   Identify bottleneck

&#x20;   Optimize

&#x20;   Benchmark

&#x20;   Test



Never optimize based on assumption alone.



====================================================================

56\. SECURITY

====================================================================



Security requirements include:



&#x20;   No secrets in source

&#x20;   No credentials in Git

&#x20;   Input validation

&#x20;   Secure configuration

&#x20;   Database credential protection

&#x20;   API authentication

&#x20;   Authorization

&#x20;   Audit logging

&#x20;   Safe plugin loading

&#x20;   Safe external execution

&#x20;   Safe file access

&#x20;   Model artifact validation



Project Intelligence must not execute arbitrary untrusted code while

scanning a workspace.



====================================================================

57\. DATA INTEGRITY

====================================================================



Trading systems require strong data integrity.



Critical records:



&#x20;   Orders

&#x20;   Trades

&#x20;   Positions

&#x20;   Balances

&#x20;   Portfolio

&#x20;   Market Data



must be traceable.



Historical records must not be silently overwritten.



====================================================================

58\. TRADING SAFETY

====================================================================



Trading execution must enforce:



&#x20;   Signal validation

&#x20;   Risk validation

&#x20;   Position constraints

&#x20;   Exposure constraints

&#x20;   Order validation

&#x20;   Broker constraints



No strategy may bypass Risk Engine.



No AI model may directly execute a trade.



Correct conceptual flow:



&#x20;   AI

&#x20;     ↓

&#x20;   Prediction

&#x20;     ↓

&#x20;   Signal

&#x20;     ↓

&#x20;   Strategy

&#x20;     ↓

&#x20;   Risk

&#x20;     ↓

&#x20;   Order

&#x20;     ↓

&#x20;   Execution



====================================================================

59\. AI SAFETY

====================================================================



AI output is not automatically truth.



AI output must be treated as:



&#x20;   Prediction / Signal / Recommendation



and must pass deterministic validation and risk constraints.



AI must not bypass:



&#x20;   Risk

&#x20;   Validation

&#x20;   Trading Rules



====================================================================

60\. SIMULATION SAFETY

====================================================================



Simulation must never accidentally execute real broker orders.



Simulation environment must have explicit execution mode.



Examples:



&#x20;   SIMULATION

&#x20;   PAPER

&#x20;   LIVE



LIVE mode must require explicit configuration.



====================================================================

61\. CONFIGURATION MODES

====================================================================



Recommended conceptual environments:



&#x20;   development

&#x20;   testing

&#x20;   simulation

&#x20;   paper

&#x20;   production



Each environment must have explicit configuration.



Do not infer LIVE mode accidentally.



====================================================================

62\. DEPLOYMENT

====================================================================



Deployment architecture must eventually support:



&#x20;   Application

&#x20;   Database

&#x20;   Data Storage

&#x20;   Model Registry

&#x20;   Configuration

&#x20;   Logging

&#x20;   Monitoring

&#x20;   Backup

&#x20;   Recovery



Deployment must be reproducible.



====================================================================

63\. BACKUP

====================================================================



Important persistent information must have backup strategy:



&#x20;   Database

&#x20;   Models

&#x20;   Datasets

&#x20;   Project State

&#x20;   Configuration metadata

&#x20;   Audit records



Recovery must be tested.



====================================================================

64\. PROJECT GENERATOR

====================================================================



PowerShell generator should eventually create:



&#x20;   Repository

&#x20;   Source tree

&#x20;   Test tree

&#x20;   Configuration

&#x20;   Documentation

&#x20;   Git setup

&#x20;   Environment structure



Generator must generate architecture-compliant structure.



====================================================================

65\. ARCHITECTURE FREEZE

====================================================================



When all required components are production-ready:



&#x20;   Architecture v1.0



is frozen.



After freeze:



&#x20;   No casual architectural changes.



Any architectural change requires:



&#x20;   ADR

&#x20;   Impact Analysis

&#x20;   Migration Plan

&#x20;   Tests

&#x20;   Documentation



====================================================================

66\. CURRENT PROJECT STRUCTURE

====================================================================



Current workspace contains conceptually:



&#x20;   ARCHITECTURE/

&#x20;   CONFIGS/

&#x20;   DATASETS/

&#x20;       Features/

&#x20;       Processed/

&#x20;       Raw/

&#x20;   DOCS/

&#x20;   LEGACY/

&#x20;   SCRIPTS/

&#x20;   SRC/

&#x20;   TESTS/



and:



&#x20;   .venv/



The current source root is:



&#x20;   src/ShadBot/



Current major packages include:



&#x20;   core/

&#x20;   domain/

&#x20;   application/



and the Project Intelligence package:



&#x20;   project/



====================================================================

67\. CURRENT PROJECT INTELLIGENCE TREE

====================================================================



&#x20;   src/ShadBot/project/

&#x20;       core/

&#x20;       models/

&#x20;       builders/

&#x20;       exporters/

&#x20;       runtime/



&#x20;   project\_state/

&#x20;       generated/

&#x20;       archive/



This structure is the beginning of the self-awareness system.



It is NOT the final implementation.



====================================================================

68\. WHAT MUST NOT BE DONE

====================================================================



DO NOT:



&#x20;   redesign architecture randomly



&#x20;   create duplicate domains



&#x20;   create duplicate engines



&#x20;   put business logic in main.py



&#x20;   put business logic in GUI



&#x20;   put business logic in database models



&#x20;   allow AI to bypass Risk



&#x20;   allow Strategy to directly access broker implementation



&#x20;   create circular dependencies



&#x20;   use global mutable state without architectural justification



&#x20;   silently catch exceptions



&#x20;   commit secrets



&#x20;   commit virtual environments



&#x20;   skip tests



&#x20;   skip type checking



&#x20;   skip linting



&#x20;   create fake implementations



&#x20;   create unnecessary abstractions



&#x20;   introduce dependencies without justification



&#x20;   rewrite working subsystems without reason



====================================================================

69\. WHAT SHOULD HAPPEN WHEN A BUG IS FOUND

====================================================================



Process:



&#x20;   Reproduce

&#x20;       ↓

&#x20;   Identify Layer

&#x20;       ↓

&#x20;   Identify Root Cause

&#x20;       ↓

&#x20;   Write / Update Test

&#x20;       ↓

&#x20;   Fix

&#x20;       ↓

&#x20;   Run Full Quality Gate

&#x20;       ↓

&#x20;   Update Documentation if needed

&#x20;       ↓

&#x20;   Commit



====================================================================

70\. WHAT SHOULD HAPPEN WHEN ARCHITECTURE IS WRONG

====================================================================



Do NOT immediately rewrite.



Process:



&#x20;   Detect

&#x20;       ↓

&#x20;   Verify

&#x20;       ↓

&#x20;   Analyze Impact

&#x20;       ↓

&#x20;   Create Decision

&#x20;       ↓

&#x20;   Define Migration

&#x20;       ↓

&#x20;   Implement

&#x20;       ↓

&#x20;   Test

&#x20;       ↓

&#x20;   Update Documentation

&#x20;       ↓

&#x20;   Commit



====================================================================

71\. CURRENT IMPLEMENTATION PHILOSOPHY

====================================================================



The project is being built incrementally.



Do not attempt to implement the entire platform in one giant commit.



Correct strategy:



&#x20;   Small coherent subsystem

&#x20;       ↓

&#x20;   Tests

&#x20;       ↓

&#x20;   Integration

&#x20;       ↓

&#x20;   Quality Gate

&#x20;       ↓

&#x20;   Commit



Then continue.



====================================================================

72\. PHASE COMPLETION CONTRACT

====================================================================



A Phase is COMPLETE only when:



&#x20;   Architecture implemented

&#x20;   Contracts implemented

&#x20;   Models implemented

&#x20;   Dependencies verified

&#x20;   Integration completed

&#x20;   Tests written

&#x20;   Ruff passed

&#x20;   Black passed

&#x20;   Mypy passed

&#x20;   Pytest passed

&#x20;   Runtime verified

&#x20;   Documentation updated

&#x20;   Project State updated

&#x20;   Git commit created



====================================================================

73\. PROJECT STATE UPDATE CONTRACT

====================================================================



After every significant change update:



&#x20;   ProjectSnapshot

&#x20;   ChatGPT\_Context

&#x20;   Architecture

&#x20;   Roadmap

&#x20;   Decisions

&#x20;   Todo

&#x20;   Statistics

&#x20;   DependencyGraph



Not every tiny code edit requires a massive documentation rewrite.



But every meaningful architectural or subsystem change must be reflected.



====================================================================

74\. NEW CHAT RECOVERY PROCEDURE

====================================================================



When previous chat is unavailable:



&#x20;   1. Start new ChatGPT session.



&#x20;   2. Provide:



&#x20;       Handoff



&#x20;   3. Provide:



&#x20;       project\_state/generated/ChatGPT\_Context.md



&#x20;   4. If architecture context is required:



&#x20;       project\_state/generated/Architecture.md



&#x20;   5. If roadmap context is required:



&#x20;       project\_state/generated/Roadmap.md



&#x20;   6. If decision history is required:



&#x20;       project\_state/generated/Decisions.md



&#x20;   7. Tell the Agent:



&#x20;       "Continue from current project state.

&#x20;        Do not redesign existing architecture.

&#x20;        Inspect the workspace before modifying anything."



====================================================================

75\. CONTEXT PRIORITY

====================================================================



When reconstructing project knowledge:



&#x20;   1. Actual source code

&#x20;   2. Actual tests

&#x20;   3. Current Project Snapshot

&#x20;   4. Current Project Context

&#x20;   5. Architecture decisions

&#x20;   6. Roadmap

&#x20;   7. Handoff

&#x20;   8. Historical documentation



Actual workspace is the source of truth for implementation state.



Architecture documents are the source of truth for intended design.



====================================================================

76\. FINAL PRODUCT

====================================================================



The final ShadBot platform should provide:



&#x20;   Market Data

&#x20;   Data Processing

&#x20;   Feature Engineering

&#x20;   AI Models

&#x20;   Prediction

&#x20;   Signal Generation

&#x20;   Strategy Execution

&#x20;   Risk Management

&#x20;   Order Management

&#x20;   Trade Management

&#x20;   Portfolio Management

&#x20;   Backtesting

&#x20;   Simulation

&#x20;   Optimization

&#x20;   Self Learning

&#x20;   Project Intelligence

&#x20;   GUI

&#x20;   Persistence

&#x20;   Configuration

&#x20;   Logging

&#x20;   Testing

&#x20;   Deployment



====================================================================

77\. FINAL SYSTEM FLOW

====================================================================



MARKET SIDE:



&#x20;   External Market

&#x20;       ↓

&#x20;   Data Provider

&#x20;       ↓

&#x20;   Data Platform

&#x20;       ↓

&#x20;   Storage

&#x20;       ↓

&#x20;   Feature Platform

&#x20;       ↓

&#x20;   AI Platform

&#x20;       ↓

&#x20;   Prediction

&#x20;       ↓

&#x20;   Signal

&#x20;       ↓

&#x20;   Strategy

&#x20;       ↓

&#x20;   Risk

&#x20;       ↓

&#x20;   Order

&#x20;       ↓

&#x20;   Execution

&#x20;       ↓

&#x20;   Trade

&#x20;       ↓

&#x20;   Position

&#x20;       ↓

&#x20;   Portfolio



PROJECT INTELLIGENCE SIDE:



&#x20;   Workspace

&#x20;       ↓

&#x20;   Scanner

&#x20;       ↓

&#x20;   Snapshot

&#x20;       ↓

&#x20;   Analysis

&#x20;       ↓

&#x20;   Evolution

&#x20;       ↓

&#x20;   Insight

&#x20;       ↓

&#x20;   Recommendation

&#x20;       ↓

&#x20;   Decision

&#x20;       ↓

&#x20;   Project State

&#x20;       ↓

&#x20;   ChatGPT Context



====================================================================

78\. FINAL ENTERPRISE LOOP

====================================================================



&#x20;   Data

&#x20;     ↓

&#x20;   Features

&#x20;     ↓

&#x20;   AI

&#x20;     ↓

&#x20;   Decision

&#x20;     ↓

&#x20;   Trading

&#x20;     ↓

&#x20;   Portfolio

&#x20;     ↓

&#x20;   Performance

&#x20;     ↓

&#x20;   Learning

&#x20;     ↓

&#x20;   Optimization

&#x20;     ↓

&#x20;   New Model

&#x20;     ↓

&#x20;   Validation

&#x20;     ↓

&#x20;   Production



Parallel:



&#x20;   Code

&#x20;     ↓

&#x20;   Project Intelligence

&#x20;     ↓

&#x20;   Snapshot

&#x20;     ↓

&#x20;   Analysis

&#x20;     ↓

&#x20;   Insight

&#x20;     ↓

&#x20;   Recommendation

&#x20;     ↓

&#x20;   Decision

&#x20;     ↓

&#x20;   Updated Project State

&#x20;     ↓

&#x20;   Better Development



====================================================================

79\. ABSOLUTE DEVELOPMENT RULE

====================================================================



The project must always move forward in this order:



&#x20;   UNDERSTAND

&#x20;       ↓

&#x20;   OBSERVE

&#x20;       ↓

&#x20;   DESIGN

&#x20;       ↓

&#x20;   IMPLEMENT

&#x20;       ↓

&#x20;   TEST

&#x20;       ↓

&#x20;   VERIFY

&#x20;       ↓

&#x20;   DOCUMENT

&#x20;       ↓

&#x20;   COMMIT

&#x20;       ↓

&#x20;   NEXT



Never:



&#x20;   GUESS

&#x20;       ↓

&#x20;   CODE

&#x20;       ↓

&#x20;   BREAK

&#x20;       ↓

&#x20;   PATCH RANDOMLY



====================================================================

80\. FINAL HANDOFF MESSAGE

====================================================================



If a new Developer or Agent reads this document, the required

understanding is:



&#x20;   ShadBot is an Enterprise AI Trading Platform.



&#x20;   The architecture has already been designed.



&#x20;   Do not redesign it casually.



&#x20;   The project uses Clean Architecture, DDD, Dependency Inversion,

&#x20;   Pipeline Architecture, Engine Architecture, Service Architecture,

&#x20;   Plugin Architecture and Event-Driven Architecture.



&#x20;   The platform contains Trading, Portfolio, AI, Data, Feature,

&#x20;   Simulation, Self Learning and Project Intelligence subsystems.



&#x20;   Project Intelligence is responsible for making ShadBot aware of

&#x20;   its own source code, architecture, dependencies, roadmap,

&#x20;   decisions and evolution.



&#x20;   The implementation has already started.



&#x20;   Core Foundation exists.



&#x20;   Domain Core exists.



&#x20;   Application Runtime exists.



&#x20;   Project Intelligence skeleton exists.



&#x20;   Continue implementation incrementally.



&#x20;   Inspect the real workspace before modifying anything.



&#x20;   Never assume.



&#x20;   Never invent existing code.



&#x20;   Never create duplicate architecture.



&#x20;   Never bypass Domain boundaries.



&#x20;   Never bypass Risk in trading.



&#x20;   Never commit failing code.



&#x20;   Every meaningful change must pass:



&#x20;       Ruff

&#x20;       Black

&#x20;       Mypy

&#x20;       Pytest



&#x20;   Every meaningful milestone must update Project State.



&#x20;   Every completed milestone must be committed to Git.



&#x20;   The final goal is a production-grade ShadBot Enterprise AI

&#x20;   Trading Platform, not a prototype or demonstration project.



====================================================================

END OF HANDOFF

====================================================================

