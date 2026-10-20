================================================================================

SHADBOTTRADER

ENTERPRISE AI TRADING PLATFORM

================================================================================



PHASE 8 — SERVICE DESIGN

================================================================================



STATUS:

&#x20;   ARCHITECTURE DESIGN



ARCHITECTURE BASELINE:

&#x20;   PHASE 1 → PHASE 8



IMPLEMENTATION:

&#x20;   PHASE 28+



PRIMARY ARCHITECTURAL STYLE:

&#x20;   Clean Architecture

&#x20;   Domain-Driven Design

&#x20;   SOLID

&#x20;   Dependency Inversion

&#x20;   Dependency Injection

&#x20;   Event-Driven Architecture

&#x20;   Modular Architecture

&#x20;   Plugin Architecture



================================================================================

1\. PURPOSE

================================================================================



Phase 8 defines the Service Architecture of ShadBotTrader.



Services are the orchestration boundary between application intent,

domain behavior, engines, repositories, infrastructure abstractions,

and event publication.



The Service layer exists to answer:



&#x20;   "What operation does the application need to perform?"



Services coordinate work.



Services do NOT become the place where all business logic is dumped.



================================================================================

2\. CORE DEFINITION

================================================================================



SERVICE = APPLICATION OPERATION / COORDINATION



A Service:



&#x20;   receives a request

&#x20;   validates application-level requirements

&#x20;   loads required state

&#x20;   invokes domain behavior

&#x20;   invokes engines when specialized execution is required

&#x20;   persists state through abstractions

&#x20;   publishes events

&#x20;   returns a typed result



Conceptual:



&#x20;   Request

&#x20;      |

&#x20;      v

&#x20;   Service

&#x20;      |

&#x20;      +--> Domain

&#x20;      |

&#x20;      +--> Engine

&#x20;      |

&#x20;      +--> Repository

&#x20;      |

&#x20;      +--> External Port

&#x20;      |

&#x20;      +--> Event Bus

&#x20;      |

&#x20;      v

&#x20;   Result



================================================================================

3\. SERVICE IS NOT A GOD OBJECT

================================================================================



FORBIDDEN:



&#x20;   TradingService doing all trading

&#x20;   ApplicationService doing everything

&#x20;   AIService containing all AI logic

&#x20;   DataService containing all data logic

&#x20;   UniversalService



Services must have narrow responsibilities.



If a Service becomes too large:



&#x20;   split the capability

&#x20;   introduce specialized services

&#x20;   move domain logic into Domain

&#x20;   move technical execution into Engine

&#x20;   move persistence into Repository



================================================================================

4\. SERVICE CATEGORIES

================================================================================



ShadBotTrader defines several Service categories.



&#x20;   01. Application Services

&#x20;   02. Domain Services

&#x20;   03. Orchestration Services

&#x20;   04. Infrastructure Services

&#x20;   05. Integration Services

&#x20;   06. Runtime Services



These categories must not be confused.



================================================================================

5\. APPLICATION SERVICE

================================================================================



Application Service coordinates an application use case.



Example:



&#x20;   ExecuteTradeService

&#x20;   RunBacktestService

&#x20;   TrainModelService

&#x20;   UpdateDatasetService

&#x20;   GeneratePredictionService



Responsibilities:



&#x20;   receive use-case request

&#x20;   coordinate dependencies

&#x20;   enforce application-level constraints

&#x20;   manage use-case transaction boundary

&#x20;   invoke domain behavior

&#x20;   invoke engines

&#x20;   persist results

&#x20;   publish relevant events



Application Services should remain technology-independent.



================================================================================

6\. DOMAIN SERVICE

================================================================================



Domain Service contains domain logic that:



&#x20;   does not naturally belong to one Entity

&#x20;   does not naturally belong to one Value Object

&#x20;   represents a domain operation



Examples:



&#x20;   PositionSizingService

&#x20;   RiskCalculationService

&#x20;   PortfolioAllocationService

&#x20;   SignalEvaluationService



Domain Services must NOT depend on:



&#x20;   database

&#x20;   HTTP

&#x20;   broker SDK

&#x20;   filesystem

&#x20;   GUI

&#x20;   framework-specific infrastructure



================================================================================

7\. ORCHESTRATION SERVICE

================================================================================



Orchestration Services coordinate multi-step operations.



Example:



&#x20;   TrainingOrchestrator

&#x20;   BacktestOrchestrator

&#x20;   LiveTradingOrchestrator

&#x20;   DatasetUpdateOrchestrator



They coordinate:



&#x20;   Services

&#x20;   Engines

&#x20;   Repositories

&#x20;   Event Bus

&#x20;   Policies



They do NOT implement every step internally.



================================================================================

8\. INFRASTRUCTURE SERVICE

================================================================================



Infrastructure Services provide technical capabilities.



Examples:



&#x20;   ClockService

&#x20;   FileStorageService

&#x20;   CacheService

&#x20;   NetworkService

&#x20;   ProcessService



They belong to Infrastructure.



Application code depends on abstractions rather than concrete implementations.



================================================================================

9\. INTEGRATION SERVICE

================================================================================



Integration Services coordinate communication with external systems.



Examples:



&#x20;   BrokerIntegrationService

&#x20;   MarketDataIntegrationService

&#x20;   NewsIntegrationService

&#x20;   ModelRegistryIntegrationService



External vendor SDKs must remain behind adapters/interfaces.



================================================================================

10\. RUNTIME SERVICE

================================================================================



Runtime Services manage system-level execution.



Examples:



&#x20;   StartupService

&#x20;   ShutdownService

&#x20;   HealthService

&#x20;   SchedulingService



They operate at the application/runtime boundary.



================================================================================

11\. SERVICE CONTRACT

================================================================================



Every public Application Service should expose a clear typed contract.



Conceptually:



&#x20;   ServiceRequest

&#x20;         |

&#x20;         v

&#x20;   Service

&#x20;         |

&#x20;         v

&#x20;   ServiceResult



Example:



&#x20;   GeneratePredictionRequest

&#x20;         |

&#x20;         v

&#x20;   GeneratePredictionService

&#x20;         |

&#x20;         v

&#x20;   GeneratePredictionResult



Avoid:



&#x20;   dict\[str, Any]



as the primary Service contract.



================================================================================

12\. REQUEST MODEL

================================================================================



Requests represent intent.



A request may contain:



&#x20;   symbol

&#x20;   timeframe

&#x20;   timestamp

&#x20;   execution\_mode

&#x20;   strategy\_id

&#x20;   model\_id

&#x20;   account\_id

&#x20;   configuration reference



A request should contain what the use case needs.



It should not contain infrastructure objects.



FORBIDDEN:



&#x20;   request.database\_connection

&#x20;   request.broker\_client

&#x20;   request.http\_session



================================================================================

13\. RESULT MODEL

================================================================================



Services should return typed results.



A result may contain:



&#x20;   success

&#x20;   data

&#x20;   warnings

&#x20;   errors

&#x20;   metadata

&#x20;   execution\_id

&#x20;   correlation\_id



The result must distinguish:



&#x20;   business rejection

&#x20;   validation failure

&#x20;   technical failure



================================================================================

14\. SERVICE LIFECYCLE

================================================================================



Long-running Services may have lifecycle:



&#x20;   CREATED

&#x20;      |

&#x20;      v

&#x20;   INITIALIZING

&#x20;      |

&#x20;      v

&#x20;   READY

&#x20;      |

&#x20;      v

&#x20;   RUNNING

&#x20;      |

&#x20;      v

&#x20;   STOPPING

&#x20;      |

&#x20;      v

&#x20;   STOPPED



Short-lived Application Services generally do not need explicit lifecycle.



Their dependencies are managed by Runtime.



================================================================================

15\. SERVICE DEPENDENCY INJECTION

================================================================================



All dependencies must be explicit.



Example:



&#x20;   ExecuteTradeService(

&#x20;       order\_repository,

&#x20;       execution\_engine,

&#x20;       risk\_service,

&#x20;       event\_bus,

&#x20;       clock

&#x20;   )



FORBIDDEN:



&#x20;   global repository

&#x20;   global broker

&#x20;   hidden singleton

&#x20;   service locator inside business logic

&#x20;   creating infrastructure internally



================================================================================

16\. SERVICE DEPENDENCY RULE

================================================================================



Application Service may depend on:



&#x20;   Domain

&#x20;   Domain Services

&#x20;   Engine abstractions

&#x20;   Repository abstractions

&#x20;   Infrastructure abstractions

&#x20;   Event Bus abstraction



Application Service must NOT depend directly on:



&#x20;   concrete database driver

&#x20;   concrete broker SDK

&#x20;   concrete filesystem implementation

&#x20;   concrete cloud SDK



================================================================================

17\. DOMAIN SERVICE DEPENDENCY RULE

================================================================================



Domain Services should depend only on:



&#x20;   Domain objects

&#x20;   Domain abstractions

&#x20;   Domain policies



They should not depend on:



&#x20;   Application

&#x20;   Infrastructure

&#x20;   Engine implementations

&#x20;   GUI

&#x20;   external SDKs



================================================================================

18\. SERVICE → ENGINE

================================================================================



Services call Engines when specialized technical capability is required.



Example:



&#x20;   GeneratePredictionService

&#x20;           |

&#x20;           v

&#x20;       AIEngine

&#x20;           |

&#x20;           v

&#x20;       Prediction



The Service owns the use case.



The Engine owns the technical AI execution.



================================================================================

19\. SERVICE → DOMAIN

================================================================================



Services invoke domain behavior.



Example:



&#x20;   OpenPositionService

&#x20;           |

&#x20;           v

&#x20;       Position.open()



The Service should not reproduce:



&#x20;   Position business rules



inside itself.



================================================================================

20\. SERVICE → REPOSITORY

================================================================================



Services use repository abstractions.



Example:



&#x20;   TradeRepository

&#x20;   PositionRepository

&#x20;   AccountRepository

&#x20;   ModelRepository



Flow:



&#x20;   Service

&#x20;      |

&#x20;      v

&#x20;   Repository Interface

&#x20;      |

&#x20;      v

&#x20;   Infrastructure Implementation



================================================================================

21\. SERVICE → EVENT BUS

================================================================================



After meaningful state changes, Services may publish domain/application events.



Example:



&#x20;   ExecuteTradeService

&#x20;         |

&#x20;         v

&#x20;   Trade Executed

&#x20;         |

&#x20;         v

&#x20;      EventBus

&#x20;         |

&#x20;         +--> Portfolio

&#x20;         +--> Audit

&#x20;         +--> GUI

&#x20;         +--> Analytics



The Service must not directly call every interested subsystem.



================================================================================

22\. SERVICE TRANSACTION BOUNDARY

================================================================================



Application Services define use-case transaction boundaries.



Example:



&#x20;   ExecuteTradeService



may coordinate:



&#x20;   validate order

&#x20;   risk check

&#x20;   execute order

&#x20;   persist trade

&#x20;   update state

&#x20;   publish event



The exact transaction implementation belongs to Unit of Work / infrastructure

abstraction.



The Service owns the logical operation boundary.



================================================================================

23\. UNIT OF WORK

================================================================================



Where multiple persistence operations must be atomic:



&#x20;   Service

&#x20;      |

&#x20;      v

&#x20;   UnitOfWork

&#x20;      |

&#x20;      +--> Repository A

&#x20;      +--> Repository B

&#x20;      +--> Repository C

&#x20;      |

&#x20;      v

&#x20;   Commit



Rollback must be supported where the persistence backend requires it.



Services must not manually manage database connections.



================================================================================

24\. SERVICE ERROR MODEL

================================================================================



Errors should be typed.



Categories:



&#x20;   ValidationError

&#x20;   BusinessRuleViolation

&#x20;   NotFoundError

&#x20;   ConflictError

&#x20;   AuthorizationError

&#x20;   DependencyUnavailableError

&#x20;   ExecutionError

&#x20;   TimeoutError

&#x20;   PersistenceError

&#x20;   ExternalServiceError



Do not expose raw infrastructure exceptions directly to higher application

layers unless intentionally wrapped.



================================================================================

25\. SERVICE FAILURE HANDLING

================================================================================



A Service must distinguish:



&#x20;   expected business rejection



from:



&#x20;   unexpected technical failure



Example:



&#x20;   insufficient balance



is a business result.



Whereas:



&#x20;   database connection lost



is a technical failure.



These must not be represented identically.



================================================================================

26\. SERVICE RETRY POLICY

================================================================================



Services may request retryable operations through defined policies.



Retry must NOT be blindly applied.



Never automatically retry:



&#x20;   non-idempotent order execution



unless the system has explicit idempotency guarantees.



Retry policy belongs to orchestration/application infrastructure.



================================================================================

27\. IDEMPOTENCY

================================================================================



Critical Services must support idempotency where required.



Especially:



&#x20;   order submission

&#x20;   dataset update

&#x20;   model registration

&#x20;   event processing

&#x20;   portfolio state updates



Example:



&#x20;   execution\_id

&#x20;   request\_id

&#x20;   idempotency\_key



Repeated request must not accidentally duplicate an irreversible operation.



================================================================================

28\. SERVICE AUTHORIZATION

================================================================================



Where authorization exists, it must be enforced at the application boundary.



Example:



&#x20;   ExecuteTradeService



may verify:



&#x20;   account access

&#x20;   execution mode

&#x20;   allowed operation



Authorization must not be buried inside:



&#x20;   domain entity

&#x20;   broker adapter

&#x20;   database repository



================================================================================

29\. SERVICE VALIDATION

================================================================================



Three validation levels:



&#x20;   1. Request validation

&#x20;   2. Domain validation

&#x20;   3. Infrastructure validation



Request validation:



&#x20;   required fields

&#x20;   formats

&#x20;   ranges



Domain validation:



&#x20;   business rules



Infrastructure validation:



&#x20;   external technical constraints



Do not duplicate the same rule across all three layers.



================================================================================

30\. SERVICE SECURITY

================================================================================



Services must:



&#x20;   validate inputs

&#x20;   enforce authorization

&#x20;   prevent unsafe execution modes

&#x20;   protect sensitive data

&#x20;   avoid logging secrets

&#x20;   preserve audit information



Especially:



&#x20;   ExecuteTradeService

&#x20;   WithdrawService

&#x20;   AccountService

&#x20;   ModelManagementService

&#x20;   ConfigurationService



require strict controls.



================================================================================

31\. SERVICE AUDIT

================================================================================



Important Service operations must be auditable.



Audit fields may include:



&#x20;   service

&#x20;   operation

&#x20;   request\_id

&#x20;   execution\_id

&#x20;   timestamp

&#x20;   actor

&#x20;   account

&#x20;   result

&#x20;   reason



Never store secrets in audit logs.



================================================================================

32\. SERVICE OBSERVABILITY

================================================================================



Services should produce:



&#x20;   execution count

&#x20;   success count

&#x20;   failure count

&#x20;   latency

&#x20;   dependency failures



Metrics should contain:



&#x20;   service\_name

&#x20;   operation

&#x20;   result

&#x20;   duration



Avoid excessive high-cardinality labels.



================================================================================

33\. SERVICE CORRELATION

================================================================================



Every significant application operation should support:



&#x20;   correlation\_id



and where appropriate:



&#x20;   execution\_id



Example:



&#x20;   User Request

&#x20;        |

&#x20;        v

&#x20;   correlation\_id

&#x20;        |

&#x20;        +--> Service

&#x20;        +--> Engine

&#x20;        +--> Repository

&#x20;        +--> Event

&#x20;        +--> Audit



This allows complete operation tracing.



================================================================================

34\. SERVICE CANCELLATION

================================================================================



Long-running Services must support cancellation where appropriate.



Examples:



&#x20;   training

&#x20;   optimization

&#x20;   backtest

&#x20;   dataset processing



Cancellation must:



&#x20;   stop safely

&#x20;   release resources

&#x20;   preserve state

&#x20;   publish completion/cancellation status



================================================================================

35\. SERVICE TIMEOUT

================================================================================



Timeouts must be explicit.



Examples:



&#x20;   GeneratePredictionService

&#x20;   ExecuteTradeService

&#x20;   ExternalNewsService



Timeout must not automatically mean:



&#x20;   operation failed permanently



The operation state must be evaluated.



Especially dangerous:



&#x20;   order submission timeout



because the broker may have accepted the order even if the response was lost.



================================================================================

36\. SERVICE CACHING

================================================================================



Services may use caching through an abstraction.



Caching must not change business correctness.



Never cache mutable trading state without explicit consistency rules.



Suitable examples:



&#x20;   model metadata

&#x20;   static configuration

&#x20;   symbol metadata

&#x20;   historical reference data



================================================================================

37\. SERVICE CONCURRENCY

================================================================================



Services may execute concurrently.



Concurrency rules must protect:



&#x20;   account state

&#x20;   portfolio state

&#x20;   order state

&#x20;   model state

&#x20;   dataset state



Critical state transitions must be atomic according to the domain and

persistence model.



================================================================================

38\. SERVICE SCHEDULING

================================================================================



Scheduling belongs to:



&#x20;   Scheduler

&#x20;   Runtime

&#x20;   Pipeline



NOT inside individual business Services.



Example:



&#x20;   Scheduler

&#x20;       |

&#x20;       v

&#x20;   DatasetUpdateService



not:



&#x20;   DatasetUpdateService

&#x20;       |

&#x20;       v

&#x20;   infinite loop



================================================================================

39\. SERVICE COMPOSITION

================================================================================



Services may call other Services when appropriate.



However, excessive nesting is forbidden.



Bad:



&#x20;   ServiceA

&#x20;     -> ServiceB

&#x20;        -> ServiceC

&#x20;           -> ServiceD

&#x20;              -> ServiceE



This creates hidden workflow complexity.



Prefer:



&#x20;   Orchestrator

&#x20;      |

&#x20;      +--> Service A

&#x20;      +--> Service B

&#x20;      +--> Service C



================================================================================

40\. APPLICATION SERVICE NAMING

================================================================================



Use explicit names.



Examples:



&#x20;   GeneratePredictionService

&#x20;   ExecuteTradeService

&#x20;   OpenPositionService

&#x20;   ClosePositionService

&#x20;   RunBacktestService

&#x20;   RunReplayService

&#x20;   TrainModelService

&#x20;   EvaluateModelService

&#x20;   UpdateDatasetService

&#x20;   RegisterModelService



Avoid:



&#x20;   Manager

&#x20;   Helper

&#x20;   Utility

&#x20;   Processor

&#x20;   Handler



unless the responsibility genuinely requires that abstraction.



================================================================================

41\. DOMAIN SERVICE NAMING

================================================================================



Examples:



&#x20;   RiskCalculationService

&#x20;   PositionSizingService

&#x20;   PortfolioAllocationService

&#x20;   SignalEvaluationService



Domain Service names should express business capability.



================================================================================

42\. TRADING SERVICES

================================================================================



Canonical Trading Services:



&#x20;   CreateOrderService

&#x20;   ValidateOrderService

&#x20;   RiskCheckService

&#x20;   ExecuteOrderService

&#x20;   CancelOrderService

&#x20;   PositionOpenService

&#x20;   PositionCloseService

&#x20;   TradeSettlementService



These Services coordinate trading operations.



They do not directly implement broker SDK calls.



================================================================================

43\. PREDICTION SERVICES

================================================================================



Canonical Prediction Services:



&#x20;   GeneratePredictionService

&#x20;   ValidatePredictionService

&#x20;   StorePredictionService

&#x20;   EvaluatePredictionService



Flow:



&#x20;   Request

&#x20;      |

&#x20;      v

&#x20;   GeneratePredictionService

&#x20;      |

&#x20;      +--> Context

&#x20;      +--> Feature

&#x20;      +--> AI Engine

&#x20;      |

&#x20;      v

&#x20;   Prediction

&#x20;      |

&#x20;      v

&#x20;   Validation

&#x20;      |

&#x20;      v

&#x20;   Persistence/Event



================================================================================

44\. TRAINING SERVICES

================================================================================



Canonical:



&#x20;   PrepareTrainingDataService

&#x20;   TrainModelService

&#x20;   EvaluateModelService

&#x20;   ValidateModelService

&#x20;   RegisterModelService



Training flow:



&#x20;   Dataset

&#x20;      |

&#x20;      v

&#x20;   Prepare

&#x20;      |

&#x20;      v

&#x20;   Train

&#x20;      |

&#x20;      v

&#x20;   Evaluate

&#x20;      |

&#x20;      v

&#x20;   Validate

&#x20;      |

&#x20;      v

&#x20;   Register



AI Engine performs model computation.



Training Pipeline controls workflow.



Services coordinate use cases.



================================================================================

45\. BACKTEST SERVICES

================================================================================



Canonical:



&#x20;   PrepareBacktestService

&#x20;   RunBacktestService

&#x20;   AnalyzeBacktestService

&#x20;   StoreBacktestResultService



Flow:



&#x20;   Backtest Request

&#x20;        |

&#x20;        v

&#x20;   RunBacktestService

&#x20;        |

&#x20;        +--> SimulationEngine

&#x20;        +--> Strategy

&#x20;        +--> Data

&#x20;        +--> Portfolio

&#x20;        |

&#x20;        v

&#x20;   Backtest Result



================================================================================

46\. REPLAY SERVICES

================================================================================



Canonical:



&#x20;   PrepareReplayService

&#x20;   RunReplayService

&#x20;   PauseReplayService

&#x20;   ResumeReplayService

&#x20;   StopReplayService



Replay must use controlled simulation/time progression.



It must never call Live Execution.



================================================================================

47\. DATA SERVICES

================================================================================



Canonical:



&#x20;   IngestMarketDataService

&#x20;   UpdateDatasetService

&#x20;   ValidateDatasetService

&#x20;   NormalizeDatasetService

&#x20;   ArchiveDatasetService



Data Services coordinate DataEngine and repositories.



================================================================================

48\. PORTFOLIO SERVICES

================================================================================



Canonical:



&#x20;   GetPortfolioService

&#x20;   UpdatePortfolioService

&#x20;   CalculateExposureService

&#x20;   CalculatePnLService

&#x20;   RebalancePortfolioService



Portfolio business rules should remain in Domain where appropriate.



================================================================================

49\. NEWS SERVICES

================================================================================



Canonical:



&#x20;   FetchNewsService

&#x20;   NormalizeNewsService

&#x20;   AnalyzeNewsService

&#x20;   StoreNewsService

&#x20;   BuildNewsContextService



News Services may coordinate:



&#x20;   NewsEngine

&#x20;   AIEngine

&#x20;   repositories

&#x20;   EventBus



================================================================================

50\. MODEL SERVICES

================================================================================



Canonical:



&#x20;   LoadModelService

&#x20;   RegisterModelService

&#x20;   ActivateModelService

&#x20;   DeactivateModelService

&#x20;   ValidateModelService

&#x20;   EvaluateModelService



Model lifecycle must be explicit.



Never silently replace an active production model.



================================================================================

51\. CONFIGURATION SERVICES

================================================================================



Configuration Services may provide:



&#x20;   LoadConfigurationService

&#x20;   ValidateConfigurationService

&#x20;   ReloadConfigurationService



Runtime configuration changes must have explicit safety rules.



Trading-critical configuration should not be changed silently while live

execution is active.



================================================================================

52\. PROJECT INTELLIGENCE SERVICES

================================================================================



Project Intelligence will expose Services such as:



&#x20;   ScanProjectService

&#x20;   BuildProjectSnapshotService

&#x20;   BuildProjectContextService

&#x20;   GenerateProjectDocumentationService

&#x20;   GenerateHandoffService

&#x20;   DetectArchitectureChangesService



These Services coordinate the Project Intelligence subsystem.



================================================================================

53\. SERVICE EVENT MODEL

================================================================================



Examples:



&#x20;   PredictionGenerated

&#x20;   ModelTrained

&#x20;   ModelRegistered

&#x20;   DatasetUpdated

&#x20;   OrderCreated

&#x20;   OrderExecuted

&#x20;   OrderCancelled

&#x20;   PositionOpened

&#x20;   PositionClosed

&#x20;   PortfolioUpdated

&#x20;   BacktestCompleted

&#x20;   ReplayCompleted



Events represent facts.



Services may emit events after successful state transitions.



================================================================================

54\. COMMAND VS EVENT

================================================================================



COMMAND:



&#x20;   "Do this."



EVENT:



&#x20;   "This happened."



Example:



&#x20;   ExecuteTradeCommand



versus:



&#x20;   TradeExecutedEvent



Commands are requests.



Events are facts.



Do not confuse them.



================================================================================

55\. SERVICE COMMAND MODEL

================================================================================



Complex workflows may use explicit Commands.



Example:



&#x20;   ExecuteTradeCommand

&#x20;       |

&#x20;       v

&#x20;   ExecuteTradeService

&#x20;       |

&#x20;       v

&#x20;   ExecutionEngine

&#x20;       |

&#x20;       v

&#x20;   TradeExecutedEvent



This provides a clean application boundary.



================================================================================

56\. SERVICE EVENT HANDLERS

================================================================================



Event handlers react to facts.



Example:



&#x20;   TradeExecutedEvent

&#x20;        |

&#x20;        +--> UpdatePortfolioHandler

&#x20;        +--> AuditHandler

&#x20;        +--> NotificationHandler

&#x20;        +--> AnalyticsHandler



Handlers should be small.



Do not turn Event Handlers into hidden Services containing entire workflows.



================================================================================

57\. SERVICE TRANSACTION + EVENT ORDER

================================================================================



For persistent state changes:



&#x20;   Validate

&#x20;      |

&#x20;      v

&#x20;   Domain operation

&#x20;      |

&#x20;      v

&#x20;   Persist

&#x20;      |

&#x20;      v

&#x20;   Commit

&#x20;      |

&#x20;      v

&#x20;   Publish event



Where transactional event publishing is required:



&#x20;   Outbox Pattern



should be used.



Never publish a durable business event and then silently fail to persist the

state it describes.



================================================================================

58\. OUTBOX PATTERN

================================================================================



Critical flow:



&#x20;   Service

&#x20;      |

&#x20;      v

&#x20;   UnitOfWork

&#x20;      |

&#x20;      +--> Business State

&#x20;      |

&#x20;      +--> Outbox Event

&#x20;      |

&#x20;      v

&#x20;   COMMIT

&#x20;      |

&#x20;      v

&#x20;   Event Dispatcher

&#x20;      |

&#x20;      v

&#x20;   Event Bus



This guarantees stronger consistency between state and events.



================================================================================

59\. SERVICE RETRIES + IDEMPOTENCY

================================================================================



If a Service operation is retryable:



&#x20;   idempotency must be evaluated.



Especially:



&#x20;   ExecuteOrderService



must never blindly retry a broker request.



Safer model:



&#x20;   request\_id

&#x20;      |

&#x20;      v

&#x20;   idempotency check

&#x20;      |

&#x20;      +--> already executed -> return known result

&#x20;      |

&#x20;      +--> not executed -> execute

&#x20;                             |

&#x20;                             v

&#x20;                        persist result



================================================================================

60\. SERVICE AUTHORIZATION + EXECUTION MODE

================================================================================



Trading Services must explicitly receive or resolve:



&#x20;   LIVE

&#x20;   PAPER

&#x20;   SIMULATION



Example:



&#x20;   ExecuteOrderService

&#x20;          |

&#x20;          v

&#x20;   ExecutionMode

&#x20;          |

&#x20;      +---+---+

&#x20;      |   |   |

&#x20;     LIVE PAPER SIMULATION



Mode must never be inferred accidentally.



================================================================================

61\. SERVICE DEPENDENCY GRAPH

================================================================================



&#x20;                       APPLICATION

&#x20;                           |

&#x20;                           v

&#x20;                        SERVICE

&#x20;                    /      |      \\

&#x20;                   /       |       \\

&#x20;                  v        v        v

&#x20;              DOMAIN    ENGINE   REPOSITORY

&#x20;                  |        |        |

&#x20;                  |        |        v

&#x20;                  |        |   INFRASTRUCTURE

&#x20;                  |        |

&#x20;                  +--------+

&#x20;                       |

&#x20;                       v

&#x20;                   EVENT BUS



================================================================================

62\. SERVICE BOUNDARY RULE

================================================================================



A Service owns:



&#x20;   USE CASE COORDINATION



A Service does NOT own:



&#x20;   entire domain model

&#x20;   entire engine

&#x20;   entire repository system

&#x20;   entire infrastructure

&#x20;   entire pipeline



================================================================================

63\. SERVICE TESTING

================================================================================



Every Application Service requires:



&#x20;   unit tests

&#x20;   dependency tests

&#x20;   failure tests

&#x20;   authorization tests where applicable

&#x20;   idempotency tests where applicable

&#x20;   transaction tests where applicable

&#x20;   event publication tests



Critical trading services additionally require:



&#x20;   simulation integration tests

&#x20;   broker adapter contract tests

&#x20;   duplicate execution tests

&#x20;   timeout tests

&#x20;   failure recovery tests



================================================================================

64\. SERVICE TEST DOUBLE RULES

================================================================================



Use:



&#x20;   FakeRepository

&#x20;   FakeEngine

&#x20;   FakeEventBus

&#x20;   FakeClock

&#x20;   FakeBrokerAdapter



Tests must verify service behavior rather than implementation details.



================================================================================

65\. SERVICE PERFORMANCE

================================================================================



Services should remain thin.



Heavy computation belongs in:



&#x20;   Engine

&#x20;   Domain algorithm

&#x20;   specialized component



Example:



&#x20;   Service:

&#x20;       coordinates model inference



&#x20;   AIEngine:

&#x20;       performs model inference



Do not put a large NumPy/TensorFlow computation directly inside an

Application Service.



================================================================================

66\. SERVICE THREAD SAFETY

================================================================================



Application Services should preferably be stateless.



State belongs in:



&#x20;   Domain

&#x20;   repositories

&#x20;   runtime state

&#x20;   explicit state managers



Avoid mutable Service-level state.



================================================================================

67\. SERVICE STATE

================================================================================



Preferred:



&#x20;   Service instance

&#x20;       |

&#x20;       +--> immutable configuration

&#x20;       +--> injected dependencies



Avoid:



&#x20;   Service instance

&#x20;       |

&#x20;       +--> mutable account state

&#x20;       +--> mutable portfolio state

&#x20;       +--> mutable trading state



Persistent/business state belongs elsewhere.



================================================================================

68\. SERVICE SECURITY BOUNDARY

================================================================================



The Service layer is one of the main security boundaries.



It must ensure:



&#x20;   valid request

&#x20;   authorized operation

&#x20;   correct execution mode

&#x20;   correct account

&#x20;   correct state

&#x20;   correct dependencies



before invoking irreversible operations.



================================================================================

69\. SERVICE ARCHITECTURE WITH RUNTIME

================================================================================



&#x20;   Application

&#x20;      |

&#x20;      v

&#x20;   Runtime

&#x20;      |

&#x20;      +--> ServiceRegistry

&#x20;      |

&#x20;      +--> EngineRegistry

&#x20;      |

&#x20;      +--> EventBus

&#x20;      |

&#x20;      +--> Configuration

&#x20;      |

&#x20;      +--> Services

&#x20;                |

&#x20;                +--> Domain

&#x20;                +--> Engines

&#x20;                +--> Repositories

&#x20;                +--> Infrastructure



================================================================================

70\. SERVICE REGISTRY

================================================================================



A ServiceRegistry may resolve application services.



Responsibilities:



&#x20;   register

&#x20;   resolve

&#x20;   validate

&#x20;   list



It must not become a global service locator inside business code.



Dependency Injection should construct Services with explicit dependencies.



Registry is primarily a composition/runtime concern.



================================================================================

71\. SERVICE COMPOSITION ROOT

================================================================================



The composition root is responsible for:



&#x20;   creating dependencies

&#x20;   wiring implementations

&#x20;   constructing Services

&#x20;   registering Engines

&#x20;   registering handlers

&#x20;   creating Runtime



Business code must not perform composition.



Conceptual:



&#x20;   Bootstrap

&#x20;      |

&#x20;      v

&#x20;   Container

&#x20;      |

&#x20;      +--> Repositories

&#x20;      +--> Engines

&#x20;      +--> Services

&#x20;      +--> EventBus

&#x20;      +--> Runtime



================================================================================

72\. SERVICE VERSIONING

================================================================================



Public Service contracts should be versioned deliberately when external

consumers depend on them.



Internal refactoring is allowed as long as the contract remains compatible.



================================================================================

73\. SERVICE API BOUNDARY

================================================================================



GUI/API/CLI should not directly call:



&#x20;   Engine

&#x20;   Repository

&#x20;   Infrastructure



Preferred:



&#x20;   GUI/API/CLI

&#x20;         |

&#x20;         v

&#x20;      Application

&#x20;         |

&#x20;         v

&#x20;       Service

&#x20;         |

&#x20;         v

&#x20;       Engine/Domain

&#x20;         |

&#x20;         v

&#x20;     Infrastructure



================================================================================

74\. SERVICE + PIPELINE

================================================================================



Pipeline:



&#x20;   controls multi-step workflow



Service:



&#x20;   executes a specific application operation



Example:



&#x20;   Training Pipeline

&#x20;        |

&#x20;        +--> PrepareTrainingDataService

&#x20;        +--> TrainModelService

&#x20;        +--> EvaluateModelService

&#x20;        +--> RegisterModelService



Each Service remains independently testable.



================================================================================

75\. SERVICE + ENGINE

================================================================================



Example:



&#x20;   TrainModelService

&#x20;         |

&#x20;         v

&#x20;   AIEngine.train()



AIEngine does not decide:



&#x20;   whether training should happen



The Service/Pipeline decides that.



AIEngine performs:



&#x20;   model training computation.



================================================================================

76\. SERVICE + DOMAIN

================================================================================



Example:



&#x20;   OpenPositionService

&#x20;         |

&#x20;         v

&#x20;   Position.open()



The Domain controls:



&#x20;   valid position state transitions.



The Service controls:



&#x20;   when the use case is executed.



================================================================================

77\. SERVICE + EVENT BUS

================================================================================



Example:



&#x20;   ExecuteOrderService

&#x20;         |

&#x20;         v

&#x20;   Persist Trade

&#x20;         |

&#x20;         v

&#x20;   TradeExecutedEvent

&#x20;         |

&#x20;         v

&#x20;       EventBus



Consumers remain decoupled.



================================================================================

78\. SERVICE + PROJECT INTELLIGENCE

================================================================================



Project Intelligence Services may follow:



&#x20;   Scan

&#x20;     |

&#x20;     v

&#x20;   Snapshot

&#x20;     |

&#x20;     v

&#x20;   Analysis

&#x20;     |

&#x20;     v

&#x20;   Context

&#x20;     |

&#x20;     v

&#x20;   Insight

&#x20;     |

&#x20;     v

&#x20;   Recommendation

&#x20;     |

&#x20;     v

&#x20;   Decision

&#x20;     |

&#x20;     v

&#x20;   Export / Handoff



Services coordinate each stage.



Specialized Engines perform computational work.



================================================================================

79\. SERVICE DESIGN ANTI-PATTERNS

================================================================================



FORBIDDEN:



&#x20;   God Service

&#x20;   Service Locator everywhere

&#x20;   hidden dependencies

&#x20;   direct SQL

&#x20;   direct broker SDK calls

&#x20;   direct HTTP calls from domain

&#x20;   mutable global state

&#x20;   giant switch statements

&#x20;   generic UtilityService

&#x20;   HelperService dumping ground

&#x20;   business logic duplicated in Services

&#x20;   infrastructure exceptions leaking everywhere

&#x20;   uncontrolled nested Service calls

&#x20;   service-owned persistent state



================================================================================

80\. SERVICE PACKAGE ORGANIZATION

================================================================================



Conceptual structure:



&#x20;   application/

&#x20;       services/

&#x20;           trading/

&#x20;           prediction/

&#x20;           training/

&#x20;           portfolio/

&#x20;           backtest/

&#x20;           replay/

&#x20;           dataset/

&#x20;           news/

&#x20;           model/

&#x20;           configuration/

&#x20;           project/



&#x20;   domain/

&#x20;       services/



&#x20;   infrastructure/

&#x20;       services/



The exact project tree remains subject to the frozen Project Tree and later

implementation decisions.



================================================================================

81\. SERVICE IMPLEMENTATION RULE

================================================================================



When implementing a Service:



&#x20;   1. Define use case.

&#x20;   2. Define Request.

&#x20;   3. Define Result.

&#x20;   4. Identify dependencies.

&#x20;   5. Define transaction boundary.

&#x20;   6. Invoke Domain behavior.

&#x20;   7. Invoke Engine capability if required.

&#x20;   8. Persist through abstractions.

&#x20;   9. Publish events.

&#x20;   10. Return typed Result.

&#x20;   11. Add tests.

&#x20;   12. Pass quality gate.



================================================================================

82\. SERVICE QUALITY GATE

================================================================================



Every implementation must pass:



&#x20;   pytest

&#x20;   ruff

&#x20;   black

&#x20;   mypy



No Service is complete while the quality gate is failing.



Critical Services additionally require:



&#x20;   integration tests

&#x20;   failure tests

&#x20;   idempotency tests

&#x20;   authorization tests

&#x20;   transaction tests



================================================================================

83\. PHASE 8 COMPLETION CRITERIA

================================================================================



Phase 8 is architecturally complete when:



&#x20;   \[OK] Service definition is established.

&#x20;   \[OK] Application Service is defined.

&#x20;   \[OK] Domain Service is defined.

&#x20;   \[OK] Orchestration Service is defined.

&#x20;   \[OK] Infrastructure Service is defined.

&#x20;   \[OK] Integration Service is defined.

&#x20;   \[OK] Runtime Service is defined.

&#x20;   \[OK] Request contract is defined.

&#x20;   \[OK] Result contract is defined.

&#x20;   \[OK] Dependency injection is defined.

&#x20;   \[OK] Service → Domain boundary is defined.

&#x20;   \[OK] Service → Engine boundary is defined.

&#x20;   \[OK] Service → Repository boundary is defined.

&#x20;   \[OK] Service → Event Bus boundary is defined.

&#x20;   \[OK] Transaction boundary is defined.

&#x20;   \[OK] Error model is defined.

&#x20;   \[OK] Idempotency model is defined.

&#x20;   \[OK] Retry model is defined.

&#x20;   \[OK] Security boundary is defined.

&#x20;   \[OK] Observability is defined.

&#x20;   \[OK] Cancellation is defined.

&#x20;   \[OK] Service Registry is defined.

&#x20;   \[OK] Composition Root integration is defined.

&#x20;   \[OK] Trading Services are defined.

&#x20;   \[OK] Prediction Services are defined.

&#x20;   \[OK] Training Services are defined.

&#x20;   \[OK] Backtest Services are defined.

&#x20;   \[OK] Replay Services are defined.

&#x20;   \[OK] Data Services are defined.

&#x20;   \[OK] Portfolio Services are defined.

&#x20;   \[OK] News Services are defined.

&#x20;   \[OK] Model Services are defined.

&#x20;   \[OK] Project Intelligence Services are defined.

&#x20;   \[OK] Testing strategy is defined.



================================================================================

84\. FINAL ARCHITECTURAL RULE

================================================================================



THE MOST IMPORTANT RULE:



&#x20;   SERVICE = USE CASE COORDINATION



Pipeline says:



&#x20;   "This workflow must happen."



Service says:



&#x20;   "Perform this application operation."



Domain says:



&#x20;   "These are the business rules."



Engine says:



&#x20;   "I perform this specialized capability."



Repository says:



&#x20;   "I persist/retrieve this state."



Infrastructure says:



&#x20;   "I communicate with the external technical system."



Event Bus says:



&#x20;   "I transport facts/events."



Runtime says:



&#x20;   "I manage lifecycle."



================================================================================

85\. FINAL SHADBOTTRADER FLOW

================================================================================



&#x20;                        USER / GUI / API / CLI

&#x20;                                 |

&#x20;                                 v

&#x20;                            APPLICATION

&#x20;                                 |

&#x20;                                 v

&#x20;                             PIPELINE

&#x20;                                 |

&#x20;                                 v

&#x20;                              SERVICE

&#x20;                          /      |       \\

&#x20;                         /       |        \\

&#x20;                        v        v         v

&#x20;                    DOMAIN    ENGINE   REPOSITORY

&#x20;                        |        |         |

&#x20;                        |        |         v

&#x20;                        |        |   INFRASTRUCTURE

&#x20;                        |        |

&#x20;                        +--------+

&#x20;                             |

&#x20;                             v

&#x20;                         EVENT BUS

&#x20;                             |

&#x20;                +------------+------------+

&#x20;                |            |            |

&#x20;                v            v            v

&#x20;            Portfolio     GUI         Analytics





================================================================================

END OF PHASE 8 — SERVICE DESIGN

================================================================================

