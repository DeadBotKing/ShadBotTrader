====================================================================

SHADBOTTRADER

API\_AND\_CONTRACT\_SPECIFICATION

====================================================================



DOCUMENT TYPE:

&#x20;   Master API \& Contract Specification



PROJECT:

&#x20;   ShadBotTrader



PURPOSE:

&#x20;   This document defines the complete contractual boundaries of

&#x20;   ShadBotTrader.



&#x20;   It defines:



&#x20;       Interfaces

&#x20;       Ports

&#x20;       Application contracts

&#x20;       Domain contracts

&#x20;       Service contracts

&#x20;       Repository contracts

&#x20;       Provider contracts

&#x20;       Execution contracts

&#x20;       Strategy contracts

&#x20;       Risk contracts

&#x20;       Event contracts

&#x20;       Clock contracts

&#x20;       Simulation contracts

&#x20;       Backtesting contracts

&#x20;       Input contracts

&#x20;       Output contracts

&#x20;       Error contracts

&#x20;       Lifecycle contracts

&#x20;       Dependency rules

&#x20;       Side-effect rules

&#x20;       Idempotency requirements

&#x20;       Determinism requirements



&#x20;   This document is a binding implementation contract.



====================================================================

1\. FUNDAMENTAL RULE

====================================================================



The implementation MUST follow the contracts defined in this file.



An implementation agent MUST NOT:



&#x20;   invent alternate interfaces

&#x20;   rename contracts without architectural approval

&#x20;   bypass contracts

&#x20;   introduce hidden dependencies

&#x20;   couple Domain to Infrastructure

&#x20;   make Application services depend directly on concrete adapters

&#x20;   allow Strategy to execute orders

&#x20;   allow Prediction to bypass Risk

&#x20;   allow Signal to directly invoke Execution

&#x20;   allow Simulation to access Live Execution

&#x20;   allow Backtesting to access Live Execution

&#x20;   introduce global mutable state

&#x20;   silently change method semantics



If the existing implementation conflicts with this document:



&#x20;   1. Inspect the actual implementation.

&#x20;   2. Identify the conflict.

&#x20;   3. Determine whether the implementation or specification is newer.

&#x20;   4. Do not silently redesign the architecture.

&#x20;   5. Preserve backward compatibility where required.

&#x20;   6. Update documentation when an approved architectural change occurs.



====================================================================

2\. ARCHITECTURAL CONTRACT

====================================================================



ShadBotTrader uses:



&#x20;   Clean Architecture

&#x20;   Domain-Driven Design

&#x20;   Dependency Inversion

&#x20;   Explicit Contracts

&#x20;   Event-Oriented Communication



Dependency direction:



&#x20;   Interfaces

&#x20;       ↓

&#x20;   Application

&#x20;       ↓

&#x20;   Domain



Infrastructure implements contracts defined inward.



Therefore:



&#x20;   Domain

&#x20;       MUST NOT depend on Infrastructure.



&#x20;   Application

&#x20;       MUST NOT depend on concrete Infrastructure implementations.



&#x20;   Infrastructure

&#x20;       MAY depend on Application contracts.



&#x20;   Interfaces

&#x20;       MAY depend on Application.



====================================================================

3\. LAYER CONTRACT

====================================================================



DOMAIN

\------



Responsibilities:



&#x20;   business concepts

&#x20;   business rules

&#x20;   entities

&#x20;   value objects

&#x20;   aggregates

&#x20;   domain events

&#x20;   domain invariants



Domain MUST NOT:



&#x20;   access database

&#x20;   access filesystem

&#x20;   access network

&#x20;   access broker SDK

&#x20;   access environment variables directly

&#x20;   print to console

&#x20;   depend on CLI

&#x20;   depend on HTTP

&#x20;   depend on YAML implementation

&#x20;   depend on ORM





APPLICATION

\-----------



Responsibilities:



&#x20;   use cases

&#x20;   orchestration

&#x20;   workflows

&#x20;   application services

&#x20;   ports

&#x20;   commands

&#x20;   queries



Application MAY:



&#x20;   call Domain

&#x20;   call ports

&#x20;   publish events

&#x20;   coordinate repositories

&#x20;   coordinate execution



Application MUST NOT:



&#x20;   contain broker-specific implementation

&#x20;   contain SQL implementation

&#x20;   contain filesystem implementation

&#x20;   bypass domain invariants





INFRASTRUCTURE

\--------------



Responsibilities:



&#x20;   database

&#x20;   files

&#x20;   APIs

&#x20;   broker adapters

&#x20;   market data providers

&#x20;   event transport

&#x20;   logging implementations

&#x20;   configuration loading

&#x20;   external services



Infrastructure implements Application contracts.





INTERFACES

\----------



Responsibilities:



&#x20;   CLI

&#x20;   external input

&#x20;   presentation

&#x20;   command dispatch



Interfaces MUST NOT contain domain business logic.



====================================================================

4\. CONTRACT CATEGORIES

====================================================================



Contracts are divided into:



&#x20;   Domain Contracts

&#x20;   Application Contracts

&#x20;   Infrastructure Ports

&#x20;   Execution Contracts

&#x20;   Strategy Contracts

&#x20;   Risk Contracts

&#x20;   Portfolio Contracts

&#x20;   Event Contracts

&#x20;   Simulation Contracts

&#x20;   Backtesting Contracts

&#x20;   Persistence Contracts

&#x20;   Configuration Contracts

&#x20;   Lifecycle Contracts



====================================================================

5\. CONTRACT DESIGN RULES

====================================================================



Every contract MUST define:



&#x20;   Name

&#x20;   Responsibility

&#x20;   Inputs

&#x20;   Outputs

&#x20;   Errors

&#x20;   Side Effects

&#x20;   Dependencies

&#x20;   Lifecycle

&#x20;   Idempotency

&#x20;   Determinism requirements



Methods MUST have:



&#x20;   explicit parameters

&#x20;   explicit return types

&#x20;   explicit exceptions or failure semantics



Avoid:



&#x20;   Any

&#x20;   untyped dictionaries

&#x20;   implicit return values

&#x20;   hidden mutable state



Typed DTOs / Value Objects should be preferred.



====================================================================

6\. DOMAIN VALUE OBJECT CONTRACTS

====================================================================



6.1 SYMBOL

\--------------------------------------------------------------------



Concept:



&#x20;   Represents a tradable instrument identifier.



Contract:



&#x20;   Symbol(value: str)



Rules:



&#x20;   value MUST NOT be empty.

&#x20;   value MUST be normalized according to project convention.

&#x20;   whitespace-only values are invalid.



Properties:



&#x20;   value: str



Behavior:



&#x20;   immutable

&#x20;   equality by value

&#x20;   hashable



Forbidden:



&#x20;   Symbol accessing market data

&#x20;   Symbol accessing broker

&#x20;   Symbol accessing database





6.2 TIMEFRAME

\--------------------------------------------------------------------



Represents market-data resolution.



Examples:



&#x20;   M1

&#x20;   M5

&#x20;   M15

&#x20;   M30

&#x20;   H1

&#x20;   H4

&#x20;   D1



Contract:



&#x20;   TimeFrame(value)



Rules:



&#x20;   invalid timeframe MUST be rejected.



Behavior:



&#x20;   immutable

&#x20;   comparable

&#x20;   hashable





6.3 PRICE

\--------------------------------------------------------------------



Represents monetary price.



Rules:



&#x20;   MUST NOT be negative unless explicitly allowed by domain.

&#x20;   precision MUST be controlled.



Price MUST NOT be represented as uncontrolled floating-point

business state where financial precision matters.



Preferred implementation:



&#x20;   Decimal





6.4 QUANTITY

\--------------------------------------------------------------------



Represents trade/order quantity.



Rules:



&#x20;   quantity > 0



Invalid:



&#x20;   zero

&#x20;   negative

&#x20;   NaN

&#x20;   infinite





6.5 MONEY

\--------------------------------------------------------------------



Represents monetary amount.



Contains:



&#x20;   amount

&#x20;   currency



Rules:



&#x20;   currency MUST be valid.

&#x20;   arithmetic MUST preserve financial precision.





6.6 PERCENTAGE

\--------------------------------------------------------------------



Represents percentage values.



Rules:



&#x20;   valid range MUST be explicit.

&#x20;   conversion between ratio and percentage MUST be unambiguous.





6.7 IDENTIFIER

\--------------------------------------------------------------------



All domain entities SHOULD use explicit identifiers.



Examples:



&#x20;   OrderId

&#x20;   TradeId

&#x20;   PositionId

&#x20;   SignalId

&#x20;   PredictionId

&#x20;   AccountId

&#x20;   EventId

&#x20;   StrategyId

&#x20;   BacktestId



Identifiers MUST be unique within their defined scope.



====================================================================

7\. MARKET DATA CONTRACT

====================================================================



7.1 CANDLE



Candle represents one OHLCV observation.



Fields:



&#x20;   timestamp

&#x20;   symbol

&#x20;   timeframe

&#x20;   open

&#x20;   high

&#x20;   low

&#x20;   close

&#x20;   volume



Invariants:



&#x20;   high >= open

&#x20;   high >= close

&#x20;   low <= open

&#x20;   low <= close

&#x20;   high >= low

&#x20;   volume >= 0



Candle MUST be immutable after creation.



A candle MUST NOT be mutated by downstream consumers.





7.2 MARKET DATA PROVIDER

\--------------------------------------------------------------------



Contract:



&#x20;   MarketDataProvider



Responsibility:



&#x20;   Provide normalized market data to Application.



Required conceptual operations:



&#x20;   get\_latest(symbol, timeframe)

&#x20;   get\_history(symbol, timeframe, start, end)



Input:



&#x20;   Symbol

&#x20;   TimeFrame

&#x20;   time range



Output:



&#x20;   Candle or sequence of Candle



Rules:



&#x20;   returned candles MUST be chronologically ordered

&#x20;   returned data MUST conform to Candle invariants

&#x20;   provider-specific models MUST NOT leak into Domain



Errors:



&#x20;   MarketDataError

&#x20;   DataNotFoundError

&#x20;   DataValidationError

&#x20;   ProviderUnavailableError





7.3 MARKET DATA REPOSITORY

\--------------------------------------------------------------------



Contract:



&#x20;   MarketDataRepository



Responsibility:



&#x20;   Persist and retrieve normalized market data.



Operations:



&#x20;   save(candle)

&#x20;   save\_many(candles)

&#x20;   get\_latest(symbol, timeframe)

&#x20;   get\_range(symbol, timeframe, start, end)



Side Effects:



&#x20;   persistence



Idempotency:



&#x20;   saving the same uniquely identified candle SHOULD be idempotent.



====================================================================

8\. MARKET DATA VALIDATION CONTRACT

====================================================================



Contract:



&#x20;   MarketDataValidator



Input:



&#x20;   Candle

&#x20;   or sequence of Candle



Output:



&#x20;   ValidationResult



Must validate:



&#x20;   OHLC relationships

&#x20;   timestamp validity

&#x20;   symbol validity

&#x20;   timeframe validity

&#x20;   chronological order

&#x20;   duplicates

&#x20;   missing data

&#x20;   volume validity



Validation MUST be deterministic.



Validation MUST NOT modify source data.



====================================================================

9\. FEATURE CONTRACT

====================================================================



Feature calculation is a pure analytical operation.



Contract:



&#x20;   FeatureCalculator



Input:



&#x20;   historical market context



Output:



&#x20;   FeatureSet



Rules:



&#x20;   no future information

&#x20;   deterministic

&#x20;   reproducible

&#x20;   versionable



A feature calculator MUST NOT:



&#x20;   execute orders

&#x20;   modify portfolio

&#x20;   access broker

&#x20;   mutate market history



====================================================================

10\. FEATURE SET CONTRACT

====================================================================



FeatureSet represents calculated features at a specific point in time.



Must contain:



&#x20;   timestamp

&#x20;   symbol

&#x20;   feature values

&#x20;   feature version



Examples:



&#x20;   sma\_20

&#x20;   sma\_50

&#x20;   ema\_20

&#x20;   rsi\_14

&#x20;   macd

&#x20;   atr



Feature values MUST have explicit names and types.



====================================================================

11\. STRATEGY CONTRACT

====================================================================



11.1 STRATEGY



Contract:



&#x20;   Strategy



Responsibility:



&#x20;   Convert market context into a trading decision candidate.



Conceptual operation:



&#x20;   evaluate(context) -> Signal



Input may contain:



&#x20;   market data

&#x20;   features

&#x20;   portfolio context

&#x20;   optional prediction



Output:



&#x20;   Signal



Strategy MUST NOT:



&#x20;   submit orders

&#x20;   execute trades

&#x20;   access broker

&#x20;   directly mutate portfolio

&#x20;   directly persist trades

&#x20;   bypass risk management



Strategy MUST be deterministic unless explicitly declared otherwise.



====================================================================

12\. STRATEGY CONTEXT

====================================================================



StrategyContext may contain:



&#x20;   symbol

&#x20;   timestamp

&#x20;   latest candle

&#x20;   historical candles

&#x20;   features

&#x20;   current position

&#x20;   portfolio state

&#x20;   prediction

&#x20;   configuration



The context MUST contain only information available at evaluation

time.



====================================================================

13\. STRATEGY REGISTRY

====================================================================



Contract:



&#x20;   StrategyRegistry



Operations:



&#x20;   register(strategy)

&#x20;   get(strategy\_id)

&#x20;   list()



Rules:



&#x20;   strategy IDs MUST be unique.

&#x20;   registration MUST be explicit.

&#x20;   registry MUST NOT silently overwrite an existing strategy.



Errors:



&#x20;   StrategyAlreadyRegisteredError

&#x20;   StrategyNotFoundError



====================================================================

14\. SIGNAL CONTRACT

====================================================================



Signal represents a strategy decision.



Fields:



&#x20;   signal\_id

&#x20;   symbol

&#x20;   direction

&#x20;   strength

&#x20;   generated\_at

&#x20;   strategy\_id

&#x20;   metadata



Direction:



&#x20;   BUY

&#x20;   SELL

&#x20;   HOLD



Signal MUST NOT be executable by itself.



Signal MUST NOT contain broker-specific instructions.



====================================================================

15\. PREDICTION CONTRACT

====================================================================



Prediction represents model output.



Fields:



&#x20;   prediction\_id

&#x20;   symbol

&#x20;   predicted\_direction

&#x20;   probability

&#x20;   model\_id

&#x20;   model\_version

&#x20;   generated\_at

&#x20;   metadata



Rules:



&#x20;   probability MUST be within valid range.

&#x20;   prediction MUST be traceable to model/version.

&#x20;   prediction MUST NOT directly execute trades.



====================================================================

16\. PREDICTION PROVIDER CONTRACT

====================================================================



Contract:



&#x20;   PredictionProvider



Operation:



&#x20;   predict(context) -> Prediction



The provider MUST:



&#x20;   return typed Prediction

&#x20;   identify model

&#x20;   identify model version

&#x20;   provide generation timestamp



The provider MUST NOT:



&#x20;   execute orders

&#x20;   mutate portfolio

&#x20;   bypass Risk



AI failure MUST NOT corrupt portfolio state.



====================================================================

17\. RISK CONTRACT

====================================================================



17.1 RISK ENGINE



Contract:



&#x20;   RiskEngine



Operation:



&#x20;   evaluate(order\_candidate, portfolio\_context) -> RiskDecision



Output:



&#x20;   APPROVED

&#x20;   REJECTED



RiskDecision MUST contain:



&#x20;   decision

&#x20;   reason

&#x20;   evaluated\_at

&#x20;   rule identifiers

&#x20;   metadata



====================================================================

18\. RISK RULE CONTRACT

====================================================================



Contract:



&#x20;   RiskRule



Operation:



&#x20;   evaluate(context) -> RuleResult



Possible results:



&#x20;   PASS

&#x20;   FAIL



Examples:



&#x20;   MaximumPositionSizeRule

&#x20;   MaximumExposureRule

&#x20;   MaximumDailyLossRule

&#x20;   MaximumDrawdownRule

&#x20;   InsufficientBalanceRule



Rules MUST be independently testable.



====================================================================

19\. RISK INVARIANTS

====================================================================



No order may reach execution unless:



&#x20;   order validation passes

&#x20;   risk evaluation passes

&#x20;   execution mode permits operation



Risk rejection MUST prevent execution.



Risk decisions MUST be auditable.



====================================================================

20\. ORDER CONTRACT

====================================================================



Order represents execution intent.



Required fields:



&#x20;   order\_id

&#x20;   account\_id

&#x20;   symbol

&#x20;   side

&#x20;   type

&#x20;   quantity

&#x20;   price

&#x20;   status

&#x20;   created\_at

&#x20;   correlation\_id



Order statuses:



&#x20;   CREATED

&#x20;   VALIDATED

&#x20;   REJECTED

&#x20;   SUBMITTED

&#x20;   PARTIALLY\_FILLED

&#x20;   FILLED

&#x20;   CANCELLED

&#x20;   EXPIRED



====================================================================

21\. ORDER STATE MACHINE

====================================================================



Valid transitions:



&#x20;   CREATED

&#x20;       ↓

&#x20;   VALIDATED



&#x20;   CREATED

&#x20;       ↓

&#x20;   REJECTED



&#x20;   VALIDATED

&#x20;       ↓

&#x20;   SUBMITTED



&#x20;   SUBMITTED

&#x20;       ↓

&#x20;   PARTIALLY\_FILLED



&#x20;   SUBMITTED

&#x20;       ↓

&#x20;   FILLED



&#x20;   SUBMITTED

&#x20;       ↓

&#x20;   CANCELLED



&#x20;   SUBMITTED

&#x20;       ↓

&#x20;   EXPIRED



&#x20;   PARTIALLY\_FILLED

&#x20;       ↓

&#x20;   FILLED



&#x20;   PARTIALLY\_FILLED

&#x20;       ↓

&#x20;   CANCELLED



Invalid transitions MUST fail.



An order MUST NOT move backward in lifecycle.



====================================================================

22\. ORDER VALIDATOR

====================================================================



Contract:



&#x20;   OrderValidator



Operation:



&#x20;   validate(order, account\_context) -> ValidationResult



Must validate:



&#x20;   symbol

&#x20;   side

&#x20;   type

&#x20;   quantity

&#x20;   price

&#x20;   account availability

&#x20;   trading mode

&#x20;   order constraints



Validation MUST occur before execution.



====================================================================

23\. ORDER FACTORY

====================================================================



Contract:



&#x20;   OrderFactory



Responsibility:



&#x20;   Create valid Order objects.



Input:



&#x20;   Signal

&#x20;   RiskDecision

&#x20;   portfolio/account context

&#x20;   strategy configuration



Output:



&#x20;   Order



Rules:



&#x20;   RiskDecision MUST be APPROVED.

&#x20;   invalid inputs MUST fail.

&#x20;   factory MUST NOT execute order.



====================================================================

24\. EXECUTION CONTRACT

====================================================================



24.1 ORDER EXECUTOR



Contract:



&#x20;   OrderExecutor



Operations:



&#x20;   submit(order)

&#x20;   cancel(order\_id)

&#x20;   get\_status(order\_id)



Output:



&#x20;   ExecutionResult



The interface MUST be independent of broker technology.



====================================================================

25\. EXECUTION RESULT

====================================================================



ExecutionResult contains:



&#x20;   execution\_id

&#x20;   order\_id

&#x20;   status

&#x20;   filled\_quantity

&#x20;   average\_price

&#x20;   fees

&#x20;   executed\_at

&#x20;   metadata

&#x20;   correlation\_id



Possible execution statuses:



&#x20;   ACCEPTED

&#x20;   PARTIALLY\_FILLED

&#x20;   FILLED

&#x20;   REJECTED

&#x20;   CANCELLED

&#x20;   FAILED



====================================================================

26\. SIMULATED EXECUTOR

====================================================================



Contract:



&#x20;   SimulatedOrderExecutor



Responsibilities:



&#x20;   deterministic order matching

&#x20;   fees

&#x20;   slippage

&#x20;   fills

&#x20;   order lifecycle



MUST NOT:



&#x20;   contact network

&#x20;   contact broker

&#x20;   use live credentials



====================================================================

27\. PAPER EXECUTOR

====================================================================



Contract:



&#x20;   PaperOrderExecutor



Responsibilities:



&#x20;   emulate or use paper broker environment.



Must maintain the same OrderExecutor contract.



====================================================================

28\. LIVE EXECUTOR

====================================================================



Contract:



&#x20;   BrokerOrderExecutor



Responsibilities:



&#x20;   translate domain Order to broker-specific order

&#x20;   submit through broker API

&#x20;   translate broker response to ExecutionResult



Broker SDK types MUST NOT escape Infrastructure.



====================================================================

29\. EXECUTION MODE CONTRACT

====================================================================



Enum:



&#x20;   SIMULATION

&#x20;   PAPER

&#x20;   LIVE



Rules:



&#x20;   default = SIMULATION



LIVE MUST require explicit configuration.



Tests MUST NOT default to LIVE.



====================================================================

30\. TRADE CONTRACT

====================================================================



Trade represents executed financial activity.



Fields:



&#x20;   trade\_id

&#x20;   order\_id

&#x20;   symbol

&#x20;   side

&#x20;   quantity

&#x20;   entry\_price

&#x20;   exit\_price

&#x20;   opened\_at

&#x20;   closed\_at

&#x20;   fees

&#x20;   pnl

&#x20;   correlation\_id



Trade MUST be derived from actual execution results.



A Signal MUST NOT create a Trade.



====================================================================

31\. POSITION CONTRACT

====================================================================



Position represents current exposure.



Fields:



&#x20;   position\_id

&#x20;   symbol

&#x20;   side

&#x20;   quantity

&#x20;   average\_entry\_price

&#x20;   current\_price

&#x20;   realized\_pnl

&#x20;   unrealized\_pnl



Operations:



&#x20;   open

&#x20;   increase

&#x20;   decrease

&#x20;   close



Invalid position transitions MUST fail.



====================================================================

32\. POSITION SERVICE

====================================================================



Contract:



&#x20;   PositionService



Operations:



&#x20;   apply\_execution(execution\_result)

&#x20;   get\_position(symbol)

&#x20;   get\_all\_positions()



Responsibilities:



&#x20;   update positions from execution.



PositionService MUST NOT invent fills.



====================================================================

33\. PORTFOLIO CONTRACT

====================================================================



Portfolio contains:



&#x20;   cash

&#x20;   equity

&#x20;   positions

&#x20;   exposure

&#x20;   realized\_pnl

&#x20;   unrealized\_pnl

&#x20;   fees

&#x20;   drawdown



Portfolio state MUST be derived from valid financial events.



====================================================================

34\. PORTFOLIO SERVICE

====================================================================



Contract:



&#x20;   PortfolioService



Operations:



&#x20;   apply\_trade(trade)

&#x20;   update\_market\_price(symbol, price)

&#x20;   snapshot()

&#x20;   get\_equity()

&#x20;   get\_exposure()



PortfolioService MUST be deterministic.



====================================================================

35\. ACCOUNT CONTRACT

====================================================================



Account contains:



&#x20;   account\_id

&#x20;   currency

&#x20;   balance

&#x20;   status



Account status may include:



&#x20;   ACTIVE

&#x20;   SUSPENDED

&#x20;   CLOSED



Trading MUST NOT occur on an inactive account.



====================================================================

36\. BALANCE CONTRACT

====================================================================



Balance contains:



&#x20;   available

&#x20;   reserved

&#x20;   total

&#x20;   currency



Rules:



&#x20;   available >= 0

&#x20;   reserved >= 0

&#x20;   total >= available



Financial arithmetic must use appropriate precision.



====================================================================

37\. EVENT CONTRACT

====================================================================



Base contract:



&#x20;   Event



Required fields:



&#x20;   event\_id

&#x20;   event\_type

&#x20;   occurred\_at

&#x20;   source

&#x20;   correlation\_id

&#x20;   payload

&#x20;   metadata



Events SHOULD be immutable.



====================================================================

38\. REQUIRED EVENTS

====================================================================



Market:



&#x20;   MarketDataReceived

&#x20;   MarketDataValidated

&#x20;   MarketDataRejected



Strategy:



&#x20;   PredictionGenerated

&#x20;   SignalGenerated



Risk:



&#x20;   RiskApproved

&#x20;   RiskRejected



Orders:



&#x20;   OrderCreated

&#x20;   OrderValidated

&#x20;   OrderRejected

&#x20;   OrderSubmitted

&#x20;   OrderPartiallyFilled

&#x20;   OrderFilled

&#x20;   OrderCancelled

&#x20;   OrderExpired



Trading:



&#x20;   TradeOpened

&#x20;   TradeClosed



Portfolio:



&#x20;   PositionOpened

&#x20;   PositionUpdated

&#x20;   PositionClosed

&#x20;   PortfolioUpdated



Simulation:



&#x20;   SimulationStarted

&#x20;   SimulationCompleted



Backtesting:



&#x20;   BacktestStarted

&#x20;   BacktestCompleted

&#x20;   BacktestFailed



====================================================================

39\. EVENT BUS CONTRACT

====================================================================



Contract:



&#x20;   EventBus



Operations:



&#x20;   publish(event)

&#x20;   subscribe(event\_type, handler)

&#x20;   unsubscribe(event\_type, handler)



Rules:



&#x20;   handlers MUST be explicit.

&#x20;   event delivery MUST be observable.

&#x20;   event handlers MUST NOT mutate unrelated domain state.

&#x20;   failures MUST be handled according to configured policy.



====================================================================

40\. EVENT HANDLER CONTRACT

====================================================================



Contract:



&#x20;   EventHandler\[TEvent]



Operation:



&#x20;   handle(event) -> None



Handlers should be:



&#x20;   deterministic where possible

&#x20;   idempotent

&#x20;   independently testable



====================================================================

41\. EVENT IDEMPOTENCY

====================================================================



Events may be delivered more than once.



Handlers MUST protect against duplicate processing when the

operation is not naturally idempotent.



Use:



&#x20;   event\_id

&#x20;   execution\_id

&#x20;   correlation\_id



as appropriate.



====================================================================

42\. CLOCK CONTRACT

====================================================================



Contract:



&#x20;   Clock



Operation:



&#x20;   now() -> datetime



Implementations:



&#x20;   SystemClock

&#x20;   FixedClock

&#x20;   SimulationClock



Domain code MUST NOT directly call:



&#x20;   datetime.now()



when deterministic time is required.



====================================================================

43\. SIMULATION CLOCK

====================================================================



Contract:



&#x20;   SimulationClock



Operations:



&#x20;   now()

&#x20;   advance(timestamp)

&#x20;   reset()



Rules:



&#x20;   time MUST move forward according to simulation rules.

&#x20;   simulation MUST NOT depend on wall-clock time.



====================================================================

44\. REPOSITORY CONTRACT

====================================================================



Repositories provide persistence abstraction.



General contract:



&#x20;   save(entity)

&#x20;   get(id)

&#x20;   delete(id)

&#x20;   exists(id)



Concrete repositories may extend this contract.



Repositories MUST return Domain/Application models,

not infrastructure-specific models.



====================================================================

45\. ORDER REPOSITORY

====================================================================



Contract:



&#x20;   OrderRepository



Operations:



&#x20;   save(order)

&#x20;   get(order\_id)

&#x20;   list\_by\_account(account\_id)

&#x20;   list\_by\_status(status)



====================================================================

46\. TRADE REPOSITORY

====================================================================



Contract:



&#x20;   TradeRepository



Operations:



&#x20;   save(trade)

&#x20;   get(trade\_id)

&#x20;   list\_by\_account(account\_id)

&#x20;   list\_by\_symbol(symbol)

&#x20;   list\_by\_period(start, end)



====================================================================

47\. POSITION REPOSITORY

====================================================================



Contract:



&#x20;   PositionRepository



Operations:



&#x20;   save(position)

&#x20;   get(position\_id)

&#x20;   get\_by\_symbol(symbol)

&#x20;   list\_open(account\_id)



====================================================================

48\. PORTFOLIO REPOSITORY

====================================================================



Contract:



&#x20;   PortfolioRepository



Operations:



&#x20;   save\_snapshot(snapshot)

&#x20;   get\_latest(account\_id)

&#x20;   list\_snapshots(account\_id, start, end)



====================================================================

49\. SIGNAL REPOSITORY

====================================================================



Contract:



&#x20;   SignalRepository



Operations:



&#x20;   save(signal)

&#x20;   get(signal\_id)

&#x20;   list\_by\_strategy(strategy\_id)

&#x20;   list\_by\_symbol(symbol)



====================================================================

50\. PREDICTION REPOSITORY

====================================================================



Contract:



&#x20;   PredictionRepository



Operations:



&#x20;   save(prediction)

&#x20;   get(prediction\_id)

&#x20;   list\_by\_model(model\_id)

&#x20;   list\_by\_symbol(symbol)



====================================================================

51\. EVENT REPOSITORY

====================================================================



Contract:



&#x20;   EventRepository



Operations:



&#x20;   append(event)

&#x20;   get(event\_id)

&#x20;   list\_by\_correlation(correlation\_id)

&#x20;   list\_by\_type(event\_type)



Events should be append-only.



Existing events MUST NOT be silently modified.



====================================================================

52\. UNIT OF WORK CONTRACT

====================================================================



Contract:



&#x20;   UnitOfWork



Operations:



&#x20;   commit()

&#x20;   rollback()



Repositories may be exposed through UnitOfWork.



Example conceptual flow:



&#x20;   begin

&#x20;      ↓

&#x20;   modify domain

&#x20;      ↓

&#x20;   persist

&#x20;      ↓

&#x20;   commit



Failure:



&#x20;   rollback



====================================================================

53\. TRANSACTION RULE

====================================================================



Operations that modify multiple related aggregates MUST maintain

consistent transaction boundaries.



Financial state changes MUST NOT partially persist.



====================================================================

54\. APPLICATION COMMAND CONTRACT

====================================================================



Commands represent requests to perform state-changing operations.



Examples:



&#x20;   CreateOrderCommand

&#x20;   CancelOrderCommand

&#x20;   RunSimulationCommand

&#x20;   RunBacktestCommand



Commands SHOULD be immutable.



====================================================================

55\. CREATE ORDER COMMAND

====================================================================



Input:



&#x20;   account\_id

&#x20;   symbol

&#x20;   side

&#x20;   order\_type

&#x20;   quantity

&#x20;   price

&#x20;   strategy\_id

&#x20;   correlation\_id



Processing:



&#x20;   validate

&#x20;       ↓

&#x20;   risk

&#x20;       ↓

&#x20;   create order

&#x20;       ↓

&#x20;   persist

&#x20;       ↓

&#x20;   execute if permitted

&#x20;       ↓

&#x20;   publish events



Output:



&#x20;   CreateOrderResult



====================================================================

56\. CANCEL ORDER COMMAND

====================================================================



Input:



&#x20;   order\_id

&#x20;   correlation\_id



Processing:



&#x20;   load order

&#x20;       ↓

&#x20;   validate lifecycle

&#x20;       ↓

&#x20;   executor.cancel()

&#x20;       ↓

&#x20;   persist

&#x20;       ↓

&#x20;   publish event



====================================================================

57\. QUERY CONTRACT

====================================================================



Queries MUST NOT mutate state.



Examples:



&#x20;   GetOrderQuery

&#x20;   GetPositionQuery

&#x20;   GetPortfolioQuery

&#x20;   GetBacktestResultQuery



Queries should return DTOs or read models.



====================================================================

58\. APPLICATION SERVICE CONTRACT

====================================================================



Application Services coordinate use cases.



Examples:



&#x20;   MarketDataService

&#x20;   SignalService

&#x20;   RiskService

&#x20;   OrderService

&#x20;   ExecutionService

&#x20;   PositionService

&#x20;   PortfolioService

&#x20;   SimulationService

&#x20;   BacktestService



Services MUST remain cohesive.



Avoid a single:



&#x20;   TradingService



containing all logic.



====================================================================

59\. MARKET DATA SERVICE

====================================================================



Operation:



&#x20;   load\_market\_data(request) -> MarketDataResult



Flow:



&#x20;   provider

&#x20;       ↓

&#x20;   validate

&#x20;       ↓

&#x20;   normalize

&#x20;       ↓

&#x20;   optionally persist

&#x20;       ↓

&#x20;   return



====================================================================

60\. SIGNAL SERVICE

====================================================================



Operation:



&#x20;   generate\_signal(context) -> Signal



Flow:



&#x20;   market context

&#x20;       ↓

&#x20;   feature calculation

&#x20;       ↓

&#x20;   optional prediction

&#x20;       ↓

&#x20;   strategy

&#x20;       ↓

&#x20;   signal



SignalService MUST NOT execute orders.



====================================================================

61\. RISK SERVICE

====================================================================



Operation:



&#x20;   evaluate(candidate) -> RiskDecision



Responsibilities:



&#x20;   execute all configured risk rules

&#x20;   aggregate results

&#x20;   provide reasons

&#x20;   produce auditable decision



====================================================================

62\. ORDER SERVICE

====================================================================



Responsibilities:



&#x20;   create

&#x20;   validate

&#x20;   persist

&#x20;   submit

&#x20;   cancel

&#x20;   reconcile



OrderService MUST enforce:



&#x20;   risk gate

&#x20;   lifecycle rules

&#x20;   idempotency



====================================================================

63\. EXECUTION SERVICE

====================================================================



Operation:



&#x20;   execute(order) -> ExecutionResult



ExecutionService chooses or receives an OrderExecutor.



It MUST NOT contain broker-specific logic.



====================================================================

64\. SIMULATION SERVICE

====================================================================



Operation:



&#x20;   run(request) -> SimulationResult



Request:



&#x20;   dataset

&#x20;   strategy

&#x20;   risk configuration

&#x20;   starting capital

&#x20;   execution configuration

&#x20;   seed



Output:



&#x20;   trades

&#x20;   positions

&#x20;   portfolio snapshots

&#x20;   metrics

&#x20;   events



====================================================================

65\. BACKTEST SERVICE

====================================================================



Operation:



&#x20;   run(request) -> BacktestResult



BacktestResult MUST include:



&#x20;   backtest\_id

&#x20;   configuration

&#x20;   dataset information

&#x20;   trades

&#x20;   metrics

&#x20;   equity curve

&#x20;   drawdown

&#x20;   warnings

&#x20;   errors

&#x20;   reproducibility metadata



====================================================================

66\. BACKTEST ENGINE CONTRACT

====================================================================



Contract:



&#x20;   BacktestEngine



Operation:



&#x20;   run(request) -> BacktestResult



Rules:



&#x20;   chronological processing

&#x20;   deterministic execution

&#x20;   no lookahead

&#x20;   explicit fees

&#x20;   explicit slippage

&#x20;   explicit starting capital



BacktestEngine MUST NOT access live execution.



====================================================================

67\. BACKTEST DATA SOURCE

====================================================================



Contract:



&#x20;   HistoricalDataSource



Operation:



&#x20;   stream(request) -> Iterable\[Candle]



Data MUST be:



&#x20;   ordered

&#x20;   validated

&#x20;   reproducible



====================================================================

68\. BACKTEST METRICS CONTRACT

====================================================================



Contract:



&#x20;   MetricsCalculator



Operation:



&#x20;   calculate(result\_context) -> PerformanceMetrics



Metrics:



&#x20;   total\_return

&#x20;   net\_pnl

&#x20;   gross\_profit

&#x20;   gross\_loss

&#x20;   win\_rate

&#x20;   trade\_count

&#x20;   average\_trade

&#x20;   maximum\_drawdown

&#x20;   profit\_factor



Optional:



&#x20;   sharpe

&#x20;   sortino

&#x20;   calmar

&#x20;   volatility

&#x20;   CAGR



====================================================================

69\. STRATEGY VERSION CONTRACT

====================================================================



Every strategy SHOULD expose:



&#x20;   strategy\_id

&#x20;   strategy\_name

&#x20;   strategy\_version



Backtests MUST record the strategy version.



====================================================================

70\. MODEL VERSION CONTRACT

====================================================================



Every AI prediction source MUST expose:



&#x20;   model\_id

&#x20;   model\_version



Backtests involving AI MUST record model identity and version.



====================================================================

71\. CONFIGURATION CONTRACT

====================================================================



Contract:



&#x20;   ConfigurationProvider



Operation:



&#x20;   load() -> Configuration



Configuration MUST be:



&#x20;   validated

&#x20;   typed

&#x20;   immutable after initialization where possible



====================================================================

72\. CONFIGURATION SECTIONS

====================================================================



Configuration SHOULD contain:



&#x20;   application

&#x20;   environment

&#x20;   logging

&#x20;   market\_data

&#x20;   strategy

&#x20;   prediction

&#x20;   risk

&#x20;   execution

&#x20;   simulation

&#x20;   backtesting

&#x20;   persistence



====================================================================

73\. CONFIGURATION PRIORITY

====================================================================



Recommended precedence:



&#x20;   hardcoded defaults

&#x20;       <

&#x20;   configuration file

&#x20;       <

&#x20;   environment variables

&#x20;       <

&#x20;   explicit runtime arguments



Secrets MUST come from secure sources.



====================================================================

74\. LIFECYCLE CONTRACT

====================================================================



Contract:



&#x20;   LifecycleManager



Operations:



&#x20;   initialize()

&#x20;   start()

&#x20;   stop()

&#x20;   shutdown()



Valid conceptual lifecycle:



&#x20;   CREATED

&#x20;       ↓

&#x20;   INITIALIZING

&#x20;       ↓

&#x20;   READY

&#x20;       ↓

&#x20;   RUNNING

&#x20;       ↓

&#x20;   STOPPING

&#x20;       ↓

&#x20;   STOPPED



Failure:



&#x20;   FAILED



Invalid transitions MUST be rejected.



====================================================================

75\. HEALTH CONTRACT

====================================================================



Optional but recommended:



&#x20;   HealthChecker



Operation:



&#x20;   check() -> HealthStatus



Health checks may cover:



&#x20;   database

&#x20;   market data provider

&#x20;   execution adapter

&#x20;   configuration

&#x20;   event system



====================================================================

76\. OBSERVABILITY CONTRACT

====================================================================



Components SHOULD expose:



&#x20;   operation name

&#x20;   duration

&#x20;   status

&#x20;   correlation ID

&#x20;   relevant entity IDs



Observability MUST NOT modify business behavior.



====================================================================

77\. CORRELATION ID CONTRACT

====================================================================



Every major application workflow SHOULD have:



&#x20;   correlation\_id



Example:



&#x20;   SignalGenerated

&#x20;       correlation\_id = ABC



&#x20;   RiskApproved

&#x20;       correlation\_id = ABC



&#x20;   OrderCreated

&#x20;       correlation\_id = ABC



&#x20;   OrderFilled

&#x20;       correlation\_id = ABC



&#x20;   TradeOpened

&#x20;       correlation\_id = ABC



====================================================================

78\. ERROR CONTRACT

====================================================================



Errors should have stable categories.



Core:



&#x20;   ShadBotTraderError



Configuration:



&#x20;   ConfigurationError



Domain:



&#x20;   DomainError

&#x20;   ValidationError

&#x20;   InvalidStateTransitionError



Market:



&#x20;   MarketDataError

&#x20;   DataValidationError



Strategy:



&#x20;   StrategyError



Risk:



&#x20;   RiskError

&#x20;   RiskRejectedError



Trading:



&#x20;   OrderError

&#x20;   TradeError

&#x20;   PositionError



Execution:



&#x20;   ExecutionError

&#x20;   ExecutionRejectedError

&#x20;   ProviderUnavailableError



Persistence:



&#x20;   PersistenceError

&#x20;   RepositoryError



Simulation:



&#x20;   SimulationError



Backtesting:



&#x20;   BacktestError



====================================================================

79\. ERROR BEHAVIOR

====================================================================



Errors MUST:



&#x20;   be explicit

&#x20;   be loggable

&#x20;   preserve context

&#x20;   avoid secret leakage



Financial operation errors MUST include enough context for

investigation without exposing credentials.



====================================================================

80\. RETRY CONTRACT

====================================================================



Retry MUST be explicit.



Safe retry examples:



&#x20;   market data request

&#x20;   read-only repository operation

&#x20;   temporary infrastructure health check



Unsafe blind retry:



&#x20;   live order submission



Order submission MUST use idempotency protection.



====================================================================

81\. IDEMPOTENCY CONTRACT

====================================================================



Operations that can be retried MUST define idempotency semantics.



Potential keys:



&#x20;   event\_id

&#x20;   command\_id

&#x20;   execution\_id

&#x20;   client\_order\_id



Repeated execution of the same logical operation MUST NOT create

duplicate financial effects.



====================================================================

82\. TRANSACTIONAL EVENT CONTRACT

====================================================================



Where persistence and event publication must be atomic,

an appropriate transactional/outbox pattern SHOULD be used.



The system MUST NOT silently lose important financial events.



====================================================================

83\. DTO CONTRACT

====================================================================



DTOs are allowed at Application boundaries.



DTOs SHOULD:



&#x20;   be typed

&#x20;   be immutable

&#x20;   represent one use case

&#x20;   avoid exposing infrastructure models



Domain entities MUST NOT become uncontrolled API response objects.



====================================================================

84\. SERIALIZATION CONTRACT

====================================================================



Serialized objects MUST have:



&#x20;   stable field names

&#x20;   explicit versions where necessary

&#x20;   deterministic representation



Domain serialization must not depend on a broker SDK.



====================================================================

85\. EXTERNAL ADAPTER CONTRACT

====================================================================



Every external provider adapter must translate:



&#x20;   External Model

&#x20;       ↓

&#x20;   Adapter

&#x20;       ↓

&#x20;   Domain/Application Model



Never:



&#x20;   External Model

&#x20;       ↓

&#x20;   Domain



====================================================================

86\. BROKER ADAPTER CONTRACT

====================================================================



Broker adapters MUST:



&#x20;   map Symbol

&#x20;   map OrderSide

&#x20;   map OrderType

&#x20;   map Quantity

&#x20;   map Price

&#x20;   map OrderId

&#x20;   map execution status

&#x20;   map broker errors



Broker-specific concepts MUST remain inside Infrastructure.



====================================================================

87\. MARKET DATA ADAPTER CONTRACT

====================================================================



Market data adapters MUST:



&#x20;   retrieve external data

&#x20;   validate external response

&#x20;   normalize it

&#x20;   create Candle objects

&#x20;   report provider failures



They MUST NOT implement trading decisions.



====================================================================

88\. STRATEGY PLUGIN CONTRACT

====================================================================



Strategies should be pluggable.



A strategy MUST provide:



&#x20;   strategy\_id

&#x20;   strategy\_version

&#x20;   evaluate(context)



Registration MUST be explicit.



====================================================================

89\. RISK PLUGIN CONTRACT

====================================================================



Risk rules should be composable.



Example:



&#x20;   RiskEngine

&#x20;       ├── MaxPositionSizeRule

&#x20;       ├── MaxExposureRule

&#x20;       ├── DailyLossRule

&#x20;       └── DrawdownRule



All rules must return structured results.



====================================================================

90\. EXECUTION PLUGIN CONTRACT

====================================================================



Execution adapters are interchangeable.



Example:



&#x20;   OrderExecutor

&#x20;       ├── SimulatedOrderExecutor

&#x20;       ├── PaperOrderExecutor

&#x20;       └── BrokerOrderExecutor



Application MUST depend only on:



&#x20;   OrderExecutor



====================================================================

91\. REPOSITORY PLUGIN CONTRACT

====================================================================



Repositories are interchangeable.



Example:



&#x20;   OrderRepository

&#x20;       ├── InMemoryOrderRepository

&#x20;       ├── SqlOrderRepository

&#x20;       └── FileOrderRepository



Application MUST depend only on:



&#x20;   OrderRepository



====================================================================

92\. TEST CONTRACT

====================================================================



Every contract implementation MUST have tests.



Minimum:



&#x20;   happy path

&#x20;   invalid input

&#x20;   boundary conditions

&#x20;   failure behavior

&#x20;   idempotency where relevant

&#x20;   lifecycle behavior

&#x20;   dependency isolation



====================================================================

93\. CONTRACT TEST SUITE

====================================================================



Contract tests should be reusable.



Example:



&#x20;   test\_order\_executor\_contract(executor)



The same suite must run against:



&#x20;   simulated executor

&#x20;   paper executor

&#x20;   broker executor



where applicable.



====================================================================

94\. ARCHITECTURE CONTRACT TESTS

====================================================================



Automated tests MUST detect:



&#x20;   Domain importing Infrastructure

&#x20;   Domain importing broker SDK

&#x20;   Domain importing database package

&#x20;   Application importing concrete adapters

&#x20;   circular imports



Architecture rules are executable constraints.



====================================================================

95\. DETERMINISM CONTRACT

====================================================================



The following must be deterministic:



&#x20;   Feature calculations

&#x20;   Strategy calculations

&#x20;   Risk calculations

&#x20;   Simulation

&#x20;   Backtesting

&#x20;   Performance metrics



unless randomness is explicitly part of configuration.



====================================================================

96\. LOOKAHEAD CONTRACT

====================================================================



Any analytical component operating during historical simulation

MUST only consume information available at the current simulated

timestamp.



This includes:



&#x20;   Features

&#x20;   Strategy

&#x20;   Prediction

&#x20;   Risk

&#x20;   Portfolio valuation



====================================================================

97\. SIDE EFFECT CONTRACT

====================================================================



Pure operations:



&#x20;   Value Objects

&#x20;   Feature calculations

&#x20;   Strategy evaluation

&#x20;   Risk calculations

&#x20;   Metrics calculations



Potential side effects:



&#x20;   Repository writes

&#x20;   Event publication

&#x20;   Order execution

&#x20;   Logging

&#x20;   External API calls



Side effects MUST be explicit at Application/Infrastructure

boundaries.



====================================================================

98\. NO HIDDEN SIDE EFFECTS

====================================================================



A method named:



&#x20;   calculate()

&#x20;   evaluate()

&#x20;   validate()



should not secretly:



&#x20;   execute orders

&#x20;   write database state

&#x20;   publish financial events

&#x20;   modify portfolio



unless explicitly documented by its contract.



====================================================================

99\. THREAD SAFETY

====================================================================



If concurrent execution is introduced:



&#x20;   mutable shared state MUST be protected.



Domain objects should remain as isolated as possible.



Do not introduce concurrency merely for performance before

correctness is established.



====================================================================

100\. ASYNC CONTRACT

====================================================================



Async APIs may be introduced for:



&#x20;   network providers

&#x20;   broker communication

&#x20;   event infrastructure



Do NOT make the Domain async merely because Infrastructure is async.



Adapters may translate async external operations into Application

contracts.



====================================================================

101\. PERFORMANCE CONTRACT

====================================================================



Correctness has priority over premature optimization.



Performance-critical paths include:



&#x20;   market data processing

&#x20;   feature calculation

&#x20;   simulation loop

&#x20;   backtesting loop



Optimization MUST preserve:



&#x20;   determinism

&#x20;   correctness

&#x20;   testability

&#x20;   architecture



====================================================================

102\. SECURITY CONTRACT

====================================================================



Contracts MUST NOT expose:



&#x20;   API keys

&#x20;   passwords

&#x20;   broker secrets

&#x20;   database passwords

&#x20;   private tokens



Sensitive configuration MUST remain Infrastructure-level.



====================================================================

103\. LIVE SAFETY CONTRACT

====================================================================



The following chain is mandatory:



&#x20;   Signal

&#x20;       ↓

&#x20;   Risk

&#x20;       ↓

&#x20;   Order Validation

&#x20;       ↓

&#x20;   Execution Mode Validation

&#x20;       ↓

&#x20;   Execution



No component may bypass this chain.



====================================================================

104\. SIMULATION SAFETY CONTRACT

====================================================================



Simulation MUST be isolated.



Simulation MUST NOT:



&#x20;   access production credentials

&#x20;   access live broker

&#x20;   silently switch execution mode

&#x20;   use system time for simulation state



====================================================================

105\. BACKTEST SAFETY CONTRACT

====================================================================



Backtest MUST:



&#x20;   use historical data

&#x20;   use simulated execution

&#x20;   use deterministic clock

&#x20;   prevent future data access

&#x20;   record configuration

&#x20;   record strategy version



====================================================================

106\. API VERSIONING

====================================================================



Public Application/API contracts should be versioned when

breaking changes are introduced.



Example:



&#x20;   v1



Breaking changes MUST NOT be silently introduced.



====================================================================

107\. BACKWARD COMPATIBILITY

====================================================================



When changing a contract:



&#x20;   identify consumers

&#x20;   identify implementations

&#x20;   update tests

&#x20;   update documentation

&#x20;   migrate implementations

&#x20;   verify architecture



Do not silently break downstream consumers.



====================================================================

108\. CONTRACT CHANGE PROCESS

====================================================================



Required process:



&#x20;   1. Identify reason.



&#x20;   2. Identify affected contracts.



&#x20;   3. Identify implementations.



&#x20;   4. Identify tests.



&#x20;   5. Identify documentation.



&#x20;   6. Implement change.



&#x20;   7. Run quality gate.



&#x20;   8. Run contract tests.



&#x20;   9. Run integration tests.



&#x20;   10. Update architecture documentation.



&#x20;   11. Record architectural decision.



====================================================================

109\. APPLICATION DEPENDENCY GRAPH

====================================================================



Expected dependency direction:



&#x20;   CLI

&#x20;    |

&#x20;    v

&#x20;   Application

&#x20;    |

&#x20;    +------> Domain

&#x20;    |

&#x20;    +------> Ports

&#x20;                ^

&#x20;                |

&#x20;         Infrastructure



Infrastructure:



&#x20;   Infrastructure

&#x20;        |

&#x20;        +----> Application Contracts

&#x20;        |

&#x20;        +----> Domain



Domain:



&#x20;   Domain

&#x20;      |

&#x20;      X

&#x20;   Infrastructure



====================================================================

110\. COMPLETE CONTRACT GRAPH

====================================================================



&#x20;   MARKET DATA

&#x20;        |

&#x20;        v

&#x20;   MarketDataProvider

&#x20;        |

&#x20;        v

&#x20;   MarketDataService

&#x20;        |

&#x20;        v

&#x20;   FeatureCalculator

&#x20;        |

&#x20;        v

&#x20;   PredictionProvider (optional)

&#x20;        |

&#x20;        v

&#x20;   Strategy

&#x20;        |

&#x20;        v

&#x20;   Signal

&#x20;        |

&#x20;        v

&#x20;   RiskEngine

&#x20;        |

&#x20;        v

&#x20;   RiskDecision

&#x20;        |

&#x20;        v

&#x20;   OrderFactory

&#x20;        |

&#x20;        v

&#x20;   OrderValidator

&#x20;        |

&#x20;        v

&#x20;   OrderService

&#x20;        |

&#x20;        v

&#x20;   OrderExecutor

&#x20;        |

&#x20;        v

&#x20;   ExecutionResult

&#x20;        |

&#x20;        +----------+

&#x20;        |          |

&#x20;        v          v

&#x20;     Trade      Position

&#x20;        |          |

&#x20;        +-----+----+

&#x20;              |

&#x20;              v

&#x20;          Portfolio

&#x20;              |

&#x20;              v

&#x20;         Metrics / Events



====================================================================

111\. CONTRACT OWNERSHIP

====================================================================



Domain owns:



&#x20;   Entity contracts

&#x20;   Value Object contracts

&#x20;   Domain invariants

&#x20;   State machines

&#x20;   Domain Events



Application owns:



&#x20;   Use case contracts

&#x20;   Ports

&#x20;   Services

&#x20;   Commands

&#x20;   Queries

&#x20;   DTOs



Infrastructure owns:



&#x20;   Adapter implementations

&#x20;   Database implementations

&#x20;   Broker implementations

&#x20;   External API implementations



Interfaces owns:



&#x20;   CLI contracts

&#x20;   Presentation contracts



====================================================================

112\. IMPLEMENTATION ORDER

====================================================================



Implement contracts in this order:



&#x20;   1. Core types

&#x20;   2. Value Objects

&#x20;   3. Market Domain

&#x20;   4. Trading Domain

&#x20;   5. Portfolio Domain

&#x20;   6. Risk Domain

&#x20;   7. Domain Events

&#x20;   8. Application Ports

&#x20;   9. Application DTOs

&#x20;   10. Application Services

&#x20;   11. In-memory adapters

&#x20;   12. Simulation

&#x20;   13. Strategy framework

&#x20;   14. Backtesting

&#x20;   15. Persistence

&#x20;   16. Event infrastructure

&#x20;   17. CLI

&#x20;   18. Paper execution

&#x20;   19. Broker execution

&#x20;   20. Production hardening



Do NOT implement broker integration before simulation is stable.



====================================================================

113\. ACCEPTANCE CRITERIA

====================================================================



The API/Contract architecture is considered implemented only when:



&#x20;   \[ ] Domain contracts exist.



&#x20;   \[ ] Value Objects exist.



&#x20;   \[ ] Market contracts exist.



&#x20;   \[ ] Strategy contract exists.



&#x20;   \[ ] Prediction contract exists.



&#x20;   \[ ] Risk contracts exist.



&#x20;   \[ ] Order contract exists.



&#x20;   \[ ] Trade contract exists.



&#x20;   \[ ] Position contract exists.



&#x20;   \[ ] Portfolio contracts exist.



&#x20;   \[ ] Event contract exists.



&#x20;   \[ ] EventBus contract exists.



&#x20;   \[ ] Clock contract exists.



&#x20;   \[ ] Repository contracts exist.



&#x20;   \[ ] MarketDataProvider exists.



&#x20;   \[ ] OrderExecutor exists.



&#x20;   \[ ] Application services use ports.



&#x20;   \[ ] Infrastructure implements ports.



&#x20;   \[ ] Simulation uses OrderExecutor abstraction.



&#x20;   \[ ] Backtesting uses simulation.



&#x20;   \[ ] Live execution is isolated.



&#x20;   \[ ] Idempotency is defined.



&#x20;   \[ ] Error contracts exist.



&#x20;   \[ ] Lifecycle contracts exist.



&#x20;   \[ ] Architecture tests exist.



&#x20;   \[ ] Contract tests exist.



&#x20;   \[ ] Unit tests exist.



&#x20;   \[ ] No Domain → Infrastructure dependency exists.



&#x20;   \[ ] No Signal → Execution bypass exists.



&#x20;   \[ ] No AI → Execution bypass exists.



&#x20;   \[ ] No Risk bypass exists.



&#x20;   \[ ] No Simulation → Live dependency exists.



====================================================================

114\. CODING AGENT INSTRUCTIONS

====================================================================



When implementing this document, the coding agent MUST follow:



&#x20;   READ

&#x20;       ↓

&#x20;   INSPECT

&#x20;       ↓

&#x20;   UNDERSTAND

&#x20;       ↓

&#x20;   IMPLEMENT CONTRACT

&#x20;       ↓

&#x20;   IMPLEMENT TEST

&#x20;       ↓

&#x20;   IMPLEMENT ADAPTER

&#x20;       ↓

&#x20;   RUN QUALITY GATE

&#x20;       ↓

&#x20;   RUN CONTRACT TESTS

&#x20;       ↓

&#x20;   RUN INTEGRATION TESTS

&#x20;       ↓

&#x20;   VERIFY RUNTIME

&#x20;       ↓

&#x20;   DOCUMENT

&#x20;       ↓

&#x20;   COMMIT



The agent MUST NOT jump directly to Infrastructure.



The agent MUST NOT start with broker integration.



The agent MUST NOT start with AI.



The agent MUST establish the Domain and Application contracts

first.



====================================================================

115\. QUALITY GATE

====================================================================



Every contract implementation MUST pass:



&#x20;   python -m ruff check .



&#x20;   python -m black .



&#x20;   python -m mypy src



&#x20;   python -m pytest



If any command fails:



&#x20;   implementation is NOT complete.



The agent must fix the failure before moving to the next milestone.



====================================================================

116\. FINAL RULE

====================================================================



The contracts defined in this document are the boundaries of

ShadBotTrader.



Implementations may change internally.



The contractual behavior MUST remain stable unless an explicit

architectural decision changes it.



The goal is:



&#x20;   MANY IMPLEMENTATIONS



&#x20;           ↓



&#x20;   ONE STABLE CONTRACT



&#x20;           ↓



&#x20;   ONE CONSISTENT APPLICATION



&#x20;           ↓



&#x20;   DETERMINISTIC SIMULATION



&#x20;           ↓



&#x20;   REPRODUCIBLE BACKTESTING



&#x20;           ↓



&#x20;   SAFE PAPER TRADING



&#x20;           ↓



&#x20;   CONTROLLED LIVE TRADING



====================================================================

END OF API\_AND\_CONTRACT\_SPECIFICATION

====================================================================

