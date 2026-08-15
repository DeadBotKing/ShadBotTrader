====================================================================

SHADBOTTRADER

MASTER IMPLEMENTATION SPECIFICATION

====================================================================



Document:

&#x20;   SHADBOTTRADER\_MASTER\_IMPLEMENTATION\_SPECIFICATION



Version:

&#x20;   1.0



Status:

&#x20;   MASTER IMPLEMENTATION CONTRACT



Purpose:

&#x20;   This document defines exactly how ShadBotTrader must be built

&#x20;   from zero to a complete production-grade trading application.



Audience:

&#x20;   Human Developer

&#x20;   Coding Agent

&#x20;   Autonomous Coding Agent

&#x20;   AI Software Engineer



IMPORTANT:

&#x20;   The developer must implement the system according to this

&#x20;   specification and must NOT redesign the architecture casually.



====================================================================

1\. PROJECT IDENTITY

====================================================================



Project Name:



&#x20;   ShadBotTrader



Project Type:



&#x20;   Enterprise AI Trading Platform



Platform identity:



&#x20;   ShadBotTrader is a single, unified enterprise AI trading

&#x20;   platform. It is built from scratch as one project and one

&#x20;   codebase. There is no separate companion project.



The platform includes these subsystems, all developed together:



&#x20;   Data, Feature, AI, Trading, Portfolio, Simulation,

&#x20;   Self-Learning, Project Intelligence, GUI, Infrastructure.



Its purpose is to provide a real, executable, production-grade

trading platform.



====================================================================

2\. PRIMARY OBJECTIVE

====================================================================



The final ShadBotTrader system must be able to:



&#x20;   1. Load configuration.

&#x20;   2. Initialize the application.

&#x20;   3. Load market data.

&#x20;   4. Validate market data.

&#x20;   5. Normalize market data.

&#x20;   6. Maintain market state.

&#x20;   7. Calculate indicators/features.

&#x20;   8. Run trading strategies.

&#x20;   9. Produce trading signals.

&#x20;   10. Apply risk management.

&#x20;   11. Create orders.

&#x20;   12. Validate orders.

&#x20;   13. Execute orders through an execution abstraction.

&#x20;   14. Track trades.

&#x20;   15. Track positions.

&#x20;   16. Track balances.

&#x20;   17. Calculate portfolio state.

&#x20;   18. Support simulation.

&#x20;   19. Support backtesting.

&#x20;   20. Produce performance metrics.

&#x20;   21. Persist required state.

&#x20;   22. Emit domain/application events.

&#x20;   23. Log all important operations.

&#x20;   24. Run automated tests.

&#x20;   25. Be inspectable by ShadBotTrader Project Intelligence.



====================================================================

3\. NON-GOALS

====================================================================



ShadBotTrader must NOT initially attempt to implement:



&#x20;   - Full AI model training platform

&#x20;   - Full self-learning platform

&#x20;   - Full GUI platform

&#x20;   - Full distributed microservice infrastructure

&#x20;   - Production broker integration before simulation is stable

&#x20;   - Arbitrary plugin ecosystems

&#x20;   - Autonomous code modification



Those capabilities belong primarily to ShadBotTrader.



ShadBotTrader should expose clean interfaces that allow those

capabilities to be integrated later.



====================================================================

4\. DESIGN PRINCIPLES

====================================================================



Mandatory principles:



&#x20;   Clean Architecture

&#x20;   Domain-Driven Design

&#x20;   Dependency Inversion

&#x20;   Explicit Contracts

&#x20;   Strong Typing

&#x20;   Testability

&#x20;   Deterministic Simulation

&#x20;   Event-Driven Communication

&#x20;   Configuration Separation

&#x20;   Infrastructure Isolation

&#x20;   No hidden global state

&#x20;   No circular dependencies

&#x20;   No business logic in infrastructure

&#x20;   No business logic in CLI

&#x20;   No business logic in configuration

&#x20;   No broker-specific logic in Domain



====================================================================

5\. ARCHITECTURAL LAYERS

====================================================================



The system must conceptually follow:



&#x20;   Presentation / Entry Point

&#x20;             ↓

&#x20;   Application

&#x20;             ↓

&#x20;   Domain

&#x20;             ↑

&#x20;   Infrastructure



Dependency direction:



&#x20;   Presentation

&#x20;       ↓

&#x20;   Application

&#x20;       ↓

&#x20;   Domain



&#x20;   Infrastructure

&#x20;       ↓

&#x20;   Application / Domain Contracts



Domain must never depend on Infrastructure.



====================================================================

6\. MASTER PACKAGE STRUCTURE

====================================================================



Recommended structure:



&#x20;   src/

&#x20;       shadbottrader/

&#x20;           \_\_init\_\_.py



&#x20;           main.py



&#x20;           core/

&#x20;               \_\_init\_\_.py

&#x20;               config/

&#x20;               errors/

&#x20;               events/

&#x20;               lifecycle/

&#x20;               logging/

&#x20;               result/

&#x20;               types/



&#x20;           domain/

&#x20;               \_\_init\_\_.py



&#x20;               market/

&#x20;               trading/

&#x20;               portfolio/

&#x20;               risk/

&#x20;               strategy/

&#x20;               prediction/

&#x20;               common/



&#x20;           application/

&#x20;               \_\_init\_\_.py



&#x20;               commands/

&#x20;               queries/

&#x20;               services/

&#x20;               workflows/

&#x20;               runtime/

&#x20;               ports/



&#x20;           infrastructure/

&#x20;               \_\_init\_\_.py



&#x20;               config/

&#x20;               logging/

&#x20;               persistence/

&#x20;               market\_data/

&#x20;               execution/

&#x20;               filesystem/

&#x20;               clock/



&#x20;           simulation/

&#x20;               \_\_init\_\_.py

&#x20;               market/

&#x20;               execution/

&#x20;               engine/

&#x20;               clock/



&#x20;           backtesting/

&#x20;               \_\_init\_\_.py

&#x20;               engine/

&#x20;               metrics/

&#x20;               reports/



&#x20;           strategies/

&#x20;               \_\_init\_\_.py

&#x20;               base/

&#x20;               implementations/



&#x20;           interfaces/

&#x20;               \_\_init\_\_.py

&#x20;               cli/



&#x20;   tests/

&#x20;       unit/

&#x20;       integration/

&#x20;       contract/

&#x20;       simulation/

&#x20;       backtesting/

&#x20;       architecture/

&#x20;       e2e/



&#x20;   configs/



&#x20;   datasets/

&#x20;       raw/

&#x20;       processed/

&#x20;       features/



&#x20;   docs/



&#x20;   scripts/



====================================================================

7\. CORE PACKAGE

====================================================================



Core contains cross-cutting abstractions.



It must NOT contain trading business logic.



Core responsibilities:



&#x20;   Configuration contracts

&#x20;   Events

&#x20;   Lifecycle

&#x20;   Logging abstractions

&#x20;   Result abstractions

&#x20;   Common exceptions

&#x20;   Common technical types



====================================================================

8\. CORE CONFIGURATION

====================================================================



Configuration must support:



&#x20;   Environment

&#x20;   Application identity

&#x20;   Trading mode

&#x20;   Data source

&#x20;   Execution mode

&#x20;   Risk configuration

&#x20;   Strategy configuration

&#x20;   Logging configuration

&#x20;   Persistence configuration



Supported modes:



&#x20;   DEVELOPMENT

&#x20;   TEST

&#x20;   SIMULATION

&#x20;   PAPER

&#x20;   LIVE



LIVE must never be the implicit default.



Default:



&#x20;   SIMULATION



====================================================================

9\. CORE RESULT

====================================================================



Application operations should support explicit result semantics.



Conceptually:



&#x20;   Success

&#x20;   Failure



A Result should not require exceptions for normal business failures.



Exceptions remain appropriate for unexpected technical failures.



====================================================================

10\. CORE EVENTS

====================================================================



Event abstraction must contain:



&#x20;   event\_id

&#x20;   event\_type

&#x20;   occurred\_at

&#x20;   source

&#x20;   correlation\_id

&#x20;   payload

&#x20;   metadata



Important events include:



&#x20;   MarketDataReceived

&#x20;   MarketDataValidated

&#x20;   SignalGenerated

&#x20;   RiskApproved

&#x20;   RiskRejected

&#x20;   OrderCreated

&#x20;   OrderRejected

&#x20;   OrderSubmitted

&#x20;   OrderFilled

&#x20;   OrderCancelled

&#x20;   TradeOpened

&#x20;   TradeClosed

&#x20;   PositionOpened

&#x20;   PositionClosed

&#x20;   PortfolioUpdated

&#x20;   BacktestStarted

&#x20;   BacktestCompleted



====================================================================

11\. DOMAIN MODEL

====================================================================



Domain is the heart of ShadBotTrader.



Domain entities must represent actual trading concepts.



Required concepts:



&#x20;   Symbol

&#x20;   TimeFrame

&#x20;   Candle

&#x20;   MarketData

&#x20;   Account

&#x20;   Balance

&#x20;   Position

&#x20;   Trade

&#x20;   Order

&#x20;   Signal

&#x20;   Prediction

&#x20;   RiskDecision

&#x20;   Strategy

&#x20;   Portfolio



====================================================================

12\. VALUE OBJECTS

====================================================================



Important Value Objects:



&#x20;   Symbol

&#x20;   TimeFrame

&#x20;   Price

&#x20;   Quantity

&#x20;   Money

&#x20;   Percentage

&#x20;   Timestamp

&#x20;   OrderSide

&#x20;   OrderType

&#x20;   PositionSide

&#x20;   SignalDirection

&#x20;   TradingMode



Value Objects must be immutable where practical.



They must validate themselves.



Examples:



&#x20;   Price >= 0

&#x20;   Quantity > 0

&#x20;   Percentage within defined range

&#x20;   Symbol must not be empty



====================================================================

13\. SYMBOL

====================================================================



Symbol represents a tradable instrument.



Examples:



&#x20;   EURUSD

&#x20;   GBPUSD

&#x20;   XAUUSD

&#x20;   BTCUSDT



Symbol must normalize input.



Example:



&#x20;   " eurusd "

&#x20;       ↓

&#x20;   "EURUSD"



====================================================================

14\. TIMEFRAME

====================================================================



TimeFrame must represent candle intervals.



Examples:



&#x20;   1m

&#x20;   5m

&#x20;   15m

&#x20;   1h

&#x20;   4h

&#x20;   1d



Invalid timeframes must be rejected.



====================================================================

15\. CANDLE

====================================================================



Candle fields:



&#x20;   timestamp

&#x20;   open

&#x20;   high

&#x20;   low

&#x20;   close

&#x20;   volume



Validation:



&#x20;   high >= max(open, close)

&#x20;   low <= min(open, close)

&#x20;   volume >= 0



Invalid candle data must never enter the trading pipeline.



====================================================================

16\. MARKET DATA

====================================================================



MarketData represents a stream or collection of market observations.



It should support:



&#x20;   symbol

&#x20;   timeframe

&#x20;   candles

&#x20;   source

&#x20;   timestamp



Market data must be ordered chronologically.



Duplicate timestamps must be handled explicitly.



====================================================================

17\. ACCOUNT

====================================================================



Account represents trading account state.



It must support:



&#x20;   account\_id

&#x20;   currency

&#x20;   balances

&#x20;   equity

&#x20;   margin

&#x20;   free\_margin



====================================================================

18\. BALANCE

====================================================================



Balance contains:



&#x20;   asset

&#x20;   available

&#x20;   locked



Balance operations must preserve invariants.



Available balance must never become negative unless explicitly

supported by the configured account model.



====================================================================

19\. ORDER

====================================================================



Order represents an intention to trade.



Required fields:



&#x20;   order\_id

&#x20;   symbol

&#x20;   side

&#x20;   type

&#x20;   quantity

&#x20;   price

&#x20;   status

&#x20;   created\_at



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

20\. ORDER TYPES

====================================================================



At minimum:



&#x20;   MARKET

&#x20;   LIMIT



Architecture should allow future:



&#x20;   STOP

&#x20;   STOP\_LIMIT

&#x20;   TAKE\_PROFIT

&#x20;   STOP\_LOSS



without redesigning the Order entity.



====================================================================

21\. TRADE

====================================================================



Trade represents executed trading activity.



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



====================================================================

22\. POSITION

====================================================================



Position represents current exposure.



Fields:



&#x20;   position\_id

&#x20;   symbol

&#x20;   side

&#x20;   quantity

&#x20;   average\_entry\_price

&#x20;   current\_price

&#x20;   unrealized\_pnl

&#x20;   realized\_pnl



Position must be updated from execution events.



====================================================================

23\. SIGNAL

====================================================================



Signal represents a trading decision candidate.



Fields:



&#x20;   signal\_id

&#x20;   symbol

&#x20;   direction

&#x20;   strength

&#x20;   generated\_at

&#x20;   strategy\_id

&#x20;   metadata



Directions:



&#x20;   BUY

&#x20;   SELL

&#x20;   HOLD



Signal is NOT an order.



Signal must never directly execute a trade.



====================================================================

24\. PREDICTION

====================================================================



Prediction represents model output.



It may contain:



&#x20;   prediction\_id

&#x20;   symbol

&#x20;   predicted\_direction

&#x20;   probability

&#x20;   model\_id

&#x20;   model\_version

&#x20;   generated\_at



Prediction is not automatically a Signal.



A strategy or decision layer converts prediction into a signal.



====================================================================

25\. RISK DECISION

====================================================================



RiskDecision:



&#x20;   APPROVED

&#x20;   REJECTED



Must contain:



&#x20;   decision\_id

&#x20;   order\_id / request\_id

&#x20;   reason

&#x20;   limits\_checked

&#x20;   created\_at



====================================================================

26\. STRATEGY

====================================================================



Strategy is responsible for transforming market state into a

candidate decision.



Conceptual contract:



&#x20;   Market Context

&#x20;       ↓

&#x20;   Strategy

&#x20;       ↓

&#x20;   Signal



Strategy must not:



&#x20;   execute broker orders

&#x20;   modify database directly

&#x20;   bypass risk

&#x20;   access infrastructure directly



====================================================================

27\. RISK MANAGEMENT

====================================================================



Risk management is a mandatory gate.



Flow:



&#x20;   Signal

&#x20;       ↓

&#x20;   Order Candidate

&#x20;       ↓

&#x20;   Risk Engine

&#x20;       ↓

&#x20;   APPROVED / REJECTED



Possible checks:



&#x20;   Maximum position size

&#x20;   Maximum exposure

&#x20;   Maximum daily loss

&#x20;   Maximum drawdown

&#x20;   Account balance

&#x20;   Margin

&#x20;   Symbol limits

&#x20;   Strategy limits

&#x20;   Order quantity

&#x20;   Price validity



====================================================================

28\. APPLICATION LAYER

====================================================================



Application coordinates use cases.



Application must not contain infrastructure implementation.



Application services include:



&#x20;   MarketDataService

&#x20;   SignalService

&#x20;   RiskService

&#x20;   OrderService

&#x20;   ExecutionService

&#x20;   PortfolioService

&#x20;   BacktestService

&#x20;   SimulationService



====================================================================

29\. APPLICATION PORTS

====================================================================



Application should define interfaces for external capabilities.



Examples:



&#x20;   MarketDataProvider

&#x20;   OrderExecutor

&#x20;   TradeRepository

&#x20;   PositionRepository

&#x20;   PortfolioRepository

&#x20;   MarketDataRepository

&#x20;   EventPublisher

&#x20;   Clock



Infrastructure implements these contracts.



====================================================================

30\. MARKET DATA PORT

====================================================================



Conceptual contract:



&#x20;   get\_latest()

&#x20;   get\_history()

&#x20;   subscribe()



Provider must return validated domain-compatible data.



====================================================================

31\. EXECUTION PORT

====================================================================



Execution abstraction:



&#x20;   submit\_order()

&#x20;   cancel\_order()

&#x20;   get\_order()

&#x20;   get\_status()



Implementations:



&#x20;   SimulatedExecution

&#x20;   PaperExecution

&#x20;   BrokerExecution



All must conform to the same contract.



====================================================================

32\. SIMULATION

====================================================================



Simulation is a first-class execution environment.



Flow:



&#x20;   Historical Market Data

&#x20;       ↓

&#x20;   Market Simulator

&#x20;       ↓

&#x20;   Strategy

&#x20;       ↓

&#x20;   Risk

&#x20;       ↓

&#x20;   Simulated Order

&#x20;       ↓

&#x20;   Simulated Execution

&#x20;       ↓

&#x20;   Trade

&#x20;       ↓

&#x20;   Position

&#x20;       ↓

&#x20;   Portfolio



Simulation must never call a live broker.



====================================================================

33\. SIMULATED MARKET

====================================================================



Simulator must support:



&#x20;   candle progression

&#x20;   current price

&#x20;   order matching

&#x20;   fills

&#x20;   slippage

&#x20;   fees

&#x20;   latency model



All parameters must be configurable.



====================================================================

34\. BACKTESTING

====================================================================



Backtest input:



&#x20;   Dataset

&#x20;   Strategy

&#x20;   Risk Configuration

&#x20;   Initial Capital

&#x20;   Trading Costs

&#x20;   Slippage

&#x20;   Timeframe



Backtest output:



&#x20;   Trades

&#x20;   Equity Curve

&#x20;   PnL

&#x20;   Return

&#x20;   Drawdown

&#x20;   Win Rate

&#x20;   Profit Factor

&#x20;   Sharpe Ratio where applicable

&#x20;   Number of Trades



====================================================================

35\. BACKTESTING LOOP

====================================================================



Exact conceptual loop:



&#x20;   Load Dataset



&#x20;       ↓



&#x20;   Initialize Portfolio



&#x20;       ↓



&#x20;   Initialize Strategy



&#x20;       ↓



&#x20;   Initialize Risk Engine



&#x20;       ↓



&#x20;   For each Market Event:



&#x20;       Update Market State



&#x20;       ↓



&#x20;       Calculate Features



&#x20;       ↓



&#x20;       Strategy Evaluation



&#x20;       ↓



&#x20;       Generate Signal



&#x20;       ↓



&#x20;       Risk Check



&#x20;       ↓



&#x20;       Create Order



&#x20;       ↓



&#x20;       Simulate Execution



&#x20;       ↓



&#x20;       Update Position



&#x20;       ↓



&#x20;       Update Portfolio



&#x20;       ↓



&#x20;       Record Event



&#x20;       ↓



&#x20;   Calculate Metrics



&#x20;       ↓



&#x20;   Generate Report



====================================================================

36\. LOOKAHEAD BIAS

====================================================================



Backtesting must prevent future information leakage.



At time T:



&#x20;   Strategy may use information available at or before T.



Strategy must NOT use:



&#x20;   future candles

&#x20;   future prices

&#x20;   future indicators

&#x20;   future portfolio state



Feature calculation must be causal.



====================================================================

37\. DATA LEAKAGE

====================================================================



Training / backtesting pipelines must not mix future data into

historical decisions.



Train/Test split must respect temporal ordering.



Never randomly shuffle time series for a production trading

backtest unless explicitly required by a valid methodology.



====================================================================

38\. PORTFOLIO

====================================================================



Portfolio service must calculate:



&#x20;   Cash

&#x20;   Equity

&#x20;   Positions

&#x20;   Exposure

&#x20;   Unrealized PnL

&#x20;   Realized PnL

&#x20;   Fees

&#x20;   Returns

&#x20;   Drawdown



Portfolio state must be reconstructible from events or persisted

records.



====================================================================

39\. PERFORMANCE METRICS

====================================================================



Minimum metrics:



&#x20;   Total Return

&#x20;   Net PnL

&#x20;   Gross Profit

&#x20;   Gross Loss

&#x20;   Win Rate

&#x20;   Loss Rate

&#x20;   Number of Trades

&#x20;   Average Trade

&#x20;   Maximum Drawdown

&#x20;   Profit Factor



Optional:



&#x20;   Sharpe Ratio

&#x20;   Sortino Ratio

&#x20;   Calmar Ratio

&#x20;   CAGR

&#x20;   Volatility



Metrics must clearly define their calculation methodology.



====================================================================

40\. FEATURE ENGINEERING

====================================================================



Feature layer must support indicators such as:



&#x20;   SMA

&#x20;   EMA

&#x20;   RSI

&#x20;   MACD

&#x20;   ATR

&#x20;   Bollinger Bands



Feature system must be extensible.



Each feature must specify:



&#x20;   name

&#x20;   version

&#x20;   input requirements

&#x20;   calculation

&#x20;   output schema



====================================================================

41\. STRATEGY IMPLEMENTATIONS

====================================================================



Initial strategies should be simple and deterministic.



Examples:



&#x20;   MovingAverageCrossStrategy



&#x20;   RSIReversalStrategy



&#x20;   MomentumStrategy



Strategies must implement the common Strategy contract.



Each strategy must have:



&#x20;   strategy\_id

&#x20;   name

&#x20;   version

&#x20;   configuration

&#x20;   evaluate()



====================================================================

42\. AI INTEGRATION

====================================================================



AI should be optional.



The system must function without AI.



AI integration point:



&#x20;   Market Data

&#x20;       ↓

&#x20;   Features

&#x20;       ↓

&#x20;   Model

&#x20;       ↓

&#x20;   Prediction

&#x20;       ↓

&#x20;   Strategy / Decision

&#x20;       ↓

&#x20;   Signal



AI model must not directly create broker orders.



====================================================================

43\. MODEL METADATA

====================================================================



Each model must identify:



&#x20;   model\_id

&#x20;   version

&#x20;   algorithm

&#x20;   training\_data

&#x20;   feature\_set

&#x20;   target

&#x20;   metrics

&#x20;   created\_at



====================================================================

44\. EVENT-DRIVEN ARCHITECTURE

====================================================================



Important operations should publish events.



Example:



&#x20;   OrderFilled

&#x20;       ↓

&#x20;   TradeCreated

&#x20;       ↓

&#x20;   PositionUpdated

&#x20;       ↓

&#x20;   PortfolioUpdated



Subscribers should be independently testable.



====================================================================

45\. PERSISTENCE

====================================================================



Persistence must be abstracted.



Repositories:



&#x20;   MarketDataRepository

&#x20;   OrderRepository

&#x20;   TradeRepository

&#x20;   PositionRepository

&#x20;   PortfolioRepository



Domain should not know whether persistence is:



&#x20;   SQL Server

&#x20;   SQLite

&#x20;   PostgreSQL

&#x20;   File

&#x20;   Memory



====================================================================

46\. DATABASE

====================================================================



If SQL Server is used, schema must support:



&#x20;   accounts

&#x20;   balances

&#x20;   market\_data

&#x20;   orders

&#x20;   trades

&#x20;   positions

&#x20;   portfolio\_snapshots

&#x20;   signals

&#x20;   predictions

&#x20;   events

&#x20;   backtests

&#x20;   backtest\_trades

&#x20;   strategies

&#x20;   models



Foreign keys and indexes must be deliberate.



====================================================================

47\. CONFIGURATION FILES

====================================================================



Recommended:



&#x20;   configs/

&#x20;       development.yaml

&#x20;       test.yaml

&#x20;       simulation.yaml

&#x20;       paper.yaml

&#x20;       production.yaml



Secrets must come from environment variables or secret management.



====================================================================

48\. LOGGING

====================================================================



Every major workflow should log:



&#x20;   start

&#x20;   success

&#x20;   failure

&#x20;   duration



Trading operations should include:



&#x20;   order\_id

&#x20;   symbol

&#x20;   strategy\_id

&#x20;   account\_id

&#x20;   correlation\_id



Never log secrets.



====================================================================

49\. OBSERVABILITY

====================================================================



System should expose:



&#x20;   application health

&#x20;   execution health

&#x20;   data health

&#x20;   persistence health

&#x20;   strategy status

&#x20;   simulation status



====================================================================

50\. ERROR MODEL

====================================================================



Errors should be categorized.



Examples:



&#x20;   ConfigurationError

&#x20;   ValidationError

&#x20;   MarketDataError

&#x20;   StrategyError

&#x20;   RiskError

&#x20;   OrderError

&#x20;   ExecutionError

&#x20;   PersistenceError

&#x20;   SimulationError

&#x20;   BacktestError



Do not use generic Exception as the primary business error model.



====================================================================

51\. TESTING ARCHITECTURE

====================================================================



Tests must be separated.



&#x20;   tests/

&#x20;       unit/

&#x20;       integration/

&#x20;       contract/

&#x20;       simulation/

&#x20;       backtesting/

&#x20;       architecture/

&#x20;       e2e/



====================================================================

52\. UNIT TESTS

====================================================================



Unit test:



&#x20;   Value Objects

&#x20;   Domain Entities

&#x20;   Risk Rules

&#x20;   Strategies

&#x20;   Feature Calculations

&#x20;   Portfolio Calculations

&#x20;   Metrics



Unit tests must be deterministic.



====================================================================

53\. INTEGRATION TESTS

====================================================================



Integration tests must validate:



&#x20;   Application + Domain

&#x20;   Repository implementations

&#x20;   Event Bus

&#x20;   Market Data adapters

&#x20;   Execution adapters

&#x20;   Persistence



====================================================================

54\. CONTRACT TESTS

====================================================================



Every implementation of:



&#x20;   MarketDataProvider

&#x20;   OrderExecutor

&#x20;   Repository

&#x20;   EventPublisher



must satisfy its contract tests.



====================================================================

55\. SIMULATION TESTS

====================================================================



Simulation tests must verify:



&#x20;   order fill

&#x20;   partial fill

&#x20;   rejected order

&#x20;   fees

&#x20;   slippage

&#x20;   position creation

&#x20;   position closing

&#x20;   PnL

&#x20;   portfolio update



====================================================================

56\. BACKTEST TESTS

====================================================================



Backtest tests must verify:



&#x20;   deterministic output

&#x20;   no lookahead bias

&#x20;   correct timestamps

&#x20;   correct order sequence

&#x20;   correct PnL

&#x20;   correct fees

&#x20;   correct drawdown



====================================================================

57\. ARCHITECTURE TESTS

====================================================================



Architecture tests must verify:



&#x20;   Domain does not import Infrastructure.



&#x20;   Domain does not import CLI.



&#x20;   Domain does not import GUI.



&#x20;   Application does not depend on concrete broker SDKs.



&#x20;   No forbidden circular dependencies exist.



====================================================================

58\. QUALITY GATE

====================================================================



Every implementation milestone must pass:



&#x20;   python -m ruff check .



&#x20;   python -m black .



&#x20;   python -m mypy src



&#x20;   python -m pytest



No known failing test may be committed.



====================================================================

59\. CODE QUALITY

====================================================================



Required:



&#x20;   Type annotations

&#x20;   Small cohesive classes

&#x20;   Explicit dependencies

&#x20;   Clear naming

&#x20;   No duplicated business logic

&#x20;   No dead code

&#x20;   No unexplained magic numbers



Avoid:



&#x20;   giant functions

&#x20;   giant classes

&#x20;   god services

&#x20;   global mutable state

&#x20;   circular dependencies



====================================================================

60\. SECURITY

====================================================================



Never commit:



&#x20;   API keys

&#x20;   passwords

&#x20;   broker credentials

&#x20;   tokens

&#x20;   database credentials



Use:



&#x20;   .env

&#x20;   environment variables

&#x20;   secure configuration



====================================================================

61\. LIVE TRADING SAFETY

====================================================================



LIVE trading must require explicit configuration.



Required safeguards:



&#x20;   explicit LIVE mode

&#x20;   broker credentials

&#x20;   risk limits

&#x20;   order validation

&#x20;   account validation

&#x20;   logging

&#x20;   audit trail



Default must never be LIVE.



====================================================================

62\. PAPER TRADING

====================================================================



Paper trading must use the same application flow as live trading.



Only execution adapter changes.



Correct:



&#x20;   Strategy

&#x20;       ↓

&#x20;   Risk

&#x20;       ↓

&#x20;   Order

&#x20;       ↓

&#x20;   ExecutionPort

&#x20;       ↓

&#x20;   PaperExecution



and:



&#x20;   Strategy

&#x20;       ↓

&#x20;   Risk

&#x20;       ↓

&#x20;   Order

&#x20;       ↓

&#x20;   ExecutionPort

&#x20;       ↓

&#x20;   BrokerExecution



====================================================================

63\. SIMULATION / PAPER / LIVE SEPARATION

====================================================================



The mode must be explicit.



&#x20;   SIMULATION

&#x20;       → historical / synthetic execution



&#x20;   PAPER

&#x20;       → simulated real-time execution



&#x20;   LIVE

&#x20;       → real broker execution



Never infer execution mode from broker availability.



====================================================================

64\. CLI

====================================================================



CLI should provide commands such as:



&#x20;   start

&#x20;   simulate

&#x20;   backtest

&#x20;   validate

&#x20;   status



Example:



&#x20;   python -m shadbottrader simulate



CLI should call Application services.



CLI must not contain trading logic.



====================================================================

65\. MAIN

====================================================================



main.py responsibilities:



&#x20;   load configuration

&#x20;   initialize logging

&#x20;   bootstrap dependencies

&#x20;   initialize application

&#x20;   start selected mode

&#x20;   handle shutdown



Nothing more.



====================================================================

66\. BOOTSTRAP

====================================================================



Bootstrap must construct:



&#x20;   configuration

&#x20;   logger

&#x20;   event bus

&#x20;   repositories

&#x20;   market data provider

&#x20;   execution adapter

&#x20;   risk service

&#x20;   strategy service

&#x20;   portfolio service

&#x20;   application runtime



Dependency construction must be centralized.



====================================================================

67\. DEPENDENCY INJECTION

====================================================================



Prefer constructor injection.



Avoid:



&#x20;   hidden service locators

&#x20;   module-level singleton state

&#x20;   direct object creation inside business services



Example conceptual dependency:



&#x20;   OrderService(

&#x20;       order\_repository,

&#x20;       risk\_service,

&#x20;       execution\_service,

&#x20;       event\_publisher

&#x20;   )



====================================================================

68\. CLOCK

====================================================================



Time must be abstracted where deterministic behavior matters.



Provide:



&#x20;   SystemClock

&#x20;   FixedClock

&#x20;   SimulationClock



Backtesting must use SimulationClock.



====================================================================

69\. ID GENERATION

====================================================================



Identifiers must be generated through explicit mechanisms.



Examples:



&#x20;   UUID



IDs must be unique and traceable.



====================================================================

70\. CORRELATION

====================================================================



A trading workflow should maintain correlation identifiers.



Example:



&#x20;   Signal

&#x20;       correlation\_id = X



&#x20;   RiskDecision

&#x20;       correlation\_id = X



&#x20;   Order

&#x20;       correlation\_id = X



&#x20;   Trade

&#x20;       correlation\_id = X



This allows end-to-end tracing.



====================================================================

71\. AUDIT

====================================================================



Important trading actions must be auditable.



At minimum:



&#x20;   Signal

&#x20;   Risk Decision

&#x20;   Order

&#x20;   Execution

&#x20;   Trade

&#x20;   Position Change



Audit data should include:



&#x20;   who/what

&#x20;   when

&#x20;   why

&#x20;   result

&#x20;   correlation ID



====================================================================

72\. DETERMINISM

====================================================================



Simulation and backtesting should be deterministic.



Same:



&#x20;   Dataset

&#x20;   Configuration

&#x20;   Strategy

&#x20;   Seed

&#x20;   Starting Capital



must produce equivalent results.



====================================================================

73\. RANDOMNESS

====================================================================



If randomness is required:



&#x20;   seed must be configurable.



Never use uncontrolled randomness in deterministic tests.



====================================================================

74\. DATASET FORMAT

====================================================================



Market dataset should contain at minimum:



&#x20;   timestamp

&#x20;   symbol

&#x20;   timeframe

&#x20;   open

&#x20;   high

&#x20;   low

&#x20;   close

&#x20;   volume



CSV, Parquet or database storage may be supported.



Internal domain representation must remain independent of storage

format.



====================================================================

75\. DATA VALIDATION

====================================================================



Validate:



&#x20;   timestamp

&#x20;   OHLC

&#x20;   volume

&#x20;   symbol

&#x20;   timeframe

&#x20;   ordering

&#x20;   duplicates

&#x20;   missing values



Invalid data should be rejected or explicitly quarantined.



====================================================================

76\. MARKET DATA NORMALIZATION

====================================================================



Different providers may return different formats.



Normalize into:



&#x20;   Candle

&#x20;   MarketData



Provider-specific schemas must not leak into Domain.



====================================================================

77\. STRATEGY LIFECYCLE

====================================================================



Strategy lifecycle:



&#x20;   Create

&#x20;       ↓

&#x20;   Configure

&#x20;       ↓

&#x20;   Initialize

&#x20;       ↓

&#x20;   Evaluate

&#x20;       ↓

&#x20;   Shutdown



====================================================================

78\. ORDER LIFECYCLE

====================================================================



Order lifecycle:



&#x20;   CREATED

&#x20;       ↓

&#x20;   VALIDATED

&#x20;       ↓

&#x20;   SUBMITTED

&#x20;       ↓

&#x20;   PARTIALLY\_FILLED

&#x20;       ↓

&#x20;   FILLED



Alternative terminal states:



&#x20;   REJECTED

&#x20;   CANCELLED

&#x20;   EXPIRED



Invalid transitions must be rejected.



====================================================================

79\. POSITION LIFECYCLE

====================================================================



Position lifecycle:



&#x20;   NONE

&#x20;       ↓

&#x20;   OPEN

&#x20;       ↓

&#x20;   INCREASED / REDUCED

&#x20;       ↓

&#x20;   CLOSED



====================================================================

80\. TRADE LIFECYCLE

====================================================================



Trade lifecycle:



&#x20;   CREATED

&#x20;       ↓

&#x20;   OPEN

&#x20;       ↓

&#x20;   CLOSED



PnL must be calculated according to side and execution prices.



====================================================================

81\. RISK RULE ENGINE

====================================================================



Risk engine should be composable.



Example:



&#x20;   RiskRule 1

&#x20;       ↓

&#x20;   RiskRule 2

&#x20;       ↓

&#x20;   RiskRule 3

&#x20;       ↓

&#x20;   Aggregate Decision



Rules may include:



&#x20;   MaximumOrderSizeRule

&#x20;   MaximumExposureRule

&#x20;   BalanceRule

&#x20;   DailyLossRule

&#x20;   DrawdownRule

&#x20;   SymbolRestrictionRule



====================================================================

82\. RISK RESULT

====================================================================



Risk result must provide:



&#x20;   approved

&#x20;   rejected\_rules

&#x20;   warnings

&#x20;   calculated\_exposure

&#x20;   calculated\_risk

&#x20;   reason



====================================================================

83\. FEATURE PIPELINE

====================================================================



Feature pipeline:



&#x20;   Candle

&#x20;       ↓

&#x20;   Window

&#x20;       ↓

&#x20;   Feature Calculators

&#x20;       ↓

&#x20;   Feature Vector

&#x20;       ↓

&#x20;   Validation

&#x20;       ↓

&#x20;   Strategy / Model



====================================================================

84\. STRATEGY PIPELINE

====================================================================



Strategy pipeline:



&#x20;   Market Context

&#x20;       ↓

&#x20;   Feature Vector

&#x20;       ↓

&#x20;   Strategy

&#x20;       ↓

&#x20;   Signal

&#x20;       ↓

&#x20;   Signal Validation



====================================================================

85\. TRADING PIPELINE

====================================================================



Complete pipeline:



&#x20;   Market Data

&#x20;       ↓

&#x20;   Validation

&#x20;       ↓

&#x20;   Feature Engineering

&#x20;       ↓

&#x20;   Strategy / AI

&#x20;       ↓

&#x20;   Prediction

&#x20;       ↓

&#x20;   Signal

&#x20;       ↓

&#x20;   Risk

&#x20;       ↓

&#x20;   Order Candidate

&#x20;       ↓

&#x20;   Order Validation

&#x20;       ↓

&#x20;   Execution

&#x20;       ↓

&#x20;   Trade

&#x20;       ↓

&#x20;   Position

&#x20;       ↓

&#x20;   Portfolio

&#x20;       ↓

&#x20;   Metrics

&#x20;       ↓

&#x20;   Event / Audit



====================================================================

86\. PROJECT INTELLIGENCE INTEGRATION

====================================================================



ShadBotTrader must be inspectable by ShadBotTrader Project Intelligence.



Project Intelligence must be able to discover:



&#x20;   package structure

&#x20;   source files

&#x20;   classes

&#x20;   functions

&#x20;   dependencies

&#x20;   tests

&#x20;   configuration

&#x20;   Git history

&#x20;   statistics

&#x20;   TODOs

&#x20;   architecture documentation



====================================================================

87\. PROJECT INTELLIGENCE TEST TARGET

====================================================================



ShadBotTrader exists partly to serve as a realistic test project.



Therefore it must contain enough structure to test:



&#x20;   filesystem scanning

&#x20;   AST scanning

&#x20;   dependency analysis

&#x20;   Git analysis

&#x20;   package analysis

&#x20;   statistics

&#x20;   roadmap

&#x20;   decisions

&#x20;   TODO detection

&#x20;   documentation generation



====================================================================

88\. DOCUMENTATION

====================================================================



Required project documentation:



&#x20;   README.md



&#x20;   docs/

&#x20;       ARCHITECTURE.md

&#x20;       DATA\_FLOW.md

&#x20;       DEVELOPMENT.md

&#x20;       TRADING.md

&#x20;       SIMULATION.md

&#x20;       BACKTESTING.md

&#x20;       CONFIGURATION.md

&#x20;       TESTING.md



Documentation must reflect actual implementation.



====================================================================

89\. PROJECT METADATA

====================================================================



Project should expose metadata:



&#x20;   project\_name

&#x20;   version

&#x20;   environment

&#x20;   build\_version

&#x20;   git\_commit

&#x20;   application\_mode



====================================================================

90\. VERSIONING

====================================================================



Application version should follow semantic versioning where practical:



&#x20;   MAJOR.MINOR.PATCH



Architecture version is independent from application version.



====================================================================

91\. DEVELOPMENT ORDER

====================================================================



Implementation must proceed in this order:



&#x20;   STEP 1

&#x20;       Repository foundation



&#x20;   STEP 2

&#x20;       Core abstractions



&#x20;   STEP 3

&#x20;       Domain common



&#x20;   STEP 4

&#x20;       Market domain



&#x20;   STEP 5

&#x20;       Trading domain



&#x20;   STEP 6

&#x20;       Portfolio domain



&#x20;   STEP 7

&#x20;       Risk domain



&#x20;   STEP 8

&#x20;       Application ports



&#x20;   STEP 9

&#x20;       Application services



&#x20;   STEP 10

&#x20;       In-memory infrastructure



&#x20;   STEP 11

&#x20;       Simulation



&#x20;   STEP 12

&#x20;       Strategy framework



&#x20;   STEP 13

&#x20;       First deterministic strategy



&#x20;   STEP 14

&#x20;       Backtesting



&#x20;   STEP 15

&#x20;       Persistence



&#x20;   STEP 16

&#x20;       Event infrastructure



&#x20;   STEP 17

&#x20;       Configuration



&#x20;   STEP 18

&#x20;       CLI



&#x20;   STEP 19

&#x20;       Integration tests



&#x20;   STEP 20

&#x20;       Project Intelligence compatibility



&#x20;   STEP 21

&#x20;       Paper execution



&#x20;   STEP 22

&#x20;       Broker integration



&#x20;   STEP 23

&#x20;       Production hardening



====================================================================

92\. PHASE IMPLEMENTATION RULE

====================================================================



Do not implement later phases before their dependencies.



Example:



&#x20;   Do not implement broker execution before Order,

&#x20;   Risk and Execution contracts are stable.



&#x20;   Do not implement AI strategy before feature contracts exist.



&#x20;   Do not implement production persistence before domain models

&#x20;   are stable.



====================================================================

93\. INITIAL IMPLEMENTATION

====================================================================



The first working implementation must use:



&#x20;   In-memory repositories

&#x20;   Deterministic market data

&#x20;   Simulated execution

&#x20;   Deterministic strategy

&#x20;   Explicit configuration



This allows the complete trading loop to be tested without external

dependencies.



====================================================================

94\. FIRST END-TO-END DEMO

====================================================================



The first complete demo must perform:



&#x20;   Load sample market data



&#x20;       ↓



&#x20;   Create strategy



&#x20;       ↓



&#x20;   Generate signal



&#x20;       ↓



&#x20;   Apply risk



&#x20;       ↓



&#x20;   Create order



&#x20;       ↓



&#x20;   Simulate execution



&#x20;       ↓



&#x20;   Create trade



&#x20;       ↓



&#x20;   Update position



&#x20;       ↓



&#x20;   Update portfolio



&#x20;       ↓



&#x20;   Print final metrics



This must work without an external broker.



====================================================================

95\. MINIMUM ACCEPTANCE TEST

====================================================================



Given deterministic market data:



&#x20;   Strategy must generate deterministic signals.



Risk must:



&#x20;   approve valid order



&#x20;   reject invalid order



Execution must:



&#x20;   fill valid simulated order



Trade must:



&#x20;   be recorded



Position must:



&#x20;   update correctly



Portfolio must:



&#x20;   calculate correct equity and PnL



Backtest must:



&#x20;   produce deterministic metrics



====================================================================

96\. FAILURE SCENARIOS

====================================================================



Must test:



&#x20;   invalid candle

&#x20;   missing market data

&#x20;   invalid symbol

&#x20;   invalid quantity

&#x20;   insufficient balance

&#x20;   excessive exposure

&#x20;   invalid order state transition

&#x20;   rejected risk decision

&#x20;   execution failure

&#x20;   persistence failure

&#x20;   strategy failure

&#x20;   configuration failure



====================================================================

97\. TRANSACTION BOUNDARIES

====================================================================



Operations affecting multiple persistent entities should have

clear transaction semantics.



Example:



&#x20;   Order Filled

&#x20;       ↓

&#x20;   Trade

&#x20;       ↓

&#x20;   Position

&#x20;       ↓

&#x20;   Portfolio



Either the operation succeeds consistently or failure must be

recoverable.



====================================================================

98\. RETRY POLICY

====================================================================



Retries are allowed for technical failures where safe.



Never blindly retry:



&#x20;   financial order execution



without idempotency protection.



====================================================================

99\. IDEMPOTENCY

====================================================================



Execution operations must support idempotency.



Repeated processing of the same execution event must not create

duplicate trades.



====================================================================

100\. DUPLICATE EVENT HANDLING

====================================================================



Event consumers should be able to detect duplicates.



Use:



&#x20;   event\_id



and/or:



&#x20;   execution\_id



====================================================================

101\. OBSERVABILITY REQUIREMENT

====================================================================



Every major workflow should be traceable from:



&#x20;   Market Data

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



====================================================================

102\. TEST DATA

====================================================================



Tests must use controlled datasets.



Do not depend on live markets for unit tests.



External APIs should be mocked or replaced by test adapters.



====================================================================

103\. EXTERNAL BROKER

====================================================================



Broker integration must implement:



&#x20;   OrderExecutor



Broker-specific implementation belongs in:



&#x20;   infrastructure/execution/



It must not leak into:



&#x20;   domain/



====================================================================

104\. EXTERNAL MARKET DATA

====================================================================



Market provider implementation belongs in:



&#x20;   infrastructure/market\_data/



Provider-specific schemas must be converted to Domain objects.



====================================================================

105\. DATABASE IMPLEMENTATION

====================================================================



Database repositories belong in:



&#x20;   infrastructure/persistence/



Application depends on repository contracts.



Database implementation depends on those contracts.



====================================================================

106\. TEST IMPLEMENTATIONS

====================================================================



Test adapters:



&#x20;   InMemoryMarketDataProvider

&#x20;   InMemoryOrderRepository

&#x20;   InMemoryTradeRepository

&#x20;   InMemoryPositionRepository

&#x20;   InMemoryPortfolioRepository

&#x20;   SimulatedOrderExecutor



must be available.



====================================================================

107\. ARCHITECTURE ENFORCEMENT

====================================================================



Architecture tests should automatically fail if:



&#x20;   Domain imports infrastructure



&#x20;   Domain imports broker SDK



&#x20;   Domain imports database driver



&#x20;   Application imports concrete infrastructure classes



&#x20;   CLI contains domain implementation



====================================================================

108\. STATIC QUALITY

====================================================================



Required tools:



&#x20;   Ruff

&#x20;   Black

&#x20;   Mypy

&#x20;   Pytest



All source code must remain compatible with the project's declared

Python version.



====================================================================

109\. GIT WORKFLOW

====================================================================



Each logical implementation milestone:



&#x20;   git status



&#x20;   git diff



&#x20;   quality gate



&#x20;   git add .



&#x20;   git commit



Commit messages should describe actual work.



Examples:



&#x20;   Implement domain trading model



&#x20;   Implement risk engine



&#x20;   Implement simulated execution



&#x20;   Implement backtesting engine



Do not create giant unrelated commits.



====================================================================

110\. BRANCHING

====================================================================



Development should use feature branches where appropriate.



Examples:



&#x20;   feature/domain

&#x20;   feature/simulation

&#x20;   feature/backtesting

&#x20;   feature/execution



Merge only after quality gate passes.



====================================================================

111\. NO PLACEHOLDER IMPLEMENTATION

====================================================================



Forbidden:



&#x20;   pass



&#x20;   TODO used instead of implementation



&#x20;   fake return values



&#x20;   hardcoded successful results



&#x20;   NotImplementedError in required production paths



&#x20;   dummy trading results



If a capability is intentionally not implemented yet:



&#x20;   define a proper contract



&#x20;   document the limitation



&#x20;   create an explicit controlled failure



====================================================================

112\. NO MAGIC TRADING LOGIC

====================================================================



Do not hardcode:



&#x20;   account balance



&#x20;   risk percentage



&#x20;   position size



&#x20;   spread



&#x20;   fees



&#x20;   slippage



&#x20;   strategy parameters



These belong in configuration or explicit strategy parameters.



====================================================================

113\. REPRODUCIBILITY

====================================================================



Backtest result must include:



&#x20;   dataset identifier

&#x20;   dataset version

&#x20;   strategy identifier

&#x20;   strategy version

&#x20;   configuration

&#x20;   starting capital

&#x20;   fees

&#x20;   slippage

&#x20;   timestamp

&#x20;   application version

&#x20;   Git commit



====================================================================

114\. BACKTEST REPORT

====================================================================



Backtest report must include:



&#x20;   Summary

&#x20;   Configuration

&#x20;   Dataset

&#x20;   Strategy

&#x20;   Trades

&#x20;   Equity Curve

&#x20;   Metrics

&#x20;   Drawdown

&#x20;   Errors / Warnings



====================================================================

115\. SIMULATION REPORT

====================================================================



Simulation report should contain:



&#x20;   start time

&#x20;   end time

&#x20;   initial balance

&#x20;   final balance

&#x20;   trades

&#x20;   positions

&#x20;   PnL

&#x20;   fees

&#x20;   drawdown

&#x20;   execution statistics



====================================================================

116\. STRATEGY CONFIGURATION

====================================================================



Strategy configuration must be externalized.



Example:



&#x20;   strategy:

&#x20;       name: moving\_average\_cross

&#x20;       fast\_period: 20

&#x20;       slow\_period: 50



Configuration must be validated before runtime.



====================================================================

117\. RISK CONFIGURATION

====================================================================



Example conceptual configuration:



&#x20;   risk:

&#x20;       max\_position\_size

&#x20;       max\_exposure

&#x20;       max\_daily\_loss

&#x20;       max\_drawdown



Values must be validated.



====================================================================

118\. EXECUTION CONFIGURATION

====================================================================



Execution configuration should define:



&#x20;   mode

&#x20;   fees

&#x20;   slippage

&#x20;   latency

&#x20;   broker

&#x20;   retry\_policy



====================================================================

119\. ENVIRONMENT ISOLATION

====================================================================



Test environment must never accidentally use:



&#x20;   production database

&#x20;   production broker

&#x20;   live credentials



Production configuration must be explicitly selected.



====================================================================

120\. SHUTDOWN

====================================================================



Application shutdown must:



&#x20;   stop new operations

&#x20;   flush events

&#x20;   persist necessary state

&#x20;   close repositories

&#x20;   close execution adapters

&#x20;   release resources

&#x20;   log shutdown



====================================================================

121\. STARTUP

====================================================================



Startup:



&#x20;   Load configuration

&#x20;       ↓

&#x20;   Validate configuration

&#x20;       ↓

&#x20;   Initialize logging

&#x20;       ↓

&#x20;   Initialize dependencies

&#x20;       ↓

&#x20;   Validate infrastructure

&#x20;       ↓

&#x20;   Initialize application

&#x20;       ↓

&#x20;   Start runtime



====================================================================

122\. HEALTH CHECK

====================================================================



Startup must verify:



&#x20;   Configuration

&#x20;   Data source

&#x20;   Persistence

&#x20;   Execution adapter



In simulation mode, external broker health is not required.



====================================================================

123\. PROJECT INTELLIGENCE COMPATIBILITY

====================================================================



The project must remain easy to scan.



Avoid:



&#x20;   dynamically generated source structures

&#x20;   hidden modules

&#x20;   excessive metaprogramming

&#x20;   code that cannot be statically analyzed



Use explicit packages and imports.



====================================================================

124\. DOCUMENTATION GENERATION

====================================================================



Project Intelligence should eventually be able to generate:



&#x20;   Architecture

&#x20;   Project Snapshot

&#x20;   Dependency Graph

&#x20;   Statistics

&#x20;   Roadmap

&#x20;   Decisions

&#x20;   Todo

&#x20;   ChatGPT Context



from ShadBotTrader.



====================================================================

125\. FINAL ARCHITECTURE

====================================================================



FINAL HIGH-LEVEL STRUCTURE:



&#x20;   +------------------------------------------------------+

&#x20;   |                  SHADBOTTRADER                      |

&#x20;   +------------------------------------------------------+

&#x20;   |                    Interfaces                        |

&#x20;   |                       CLI                            |

&#x20;   +------------------------------------------------------+

&#x20;   |                  Application                         |

&#x20;   |                                                      |

&#x20;   | Services / Workflows / Commands / Queries / Ports    |

&#x20;   +------------------------------------------------------+

&#x20;   |                     Domain                           |

&#x20;   |                                                      |

&#x20;   | Market / Trading / Risk / Portfolio / Strategy       |

&#x20;   +------------------------------------------------------+

&#x20;   |                 Infrastructure                       |

&#x20;   |                                                      |

&#x20;   | Data / Execution / Persistence / Config / Logging    |

&#x20;   +------------------------------------------------------+

&#x20;   |                  Simulation                          |

&#x20;   |                                                      |

&#x20;   | Market Simulator / Execution Simulator / Clock      |

&#x20;   +------------------------------------------------------+

&#x20;   |                  Backtesting                         |

&#x20;   |                                                      |

&#x20;   | Engine / Metrics / Reports                           |

&#x20;   +------------------------------------------------------+



====================================================================

126\. FINAL TRADING ARCHITECTURE

====================================================================



&#x20;   MARKET DATA

&#x20;        |

&#x20;        v

&#x20;   DATA VALIDATION

&#x20;        |

&#x20;        v

&#x20;   FEATURE ENGINEERING

&#x20;        |

&#x20;        v

&#x20;   STRATEGY / AI

&#x20;        |

&#x20;        v

&#x20;   PREDICTION

&#x20;        |

&#x20;        v

&#x20;   SIGNAL

&#x20;        |

&#x20;        v

&#x20;   RISK ENGINE

&#x20;        |

&#x20;        +---- REJECT ----> AUDIT / LOG

&#x20;        |

&#x20;        v

&#x20;   ORDER

&#x20;        |

&#x20;        v

&#x20;   EXECUTION PORT

&#x20;        |

&#x20;        +---- SIMULATION

&#x20;        |

&#x20;        +---- PAPER

&#x20;        |

&#x20;        +---- LIVE

&#x20;        |

&#x20;        v

&#x20;   TRADE

&#x20;        |

&#x20;        v

&#x20;   POSITION

&#x20;        |

&#x20;        v

&#x20;   PORTFOLIO

&#x20;        |

&#x20;        v

&#x20;   PERFORMANCE

&#x20;        |

&#x20;        v

&#x20;   AUDIT / EVENTS



====================================================================

127\. FINAL IMPLEMENTATION MILESTONES

====================================================================



MILESTONE 01:

&#x20;   Repository + Python package



MILESTONE 02:

&#x20;   Core abstractions



MILESTONE 03:

&#x20;   Domain common



MILESTONE 04:

&#x20;   Market domain



MILESTONE 05:

&#x20;   Trading domain



MILESTONE 06:

&#x20;   Portfolio domain



MILESTONE 07:

&#x20;   Risk domain



MILESTONE 08:

&#x20;   Application contracts



MILESTONE 09:

&#x20;   Application services



MILESTONE 10:

&#x20;   In-memory infrastructure



MILESTONE 11:

&#x20;   Simulated execution



MILESTONE 12:

&#x20;   Strategy framework



MILESTONE 13:

&#x20;   First strategy



MILESTONE 14:

&#x20;   End-to-end simulation



MILESTONE 15:

&#x20;   Backtesting



MILESTONE 16:

&#x20;   Persistence



MILESTONE 17:

&#x20;   Event Bus integration



MILESTONE 18:

&#x20;   Configuration system



MILESTONE 19:

&#x20;   CLI



MILESTONE 20:

&#x20;   Architecture tests



MILESTONE 21:

&#x20;   Project Intelligence compatibility



MILESTONE 22:

&#x20;   Paper execution



MILESTONE 23:

&#x20;   Broker adapter



MILESTONE 24:

&#x20;   Production hardening



====================================================================

128\. DEFINITION OF DONE

====================================================================



A subsystem is DONE only when:



&#x20;   implementation exists



&#x20;   public contracts exist



&#x20;   type annotations exist



&#x20;   unit tests exist



&#x20;   integration tests exist where necessary



&#x20;   error handling exists



&#x20;   logging exists where necessary



&#x20;   documentation exists



&#x20;   Ruff passes



&#x20;   Black passes



&#x20;   Mypy passes



&#x20;   Pytest passes



&#x20;   architecture rules pass



&#x20;   Git commit exists



====================================================================

129\. FINAL ACCEPTANCE CRITERIA

====================================================================



ShadBotTrader is considered complete only when:



&#x20;   \[ ] Application starts successfully



&#x20;   \[ ] Configuration is validated



&#x20;   \[ ] Domain is independent



&#x20;   \[ ] Market data can be loaded



&#x20;   \[ ] Market data is validated



&#x20;   \[ ] Features can be calculated



&#x20;   \[ ] Strategy can generate signals



&#x20;   \[ ] Risk engine can approve/reject orders



&#x20;   \[ ] Orders have valid lifecycle



&#x20;   \[ ] Simulation execution works



&#x20;   \[ ] Trades are recorded



&#x20;   \[ ] Positions are maintained



&#x20;   \[ ] Portfolio is maintained



&#x20;   \[ ] PnL is correct



&#x20;   \[ ] Backtesting works



&#x20;   \[ ] Metrics are calculated



&#x20;   \[ ] Persistence works



&#x20;   \[ ] Events work



&#x20;   \[ ] Logging works



&#x20;   \[ ] Configuration works



&#x20;   \[ ] CLI works



&#x20;   \[ ] Architecture tests pass



&#x20;   \[ ] Project Intelligence can inspect project



&#x20;   \[ ] Ruff passes



&#x20;   \[ ] Black passes



&#x20;   \[ ] Mypy passes



&#x20;   \[ ] Pytest passes



&#x20;   \[ ] No secrets are committed



&#x20;   \[ ] No live trading can occur accidentally



====================================================================

130\. FINAL AGENT COMMAND

====================================================================



If this specification is provided to a Coding Agent, the Agent must

follow these rules:



&#x20;   DO NOT redesign the system.



&#x20;   DO NOT invent requirements.



&#x20;   DO NOT skip architecture layers.



&#x20;   DO NOT create duplicate domain models.



&#x20;   DO NOT put infrastructure logic into Domain.



&#x20;   DO NOT allow signals to directly execute orders.



&#x20;   DO NOT allow AI to bypass Risk.



&#x20;   DO NOT allow simulation to access live execution.



&#x20;   DO NOT use placeholder implementations.



&#x20;   DO NOT commit failing code.



&#x20;   DO NOT ignore tests.



&#x20;   DO NOT ignore typing errors.



&#x20;   DO NOT silently change architectural decisions.



&#x20;   DO inspect the actual workspace.



&#x20;   DO inspect existing code before modifying it.



&#x20;   DO reuse existing contracts when they are correct.



&#x20;   DO create tests before or together with implementation.



&#x20;   DO maintain backward compatibility when required.



&#x20;   DO update documentation after architectural changes.



&#x20;   DO update project state.



&#x20;   DO commit completed milestones.



====================================================================

131\. IMPLEMENTATION COMMAND

====================================================================



The implementation process must be:



&#x20;   READ SPECIFICATION



&#x20;       ↓



&#x20;   INSPECT WORKSPACE



&#x20;       ↓



&#x20;   IDENTIFY CURRENT STATE



&#x20;       ↓



&#x20;   IDENTIFY FIRST UNIMPLEMENTED MILESTONE



&#x20;       ↓



&#x20;   IMPLEMENT ONLY THAT MILESTONE



&#x20;       ↓



&#x20;   WRITE TESTS



&#x20;       ↓



&#x20;   RUN:



&#x20;       python -m ruff check .



&#x20;       python -m black .



&#x20;       python -m mypy src



&#x20;       python -m pytest



&#x20;       ↓



&#x20;   FIX ALL FAILURES



&#x20;       ↓



&#x20;   VERIFY RUNTIME



&#x20;       ↓



&#x20;   UPDATE DOCUMENTATION



&#x20;       ↓



&#x20;   COMMIT



&#x20;       ↓



&#x20;   MOVE TO NEXT MILESTONE



====================================================================

132\. FINAL SYSTEM OBJECTIVE

====================================================================



The final result must not be a toy trading bot.



It must be a clean, testable, deterministic, extensible trading

application that can serve as:



&#x20;   1. A real trading runtime.



&#x20;   2. A simulation environment.



&#x20;   3. A backtesting environment.



&#x20;   4. A reference implementation for ShadBotTrader.



&#x20;   5. A realistic target for ShadBotTrader Project Intelligence.



&#x20;   6. A future integration target for ShadBotTrader AI capabilities.



====================================================================

133\. FINAL RELATIONSHIP WITH SHADBOTTRADER

====================================================================



ShadBotTrader is one unified platform with the following subsystems:



&#x20;   ShadBotTrader

&#x20;       |

&#x20;       +---- Project Intelligence

&#x20;       |

&#x20;       +---- AI Platform

&#x20;       |

&#x20;       +---- Data Platform

&#x20;       |

&#x20;       +---- Feature Platform

&#x20;       |

&#x20;       +---- Trading Platform

&#x20;       |

&#x20;       +---- Simulation

&#x20;       |

&#x20;       +---- Portfolio

&#x20;       |

&#x20;       +---- GUI

&#x20;       |

&#x20;       +---- Infrastructure



All subsystems are part of the single ShadBotTrader project and are

developed together from scratch.



====================================================================

134\. FINAL RULE

====================================================================



The developer must always prefer:



&#x20;   explicit architecture

&#x20;   explicit contracts

&#x20;   deterministic behavior

&#x20;   testable code

&#x20;   small cohesive modules

&#x20;   dependency inversion

&#x20;   observable execution

&#x20;   reproducible results



over:



&#x20;   shortcuts

&#x20;   magic

&#x20;   hidden dependencies

&#x20;   duplicated logic

&#x20;   premature optimization

&#x20;   temporary hacks



====================================================================

END OF

SHADBOTTRADER\_MASTER\_IMPLEMENTATION\_SPECIFICATION

====================================================================

