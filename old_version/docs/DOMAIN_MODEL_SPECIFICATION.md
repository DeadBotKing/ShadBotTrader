====================================================================

SHADBOTTRADER

DOMAIN\_MODEL\_SPECIFICATION

====================================================================



DOCUMENT TYPE:

&#x20;   Canonical Domain Model Specification



PROJECT:

&#x20;   ShadBotTrader



DOMAIN STYLE:

&#x20;   Domain-Driven Design (DDD)

&#x20;   Clean Architecture

&#x20;   Explicit Domain Model

&#x20;   Aggregate-based consistency

&#x20;   Immutable Value Objects where practical

&#x20;   Domain Events

&#x20;   Domain Services

&#x20;   Repository abstractions

&#x20;   Strong invariants



PRIMARY PURPOSE:

&#x20;   Define the complete business/domain model of ShadBotTrader.



IMPORTANT:



&#x20;   This document defines DOMAIN semantics.



&#x20;   It is NOT a database specification.



&#x20;   It is NOT an ORM specification.



&#x20;   It is NOT an API specification.



&#x20;   It is NOT an implementation-specific specification.



&#x20;   Database models must map to this domain model.



&#x20;   API DTOs must map to this domain model.



&#x20;   Domain entities must NOT depend on:



&#x20;       SQLAlchemy

&#x20;       SQL Server

&#x20;       Django

&#x20;       FastAPI

&#x20;       Flask

&#x20;       Pydantic

&#x20;       HTTP

&#x20;       REST

&#x20;       ORM sessions

&#x20;       database connections

&#x20;       UI

&#x20;       broker SDKs

&#x20;       external APIs



====================================================================

1\. DOMAIN OBJECTIVE

====================================================================



ShadBotTrader is an enterprise AI-powered trading platform.



The domain must support:



&#x20;   Market observation

&#x20;   Market data normalization

&#x20;   Feature generation

&#x20;   AI prediction

&#x20;   Strategy evaluation

&#x20;   Signal generation

&#x20;   Risk evaluation

&#x20;   Order creation

&#x20;   Order execution

&#x20;   Trade lifecycle

&#x20;   Position management

&#x20;   Account management

&#x20;   Portfolio management

&#x20;   PnL calculation

&#x20;   Simulation

&#x20;   Backtesting

&#x20;   Optimization

&#x20;   Model lifecycle

&#x20;   Dataset lifecycle

&#x20;   Strategy versioning

&#x20;   Self-learning

&#x20;   Event tracking

&#x20;   Reconciliation

&#x20;   Auditability



The domain must support:



&#x20;   research mode

&#x20;   simulation mode

&#x20;   backtest mode

&#x20;   paper trading

&#x20;   live trading



These modes must be explicitly separated.



====================================================================

2\. DOMAIN PRINCIPLES

====================================================================



RULE 1:



&#x20;   Domain logic must be deterministic whenever its inputs are

&#x20;   deterministic.



RULE 2:



&#x20;   Domain objects own their invariants.



RULE 3:



&#x20;   Application services orchestrate.



RULE 4:



&#x20;   Infrastructure integrates external systems.



RULE 5:



&#x20;   Domain does not perform I/O.



RULE 6:



&#x20;   Domain does not access databases.



RULE 7:



&#x20;   Domain does not call broker APIs.



RULE 8:



&#x20;   Domain does not call AI frameworks directly.



RULE 9:



&#x20;   Domain does not read environment variables.



RULE 10:



&#x20;   Domain does not contain configuration loading logic.



RULE 11:



&#x20;   External provider representations must be translated into

&#x20;   canonical domain representations.



RULE 12:



&#x20;   Financial calculations must use exact decimal arithmetic.



RULE 13:



&#x20;   Historical decisions must remain explainable.



RULE 14:



&#x20;   Versioned artifacts must be immutable.



RULE 15:



&#x20;   Live trading must require explicit authorization.



====================================================================

3\. DOMAIN LAYERS

====================================================================



The domain is logically divided into bounded areas:



&#x20;   Market

&#x20;   Feature

&#x20;   AI

&#x20;   Strategy

&#x20;   Risk

&#x20;   Trading

&#x20;   Portfolio

&#x20;   Simulation

&#x20;   Backtesting

&#x20;   Optimization

&#x20;   Learning

&#x20;   Account

&#x20;   Reconciliation



These are domain concepts.



They must not become arbitrary technical packages.



====================================================================

4\. DOMAIN OBJECT TYPES

====================================================================



The domain uses:



&#x20;   Entity

&#x20;   Value Object

&#x20;   Aggregate

&#x20;   Aggregate Root

&#x20;   Domain Service

&#x20;   Domain Event

&#x20;   Domain Policy

&#x20;   Specification

&#x20;   Repository Interface



====================================================================

5\. ENTITY

====================================================================



An Entity:



&#x20;   has stable identity



&#x20;   has lifecycle



&#x20;   may change state



&#x20;   defines identity independently of attribute equality



Examples:



&#x20;   Instrument

&#x20;   Order

&#x20;   Trade

&#x20;   Position

&#x20;   Account

&#x20;   Portfolio

&#x20;   Strategy

&#x20;   Model

&#x20;   Dataset



====================================================================

6\. VALUE OBJECT

====================================================================



Value Objects:



&#x20;   have no independent identity



&#x20;   are compared by value



&#x20;   should preferably be immutable



Examples:



&#x20;   Symbol

&#x20;   Money

&#x20;   Quantity

&#x20;   Price

&#x20;   Percentage

&#x20;   Timestamp

&#x20;   Timeframe

&#x20;   PriceRange

&#x20;   PnL

&#x20;   OrderSide

&#x20;   SignalDirection



====================================================================

7\. AGGREGATE

====================================================================



Aggregates define consistency boundaries.



External code must interact with an Aggregate through its root.



Do NOT modify child entities directly from outside the aggregate.



====================================================================

8\. AGGREGATE ROOTS

====================================================================



Primary Aggregate Roots:



&#x20;   Instrument

&#x20;   MarketDataSeries

&#x20;   FeatureDefinition

&#x20;   Dataset

&#x20;   Model

&#x20;   Strategy

&#x20;   RiskProfile

&#x20;   Account

&#x20;   Portfolio

&#x20;   Order

&#x20;   Trade

&#x20;   Position

&#x20;   SimulationRun

&#x20;   BacktestRun

&#x20;   OptimizationRun

&#x20;   LearningSession



====================================================================

9\. CORE VALUE OBJECTS

====================================================================



The following Value Objects are foundational.



\--------------------------------------------------------------------

9.1 Symbol

\--------------------------------------------------------------------



Fields:



&#x20;   value



Examples:



&#x20;   EURUSD

&#x20;   BTCUSD

&#x20;   XAUUSD



Rules:



&#x20;   non-empty

&#x20;   normalized

&#x20;   no whitespace

&#x20;   canonical representation



\--------------------------------------------------------------------

9.2 CurrencyCode

\--------------------------------------------------------------------



Fields:



&#x20;   value



Example:



&#x20;   USD

&#x20;   EUR

&#x20;   GBP



Rules:



&#x20;   ISO-compatible representation



\--------------------------------------------------------------------

9.3 Price

\--------------------------------------------------------------------



Fields:



&#x20;   value

&#x20;   currency



Rules:



&#x20;   Decimal only

&#x20;   non-negative unless explicitly required by instrument semantics



Never use:



&#x20;   float



\--------------------------------------------------------------------

9.4 Quantity

\--------------------------------------------------------------------



Fields:



&#x20;   value



Rules:



&#x20;   Decimal

&#x20;   positive for normal orders

&#x20;   zero only where explicitly permitted



\--------------------------------------------------------------------

9.5 Money

\--------------------------------------------------------------------



Fields:



&#x20;   amount

&#x20;   currency



Operations:



&#x20;   add

&#x20;   subtract

&#x20;   multiply

&#x20;   divide

&#x20;   compare



Rules:



&#x20;   currencies must match for addition/subtraction



\--------------------------------------------------------------------

9.6 Percentage

\--------------------------------------------------------------------



Fields:



&#x20;   value



Operations:



&#x20;   add

&#x20;   subtract

&#x20;   multiply



Used for:



&#x20;   return

&#x20;   confidence

&#x20;   drawdown

&#x20;   risk

&#x20;   fees



\--------------------------------------------------------------------

9.7 Timeframe

\--------------------------------------------------------------------



Fields:



&#x20;   code

&#x20;   duration



Examples:



&#x20;   1m

&#x20;   5m

&#x20;   15m

&#x20;   1h

&#x20;   4h

&#x20;   1d



\--------------------------------------------------------------------

9.8 Timestamp

\--------------------------------------------------------------------



Rules:



&#x20;   UTC



The domain must not operate with ambiguous local timestamps.



\--------------------------------------------------------------------

9.9 PriceRange

\--------------------------------------------------------------------



Fields:



&#x20;   low

&#x20;   high



Invariant:



&#x20;   low <= high



\--------------------------------------------------------------------

9.10 PnL

\--------------------------------------------------------------------



Fields:



&#x20;   realized

&#x20;   unrealized

&#x20;   fees

&#x20;   net



====================================================================

10\. MARKET DOMAIN

====================================================================



Purpose:



&#x20;   Represent financial instruments and observations.



Core concepts:



&#x20;   Instrument

&#x20;   Market

&#x20;   Candle

&#x20;   Tick

&#x20;   Timeframe

&#x20;   MarketDataSeries

&#x20;   DataSource



====================================================================

11\. INSTRUMENT

====================================================================



Entity:



&#x20;   Instrument



Fields:



&#x20;   id

&#x20;   symbol

&#x20;   name

&#x20;   instrument\_type

&#x20;   market

&#x20;   base\_currency

&#x20;   quote\_currency

&#x20;   exchange

&#x20;   active



Responsibilities:



&#x20;   identify financial instrument



&#x20;   validate instrument identity



&#x20;   expose trading characteristics



Invariants:



&#x20;   symbol cannot be empty



&#x20;   base and quote currencies must be valid



&#x20;   instrument type must be supported



====================================================================

12\. INSTRUMENT TYPE

====================================================================



Supported conceptual types:



&#x20;   FOREX

&#x20;   CRYPTO

&#x20;   EQUITY

&#x20;   INDEX

&#x20;   COMMODITY

&#x20;   FUTURE

&#x20;   OPTION

&#x20;   CFD

&#x20;   OTHER



The implementation may extend this enumeration through explicit

architecture decisions.



====================================================================

13\. MARKET

====================================================================



Entity:



&#x20;   Market



Fields:



&#x20;   id

&#x20;   code

&#x20;   name

&#x20;   type

&#x20;   active



Responsibilities:



&#x20;   identify market context



====================================================================

14\. CANDLE

====================================================================



Entity:



&#x20;   Candle



Fields:



&#x20;   timestamp

&#x20;   timeframe

&#x20;   open

&#x20;   high

&#x20;   low

&#x20;   close

&#x20;   volume

&#x20;   spread



Invariants:



&#x20;   high >= open



&#x20;   high >= close



&#x20;   high >= low



&#x20;   low <= open



&#x20;   low <= close



&#x20;   prices must be valid for the instrument



&#x20;   timestamp must align with timeframe



====================================================================

15\. TICK

====================================================================



Entity:



&#x20;   Tick



Fields:



&#x20;   timestamp

&#x20;   instrument

&#x20;   bid

&#x20;   ask

&#x20;   last

&#x20;   bid\_volume

&#x20;   ask\_volume



Invariants:



&#x20;   bid >= 0



&#x20;   ask >= 0



&#x20;   ask >= bid when both are available



====================================================================

16\. MARKET DATA SERIES

====================================================================



Aggregate Root:



&#x20;   MarketDataSeries



Represents:



&#x20;   ordered observations for one instrument/timeframe/context.



Identity:



&#x20;   instrument + timeframe + dataset context



Responsibilities:



&#x20;   add observation



&#x20;   validate chronological ordering



&#x20;   reject invalid observations



&#x20;   retrieve observation ranges



&#x20;   maintain data integrity



Must not:



&#x20;   perform network requests



&#x20;   fetch data from providers



====================================================================

17\. FEATURE DOMAIN

====================================================================



Core concepts:



&#x20;   Feature

&#x20;   FeatureDefinition

&#x20;   FeatureVersion

&#x20;   FeatureObservation

&#x20;   FeatureSet



====================================================================

18\. FEATURE DEFINITION

====================================================================



Entity:



&#x20;   FeatureDefinition



Fields:



&#x20;   id

&#x20;   code

&#x20;   name

&#x20;   description

&#x20;   category

&#x20;   calculation\_definition

&#x20;   active



Examples:



&#x20;   SMA

&#x20;   EMA

&#x20;   RSI

&#x20;   MACD

&#x20;   ATR

&#x20;   volatility

&#x20;   momentum



====================================================================

19\. FEATURE VERSION

====================================================================



Entity:



&#x20;   FeatureVersion



Fields:



&#x20;   id

&#x20;   feature\_definition\_id

&#x20;   version

&#x20;   configuration

&#x20;   source\_hash



Invariant:



&#x20;   Versioned feature definitions are immutable.



A new calculation requires a new version.



====================================================================

20\. FEATURE OBSERVATION

====================================================================



Entity:



&#x20;   FeatureObservation



Fields:



&#x20;   instrument

&#x20;   timeframe

&#x20;   timestamp

&#x20;   feature\_version

&#x20;   value

&#x20;   quality



Critical invariant:



&#x20;   No future information may influence a feature at timestamp T.



This prevents lookahead bias.



====================================================================

21\. FEATURE SET

====================================================================



Value/Object or Entity depending on implementation.



Represents:



&#x20;   ordered set of feature definitions/versions used by a model or

&#x20;   strategy.



Must be versionable.



====================================================================

22\. AI DOMAIN

====================================================================



Core concepts:



&#x20;   Dataset

&#x20;   DatasetVersion

&#x20;   Model

&#x20;   ModelVersion

&#x20;   TrainingRun

&#x20;   Prediction

&#x20;   Experiment



====================================================================

23\. DATASET

====================================================================



Aggregate Root:



&#x20;   Dataset



Fields:



&#x20;   id

&#x20;   code

&#x20;   name

&#x20;   type

&#x20;   description



Responsibilities:



&#x20;   define logical dataset identity



====================================================================

24\. DATASET VERSION

====================================================================



Entity:



&#x20;   DatasetVersion



Fields:



&#x20;   id

&#x20;   dataset

&#x20;   version

&#x20;   source\_hash

&#x20;   feature\_set

&#x20;   row\_count



Invariant:



&#x20;   immutable after publication



====================================================================

25\. MODEL

====================================================================



Aggregate Root:



&#x20;   Model



Fields:



&#x20;   id

&#x20;   code

&#x20;   name

&#x20;   model\_type

&#x20;   description



Responsibilities:



&#x20;   identify logical AI model



====================================================================

26\. MODEL VERSION

====================================================================



Entity:



&#x20;   ModelVersion



Fields:



&#x20;   id

&#x20;   model

&#x20;   version

&#x20;   framework

&#x20;   artifact\_reference

&#x20;   checksum

&#x20;   feature\_version

&#x20;   training\_run

&#x20;   status



Statuses:



&#x20;   CREATED

&#x20;   TRAINING

&#x20;   VALIDATED

&#x20;   ACTIVE

&#x20;   RETIRED

&#x20;   FAILED



Invariant:



&#x20;   published model versions are immutable.



====================================================================

27\. TRAINING RUN

====================================================================



Entity:



&#x20;   TrainingRun



Fields:



&#x20;   id

&#x20;   dataset\_version

&#x20;   model

&#x20;   started\_at

&#x20;   completed\_at

&#x20;   hyperparameters

&#x20;   metrics

&#x20;   status



Responsibilities:



&#x20;   represent one reproducible training operation.



====================================================================

28\. PREDICTION

====================================================================



Entity:



&#x20;   Prediction



Fields:



&#x20;   id

&#x20;   model\_version

&#x20;   instrument

&#x20;   timeframe

&#x20;   timestamp

&#x20;   prediction\_type

&#x20;   predicted\_value

&#x20;   confidence

&#x20;   horizon

&#x20;   input\_snapshot\_reference



Invariants:



&#x20;   confidence must be within valid domain range



&#x20;   prediction must reference a valid model version



&#x20;   prediction timestamp must represent the actual inference context



====================================================================

29\. PREDICTION HORIZON

====================================================================



Value Object:



&#x20;   PredictionHorizon



Examples:



&#x20;   1 candle

&#x20;   5 candles

&#x20;   1 hour

&#x20;   1 day



Must be explicit.



Do not represent horizon as an unexplained integer.



====================================================================

30\. STRATEGY DOMAIN

====================================================================



Core concepts:



&#x20;   Strategy

&#x20;   StrategyVersion

&#x20;   StrategyRun

&#x20;   Signal



====================================================================

31\. STRATEGY

====================================================================



Aggregate Root:



&#x20;   Strategy



Fields:



&#x20;   id

&#x20;   code

&#x20;   name

&#x20;   description

&#x20;   strategy\_type

&#x20;   active



Responsibilities:



&#x20;   own strategy identity



&#x20;   manage versions



&#x20;   validate strategy lifecycle



====================================================================

32\. STRATEGY VERSION

====================================================================



Entity:



&#x20;   StrategyVersion



Fields:



&#x20;   id

&#x20;   strategy

&#x20;   version

&#x20;   configuration

&#x20;   source\_hash



Invariant:



&#x20;   published versions are immutable.



====================================================================

33\. STRATEGY RUN

====================================================================



Entity:



&#x20;   StrategyRun



Fields:



&#x20;   id

&#x20;   strategy\_version

&#x20;   execution\_mode

&#x20;   start\_time

&#x20;   end\_time

&#x20;   status

&#x20;   configuration



Execution modes:



&#x20;   RESEARCH

&#x20;   BACKTEST

&#x20;   SIMULATION

&#x20;   PAPER

&#x20;   LIVE



====================================================================

34\. SIGNAL

====================================================================



Entity:



&#x20;   Signal



Fields:



&#x20;   id

&#x20;   strategy\_run

&#x20;   instrument

&#x20;   timestamp

&#x20;   signal\_type

&#x20;   direction

&#x20;   strength

&#x20;   confidence

&#x20;   reference\_price

&#x20;   reason

&#x20;   metadata



Signal types:



&#x20;   ENTRY

&#x20;   EXIT

&#x20;   HOLD

&#x20;   REDUCE

&#x20;   INCREASE



Directions:



&#x20;   LONG

&#x20;   SHORT

&#x20;   FLAT



Invariants:



&#x20;   signal must reference a valid instrument



&#x20;   signal timestamp must belong to the strategy context



&#x20;   confidence must be valid



====================================================================

35\. RISK DOMAIN

====================================================================



Core concepts:



&#x20;   RiskProfile

&#x20;   RiskRule

&#x20;   RiskEvaluation

&#x20;   RiskDecision



====================================================================

36\. RISK PROFILE

====================================================================



Aggregate Root:



&#x20;   RiskProfile



Fields:



&#x20;   id

&#x20;   code

&#x20;   name

&#x20;   configuration

&#x20;   active



Responsibilities:



&#x20;   define risk policy.



====================================================================

37\. RISK RULE

====================================================================



Entity:



&#x20;   RiskRule



Fields:



&#x20;   id

&#x20;   code

&#x20;   type

&#x20;   configuration

&#x20;   priority

&#x20;   active



Examples:



&#x20;   maximum position size



&#x20;   maximum exposure



&#x20;   maximum daily loss



&#x20;   maximum drawdown



&#x20;   maximum leverage



&#x20;   stop-loss requirement



&#x20;   concentration limit



====================================================================

38\. RISK EVALUATION

====================================================================



Entity:



&#x20;   RiskEvaluation



Inputs:



&#x20;   signal

&#x20;   account

&#x20;   portfolio

&#x20;   market state

&#x20;   risk profile



Outputs:



&#x20;   risk score

&#x20;   exposure

&#x20;   maximum quantity

&#x20;   status

&#x20;   explanation



Statuses:



&#x20;   APPROVED

&#x20;   REJECTED

&#x20;   MODIFIED

&#x20;   REVIEW



====================================================================

39\. RISK DECISION

====================================================================



Entity:



&#x20;   RiskDecision



Fields:



&#x20;   evaluation

&#x20;   decision

&#x20;   reason

&#x20;   approved\_quantity

&#x20;   approved\_price

&#x20;   timestamp



Invariant:



&#x20;   no live order may bypass the risk decision boundary.



====================================================================

40\. ACCOUNT DOMAIN

====================================================================



Core concepts:



&#x20;   Account

&#x20;   Balance



====================================================================

41\. ACCOUNT

====================================================================



Aggregate Root:



&#x20;   Account



Fields:



&#x20;   id

&#x20;   code

&#x20;   name

&#x20;   account\_type

&#x20;   base\_currency

&#x20;   execution\_mode

&#x20;   initial\_balance

&#x20;   status



Account types:



&#x20;   DEMO

&#x20;   PAPER

&#x20;   LIVE

&#x20;   SIMULATION



Responsibilities:



&#x20;   own account-level financial state.



====================================================================

42\. BALANCE

====================================================================



Entity:



&#x20;   Balance



Fields:



&#x20;   currency

&#x20;   available

&#x20;   reserved

&#x20;   total



Invariant:



&#x20;   total = available + reserved



unless the account model explicitly defines another accounting

representation.



====================================================================

43\. PORTFOLIO DOMAIN

====================================================================



Core concepts:



&#x20;   Portfolio

&#x20;   Position

&#x20;   PortfolioSnapshot

&#x20;   PortfolioPnL



====================================================================

44\. PORTFOLIO

====================================================================



Aggregate Root:



&#x20;   Portfolio



Fields:



&#x20;   id

&#x20;   account

&#x20;   name

&#x20;   description

&#x20;   status



Responsibilities:



&#x20;   manage positions



&#x20;   calculate portfolio exposure



&#x20;   track portfolio-level financial state



====================================================================

45\. POSITION

====================================================================



Entity:



&#x20;   Position



Fields:



&#x20;   id

&#x20;   instrument

&#x20;   side

&#x20;   quantity

&#x20;   average\_entry\_price

&#x20;   realized\_pnl

&#x20;   unrealized\_pnl

&#x20;   exposure

&#x20;   opened\_at

&#x20;   updated\_at



Sides:



&#x20;   LONG

&#x20;   SHORT



Invariants:



&#x20;   quantity >= 0



&#x20;   average entry price must be valid when quantity > 0



Position transitions:



&#x20;   OPEN

&#x20;   INCREASE

&#x20;   REDUCE

&#x20;   CLOSE



====================================================================

46\. POSITION LIFECYCLE

====================================================================



Opening:



&#x20;   zero → positive quantity



Increasing:



&#x20;   existing quantity → larger quantity



Reducing:



&#x20;   existing quantity → smaller quantity



Closing:



&#x20;   positive quantity → zero



Invalid:



&#x20;   negative quantity



unless the domain explicitly models net positions differently.



====================================================================

47\. PORTFOLIO SNAPSHOT

====================================================================



Entity:



&#x20;   PortfolioSnapshot



Fields:



&#x20;   timestamp

&#x20;   equity

&#x20;   balance

&#x20;   exposure

&#x20;   realized\_pnl

&#x20;   unrealized\_pnl

&#x20;   drawdown



Purpose:



&#x20;   immutable historical portfolio state.



====================================================================

48\. PNL

====================================================================



Value Object:



&#x20;   PnL



Components:



&#x20;   realized

&#x20;   unrealized

&#x20;   fees

&#x20;   net



Core relationship:



&#x20;   net PnL must account for fees according to the accounting

&#x20;   convention defined by the portfolio domain.



====================================================================

49\. TRADING DOMAIN

====================================================================



Core concepts:



&#x20;   Order

&#x20;   OrderRequest

&#x20;   OrderType

&#x20;   OrderSide

&#x20;   OrderStatus

&#x20;   Execution

&#x20;   Trade

&#x20;   TradeLeg



====================================================================

50\. ORDER

====================================================================



Aggregate Root:



&#x20;   Order



Fields:



&#x20;   id

&#x20;   account

&#x20;   instrument

&#x20;   strategy\_run

&#x20;   signal

&#x20;   risk\_decision

&#x20;   client\_order\_id

&#x20;   provider\_order\_id

&#x20;   type

&#x20;   side

&#x20;   quantity

&#x20;   price

&#x20;   stop\_price

&#x20;   time\_in\_force

&#x20;   execution\_mode

&#x20;   status

&#x20;   timestamps



Responsibilities:



&#x20;   validate lifecycle transitions



&#x20;   track submitted quantity



&#x20;   track filled quantity



&#x20;   prevent invalid transitions



====================================================================

51\. ORDER TYPES

====================================================================



Supported conceptual order types:



&#x20;   MARKET

&#x20;   LIMIT

&#x20;   STOP

&#x20;   STOP\_LIMIT



Future types require explicit domain extension.



====================================================================

52\. ORDER SIDE

====================================================================



Values:



&#x20;   BUY

&#x20;   SELL



====================================================================

53\. ORDER STATUS

====================================================================



Lifecycle:



&#x20;   CREATED

&#x20;   VALIDATED

&#x20;   SUBMITTED

&#x20;   PARTIALLY\_FILLED

&#x20;   FILLED

&#x20;   CANCEL\_REQUESTED

&#x20;   CANCELLED

&#x20;   REJECTED

&#x20;   EXPIRED

&#x20;   FAILED



====================================================================

54\. ORDER TRANSITION RULES

====================================================================



Valid examples:



&#x20;   CREATED

&#x20;       → VALIDATED



&#x20;   VALIDATED

&#x20;       → SUBMITTED

&#x20;       → REJECTED

&#x20;       → FAILED



&#x20;   SUBMITTED

&#x20;       → PARTIALLY\_FILLED

&#x20;       → FILLED

&#x20;       → CANCEL\_REQUESTED

&#x20;       → REJECTED

&#x20;       → FAILED

&#x20;       → EXPIRED



&#x20;   PARTIALLY\_FILLED

&#x20;       → PARTIALLY\_FILLED

&#x20;       → FILLED

&#x20;       → CANCEL\_REQUESTED



&#x20;   CANCEL\_REQUESTED

&#x20;       → CANCELLED

&#x20;       → PARTIALLY\_FILLED

&#x20;       → FILLED



Terminal states:



&#x20;   FILLED

&#x20;   CANCELLED

&#x20;   REJECTED

&#x20;   EXPIRED

&#x20;   FAILED



Terminal orders must not transition to active states.



====================================================================

55\. ORDER QUANTITY INVARIANTS

====================================================================



Required:



&#x20;   requested\_quantity > 0



&#x20;   filled\_quantity >= 0



&#x20;   filled\_quantity <= requested\_quantity



Remaining quantity:



&#x20;   requested\_quantity - filled\_quantity



An order cannot be FILLED if:



&#x20;   filled\_quantity < requested\_quantity



unless partial-fill semantics explicitly define a different model.



====================================================================

56\. EXECUTION

====================================================================



Entity:



&#x20;   Execution



Represents:



&#x20;   actual fill performed by a venue/provider.



Fields:



&#x20;   id

&#x20;   order

&#x20;   provider\_execution\_id

&#x20;   timestamp

&#x20;   quantity

&#x20;   price

&#x20;   fee

&#x20;   fee\_currency

&#x20;   liquidity\_type

&#x20;   metadata



Invariant:



&#x20;   quantity > 0



Execution is immutable.



====================================================================

57\. TRADE

====================================================================



Aggregate Root:



&#x20;   Trade



Represents:



&#x20;   logical completed trading transaction.



Fields:



&#x20;   id

&#x20;   account

&#x20;   instrument

&#x20;   strategy\_run

&#x20;   entry

&#x20;   exit

&#x20;   quantity

&#x20;   realized\_pnl

&#x20;   fees

&#x20;   return

&#x20;   status



Statuses:



&#x20;   OPEN

&#x20;   CLOSED

&#x20;   CANCELLED



====================================================================

58\. TRADE LEG

====================================================================



Entity:



&#x20;   TradeLeg



Types:



&#x20;   ENTRY

&#x20;   EXIT

&#x20;   SCALE\_IN

&#x20;   SCALE\_OUT



Each leg references an Execution.



====================================================================

59\. SIMULATION DOMAIN

====================================================================



Core concepts:



&#x20;   SimulationRun

&#x20;   SimulationConfiguration

&#x20;   SimulationEvent

&#x20;   SimulatedFill



====================================================================

60\. SIMULATION RUN

====================================================================



Aggregate Root:



&#x20;   SimulationRun



Fields:



&#x20;   id

&#x20;   name

&#x20;   execution\_context

&#x20;   start\_time

&#x20;   end\_time

&#x20;   initial\_capital

&#x20;   final\_equity

&#x20;   status



Responsibilities:



&#x20;   deterministic replay



&#x20;   simulate order execution



&#x20;   calculate portfolio state



====================================================================

61\. SIMULATION CONFIGURATION

====================================================================



Value Object / Entity:



&#x20;   SimulationConfiguration



Contains:



&#x20;   slippage model

&#x20;   fee model

&#x20;   latency model

&#x20;   market impact model

&#x20;   initial capital



A simulation must be reproducible from its configuration.



====================================================================

62\. BACKTEST DOMAIN

====================================================================



Core concepts:



&#x20;   BacktestRun

&#x20;   BacktestConfiguration

&#x20;   BacktestMetric

&#x20;   EquityPoint

&#x20;   BacktestTradeResult



====================================================================

63\. BACKTEST RUN

====================================================================



Aggregate Root:



&#x20;   BacktestRun



Inputs:



&#x20;   strategy version

&#x20;   dataset version

&#x20;   feature versions

&#x20;   model versions where applicable

&#x20;   execution configuration

&#x20;   time range

&#x20;   initial capital



Outputs:



&#x20;   metrics

&#x20;   equity curve

&#x20;   trades

&#x20;   drawdown



====================================================================

64\. BACKTEST REPRODUCIBILITY

====================================================================



A backtest must be reproducible from immutable references.



Minimum:



&#x20;   strategy version



&#x20;   dataset version



&#x20;   feature version



&#x20;   model version if used



&#x20;   execution configuration



&#x20;   initial capital



&#x20;   start time



&#x20;   end time



====================================================================

65\. BACKTEST METRICS

====================================================================



Supported metrics may include:



&#x20;   total return



&#x20;   CAGR



&#x20;   Sharpe ratio



&#x20;   Sortino ratio



&#x20;   maximum drawdown



&#x20;   volatility



&#x20;   win rate



&#x20;   loss rate



&#x20;   profit factor



&#x20;   expectancy



&#x20;   average win



&#x20;   average loss



&#x20;   number of trades



&#x20;   average trade duration



Metrics must be calculated using explicit definitions.



====================================================================

66\. OPTIMIZATION DOMAIN

====================================================================



Core concepts:



&#x20;   OptimizationRun

&#x20;   OptimizationParameter

&#x20;   OptimizationTrial

&#x20;   OptimizationResult



====================================================================

67\. OPTIMIZATION RUN

====================================================================



Aggregate Root:



&#x20;   OptimizationRun



Fields:



&#x20;   id

&#x20;   name

&#x20;   optimization\_type

&#x20;   target\_metric

&#x20;   configuration

&#x20;   status



Responsibilities:



&#x20;   manage optimization lifecycle



====================================================================

68\. OPTIMIZATION PARAMETER

====================================================================



Defines:



&#x20;   parameter name



&#x20;   type



&#x20;   search space



Examples:



&#x20;   RSI period

&#x20;   stop loss %

&#x20;   take profit %

&#x20;   moving average period



====================================================================

69\. OPTIMIZATION TRIAL

====================================================================



Entity:



&#x20;   OptimizationTrial



Contains:



&#x20;   trial number

&#x20;   selected parameters

&#x20;   execution state

&#x20;   result



====================================================================

70\. LEARNING DOMAIN

====================================================================



Core concepts:



&#x20;   LearningSession

&#x20;   Feedback

&#x20;   Adaptation



====================================================================

71\. LEARNING SESSION

====================================================================



Aggregate Root:



&#x20;   LearningSession



Represents:



&#x20;   one controlled self-learning operation.



Fields:



&#x20;   id

&#x20;   type

&#x20;   configuration

&#x20;   start\_time

&#x20;   end\_time

&#x20;   status



====================================================================

72\. FEEDBACK

====================================================================



Entity:



&#x20;   Feedback



Sources may include:



&#x20;   prediction result



&#x20;   strategy result



&#x20;   trade outcome



&#x20;   backtest result



&#x20;   human evaluation



Feedback must have:



&#x20;   source

&#x20;   type

&#x20;   score/value

&#x20;   timestamp

&#x20;   context



====================================================================

73\. ADAPTATION

====================================================================



Entity:



&#x20;   Adaptation



Represents:



&#x20;   controlled change derived from learning.



Fields:



&#x20;   target

&#x20;   previous configuration

&#x20;   new configuration

&#x20;   reason

&#x20;   evidence



Adaptations must be auditable.



Self-learning must never silently modify production trading logic.



====================================================================

74\. RECONCILIATION DOMAIN

====================================================================



Core concepts:



&#x20;   ReconciliationSession

&#x20;   ReconciliationResult

&#x20;   Discrepancy



====================================================================

75\. RECONCILIATION SESSION

====================================================================



Aggregate Root:



&#x20;   ReconciliationSession



Purpose:



&#x20;   compare internal state with external provider state.



Examples:



&#x20;   orders

&#x20;   executions

&#x20;   positions

&#x20;   balances



====================================================================

76\. DISCREPANCY

====================================================================



Entity:



&#x20;   Discrepancy



Fields:



&#x20;   type

&#x20;   internal\_value

&#x20;   external\_value

&#x20;   severity

&#x20;   status

&#x20;   resolution



Statuses:



&#x20;   OPEN

&#x20;   INVESTIGATING

&#x20;   RESOLVED

&#x20;   IGNORED



====================================================================

77\. DOMAIN SERVICES

====================================================================



Domain Services are used only where logic does not naturally belong

to a single entity/value object.



Required conceptual services:



&#x20;   PositionCalculator



&#x20;   PnLCalculator



&#x20;   RiskEvaluator



&#x20;   OrderValidator



&#x20;   OrderTransitionPolicy



&#x20;   SignalEvaluator



&#x20;   PortfolioValuationService



&#x20;   TradeLifecycleService



&#x20;   BacktestMetricCalculator



&#x20;   ReconciliationService



====================================================================

78\. POSITION CALCULATOR

====================================================================



Responsibilities:



&#x20;   calculate new position after execution



&#x20;   calculate average entry price



&#x20;   calculate realized PnL



&#x20;   calculate remaining quantity



Must be deterministic.



====================================================================

79\. PNL CALCULATOR

====================================================================



Responsibilities:



&#x20;   realized PnL



&#x20;   unrealized PnL



&#x20;   fees



&#x20;   net PnL



Must support:



&#x20;   LONG



&#x20;   SHORT



====================================================================

80\. RISK EVALUATOR

====================================================================



Input:



&#x20;   signal



&#x20;   account



&#x20;   portfolio



&#x20;   market state



&#x20;   risk profile



Output:



&#x20;   RiskEvaluation



Must not:



&#x20;   submit orders



&#x20;   access broker



&#x20;   mutate database



====================================================================

81\. ORDER VALIDATOR

====================================================================



Validates:



&#x20;   quantity



&#x20;   price



&#x20;   order type



&#x20;   instrument



&#x20;   account



&#x20;   execution mode



&#x20;   risk authorization



====================================================================

82\. PORTFOLIO VALUATION

====================================================================



Responsibilities:



&#x20;   calculate current equity



&#x20;   calculate exposure



&#x20;   calculate unrealized PnL



&#x20;   calculate drawdown



====================================================================

83\. DOMAIN POLICIES

====================================================================



Policies may define:



&#x20;   position sizing



&#x20;   risk limits



&#x20;   execution constraints



&#x20;   signal acceptance



&#x20;   market-session restrictions



&#x20;   portfolio constraints



Policies must be explicit objects.



Avoid giant conditional statements distributed throughout the code.



====================================================================

84\. DOMAIN SPECIFICATIONS

====================================================================



Specifications may represent reusable business predicates.



Examples:



&#x20;   IsTradableInstrument



&#x20;   IsValidOrder



&#x20;   IsRiskApproved



&#x20;   IsMarketOpen



&#x20;   IsWithinRiskLimit



&#x20;   IsPositionClosable



====================================================================

85\. DOMAIN EVENTS

====================================================================



Required conceptual events:



&#x20;   InstrumentCreated



&#x20;   MarketDataReceived



&#x20;   CandleClosed



&#x20;   FeatureCalculated



&#x20;   PredictionGenerated



&#x20;   SignalGenerated



&#x20;   RiskEvaluated



&#x20;   RiskApproved



&#x20;   RiskRejected



&#x20;   OrderCreated



&#x20;   OrderValidated



&#x20;   OrderSubmitted



&#x20;   OrderPartiallyFilled



&#x20;   OrderFilled



&#x20;   OrderCancelled



&#x20;   OrderRejected



&#x20;   TradeOpened



&#x20;   TradeClosed



&#x20;   PositionOpened



&#x20;   PositionIncreased



&#x20;   PositionReduced



&#x20;   PositionClosed



&#x20;   PortfolioUpdated



&#x20;   BacktestStarted



&#x20;   BacktestCompleted



&#x20;   SimulationStarted



&#x20;   SimulationCompleted



&#x20;   ModelTrained



&#x20;   ModelValidated



&#x20;   ModelActivated



====================================================================

86\. DOMAIN EVENT RULES

====================================================================



Domain events:



&#x20;   are facts



&#x20;   use past-tense names



&#x20;   are immutable



&#x20;   contain identifiers and relevant business data



&#x20;   must not contain infrastructure objects



Example:



&#x20;   OrderFilled



NOT:



&#x20;   ExecuteOrderCommandCompleted



====================================================================

87\. EVENT PAYLOAD

====================================================================



Domain events should contain:



&#x20;   event\_id



&#x20;   occurred\_at



&#x20;   aggregate\_id



&#x20;   aggregate\_type



&#x20;   correlation\_id



&#x20;   causation\_id



&#x20;   event-specific data



====================================================================

88\. AGGREGATE BOUNDARIES

====================================================================



Instrument Aggregate:



&#x20;   Instrument



MarketData Aggregate:



&#x20;   MarketDataSeries

&#x20;   Candle/Tick observations



Strategy Aggregate:



&#x20;   Strategy

&#x20;   StrategyVersion



Risk Aggregate:



&#x20;   RiskProfile

&#x20;   RiskRules



Account Aggregate:



&#x20;   Account

&#x20;   Balances



Portfolio Aggregate:



&#x20;   Portfolio

&#x20;   Positions



Order Aggregate:



&#x20;   Order

&#x20;   order lifecycle



Trade Aggregate:



&#x20;   Trade

&#x20;   Trade legs



Model Aggregate:



&#x20;   Model

&#x20;   Model versions



Dataset Aggregate:



&#x20;   Dataset

&#x20;   Dataset versions



Backtest Aggregate:



&#x20;   BacktestRun

&#x20;   results



====================================================================

89\. CROSS-AGGREGATE RULE

====================================================================



Aggregates should reference other aggregates by identity.



Do NOT embed entire aggregate graphs.



Example:



&#x20;   Order



references:



&#x20;   account\_id



&#x20;   instrument\_id



&#x20;   strategy\_run\_id



&#x20;   risk\_decision\_id



rather than embedding:



&#x20;   Account



&#x20;   Instrument



&#x20;   Strategy



&#x20;   RiskProfile



====================================================================

90\. DOMAIN COMMANDS

====================================================================



Conceptual commands:



&#x20;   CreateOrder



&#x20;   ValidateOrder



&#x20;   SubmitOrder



&#x20;   CancelOrder



&#x20;   RecordExecution



&#x20;   OpenPosition



&#x20;   ReducePosition



&#x20;   ClosePosition



&#x20;   GenerateSignal



&#x20;   EvaluateRisk



&#x20;   GeneratePrediction



&#x20;   StartBacktest



&#x20;   CompleteBacktest



&#x20;   StartSimulation



&#x20;   CompleteSimulation



&#x20;   TrainModel



&#x20;   ValidateModel



&#x20;   ActivateModel



====================================================================

91\. COMMAND RULE

====================================================================



Commands represent intent.



Events represent facts.



Example:



&#x20;   Command:

&#x20;       SubmitOrder



&#x20;   Event:

&#x20;       OrderSubmitted



Never confuse commands with events.



====================================================================

92\. DOMAIN STATE MACHINE

====================================================================



Primary trading flow:



&#x20;   MarketData

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

&#x20;       ↓

&#x20;   PnL



====================================================================

93\. LIVE TRADING BOUNDARY

====================================================================



Live trading requires:



&#x20;   valid instrument



&#x20;   valid account



&#x20;   valid strategy



&#x20;   valid signal



&#x20;   valid risk decision



&#x20;   valid order



&#x20;   explicit LIVE execution mode



&#x20;   provider authorization



No domain object may accidentally switch:



&#x20;   SIMULATION

&#x20;       → LIVE



without explicit transition.



====================================================================

94\. EXECUTION MODE

====================================================================



Value Object / Enum:



&#x20;   ExecutionMode



Values:



&#x20;   RESEARCH

&#x20;   BACKTEST

&#x20;   SIMULATION

&#x20;   PAPER

&#x20;   LIVE



Each mode must have explicit semantics.



====================================================================

95\. MODE SAFETY

====================================================================



SIMULATION:



&#x20;   must never submit live broker orders.



BACKTEST:



&#x20;   must never submit live broker orders.



PAPER:



&#x20;   must not use real capital.



LIVE:



&#x20;   requires explicit authorization.



====================================================================

96\. FINANCIAL PRECISION

====================================================================



All financial domain calculations must use:



&#x20;   Decimal



Never:



&#x20;   float



This applies to:



&#x20;   Price



&#x20;   Quantity



&#x20;   Money



&#x20;   PnL



&#x20;   Fees



&#x20;   Returns



&#x20;   Exposure



&#x20;   Risk



====================================================================

97\. ROUNDING

====================================================================



Rounding must be explicit.



Domain must define where rounding occurs.



Do NOT repeatedly round intermediate calculations unless required by

instrument/account rules.



====================================================================

98\. CURRENCY RULES

====================================================================



Money arithmetic:



&#x20;   same currency:

&#x20;       allowed



&#x20;   different currencies:

&#x20;       requires explicit conversion



Never silently convert currencies.



Currency conversion requires:



&#x20;   exchange rate



&#x20;   rate timestamp



&#x20;   source



====================================================================

99\. FEES

====================================================================



Fees must be represented explicitly.



Fee contains:



&#x20;   amount



&#x20;   currency



&#x20;   type



Examples:



&#x20;   COMMISSION



&#x20;   SPREAD



&#x20;   FUNDING



&#x20;   TAX



&#x20;   OTHER



====================================================================

100\. SLIPPAGE

====================================================================



Slippage must be explicit in simulation/backtest.



It must never be silently applied to live domain values.



====================================================================

101\. EXPOSURE

====================================================================



Exposure represents financial risk associated with open positions.



Exposure calculation must consider:



&#x20;   quantity



&#x20;   price



&#x20;   contract specification



&#x20;   direction



&#x20;   leverage where applicable



====================================================================

102\. LEVERAGE

====================================================================



Leverage must be explicit.



Never assume:



&#x20;   leverage = 1



unless the instrument/account configuration says so.



====================================================================

103\. DRAWDOWN

====================================================================



Drawdown must be calculated relative to a defined peak.



Required concept:



&#x20;   peak\_equity



&#x20;   current\_equity



&#x20;   drawdown



The reference peak must be explicit.



====================================================================

104\. RISK INVARIANTS

====================================================================



Risk evaluation must prevent:



&#x20;   invalid quantity



&#x20;   excessive exposure



&#x20;   prohibited instruments



&#x20;   exceeded loss limits



&#x20;   exceeded drawdown limits



&#x20;   invalid account state



&#x20;   invalid market state



====================================================================

105\. STRATEGY INVARIANTS

====================================================================



A strategy version:



&#x20;   is immutable after publication.



A signal:



&#x20;   must reference strategy context.



A strategy must not directly execute an order.



Strategy produces intent.



Risk authorizes.



Trading executes.



====================================================================

106\. AI INVARIANTS

====================================================================



A prediction must reference:



&#x20;   model version



&#x20;   inference timestamp



&#x20;   instrument



&#x20;   timeframe



&#x20;   prediction context



AI model version must be immutable after activation.



====================================================================

107\. DATA LEAKAGE PREVENTION

====================================================================



The domain architecture must prevent:



&#x20;   lookahead bias



&#x20;   future leakage



&#x20;   training/test contamination



&#x20;   future-derived features



Backtest calculations must respect chronological ordering.



====================================================================

108\. REPRODUCIBILITY

====================================================================



Any:



&#x20;   prediction



&#x20;   backtest



&#x20;   simulation



&#x20;   optimization



&#x20;   training run



must be reproducible from versioned inputs and configuration.



====================================================================

109\. DOMAIN REPOSITORY INTERFACES

====================================================================



Repository interfaces may exist in the Domain/Application boundary.



Examples:



&#x20;   InstrumentRepository



&#x20;   MarketDataRepository



&#x20;   FeatureRepository



&#x20;   DatasetRepository



&#x20;   ModelRepository



&#x20;   StrategyRepository



&#x20;   RiskProfileRepository



&#x20;   AccountRepository



&#x20;   PortfolioRepository



&#x20;   OrderRepository



&#x20;   TradeRepository



&#x20;   BacktestRepository



&#x20;   SimulationRepository



&#x20;   OptimizationRepository



====================================================================

110\. REPOSITORY RULE

====================================================================



Repository interfaces define persistence intent.



They must NOT expose:



&#x20;   SQL



&#x20;   ORM session



&#x20;   database cursor



&#x20;   connection string



&#x20;   provider SDK



====================================================================

111\. DOMAIN FACTORIES

====================================================================



Factories may be used when construction is complex.



Examples:



&#x20;   OrderFactory



&#x20;   SignalFactory



&#x20;   StrategyFactory



&#x20;   ModelVersionFactory



&#x20;   BacktestFactory



Factory responsibilities:



&#x20;   validate creation rules



&#x20;   construct valid objects



&#x20;   enforce required invariants



====================================================================

112\. DOMAIN EXCEPTIONS

====================================================================



Domain-specific exceptions should include concepts such as:



&#x20;   InvalidOrder



&#x20;   InvalidPosition



&#x20;   InvalidPrice



&#x20;   InvalidQuantity



&#x20;   InvalidRiskDecision



&#x20;   InvalidStateTransition



&#x20;   InvalidStrategyVersion



&#x20;   InvalidModelVersion



&#x20;   InvalidDatasetVersion



&#x20;   InsufficientBalance



&#x20;   RiskLimitExceeded



&#x20;   UnsupportedExecutionMode



====================================================================

113\. EXCEPTION RULE

====================================================================



Exceptions must express business meaning.



Bad:



&#x20;   ValueError("bad thing")



Good:



&#x20;   RiskLimitExceeded



====================================================================

114\. IMMUTABILITY

====================================================================



Prefer immutable objects for:



&#x20;   Money



&#x20;   Price



&#x20;   Quantity



&#x20;   Percentage



&#x20;   Timeframe



&#x20;   Timestamp



&#x20;   PnL



&#x20;   DatasetVersion



&#x20;   ModelVersion



&#x20;   StrategyVersion



&#x20;   RiskDecision



&#x20;   DomainEvents



====================================================================

115\. DOMAIN MODEL VS APPLICATION

====================================================================



Domain:



&#x20;   business rules



&#x20;   invariants



&#x20;   calculations



&#x20;   state transitions



Application:



&#x20;   orchestration



&#x20;   workflows



&#x20;   transaction coordination



&#x20;   command handling



Infrastructure:



&#x20;   database



&#x20;   brokers



&#x20;   market data providers



&#x20;   ML frameworks



&#x20;   filesystem



====================================================================

116\. DOMAIN MODEL VS BROKER

====================================================================



Broker-specific concepts must NOT leak into Domain.



Example:



&#x20;   BrokerOrderResponse



must be translated into:



&#x20;   Execution



or:



&#x20;   OrderStatusUpdate



====================================================================

117\. DOMAIN MODEL VS AI FRAMEWORK

====================================================================



TensorFlow/Keras/PyTorch objects must NOT appear in Domain.



Domain stores concepts such as:



&#x20;   ModelVersion



&#x20;   Prediction



&#x20;   TrainingRun



Infrastructure handles:



&#x20;   model loading



&#x20;   tensor operations



&#x20;   GPU



&#x20;   inference runtime



====================================================================

118\. DOMAIN MODEL VS DATABASE

====================================================================



SQL table structure must not determine:



&#x20;   aggregate boundaries



&#x20;   entity behavior



&#x20;   domain invariants



Database mapping belongs to Infrastructure.



====================================================================

119\. DOMAIN PACKAGE STRUCTURE

====================================================================



Recommended logical structure:



&#x20;   src/

&#x20;       ShadBotTrader/

&#x20;           domain/

&#x20;               common/

&#x20;               market/

&#x20;               feature/

&#x20;               ai/

&#x20;               strategy/

&#x20;               risk/

&#x20;               account/

&#x20;               portfolio/

&#x20;               trading/

&#x20;               simulation/

&#x20;               backtest/

&#x20;               optimization/

&#x20;               learning/

&#x20;               reconciliation/



Each bounded area may contain:



&#x20;   entities/

&#x20;   value\_objects/

&#x20;   aggregates/

&#x20;   services/

&#x20;   policies/

&#x20;   events/

&#x20;   exceptions/

&#x20;   repositories/



Only create subdirectories when justified by actual complexity.



====================================================================

120\. DOMAIN COMMON

====================================================================



Common primitives:



&#x20;   Entity



&#x20;   AggregateRoot



&#x20;   ValueObject



&#x20;   DomainEvent



&#x20;   DomainException



&#x20;   Identifier



&#x20;   Clock abstraction if required



====================================================================

121\. ENTITY BASE

====================================================================



Base Entity responsibilities:



&#x20;   identity



&#x20;   equality by identity



&#x20;   controlled lifecycle



Do not put business logic into a generic base class merely because

it is technically convenient.



====================================================================

122\. AGGREGATE ROOT BASE

====================================================================



AggregateRoot may manage:



&#x20;   domain events



&#x20;   aggregate identity



&#x20;   event collection



&#x20;   version/concurrency metadata



It must remain domain-pure.



====================================================================

123\. DOMAIN EVENT COLLECTION

====================================================================



Aggregate roots may record events internally.



Application layer later publishes them.



Domain does not publish to Kafka, RabbitMQ, database, or EventBus

directly.



====================================================================

124\. CLOCK

====================================================================



Time-sensitive domain logic should use an abstraction where

deterministic testing requires it.



Never scatter:



&#x20;   datetime.now()



through critical domain logic.



====================================================================

125\. TESTING DOMAIN MODEL

====================================================================



Every aggregate must have unit tests for:



&#x20;   valid creation



&#x20;   invalid creation



&#x20;   state transitions



&#x20;   invariants



&#x20;   edge cases



&#x20;   domain events



&#x20;   financial precision



====================================================================

126\. ORDER TEST MATRIX

====================================================================



Must test:



&#x20;   create



&#x20;   validate



&#x20;   submit



&#x20;   partial fill



&#x20;   full fill



&#x20;   cancellation



&#x20;   rejection



&#x20;   expiry



&#x20;   invalid transition



&#x20;   duplicate execution



&#x20;   overfill prevention



====================================================================

127\. POSITION TEST MATRIX

====================================================================



Must test:



&#x20;   open



&#x20;   increase



&#x20;   reduce



&#x20;   close



&#x20;   long



&#x20;   short



&#x20;   average entry



&#x20;   realized PnL



&#x20;   unrealized PnL



&#x20;   zero quantity



&#x20;   invalid negative quantity



====================================================================

128\. RISK TEST MATRIX

====================================================================



Must test:



&#x20;   approval



&#x20;   rejection



&#x20;   modification



&#x20;   exposure limit



&#x20;   position limit



&#x20;   drawdown limit



&#x20;   insufficient balance



&#x20;   invalid account state



====================================================================

129\. BACKTEST TEST MATRIX

====================================================================



Must test:



&#x20;   chronological execution



&#x20;   no lookahead



&#x20;   deterministic result



&#x20;   fees



&#x20;   slippage



&#x20;   position accounting



&#x20;   equity curve



&#x20;   drawdown



&#x20;   metrics



====================================================================

130\. AI TEST MATRIX

====================================================================



Must test:



&#x20;   model version validation



&#x20;   dataset version compatibility



&#x20;   prediction confidence bounds



&#x20;   prediction reproducibility



&#x20;   feature/model compatibility



====================================================================

131\. DOMAIN INTEGRITY

====================================================================



No aggregate should be able to enter an invalid state.



Invalid states must be rejected at construction or transition time.



====================================================================

132\. DOMAIN STATE TRANSITIONS

====================================================================



State transitions must be:



&#x20;   explicit



&#x20;   validated



&#x20;   deterministic



&#x20;   testable



Do not expose public setters that allow arbitrary state mutation.



Bad:



&#x20;   order.status = FILLED



Good:



&#x20;   order.mark\_filled(...)



====================================================================

133\. PUBLIC API OF DOMAIN OBJECTS

====================================================================



Domain objects expose behavior.



Prefer:



&#x20;   order.submit()



&#x20;   order.record\_fill()



&#x20;   order.cancel()



&#x20;   position.increase()



&#x20;   position.reduce()



&#x20;   position.close()



instead of:



&#x20;   order.status = ...



&#x20;   position.quantity = ...



====================================================================

134\. ANEMIC MODEL PROHIBITION

====================================================================



Do not implement entities as data containers with all logic in

external services.



Important business behavior must live inside the appropriate

aggregate/entity/value object or domain service.



====================================================================

135\. GOD OBJECT PROHIBITION

====================================================================



Do not create:



&#x20;   TradingManager



&#x20;   EverythingService



&#x20;   UniversalDomainService



&#x20;   MasterTradingObject



that owns all domain logic.



Split responsibilities according to domain boundaries.



====================================================================

136\. CYCLIC DEPENDENCY PROHIBITION

====================================================================



Domain packages must avoid circular dependencies.



Use:



&#x20;   identifiers



&#x20;   domain events



&#x20;   domain services



&#x20;   ports/interfaces



where appropriate.



====================================================================

137\. DOMAIN DEPENDENCY RULE

====================================================================



Domain may depend on:



&#x20;   Python standard library



&#x20;   internal domain modules



approved pure mathematical/value libraries where architecturally

justified.



Domain must NOT depend on:



&#x20;   Infrastructure



&#x20;   Application runtime



&#x20;   UI



&#x20;   Database



&#x20;   Broker SDK



&#x20;   External APIs



====================================================================

138\. DOMAIN EVENT FLOW

====================================================================



Example:



&#x20;   order.record\_fill()

&#x20;           ↓

&#x20;   OrderFilled

&#x20;           ↓

&#x20;   Application Event Dispatcher

&#x20;           ↓

&#x20;   Portfolio Update

&#x20;           ↓

&#x20;   Position Update

&#x20;           ↓

&#x20;   PnL Update



Domain creates facts.



Application coordinates reactions.



====================================================================

139\. DOMAIN DATA FLOW

====================================================================



Canonical trading decision flow:



&#x20;   MarketData

&#x20;       ↓

&#x20;   FeatureObservation

&#x20;       ↓

&#x20;   Prediction

&#x20;       ↓

&#x20;   Strategy

&#x20;       ↓

&#x20;   Signal

&#x20;       ↓

&#x20;   RiskEvaluation

&#x20;       ↓

&#x20;   RiskDecision

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

&#x20;       ↓

&#x20;   PnL



====================================================================

140\. RESEARCH FLOW

====================================================================



&#x20;   Dataset

&#x20;       ↓

&#x20;   FeatureSet

&#x20;       ↓

&#x20;   Model

&#x20;       ↓

&#x20;   TrainingRun

&#x20;       ↓

&#x20;   ModelVersion

&#x20;       ↓

&#x20;   Prediction

&#x20;       ↓

&#x20;   Evaluation



====================================================================

141\. BACKTEST FLOW

====================================================================



&#x20;   DatasetVersion

&#x20;       +

&#x20;   StrategyVersion

&#x20;       +

&#x20;   FeatureVersion

&#x20;       +

&#x20;   ModelVersion

&#x20;       +

&#x20;   BacktestConfiguration

&#x20;       ↓

&#x20;   BacktestRun

&#x20;       ↓

&#x20;   Simulation

&#x20;       ↓

&#x20;   Trades

&#x20;       ↓

&#x20;   Equity Curve

&#x20;       ↓

&#x20;   Metrics



====================================================================

142\. LIVE FLOW

====================================================================



&#x20;   MarketData

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

&#x20;   RiskDecision

&#x20;       ↓

&#x20;   Order

&#x20;       ↓

&#x20;   Broker Adapter

&#x20;       ↓

&#x20;   Execution

&#x20;       ↓

&#x20;   Trade

&#x20;       ↓

&#x20;   Position

&#x20;       ↓

&#x20;   Portfolio



The Domain never calls the Broker Adapter directly.



====================================================================

143\. DOMAIN SAFETY BOUNDARY

====================================================================



The Domain must make it structurally difficult to:



&#x20;   bypass risk



&#x20;   bypass order validation



&#x20;   execute invalid transitions



&#x20;   use float for money



&#x20;   mutate immutable versions



&#x20;   mix simulation with live execution



====================================================================

144\. FINAL DOMAIN MODEL MAP

====================================================================



&#x20;                   MARKET

&#x20;                     |

&#x20;                     v

&#x20;             +---------------+

&#x20;             |   Instrument  |

&#x20;             +---------------+

&#x20;                     |

&#x20;                     v

&#x20;             +---------------+

&#x20;             | Market Data   |

&#x20;             +---------------+

&#x20;                     |

&#x20;                     v

&#x20;             +---------------+

&#x20;             |   Features    |

&#x20;             +---------------+

&#x20;                     |

&#x20;                     v

&#x20;             +---------------+

&#x20;             |   AI Model    |

&#x20;             +---------------+

&#x20;                     |

&#x20;                     v

&#x20;             +---------------+

&#x20;             |  Prediction   |

&#x20;             +---------------+

&#x20;                     |

&#x20;                     v

&#x20;             +---------------+

&#x20;             |   Strategy    |

&#x20;             +---------------+

&#x20;                     |

&#x20;                     v

&#x20;             +---------------+

&#x20;             |    Signal     |

&#x20;             +---------------+

&#x20;                     |

&#x20;                     v

&#x20;             +---------------+

&#x20;             |     Risk      |

&#x20;             +---------------+

&#x20;                     |

&#x20;                     v

&#x20;             +---------------+

&#x20;             |     Order     |

&#x20;             +---------------+

&#x20;                     |

&#x20;                     v

&#x20;             +---------------+

&#x20;             |  Execution    |

&#x20;             +---------------+

&#x20;                     |

&#x20;                     v

&#x20;             +---------------+

&#x20;             |     Trade     |

&#x20;             +---------------+

&#x20;                     |

&#x20;                     v

&#x20;             +---------------+

&#x20;             |   Position    |

&#x20;             +---------------+

&#x20;                     |

&#x20;                     v

&#x20;             +---------------+

&#x20;             |   Portfolio   |

&#x20;             +---------------+

&#x20;                     |

&#x20;                     v

&#x20;             +---------------+

&#x20;             |     PnL       |

&#x20;             +---------------+



Parallel domains:



&#x20;   Backtesting

&#x20;   Simulation

&#x20;   Optimization

&#x20;   Learning

&#x20;   Reconciliation



all consume and produce domain concepts through explicit

boundaries.



====================================================================

145\. IMPLEMENTATION ORDER

====================================================================



The coding agent should implement the Domain in this order:



&#x20;   STEP 1:

&#x20;       common primitives



&#x20;   STEP 2:

&#x20;       Value Objects



&#x20;   STEP 3:

&#x20;       Market entities



&#x20;   STEP 4:

&#x20;       MarketData aggregate



&#x20;   STEP 5:

&#x20;       Feature domain



&#x20;   STEP 6:

&#x20;       AI domain



&#x20;   STEP 7:

&#x20;       Strategy domain



&#x20;   STEP 8:

&#x20;       Risk domain



&#x20;   STEP 9:

&#x20;       Account domain



&#x20;   STEP 10:

&#x20;       Portfolio domain



&#x20;   STEP 11:

&#x20;       Trading domain



&#x20;   STEP 12:

&#x20;       Simulation domain



&#x20;   STEP 13:

&#x20;       Backtest domain



&#x20;   STEP 14:

&#x20;       Optimization domain



&#x20;   STEP 15:

&#x20;       Learning domain



&#x20;   STEP 16:

&#x20;       Reconciliation domain



&#x20;   STEP 17:

&#x20;       Domain events



&#x20;   STEP 18:

&#x20;       Domain services



&#x20;   STEP 19:

&#x20;       Repository interfaces



&#x20;   STEP 20:

&#x20;       Domain tests



====================================================================

146\. IMPLEMENTATION RULE

====================================================================



Before implementing any Domain object, the coding agent MUST:



&#x20;   inspect existing project structure



&#x20;   inspect current Domain code



&#x20;   inspect existing naming conventions



&#x20;   inspect existing imports



&#x20;   inspect existing tests



&#x20;   inspect current architecture documents



&#x20;   preserve already-approved architecture



The agent MUST NOT redesign the architecture simply because a

different implementation appears easier.



====================================================================

147\. QUALITY GATE

====================================================================



After implementation:



&#x20;   python -m ruff check .



&#x20;   python -m black --check .



&#x20;   python -m mypy src



&#x20;   python -m pytest



All checks must pass.



If a check fails:



&#x20;   identify root cause



&#x20;   fix implementation



&#x20;   rerun checks



Do not disable rules merely to make the checks pass.



====================================================================

148\. COMPLETION CRITERIA

====================================================================



Domain implementation is complete only when:



&#x20;   \[ ] All core Value Objects exist



&#x20;   \[ ] All core Entities exist



&#x20;   \[ ] All required Aggregate Roots exist



&#x20;   \[ ] Aggregate boundaries are enforced



&#x20;   \[ ] State transitions are explicit



&#x20;   \[ ] Business invariants are enforced



&#x20;   \[ ] Domain Events exist



&#x20;   \[ ] Domain Services exist where required



&#x20;   \[ ] Repository interfaces exist



&#x20;   \[ ] Financial calculations use Decimal



&#x20;   \[ ] No infrastructure dependency exists in Domain



&#x20;   \[ ] No ORM dependency exists in Domain



&#x20;   \[ ] No broker SDK dependency exists in Domain



&#x20;   \[ ] No AI framework dependency exists in Domain



&#x20;   \[ ] Live/SIMULATION/BACKTEST boundaries are enforced



&#x20;   \[ ] Order lifecycle is tested



&#x20;   \[ ] Position lifecycle is tested



&#x20;   \[ ] Risk rules are tested



&#x20;   \[ ] PnL calculations are tested



&#x20;   \[ ] Backtest determinism is tested



&#x20;   \[ ] Lookahead prevention is tested



&#x20;   \[ ] Domain events are tested



&#x20;   \[ ] Invalid states are rejected



&#x20;   \[ ] Ruff passes



&#x20;   \[ ] Black passes



&#x20;   \[ ] Mypy passes



&#x20;   \[ ] Pytest passes



====================================================================

149\. ABSOLUTE PROHIBITIONS

====================================================================



The coding agent MUST NOT:



&#x20;   create an anemic Domain model



&#x20;   put business logic in controllers



&#x20;   put business logic in repositories



&#x20;   put business logic in ORM models



&#x20;   put SQL in Domain



&#x20;   import broker SDKs into Domain



&#x20;   import TensorFlow/Keras/PyTorch into Domain



&#x20;   use float for financial calculations



&#x20;   expose arbitrary state setters



&#x20;   bypass aggregate boundaries



&#x20;   allow direct order execution without risk authorization



&#x20;   allow live execution from simulation/backtest code



&#x20;   mutate published versions



&#x20;   use future market information in historical calculations



&#x20;   silently convert currencies



&#x20;   silently apply slippage



&#x20;   silently round financial values



&#x20;   create a giant TradingManager/God Object



&#x20;   introduce circular dependencies



&#x20;   invent business rules not defined by the architecture



====================================================================

150\. FINAL DOMAIN PRINCIPLE

====================================================================



The ShadBotTrader Domain Model is the central expression of the

business of the platform.



The most important rule is:



&#x20;   VALID DOMAIN STATE > CONVENIENT IMPLEMENTATION



Every implementation decision must preserve:



&#x20;   correctness



&#x20;   financial integrity



&#x20;   determinism



&#x20;   reproducibility



&#x20;   auditability



&#x20;   explicit business rules



&#x20;   aggregate consistency



&#x20;   separation of concerns



&#x20;   live-trading safety



The Domain is the source of business truth.



Infrastructure persists it.



Application orchestrates it.



External systems integrate with it.



Nothing external is allowed to redefine the Domain.



====================================================================

END OF DOMAIN\_MODEL\_SPECIFICATION

====================================================================

