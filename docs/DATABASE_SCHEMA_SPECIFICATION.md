====================================================================

SHADBOTTRADER

DATABASE\_SCHEMA\_SPECIFICATION

====================================================================



DOCUMENT TYPE:

&#x20;   Canonical Database Architecture \& Schema Specification



PROJECT:

&#x20;   ShadBotTrader



DATABASE ROLE:

&#x20;   Persistent enterprise data platform for ShadBotTrader



PRIMARY DATABASE TARGET:

&#x20;   SQL Server



DATABASE DESIGN PRINCIPLES:

&#x20;   Relational

&#x20;   Normalized

&#x20;   Auditable

&#x20;   Versionable

&#x20;   Deterministic

&#x20;   Transactional

&#x20;   Extensible

&#x20;   Migration-driven

&#x20;   Domain-aligned



====================================================================

1\. PURPOSE

====================================================================



The database is responsible for persistent storage of:



&#x20;   Market Data

&#x20;   Instruments

&#x20;   Timeframes

&#x20;   Features

&#x20;   Predictions

&#x20;   Signals

&#x20;   Strategies

&#x20;   Risk Decisions

&#x20;   Orders

&#x20;   Executions

&#x20;   Trades

&#x20;   Positions

&#x20;   Accounts

&#x20;   Portfolios

&#x20;   Portfolio Snapshots

&#x20;   PnL

&#x20;   Backtests

&#x20;   Simulations

&#x20;   Experiments

&#x20;   AI Models

&#x20;   Model Versions

&#x20;   Training Runs

&#x20;   Datasets

&#x20;   News

&#x20;   Events

&#x20;   Configuration

&#x20;   Audit Records

&#x20;   System State

&#x20;   Project Intelligence State



The database is NOT responsible for:



&#x20;   Domain business logic

&#x20;   Strategy logic

&#x20;   Risk calculations

&#x20;   AI inference logic

&#x20;   Application orchestration

&#x20;   UI logic



The database stores state.



The Application and Domain layers own behavior.



====================================================================

2\. DATABASE ARCHITECTURE

====================================================================



Logical database domains:



&#x20;   reference

&#x20;   market

&#x20;   feature

&#x20;   ai

&#x20;   strategy

&#x20;   risk

&#x20;   trading

&#x20;   portfolio

&#x20;   simulation

&#x20;   backtest

&#x20;   optimization

&#x20;   learning

&#x20;   news

&#x20;   system

&#x20;   audit

&#x20;   project



These logical domains may be represented as SQL Server schemas.



Recommended SQL Server schemas:



&#x20;   ref

&#x20;   market

&#x20;   feature

&#x20;   ai

&#x20;   strategy

&#x20;   risk

&#x20;   trading

&#x20;   portfolio

&#x20;   simulation

&#x20;   backtest

&#x20;   optimization

&#x20;   learning

&#x20;   news

&#x20;   system

&#x20;   audit

&#x20;   project



====================================================================

3\. DATABASE NAMING

====================================================================



Rules:



&#x20;   Table names:

&#x20;       singular PascalCase or singular snake\_case



&#x20;   Column names:

&#x20;       snake\_case



&#x20;   Primary keys:

&#x20;       id



&#x20;   Foreign keys:

&#x20;       <entity>\_id



&#x20;   Created timestamp:

&#x20;       created\_at



&#x20;   Updated timestamp:

&#x20;       updated\_at



&#x20;   Deleted timestamp:

&#x20;       deleted\_at



Recommended standard:



&#x20;   snake\_case



Example:



&#x20;   market.instrument



&#x20;   market.candle



&#x20;   trading.order



&#x20;   trading.execution



====================================================================

4\. PRIMARY KEY STRATEGY

====================================================================



All major persistent entities MUST have a stable primary key.



Recommended:



&#x20;   UUID / UNIQUEIDENTIFIER



Example:



&#x20;   id UNIQUEIDENTIFIER NOT NULL



Primary keys must not encode business meaning.



Do NOT use:



&#x20;   symbol as PK

&#x20;   order\_number as PK

&#x20;   ticker as PK



Business identifiers may have UNIQUE constraints.



====================================================================

5\. TEMPORAL STANDARD

====================================================================



All timestamps MUST use UTC.



Recommended SQL Server type:



&#x20;   DATETIME2(7)



Example:



&#x20;   created\_at DATETIME2(7) NOT NULL



Never store application timestamps as local machine time.



====================================================================

6\. MONEY / FINANCIAL PRECISION

====================================================================



Financial values MUST NOT use FLOAT.



Do NOT use:



&#x20;   FLOAT

&#x20;   REAL



Recommended:



&#x20;   DECIMAL(38, 18)



or domain-specific precision such as:



&#x20;   DECIMAL(28, 10)

&#x20;   DECIMAL(28, 18)



depending on the value.



Examples:



&#x20;   price

&#x20;   quantity

&#x20;   balance

&#x20;   fee

&#x20;   pnl

&#x20;   exposure



must use DECIMAL.



====================================================================

7\. BOOLEAN

====================================================================



SQL Server:



&#x20;   BIT



Examples:



&#x20;   is\_active

&#x20;   is\_enabled

&#x20;   is\_live

&#x20;   is\_valid



====================================================================

8\. ENUM STRATEGY

====================================================================



Do not store arbitrary Python enum names without validation.



For stable finite enumerations use either:



&#x20;   reference tables



or:



&#x20;   VARCHAR + CHECK constraint



depending on domain requirements.



Trading-critical states should be controlled.



====================================================================

9\. AUDIT COLUMNS

====================================================================



Persistent entities should normally contain:



&#x20;   created\_at

&#x20;   updated\_at



Where lifecycle/history matters:



&#x20;   deleted\_at

&#x20;   version



Version may be:



&#x20;   BIGINT



or SQL Server ROWVERSION where appropriate.



====================================================================

10\. CONCURRENCY

====================================================================



Optimistic concurrency should be supported for mutable aggregate

records.



Recommended:



&#x20;   rowversion



where appropriate.



Do not use application timestamps as concurrency tokens.



====================================================================

11\. DATABASE SCHEMAS

====================================================================



The database should contain the following logical schemas:



&#x20;   ref

&#x20;   market

&#x20;   feature

&#x20;   ai

&#x20;   strategy

&#x20;   risk

&#x20;   trading

&#x20;   portfolio

&#x20;   simulation

&#x20;   backtest

&#x20;   optimization

&#x20;   learning

&#x20;   news

&#x20;   system

&#x20;   audit

&#x20;   project



====================================================================

12\. REF SCHEMA

====================================================================



Purpose:



&#x20;   Static and semi-static reference data.



Tables:



&#x20;   ref.currency



&#x20;   ref.exchange



&#x20;   ref.market



&#x20;   ref.timeframe



&#x20;   ref.instrument\_type



====================================================================

13\. ref.currency

====================================================================



Purpose:



&#x20;   Supported currencies.



Columns:



&#x20;   id

&#x20;   code

&#x20;   name

&#x20;   numeric\_code

&#x20;   decimals

&#x20;   is\_active

&#x20;   created\_at

&#x20;   updated\_at



Constraints:



&#x20;   code UNIQUE



Examples:



&#x20;   USD

&#x20;   EUR

&#x20;   GBP

&#x20;   JPY



====================================================================

14\. ref.exchange

====================================================================



Purpose:



&#x20;   Exchange or market venue.



Columns:



&#x20;   id

&#x20;   code

&#x20;   name

&#x20;   country

&#x20;   timezone

&#x20;   currency\_id

&#x20;   is\_active

&#x20;   created\_at

&#x20;   updated\_at



Foreign keys:



&#x20;   currency\_id

&#x20;       → ref.currency.id



====================================================================

15\. ref.market

====================================================================



Purpose:



&#x20;   Logical market classification.



Columns:



&#x20;   id

&#x20;   code

&#x20;   name

&#x20;   description

&#x20;   is\_active

&#x20;   created\_at

&#x20;   updated\_at



Examples:



&#x20;   FOREX

&#x20;   CRYPTO

&#x20;   EQUITY

&#x20;   FUTURES

&#x20;   COMMODITY

====================================================================

16\. ref.timeframe

====================================================================



Purpose:



&#x20;   Supported candle/time-series intervals.



Columns:



&#x20;   id

&#x20;   code

&#x20;   name

&#x20;   duration\_seconds

&#x20;   is\_active



Examples:



&#x20;   1m

&#x20;   5m

&#x20;   15m

&#x20;   1h

&#x20;   4h

&#x20;   1d



Constraints:



&#x20;   code UNIQUE



====================================================================

17\. MARKET SCHEMA

====================================================================



Purpose:



&#x20;   Market instruments and historical market data.



Core tables:



&#x20;   market.instrument



&#x20;   market.instrument\_symbol



&#x20;   market.candle



&#x20;   market.tick



&#x20;   market.market\_data\_batch



&#x20;   market.data\_source



====================================================================

18\. market.instrument

====================================================================



Purpose:



&#x20;   Canonical financial instrument identity.



Columns:



&#x20;   id

&#x20;   symbol

&#x20;   name

&#x20;   instrument\_type\_id

&#x20;   market\_id

&#x20;   base\_currency\_id

&#x20;   quote\_currency\_id

&#x20;   exchange\_id

&#x20;   is\_active

&#x20;   created\_at

&#x20;   updated\_at



Foreign keys:



&#x20;   market\_id

&#x20;       → ref.market.id



&#x20;   base\_currency\_id

&#x20;       → ref.currency.id



&#x20;   quote\_currency\_id

&#x20;       → ref.currency.id



&#x20;   exchange\_id

&#x20;       → ref.exchange.id



Constraints:



&#x20;   canonical identity must be unique



====================================================================

19\. market.instrument\_symbol

====================================================================



Purpose:



&#x20;   Provider-specific symbol mapping.



Columns:



&#x20;   id

&#x20;   instrument\_id

&#x20;   provider

&#x20;   provider\_symbol

&#x20;   valid\_from

&#x20;   valid\_to

&#x20;   is\_active

&#x20;   created\_at

&#x20;   updated\_at



Example:



&#x20;   canonical:

&#x20;       EURUSD



&#x20;   broker A:

&#x20;       EUR/USD



&#x20;   provider B:

&#x20;       EURUSD=X



This prevents external naming conventions from leaking into Domain.



====================================================================

20\. market.data\_source

====================================================================



Purpose:



&#x20;   Market data provider registry.



Columns:



&#x20;   id

&#x20;   code

&#x20;   name

&#x20;   provider\_type

&#x20;   configuration\_reference

&#x20;   is\_active

&#x20;   created\_at

&#x20;   updated\_at



Credentials MUST NOT be stored directly.



Only secure references may be stored.



====================================================================

21\. market.market\_data\_batch

====================================================================



Purpose:



&#x20;   Track ingestion batches.



Columns:



&#x20;   id

&#x20;   data\_source\_id

&#x20;   instrument\_id

&#x20;   timeframe\_id

&#x20;   started\_at

&#x20;   completed\_at

&#x20;   first\_timestamp

&#x20;   last\_timestamp

&#x20;   record\_count

&#x20;   status

&#x20;   error\_message

&#x20;   created\_at



Statuses:



&#x20;   CREATED

&#x20;   RUNNING

&#x20;   COMPLETED

&#x20;   FAILED

&#x20;   PARTIAL



====================================================================

22\. market.candle

====================================================================



Purpose:



&#x20;   OHLCV time-series data.



Columns:



&#x20;   id

&#x20;   instrument\_id

&#x20;   timeframe\_id

&#x20;   timestamp

&#x20;   open

&#x20;   high

&#x20;   low

&#x20;   close

&#x20;   volume

&#x20;   spread

&#x20;   data\_source\_id

&#x20;   batch\_id

&#x20;   created\_at



Constraints:



&#x20;   instrument\_id

&#x20;   timeframe\_id

&#x20;   timestamp



must form a unique key for a canonical dataset.



OHLC validation:



&#x20;   high >= open

&#x20;   high >= close

&#x20;   high >= low



&#x20;   low <= open

&#x20;   low <= close



Prices MUST be positive where instrument semantics require it.



====================================================================

23\. market.tick

====================================================================



Purpose:



&#x20;   Optional high-frequency market observations.



Columns:



&#x20;   id

&#x20;   instrument\_id

&#x20;   timestamp

&#x20;   bid

&#x20;   ask

&#x20;   last\_price

&#x20;   bid\_volume

&#x20;   ask\_volume

&#x20;   data\_source\_id

&#x20;   created\_at



Constraint:



&#x20;   ask >= bid where applicable.



====================================================================

24\. FEATURE SCHEMA

====================================================================



Purpose:



&#x20;   Persist calculated features and feature definitions.



Tables:



&#x20;   feature.definition



&#x20;   feature.version



&#x20;   feature.value



&#x20;   feature.dataset



====================================================================

25\. feature.definition

====================================================================



Purpose:



&#x20;   Defines a feature.



Columns:



&#x20;   id

&#x20;   code

&#x20;   name

&#x20;   description

&#x20;   category

&#x20;   calculation\_type

&#x20;   is\_active

&#x20;   created\_at

&#x20;   updated\_at



Constraint:



&#x20;   code UNIQUE



====================================================================

26\. feature.version

====================================================================



Purpose:



&#x20;   Versioned feature calculation definition.



Columns:



&#x20;   id

&#x20;   feature\_id

&#x20;   version

&#x20;   configuration\_json

&#x20;   source\_hash

&#x20;   created\_at



Constraint:



&#x20;   feature\_id + version UNIQUE



====================================================================

27\. feature.value

====================================================================



Purpose:



&#x20;   Stores calculated feature observations.



Columns:



&#x20;   id

&#x20;   instrument\_id

&#x20;   timeframe\_id

&#x20;   feature\_version\_id

&#x20;   timestamp

&#x20;   value

&#x20;   quality\_status

&#x20;   created\_at



Unique:



&#x20;   instrument\_id

&#x20;   timeframe\_id

&#x20;   feature\_version\_id

&#x20;   timestamp



No future information may be used to calculate a feature at timestamp T.



====================================================================

28\. AI SCHEMA

====================================================================



Purpose:



&#x20;   Machine learning and inference state.



Tables:



&#x20;   ai.dataset



&#x20;   ai.dataset\_version



&#x20;   ai.model



&#x20;   ai.model\_version



&#x20;   ai.training\_run



&#x20;   ai.prediction



&#x20;   ai.experiment



====================================================================

29\. ai.dataset

====================================================================



Columns:



&#x20;   id

&#x20;   code

&#x20;   name

&#x20;   description

&#x20;   dataset\_type

&#x20;   created\_at

&#x20;   updated\_at



====================================================================

30\. ai.dataset\_version

====================================================================



Columns:



&#x20;   id

&#x20;   dataset\_id

&#x20;   version

&#x20;   source\_hash

&#x20;   feature\_set\_version

&#x20;   row\_count

&#x20;   created\_at



Constraint:



&#x20;   dataset\_id + version UNIQUE



====================================================================

31\. ai.model

====================================================================



Purpose:



&#x20;   Logical model identity.



Columns:



&#x20;   id

&#x20;   code

&#x20;   name

&#x20;   model\_type

&#x20;   description

&#x20;   created\_at

&#x20;   updated\_at



====================================================================

32\. ai.model\_version

====================================================================



Purpose:



&#x20;   Immutable model version.



Columns:



&#x20;   id

&#x20;   model\_id

&#x20;   version

&#x20;   framework

&#x20;   artifact\_uri

&#x20;   checksum

&#x20;   feature\_version

&#x20;   training\_run\_id

&#x20;   status

&#x20;   created\_at



Statuses:



&#x20;   TRAINING

&#x20;   VALIDATED

&#x20;   ACTIVE

&#x20;   RETIRED

&#x20;   FAILED



====================================================================

33\. ai.training\_run

====================================================================



Columns:



&#x20;   id

&#x20;   dataset\_version\_id

&#x20;   model\_id

&#x20;   started\_at

&#x20;   completed\_at

&#x20;   hyperparameters\_json

&#x20;   metrics\_json

&#x20;   status

&#x20;   error\_message

&#x20;   created\_at



====================================================================

34\. ai.prediction

====================================================================



Purpose:



&#x20;   Store model inference.



Columns:



&#x20;   id

&#x20;   model\_version\_id

&#x20;   instrument\_id

&#x20;   timeframe\_id

&#x20;   timestamp

&#x20;   prediction\_type

&#x20;   predicted\_value

&#x20;   confidence

&#x20;   horizon

&#x20;   input\_snapshot\_hash

&#x20;   created\_at



Prediction MUST be traceable to:



&#x20;   model version

&#x20;   feature/data version

&#x20;   timestamp



====================================================================

35\. ai.experiment

====================================================================



Columns:



&#x20;   id

&#x20;   name

&#x20;   experiment\_type

&#x20;   description

&#x20;   configuration\_json

&#x20;   started\_at

&#x20;   completed\_at

&#x20;   status

&#x20;   created\_at



====================================================================

36\. STRATEGY SCHEMA

====================================================================



Purpose:



&#x20;   Strategy definitions and executions.



Tables:



&#x20;   strategy.strategy



&#x20;   strategy.version



&#x20;   strategy.run



&#x20;   strategy.signal



====================================================================

37\. strategy.strategy

====================================================================



Columns:



&#x20;   id

&#x20;   code

&#x20;   name

&#x20;   description

&#x20;   strategy\_type

&#x20;   is\_active

&#x20;   created\_at

&#x20;   updated\_at



Constraint:



&#x20;   code UNIQUE



====================================================================

38\. strategy.version

====================================================================



Columns:



&#x20;   id

&#x20;   strategy\_id

&#x20;   version

&#x20;   configuration\_json

&#x20;   source\_hash

&#x20;   created\_at



Constraint:



&#x20;   strategy\_id + version UNIQUE



====================================================================

39\. strategy.run

====================================================================



Purpose:



&#x20;   Track a strategy execution.



Columns:



&#x20;   id

&#x20;   strategy\_version\_id

&#x20;   execution\_mode

&#x20;   started\_at

&#x20;   completed\_at

&#x20;   status

&#x20;   configuration\_json

&#x20;   created\_at



Modes:



&#x20;   SIMULATION

&#x20;   PAPER

&#x20;   LIVE



====================================================================

40\. strategy.signal

====================================================================



Columns:



&#x20;   id

&#x20;   strategy\_run\_id

&#x20;   instrument\_id

&#x20;   timestamp

&#x20;   signal\_type

&#x20;   direction

&#x20;   strength

&#x20;   confidence

&#x20;   price\_reference

&#x20;   reason

&#x20;   metadata\_json

&#x20;   created\_at



Signal types may include:



&#x20;   ENTRY

&#x20;   EXIT

&#x20;   HOLD

&#x20;   REDUCE

&#x20;   INCREASE



====================================================================

41\. RISK SCHEMA

====================================================================



Purpose:



&#x20;   Risk evaluations and risk decisions.



Tables:



&#x20;   risk.profile



&#x20;   risk.rule



&#x20;   risk.evaluation



&#x20;   risk.decision



====================================================================

42\. risk.profile

====================================================================



Columns:



&#x20;   id

&#x20;   code

&#x20;   name

&#x20;   description

&#x20;   configuration\_json

&#x20;   is\_active

&#x20;   created\_at

&#x20;   updated\_at



====================================================================

43\. risk.rule

====================================================================



Columns:



&#x20;   id

&#x20;   profile\_id

&#x20;   code

&#x20;   name

&#x20;   rule\_type

&#x20;   configuration\_json

&#x20;   priority

&#x20;   is\_active

&#x20;   created\_at

&#x20;   updated\_at



====================================================================

44\. risk.evaluation

====================================================================



Columns:



&#x20;   id

&#x20;   signal\_id

&#x20;   profile\_id

&#x20;   evaluated\_at

&#x20;   risk\_score

&#x20;   exposure

&#x20;   max\_position\_size

&#x20;   status

&#x20;   explanation

&#x20;   metadata\_json

&#x20;   created\_at



Statuses:



&#x20;   APPROVED

&#x20;   REJECTED

&#x20;   MODIFIED

&#x20;   REVIEW



====================================================================

45\. risk.decision

====================================================================



Purpose:



&#x20;   Immutable record of the final risk decision.



Columns:



&#x20;   id

&#x20;   evaluation\_id

&#x20;   decision

&#x20;   reason

&#x20;   approved\_quantity

&#x20;   approved\_price

&#x20;   created\_at



====================================================================

46\. TRADING SCHEMA

====================================================================



Purpose:



&#x20;   Orders, executions and trades.



Tables:



&#x20;   trading.order



&#x20;   trading.order\_event



&#x20;   trading.execution



&#x20;   trading.trade



&#x20;   trading.trade\_leg



====================================================================

47\. trading.order

====================================================================



Columns:



&#x20;   id

&#x20;   account\_id

&#x20;   instrument\_id

&#x20;   strategy\_run\_id

&#x20;   signal\_id

&#x20;   risk\_decision\_id

&#x20;   client\_order\_id

&#x20;   provider\_order\_id

&#x20;   order\_type

&#x20;   side

&#x20;   quantity

&#x20;   price

&#x20;   stop\_price

&#x20;   time\_in\_force

&#x20;   execution\_mode

&#x20;   status

&#x20;   submitted\_at

&#x20;   created\_at

&#x20;   updated\_at



Order status lifecycle:



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



Constraint:



&#x20;   client\_order\_id UNIQUE within execution context.



====================================================================

48\. trading.order\_event

====================================================================



Purpose:



&#x20;   Immutable order lifecycle history.



Columns:



&#x20;   id

&#x20;   order\_id

&#x20;   event\_type

&#x20;   previous\_status

&#x20;   new\_status

&#x20;   event\_timestamp

&#x20;   payload\_json

&#x20;   created\_at



This table provides an audit trail.



====================================================================

49\. trading.execution

====================================================================



Purpose:



&#x20;   Actual fill/execution.



Columns:



&#x20;   id

&#x20;   order\_id

&#x20;   provider\_execution\_id

&#x20;   executed\_at

&#x20;   quantity

&#x20;   price

&#x20;   fee

&#x20;   fee\_currency\_id

&#x20;   liquidity\_type

&#x20;   metadata\_json

&#x20;   created\_at



Provider execution IDs should be unique per provider.



====================================================================

50\. trading.trade

====================================================================



Purpose:



&#x20;   Completed trading transaction / logical trade.



Columns:



&#x20;   id

&#x20;   account\_id

&#x20;   instrument\_id

&#x20;   strategy\_run\_id

&#x20;   opened\_at

&#x20;   closed\_at

&#x20;   entry\_price

&#x20;   exit\_price

&#x20;   quantity

&#x20;   realized\_pnl

&#x20;   fees

&#x20;   return\_pct

&#x20;   status

&#x20;   created\_at

&#x20;   updated\_at



Statuses:



&#x20;   OPEN

&#x20;   CLOSED

&#x20;   CANCELLED



====================================================================

51\. trading.trade\_leg

====================================================================



Purpose:



&#x20;   Link trade to executions.



Columns:



&#x20;   id

&#x20;   trade\_id

&#x20;   execution\_id

&#x20;   leg\_type

&#x20;   quantity

&#x20;   created\_at



Leg types:



&#x20;   ENTRY

&#x20;   EXIT

&#x20;   SCALE\_IN

&#x20;   SCALE\_OUT



====================================================================

52\. PORTFOLIO SCHEMA

====================================================================



Purpose:



&#x20;   Account and portfolio state.



Tables:



&#x20;   portfolio.account



&#x20;   portfolio.balance



&#x20;   portfolio.position



&#x20;   portfolio.portfolio



&#x20;   portfolio.snapshot



&#x20;   portfolio.pnl



====================================================================

53\. portfolio.account

====================================================================



Columns:



&#x20;   id

&#x20;   code

&#x20;   name

&#x20;   account\_type

&#x20;   base\_currency\_id

&#x20;   execution\_mode

&#x20;   initial\_balance

&#x20;   is\_active

&#x20;   created\_at

&#x20;   updated\_at



====================================================================

54\. portfolio.balance

====================================================================



Columns:



&#x20;   id

&#x20;   account\_id

&#x20;   currency\_id

&#x20;   available

&#x20;   reserved

&#x20;   total

&#x20;   updated\_at



Unique:



&#x20;   account\_id + currency\_id



====================================================================

55\. portfolio.portfolio

====================================================================



Columns:



&#x20;   id

&#x20;   account\_id

&#x20;   name

&#x20;   description

&#x20;   is\_active

&#x20;   created\_at

&#x20;   updated\_at



====================================================================

56\. portfolio.position

====================================================================



Columns:



&#x20;   id

&#x20;   account\_id

&#x20;   portfolio\_id

&#x20;   instrument\_id

&#x20;   side

&#x20;   quantity

&#x20;   average\_entry\_price

&#x20;   realized\_pnl

&#x20;   unrealized\_pnl

&#x20;   exposure

&#x20;   opened\_at

&#x20;   updated\_at



Unique logical position:



&#x20;   account + portfolio + instrument + side



====================================================================

57\. portfolio.snapshot

====================================================================



Purpose:



&#x20;   Historical portfolio state.



Columns:



&#x20;   id

&#x20;   account\_id

&#x20;   portfolio\_id

&#x20;   timestamp

&#x20;   equity

&#x20;   balance

&#x20;   exposure

&#x20;   unrealized\_pnl

&#x20;   realized\_pnl

&#x20;   drawdown

&#x20;   created\_at



Unique:



&#x20;   portfolio\_id + timestamp



====================================================================

58\. portfolio.pnl

====================================================================



Columns:



&#x20;   id

&#x20;   account\_id

&#x20;   portfolio\_id

&#x20;   period\_start

&#x20;   period\_end

&#x20;   realized\_pnl

&#x20;   unrealized\_pnl

&#x20;   fees

&#x20;   net\_pnl

&#x20;   return\_pct

&#x20;   created\_at



====================================================================

59\. SIMULATION SCHEMA

====================================================================



Purpose:



&#x20;   Deterministic trading simulation.



Tables:



&#x20;   simulation.run



&#x20;   simulation.configuration



&#x20;   simulation.fill



&#x20;   simulation.event



====================================================================

60\. simulation.run

====================================================================



Columns:



&#x20;   id

&#x20;   name

&#x20;   strategy\_run\_id

&#x20;   start\_time

&#x20;   end\_time

&#x20;   initial\_capital

&#x20;   final\_equity

&#x20;   status

&#x20;   started\_at

&#x20;   completed\_at

&#x20;   created\_at



====================================================================

61\. simulation.configuration

====================================================================



Columns:



&#x20;   id

&#x20;   simulation\_run\_id

&#x20;   slippage\_model

&#x20;   fee\_model

&#x20;   latency\_model

&#x20;   initial\_capital

&#x20;   configuration\_json

&#x20;   created\_at



====================================================================

62\. simulation.fill

====================================================================



Columns:



&#x20;   id

&#x20;   simulation\_run\_id

&#x20;   order\_id

&#x20;   timestamp

&#x20;   quantity

&#x20;   price

&#x20;   fee

&#x20;   created\_at



====================================================================

63\. simulation.event

====================================================================



Columns:



&#x20;   id

&#x20;   simulation\_run\_id

&#x20;   timestamp

&#x20;   event\_type

&#x20;   payload\_json

&#x20;   created\_at



====================================================================

64\. BACKTEST SCHEMA

====================================================================



Purpose:



&#x20;   Historical strategy evaluation.



Tables:



&#x20;   backtest.run



&#x20;   backtest.metric



&#x20;   backtest.equity\_point



&#x20;   backtest.trade\_result



====================================================================

65\. backtest.run

====================================================================



Columns:



&#x20;   id

&#x20;   name

&#x20;   strategy\_version\_id

&#x20;   dataset\_version\_id

&#x20;   start\_time

&#x20;   end\_time

&#x20;   initial\_capital

&#x20;   execution\_configuration\_json

&#x20;   status

&#x20;   started\_at

&#x20;   completed\_at

&#x20;   created\_at



====================================================================

66\. backtest.metric

====================================================================



Columns:



&#x20;   id

&#x20;   backtest\_run\_id

&#x20;   metric\_name

&#x20;   metric\_value

&#x20;   created\_at



Examples:



&#x20;   total\_return

&#x20;   CAGR

&#x20;   Sharpe

&#x20;   Sortino

&#x20;   max\_drawdown

&#x20;   win\_rate

&#x20;   profit\_factor

&#x20;   expectancy



====================================================================

67\. backtest.equity\_point

====================================================================



Columns:



&#x20;   id

&#x20;   backtest\_run\_id

&#x20;   timestamp

&#x20;   equity

&#x20;   cash

&#x20;   exposure

&#x20;   drawdown

&#x20;   created\_at



====================================================================

68\. backtest.trade\_result

====================================================================



Columns:



&#x20;   id

&#x20;   backtest\_run\_id

&#x20;   trade\_id

&#x20;   pnl

&#x20;   return\_pct

&#x20;   duration\_seconds

&#x20;   created\_at



====================================================================

69\. OPTIMIZATION SCHEMA

====================================================================



Purpose:



&#x20;   Parameter and model optimization.



Tables:



&#x20;   optimization.run



&#x20;   optimization.parameter



&#x20;   optimization.trial



&#x20;   optimization.result



====================================================================

70\. optimization.run

====================================================================



Columns:



&#x20;   id

&#x20;   name

&#x20;   optimization\_type

&#x20;   target\_metric

&#x20;   configuration\_json

&#x20;   started\_at

&#x20;   completed\_at

&#x20;   status

&#x20;   created\_at



====================================================================

71\. optimization.parameter

====================================================================



Columns:



&#x20;   id

&#x20;   optimization\_run\_id

&#x20;   name

&#x20;   parameter\_type

&#x20;   search\_space\_json

&#x20;   created\_at



====================================================================

72\. optimization.trial

====================================================================



Columns:



&#x20;   id

&#x20;   optimization\_run\_id

&#x20;   trial\_number

&#x20;   parameters\_json

&#x20;   started\_at

&#x20;   completed\_at

&#x20;   status

&#x20;   created\_at



Unique:



&#x20;   optimization\_run\_id + trial\_number



====================================================================

73\. optimization.result

====================================================================



Columns:



&#x20;   id

&#x20;   trial\_id

&#x20;   metric\_name

&#x20;   metric\_value

&#x20;   rank

&#x20;   created\_at



====================================================================

74\. LEARNING SCHEMA

====================================================================



Purpose:



&#x20;   Self-learning and feedback.



Tables:



&#x20;   learning.session



&#x20;   learning.feedback



&#x20;   learning.adaptation



====================================================================

75\. learning.session

====================================================================



Columns:



&#x20;   id

&#x20;   name

&#x20;   learning\_type

&#x20;   started\_at

&#x20;   completed\_at

&#x20;   status

&#x20;   configuration\_json

&#x20;   created\_at



====================================================================

76\. learning.feedback

====================================================================



Columns:



&#x20;   id

&#x20;   learning\_session\_id

&#x20;   source\_type

&#x20;   source\_id

&#x20;   feedback\_type

&#x20;   score

&#x20;   payload\_json

&#x20;   created\_at



====================================================================

77\. learning.adaptation

====================================================================



Columns:



&#x20;   id

&#x20;   learning\_session\_id

&#x20;   target\_type

&#x20;   target\_id

&#x20;   previous\_configuration\_json

&#x20;   new\_configuration\_json

&#x20;   reason

&#x20;   created\_at



All learning changes must be auditable.



====================================================================

78\. NEWS SCHEMA

====================================================================



Purpose:



&#x20;   News and external information.



Tables:



&#x20;   news.source



&#x20;   news.article



&#x20;   news.sentiment



&#x20;   news.market\_event



====================================================================

79\. news.source

====================================================================



Columns:



&#x20;   id

&#x20;   code

&#x20;   name

&#x20;   source\_type

&#x20;   base\_url

&#x20;   is\_active

&#x20;   created\_at

&#x20;   updated\_at



====================================================================

80\. news.article

====================================================================



Columns:



&#x20;   id

&#x20;   source\_id

&#x20;   external\_id

&#x20;   published\_at

&#x20;   title

&#x20;   summary

&#x20;   content\_reference

&#x20;   language

&#x20;   url\_reference

&#x20;   checksum

&#x20;   created\_at



Unique:



&#x20;   source\_id + external\_id



====================================================================

81\. news.sentiment

====================================================================



Columns:



&#x20;   id

&#x20;   article\_id

&#x20;   model\_version\_id

&#x20;   sentiment

&#x20;   score

&#x20;   confidence

&#x20;   created\_at



====================================================================

82\. news.market\_event

====================================================================



Columns:



&#x20;   id

&#x20;   article\_id

&#x20;   instrument\_id

&#x20;   event\_type

&#x20;   event\_time

&#x20;   impact\_score

&#x20;   metadata\_json

&#x20;   created\_at



====================================================================

83\. SYSTEM SCHEMA

====================================================================



Purpose:



&#x20;   System-level configuration and runtime state.



Tables:



&#x20;   system.configuration



&#x20;   system.configuration\_version



&#x20;   system.job



&#x20;   system.job\_execution



&#x20;   system.system\_event



====================================================================

84\. system.configuration

====================================================================



Columns:



&#x20;   id

&#x20;   key

&#x20;   value

&#x20;   value\_type

&#x20;   environment

&#x20;   is\_secret\_reference

&#x20;   is\_active

&#x20;   created\_at

&#x20;   updated\_at



Secrets MUST NOT be stored as plaintext.



====================================================================

85\. system.configuration\_version

====================================================================



Columns:



&#x20;   id

&#x20;   configuration\_id

&#x20;   version

&#x20;   value

&#x20;   changed\_by

&#x20;   changed\_at



====================================================================

86\. system.job

====================================================================



Columns:



&#x20;   id

&#x20;   code

&#x20;   name

&#x20;   job\_type

&#x20;   schedule

&#x20;   is\_active

&#x20;   created\_at

&#x20;   updated\_at



====================================================================

87\. system.job\_execution

====================================================================



Columns:



&#x20;   id

&#x20;   job\_id

&#x20;   started\_at

&#x20;   completed\_at

&#x20;   status

&#x20;   error\_message

&#x20;   metadata\_json

&#x20;   created\_at



====================================================================

88\. system.system\_event

====================================================================



Purpose:



&#x20;   General system event persistence.



Columns:



&#x20;   id

&#x20;   event\_type

&#x20;   aggregate\_type

&#x20;   aggregate\_id

&#x20;   occurred\_at

&#x20;   payload\_json

&#x20;   correlation\_id

&#x20;   causation\_id

&#x20;   created\_at



====================================================================

89\. AUDIT SCHEMA

====================================================================



Purpose:



&#x20;   Immutable audit history.



Tables:



&#x20;   audit.audit\_log



&#x20;   audit.security\_event



====================================================================

90\. audit.audit\_log

====================================================================



Columns:



&#x20;   id

&#x20;   timestamp

&#x20;   actor\_type

&#x20;   actor\_id

&#x20;   action

&#x20;   entity\_type

&#x20;   entity\_id

&#x20;   before\_json

&#x20;   after\_json

&#x20;   correlation\_id

&#x20;   source

&#x20;   created\_at



Audit records should be append-only.



====================================================================

91\. audit.security\_event

====================================================================



Columns:



&#x20;   id

&#x20;   timestamp

&#x20;   event\_type

&#x20;   severity

&#x20;   actor\_id

&#x20;   source

&#x20;   metadata\_json

&#x20;   created\_at



====================================================================

92\. PROJECT SCHEMA

====================================================================



Purpose:



&#x20;   Persistent Project Intelligence state.



Tables:



&#x20;   project.snapshot



&#x20;   project.file



&#x20;   project.dependency



&#x20;   project.decision



&#x20;   project.roadmap\_item



&#x20;   project.todo



&#x20;   project.analysis\_run



====================================================================

93\. project.snapshot

====================================================================



Columns:



&#x20;   id

&#x20;   snapshot\_hash

&#x20;   project\_name

&#x20;   project\_version

&#x20;   git\_commit

&#x20;   branch

&#x20;   generated\_at

&#x20;   source\_file\_count

&#x20;   test\_count

&#x20;   metadata\_json

&#x20;   created\_at



====================================================================

94\. project.file

====================================================================



Columns:



&#x20;   id

&#x20;   snapshot\_id

&#x20;   path

&#x20;   file\_type

&#x20;   language

&#x20;   size\_bytes

&#x20;   content\_hash

&#x20;   modified\_at

&#x20;   created\_at



Unique:



&#x20;   snapshot\_id + path



====================================================================

95\. project.dependency

====================================================================



Columns:



&#x20;   id

&#x20;   snapshot\_id

&#x20;   source\_path

&#x20;   target\_path

&#x20;   dependency\_type

&#x20;   created\_at



====================================================================

96\. project.decision

====================================================================



Columns:



&#x20;   id

&#x20;   decision\_key

&#x20;   title

&#x20;   description

&#x20;   rationale

&#x20;   status

&#x20;   decided\_at

&#x20;   source

&#x20;   created\_at

&#x20;   updated\_at



====================================================================

97\. project.roadmap\_item

====================================================================



Columns:



&#x20;   id

&#x20;   phase

&#x20;   code

&#x20;   title

&#x20;   description

&#x20;   status

&#x20;   priority

&#x20;   dependency\_json

&#x20;   created\_at

&#x20;   updated\_at



Statuses:



&#x20;   PLANNED

&#x20;   IN\_PROGRESS

&#x20;   BLOCKED

&#x20;   COMPLETED

&#x20;   CANCELLED



====================================================================

98\. project.todo

====================================================================



Columns:



&#x20;   id

&#x20;   snapshot\_id

&#x20;   path

&#x20;   line\_number

&#x20;   todo\_type

&#x20;   text

&#x20;   status

&#x20;   created\_at



====================================================================

99\. project.analysis\_run

====================================================================



Columns:



&#x20;   id

&#x20;   started\_at

&#x20;   completed\_at

&#x20;   status

&#x20;   git\_commit

&#x20;   files\_scanned

&#x20;   errors

&#x20;   result\_hash

&#x20;   created\_at



====================================================================

100\. RELATIONSHIP OVERVIEW

====================================================================



Core relationship flow:



&#x20;   ref.currency

&#x20;       ↓

&#x20;   ref.exchange

&#x20;       ↓

&#x20;   market.instrument

&#x20;       ↓

&#x20;   market.candle

&#x20;       ↓

&#x20;   feature.value

&#x20;       ↓

&#x20;   ai.prediction

&#x20;       ↓

&#x20;   strategy.signal

&#x20;       ↓

&#x20;   risk.evaluation

&#x20;       ↓

&#x20;   risk.decision

&#x20;       ↓

&#x20;   trading.order

&#x20;       ↓

&#x20;   trading.execution

&#x20;       ↓

&#x20;   trading.trade

&#x20;       ↓

&#x20;   portfolio.position

&#x20;       ↓

&#x20;   portfolio.snapshot



====================================================================

101\. MARKET → FEATURE

====================================================================



&#x20;   market.instrument

&#x20;       |

&#x20;       +---- market.candle

&#x20;       |

&#x20;       +---- market.tick

&#x20;                   |

&#x20;                   ↓

&#x20;           feature.value



Features reference:



&#x20;   instrument

&#x20;   timeframe

&#x20;   timestamp

&#x20;   feature version



====================================================================

102\. FEATURE → AI

====================================================================



&#x20;   feature.version

&#x20;           ↓

&#x20;   ai.dataset\_version

&#x20;           ↓

&#x20;   ai.training\_run

&#x20;           ↓

&#x20;   ai.model\_version

&#x20;           ↓

&#x20;   ai.prediction



All predictions must be reproducible.



====================================================================

103\. STRATEGY → RISK

====================================================================



&#x20;   strategy.strategy

&#x20;           ↓

&#x20;   strategy.version

&#x20;           ↓

&#x20;   strategy.run

&#x20;           ↓

&#x20;   strategy.signal

&#x20;           ↓

&#x20;   risk.evaluation

&#x20;           ↓

&#x20;   risk.decision



====================================================================

104\. RISK → TRADING

====================================================================



&#x20;   risk.decision

&#x20;           ↓

&#x20;   trading.order

&#x20;           ↓

&#x20;   trading.order\_event

&#x20;           ↓

&#x20;   trading.execution

&#x20;           ↓

&#x20;   trading.trade



No direct:



&#x20;   signal → execution



relationship is permitted.



====================================================================

105\. TRADING → PORTFOLIO

====================================================================



&#x20;   trading.execution

&#x20;           ↓

&#x20;   trading.trade

&#x20;           ↓

&#x20;   portfolio.position

&#x20;           ↓

&#x20;   portfolio.snapshot



Balances are updated transactionally.



====================================================================

106\. BACKTEST RELATIONSHIP

====================================================================



&#x20;   ai.dataset\_version

&#x20;           ↓

&#x20;   backtest.run

&#x20;           ↑

&#x20;   strategy.version

&#x20;           |

&#x20;           ↓

&#x20;   simulation.run

&#x20;           ↓

&#x20;   backtest.metric

&#x20;           ↓

&#x20;   backtest.equity\_point

&#x20;           ↓

&#x20;   backtest.trade\_result



====================================================================

107\. EVENT STORAGE

====================================================================



Important business events may be persisted.



Examples:



&#x20;   MarketDataReceived

&#x20;   CandleClosed

&#x20;   PredictionGenerated

&#x20;   SignalGenerated

&#x20;   RiskEvaluated

&#x20;   OrderCreated

&#x20;   OrderSubmitted

&#x20;   OrderFilled

&#x20;   OrderCancelled

&#x20;   TradeOpened

&#x20;   TradeClosed

&#x20;   PositionChanged

&#x20;   PortfolioUpdated

&#x20;   BacktestCompleted



Events should include:



&#x20;   event\_id

&#x20;   event\_type

&#x20;   aggregate\_type

&#x20;   aggregate\_id

&#x20;   occurred\_at

&#x20;   correlation\_id

&#x20;   causation\_id

&#x20;   payload



====================================================================

108\. TRANSACTION BOUNDARIES

====================================================================



Transactions should follow Aggregate boundaries.



Example:



&#x20;   Order creation + initial order event



should be atomic.



Example:



&#x20;   Execution + position update + balance update



must be designed carefully so partial persistence cannot create

financially inconsistent state.



====================================================================

109\. IDEMPOTENCY

====================================================================



External execution operations must be idempotent.



Important identifiers:



&#x20;   client\_order\_id

&#x20;   provider\_order\_id

&#x20;   provider\_execution\_id

&#x20;   event\_id



Duplicate external messages MUST NOT create duplicate executions.



====================================================================

110\. INDEXING

====================================================================



High-volume tables MUST be indexed appropriately.



Critical indexes:



&#x20;   market.candle

&#x20;       instrument\_id

&#x20;       timeframe\_id

&#x20;       timestamp



&#x20;   market.tick

&#x20;       instrument\_id

&#x20;       timestamp



&#x20;   feature.value

&#x20;       instrument\_id

&#x20;       timeframe\_id

&#x20;       feature\_version\_id

&#x20;       timestamp



&#x20;   ai.prediction

&#x20;       instrument\_id

&#x20;       timeframe\_id

&#x20;       timestamp



&#x20;   trading.order

&#x20;       account\_id

&#x20;       status

&#x20;       created\_at



&#x20;   trading.execution

&#x20;       order\_id

&#x20;       executed\_at



&#x20;   portfolio.snapshot

&#x20;       portfolio\_id

&#x20;       timestamp



&#x20;   backtest.equity\_point

&#x20;       backtest\_run\_id

&#x20;       timestamp



====================================================================

111\. TIME-SERIES INDEXING

====================================================================



For market data:



&#x20;   Primary access pattern:



&#x20;       instrument

&#x20;       +

&#x20;       timeframe

&#x20;       +

&#x20;       timestamp



Composite indexes should reflect this.



Do not create random single-column indexes on every column.



====================================================================

112\. PARTITIONING

====================================================================



Potentially very large tables:



&#x20;   market.candle

&#x20;   market.tick

&#x20;   feature.value

&#x20;   ai.prediction

&#x20;   trading.order\_event

&#x20;   system.system\_event



may eventually require partitioning.



Partitioning strategy should be based on:



&#x20;   timestamp



and possibly:



&#x20;   instrument



depending on scale.



Do not prematurely partition the database before measuring volume.



====================================================================

113\. JSON USAGE

====================================================================



JSON may be used for:



&#x20;   configuration

&#x20;   provider-specific metadata

&#x20;   experiment parameters

&#x20;   model metadata

&#x20;   event payloads



JSON MUST NOT replace relational structure for core queryable data.



Bad:



&#x20;   entire order stored as JSON



Good:



&#x20;   order columns relationally

&#x20;   provider-specific metadata in JSON



====================================================================

114\. FOREIGN KEY POLICY

====================================================================



Foreign keys must be used for persistent relational integrity.



Exceptions require explicit justification.



Do not rely solely on application code for referential integrity

where SQL constraints can safely enforce it.



====================================================================

115\. DELETE POLICY

====================================================================



Financial records should generally NOT be hard-deleted.



Prefer:



&#x20;   immutable records

&#x20;   status transitions

&#x20;   soft deletion

&#x20;   archival



Examples:



&#x20;   orders

&#x20;   executions

&#x20;   trades

&#x20;   audit logs

&#x20;   risk decisions



must remain historically traceable.



====================================================================

116\. MARKET DATA DELETE POLICY

====================================================================



Market data may be deleted/rebuilt when:



&#x20;   source data is invalid

&#x20;   dataset version is replaced

&#x20;   retention policy requires deletion



But deletion must be controlled and auditable.



====================================================================

117\. MIGRATION POLICY

====================================================================



Database changes MUST use migrations.



Never manually modify production schema without a migration.



Every migration must be:



&#x20;   versioned

&#x20;   deterministic

&#x20;   reviewable

&#x20;   reversible where practical



====================================================================

118\. SEED DATA

====================================================================



Reference data may be seeded.



Examples:



&#x20;   currencies

&#x20;   timeframes

&#x20;   market types

&#x20;   instrument types



Seed operations MUST be idempotent.



====================================================================

119\. REPOSITORY BOUNDARY

====================================================================



Domain must not know SQL Server.



Application uses repository interfaces.



Infrastructure implements:



&#x20;   SQL repositories

&#x20;   database session

&#x20;   UnitOfWork

&#x20;   transaction management



Example:



&#x20;   Domain:

&#x20;       Candle



&#x20;   Application:

&#x20;       CandleRepository protocol/interface



&#x20;   Infrastructure:

&#x20;       SqlServerCandleRepository



====================================================================

120\. UNIT OF WORK

====================================================================



A UnitOfWork abstraction should coordinate transactional changes.



Example:



&#x20;   begin

&#x20;   execute domain operation

&#x20;   persist aggregate

&#x20;   persist events

&#x20;   commit



On failure:



&#x20;   rollback



====================================================================

121\. CONNECTION MANAGEMENT

====================================================================



Database connections must be managed by Infrastructure.



Do NOT:



&#x20;   create a DB connection inside Domain objects.



Connection configuration comes from:



&#x20;   Configuration System



Credentials come from:



&#x20;   secure environment / secret provider



====================================================================

122\. DATABASE SECURITY

====================================================================



Required:



&#x20;   least privilege

&#x20;   separate application credentials

&#x20;   encrypted connections

&#x20;   no credentials in Git

&#x20;   no credentials in source code

&#x20;   audit logging

&#x20;   controlled migrations



====================================================================

123\. LIVE TRADING DATABASE SAFETY

====================================================================



Live trading requires additional protections.



Production database must not be accidentally used by:



&#x20;   unit tests

&#x20;   simulations

&#x20;   development runs

&#x20;   backtests



Environment separation is mandatory.



Recommended:



&#x20;   development database

&#x20;   test database

&#x20;   simulation database

&#x20;   paper database

&#x20;   production database



====================================================================

124\. TEST DATABASE

====================================================================



Tests must use:



&#x20;   isolated database



or:



&#x20;   deterministic test database schema



Tests must never destroy production data.



====================================================================

125\. BACKTEST DATA ISOLATION

====================================================================



Backtest data must be versioned.



A backtest must be reproducible from:



&#x20;   strategy version

&#x20;   dataset version

&#x20;   feature version

&#x20;   model version

&#x20;   configuration

&#x20;   execution model



====================================================================

126\. AUDITABILITY

====================================================================



Every important financial operation must be traceable.



Example:



&#x20;   Signal

&#x20;      ↓

&#x20;   Risk Evaluation

&#x20;      ↓

&#x20;   Risk Decision

&#x20;      ↓

&#x20;   Order

&#x20;      ↓

&#x20;   Execution

&#x20;      ↓

&#x20;   Trade

&#x20;      ↓

&#x20;   Position

&#x20;      ↓

&#x20;   Portfolio Snapshot



The database must preserve enough relationships to reconstruct

this chain.



====================================================================

127\. CORRELATION IDS

====================================================================



Distributed/application operations should carry:



&#x20;   correlation\_id



Example:



&#x20;   strategy run

&#x20;       ↓

&#x20;   signal

&#x20;       ↓

&#x20;   risk

&#x20;       ↓

&#x20;   order

&#x20;       ↓

&#x20;   execution



All should be traceable to the same correlation context.



====================================================================

128\. CAUSATION IDS

====================================================================



Events should support:



&#x20;   causation\_id



Example:



&#x20;   OrderFilled event



may reference:



&#x20;   OrderSubmitted event



This enables event lineage.



====================================================================

129\. IMMUTABLE DATA

====================================================================



The following should be treated as immutable after creation:



&#x20;   executions

&#x20;   audit logs

&#x20;   risk decisions

&#x20;   model versions

&#x20;   dataset versions

&#x20;   strategy versions

&#x20;   feature versions

&#x20;   important events



Corrections should create new records or explicit correction events.



====================================================================

130\. VERSIONING

====================================================================



Versioned artifacts:



&#x20;   datasets

&#x20;   models

&#x20;   strategies

&#x20;   features

&#x20;   configurations



must never silently mutate historical versions.



====================================================================

131\. DATA LINEAGE

====================================================================



AI predictions should be traceable to:



&#x20;   market data

&#x20;   feature version

&#x20;   dataset version

&#x20;   model version

&#x20;   model training run



Backtests should be traceable to:



&#x20;   dataset

&#x20;   strategy

&#x20;   model

&#x20;   configuration

&#x20;   execution model



====================================================================

132\. DATABASE HEALTH

====================================================================



The system should monitor:



&#x20;   connection failures

&#x20;   slow queries

&#x20;   deadlocks

&#x20;   transaction failures

&#x20;   migration status

&#x20;   table growth

&#x20;   index health

&#x20;   storage usage



====================================================================

133\. BACKUP

====================================================================



Production database must support:



&#x20;   full backups

&#x20;   differential backups

&#x20;   transaction log backups



Recovery objectives must be defined before production deployment.



====================================================================

134\. RETENTION

====================================================================



Retention policies should be defined separately for:



&#x20;   tick data

&#x20;   candles

&#x20;   features

&#x20;   predictions

&#x20;   events

&#x20;   logs

&#x20;   audit

&#x20;   project intelligence



Financial/audit records generally require longer retention.



====================================================================

135\. DATABASE PERFORMANCE

====================================================================



Do not optimize prematurely.



First establish:



&#x20;   correct schema

&#x20;   correct constraints

&#x20;   correct indexes



Then measure:



&#x20;   query latency

&#x20;   throughput

&#x20;   storage growth



Then optimize.



====================================================================

136\. ORM POLICY

====================================================================



ORM may be used in Infrastructure.



ORM models MUST NOT become Domain models.



Domain entities remain independent.



Example:



&#x20;   SqlOrderModel

&#x20;       ≠

&#x20;   Domain Order



Mapping is explicit.



====================================================================

137\. DATABASE MODEL MAPPING

====================================================================



Recommended flow:



&#x20;   SQL Row

&#x20;       ↓

&#x20;   Infrastructure ORM/Data Model

&#x20;       ↓

&#x20;   Mapper

&#x20;       ↓

&#x20;   Domain Entity

&#x20;       ↓

&#x20;   Application



Reverse:



&#x20;   Domain Entity

&#x20;       ↓

&#x20;   Mapper

&#x20;       ↓

&#x20;   Persistence Model

&#x20;       ↓

&#x20;   SQL



====================================================================

138\. DATABASE ERROR POLICY

====================================================================



Infrastructure errors must be translated into application-level

errors.



Do not expose:



&#x20;   SQLAlchemy exceptions

&#x20;   pyodbc exceptions

&#x20;   SQL Server error codes



directly to Domain.



====================================================================

139\. SCHEMA OWNERSHIP

====================================================================



Ownership:



&#x20;   ref:

&#x20;       Reference Data



&#x20;   market:

&#x20;       Market Data



&#x20;   feature:

&#x20;       Feature Platform



&#x20;   ai:

&#x20;       AI Platform



&#x20;   strategy:

&#x20;       Strategy Platform



&#x20;   risk:

&#x20;       Risk Platform



&#x20;   trading:

&#x20;       Trading Platform



&#x20;   portfolio:

&#x20;       Portfolio Platform



&#x20;   simulation:

&#x20;       Simulation Platform



&#x20;   backtest:

&#x20;       Backtesting



&#x20;   optimization:

&#x20;       Optimization



&#x20;   learning:

&#x20;       Self Learning



&#x20;   news:

&#x20;       News Platform



&#x20;   system:

&#x20;       Runtime / Configuration



&#x20;   audit:

&#x20;       Audit



&#x20;   project:

&#x20;       Project Intelligence



====================================================================

140\. DATABASE BUILD ORDER

====================================================================



Recommended implementation order:



&#x20;   1.

&#x20;   Create database



&#x20;   2.

&#x20;   Create schemas



&#x20;   3.

&#x20;   Create reference tables



&#x20;   4.

&#x20;   Seed reference data



&#x20;   5.

&#x20;   Create market tables



&#x20;   6.

&#x20;   Create feature tables



&#x20;   7.

&#x20;   Create AI tables



&#x20;   8.

&#x20;   Create strategy tables



&#x20;   9.

&#x20;   Create risk tables



&#x20;   10.

&#x20;   Create trading tables



&#x20;   11.

&#x20;   Create portfolio tables



&#x20;   12.

&#x20;   Create simulation tables



&#x20;   13.

&#x20;   Create backtest tables



&#x20;   14.

&#x20;   Create optimization tables



&#x20;   15.

&#x20;   Create learning tables



&#x20;   16.

&#x20;   Create news tables



&#x20;   17.

&#x20;   Create system tables



&#x20;   18.

&#x20;   Create audit tables



&#x20;   19.

&#x20;   Create project intelligence tables



&#x20;   20.

&#x20;   Add foreign keys



&#x20;   21.

&#x20;   Add indexes



&#x20;   22.

&#x20;   Add constraints



&#x20;   23.

&#x20;   Add seed data



&#x20;   24.

&#x20;   Add migration tests



====================================================================

141\. IMPLEMENTATION REQUIREMENT

====================================================================



The coding agent MUST:



&#x20;   inspect current project structure



&#x20;   inspect existing database code



&#x20;   inspect configuration



&#x20;   inspect dependency files



&#x20;   inspect migration tooling



&#x20;   inspect existing Domain models



&#x20;   inspect repository contracts



before implementing this schema.



Do NOT overwrite existing implementation blindly.



====================================================================

142\. MIGRATION TOOL

====================================================================



The final implementation should use a proper migration framework.



Recommended:



&#x20;   Alembic



if SQLAlchemy is selected.



Alternative migration tooling requires explicit architectural

approval.



====================================================================

143\. SQL SERVER TARGET

====================================================================



The target production relational database is:



&#x20;   Microsoft SQL Server



The database layer should support:



&#x20;   SQL Server transactions

&#x20;   indexes

&#x20;   foreign keys

&#x20;   constraints

&#x20;   DATETIME2

&#x20;   DECIMAL

&#x20;   UNIQUEIDENTIFIER

&#x20;   ROWVERSION

&#x20;   JSON support



====================================================================

144\. DATABASE CONFIGURATION

====================================================================



Database configuration should include:



&#x20;   host

&#x20;   port

&#x20;   database

&#x20;   username

&#x20;   password / secret reference

&#x20;   driver

&#x20;   pool size

&#x20;   max overflow

&#x20;   timeout

&#x20;   encryption settings



Secrets must be externalized.



====================================================================

145\. DATABASE ENVIRONMENTS

====================================================================



Required conceptual environments:



&#x20;   development

&#x20;   testing

&#x20;   simulation

&#x20;   paper

&#x20;   production



Each environment must have separate credentials and database

configuration.



====================================================================

146\. DATABASE TESTING

====================================================================



Tests must validate:



&#x20;   schema creation

&#x20;   migrations

&#x20;   foreign keys

&#x20;   unique constraints

&#x20;   transaction rollback

&#x20;   repository behavior

&#x20;   concurrency

&#x20;   idempotency

&#x20;   financial precision

&#x20;   order lifecycle

&#x20;   execution persistence

&#x20;   portfolio consistency

&#x20;   audit integrity



====================================================================

147\. CRITICAL DATABASE INVARIANTS

====================================================================



The following must always hold:



&#x20;   1.

&#x20;   An execution references a valid order.



&#x20;   2.

&#x20;   An order references a valid account.



&#x20;   3.

&#x20;   An order references a valid instrument.



&#x20;   4.

&#x20;   A risk decision must exist before a live order is executable.



&#x20;   5.

&#x20;   An execution cannot exceed the authorized order quantity unless

&#x20;   explicitly supported by the execution model.



&#x20;   6.

&#x20;   Duplicate provider executions must not create duplicate records.



&#x20;   7.

&#x20;   A position cannot reference a non-existent account.



&#x20;   8.

&#x20;   Portfolio snapshots must have valid timestamps.



&#x20;   9.

&#x20;   Financial values must use decimal precision.



&#x20;   10.

&#x20;   Historical model versions cannot silently change.



&#x20;   11.

&#x20;   Historical strategy versions cannot silently change.



&#x20;   12.

&#x20;   Historical dataset versions cannot silently change.



====================================================================

148\. FINANCIAL CONSISTENCY

====================================================================



The database must support reconciliation between:



&#x20;   Orders

&#x20;   Executions

&#x20;   Trades

&#x20;   Positions

&#x20;   Balances

&#x20;   Portfolio

&#x20;   PnL



Any mismatch must be detectable.



====================================================================

149\. RECONCILIATION

====================================================================



A reconciliation process should eventually compare:



&#x20;   internal orders

&#x20;       vs

&#x20;   broker orders



&#x20;   internal executions

&#x20;       vs

&#x20;   broker executions



&#x20;   internal positions

&#x20;       vs

&#x20;   broker positions



&#x20;   internal balances

&#x20;       vs

&#x20;   broker balances



Discrepancies must generate audit events.



====================================================================

150\. DISASTER RECOVERY

====================================================================



Production database design must support:



&#x20;   backup

&#x20;   restore

&#x20;   point-in-time recovery

&#x20;   migration replay

&#x20;   disaster recovery testing



====================================================================

151\. DATABASE DOCUMENTATION

====================================================================



Database implementation must document:



&#x20;   schema

&#x20;   table

&#x20;   columns

&#x20;   relationships

&#x20;   indexes

&#x20;   constraints

&#x20;   migrations

&#x20;   seed data

&#x20;   retention

&#x20;   backup

&#x20;   recovery



====================================================================

152\. DATABASE CHANGE CONTROL

====================================================================



Any schema change must include:



&#x20;   migration

&#x20;   tests

&#x20;   documentation update

&#x20;   impact analysis



Breaking changes require:



&#x20;   migration strategy

&#x20;   compatibility strategy

&#x20;   explicit decision



====================================================================

153\. DATABASE / DOMAIN SEPARATION

====================================================================



CRITICAL:



Database schema is NOT the Domain model.



A table may represent persistence requirements.



A Domain aggregate may span multiple tables.



A Domain entity may be persisted into multiple tables.



Do not force Domain design to match SQL table design.



====================================================================

154\. DATABASE / EVENT BUS SEPARATION

====================================================================



Event Bus is an application/runtime mechanism.



Database event persistence is an Infrastructure concern.



Do not use database polling as the default replacement for Event Bus.



====================================================================

155\. DATABASE / CACHE SEPARATION

====================================================================



Future caching may be introduced.



Cache is NOT source of truth.



Database remains persistent source of truth unless an explicit

architecture decision changes this.



====================================================================

156\. DATABASE / DATA LAKE SEPARATION

====================================================================



Large historical datasets may eventually require object storage

or data-lake architecture.



SQL Server remains responsible for transactional and queryable

operational state.



Do not force petabyte-scale market data into transactional tables

without evaluating storage architecture.



====================================================================

157\. FINAL DATABASE ARCHITECTURE

====================================================================



Logical architecture:



&#x20;   +---------------------------------------------------------+

&#x20;   |                    SHADBOTTRADER                        |

&#x20;   +---------------------------------------------------------+

&#x20;                             |

&#x20;                      Application Layer

&#x20;                             |

&#x20;                      Repository Contracts

&#x20;                             |

&#x20;                    Infrastructure Layer

&#x20;                             |

&#x20;                   +----------------------+

&#x20;                   |     SQL Server       |

&#x20;                   +----------------------+

&#x20;                             |

&#x20;       +----------+----------+----------+----------+

&#x20;       |          |          |          |          |

&#x20;      ref       market     feature      ai       strategy

&#x20;       |

&#x20;       +-----------------------------------------------+

&#x20;       |

&#x20;      risk

&#x20;       |

&#x20;      trading

&#x20;       |

&#x20;      portfolio

&#x20;       |

&#x20;      simulation

&#x20;       |

&#x20;      backtest

&#x20;       |

&#x20;      optimization

&#x20;       |

&#x20;      learning

&#x20;       |

&#x20;      news

&#x20;       |

&#x20;      system

&#x20;       |

&#x20;      audit

&#x20;       |

&#x20;      project



====================================================================

158\. IMPLEMENTATION PRIORITY

====================================================================



Priority 1:



&#x20;   Database infrastructure

&#x20;   Connection management

&#x20;   Migration framework

&#x20;   Base SQL configuration

&#x20;   UnitOfWork



Priority 2:



&#x20;   Reference tables

&#x20;   Market tables

&#x20;   Trading tables

&#x20;   Portfolio tables



Priority 3:



&#x20;   Feature tables

&#x20;   AI tables

&#x20;   Strategy tables

&#x20;   Risk tables



Priority 4:



&#x20;   Simulation

&#x20;   Backtest

&#x20;   Optimization

&#x20;   Learning



Priority 5:



&#x20;   News

&#x20;   System

&#x20;   Audit

&#x20;   Project Intelligence persistence



Priority 6:



&#x20;   Performance optimization

&#x20;   Partitioning

&#x20;   Archival

&#x20;   Advanced reconciliation



====================================================================

159\. ABSOLUTE RULES FOR CODING AGENT

====================================================================



The coding agent MUST NOT:



&#x20;   invent tables unrelated to the architecture



&#x20;   invent foreign-key relationships



&#x20;   duplicate Domain entities as arbitrary persistence classes



&#x20;   store money as FLOAT



&#x20;   store timestamps as local time



&#x20;   store credentials in database source files



&#x20;   hard-delete financial history



&#x20;   bypass migrations



&#x20;   bypass repository contracts



&#x20;   put SQL in Domain



&#x20;   let ORM models leak into Domain



&#x20;   allow tests to connect to production



&#x20;   allow simulation to execute live orders



&#x20;   silently change a table contract



&#x20;   silently rename columns



&#x20;   silently remove historical records



====================================================================

160\. COMPLETION CRITERIA

====================================================================



Database implementation is complete only when:



&#x20;   \[ ] All required schemas exist



&#x20;   \[ ] Required tables exist



&#x20;   \[ ] Foreign keys are defined



&#x20;   \[ ] Unique constraints are defined



&#x20;   \[ ] Check constraints are defined where required



&#x20;   \[ ] Indexes are implemented



&#x20;   \[ ] Migrations work from empty database



&#x20;   \[ ] Migrations work from previous version



&#x20;   \[ ] Seed data is idempotent



&#x20;   \[ ] Repository contracts are implemented



&#x20;   \[ ] UnitOfWork is implemented



&#x20;   \[ ] Transaction behavior is tested



&#x20;   \[ ] Rollback behavior is tested



&#x20;   \[ ] Idempotency is tested



&#x20;   \[ ] Financial precision is tested



&#x20;   \[ ] Order lifecycle persistence is tested



&#x20;   \[ ] Execution persistence is tested



&#x20;   \[ ] Portfolio consistency is tested



&#x20;   \[ ] Audit behavior is tested



&#x20;   \[ ] Test database isolation is verified



&#x20;   \[ ] Production credentials are externalized



&#x20;   \[ ] Documentation matches actual schema



&#x20;   \[ ] Ruff passes



&#x20;   \[ ] Black passes



&#x20;   \[ ] Mypy passes



&#x20;   \[ ] Pytest passes



====================================================================

161\. FINAL DATABASE PRINCIPLE

====================================================================



The database must be:



&#x20;   reliable

&#x20;   deterministic

&#x20;   auditable

&#x20;   transactional

&#x20;   secure

&#x20;   versioned

&#x20;   testable

&#x20;   scalable



The database must support the architecture.



The architecture must NOT be distorted merely to make the database

implementation easier.



====================================================================

END OF DATABASE\_SCHEMA\_SPECIFICATION

====================================================================

