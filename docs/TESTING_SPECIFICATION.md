====================================================================

SHADBOTTRADER

TESTING SPECIFICATION

====================================================================



DOCUMENT TYPE:

&#x20;   Canonical Testing Architecture and Implementation Specification



PROJECT:

&#x20;   ShadBotTrader



PROJECT TYPE:

&#x20;   Enterprise AI Trading Platform



PRIMARY LANGUAGE:

&#x20;   Python



ARCHITECTURE:

&#x20;   Clean Architecture

&#x20;   Domain-Driven Design

&#x20;   Event-Driven Architecture

&#x20;   Plugin-Oriented Architecture

&#x20;   Modular Architecture



====================================================================

1\. PURPOSE

====================================================================



This document defines the complete testing architecture,

testing strategy, testing standards, test organization,

quality gates, validation rules, and acceptance criteria

for the entire ShadBotTrader platform.



The purpose is to ensure that:



&#x20;   every domain rule is testable



&#x20;   every application use case is testable



&#x20;   every infrastructure adapter is testable



&#x20;   every integration boundary is testable



&#x20;   every trading operation is testable



&#x20;   every AI pipeline is testable



&#x20;   every portfolio calculation is testable



&#x20;   every backtest is reproducible



&#x20;   every simulation is deterministic



&#x20;   every plugin is isolated



&#x20;   every event is validated



&#x20;   every architectural rule is enforced



&#x20;   every deployment artifact is validated



&#x20;   every project-intelligence operation is testable



&#x20;   regressions are detected automatically



====================================================================

2\. FUNDAMENTAL TESTING PRINCIPLE

====================================================================



A feature is NOT considered implemented merely because code exists.



A feature is considered implemented only when:



&#x20;   code exists



&#x20;   unit tests exist



&#x20;   integration behavior is validated where required



&#x20;   edge cases are covered



&#x20;   failure behavior is tested



&#x20;   architectural constraints are respected



&#x20;   quality gates pass



====================================================================

3\. TESTING PYRAMID

====================================================================



The platform must follow a layered testing strategy.



Level 1:

&#x20;   Static Analysis



Level 2:

&#x20;   Unit Tests



Level 3:

&#x20;   Component Tests



Level 4:

&#x20;   Integration Tests



Level 5:

&#x20;   Contract Tests



Level 6:

&#x20;   Architecture Tests



Level 7:

&#x20;   End-to-End Tests



Level 8:

&#x20;   Trading Simulation Tests



Level 9:

&#x20;   Backtesting Validation



Level 10:

&#x20;   Performance Tests



Level 11:

&#x20;   Resilience Tests



Level 12:

&#x20;   Security Tests



Level 13:

&#x20;   Deployment Tests



====================================================================

4\. TESTING PYRAMID RULE

====================================================================



The majority of tests must be:



&#x20;   fast



&#x20;   deterministic



&#x20;   isolated



&#x20;   repeatable



&#x20;   local



Unit tests must represent the largest test layer.



End-to-end tests must represent a smaller but critical layer.



External services must not be required for ordinary unit tests.



====================================================================

5\. TEST DIRECTORY

====================================================================



Canonical test root:



&#x20;   tests/



Recommended structure:



&#x20;   tests/

&#x20;       unit/

&#x20;       component/

&#x20;       integration/

&#x20;       contract/

&#x20;       architecture/

&#x20;       e2e/

&#x20;       simulation/

&#x20;       backtesting/

&#x20;       performance/

&#x20;       resilience/

&#x20;       security/

&#x20;       deployment/

&#x20;       fixtures/

&#x20;       factories/

&#x20;       mocks/

&#x20;       helpers/



The exact directory structure may evolve, but the separation

of test responsibilities must remain.



====================================================================

6\. TEST NAMING

====================================================================



Test files must follow:



&#x20;   test\_<component>.py



Examples:



&#x20;   test\_symbol.py



&#x20;   test\_candle.py



&#x20;   test\_order.py



&#x20;   test\_position.py



&#x20;   test\_event\_bus.py



&#x20;   test\_application\_runtime.py



Test functions should describe behavior.



Preferred:



&#x20;   test\_order\_rejects\_negative\_quantity()



Avoid:



&#x20;   test\_order\_1()



====================================================================

7\. UNIT TESTS

====================================================================



Unit tests validate one isolated unit of behavior.



Typical units:



&#x20;   Entity



&#x20;   Value Object



&#x20;   Domain Service



&#x20;   Domain Rule



&#x20;   Application Service



&#x20;   Mapper



&#x20;   Validator



&#x20;   Calculator



&#x20;   Strategy



&#x20;   Risk Rule



&#x20;   Feature Transformer



&#x20;   Prediction Processor



Unit tests must avoid:



&#x20;   real database



&#x20;   real broker



&#x20;   real network



&#x20;   real filesystem where unnecessary



&#x20;   real external AI API



====================================================================

8\. DOMAIN TESTING

====================================================================



The Domain layer has the highest testing priority.



Every domain object must have tests for:



&#x20;   construction



&#x20;   valid state



&#x20;   invalid state



&#x20;   equality



&#x20;   identity



&#x20;   immutability where applicable



&#x20;   state transitions



&#x20;   business invariants



&#x20;   boundary values



&#x20;   exceptional conditions



====================================================================

9\. ENTITY TESTING

====================================================================



Entities must be tested for:



&#x20;   identity



&#x20;   equality semantics



&#x20;   lifecycle



&#x20;   valid initialization



&#x20;   invalid initialization



&#x20;   state mutation rules



&#x20;   invariant preservation



Example concepts:



&#x20;   Account



&#x20;   Position



&#x20;   Trade



&#x20;   Order



&#x20;   Prediction



====================================================================

10\. VALUE OBJECT TESTING

====================================================================



Value Objects must be tested for:



&#x20;   value equality



&#x20;   immutability



&#x20;   validation



&#x20;   normalization



&#x20;   invalid values



&#x20;   serialization where applicable



Examples:



&#x20;   Symbol



&#x20;   Timeframe



&#x20;   Price



&#x20;   Quantity



&#x20;   Currency



&#x20;   Percentage



====================================================================

11\. MARKET DATA TESTING

====================================================================



Market data tests must validate:



&#x20;   symbol



&#x20;   timestamp



&#x20;   open



&#x20;   high



&#x20;   low



&#x20;   close



&#x20;   volume



&#x20;   ordering



&#x20;   missing values



&#x20;   invalid values



&#x20;   duplicate timestamps



&#x20;   timezone handling



&#x20;   candle consistency



====================================================================

12\. CANDLE INVARIANTS

====================================================================



Tests must validate:



&#x20;   high >= open



&#x20;   high >= close



&#x20;   low <= open



&#x20;   low <= close



&#x20;   high >= low



&#x20;   volume >= 0



&#x20;   valid timestamp



&#x20;   valid symbol



Invalid candles must be rejected.



====================================================================

13\. TIMEFRAME TESTING

====================================================================



Test:



&#x20;   valid timeframe values



&#x20;   invalid timeframe values



&#x20;   conversion



&#x20;   comparison



&#x20;   ordering



&#x20;   serialization



&#x20;   parsing



====================================================================

14\. ORDER TESTING

====================================================================



Order tests must validate:



&#x20;   order creation



&#x20;   order type



&#x20;   side



&#x20;   quantity



&#x20;   price



&#x20;   status



&#x20;   timestamps



&#x20;   identifiers



&#x20;   validation



&#x20;   state transitions



&#x20;   cancellation



&#x20;   rejection



&#x20;   fill behavior



&#x20;   duplicate transitions



====================================================================

15\. ORDER STATE MACHINE

====================================================================



The valid order lifecycle must be explicitly tested.



Example:



&#x20;   CREATED

&#x20;       ↓

&#x20;   SUBMITTED

&#x20;       ↓

&#x20;   ACCEPTED

&#x20;       ↓

&#x20;   PARTIALLY\_FILLED

&#x20;       ↓

&#x20;   FILLED



Alternative:



&#x20;   CREATED

&#x20;       ↓

&#x20;   CANCELLED



Alternative:



&#x20;   SUBMITTED

&#x20;       ↓

&#x20;   REJECTED



Invalid transitions must fail.



Tests must explicitly verify invalid state transitions.



====================================================================

16\. POSITION TESTING

====================================================================



Position tests must cover:



&#x20;   opening



&#x20;   increasing



&#x20;   reducing



&#x20;   closing



&#x20;   long position



&#x20;   short position



&#x20;   average entry price



&#x20;   realized PnL



&#x20;   unrealized PnL



&#x20;   quantity



&#x20;   fees



&#x20;   partial close



&#x20;   complete close



&#x20;   invalid quantity



====================================================================

17\. TRADE TESTING

====================================================================



Test:



&#x20;   trade creation



&#x20;   entry



&#x20;   exit



&#x20;   quantity



&#x20;   price



&#x20;   fees



&#x20;   realized PnL



&#x20;   timestamps



&#x20;   linked order



&#x20;   linked position



====================================================================

18\. ACCOUNT TESTING

====================================================================



Test:



&#x20;   account creation



&#x20;   balance



&#x20;   equity



&#x20;   available balance



&#x20;   margin



&#x20;   exposure



&#x20;   account restrictions



&#x20;   invalid balances



====================================================================

19\. RISK MODEL TESTING

====================================================================



Risk tests are critical.



Test:



&#x20;   maximum position size



&#x20;   maximum exposure



&#x20;   maximum loss



&#x20;   drawdown limits



&#x20;   leverage limits



&#x20;   concentration limits



&#x20;   invalid orders



&#x20;   invalid market conditions



&#x20;   risk rejection



&#x20;   risk approval



====================================================================

20\. PREDICTION TESTING

====================================================================



Test:



&#x20;   prediction creation



&#x20;   model identifier



&#x20;   model version



&#x20;   timestamp



&#x20;   probability



&#x20;   confidence



&#x20;   predicted value



&#x20;   invalid confidence



&#x20;   invalid probability



====================================================================

21\. SIGNAL TESTING

====================================================================



Test:



&#x20;   BUY



&#x20;   SELL



&#x20;   HOLD



&#x20;   signal confidence



&#x20;   signal timestamp



&#x20;   strategy source



&#x20;   prediction source



&#x20;   invalid signal state



====================================================================

22\. DOMAIN INVARIANT TESTING

====================================================================



Every aggregate must enforce its invariants.



Tests must attempt to violate:



&#x20;   quantity constraints



&#x20;   balance constraints



&#x20;   position constraints



&#x20;   risk constraints



&#x20;   state constraints



&#x20;   timestamp constraints



&#x20;   financial constraints



and verify rejection.



====================================================================

23\. APPLICATION TESTING

====================================================================



Application tests validate orchestration.



They must verify:



&#x20;   correct service invocation



&#x20;   correct dependency usage



&#x20;   transaction boundaries



&#x20;   error propagation



&#x20;   command handling



&#x20;   query handling



&#x20;   lifecycle handling



&#x20;   event publication



Application tests should mock external dependencies.



====================================================================

24\. APPLICATION RUNTIME TESTING

====================================================================



Test:



&#x20;   startup



&#x20;   bootstrap



&#x20;   initialization



&#x20;   service registration



&#x20;   service resolution



&#x20;   runtime execution



&#x20;   shutdown



&#x20;   failure during startup



&#x20;   failure during shutdown



&#x20;   duplicate startup



&#x20;   duplicate shutdown



====================================================================

25\. DEPENDENCY CONTAINER TESTING

====================================================================



Test:



&#x20;   registration



&#x20;   resolution



&#x20;   singleton lifetime



&#x20;   transient lifetime



&#x20;   scoped lifetime if supported



&#x20;   missing dependency



&#x20;   duplicate registration



&#x20;   circular dependency



&#x20;   invalid registration



====================================================================

26\. EVENT BUS TESTING

====================================================================



Test:



&#x20;   event creation



&#x20;   event publication



&#x20;   event subscription



&#x20;   multiple subscribers



&#x20;   event ordering



&#x20;   handler failure



&#x20;   unknown event



&#x20;   duplicate subscription



&#x20;   unsubscribe



&#x20;   isolation



====================================================================

27\. EVENT DELIVERY GUARANTEES

====================================================================



The Event Bus must have explicit tests for its guarantees.



Depending on implementation:



&#x20;   at-most-once



&#x20;   at-least-once



&#x20;   exactly-once



must never be assumed.



The implemented guarantee must be documented and tested.



====================================================================

28\. PLUGIN TESTING

====================================================================



Each plugin must be tested for:



&#x20;   discovery



&#x20;   registration



&#x20;   initialization



&#x20;   activation



&#x20;   deactivation



&#x20;   shutdown



&#x20;   dependency validation



&#x20;   version compatibility



&#x20;   capability declaration



&#x20;   failure isolation



====================================================================

29\. PLUGIN ISOLATION

====================================================================



A failing plugin must not silently corrupt unrelated platform

components.



Tests must verify:



&#x20;   plugin failure



&#x20;   plugin timeout



&#x20;   plugin initialization failure



&#x20;   plugin shutdown failure



&#x20;   invalid plugin metadata



====================================================================

30\. INFRASTRUCTURE TESTING

====================================================================



Infrastructure adapters must be tested independently.



Examples:



&#x20;   database



&#x20;   filesystem



&#x20;   broker



&#x20;   market data provider



&#x20;   AI runtime



&#x20;   message transport



&#x20;   cache



====================================================================

31\. REPOSITORY TESTING

====================================================================



Repositories require:



&#x20;   unit tests for repository logic



&#x20;   integration tests for real persistence



Test:



&#x20;   create



&#x20;   read



&#x20;   update



&#x20;   delete



&#x20;   query



&#x20;   filtering



&#x20;   ordering



&#x20;   transactions



&#x20;   rollback



&#x20;   concurrency behavior where applicable



====================================================================

32\. DATABASE TESTING

====================================================================



Database tests must validate:



&#x20;   schema



&#x20;   migrations



&#x20;   constraints



&#x20;   indexes



&#x20;   foreign keys



&#x20;   unique constraints



&#x20;   nullable rules



&#x20;   precision



&#x20;   transaction behavior



&#x20;   rollback



&#x20;   consistency



====================================================================

33\. DATABASE MIGRATION TESTING

====================================================================



Every migration must be tested for:



&#x20;   upgrade



&#x20;   downgrade where supported



&#x20;   fresh installation



&#x20;   sequential migration



&#x20;   compatibility with existing schema



====================================================================

34\. MARKET DATA PROVIDER TESTING

====================================================================



Test adapters for:



&#x20;   successful response



&#x20;   malformed response



&#x20;   timeout



&#x20;   connection error



&#x20;   rate limit



&#x20;   duplicate data



&#x20;   stale data



&#x20;   missing candles



&#x20;   invalid prices



&#x20;   provider-specific errors



====================================================================

35\. BROKER ADAPTER TESTING

====================================================================



Broker adapters require contract tests.



Test:



&#x20;   submit order



&#x20;   cancel order



&#x20;   get order



&#x20;   get position



&#x20;   get balance



&#x20;   receive fill



&#x20;   rejection



&#x20;   timeout



&#x20;   network failure



&#x20;   authentication failure



&#x20;   duplicate submission



====================================================================

36\. BROKER SAFETY TESTING

====================================================================



Never allow tests to accidentally submit real production orders.



Default testing environment:



&#x20;   MOCK



or:



&#x20;   PAPER



Live broker execution must require explicit configuration.



====================================================================

37\. CONTRACT TESTING

====================================================================



Contract tests validate boundaries between:



&#x20;   application ↔ infrastructure



&#x20;   platform ↔ plugin



&#x20;   strategy ↔ engine



&#x20;   strategy ↔ risk



&#x20;   trading engine ↔ broker



&#x20;   AI engine ↔ model provider



&#x20;   repository ↔ database



&#x20;   API ↔ client



====================================================================

38\. API TESTING

====================================================================



Every API endpoint must validate:



&#x20;   request schema



&#x20;   authentication



&#x20;   authorization



&#x20;   validation



&#x20;   successful response



&#x20;   error response



&#x20;   status code



&#x20;   response schema



&#x20;   idempotency where applicable



&#x20;   pagination where applicable



====================================================================

39\. API ERROR CONTRACT

====================================================================



Errors must have deterministic structure.



Tests must validate:



&#x20;   error code



&#x20;   message



&#x20;   field errors



&#x20;   correlation ID



&#x20;   HTTP status



&#x20;   machine-readable structure



====================================================================

40\. FEATURE ENGINEERING TESTING

====================================================================



Feature tests must validate:



&#x20;   correct calculations



&#x20;   missing data



&#x20;   NaN



&#x20;   infinity



&#x20;   warmup periods



&#x20;   rolling windows



&#x20;   lookback periods



&#x20;   timestamp alignment



&#x20;   feature ordering



&#x20;   feature names



&#x20;   feature version



====================================================================

41\. LOOKAHEAD BIAS TESTING

====================================================================



This is mandatory for time-series systems.



Tests must ensure that a feature at time T cannot use information

from:



&#x20;   T+1



&#x20;   T+2



&#x20;   future timestamps



or any future observation.



Any detected future dependency must fail the test.



====================================================================

42\. AI MODEL TESTING

====================================================================



Models must be tested for:



&#x20;   input shape



&#x20;   output shape



&#x20;   dtype



&#x20;   prediction range



&#x20;   deterministic inference where expected



&#x20;   serialization



&#x20;   deserialization



&#x20;   version compatibility



&#x20;   missing input



&#x20;   invalid input



====================================================================

43\. MODEL REGISTRY TESTING

====================================================================



Test:



&#x20;   model registration



&#x20;   model versioning



&#x20;   retrieval



&#x20;   activation



&#x20;   deactivation



&#x20;   rollback



&#x20;   metadata



&#x20;   checksum



&#x20;   compatibility



====================================================================

44\. DATASET TESTING

====================================================================



Dataset validation must test:



&#x20;   schema



&#x20;   missing values



&#x20;   duplicates



&#x20;   ordering



&#x20;   timestamps



&#x20;   invalid prices



&#x20;   invalid volumes



&#x20;   leakage



&#x20;   train/test separation



&#x20;   version identity



====================================================================

45\. TRAINING PIPELINE TESTING

====================================================================



Test:



&#x20;   dataset loading



&#x20;   preprocessing



&#x20;   feature generation



&#x20;   splitting



&#x20;   training



&#x20;   validation



&#x20;   metric calculation



&#x20;   artifact generation



&#x20;   model registration



====================================================================

46\. PREDICTION PIPELINE TESTING

====================================================================



Test:



&#x20;   input retrieval



&#x20;   preprocessing



&#x20;   feature generation



&#x20;   model loading



&#x20;   inference



&#x20;   output validation



&#x20;   signal generation



&#x20;   error handling



====================================================================

47\. STRATEGY TESTING

====================================================================



Every strategy must be tested independently.



Test:



&#x20;   BUY conditions



&#x20;   SELL conditions



&#x20;   HOLD conditions



&#x20;   no-signal conditions



&#x20;   conflicting indicators



&#x20;   missing data



&#x20;   boundary conditions



&#x20;   deterministic behavior



====================================================================

48\. RISK PIPELINE TESTING

====================================================================



Test the sequence:



&#x20;   Signal

&#x20;       ↓

&#x20;   Risk Evaluation

&#x20;       ↓

&#x20;   Approved / Rejected

&#x20;       ↓

&#x20;   Order Generation



Verify that rejected signals cannot reach execution.



====================================================================

49\. TRADING PIPELINE TESTING

====================================================================



Canonical test flow:



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



End-to-end tests must validate this flow.



====================================================================

50\. PORTFOLIO TESTING

====================================================================



Test:



&#x20;   balance



&#x20;   equity



&#x20;   exposure



&#x20;   position aggregation



&#x20;   realized PnL



&#x20;   unrealized PnL



&#x20;   fees



&#x20;   drawdown



&#x20;   portfolio valuation



&#x20;   multi-position state



====================================================================

51\. PNL TESTING

====================================================================



PnL calculations must be tested with:



&#x20;   long trades



&#x20;   short trades



&#x20;   partial closes



&#x20;   multiple entries



&#x20;   multiple exits



&#x20;   fees



&#x20;   slippage



&#x20;   currency conversion



&#x20;   rounding



====================================================================

52\. BACKTESTING TESTING

====================================================================



Backtests must be:



&#x20;   deterministic



&#x20;   reproducible



&#x20;   isolated



&#x20;   versioned



Test:



&#x20;   same data + same configuration

&#x20;       =

&#x20;   same result



====================================================================

53\. BACKTESTING VALIDATION

====================================================================



Test:



&#x20;   initial capital



&#x20;   transaction costs



&#x20;   slippage



&#x20;   position sizing



&#x20;   order execution



&#x20;   strategy execution



&#x20;   portfolio accounting



&#x20;   equity curve



&#x20;   drawdown



&#x20;   trade statistics



====================================================================

54\. BACKTESTING LOOKAHEAD TEST

====================================================================



A backtest must never use future data.



Explicitly test:



&#x20;   feature timing



&#x20;   signal timing



&#x20;   order timing



&#x20;   execution timing



Any future information must fail the test.



====================================================================

55\. SIMULATION TESTING

====================================================================



Simulation tests must validate:



&#x20;   deterministic clock



&#x20;   market replay



&#x20;   order execution



&#x20;   fills



&#x20;   slippage



&#x20;   latency



&#x20;   fees



&#x20;   account updates



&#x20;   position updates



====================================================================

56\. REPLAY TESTING

====================================================================



Given identical:



&#x20;   market data



&#x20;   strategy



&#x20;   model



&#x20;   configuration



&#x20;   initial state



the replay must produce identical:



&#x20;   signals



&#x20;   orders



&#x20;   trades



&#x20;   positions



&#x20;   portfolio state



where deterministic behavior is specified.



====================================================================

57\. SELF-LEARNING TESTING

====================================================================



Self-learning must be heavily controlled.



Test:



&#x20;   feedback ingestion



&#x20;   evaluation



&#x20;   model selection



&#x20;   retraining



&#x20;   model validation



&#x20;   model promotion



&#x20;   rollback



No unvalidated model may automatically become live.



====================================================================

58\. MODEL PROMOTION TEST

====================================================================



A candidate model must not become production/live merely because:



&#x20;   training completed



or:



&#x20;   validation completed locally.



Promotion requires explicit validation gates.



====================================================================

59\. PROJECT INTELLIGENCE TESTING

====================================================================



Project Intelligence must be tested extensively.



Test:



&#x20;   filesystem scan



&#x20;   AST scan



&#x20;   Git scan



&#x20;   configuration scan



&#x20;   dependency scan



&#x20;   package scan



&#x20;   statistics scan



&#x20;   roadmap scan



&#x20;   decision scan



&#x20;   TODO scan



====================================================================

60\. PROJECT SNAPSHOT TESTING

====================================================================



Test that snapshots correctly capture:



&#x20;   files



&#x20;   modules



&#x20;   Git state



&#x20;   dependencies



&#x20;   statistics



&#x20;   architecture state



&#x20;   roadmap



&#x20;   decisions



&#x20;   TODOs



====================================================================

61\. PROJECT CONTEXT TESTING

====================================================================



Generated context must be:



&#x20;   deterministic



&#x20;   complete



&#x20;   readable



&#x20;   internally consistent



&#x20;   machine-consumable



Test that important project state is not silently omitted.



====================================================================

62\. PROJECT STATE REGRESSION TESTING

====================================================================



Given:



&#x20;   previous snapshot



&#x20;   current project



the system must correctly detect:



&#x20;   added files



&#x20;   deleted files



&#x20;   modified files



&#x20;   renamed files where supported



&#x20;   dependency changes



&#x20;   architecture changes



&#x20;   roadmap changes



====================================================================

63\. GENERATED DOCUMENT TESTING

====================================================================



Test generated:



&#x20;   Markdown



&#x20;   JSON



&#x20;   HTML



&#x20;   PDF



for:



&#x20;   valid syntax



&#x20;   expected sections



&#x20;   correct metadata



&#x20;   correct content



&#x20;   deterministic output where required



====================================================================

64\. ARCHITECTURE TESTING

====================================================================



Architecture tests must enforce:



&#x20;   Domain cannot import Infrastructure.



&#x20;   Domain cannot import Presentation.



&#x20;   Domain cannot import database implementation.



&#x20;   Domain cannot depend on external broker SDK.



&#x20;   Application cannot violate dependency direction.



&#x20;   Infrastructure may depend inward.



====================================================================

65\. CIRCULAR DEPENDENCY TESTING

====================================================================



Automated tests must detect:



&#x20;   circular imports



&#x20;   circular package dependencies



&#x20;   forbidden module cycles



A new circular dependency must fail CI.



====================================================================

66\. ARCHITECTURE BOUNDARY TESTING

====================================================================



Tests must verify boundaries between:



&#x20;   Core



&#x20;   Domain



&#x20;   Application



&#x20;   Infrastructure



&#x20;   Presentation



&#x20;   Project Intelligence



No unauthorized cross-layer dependency is allowed.



====================================================================

67\. STATIC ANALYSIS

====================================================================



Required tools:



&#x20;   Ruff



&#x20;   Black



&#x20;   Mypy



Canonical commands:



&#x20;   python -m ruff check .



&#x20;   python -m black --check .



&#x20;   python -m mypy src



====================================================================

68\. PYTEST

====================================================================



Primary testing framework:



&#x20;   pytest



Canonical command:



&#x20;   python -m pytest



Tests must be deterministic.



Randomness must use explicit seeds.



====================================================================

69\. TEST FIXTURES

====================================================================



Fixtures must provide controlled:



&#x20;   market data



&#x20;   candles



&#x20;   accounts



&#x20;   balances



&#x20;   orders



&#x20;   positions



&#x20;   trades



&#x20;   predictions



&#x20;   signals



&#x20;   portfolios



&#x20;   models



&#x20;   datasets



====================================================================

70\. TEST DATA

====================================================================



Test data must be:



&#x20;   deterministic



&#x20;   minimal where possible



&#x20;   representative



&#x20;   version controlled



&#x20;   safe



Never store:



&#x20;   API keys



&#x20;   passwords



&#x20;   broker credentials



&#x20;   production secrets



in test fixtures.



====================================================================

71\. FACTORIES

====================================================================



Factories may be used for complex test objects.



Examples:



&#x20;   OrderFactory



&#x20;   CandleFactory



&#x20;   AccountFactory



&#x20;   PositionFactory



&#x20;   TradeFactory



&#x20;   PortfolioFactory



Factories must produce valid objects by default.



Invalid object generation must be explicit.



====================================================================

72\. MOCKING RULES

====================================================================



Mocks are allowed when testing boundaries.



Do NOT mock the unit under test.



Do NOT overmock domain logic.



Prefer:



&#x20;   real domain objects



&#x20;   fake repositories



&#x20;   deterministic adapters



for unit/component tests.



====================================================================

73\. FAKE VS MOCK

====================================================================



Prefer Fakes when behavior matters.



Use Mocks when interaction verification matters.



Example:



&#x20;   FakeRepository



is preferred for repository-dependent application tests.



A Mock may be used when verifying:



&#x20;   publish()



&#x20;   execute()



&#x20;   save()



was called with specific arguments.



====================================================================

74\. PROPERTY-BASED TESTING

====================================================================



Financial calculations should use property-based testing where

appropriate.



Candidate areas:



&#x20;   PnL



&#x20;   position sizing



&#x20;   price transformations



&#x20;   portfolio accounting



&#x20;   risk calculations



Properties must represent business invariants.



====================================================================

75\. NUMERICAL PRECISION TESTING

====================================================================



Financial calculations must define precision rules.



Tests must explicitly cover:



&#x20;   floating point behavior



&#x20;   decimal precision



&#x20;   rounding



&#x20;   minimum quantity



&#x20;   tick size



&#x20;   price precision



&#x20;   fee precision



====================================================================

76\. TIME TESTING

====================================================================



Time-dependent components must use controllable clocks.



Avoid:



&#x20;   direct uncontrolled datetime.now()



inside test-sensitive domain/application logic.



Use:



&#x20;   Clock abstraction



&#x20;   FixedClock



&#x20;   TestClock



where architecture requires.



====================================================================

77\. TIMEZONE TESTING

====================================================================



Test:



&#x20;   UTC



&#x20;   timezone-aware timestamps



&#x20;   daylight-saving transitions



&#x20;   timestamp conversion



&#x20;   ordering



The canonical internal representation should be defined by the

architecture and tested consistently.



====================================================================

78\. CONCURRENCY TESTING

====================================================================



Components supporting concurrency must be tested for:



&#x20;   race conditions



&#x20;   duplicate execution



&#x20;   lost updates



&#x20;   deadlocks



&#x20;   inconsistent state



====================================================================

79\. IDEMPOTENCY TESTING

====================================================================



Operations that must be idempotent must explicitly be tested.



Examples:



&#x20;   order submission



&#x20;   event processing



&#x20;   state updates



&#x20;   snapshot generation



&#x20;   migration operations



====================================================================

80\. RESILIENCE TESTING

====================================================================



Test failures such as:



&#x20;   network timeout



&#x20;   database unavailable



&#x20;   broker unavailable



&#x20;   malformed response



&#x20;   AI service failure



&#x20;   plugin failure



&#x20;   corrupted data



&#x20;   invalid configuration



====================================================================

81\. RETRY TESTING

====================================================================



Where retry logic exists, test:



&#x20;   retry count



&#x20;   retry delay



&#x20;   retryable errors



&#x20;   non-retryable errors



&#x20;   eventual success



&#x20;   final failure



Retries must not create duplicate trades/orders.



====================================================================

82\. CIRCUIT BREAKER TESTING

====================================================================



If circuit breakers are implemented, test:



&#x20;   closed



&#x20;   open



&#x20;   half-open



&#x20;   recovery



&#x20;   repeated failure



====================================================================

83\. SECURITY TESTING

====================================================================



Security tests must cover:



&#x20;   authentication



&#x20;   authorization



&#x20;   secret handling



&#x20;   input validation



&#x20;   injection resistance



&#x20;   privilege boundaries



&#x20;   sensitive data exposure



====================================================================

84\. SECRET TESTING

====================================================================



Tests must ensure that secrets are not present in:



&#x20;   logs



&#x20;   exceptions



&#x20;   generated documentation



&#x20;   project snapshots



&#x20;   Git commits



&#x20;   API responses



====================================================================

85\. PERFORMANCE TESTING

====================================================================



Performance tests must eventually measure:



&#x20;   market ingestion throughput



&#x20;   feature calculation latency



&#x20;   prediction latency



&#x20;   strategy latency



&#x20;   risk latency



&#x20;   order processing latency



&#x20;   portfolio update latency



&#x20;   event bus throughput



&#x20;   snapshot generation



====================================================================

86\. PERFORMANCE REGRESSION

====================================================================



Important operations should have baseline measurements.



A significant unexplained regression must fail or flag CI according

to configured thresholds.



====================================================================

87\. LOAD TESTING

====================================================================



Load tests should simulate:



&#x20;   high candle volume



&#x20;   many symbols



&#x20;   many strategies



&#x20;   many events



&#x20;   large portfolios



&#x20;   large historical datasets



====================================================================

88\. END-TO-END TESTING

====================================================================



E2E tests must validate realistic platform workflows.



Example:



&#x20;   application startup



&#x20;   market data ingestion



&#x20;   feature generation



&#x20;   prediction



&#x20;   signal



&#x20;   risk evaluation



&#x20;   order generation



&#x20;   simulated execution



&#x20;   trade



&#x20;   position update



&#x20;   portfolio update



&#x20;   shutdown



====================================================================

89\. LIVE TRADING E2E

====================================================================



Real-money/live trading must NOT be part of ordinary CI.



Live execution tests require:



&#x20;   explicit environment



&#x20;   explicit authorization



&#x20;   isolated credentials



&#x20;   strict safety checks



&#x20;   manual approval where required



====================================================================

90\. PAPER TRADING

====================================================================



Paper trading should be used as an intermediate validation layer.



Tests should validate that:



&#x20;   paper execution



matches:



&#x20;   expected broker semantics



without risking capital.



====================================================================

91\. DEPLOYMENT TESTING

====================================================================



Deployment artifacts must be tested for:



&#x20;   configuration



&#x20;   startup



&#x20;   health checks



&#x20;   migrations



&#x20;   dependency availability



&#x20;   environment variables



&#x20;   logging



&#x20;   shutdown



====================================================================

92\. HEALTH CHECK TESTING

====================================================================



Health checks must distinguish:



&#x20;   process alive



&#x20;   application ready



&#x20;   dependency ready



A process being alive does not mean the application is healthy.



====================================================================

93\. CONFIGURATION TESTING

====================================================================



Test:



&#x20;   valid configuration



&#x20;   missing configuration



&#x20;   invalid configuration



&#x20;   conflicting configuration



&#x20;   environment overrides



&#x20;   default values



&#x20;   production restrictions



====================================================================

94\. TEST ENVIRONMENT SEPARATION

====================================================================



At minimum:



&#x20;   development



&#x20;   test



&#x20;   paper



&#x20;   production



must be logically separated.



Tests must never accidentally use production configuration.



====================================================================

95\. TEST DATABASE

====================================================================



Tests requiring persistence must use:



&#x20;   isolated test database



or:



&#x20;   disposable database



Never run destructive integration tests against production.



====================================================================

96\. TEST ISOLATION

====================================================================



Each test must leave the environment in a known state.



Avoid:



&#x20;   shared mutable global state



&#x20;   test ordering dependencies



&#x20;   persistent temporary files



&#x20;   leaked database transactions



====================================================================

97\. DETERMINISM

====================================================================



Tests must be deterministic.



Control:



&#x20;   random seeds



&#x20;   time



&#x20;   external data



&#x20;   environment



&#x20;   filesystem state



&#x20;   network responses



====================================================================

98\. FLAKY TEST POLICY

====================================================================



Flaky tests are defects.



Do NOT solve flakiness by:



&#x20;   increasing arbitrary sleep()



&#x20;   retrying the test indefinitely



&#x20;   disabling the test



&#x20;   marking everything xfail



The underlying cause must be fixed.



====================================================================

99\. TEST COVERAGE

====================================================================



Coverage is a metric, not the only quality criterion.



The project must prioritize:



&#x20;   business-critical behavior



&#x20;   financial calculations



&#x20;   risk rules



&#x20;   order state transitions



&#x20;   portfolio accounting



&#x20;   data integrity



&#x20;   AI data leakage



&#x20;   architectural boundaries



over superficial line coverage.



====================================================================

100\. COVERAGE REQUIREMENTS

====================================================================



The exact numeric threshold may evolve.



However:



&#x20;   Domain:

&#x20;       very high coverage required



&#x20;   Risk:

&#x20;       extremely high coverage required



&#x20;   Trading:

&#x20;       extremely high coverage required



&#x20;   Portfolio:

&#x20;       very high coverage required



&#x20;   Application:

&#x20;       high coverage required



&#x20;   Infrastructure:

&#x20;       meaningful integration coverage required



&#x20;   Generated documentation:

&#x20;       behavior/output coverage required



====================================================================

101\. TEST TAGGING

====================================================================



Tests should be categorizable.



Recommended markers:



&#x20;   unit



&#x20;   component



&#x20;   integration



&#x20;   contract



&#x20;   architecture



&#x20;   e2e



&#x20;   simulation



&#x20;   backtesting



&#x20;   performance



&#x20;   resilience



&#x20;   security



&#x20;   deployment



====================================================================

102\. FAST TEST SUITE

====================================================================



A fast suite must contain:



&#x20;   unit tests



&#x20;   lightweight component tests



&#x20;   architecture tests



The fast suite should be executable frequently during development.



====================================================================

103\. FULL TEST SUITE

====================================================================



The full suite must include:



&#x20;   unit



&#x20;   component



&#x20;   integration



&#x20;   contract



&#x20;   architecture



&#x20;   e2e



&#x20;   simulation



&#x20;   backtesting



&#x20;   resilience



&#x20;   security



where applicable.



====================================================================

104\. CI QUALITY GATE

====================================================================



Minimum CI gate:



&#x20;   ruff



&#x20;   black



&#x20;   mypy



&#x20;   pytest



Recommended extended CI:



&#x20;   architecture tests



&#x20;   integration tests



&#x20;   contract tests



&#x20;   coverage



&#x20;   security tests



====================================================================

105\. LOCAL QUALITY GATE

====================================================================



Before every meaningful commit:



&#x20;   python -m ruff check .



&#x20;   python -m black --check .



&#x20;   python -m mypy src



&#x20;   python -m pytest



All must pass.



====================================================================

106\. COMMIT RULE

====================================================================



A phase must NOT be committed as complete if:



&#x20;   tests fail



&#x20;   lint fails



&#x20;   formatting fails



&#x20;   type checking fails



&#x20;   architectural tests fail



unless the failure is explicitly documented as an approved

temporary blocker.



====================================================================

107\. REGRESSION TESTING

====================================================================



Every bug discovered in production or development must result in:



&#x20;   bug reproduction test



then:



&#x20;   implementation fix



then:



&#x20;   regression validation



The test must remain permanently unless the behavior is intentionally

removed.



====================================================================

108\. BUG FIX RULE

====================================================================



Never fix a bug only by changing implementation.



First establish:



&#x20;   failing reproduction



Then:



&#x20;   fix



Then:



&#x20;   passing regression test.



====================================================================

109\. TEST REVIEW

====================================================================



Every new subsystem must be reviewed for:



&#x20;   happy path



&#x20;   invalid input



&#x20;   boundary conditions



&#x20;   failure modes



&#x20;   concurrency where applicable



&#x20;   persistence



&#x20;   integration



&#x20;   security



&#x20;   observability



====================================================================

110\. TRADING SAFETY TESTS

====================================================================



The following conditions must have dedicated tests:



&#x20;   negative quantity



&#x20;   zero quantity



&#x20;   excessive quantity



&#x20;   invalid price



&#x20;   stale market data



&#x20;   insufficient balance



&#x20;   excessive exposure



&#x20;   duplicate order



&#x20;   duplicate event



&#x20;   duplicate fill



&#x20;   invalid order transition



&#x20;   broker rejection



&#x20;   risk rejection



====================================================================

111\. MARKET DATA SAFETY

====================================================================



Test that stale or invalid market data cannot silently generate

valid trading decisions.



Possible safeguards:



&#x20;   timestamp validation



&#x20;   freshness threshold



&#x20;   missing data detection



&#x20;   sequence validation



====================================================================

112\. DUPLICATE EXECUTION TEST

====================================================================



The platform must protect against duplicate execution.



Test scenarios:



&#x20;   same command twice



&#x20;   same event twice



&#x20;   broker response duplicated



&#x20;   retry after timeout



Expected result:



&#x20;   no unintended duplicate trade.



====================================================================

113\. PORTFOLIO CONSISTENCY TESTING

====================================================================



After every simulated execution, verify:



&#x20;   balance consistency



&#x20;   position consistency



&#x20;   trade consistency



&#x20;   order consistency



&#x20;   PnL consistency



&#x20;   equity consistency



====================================================================

114\. ACCOUNTING RECONCILIATION TESTING

====================================================================



The system should eventually support reconciliation tests between:



&#x20;   orders



&#x20;   fills



&#x20;   trades



&#x20;   positions



&#x20;   balances



&#x20;   portfolio state



Any inconsistency must be detectable.



====================================================================

115\. AI REPRODUCIBILITY

====================================================================



AI experiments must record sufficient metadata to reproduce results.



Tests should validate that metadata includes required:



&#x20;   model version



&#x20;   dataset version



&#x20;   feature version



&#x20;   configuration



&#x20;   random seed where applicable



====================================================================

116\. AI DATA LEAKAGE

====================================================================



Training pipelines must test for:



&#x20;   train/test contamination



&#x20;   future information



&#x20;   duplicated samples



&#x20;   target leakage



&#x20;   feature leakage



====================================================================

117\. MODEL DRIFT TESTING

====================================================================



Where monitoring exists, tests should validate:



&#x20;   drift detection



&#x20;   threshold behavior



&#x20;   alerting



&#x20;   model degradation handling



====================================================================

118\. DOCUMENTATION TESTING

====================================================================



Documentation generated by the system must be checked for:



&#x20;   required sections



&#x20;   valid references



&#x20;   valid JSON



&#x20;   valid Markdown



&#x20;   consistent state



&#x20;   correct timestamps



====================================================================

119\. PROJECT INTELLIGENCE CONSISTENCY

====================================================================



Test that:



&#x20;   ProjectSnapshot



&#x20;   ProjectContext



&#x20;   Roadmap



&#x20;   Decisions



&#x20;   Todo



&#x20;   Statistics



&#x20;   DependencyGraph



do not contradict one another.



====================================================================

120\. SNAPSHOT REPRODUCIBILITY

====================================================================



For an unchanged project state:



&#x20;   same scanner input

&#x20;       →

&#x20;   equivalent snapshot



Generated timestamps may be excluded from deterministic comparison

where necessary.



====================================================================

121\. TEST ARTIFACTS

====================================================================



Test execution may generate:



&#x20;   reports



&#x20;   coverage data



&#x20;   logs



&#x20;   temporary databases



&#x20;   snapshots



These must not pollute source control.



====================================================================

122\. GITIGNORE TEST ARTIFACTS

====================================================================



Generated test artifacts must be excluded from Git where they are

not canonical project artifacts.



Examples:



&#x20;   \_\_pycache\_\_



&#x20;   .pytest\_cache



&#x20;   .coverage



&#x20;   htmlcov



&#x20;   temporary logs



&#x20;   temporary databases



====================================================================

123\. TEST REPORTING

====================================================================



Test runs should provide:



&#x20;   pass count



&#x20;   failure count



&#x20;   skipped count



&#x20;   duration



&#x20;   coverage where enabled



&#x20;   failure details



====================================================================

124\. FAILURE ANALYSIS

====================================================================



A failing test must be investigated.



Do not simply rerun until it passes.



The agent must determine whether the failure is:



&#x20;   implementation bug



&#x20;   test bug



&#x20;   environment bug



&#x20;   dependency problem



&#x20;   race condition



&#x20;   flaky behavior



====================================================================

125\. TEST MAINTENANCE

====================================================================



Tests are production assets.



When architecture changes:



&#x20;   update tests



&#x20;   preserve intended behavior



&#x20;   remove obsolete tests



&#x20;   add new boundary tests



Do not delete tests merely to make CI green.



====================================================================

126\. TEST ARCHITECTURE EVOLUTION

====================================================================



As ShadBotTrader grows, the test architecture must grow with it.



New subsystem:



&#x20;   new tests



New domain rule:



&#x20;   invariant tests



New external integration:



&#x20;   contract tests



New critical workflow:



&#x20;   integration/E2E tests



New bug:



&#x20;   regression test



====================================================================

127\. MINIMUM ACCEPTANCE FOR A NEW MODULE

====================================================================



A new module is not complete until it has:



&#x20;   unit tests



&#x20;   validation tests



&#x20;   failure tests



&#x20;   integration tests where required



&#x20;   type correctness



&#x20;   lint correctness



&#x20;   documentation where required



====================================================================

128\. MINIMUM ACCEPTANCE FOR A NEW DOMAIN OBJECT

====================================================================



Required:



&#x20;   construction tests



&#x20;   invalid-state tests



&#x20;   invariant tests



&#x20;   equality/identity tests



&#x20;   edge-case tests



&#x20;   serialization tests where applicable



====================================================================

129\. MINIMUM ACCEPTANCE FOR A NEW APPLICATION SERVICE

====================================================================



Required:



&#x20;   success path



&#x20;   invalid input



&#x20;   dependency failure



&#x20;   domain failure



&#x20;   event behavior



&#x20;   transaction behavior where applicable



====================================================================

130\. MINIMUM ACCEPTANCE FOR A NEW INFRASTRUCTURE ADAPTER

====================================================================



Required:



&#x20;   adapter unit tests



&#x20;   fake/mock external behavior



&#x20;   contract tests



&#x20;   timeout test



&#x20;   failure test



&#x20;   malformed response test



&#x20;   integration test where practical



====================================================================

131\. MINIMUM ACCEPTANCE FOR A NEW TRADING STRATEGY

====================================================================



Required:



&#x20;   BUY test



&#x20;   SELL test



&#x20;   HOLD test



&#x20;   no-data test



&#x20;   boundary test



&#x20;   deterministic output test



&#x20;   lookahead-bias test



&#x20;   risk integration test



====================================================================

132\. MINIMUM ACCEPTANCE FOR A NEW AI MODEL

====================================================================



Required:



&#x20;   input validation



&#x20;   output validation



&#x20;   serialization



&#x20;   inference



&#x20;   version metadata



&#x20;   deterministic test where applicable



&#x20;   invalid-input test



&#x20;   model compatibility test



====================================================================

133\. MINIMUM ACCEPTANCE FOR A NEW DATABASE ENTITY

====================================================================



Required:



&#x20;   schema test



&#x20;   repository unit test



&#x20;   repository integration test



&#x20;   constraint tests



&#x20;   migration test



&#x20;   rollback test where supported



====================================================================

134\. MINIMUM ACCEPTANCE FOR PROJECT INTELLIGENCE

====================================================================



Every scanner must have tests for:



&#x20;   normal project



&#x20;   empty project



&#x20;   malformed file



&#x20;   missing file



&#x20;   permission error where applicable



&#x20;   unexpected structure



&#x20;   deterministic output



====================================================================

135\. TEST COMMAND REFERENCE

====================================================================



FAST:



&#x20;   python -m pytest -m unit



STATIC:



&#x20;   python -m ruff check .



FORMAT:



&#x20;   python -m black --check .



TYPES:



&#x20;   python -m mypy src



FULL:



&#x20;   python -m pytest



====================================================================

136\. RECOMMENDED EXTENDED COMMANDS

====================================================================



Coverage:



&#x20;   python -m pytest --cov=src



Architecture:



&#x20;   python -m pytest -m architecture



Integration:



&#x20;   python -m pytest -m integration



E2E:



&#x20;   python -m pytest -m e2e



Performance:



&#x20;   python -m pytest -m performance



====================================================================

137\. TEST EXECUTION ORDER

====================================================================



Recommended CI sequence:



&#x20;   1. dependency installation



&#x20;   2. Ruff



&#x20;   3. Black



&#x20;   4. Mypy



&#x20;   5. Unit tests



&#x20;   6. Component tests



&#x20;   7. Architecture tests



&#x20;   8. Integration tests



&#x20;   9. Contract tests



&#x20;   10. E2E tests



&#x20;   11. Security tests



&#x20;   12. Performance tests



====================================================================

138\. FAIL FAST POLICY

====================================================================



Cheap deterministic failures should be detected early.



Therefore:



&#x20;   lint/type failures



must be detected before:



&#x20;   expensive integration/performance tests.



====================================================================

139\. TEST ENVIRONMENT VARIABLES

====================================================================



Tests must explicitly identify their environment.



Example concept:



&#x20;   SHADBOTTRADER\_ENV=test



Production must never be selected accidentally.



====================================================================

140\. TEST CONFIGURATION

====================================================================



Test configuration must define:



&#x20;   database



&#x20;   broker mode



&#x20;   market data source



&#x20;   AI backend



&#x20;   logging



&#x20;   random seed



&#x20;   clock



&#x20;   filesystem isolation



====================================================================

141\. NETWORK POLICY

====================================================================



Ordinary unit tests must not require network access.



Integration tests may use:



&#x20;   controlled local services



&#x20;   test containers



&#x20;   sandbox APIs



&#x20;   recorded fixtures



where appropriate.



====================================================================

142\. EXTERNAL SERVICE RECORDING

====================================================================



When practical, external responses should be:



&#x20;   deterministic fixtures



or:



&#x20;   controlled mocks/fakes



Avoid tests that depend on changing public APIs.



====================================================================

143\. TEST CONTAINERS

====================================================================



If test containers are used, they must be:



&#x20;   isolated



&#x20;   reproducible



&#x20;   version pinned



&#x20;   disposable



====================================================================

144\. DATABASE TRANSACTION TESTING

====================================================================



Explicitly test:



&#x20;   commit



&#x20;   rollback



&#x20;   nested operation failure



&#x20;   constraint failure



&#x20;   partial failure



====================================================================

145\. EVENTUAL CONSISTENCY TESTING

====================================================================



If eventual consistency exists, tests must explicitly model it.



Never use arbitrary:



&#x20;   sleep(10)



to wait for state.



Use:



&#x20;   polling with timeout



&#x20;   deterministic synchronization



&#x20;   explicit event completion



====================================================================

146\. OBSERVABILITY TESTING

====================================================================



Critical operations should verify that required:



&#x20;   logs



&#x20;   metrics



&#x20;   events



&#x20;   correlation IDs



are generated.



====================================================================

147\. ERROR HANDLING TESTING

====================================================================



Every public boundary must define expected failures.



Tests must verify:



&#x20;   correct exception type



&#x20;   correct error code



&#x20;   correct state after failure



&#x20;   no partial corruption



====================================================================

148\. TRANSACTIONAL SAFETY

====================================================================



If an operation consists of multiple state changes and one step

fails, tests must verify that the system does not leave an invalid

partial state.



====================================================================

149\. ARCHITECTURAL REGRESSION

====================================================================



Architecture tests must run continuously.



A previously valid dependency direction must not silently become

invalid.



====================================================================

150\. TEST DOCUMENTATION

====================================================================



Complex tests should explain:



&#x20;   what invariant they protect



&#x20;   why the scenario matters



&#x20;   what regression they prevent



Do not write comments that merely restate the code.



====================================================================

151\. GOLDEN TESTS

====================================================================



Generated outputs may use golden/snapshot tests where appropriate.



Candidate outputs:



&#x20;   ProjectSnapshot



&#x20;   ChatGPT\_Context



&#x20;   Architecture documentation



&#x20;   Roadmap



&#x20;   DependencyGraph



Golden files must be intentionally updated.



====================================================================

152\. SNAPSHOT UPDATE RULE

====================================================================



Never blindly regenerate and accept all snapshots.



When a snapshot changes:



&#x20;   inspect the diff



&#x20;   verify the reason



&#x20;   confirm expected behavior



&#x20;   then update the golden artifact.



====================================================================

153\. TEST SECURITY BOUNDARY

====================================================================



Tests must never expose:



&#x20;   credentials



&#x20;   API keys



&#x20;   access tokens



&#x20;   private certificates



&#x20;   production account information



====================================================================

154\. LIVE TRADING PROTECTION

====================================================================



The test framework must have multiple protections against

accidental live trading.



Recommended:



&#x20;   test environment variable



&#x20;   broker mock



&#x20;   paper mode



&#x20;   explicit LIVE confirmation



&#x20;   separate credentials



====================================================================

155\. PRODUCTION DATA PROTECTION

====================================================================



Tests must never modify production:



&#x20;   database



&#x20;   files



&#x20;   broker account



&#x20;   portfolio



&#x20;   models



&#x20;   configuration



====================================================================

156\. ACCEPTANCE TESTING

====================================================================



Each major subsystem must have acceptance criteria.



Examples:



&#x20;   Domain:

&#x20;       invariants pass



&#x20;   Application:

&#x20;       use cases execute correctly



&#x20;   Trading:

&#x20;       safe order flow



&#x20;   Portfolio:

&#x20;       accounting remains consistent



&#x20;   AI:

&#x20;       no leakage



&#x20;   Backtesting:

&#x20;       reproducibility



&#x20;   Project Intelligence:

&#x20;       accurate project state



====================================================================

157\. RELEASE TESTING

====================================================================



Before release:



&#x20;   static checks pass



&#x20;   unit tests pass



&#x20;   integration tests pass



&#x20;   contract tests pass



&#x20;   architecture tests pass



&#x20;   E2E tests pass



&#x20;   security checks pass



&#x20;   migration tests pass



&#x20;   deployment tests pass



&#x20;   critical performance checks pass



====================================================================

158\. RELEASE BLOCKERS

====================================================================



Release must be blocked by:



&#x20;   failing critical tests



&#x20;   risk calculation failure



&#x20;   accounting inconsistency



&#x20;   order state inconsistency



&#x20;   architecture violation



&#x20;   security vulnerability



&#x20;   data leakage



&#x20;   model validation failure



&#x20;   migration failure



====================================================================

159\. TEST OWNERSHIP

====================================================================



Every subsystem should have clearly identifiable test ownership.



Conceptually:



&#x20;   Domain

&#x20;       → Domain Tests



&#x20;   Application

&#x20;       → Application Tests



&#x20;   Infrastructure

&#x20;       → Integration Tests



&#x20;   Trading

&#x20;       → Trading Tests



&#x20;   AI

&#x20;       → AI Tests



&#x20;   Project Intelligence

&#x20;       → Intelligence Tests



====================================================================

160\. TEST COMPLETENESS RULE

====================================================================



"100% tested" must never mean merely:



&#x20;   100% line coverage.



A subsystem is considered sufficiently tested only when:



&#x20;   behavior



&#x20;   invariants



&#x20;   errors



&#x20;   boundaries



&#x20;   integration



&#x20;   safety



are appropriately covered.



====================================================================

161\. FINAL QUALITY GATE

====================================================================



The minimum mandatory project gate is:



&#x20;   python -m ruff check .



&#x20;   python -m black --check .



&#x20;   python -m mypy src



&#x20;   python -m pytest



ALL MUST PASS.



====================================================================

162\. FINAL IMPLEMENTATION RULE

====================================================================



Every coding agent working on ShadBotTrader must follow:



&#x20;   INSPECT

&#x20;       ↓

&#x20;   IMPLEMENT

&#x20;       ↓

&#x20;   TEST

&#x20;       ↓

&#x20;   FIX

&#x20;       ↓

&#x20;   TEST AGAIN

&#x20;       ↓

&#x20;   RUN QUALITY GATE

&#x20;       ↓

&#x20;   UPDATE PROJECT STATE

&#x20;       ↓

&#x20;   COMMIT



====================================================================

163\. ABSOLUTE RULES

====================================================================



NEVER:



&#x20;   skip failing tests



&#x20;   weaken tests to make implementation pass



&#x20;   remove regression tests



&#x20;   disable type checking



&#x20;   disable linting



&#x20;   ignore architecture violations



&#x20;   use production credentials in tests



&#x20;   send real orders during CI



&#x20;   use future data in backtests



&#x20;   ignore numerical precision



&#x20;   accept flaky tests as normal



&#x20;   hide failures



====================================================================

164\. DEFINITION OF DONE

====================================================================



A task is DONE only when:



&#x20;   implementation complete



&#x20;   unit tests complete



&#x20;   integration tests complete where required



&#x20;   edge cases covered



&#x20;   failure paths covered



&#x20;   architecture validated



&#x20;   Ruff passes



&#x20;   Black passes



&#x20;   Mypy passes



&#x20;   Pytest passes



&#x20;   project state updated



&#x20;   documentation updated where required



&#x20;   Git commit created



====================================================================

165\. FINAL TESTING PHILOSOPHY

====================================================================



ShadBotTrader is a financial and AI platform.



Therefore testing is not a secondary development activity.



Testing is part of the architecture.



The platform must be designed so that:



&#x20;   incorrect financial calculations



&#x20;   unsafe trading behavior



&#x20;   data leakage



&#x20;   invalid state transitions



&#x20;   architectural violations



&#x20;   broken integrations



&#x20;   model regressions



&#x20;   project-state corruption



are detected before they can become production problems.



====================================================================

END OF TESTING\_SPECIFICATION

====================================================================

