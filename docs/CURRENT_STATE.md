> ⚠️ **LIVE STATUS POINTER — added 2026-08-16**
>
> This document is a **frozen architecture document** (Phase 26 freeze).
> It describes the *intended* design and is deliberately left unchanged.
>
> For the **actual implementation status** — which phases are built, which
> are partial, and which are not started — see:
>
> - **`docs/IMPLEMENTATION_STATUS.md`** — phase-by-phase audit against real code
> - **`docs/WORKLOG.md`** — chronological log of every change made
>
> Per `AGENTOPERATINGRULE.md`: the source code is the authoritative
> implementation reality; this file is the authoritative design intent.

---

====================================================================

SHADBOTTRADER

CURRENT\_STATE

====================================================================



DOCUMENT TYPE:

&#x20;   Canonical Project State Document



PROJECT:

&#x20;   ShadBotTrader



PROJECT TYPE:

&#x20;   Enterprise AI Trading Platform



PURPOSE:

&#x20;   This document describes the current known state of the

&#x20;   ShadBotTrader project.



&#x20;   It is intended to allow a new developer, coding agent, AI agent,

&#x20;   or future ChatGPT session to understand exactly:



&#x20;       where the project is

&#x20;       what architecture has been defined

&#x20;       what has been implemented

&#x20;       what has not been implemented

&#x20;       what decisions have been made

&#x20;       what must NOT be redesigned

&#x20;       what must be implemented next

&#x20;       what remains in the roadmap

&#x20;       what the current repository state is

&#x20;       what the intended final system looks like



&#x20;   This document is NOT a replacement for the complete architecture

&#x20;   documentation.



&#x20;   It is the operational state of the project.



====================================================================

1\. PROJECT IDENTITY

====================================================================



PROJECT NAME:



&#x20;   ShadBotTrader



IMPORTANT:



&#x20;   The project MUST be referred to as:



&#x20;       ShadBotTrader



&#x20;   Do NOT rename the project to:



&#x20;       ShadBotTrader AI

&#x20;       ShadTrader

&#x20;       TradingBot

&#x20;       another custom name



unless an explicit architectural decision is made.



====================================================================

2\. PROJECT OBJECTIVE

====================================================================



ShadBotTrader is intended to become an enterprise-grade,

AI-assisted trading platform capable of:



&#x20;   market data ingestion

&#x20;   market data normalization

&#x20;   market data storage

&#x20;   feature engineering

&#x20;   AI/ML prediction

&#x20;   signal generation

&#x20;   strategy execution

&#x20;   risk management

&#x20;   order generation

&#x20;   order validation

&#x20;   simulated execution

&#x20;   paper execution

&#x20;   live execution

&#x20;   portfolio management

&#x20;   position management

&#x20;   trade management

&#x20;   backtesting

&#x20;   simulation

&#x20;   optimization

&#x20;   replay

&#x20;   performance analysis

&#x20;   self-learning

&#x20;   project intelligence

&#x20;   configuration

&#x20;   event-driven communication

&#x20;   observability

&#x20;   testing

&#x20;   GUI/API interaction

&#x20;   deployment



The final platform is intended to support:



&#x20;   research

&#x20;   experimentation

&#x20;   simulation

&#x20;   backtesting

&#x20;   paper trading

&#x20;   controlled live trading



====================================================================

3\. CURRENT PROJECT MATURITY

====================================================================



CURRENT MATURITY:



&#x20;   ARCHITECTURE DESIGN COMPLETE — IMPLEMENTATION NOT STARTED



The project is NOT yet a complete trading platform.



The current implementation is a foundation.



Most major trading, AI, portfolio, simulation, self-learning,

project-intelligence, GUI, persistence, deployment and production

components remain to be implemented.



The project MUST NOT be represented as production-ready trading

software at this stage.



====================================================================

4\. ARCHITECTURAL PHILOSOPHY

====================================================================



Primary architecture:



&#x20;   Clean Architecture



Combined with:



&#x20;   Domain-Driven Design

&#x20;   Dependency Inversion

&#x20;   Explicit Contracts

&#x20;   Modular Architecture

&#x20;   Event-Oriented Architecture

&#x20;   Plugin Architecture



Primary objective:



&#x20;   Keep the Domain independent from frameworks,

&#x20;   databases, brokers, external APIs and infrastructure.



====================================================================

5\. ARCHITECTURAL PRINCIPLE

====================================================================



The system follows:



&#x20;   inward dependency direction



Conceptually:



&#x20;   Interface

&#x20;       ↓

&#x20;   Application

&#x20;       ↓

&#x20;   Domain



Infrastructure implements contracts exposed by the inner layers.



Therefore:



&#x20;   Domain

&#x20;       MUST NOT depend on Infrastructure.



&#x20;   Domain

&#x20;       MUST NOT depend on broker SDKs.



&#x20;   Domain

&#x20;       MUST NOT depend on database implementations.



&#x20;   Application

&#x20;       MUST NOT directly instantiate concrete infrastructure

&#x20;       adapters.



&#x20;   Infrastructure

&#x20;       implements Application contracts.



====================================================================

6\. MASTER ARCHITECTURE ROADMAP

====================================================================



The project architecture was originally designed as a

27-phase architecture roadmap.



The phases are:



&#x20;   PHASE 1

&#x20;       Architecture Principles



&#x20;   PHASE 2

&#x20;       Dependency Rules



&#x20;   PHASE 3

&#x20;       Domain Model



&#x20;   PHASE 4

&#x20;       Project Tree / Structural Architecture



&#x20;   PHASE 5

&#x20;       Framework Design



&#x20;   PHASE 6

&#x20;       Pipeline Design



&#x20;   PHASE 7

&#x20;       Engine Design



&#x20;   PHASE 8

&#x20;       Service Design



&#x20;   PHASE 9

&#x20;       Plugin Architecture



&#x20;   PHASE 10

&#x20;       Event Bus



&#x20;   PHASE 11

&#x20;       Data Platform



&#x20;   PHASE 12

&#x20;       Feature Platform



&#x20;   PHASE 13

&#x20;       AI Platform



&#x20;   PHASE 14

&#x20;       Trading Platform



&#x20;   PHASE 15

&#x20;       Portfolio Platform



&#x20;   PHASE 16

&#x20;       Simulation Platform



&#x20;   PHASE 17

&#x20;       Self-Learning Platform



&#x20;   PHASE 18

&#x20;       Project Intelligence Platform



&#x20;   PHASE 19

&#x20;       GUI Architecture



&#x20;   PHASE 20

&#x20;       SQL Server Schema



&#x20;   PHASE 21

&#x20;       Configuration System



&#x20;   PHASE 22

&#x20;       Logging System



&#x20;   PHASE 23

&#x20;       Testing Architecture



&#x20;   PHASE 24

&#x20;       Deployment Architecture



&#x20;   PHASE 25

&#x20;       PowerShell Project Generator



&#x20;   PHASE 26

&#x20;       Architecture Validation / Integration



&#x20;   PHASE 27

&#x20;       Freeze / Architecture V1.0



Additional implementation phases:



&#x20;   PHASE 28

&#x20;       Foundation Implementation



&#x20;   PHASE 28.x

&#x20;       Incremental implementation milestones



IMPORTANT:



&#x20;   Phase 28.x implementation is NOT a redesign of Phases 1-27.



&#x20;   Phase 28 exists to implement the architecture.



====================================================================

7\. ARCHITECTURE STATUS

====================================================================



PHASE 1:

&#x20;   Designed



PHASE 2:

&#x20;   Designed



PHASE 3:

&#x20;   Designed



PHASE 4:

&#x20;   Designed



PHASE 5:

&#x20;   Designed



PHASE 6:

&#x20;   Designed



PHASE 7:

&#x20;   Designed



PHASE 8:

&#x20;   Designed



PHASE 9:

&#x20;   Designed



PHASE 10:

&#x20;   Designed



PHASE 11:

&#x20;   Designed



PHASE 12:

&#x20;   Designed



PHASE 13:

&#x20;   Designed



PHASE 14:

&#x20;   Designed



PHASE 15:

&#x20;   Designed



PHASE 16:

&#x20;   Designed



PHASE 17:

&#x20;   Designed



PHASE 18:

&#x20;   Designed



PHASE 19:

&#x20;   Designed



PHASE 20:

&#x20;   Designed



PHASE 21:

&#x20;   Designed



PHASE 22:

&#x20;   Designed



PHASE 23:

&#x20;   Designed



PHASE 24:

&#x20;   Designed



PHASE 25:

&#x20;   Designed



PHASE 26:

&#x20;   Designed



PHASE 27:

&#x20;   Designed / Architecture baseline



PHASE 28:

&#x20;   Implementation started



====================================================================

8\. IMPORTANT ARCHITECTURAL STATUS RULE

====================================================================



The architecture must NOT be redesigned from scratch simply because

implementation is incomplete.



If implementation reveals a genuine architectural conflict:



&#x20;   identify conflict

&#x20;   document conflict

&#x20;   propose change

&#x20;   validate impact

&#x20;   update architecture

&#x20;   record decision



Do NOT silently redesign the architecture.



====================================================================

9\. CURRENT REPOSITORY STATE

====================================================================



Repository:



&#x20;   ShadBotTrader



Current development branch:



&#x20;   main



Git is already initialized.



The project has an initial repository history.



Git MUST remain enabled.



Every significant implementation milestone should be committed.



====================================================================

10\. CURRENT PROJECT STRUCTURE

====================================================================



The project began with a basic structure containing concepts such as:



&#x20;   architecture/

&#x20;   configs/

&#x20;   datasets/

&#x20;       Raw/

&#x20;       Processed/

&#x20;       Features/

&#x20;   docs/

&#x20;   legacy/

&#x20;   scripts/

&#x20;   src/

&#x20;   tests/



The Python source architecture has subsequently been evolving toward

the implemented Clean Architecture structure.



The implementation agent MUST inspect the CURRENT filesystem before

creating or moving files.



Do NOT assume that an old tree is still identical to the current tree.



====================================================================

11\. CURRENT CORE IMPLEMENTATION

====================================================================



The project currently contains a foundational Core layer.



Implemented conceptual components include:



&#x20;   BaseEntity

&#x20;   BaseValueObject

&#x20;   BaseAggregateRoot

&#x20;   BaseRunner

&#x20;   Bootstrap

&#x20;   Logger

&#x20;   Result



These represent foundational architectural primitives.



They MUST be reused when appropriate.



Do NOT create duplicate foundational abstractions without a reason.



====================================================================

12\. CORE INFRASTRUCTURE — PLANNED (NOT YET IMPLEMENTED)

====================================================================



The following foundation components are PLANNED for Phase 28

(not yet implemented):



&#x20;   Dependency Container



&#x20;   Event abstraction



&#x20;   Event Bus



&#x20;   Lifecycle Manager



&#x20;   Plugin base abstraction



&#x20;   Base Service abstraction



Conceptual locations:



&#x20;   src/ShadBotTrader/core/dependency/container.py



&#x20;   src/ShadBotTrader/core/events/event.py



&#x20;   src/ShadBotTrader/core/events/eventBus.py



&#x20;   src/ShadBotTrader/core/lifecycle/lifecycleManager.py



&#x20;   src/ShadBotTrader/core/plugins/plugin.py



&#x20;   src/ShadBotTrader/core/services/baseService.py



These are part of the foundation.



====================================================================

13\. APPLICATION LAYER — PLANNED (NOT YET IMPLEMENTED)

====================================================================



The Application Runtime Layer has NOT been implemented yet (planned in Phase 28).



Conceptual files:



&#x20;   src/ShadBotTrader/application/app.py



&#x20;   src/ShadBotTrader/application/applicationState.py



&#x20;   src/ShadBotTrader/application/bootstrap.py



&#x20;   src/ShadBotTrader/application/runtime.py



&#x20;   src/ShadBotTrader/application/serviceRegistry.py



&#x20;   src/ShadBotTrader/application/shutdown.py



&#x20;   src/ShadBotTrader/application/startup.py



The Application layer is responsible for:



&#x20;   application lifecycle

&#x20;   startup

&#x20;   shutdown

&#x20;   service registration

&#x20;   runtime orchestration

&#x20;   application state



The Application layer MUST NOT become a replacement for Domain.



====================================================================

14\. DOMAIN — PLANNED (NOT YET IMPLEMENTED)

====================================================================



The Domain Core has NOT been implemented yet (planned in Phase 28).



Current conceptual Domain components include:



&#x20;   Common

&#x20;       Entity

&#x20;       Value Object



&#x20;   Market

&#x20;       Symbol

&#x20;       TimeFrame

&#x20;       Candle



&#x20;   Portfolio

&#x20;       Account

&#x20;       Balance



&#x20;   Prediction

&#x20;       Prediction

&#x20;       Signal



&#x20;   Risk

&#x20;       RiskModel



&#x20;   Trading

&#x20;       Order

&#x20;       Position

&#x20;       Trade



These represent the current Domain baseline.



====================================================================

15\. DOMAIN STATUS

====================================================================



IMPORTANT:



&#x20;   The current Domain implementation is foundational.



It is NOT yet the final complete Domain Model.



The following remain to be expanded:



&#x20;   aggregates

&#x20;   aggregate boundaries

&#x20;   invariants

&#x20;   domain services

&#x20;   domain events

&#x20;   lifecycle state machines

&#x20;   richer trading rules

&#x20;   portfolio rules

&#x20;   risk rules

&#x20;   execution models

&#x20;   financial precision rules

&#x20;   domain-level validation



Do NOT treat the current minimal entities as the final platform.



====================================================================

16\. CURRENT ENGINE STRUCTURE

====================================================================



The initial project structure includes engine concepts such as:



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



These engines represent architectural responsibilities.



They are NOT permission to place all business logic inside giant

engine classes.



Engine responsibilities must remain separated according to the

architecture.



====================================================================

17\. PROJECT INTELLIGENCE DIRECTION

====================================================================



ShadBotTrader is intended to eventually understand its own project

state.



The Project Intelligence system is intended to inspect:



&#x20;   filesystem

&#x20;   Python source

&#x20;   AST

&#x20;   Git

&#x20;   configuration

&#x20;   dependencies

&#x20;   packages

&#x20;   statistics

&#x20;   roadmap

&#x20;   decisions

&#x20;   TODOs

&#x20;   architecture

&#x20;   implementation state



It should generate:



&#x20;   Project Snapshot

&#x20;   Project Context

&#x20;   Architecture State

&#x20;   Roadmap

&#x20;   Decisions

&#x20;   TODO

&#x20;   Statistics

&#x20;   Dependency Graph

&#x20;   AI Handoff Package



====================================================================

18\. PROJECT INTELLIGENCE STRUCTURE

====================================================================



The intended Project Intelligence structure includes:



&#x20;   src/ShadBotTrader/project/



&#x20;       core/



&#x20;           projectScanner

&#x20;           astScanner

&#x20;           gitScanner

&#x20;           configScanner

&#x20;           dependencyScanner

&#x20;           packageScanner

&#x20;           statisticsScanner

&#x20;           roadmapScanner

&#x20;           decisionScanner

&#x20;           todoScanner



&#x20;       models/



&#x20;           projectSnapshot

&#x20;           projectStatistics

&#x20;           projectContext

&#x20;           roadmap

&#x20;           decision



&#x20;       builders/



&#x20;           snapshotBuilder

&#x20;           contextBuilder

&#x20;           roadmapBuilder

&#x20;           statisticsBuilder

&#x20;           documentationBuilder



&#x20;       exporters/



&#x20;           markdownExporter

&#x20;           jsonExporter

&#x20;           htmlExporter

&#x20;           pdfExporter



&#x20;       runtime/



&#x20;           intelligenceRuntime



====================================================================

19\. PROJECT STATE OUTPUT

====================================================================



The intended generated state directory is:



&#x20;   project\_state/



&#x20;       generated/



&#x20;       archive/



Generated documents include:



&#x20;   ProjectSnapshot.md

&#x20;   ProjectSnapshot.json

&#x20;   ChatGPT\_Context.md

&#x20;   Architecture.md

&#x20;   Roadmap.md

&#x20;   Decisions.md

&#x20;   Todo.md

&#x20;   Statistics.json

&#x20;   DependencyGraph.json



These are intended to become machine-readable project memory.



====================================================================

20\. PROJECT INTELLIGENCE FUTURE OBJECTIVE

====================================================================



The final objective is:



&#x20;   ShadBotTrader

&#x20;       ↓

&#x20;   scans itself

&#x20;       ↓

&#x20;   understands current implementation

&#x20;       ↓

&#x20;   compares implementation with architecture

&#x20;       ↓

&#x20;   identifies completed work

&#x20;       ↓

&#x20;   identifies missing work

&#x20;       ↓

&#x20;   identifies changes

&#x20;       ↓

&#x20;   updates project state

&#x20;       ↓

&#x20;   generates AI handoff

&#x20;       ↓

&#x20;   coding agent consumes handoff

&#x20;       ↓

&#x20;   coding agent continues implementation



This is a core long-term capability.



====================================================================

21\. DOCUMENTATION PACKAGE

====================================================================



The project documentation package includes:



&#x20;   README



&#x20;   ARCHITECTURE\_HANDOFF



&#x20;   DATA\_FLOW\_DOCUMENTATION



&#x20;   DEVELOPMENT\_RULES



&#x20;   EXECUTION\_GUIDE



&#x20;   Handoff



&#x20;   SHADBOTTRADER\_MASTER\_IMPLEMENTATION\_SPECIFICATION



&#x20;   API\_AND\_CONTRACT\_SPECIFICATION



&#x20;   CURRENT\_STATE



Additional recommended specifications include:



&#x20;   DOMAIN\_MODEL\_SPECIFICATION



&#x20;   DATABASE\_SCHEMA\_SPECIFICATION



&#x20;   TESTING\_SPECIFICATION



====================================================================

22\. API CONTRACT STATUS

====================================================================



The API and contract architecture has been specified.



Important contracts include:



&#x20;   MarketDataProvider



&#x20;   MarketDataRepository



&#x20;   FeatureCalculator



&#x20;   Strategy



&#x20;   StrategyRegistry



&#x20;   PredictionProvider



&#x20;   RiskEngine



&#x20;   RiskRule



&#x20;   OrderFactory



&#x20;   OrderValidator



&#x20;   OrderExecutor



&#x20;   PositionService



&#x20;   PortfolioService



&#x20;   EventBus



&#x20;   EventHandler



&#x20;   Clock



&#x20;   Repository contracts



&#x20;   UnitOfWork



&#x20;   ConfigurationProvider



&#x20;   LifecycleManager



&#x20;   SimulationEngine



&#x20;   BacktestEngine



&#x20;   MetricsCalculator



These contracts define boundaries.



Concrete implementations may evolve.



The contract boundary must remain stable unless explicitly changed.



====================================================================

23\. CURRENT EXECUTION MODEL

====================================================================



The intended trading flow is:



&#x20;   Market Data

&#x20;       ↓

&#x20;   Validation

&#x20;       ↓

&#x20;   Feature Engineering

&#x20;       ↓

&#x20;   AI Prediction (optional)

&#x20;       ↓

&#x20;   Strategy

&#x20;       ↓

&#x20;   Signal

&#x20;       ↓

&#x20;   Risk

&#x20;       ↓

&#x20;   Order Creation

&#x20;       ↓

&#x20;   Order Validation

&#x20;       ↓

&#x20;   Execution

&#x20;       ↓

&#x20;   Execution Result

&#x20;       ↓

&#x20;   Trade / Position

&#x20;       ↓

&#x20;   Portfolio

&#x20;       ↓

&#x20;   Metrics / Events / Persistence



No stage may bypass mandatory safety boundaries.



====================================================================

24\. RISK GATE

====================================================================



The mandatory safety chain is:



&#x20;   Signal

&#x20;       ↓

&#x20;   Risk Evaluation

&#x20;       ↓

&#x20;   Risk Approval

&#x20;       ↓

&#x20;   Order Validation

&#x20;       ↓

&#x20;   Execution Mode Validation

&#x20;       ↓

&#x20;   Execution



A Signal MUST NOT directly execute an Order.



An AI Prediction MUST NOT directly execute an Order.



A Strategy MUST NOT directly execute an Order.



====================================================================

25\. EXECUTION MODES

====================================================================



The system is intended to support:



&#x20;   SIMULATION

&#x20;   PAPER

&#x20;   LIVE



Default development mode:



&#x20;   SIMULATION



LIVE execution MUST require explicit configuration.



Tests MUST NEVER accidentally execute live orders.



====================================================================

26\. SIMULATION

====================================================================



Simulation is a first-class execution environment.



Simulation must support:



&#x20;   historical data

&#x20;   deterministic clock

&#x20;   simulated fills

&#x20;   configurable fees

&#x20;   configurable slippage

&#x20;   portfolio accounting

&#x20;   position accounting

&#x20;   trade generation

&#x20;   performance metrics



Simulation MUST NOT access live broker credentials.



====================================================================

27\. BACKTESTING

====================================================================



Backtesting is intended to provide:



&#x20;   reproducible historical evaluation

&#x20;   strategy testing

&#x20;   AI model testing

&#x20;   risk testing

&#x20;   portfolio evaluation

&#x20;   metrics

&#x20;   equity curves

&#x20;   drawdown analysis

&#x20;   trade analysis



Backtesting MUST prevent lookahead bias.



====================================================================

28\. AI PLATFORM STATUS

====================================================================



AI/ML is architecturally planned but not yet fully implemented.



Expected responsibilities:



&#x20;   dataset preparation

&#x20;   feature generation

&#x20;   model training

&#x20;   model validation

&#x20;   model registry

&#x20;   prediction

&#x20;   model versioning

&#x20;   experiment tracking

&#x20;   inference

&#x20;   evaluation



AI is a component of the trading system.



AI is NOT the owner of trading execution.



====================================================================

29\. FEATURE PLATFORM STATUS

====================================================================



Feature engineering is architecturally planned.



Expected capabilities:



&#x20;   technical indicators

&#x20;   statistical features

&#x20;   temporal features

&#x20;   market regime features

&#x20;   normalized features

&#x20;   feature versioning

&#x20;   feature validation



Features must respect:



&#x20;   no lookahead

&#x20;   deterministic calculation

&#x20;   versioning

&#x20;   reproducibility



====================================================================

30\. TRADING PLATFORM STATUS

====================================================================



Trading architecture is defined conceptually.



Still required:



&#x20;   complete Order lifecycle

&#x20;   complete execution model

&#x20;   order validation

&#x20;   broker adapters

&#x20;   execution reconciliation

&#x20;   trade lifecycle

&#x20;   position lifecycle

&#x20;   execution events

&#x20;   error handling

&#x20;   idempotency



====================================================================

31\. PORTFOLIO PLATFORM STATUS

====================================================================



Portfolio foundation does NOT exist yet (planned).



Still required:



&#x20;   complete accounting

&#x20;   position aggregation

&#x20;   realized PnL

&#x20;   unrealized PnL

&#x20;   fees

&#x20;   exposure

&#x20;   equity

&#x20;   drawdown

&#x20;   portfolio snapshots

&#x20;   performance analytics



====================================================================

32\. DATA PLATFORM STATUS

====================================================================



Data platform architecture is planned.



Still required:



&#x20;   ingestion

&#x20;   normalization

&#x20;   validation

&#x20;   storage

&#x20;   historical data management

&#x20;   dataset versioning

&#x20;   update pipelines

&#x20;   data quality checks

&#x20;   replay support



====================================================================

33\. NEWS PLATFORM STATUS

====================================================================



News architecture is defined conceptually in the docs only; implementation not started.



Still required:



&#x20;   news providers

&#x20;   ingestion

&#x20;   normalization

&#x20;   storage

&#x20;   sentiment analysis

&#x20;   event extraction

&#x20;   AI integration

&#x20;   correlation with market events



====================================================================

34\. OPTIMIZATION PLATFORM STATUS

====================================================================



Optimization is architecturally planned.



Expected capabilities:



&#x20;   hyperparameter optimization

&#x20;   strategy parameter optimization

&#x20;   model optimization

&#x20;   risk parameter optimization

&#x20;   walk-forward analysis

&#x20;   experiment comparison



Optimization MUST NOT silently introduce data leakage.



====================================================================

35\. SELF-LEARNING PLATFORM STATUS

====================================================================



Self-learning is planned.



Expected responsibilities:



&#x20;   performance analysis

&#x20;   feedback generation

&#x20;   experiment management

&#x20;   model improvement

&#x20;   strategy adaptation

&#x20;   parameter adaptation

&#x20;   learning history



Self-learning MUST NOT bypass risk controls.



====================================================================

36\. GUI STATUS

====================================================================



GUI architecture is planned.



Expected capabilities:



&#x20;   market monitoring

&#x20;   portfolio monitoring

&#x20;   strategy monitoring

&#x20;   AI monitoring

&#x20;   backtest execution

&#x20;   simulation

&#x20;   configuration

&#x20;   logs

&#x20;   alerts

&#x20;   project intelligence



GUI MUST communicate through Application boundaries.



GUI MUST NOT contain Domain business logic.



====================================================================

37\. DATABASE STATUS

====================================================================



Database architecture is planned.



Expected persistence domains include:



&#x20;   market data

&#x20;   features

&#x20;   predictions

&#x20;   signals

&#x20;   orders

&#x20;   executions

&#x20;   trades

&#x20;   positions

&#x20;   portfolios

&#x20;   events

&#x20;   backtests

&#x20;   simulations

&#x20;   experiments

&#x20;   models

&#x20;   configuration

&#x20;   audit records



Database implementation MUST remain behind repository contracts.



====================================================================

38\. CONFIGURATION STATUS

====================================================================



Configuration architecture is planned.



Configuration should be:



&#x20;   typed

&#x20;   validated

&#x20;   environment-aware

&#x20;   centralized

&#x20;   secure



Secrets MUST NOT be committed to Git.



====================================================================

39\. LOGGING STATUS

====================================================================



Logging architecture is planned.



Logging should support:



&#x20;   structured logging

&#x20;   log levels

&#x20;   correlation IDs

&#x20;   component names

&#x20;   error context

&#x20;   lifecycle events

&#x20;   trading events



Logging MUST NOT leak credentials.



====================================================================

40\. TESTING STATUS

====================================================================



Testing architecture is planned.



Required categories:



&#x20;   Unit tests

&#x20;   Integration tests

&#x20;   Contract tests

&#x20;   Architecture tests

&#x20;   Simulation tests

&#x20;   Backtest tests

&#x20;   End-to-End tests

&#x20;   Regression tests



Financial safety behavior must have dedicated tests.



====================================================================

41\. QUALITY GATE

====================================================================



The project uses:



&#x20;   Ruff

&#x20;   Black

&#x20;   Mypy

&#x20;   Pytest



Minimum quality gate:



&#x20;   python -m ruff check .



&#x20;   python -m black .



&#x20;   python -m mypy src



&#x20;   python -m pytest



A milestone is NOT complete until the quality gate is green.



====================================================================

42\. DEVELOPMENT RULE

====================================================================



Every significant implementation step must:



&#x20;   inspect current code

&#x20;   understand architecture

&#x20;   implement smallest coherent unit

&#x20;   add tests

&#x20;   run quality gate

&#x20;   verify runtime behavior

&#x20;   update documentation

&#x20;   commit to Git



====================================================================

43\. NO PLACEHOLDER CODE

====================================================================



The project target is:



&#x20;   production-grade

&#x20;   enterprise-grade

&#x20;   maintainable

&#x20;   testable

&#x20;   extensible



Do NOT introduce:



&#x20;   pass-only classes

&#x20;   fake implementations

&#x20;   TODO-only methods

&#x20;   dummy return values

&#x20;   hardcoded fake business results

&#x20;   temporary architecture



If a component is not ready to be implemented correctly,

the agent must report the dependency instead of pretending it is

implemented.



====================================================================

44\. CURRENT GIT STATE

====================================================================



No implementation milestones exist yet.



Current repository history contains only documentation and cleanup

commits (Initial commit, New, gitignore, Docs).



The repository uses Git as the source of truth for implementation

history.



Before modifying the project:



&#x20;   inspect git status

&#x20;   inspect recent commits

&#x20;   inspect current branch



Never assume the current HEAD is identical to historical state.



====================================================================

45\. CURRENT IMPLEMENTATION MILESTONE

====================================================================



Current implementation area:



&#x20;   Phase 28.x



Completed foundation milestones include:



&#x20;   Core foundation

&#x20;   Domain foundation

&#x20;   Application runtime foundation



Project Intelligence filesystem skeleton has also been prepared.



The project is now ready for continued incremental implementation.



====================================================================

46\. IMPLEMENTATION STATUS — NOT YET STARTED

====================================================================



NOT YET IMPLEMENTED (PLANNED FOR PHASE 28):



&#x20;   [ ] Git repository

&#x20;   [ ] Python project foundation

&#x20;   [ ] Core base abstractions

&#x20;   [ ] Dependency container foundation

&#x20;   [ ] Event abstraction foundation

&#x20;   [ ] Event bus foundation

&#x20;   [ ] Lifecycle manager foundation

&#x20;   [ ] Plugin abstraction foundation

&#x20;   [ ] Base service abstraction

&#x20;   [ ] Application runtime foundation

&#x20;   [ ] Application startup

&#x20;   [ ] Application shutdown

&#x20;   [ ] Application state

&#x20;   [ ] Service registry

&#x20;   [ ] Domain entity foundation

&#x20;   [ ] Domain value object foundation

&#x20;   [ ] Symbol

&#x20;   [ ] TimeFrame

&#x20;   [ ] Candle

&#x20;   [ ] Account

&#x20;   [ ] Balance

&#x20;   [ ] Prediction

&#x20;   [ ] Signal

&#x20;   [ ] Risk model foundation

&#x20;   [ ] Order foundation

&#x20;   [ ] Position foundation

&#x20;   [ ] Trade foundation

&#x20;   [ ] Project Intelligence directory skeleton

&#x20;   [ ] Project State directory skeleton





PLANNED / INCOMPLETE:



&#x20;   \[ ] Complete Domain Model

&#x20;   \[ ] Complete Aggregate Model

&#x20;   \[ ] Complete Domain Events

&#x20;   \[ ] Complete Market Data Platform

&#x20;   \[ ] Complete Feature Platform

&#x20;   \[ ] Complete AI Platform

&#x20;   \[ ] Complete Strategy Platform

&#x20;   \[ ] Complete Risk Platform

&#x20;   \[ ] Complete Trading Platform

&#x20;   \[ ] Complete Execution Platform

&#x20;   \[ ] Complete Portfolio Platform

&#x20;   \[ ] Complete Simulation Platform

&#x20;   \[ ] Complete Backtesting Platform

&#x20;   \[ ] Complete Optimization Platform

&#x20;   \[ ] Complete Self-Learning Platform

&#x20;   \[ ] Complete Project Intelligence

&#x20;   \[ ] Complete GUI

&#x20;   \[ ] Complete Database

&#x20;   \[ ] Complete Configuration System

&#x20;   \[ ] Complete Logging System

&#x20;   \[ ] Complete Testing Architecture

&#x20;   \[ ] Complete Deployment Architecture

&#x20;   \[ ] Complete Project Generator

&#x20;   \[ ] Complete architecture validation

&#x20;   \[ ] Production hardening



====================================================================

47\. IMMEDIATE NEXT IMPLEMENTATION AREA

====================================================================



The next implementation step MUST be determined from:



&#x20;   current Git HEAD

&#x20;   current filesystem

&#x20;   completed Phase 28.x milestone

&#x20;   architecture roadmap

&#x20;   API contracts

&#x20;   tests

&#x20;   project intelligence state



Do NOT blindly continue from an old task list.



The agent MUST inspect the repository before selecting the next task.



====================================================================

48\. REQUIRED FIRST ACTION FOR A NEW AGENT

====================================================================



A new agent MUST NOT immediately start coding.



It MUST first:



&#x20;   1. Inspect repository tree.



&#x20;   2. Inspect Git status.



&#x20;   3. Inspect recent Git history.



&#x20;   4. Read README.



&#x20;   5. Read ARCHITECTURE\_HANDOFF.



&#x20;   6. Read DATA\_FLOW\_DOCUMENTATION.



&#x20;   7. Read DEVELOPMENT\_RULES.



&#x20;   8. Read EXECUTION\_GUIDE.



&#x20;   9. Read Handoff.



&#x20;   10. Read SHADBOTTRADER\_MASTER\_IMPLEMENTATION\_SPECIFICATION.



&#x20;   11. Read API\_AND\_CONTRACT\_SPECIFICATION.



&#x20;   12. Read CURRENT\_STATE.



&#x20;   13. Inspect actual source files.



&#x20;   14. Run the test suite.



&#x20;   15. Run quality checks.



&#x20;   16. Compare documentation with actual code.



Only then may implementation begin.



====================================================================

49\. STATE RECONCILIATION RULE

====================================================================



CURRENT\_STATE is a high-level project memory.



The actual repository is the implementation source of truth.



Therefore:



&#x20;   DOCUMENTATION

&#x20;       +

&#x20;   GIT HISTORY

&#x20;       +

&#x20;   ACTUAL SOURCE

&#x20;       +

&#x20;   TEST RESULTS



must be reconciled.



If these disagree:



&#x20;   do not guess.



Determine the actual state.



====================================================================

50\. CHANGE DETECTION

====================================================================



The future Project Intelligence system should detect:



&#x20;   new files

&#x20;   deleted files

&#x20;   renamed files

&#x20;   modified files

&#x20;   new classes

&#x20;   deleted classes

&#x20;   changed dependencies

&#x20;   changed configuration

&#x20;   changed architecture

&#x20;   new tests

&#x20;   test failures

&#x20;   Git commits

&#x20;   TODO changes

&#x20;   roadmap changes



====================================================================

51\. PROJECT STATE VERSIONING

====================================================================



CURRENT\_STATE should contain a version.



Example:



&#x20;   STATE\_VERSION:

&#x20;       1.0



Whenever the project state changes significantly:



&#x20;   update state version

&#x20;   record change

&#x20;   update timestamp

&#x20;   record commit



====================================================================

52\. STATE METADATA

====================================================================



Current document metadata should contain:



&#x20;   PROJECT:

&#x20;       ShadBotTrader



&#x20;   STATE\_VERSION:

&#x20;       1.0



&#x20;   ARCHITECTURE\_VERSION:

&#x20;       V1.0



&#x20;   IMPLEMENTATION\_BRANCH:

&#x20;       main



&#x20;   STATUS:

&#x20;       FOUNDATION\_IMPLEMENTATION



&#x20;   LAST\_KNOWN\_PHASE:

&#x20;       28.x



&#x20;   DOCUMENT\_STATUS:

&#x20;       ACTIVE



====================================================================

53\. ARCHITECTURAL DECISIONS

====================================================================



Important decisions:



&#x20;   1.

&#x20;   ShadBotTrader uses Clean Architecture.



&#x20;   2.

&#x20;   ShadBotTrader uses DDD principles.



&#x20;   3.

&#x20;   Domain must remain independent from Infrastructure.



&#x20;   4.

&#x20;   Application depends on contracts rather than concrete adapters.



&#x20;   5.

&#x20;   Trading execution must pass Risk.



&#x20;   6.

&#x20;   AI must not directly execute orders.



&#x20;   7.

&#x20;   Simulation must be isolated from Live Execution.



&#x20;   8.

&#x20;   Backtesting must be deterministic.



&#x20;   9.

&#x20;   Financial calculations require appropriate precision.



&#x20;   10.

&#x20;   External provider models must not leak into Domain.



&#x20;   11.

&#x20;   The platform must support plugin-style replacement of

&#x20;       strategies, providers, executors and repositories.



&#x20;   12.

&#x20;   Git is part of project history and must be maintained.



&#x20;   13.

&#x20;   Quality gates are mandatory.



&#x20;   14.

&#x20;   No temporary architecture is acceptable.



&#x20;   15.

&#x20;   Project Intelligence is intended to become the project's

&#x20;       automatic state/memory mechanism.



====================================================================

54\. PROHIBITED ARCHITECTURAL BEHAVIOR

====================================================================



Never:



&#x20;   rewrite the architecture without approval



&#x20;   move all logic into one service



&#x20;   create a giant TradingService



&#x20;   allow Domain to import Infrastructure



&#x20;   allow Strategy to submit orders



&#x20;   allow AI to submit orders



&#x20;   bypass Risk



&#x20;   allow Simulation to call Live Broker



&#x20;   put broker SDK types into Domain



&#x20;   put SQL queries into Domain



&#x20;   use global mutable singleton state as business state



&#x20;   use untyped dictionaries as core Domain models



&#x20;   silently change contract semantics



&#x20;   silently delete existing functionality



&#x20;   mark incomplete code as production-ready



====================================================================

55\. REQUIRED FUTURE PROJECT STATE

====================================================================



The final Project State system should be able to answer:



&#x20;   What is ShadBotTrader?



&#x20;   What architecture does it use?



&#x20;   Which phase is complete?



&#x20;   Which phase is currently active?



&#x20;   Which files exist?



&#x20;   Which classes exist?



&#x20;   Which interfaces exist?



&#x20;   Which dependencies exist?



&#x20;   Which tests exist?



&#x20;   Which tests pass?



&#x20;   Which tests fail?



&#x20;   What changed since the previous snapshot?



&#x20;   What was the last architectural decision?



&#x20;   What is currently being implemented?



&#x20;   What should be implemented next?



&#x20;   What remains incomplete?



&#x20;   What architectural constraints must be respected?



&#x20;   What is the current Git commit?



====================================================================

56\. FINAL TARGET STATE

====================================================================



The final ShadBotTrader architecture should conceptually become:



&#x20;                       SHADBOTTRADER

&#x20;                             |

&#x20;         +-------------------+-------------------+

&#x20;         |                   |                   |

&#x20;      DOMAIN            APPLICATION         INTERFACES

&#x20;         |                   |                   |

&#x20;         |                   |                   |

&#x20;         +-------------------+-------------------+

&#x20;                             |

&#x20;                        CONTRACTS / PORTS

&#x20;                             |

&#x20;         +-------------------+-------------------+

&#x20;         |                   |                   |

&#x20;      DATA              AI / ML             TRADING

&#x20;         |                   |                   |

&#x20;         |                   |                   |

&#x20;     DATABASE          MODEL SYSTEM          EXECUTION

&#x20;                             |

&#x20;                        PORTFOLIO

&#x20;                             |

&#x20;                        SIMULATION

&#x20;                             |

&#x20;                        BACKTESTING

&#x20;                             |

&#x20;                        OPTIMIZATION

&#x20;                             |

&#x20;                       SELF-LEARNING

&#x20;                             |

&#x20;                     PROJECT INTELLIGENCE

&#x20;                             |

&#x20;                          GUI/API

&#x20;                             |

&#x20;                        DEPLOYMENT



====================================================================

57\. PROJECT INTELLIGENCE FINAL LOOP

====================================================================



Final long-term loop:



&#x20;   CODE CHANGE

&#x20;       ↓

&#x20;   GIT

&#x20;       ↓

&#x20;   PROJECT SCANNER

&#x20;       ↓

&#x20;   AST ANALYSIS

&#x20;       ↓

&#x20;   DEPENDENCY ANALYSIS

&#x20;       ↓

&#x20;   ARCHITECTURE ANALYSIS

&#x20;       ↓

&#x20;   TEST ANALYSIS

&#x20;       ↓

&#x20;   PROJECT SNAPSHOT

&#x20;       ↓

&#x20;   PROJECT STATE

&#x20;       ↓

&#x20;   ROADMAP UPDATE

&#x20;       ↓

&#x20;   AI CONTEXT PACKAGE

&#x20;       ↓

&#x20;   CODING AGENT

&#x20;       ↓

&#x20;   CODE CHANGE



This loop is intended to make ShadBotTrader self-describing.



====================================================================

58\. HANDOFF RULE

====================================================================



When this document is supplied to a new AI agent:



&#x20;   The agent must treat it as project-state context.



However:



&#x20;   The agent MUST verify the state against the actual repository.



The agent must never assume:



&#x20;   a planned feature is implemented

&#x20;   a file exists because it is mentioned here

&#x20;   a test passes because it passed historically

&#x20;   a branch is unchanged

&#x20;   an architecture document reflects uncommitted changes



====================================================================

59\. CURRENT STATE SUMMARY

====================================================================



ShadBotTrader currently has:



&#x20;   architecture:

&#x20;       designed



&#x20;   repository:

&#x20;       initialized



&#x20;   core:

&#x20;       not implemented



&#x20;   domain:

&#x20;       not implemented



&#x20;   application:

&#x20;       not implemented



&#x20;   infrastructure:

&#x20;       not implemented



&#x20;   market data:

&#x20;       incomplete



&#x20;   features:

&#x20;       incomplete



&#x20;   AI:

&#x20;       incomplete



&#x20;   strategies:

&#x20;       incomplete



&#x20;   risk:

&#x20;       foundation only



&#x20;   trading:

&#x20;       foundation only



&#x20;   execution:

&#x20;       incomplete



&#x20;   portfolio:

&#x20;       foundation only



&#x20;   simulation:

&#x20;       incomplete



&#x20;   backtesting:

&#x20;       incomplete



&#x20;   optimization:

&#x20;       incomplete



&#x20;   self-learning:

&#x20;       incomplete



&#x20;   project intelligence:

&#x20;       structural foundation prepared



&#x20;   GUI:

&#x20;       incomplete



&#x20;   database:

&#x20;       incomplete



&#x20;   configuration:

&#x20;       incomplete



&#x20;   logging:

&#x20;       foundation / incomplete



&#x20;   testing:

&#x20;       architecture planned; implementation ongoing



&#x20;   deployment:

&#x20;       incomplete



====================================================================

60\. NEXT-STEP PRINCIPLE

====================================================================



The next task must always be selected from:



&#x20;   CURRENT\_STATE

&#x20;       +

&#x20;   ARCHITECTURE

&#x20;       +

&#x20;   ACTUAL CODE

&#x20;       +

&#x20;   TEST STATUS

&#x20;       +

&#x20;   GIT HISTORY



Never from memory alone.



Never from assumptions.



Never by redesigning the system.



====================================================================

61\. DOCUMENT MAINTENANCE

====================================================================



This document MUST be updated whenever a major milestone occurs.



Update when:



&#x20;   architecture changes

&#x20;   phase completes

&#x20;   major subsystem completes

&#x20;   major files are added

&#x20;   major files are removed

&#x20;   contracts change

&#x20;   tests change materially

&#x20;   quality gate changes

&#x20;   deployment state changes

&#x20;   project roadmap changes



The future Project Intelligence system should automate this process.



====================================================================

62\. FINAL IMPLEMENTATION COMMANDMENT

====================================================================



ShadBotTrader is a long-term enterprise system.



Every implementation decision must optimize for:



&#x20;   correctness

&#x20;   architectural integrity

&#x20;   maintainability

&#x20;   testability

&#x20;   determinism

&#x20;   extensibility

&#x20;   observability

&#x20;   financial safety

&#x20;   reproducibility



NOT:



&#x20;   speed of typing

&#x20;   minimum line count

&#x20;   temporary hacks

&#x20;   demo-only behavior

&#x20;   superficial completeness



====================================================================

END OF CURRENT\_STATE

====================================================================

