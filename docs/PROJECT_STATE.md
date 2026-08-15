====================================================================

SHADBOTTRADER

PROJECT\_STATE

====================================================================



DOCUMENT TYPE:

&#x20;   Canonical Project State Document



PROJECT NAME:

&#x20;   ShadBotTrader



PROJECT TYPE:

&#x20;   Enterprise AI Trading Platform



ARCHITECTURE:

&#x20;   Clean Architecture

&#x20;   Domain-Driven Design (DDD)

&#x20;   Modular Architecture

&#x20;   Event-Driven Architecture

&#x20;   Plugin-Oriented Architecture

&#x20;   AI-Driven Architecture



PRIMARY LANGUAGE:

&#x20;   Python



TARGET:

&#x20;   Enterprise-grade production system



DOCUMENT PURPOSE:

&#x20;   This document defines the CURRENT and PLANNED state of the

&#x20;   ShadBotTrader project.



====================================================================

1\. ABSOLUTE PROJECT IDENTITY

====================================================================



The project name is:



&#x20;   ShadBotTrader



Do NOT rename the project to:



&#x20;   ShadBotTrader2

&#x20;   TradingBot

&#x20;   AITrader

&#x20;   TraderBot



The canonical package name (used in paths, imports, CLI commands

and code) is:



&#x20;   ShadBotTrader



====================================================================

2\. PROJECT MISSION

====================================================================



ShadBotTrader is intended to become a complete enterprise-grade

AI-powered trading platform capable of:



&#x20;   market data ingestion



&#x20;   market data normalization



&#x20;   feature engineering



&#x20;   AI/ML prediction



&#x20;   strategy execution



&#x20;   signal generation



&#x20;   risk management



&#x20;   order management



&#x20;   broker integration



&#x20;   portfolio management



&#x20;   trade management



&#x20;   backtesting



&#x20;   simulation



&#x20;   replay



&#x20;   optimization



&#x20;   model training



&#x20;   model evaluation



&#x20;   self-learning



&#x20;   project intelligence



&#x20;   observability



&#x20;   auditability



&#x20;   configuration management



&#x20;   plugin management



&#x20;   event-driven processing



&#x20;   automated testing



&#x20;   autonomous project development



====================================================================

3\. CURRENT DEVELOPMENT PHILOSOPHY

====================================================================



The project is NOT being built as a quick trading script.



It is being built as an enterprise platform.



Therefore:



&#x20;   no temporary architecture



&#x20;   no throwaway code



&#x20;   no fake implementations



&#x20;   no placeholder business logic



&#x20;   no arbitrary shortcuts



&#x20;   no giant monolithic classes



&#x20;   no uncontrolled dependencies



&#x20;   no infrastructure leakage into Domain



&#x20;   no undocumented architectural changes



====================================================================

4\. ARCHITECTURE STATUS

====================================================================



The high-level architecture has already been designed through

Phase 28.



Phases 1-27 define the main platform architecture.



Phase 28 begins the actual implementation/foundation evolution

beyond the original architecture design.



The architecture is considered:



&#x20;   APPROVED



&#x20;   FROZEN where explicitly marked



&#x20;   EXTENSIBLE only through controlled architectural decisions



An implementation agent must NOT redesign the architecture simply

because an alternative implementation appears easier.



====================================================================

5\. ARCHITECTURE PHASE MAP

====================================================================



Phase 1:

&#x20;   Architecture Principles



Phase 2:

&#x20;   Dependency Rules



Phase 3:

&#x20;   Domain Model



Phase 4:

&#x20;   Project Tree



Phase 5:

&#x20;   Framework Design



Phase 6:

&#x20;   Pipeline Design



Phase 7:

&#x20;   Engine Design



Phase 8:

&#x20;   Service Design



Phase 9:

&#x20;   Plugin Architecture



Phase 10:

&#x20;   Event Bus



Phase 11:

&#x20;   Data Platform



Phase 12:

&#x20;   Feature Platform



Phase 13:

&#x20;   AI Platform



Phase 14:

&#x20;   Trading Platform



Phase 15:

&#x20;   Portfolio Platform



Phase 16:

&#x20;   Simulation Platform



Phase 17:

&#x20;   Self Learning Platform



Phase 18:

&#x20;   Project Intelligence Platform



Phase 19:

&#x20;   GUI Architecture



Phase 20:

&#x20;   SQL Server Schema



Phase 21:

&#x20;   Configuration System



Phase 22:

&#x20;   Logging System



Phase 23:

&#x20;   Testing Architecture



Phase 24:

&#x20;   Deployment Architecture



Phase 25:

&#x20;   PowerShell Project Generator



Phase 26:

&#x20;   Architecture Validation / Integration



Phase 27:

&#x20;   Architecture Freeze / V1 Foundation



Phase 28:

&#x20;   Implementation Foundation



====================================================================

6\. PHASE 28 IMPLEMENTATION TRACK

====================================================================



Phase 28 is divided into implementation sub-phases.



Current known implementation sequence:



&#x20;   Phase 28.1

&#x20;       Initial implementation foundation



&#x20;   Phase 28.2

&#x20;       Core foundation



&#x20;   Phase 28.3

&#x20;       Core infrastructure/domain foundation



&#x20;   Phase 28.4

&#x20;       Domain Core



&#x20;   Phase 28.5

&#x20;       Application Runtime Layer



Further Phase 28.x work continues according to the implementation

roadmap.



IMPORTANT:



&#x20;   Phase 28.x implementation must respect Phases 1-27.



Phase 28 does NOT replace the architecture.



It implements it.



====================================================================

7\. CURRENT GIT STATE

====================================================================



Repository:



&#x20;   Git



Primary branch historically used:



&#x20;   main



Implementation branch currently observed:



&#x20;   main



IMPORTANT:



&#x20;   Always inspect the actual current branch with:



&#x20;       git branch --show-current



before making assumptions.



Current previously observed repository state:



&#x20;   working tree clean



&#x20;   local branch ahead of origin by one commit at one point



The repository has been actively committed throughout development.



====================================================================

8\. KNOWN IMPLEMENTATION COMMITS

====================================================================



Known important commits include:



\--------------------------------------------------------------------

Commit:

&#x20;   d085a92



Message:

&#x20;   Implement ShadBotTrader Core Foundation



Created:



&#x20;   src/ShadBotTrader/core/dependency/container.py

&#x20;   src/ShadBotTrader/core/events/event.py

&#x20;   src/ShadBotTrader/core/events/eventBus.py

&#x20;   src/ShadBotTrader/core/lifecycle/lifecycleManager.py

&#x20;   src/ShadBotTrader/core/plugins/plugin.py

&#x20;   src/ShadBotTrader/core/services/baseService.py



\--------------------------------------------------------------------

Commit:

&#x20;   5fed9b8



Message:

&#x20;   Implement ShadBotTrader Domain Core



Created:



&#x20;   src/ShadBotTrader/domain/common/entity.py

&#x20;   src/ShadBotTrader/domain/common/valueObject.py

&#x20;   src/ShadBotTrader/domain/market/candle.py

&#x20;   src/ShadBotTrader/domain/market/symbol.py

&#x20;   src/ShadBotTrader/domain/market/timefram.py

&#x20;   src/ShadBotTrader/domain/portfolio/account.py

&#x20;   src/ShadBotTrader/domain/portfolio/balance.py

&#x20;   src/ShadBotTrader/domain/prediction/prediction.py

&#x20;   src/ShadBotTrader/domain/prediction/signal.py

&#x20;   src/ShadBotTrader/domain/risk/riskModel.py

&#x20;   src/ShadBotTrader/domain/trading/oerder.py

&#x20;   src/ShadBotTrader/domain/trading/position.py

&#x20;   src/ShadBotTrader/domain/trading/trade.py



\--------------------------------------------------------------------

Commit:

&#x20;   f96557b



Message:

&#x20;   Implement application runtime layer



Created:



&#x20;   src/ShadBotTrader/application/app.py

&#x20;   src/ShadBotTrader/application/applicationState.py

&#x20;   src/ShadBotTrader/application/bootstrap.py

&#x20;   src/ShadBotTrader/application/runtime.py

&#x20;   src/ShadBotTrader/application/serviceRegistry.py

&#x20;   src/ShadBotTrader/application/shutdown.py

&#x20;   src/ShadBotTrader/application/startup.py



====================================================================

9\. CURRENT EXECUTABLE STATE

====================================================================



The project has NOT been executed yet — no new-platform code exists

to run.



There is no runtime output yet.



IMPORTANT:



&#x20;   The first successful runtime will be produced during Phase 28

&#x20;   implementation, not before.



====================================================================

10\. CURRENT CORE FOUNDATION

====================================================================



The following conceptual core components are PLANNED (not yet implemented):



&#x20;   Dependency Container



&#x20;   Event



&#x20;   Event Bus



&#x20;   Lifecycle Manager



&#x20;   Plugin Base



&#x20;   Base Service



These represent the beginning of the platform runtime foundation.



====================================================================

11\. CURRENT DOMAIN FOUNDATION

====================================================================



Existing domain concepts include:



&#x20;   Entity



&#x20;   Value Object



&#x20;   Candle



&#x20;   Symbol



&#x20;   Timeframe



&#x20;   Account



&#x20;   Balance



&#x20;   Prediction



&#x20;   Signal



&#x20;   Risk Model



&#x20;   Order



&#x20;   Position



&#x20;   Trade



These files form the initial Domain Core.



IMPORTANT:



&#x20;   Existing implementations must be inspected before extending them.



Do not blindly recreate equivalent classes.



====================================================================

12\. CURRENT APPLICATION FOUNDATION

====================================================================



Existing application concepts include:



&#x20;   Application



&#x20;   ApplicationState



&#x20;   Bootstrap



&#x20;   Runtime



&#x20;   ServiceRegistry



&#x20;   Startup



&#x20;   Shutdown



These components form the Application Runtime Layer.



====================================================================

13\. PROJECT INTELLIGENCE PLATFORM

====================================================================



A major architectural requirement is the Project Intelligence

Platform.



Its purpose is to allow ShadBotTrader/ShadBotTrader development tooling

to understand its own project.



The Project Intelligence system is intended to automatically:



&#x20;   scan the workspace



&#x20;   understand project structure



&#x20;   analyze Python files



&#x20;   inspect AST



&#x20;   inspect Git



&#x20;   inspect configuration



&#x20;   inspect dependencies



&#x20;   inspect packages



&#x20;   calculate project statistics



&#x20;   inspect roadmap



&#x20;   inspect decisions



&#x20;   inspect TODOs



&#x20;   generate project snapshots



&#x20;   generate project context



&#x20;   generate architecture documentation



&#x20;   generate roadmap documentation



&#x20;   generate decisions documentation



&#x20;   generate TODO documentation



&#x20;   generate statistics



&#x20;   generate dependency graph



&#x20;   generate ChatGPT/Agent context



&#x20;   preserve historical project state



====================================================================

14\. PROJECT INTELLIGENCE DIRECTORY

====================================================================



The following structure is PLANNED (not yet created):



&#x20;   src/ShadBotTrader/project/



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

15\. PROJECT STATE STORAGE

====================================================================



The following directory exists:



&#x20;   project\_state/



with:



&#x20;   project\_state/generated/



&#x20;   project\_state/archive/



====================================================================

16\. GENERATED PROJECT STATE FILES

====================================================================



Expected/generated artifacts include:



&#x20;   ProjectSnapshot.md



&#x20;   ProjectSnapshot.json



&#x20;   ChatGPT\_Context.md



&#x20;   Architecture.md



&#x20;   Roadmap.md



&#x20;   Decisions.md



&#x20;   Todo.md



&#x20;   Statistics.json



&#x20;   DependencyGraph.json



These files are intended to become the persistent bridge between

project development sessions.



====================================================================

17\. CHATGPT HANDOFF OBJECTIVE

====================================================================



The Project Intelligence Platform must eventually generate a

canonical context document that can be provided to a new AI

conversation.



The new AI must be able to understand:



&#x20;   project identity



&#x20;   architecture



&#x20;   current phase



&#x20;   completed phases



&#x20;   current implementation



&#x20;   current file tree



&#x20;   domain model



&#x20;   application model



&#x20;   infrastructure model



&#x20;   project decisions



&#x20;   known issues



&#x20;   TODOs



&#x20;   roadmap



&#x20;   recent changes



&#x20;   Git state



&#x20;   tests



&#x20;   quality gate



&#x20;   next implementation step



without requiring the previous conversation.



====================================================================

18\. PROJECT SNAPSHOT

====================================================================



ProjectSnapshot represents a point-in-time representation of the

entire project.



It should eventually include:



&#x20;   project metadata



&#x20;   Git state



&#x20;   filesystem state



&#x20;   package state



&#x20;   dependency state



&#x20;   source statistics



&#x20;   architecture state



&#x20;   domain state



&#x20;   application state



&#x20;   roadmap



&#x20;   decisions



&#x20;   TODOs



&#x20;   quality state



&#x20;   implementation state



&#x20;   generated artifact metadata



====================================================================

19\. PROJECT CONTEXT

====================================================================



ProjectContext is the condensed operational representation of the

project for AI/Agent consumption.



It should answer:



&#x20;   What is this project?



&#x20;   What architecture does it use?



&#x20;   What has already been implemented?



&#x20;   What is currently being implemented?



&#x20;   What remains?



&#x20;   What decisions have been made?



&#x20;   What files are important?



&#x20;   What must not be changed?



&#x20;   What is the next task?



====================================================================

20\. ROADMAP

====================================================================



The roadmap must represent:



&#x20;   completed phases



&#x20;   active phase



&#x20;   blocked phases



&#x20;   future phases



&#x20;   implementation tasks



&#x20;   dependencies between tasks



&#x20;   completion criteria



====================================================================

21\. DECISIONS

====================================================================



Architectural decisions must be preserved.



Examples:



&#x20;   Clean Architecture



&#x20;   DDD



&#x20;   dependency direction



&#x20;   frozen framework choices



&#x20;   domain boundaries



&#x20;   event-driven architecture



&#x20;   plugin architecture



&#x20;   AI architecture



&#x20;   trading architecture



&#x20;   testing rules



&#x20;   quality gate



Every significant architectural change must create/update a

Decision record.



====================================================================

22\. TODO SYSTEM

====================================================================



TODO items must not be random comments only.



The future system should support:



&#x20;   ID



&#x20;   title



&#x20;   description



&#x20;   priority



&#x20;   category



&#x20;   status



&#x20;   phase



&#x20;   dependencies



&#x20;   created\_at



&#x20;   updated\_at



&#x20;   completion criteria



====================================================================

23\. PROJECT STATISTICS

====================================================================



Statistics should eventually include:



&#x20;   total files



&#x20;   Python files



&#x20;   lines of code



&#x20;   classes



&#x20;   functions



&#x20;   modules



&#x20;   tests



&#x20;   dependencies



&#x20;   packages



&#x20;   source directories



&#x20;   test directories



&#x20;   Git commits



&#x20;   changed files



====================================================================

24\. DEPENDENCY GRAPH

====================================================================



The DependencyGraph must represent:



&#x20;   module → dependency



and eventually:



&#x20;   package → package



&#x20;   layer → layer



&#x20;   bounded context → bounded context



It must be used to detect:



&#x20;   circular dependencies



&#x20;   forbidden dependencies



&#x20;   architectural violations



====================================================================

25\. ARCHITECTURAL DEPENDENCY DIRECTION

====================================================================



Canonical direction:



&#x20;   Domain

&#x20;       ↑

&#x20;   Application

&#x20;       ↑

&#x20;   Infrastructure



More precisely:



&#x20;   outer layers may depend on inner layers.



Inner layers must not depend on outer layers.



The Domain is the most protected layer.



====================================================================

26\. CORE ARCHITECTURAL LAYERS

====================================================================



Primary layers:



&#x20;   Core/Foundation



&#x20;   Domain



&#x20;   Application



&#x20;   Infrastructure



&#x20;   Presentation/Interface



&#x20;   Project Intelligence



&#x20;   Platform Services



Exact implementation must follow the approved architecture.



====================================================================

27\. DOMAIN STATUS

====================================================================



Domain Core:



&#x20;   NOT IMPLEMENTED (PLANNED)



Planned objects:



&#x20;   Entity



&#x20;   ValueObject



&#x20;   Candle



&#x20;   Symbol



&#x20;   Timeframe



&#x20;   Account



&#x20;   Balance



&#x20;   Prediction



&#x20;   Signal



&#x20;   RiskModel



&#x20;   Order



&#x20;   Position



&#x20;   Trade



The complete canonical Domain Model remains larger than these

initial files.



The full Domain Model includes:



&#x20;   Market



&#x20;   Feature



&#x20;   AI



&#x20;   Strategy



&#x20;   Risk



&#x20;   Account



&#x20;   Portfolio



&#x20;   Trading



&#x20;   Simulation



&#x20;   Backtesting



&#x20;   Optimization



&#x20;   Learning



&#x20;   Reconciliation



====================================================================

28\. APPLICATION STATUS

====================================================================



Application Runtime:



&#x20;   NOT IMPLEMENTED (PLANNED)



Planned concepts:



&#x20;   Application



&#x20;   Runtime



&#x20;   Startup



&#x20;   Shutdown



&#x20;   Bootstrap



&#x20;   ServiceRegistry



&#x20;   ApplicationState



This layer must continue evolving according to the Phase 28

implementation roadmap.



====================================================================

29\. INFRASTRUCTURE STATUS

====================================================================



Infrastructure has NOT been implemented.



No runtime output exists yet.



The final infrastructure platform is NOT considered complete.



Future infrastructure includes:



&#x20;   database



&#x20;   repositories



&#x20;   external market data



&#x20;   broker adapters



&#x20;   AI runtime adapters



&#x20;   filesystem



&#x20;   persistence



&#x20;   messaging



&#x20;   logging



&#x20;   configuration



====================================================================

30\. TRADING PLATFORM STATUS

====================================================================



Trading platform is:



&#x20;   ARCHITECTED



&#x20;   NOT IMPLEMENTED



The conceptual flow is:



&#x20;   Market Data

&#x20;       ↓

&#x20;   Feature

&#x20;       ↓

&#x20;   Prediction

&#x20;       ↓

&#x20;   Strategy

&#x20;       ↓

&#x20;   Signal

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



The complete implementation is still future work.



====================================================================

31\. AI PLATFORM STATUS

====================================================================



AI Platform is:



&#x20;   ARCHITECTED



&#x20;   NOT IMPLEMENTED



Expected capabilities:



&#x20;   dataset management



&#x20;   feature pipeline



&#x20;   training



&#x20;   validation



&#x20;   model registry



&#x20;   model versioning



&#x20;   prediction



&#x20;   evaluation



&#x20;   experiment tracking



====================================================================

32\. BACKTESTING STATUS

====================================================================



Backtesting is:



&#x20;   ARCHITECTED



&#x20;   NOT IMPLEMENTED



Must eventually support:



&#x20;   historical data



&#x20;   strategy replay



&#x20;   feature generation



&#x20;   AI inference



&#x20;   simulated execution



&#x20;   fees



&#x20;   slippage



&#x20;   portfolio accounting



&#x20;   metrics



&#x20;   equity curve



&#x20;   drawdown



&#x20;   reproducibility



====================================================================

33\. SIMULATION STATUS

====================================================================



Simulation is:



&#x20;   ARCHITECTED



&#x20;   NOT IMPLEMENTED



Must support:



&#x20;   deterministic execution



&#x20;   configurable slippage



&#x20;   configurable fees



&#x20;   configurable latency



&#x20;   simulated fills



&#x20;   portfolio state



====================================================================

34\. SELF-LEARNING STATUS

====================================================================



Self-learning is:



&#x20;   ARCHITECTED



&#x20;   NOT IMPLEMENTED



Must support controlled:



&#x20;   feedback



&#x20;   evaluation



&#x20;   adaptation



&#x20;   retraining



&#x20;   model replacement



No automatic learning mechanism may silently modify live trading

behavior.



====================================================================

35\. PORTFOLIO STATUS

====================================================================



Portfolio management is:



&#x20;   ARCHITECTED



&#x20;   NOT IMPLEMENTED



Full implementation remains future work.



Expected capabilities:



&#x20;   positions



&#x20;   balances



&#x20;   exposure



&#x20;   equity



&#x20;   realized PnL



&#x20;   unrealized PnL



&#x20;   drawdown



&#x20;   portfolio snapshots



====================================================================

36\. RISK STATUS

====================================================================



Risk management is:



&#x20;   ARCHITECTED



&#x20;   NOT IMPLEMENTED



Full risk engine remains future work.



Must eventually support:



&#x20;   position sizing



&#x20;   exposure limits



&#x20;   maximum loss



&#x20;   drawdown



&#x20;   leverage



&#x20;   concentration



&#x20;   instrument restrictions



&#x20;   account restrictions



====================================================================

37\. EVENT BUS STATUS

====================================================================



Core Event Bus foundation does NOT exist yet.



Planned:



&#x20;   event.py



&#x20;   eventBus.py



Future requirements:



&#x20;   typed events



&#x20;   event handlers



&#x20;   event routing



&#x20;   correlation IDs



&#x20;   causation IDs



&#x20;   event persistence where required



&#x20;   reliable dispatch



&#x20;   error handling



&#x20;   observability



====================================================================

38\. PLUGIN STATUS

====================================================================



Plugin foundation does NOT exist yet.



Planned:



&#x20;   plugin.py



Future plugin architecture must support:



&#x20;   discovery



&#x20;   registration



&#x20;   lifecycle



&#x20;   dependency management



&#x20;   enable/disable



&#x20;   versioning



&#x20;   isolation



&#x20;   capability declaration



Potential plugin areas:



&#x20;   market providers



&#x20;   brokers



&#x20;   strategies



&#x20;   AI models



&#x20;   feature providers



&#x20;   exporters



====================================================================

39\. DEPENDENCY INJECTION STATUS

====================================================================



Dependency container foundation does NOT exist yet (planned):



&#x20;   src/ShadBotTrader/core/dependency/container.py



The final DI system must support:



&#x20;   registration



&#x20;   resolution



&#x20;   singleton/scoped/transient semantics where required



&#x20;   lifecycle management



&#x20;   dependency validation



&#x20;   test replacement



====================================================================

40\. LIFECYCLE STATUS

====================================================================



Lifecycle foundation does NOT exist yet (planned):



&#x20;   lifecycle_manager.py



Application lifecycle must eventually be:



&#x20;   bootstrap



&#x20;   initialize



&#x20;   validate



&#x20;   start



&#x20;   run



&#x20;   stop



&#x20;   shutdown



with deterministic ordering.



====================================================================

41\. CONFIGURATION STATUS

====================================================================



Configuration system is architected.



Final configuration must support:



&#x20;   environment configuration



&#x20;   development configuration



&#x20;   testing configuration



&#x20;   production configuration



&#x20;   trading configuration



&#x20;   risk configuration



&#x20;   AI configuration



&#x20;   database configuration



&#x20;   broker configuration



Configuration must not be hardcoded into Domain objects.



====================================================================

42\. LOGGING STATUS

====================================================================



Logging architecture is defined but requires complete

implementation.



Logging must support:



&#x20;   structured logs



&#x20;   levels



&#x20;   correlation ID



&#x20;   component



&#x20;   event



&#x20;   timestamp



&#x20;   exception details



&#x20;   trading context where appropriate



Never log secrets.



====================================================================

43\. TESTING STATUS

====================================================================



Testing architecture is defined.



Mandatory quality gate:



&#x20;   pytest



&#x20;   ruff



&#x20;   black



&#x20;   mypy



Every meaningful implementation change must be validated.



====================================================================

44\. QUALITY GATE

====================================================================



Canonical commands:



&#x20;   python -m ruff check .



&#x20;   python -m black --check .



&#x20;   python -m mypy src



&#x20;   python -m pytest



A task is not considered complete until the quality gate passes.



If a check fails:



&#x20;   fix the root cause



&#x20;   rerun the complete quality gate



Do not:



&#x20;   disable lint rules



&#x20;   ignore typing errors



&#x20;   skip tests



&#x20;   weaken architecture



====================================================================

45\. CODING STANDARDS

====================================================================



Python implementation must favor:



&#x20;   type hints



&#x20;   explicit interfaces



&#x20;   small cohesive classes



&#x20;   immutable value objects



&#x20;   dependency injection



&#x20;   deterministic behavior



&#x20;   testability



&#x20;   clear naming



&#x20;   domain-oriented terminology



Avoid:



&#x20;   magic numbers



&#x20;   hidden global state



&#x20;   implicit side effects



&#x20;   generic utility dumping grounds



&#x20;   giant classes



&#x20;   giant functions



====================================================================

46\. FILE NAMING STATUS

====================================================================



Existing code contains historical naming such as:



&#x20;   eventBus.py



&#x20;   lifecycleManager.py



&#x20;   baseService.py



&#x20;   applicationState.py



&#x20;   serviceRegistry.py



&#x20;   timefram.py



&#x20;   oerder.py



These files exist in the current implementation history.



IMPORTANT:



&#x20;   Do not rename existing files automatically.



First inspect imports, tests and architectural intent.



If naming correction is required, perform it as a controlled

refactoring with full validation.



====================================================================

47\. CURRENT PROJECT INTELLIGENCE SCAFFOLD

====================================================================



Directories already created:



&#x20;   src/ShadBotTrader/project



&#x20;   src/ShadBotTrader/project/core



&#x20;   src/ShadBotTrader/project/models



&#x20;   src/ShadBotTrader/project/builders



&#x20;   src/ShadBotTrader/project/exporters



&#x20;   src/ShadBotTrader/project/runtime



&#x20;   project\_state



&#x20;   project\_state/generated



&#x20;   project\_state/archive



Many initial files were created as structural files.



IMPORTANT:



&#x20;   File existence does NOT mean functional implementation is

&#x20;   complete.



The implementation agent must inspect actual contents before

assuming functionality.



====================================================================

48\. PROJECT INTELLIGENCE IMPLEMENTATION STATUS

====================================================================



Current status:



&#x20;   NOT IMPLEMENTED



&#x20;   PLANNED (Phase 28 / Sprint P0)



Required future behavior:



&#x20;   scan



&#x20;   analyze



&#x20;   model



&#x20;   build



&#x20;   export



&#x20;   archive



&#x20;   generate context



&#x20;   generate handoff



&#x20;   detect changes



&#x20;   update state



&#x20;   preserve history



====================================================================

49\. AUTOMATIC STATE UPDATE

====================================================================



The eventual Project Intelligence Runtime must be able to:



&#x20;   detect project changes



&#x20;   run project scans



&#x20;   update ProjectSnapshot



&#x20;   update statistics



&#x20;   update dependency graph



&#x20;   update roadmap state



&#x20;   update decisions



&#x20;   update TODOs



&#x20;   generate ChatGPT\_Context.md



&#x20;   archive previous state



&#x20;   produce a new canonical state package



This is a major long-term requirement.



====================================================================

50\. ARCHIVE MODEL

====================================================================



Previous generated project states must not simply be overwritten.



The system should support:



&#x20;   current state



&#x20;   previous state



&#x20;   historical snapshots



Example conceptual structure:



&#x20;   project\_state/

&#x20;       current/

&#x20;       generated/

&#x20;       archive/

&#x20;           <timestamp>/

&#x20;               ...



Exact implementation may follow the final architecture.



====================================================================

51\. CHATGPT CONTEXT

====================================================================



ChatGPT\_Context.md must eventually become the primary handoff file

for starting a new AI conversation.



It should include:



&#x20;   PROJECT IDENTITY



&#x20;   ARCHITECTURE



&#x20;   CURRENT PHASE



&#x20;   COMPLETED PHASES



&#x20;   CURRENT IMPLEMENTATION



&#x20;   CURRENT FILE TREE



&#x20;   DOMAIN MODEL



&#x20;   APPLICATION MODEL



&#x20;   INFRASTRUCTURE STATUS



&#x20;   PROJECT INTELLIGENCE STATUS



&#x20;   GIT STATE



&#x20;   TEST STATE



&#x20;   DECISIONS



&#x20;   TODO



&#x20;   ROADMAP



&#x20;   NEXT ACTION



====================================================================

52\. CURRENT ROADMAP STATUS

====================================================================



Completed/design-complete:



&#x20;   Phases 1-27 architecture design



Implementation begun:



&#x20;   NO — not started



Known implementation work completed:



&#x20;   NONE



Project Intelligence scaffold created:



&#x20;   NO



Project Intelligence complete:



&#x20;   NO



Full Trading Platform:



&#x20;   NO



Full AI Platform:



&#x20;   NO



Full Portfolio Platform:



&#x20;   NO



Full Backtesting:



&#x20;   NO



Full Simulation:



&#x20;   NO



Full Self Learning:



&#x20;   NO



Full production Infrastructure:



&#x20;   NO



====================================================================

53\. CURRENT DEVELOPMENT POSITION

====================================================================



CURRENT HIGH-LEVEL STATE:



&#x20;   Architecture:

&#x20;       APPROVED



&#x20;   Architecture Design:

&#x20;       COMPLETE THROUGH PHASE 27



&#x20;   Implementation:

&#x20;       NOT STARTED



&#x20;   Core Foundation:

&#x20;       NOT IMPLEMENTED



&#x20;   Domain:

&#x20;       NOT IMPLEMENTED



&#x20;   Application:

&#x20;       NOT IMPLEMENTED



&#x20;   Project Intelligence:

&#x20;       NOT IMPLEMENTED



&#x20;   Complete Product:

&#x20;       NOT COMPLETE



====================================================================

54\. NEXT WORK RULE

====================================================================



Before starting a new phase:



&#x20;   1. Inspect actual Git state.



&#x20;   2. Inspect actual directory tree.



&#x20;   3. Inspect files already implemented.



&#x20;   4. Inspect tests.



&#x20;   5. Run quality gate.



&#x20;   6. Compare implementation with architecture.



&#x20;   7. Identify missing work.



&#x20;   8. Implement only the current phase.



&#x20;   9. Run quality gate again.



&#x20;   10. Commit the completed phase.



====================================================================

55\. NEVER ASSUME

====================================================================



An implementation agent MUST NOT assume:



&#x20;   a file is empty because its name suggests it is new



&#x20;   a module is complete because it exists



&#x20;   a phase is complete because a commit exists



&#x20;   architecture documents match implementation automatically



&#x20;   tests are sufficient without running them



&#x20;   Git branch is main



&#x20;   current working tree is clean



&#x20;   generated state is current



====================================================================

56\. FIRST ACTION FOR ANY NEW AGENT

====================================================================



A new coding agent must first inspect:



&#x20;   git status



&#x20;   git branch --show-current



&#x20;   git log --oneline -20



&#x20;   complete source tree



&#x20;   tests



&#x20;   project\_state



&#x20;   architecture documents



Then it must compare actual implementation against this

PROJECT\_STATE document.



====================================================================

57\. SECOND ACTION FOR NEW AGENT

====================================================================



Run:



&#x20;   python -m ruff check .



&#x20;   python -m black --check .



&#x20;   python -m mypy src



&#x20;   python -m pytest



Record the result.



Do not begin a large implementation task before understanding the

baseline.



====================================================================

58\. THIRD ACTION FOR NEW AGENT

====================================================================



Determine:



&#x20;   current phase



&#x20;   current sub-phase



&#x20;   completed work



&#x20;   incomplete work



&#x20;   broken work



&#x20;   next required implementation



The agent must NOT jump ahead because a later module appears

interesting.



====================================================================

59\. SOURCE OF TRUTH PRIORITY

====================================================================



When documents disagree, use this priority:



&#x20;   1. Actual source code



&#x20;   2. Passing tests



&#x20;   3. Explicit architectural decisions



&#x20;   4. Current project state



&#x20;   5. Roadmap



&#x20;   6. Older generated documents



&#x20;   7. Agent assumptions



Agent assumptions have the lowest authority.



====================================================================

60\. CHANGE MANAGEMENT

====================================================================



Any architectural change must be:



&#x20;   explicit



&#x20;   documented



&#x20;   tested



&#x20;   committed



&#x20;   reflected in Project Intelligence



Never silently alter:



&#x20;   aggregate boundaries



&#x20;   dependency rules



&#x20;   domain semantics



&#x20;   execution modes



&#x20;   trading safety rules



====================================================================

61\. GIT DISCIPLINE

====================================================================



Each meaningful implementation phase should produce a focused

commit.



Commit messages should clearly describe the implementation.



Examples:



&#x20;   Implement ShadBotTrader Core Foundation



&#x20;   Implement ShadBotTrader Domain Core



&#x20;   Implement application runtime layer



Future commits should use similarly explicit descriptions.



====================================================================

62\. PRODUCTION SAFETY

====================================================================



The system must eventually protect against:



&#x20;   accidental live execution



&#x20;   invalid orders



&#x20;   invalid quantities



&#x20;   excessive exposure



&#x20;   stale market data



&#x20;   duplicate execution



&#x20;   inconsistent portfolio state



&#x20;   model/data mismatch



&#x20;   lookahead bias



&#x20;   silent configuration changes



&#x20;   untracked strategy changes



====================================================================

63\. VERSIONING

====================================================================



The following must be versionable:



&#x20;   strategy



&#x20;   strategy configuration



&#x20;   feature definitions



&#x20;   datasets



&#x20;   dataset versions



&#x20;   AI models



&#x20;   model versions



&#x20;   backtest configuration



&#x20;   simulation configuration



&#x20;   risk configuration



====================================================================

64\. AUDITABILITY

====================================================================



Important business decisions must be traceable.



The system should eventually answer:



&#x20;   Why was this signal generated?



&#x20;   Which model generated it?



&#x20;   Which model version?



&#x20;   Which features?



&#x20;   Which dataset?



&#x20;   Which strategy version?



&#x20;   Which risk rules?



&#x20;   Which risk decision?



&#x20;   Which order?



&#x20;   Which execution?



&#x20;   Which portfolio state?



====================================================================

65\. REPRODUCIBILITY

====================================================================



Any historical decision must be reproducible wherever practical.



Required references include:



&#x20;   data version



&#x20;   feature version



&#x20;   strategy version



&#x20;   model version



&#x20;   configuration



&#x20;   execution mode



&#x20;   timestamps



====================================================================

66\. PROJECT COMPLETION DEFINITION

====================================================================



ShadBotTrader is NOT complete merely because:



&#x20;   application starts



&#x20;   tests pass



&#x20;   domain classes exist



&#x20;   database connects



&#x20;   broker connects



A complete system requires:



&#x20;   architecture



&#x20;   domain



&#x20;   application



&#x20;   infrastructure



&#x20;   data platform



&#x20;   feature platform



&#x20;   AI platform



&#x20;   trading platform



&#x20;   portfolio platform



&#x20;   simulation



&#x20;   backtesting



&#x20;   self-learning



&#x20;   project intelligence



&#x20;   GUI/interface



&#x20;   configuration



&#x20;   logging



&#x20;   testing



&#x20;   deployment



&#x20;   documentation



&#x20;   operational safety



====================================================================

67\. CURRENT NEXT-STEP PRINCIPLE

====================================================================



The next task must always be determined from:



&#x20;   current implementation



&#x20;   architecture roadmap



&#x20;   latest successful phase



&#x20;   outstanding TODOs



&#x20;   test status



&#x20;   project state



NOT from guesswork.



====================================================================

68\. AGENT HANDOFF REQUIREMENT

====================================================================



A new AI agent receiving:



&#x20;   PROJECT\_STATE



&#x20;   ARCHITECTURE\_HANDOFF



&#x20;   DATA\_FLOW\_DOCUMENTATION



&#x20;   DEVELOPMENT\_RULES



&#x20;   EXECUTION\_GUIDE



&#x20;   Handoff



&#x20;   SHADBOTTRADER\_MASTER\_IMPLEMENTATION\_SPECIFICATION



&#x20;   API\_AND\_CONTRACT\_SPECIFICATION



&#x20;   DATABASE\_SCHEMA\_SPECIFICATION



&#x20;   DOMAIN\_MODEL\_SPECIFICATION



&#x20;   README



must be able to reconstruct the project's intended state and

continue implementation without access to the previous chat.



====================================================================

69\. CURRENT FILES OF HIGH IMPORTANCE

====================================================================



Core:



&#x20;   src/ShadBotTrader/core/



Domain:



&#x20;   src/ShadBotTrader/domain/



Application:



&#x20;   src/ShadBotTrader/application/



Project Intelligence:



&#x20;   src/ShadBotTrader/project/



Generated state:



&#x20;   project\_state/generated/



Historical state:



&#x20;   project\_state/archive/



====================================================================

70\. CURRENT IMPLEMENTATION WARNING

====================================================================



The project contains both:



&#x20;   architectural design



and:



&#x20;   partial implementation



These are NOT equivalent.



An agent must distinguish:



&#x20;   DESIGNED



&#x20;   IMPLEMENTED



&#x20;   TESTED



&#x20;   VERIFIED



&#x20;   PRODUCTION READY



A feature marked ARCHITECTED is not automatically implemented.



A file marked EXISTS is not automatically functional.



A passing startup command does not mean the subsystem is complete.



====================================================================

71\. CURRENT STATUS LEGEND

====================================================================



Use these statuses consistently:



&#x20;   DESIGNED

&#x20;       Architecture/specification exists.



&#x20;   SCAFFOLDED

&#x20;       Directory/file structure exists.



&#x20;   IMPLEMENTED

&#x20;       Functional code exists.



&#x20;   TESTED

&#x20;       Automated tests validate behavior.



&#x20;   VERIFIED

&#x20;       Integration/quality checks confirm behavior.



&#x20;   PRODUCTION\_READY

&#x20;       Meets production requirements.



&#x20;   BLOCKED

&#x20;       Cannot proceed because of a dependency/problem.



====================================================================

72\. CURRENT PROJECT STATUS MATRIX

====================================================================



Architecture:

&#x20;   PRODUCTION DESIGN / APPROVED



Core Foundation:

&#x20;   NOT IMPLEMENTED



Domain Core:

&#x20;   NOT IMPLEMENTED



Application Runtime:

&#x20;   NOT IMPLEMENTED



Event Bus:

&#x20;   NOT IMPLEMENTED



Plugin Foundation:

&#x20;   NOT IMPLEMENTED



Dependency Injection:

&#x20;   NOT IMPLEMENTED



Lifecycle:

&#x20;   NOT IMPLEMENTED



Trading Platform:

&#x20;   DESIGNED



Portfolio Platform:

&#x20;   DESIGNED



AI Platform:

&#x20;   DESIGNED



Feature Platform:

&#x20;   DESIGNED



Data Platform:

&#x20;   DESIGNED



Simulation:

&#x20;   DESIGNED



Backtesting:

&#x20;   DESIGNED



Optimization:

&#x20;   DESIGNED



Self Learning:

&#x20;   DESIGNED



Project Intelligence:

&#x20;   NOT IMPLEMENTED



GUI:

&#x20;   DESIGNED



Database:

&#x20;   DESIGNED



Configuration:

&#x20;   DESIGNED



Logging:

&#x20;   DESIGNED



Testing Architecture:

&#x20;   DESIGNED



Deployment:

&#x20;   DESIGNED



PowerShell Generator:

&#x20;   DESIGNED



====================================================================

73\. IMMEDIATE DEVELOPMENT OBJECTIVE

====================================================================



The immediate objective is NOT to build the entire trading system

at once.



The immediate objective is:



&#x20;   incrementally implement the approved architecture



&#x20;   preserve clean boundaries



&#x20;   validate every phase



&#x20;   maintain project state



&#x20;   keep the project reproducible



&#x20;   make future AI-agent handoff reliable



====================================================================

74\. PROJECT INTELLIGENCE FINAL OBJECTIVE

====================================================================



Eventually ShadBotTrader should be capable of generating its own

complete development state.



Conceptually:



&#x20;   Code changes

&#x20;       ↓

&#x20;   Project Scanner

&#x20;       ↓

&#x20;   Project Snapshot

&#x20;       ↓

&#x20;   Analysis

&#x20;       ↓

&#x20;   State Update

&#x20;       ↓

&#x20;   Documentation

&#x20;       ↓

&#x20;   ChatGPT Context

&#x20;       ↓

&#x20;   Agent Handoff



Therefore a future agent can start with:



&#x20;   current state



rather than:



&#x20;   historical chat history.



====================================================================

75\. FINAL RULE FOR FUTURE AGENTS

====================================================================



DO NOT START BY REBUILDING THE PROJECT.



DO NOT REDESIGN THE ARCHITECTURE.



DO NOT DELETE EXISTING WORK.



DO NOT REPLACE EXISTING MODULES WITHOUT INSPECTION.



DO NOT ASSUME THE DOCUMENTATION IS PERFECT.



DO NOT ASSUME THE CODE IS COMPLETE.



FIRST:



&#x20;   inspect



&#x20;   understand



&#x20;   compare



&#x20;   validate



THEN:



&#x20;   implement



THEN:



&#x20;   test



THEN:



&#x20;   update project state



THEN:



&#x20;   commit



====================================================================

76\. CURRENT STATE SUMMARY

====================================================================



PROJECT:



&#x20;   ShadBotTrader



ARCHITECTURE:



&#x20;   Enterprise Clean Architecture + DDD



ARCHITECTURE DESIGN:



&#x20;   Complete through Phase 27



IMPLEMENTATION:



&#x20;   Not started



CORE:



&#x20;   Not implemented



DOMAIN:



&#x20;   Not implemented



APPLICATION:



&#x20;   Not implemented



PROJECT INTELLIGENCE:



&#x20;   Not implemented



TRADING:



&#x20;   Architecture designed; not implemented



AI:



&#x20;   Architecture designed; not implemented



PORTFOLIO:



&#x20;   Architecture designed; not implemented



BACKTESTING:



&#x20;   Architecture designed; not implemented



SIMULATION:



&#x20;   Architecture designed; not implemented



SELF LEARNING:



&#x20;   Architecture designed; not implemented



DATABASE:



&#x20;   Architecture/specification exists



CONFIGURATION:



&#x20;   Architecture/specification exists



LOGGING:



&#x20;   Architecture/specification exists



TESTING:



&#x20;   Architecture/specification exists



DEPLOYMENT:



&#x20;   Architecture/specification exists



CURRENT OBJECTIVE:



&#x20;   Continue Phase 28 implementation without violating the approved

&#x20;   architecture.



====================================================================

END OF PROJECT\_STATE

====================================================================

