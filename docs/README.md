====================================================================

SHADBOTTRADER

README

====================================================================



PROJECT:

&#x20;   ShadBotTrader



TYPE:

&#x20;   Enterprise Trading Application / Reference Trading Runtime



STATUS:

&#x20;   Active Development



VERSION:

&#x20;   1.0



ARCHITECTURE:

&#x20;   Clean Architecture + Domain-Driven Design

&#x20;   + Dependency Inversion

&#x20;   + Event-Driven Communication

&#x20;   + Deterministic Simulation

&#x20;   + Backtesting



PRIMARY LANGUAGE:

&#x20;   Python



PRIMARY PURPOSE:

&#x20;   Build a complete, testable and extensible trading application

&#x20;   that can operate in simulation, paper-trading and eventually

&#x20;   live-trading environments while remaining independently

&#x20;   testable and compatible with the ShadBot ecosystem.



====================================================================

1\. WHAT IS SHADBOTTRADER?

====================================================================



ShadBotTrader is an enterprise-grade trading application designed

to provide a real executable trading runtime.



It is NOT a toy trading bot.



It is NOT a single Python script.



It is NOT a collection of indicators.



It is NOT an AI model wrapped around a broker API.



It is a structured trading system containing:



&#x20;   Market Data

&#x20;   Data Validation

&#x20;   Feature Engineering

&#x20;   Strategy

&#x20;   Prediction

&#x20;   Signal Generation

&#x20;   Risk Management

&#x20;   Order Management

&#x20;   Execution

&#x20;   Trade Management

&#x20;   Position Management

&#x20;   Portfolio Management

&#x20;   Simulation

&#x20;   Backtesting

&#x20;   Persistence

&#x20;   Event Processing

&#x20;   Logging

&#x20;   Configuration

&#x20;   Testing

&#x20;   Observability



The architecture is intentionally designed so that each concern

can evolve independently.



====================================================================

2\. RELATIONSHIP TO SHADBOT

====================================================================



ShadBot is the main enterprise AI trading platform.



ShadBotTrader is a separate trading application and reference

runtime.



The relationship is:



&#x20;   SHADBOT

&#x20;      |

&#x20;      +-- AI Platform

&#x20;      |

&#x20;      +-- Data Platform

&#x20;      |

&#x20;      +-- Feature Platform

&#x20;      |

&#x20;      +-- Trading Platform

&#x20;      |

&#x20;      +-- Portfolio Platform

&#x20;      |

&#x20;      +-- Simulation Platform

&#x20;      |

&#x20;      +-- Project Intelligence

&#x20;      |

&#x20;      +-- GUI

&#x20;      |

&#x20;      +-- Infrastructure

&#x20;      |

&#x20;      +-- ShadBotTrader Integration Target



ShadBotTrader must remain independently executable.



Do NOT merge the two repositories into one architecture.



Do NOT copy the entire ShadBot architecture into ShadBotTrader.



ShadBotTrader exists to provide a realistic trading workspace and

runtime that can later integrate with ShadBot.



====================================================================

3\. PRIMARY OBJECTIVES

====================================================================



The final system must be able to:



&#x20;   1. Start safely.

&#x20;   2. Load and validate configuration.

&#x20;   3. Load market data.

&#x20;   4. Validate market data.

&#x20;   5. Normalize market data.

&#x20;   6. Maintain market state.

&#x20;   7. Calculate technical features.

&#x20;   8. Execute deterministic strategies.

&#x20;   9. Optionally consume AI predictions.

&#x20;   10. Generate trading signals.

&#x20;   11. Convert signals into order candidates.

&#x20;   12. Apply risk management.

&#x20;   13. Validate orders.

&#x20;   14. Execute orders.

&#x20;   15. Track trades.

&#x20;   16. Track positions.

&#x20;   17. Track balances.

&#x20;   18. Track portfolio state.

&#x20;   19. Run simulations.

&#x20;   20. Run backtests.

&#x20;   21. Calculate performance metrics.

&#x20;   22. Persist required state.

&#x20;   23. Publish important events.

&#x20;   24. Maintain an audit trail.

&#x20;   25. Support paper trading.

&#x20;   26. Support future broker integrations.

&#x20;   27. Remain inspectable by ShadBot Project Intelligence.



====================================================================

4\. NON-GOALS

====================================================================



The initial ShadBotTrader implementation must NOT attempt to become:



&#x20;   - A complete AI training platform.

&#x20;   - A complete self-learning platform.

&#x20;   - A distributed microservice platform.

&#x20;   - A complete GUI framework.

&#x20;   - A broker-specific application.

&#x20;   - An autonomous coding agent.

&#x20;   - A replacement for ShadBot.



AI is optional.



Simulation is mandatory.



Backtesting is mandatory.



Live trading is a later integration target.



====================================================================

5\. CORE DESIGN PHILOSOPHY

====================================================================



The system must prioritize:



&#x20;   Correctness

&#x20;   Determinism

&#x20;   Testability

&#x20;   Explicit contracts

&#x20;   Separation of concerns

&#x20;   Dependency inversion

&#x20;   Observability

&#x20;   Reproducibility

&#x20;   Safety



over:



&#x20;   Short code

&#x20;   Fast hacks

&#x20;   Hidden dependencies

&#x20;   Global state

&#x20;   Magic numbers

&#x20;   Broker-specific shortcuts

&#x20;   Premature optimization



====================================================================

6\. ARCHITECTURE

====================================================================



The system follows:



&#x20;   Clean Architecture

&#x20;   Domain-Driven Design

&#x20;   Dependency Inversion

&#x20;   Event-Oriented Communication



High-level structure:



&#x20;   +------------------------------------------------------+

&#x20;   |                    INTERFACES                        |

&#x20;   |                       CLI                            |

&#x20;   +------------------------------------------------------+

&#x20;                          |

&#x20;                          v

&#x20;   +------------------------------------------------------+

&#x20;   |                  APPLICATION                         |

&#x20;   |                                                      |

&#x20;   | Commands / Queries / Services / Workflows / Ports    |

&#x20;   +------------------------------------------------------+

&#x20;                          |

&#x20;                          v

&#x20;   +------------------------------------------------------+

&#x20;   |                     DOMAIN                           |

&#x20;   |                                                      |

&#x20;   | Market / Trading / Risk / Portfolio / Strategy       |

&#x20;   +------------------------------------------------------+

&#x20;                          ^

&#x20;                          |

&#x20;   +------------------------------------------------------+

&#x20;   |                 INFRASTRUCTURE                       |

&#x20;   |                                                      |

&#x20;   | Data / Execution / Persistence / Config / Logging    |

&#x20;   +------------------------------------------------------+



Simulation and Backtesting operate around the application and

domain contracts.



====================================================================

7\. DEPENDENCY RULE

====================================================================



The most important dependency rule:



&#x20;   Domain MUST NOT depend on Infrastructure.



Therefore:



&#x20;   domain

&#x20;       X -> database driver



&#x20;   domain

&#x20;       X -> broker SDK



&#x20;   domain

&#x20;       X -> filesystem implementation



&#x20;   domain

&#x20;       X -> HTTP client



&#x20;   domain

&#x20;       X -> CLI



Instead:



&#x20;   Domain

&#x20;       ^

&#x20;       |

&#x20;   Application Contracts

&#x20;       ^

&#x20;       |

&#x20;   Infrastructure Implementations



====================================================================

8\. PROJECT STRUCTURE

====================================================================



The target structure is:



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



&#x20;               common/



&#x20;               market/



&#x20;               trading/



&#x20;               portfolio/



&#x20;               risk/



&#x20;               strategy/



&#x20;               prediction/



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

9\. CORE PACKAGE

====================================================================



Core contains technical abstractions shared by the application.



Core MUST NOT contain trading business logic.



Responsibilities:



&#x20;   Configuration contracts

&#x20;   Event abstractions

&#x20;   Lifecycle abstractions

&#x20;   Logging abstractions

&#x20;   Result types

&#x20;   Exceptions

&#x20;   Technical shared types



====================================================================

10\. DOMAIN

====================================================================



Domain is the heart of the system.



The domain represents trading concepts and business rules.



Required domain concepts:



&#x20;   Symbol

&#x20;   TimeFrame

&#x20;   Candle

&#x20;   MarketData



&#x20;   Account

&#x20;   Balance

&#x20;   Order

&#x20;   Trade

&#x20;   Position



&#x20;   Signal

&#x20;   Prediction



&#x20;   RiskDecision

&#x20;   Strategy

&#x20;   Portfolio



====================================================================

11\. VALUE OBJECTS

====================================================================



Required or recommended Value Objects:



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



Value Objects should be immutable.



They must validate their own invariants.



Examples:



&#x20;   Price >= 0



&#x20;   Quantity > 0



&#x20;   Symbol != empty



&#x20;   Percentage within defined limits



====================================================================

12\. MARKET DOMAIN

====================================================================



Market domain contains:



&#x20;   Symbol

&#x20;   TimeFrame

&#x20;   Candle

&#x20;   MarketData



Candle:



&#x20;   timestamp

&#x20;   open

&#x20;   high

&#x20;   low

&#x20;   close

&#x20;   volume



Validation:



&#x20;   high >= open

&#x20;   high >= close

&#x20;   low <= open

&#x20;   low <= close

&#x20;   volume >= 0



Market data must be chronologically ordered.



====================================================================

13\. TRADING DOMAIN

====================================================================



Trading domain contains:



&#x20;   Order

&#x20;   Trade

&#x20;   Position



Order represents intention.



Trade represents execution.



Position represents exposure.



These concepts MUST NOT be conflated.



====================================================================

14\. ORDER

====================================================================



Order contains:



&#x20;   order\_id

&#x20;   symbol

&#x20;   side

&#x20;   type

&#x20;   quantity

&#x20;   price

&#x20;   status

&#x20;   created\_at



Statuses:



&#x20;   CREATED

&#x20;   VALIDATED

&#x20;   REJECTED

&#x20;   SUBMITTED

&#x20;   PARTIALLY\_FILLED

&#x20;   FILLED

&#x20;   CANCELLED

&#x20;   EXPIRED



Invalid state transitions must be rejected.



====================================================================

15\. TRADE

====================================================================



Trade contains:



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

16\. POSITION

====================================================================



Position contains:



&#x20;   position\_id

&#x20;   symbol

&#x20;   side

&#x20;   quantity

&#x20;   average\_entry\_price

&#x20;   current\_price

&#x20;   unrealized\_pnl

&#x20;   realized\_pnl



Position is updated from execution results.



====================================================================

17\. SIGNAL

====================================================================



Signal is a candidate trading decision.



Signal contains:



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



IMPORTANT:



&#x20;   Signal != Order



A signal must never directly execute a broker operation.



====================================================================

18\. PREDICTION

====================================================================



Prediction represents model output.



Contains:



&#x20;   prediction\_id

&#x20;   symbol

&#x20;   predicted\_direction

&#x20;   probability

&#x20;   model\_id

&#x20;   model\_version

&#x20;   generated\_at



Prediction is not automatically a trading signal.



A strategy or decision layer must interpret it.



====================================================================

19\. STRATEGY

====================================================================



Strategy converts market context into a candidate signal.



Conceptually:



&#x20;   Market Context

&#x20;       ↓

&#x20;   Strategy

&#x20;       ↓

&#x20;   Signal



Strategy MUST NOT:



&#x20;   execute orders

&#x20;   call a broker

&#x20;   write directly to database

&#x20;   bypass risk management

&#x20;   access infrastructure directly



====================================================================

20\. RISK MANAGEMENT

====================================================================



Risk management is a mandatory gate.



Flow:



&#x20;   Signal

&#x20;       ↓

&#x20;   Order Candidate

&#x20;       ↓

&#x20;   Risk Engine

&#x20;       ↓

&#x20;   Approved / Rejected



Possible rules:



&#x20;   Maximum Position Size

&#x20;   Maximum Exposure

&#x20;   Maximum Daily Loss

&#x20;   Maximum Drawdown

&#x20;   Balance Requirement

&#x20;   Margin Requirement

&#x20;   Symbol Restrictions

&#x20;   Strategy Restrictions

&#x20;   Quantity Limits



====================================================================

21\. APPLICATION LAYER

====================================================================



Application coordinates use cases.



Examples:



&#x20;   MarketDataService

&#x20;   SignalService

&#x20;   RiskService

&#x20;   OrderService

&#x20;   ExecutionService

&#x20;   PortfolioService

&#x20;   SimulationService

&#x20;   BacktestService



Application should depend on contracts.



It should not instantiate concrete infrastructure directly.



====================================================================

22\. APPLICATION PORTS

====================================================================



Ports define external capabilities.



Examples:



&#x20;   MarketDataProvider

&#x20;   OrderExecutor

&#x20;   TradeRepository

&#x20;   PositionRepository

&#x20;   PortfolioRepository

&#x20;   MarketDataRepository

&#x20;   EventPublisher

&#x20;   Clock



Infrastructure implements these interfaces.



====================================================================

23\. INFRASTRUCTURE

====================================================================



Infrastructure contains technical implementations.



Examples:



&#x20;   SQL repositories

&#x20;   File repositories

&#x20;   HTTP market data adapters

&#x20;   Broker adapters

&#x20;   Logging implementations

&#x20;   Configuration loaders

&#x20;   Filesystem access

&#x20;   System clock



Infrastructure must translate external formats into domain objects.



====================================================================

24\. EXECUTION

====================================================================



Execution is abstracted.



Required conceptual interface:



&#x20;   submit\_order()

&#x20;   cancel\_order()

&#x20;   get\_order()

&#x20;   get\_status()



Implementations:



&#x20;   SimulatedExecution

&#x20;   PaperExecution

&#x20;   BrokerExecution



All implementations must obey the same contract.



====================================================================

25\. EXECUTION MODES

====================================================================



Supported modes:



&#x20;   SIMULATION

&#x20;   PAPER

&#x20;   LIVE



Default:



&#x20;   SIMULATION



LIVE must never be implicit.



====================================================================

26\. SIMULATION

====================================================================



Simulation is mandatory.



Simulation must provide:



&#x20;   market progression

&#x20;   current price

&#x20;   order matching

&#x20;   fills

&#x20;   fees

&#x20;   slippage

&#x20;   optional latency

&#x20;   deterministic clock



Simulation must never call a live broker.



====================================================================

27\. PAPER TRADING

====================================================================



Paper trading uses the same application pipeline as live trading.



Only the execution adapter changes.



Correct architecture:



&#x20;   Strategy

&#x20;       ↓

&#x20;   Risk

&#x20;       ↓

&#x20;   Order

&#x20;       ↓

&#x20;   Execution Port

&#x20;       ↓

&#x20;   Paper Execution



====================================================================

28\. LIVE TRADING

====================================================================



Live trading is a later capability.



It must require explicit:



&#x20;   LIVE mode

&#x20;   broker configuration

&#x20;   credentials

&#x20;   risk limits

&#x20;   order validation

&#x20;   audit logging



Live execution must never be reachable accidentally from tests.



====================================================================

29\. COMPLETE TRADING PIPELINE

====================================================================



The complete trading flow is:



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

&#x20;   Risk Engine

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

&#x20;   Events / Audit



====================================================================

30\. FEATURE ENGINEERING

====================================================================



Initial feature support should include:



&#x20;   SMA

&#x20;   EMA

&#x20;   RSI

&#x20;   MACD

&#x20;   ATR

&#x20;   Bollinger Bands



Feature calculations must be:



&#x20;   deterministic

&#x20;   testable

&#x20;   causal

&#x20;   versionable



No future data may be used.



====================================================================

31\. AI

====================================================================



AI is optional.



The system must operate without AI.



AI integration:



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



AI must never bypass:



&#x20;   Risk

&#x20;   Order validation

&#x20;   Execution contracts



====================================================================

32\. BACKTESTING

====================================================================



Backtesting is a first-class subsystem.



Input:



&#x20;   Historical Dataset

&#x20;   Strategy

&#x20;   Risk Configuration

&#x20;   Initial Capital

&#x20;   Fees

&#x20;   Slippage

&#x20;   Timeframe



Output:



&#x20;   Trades

&#x20;   Equity Curve

&#x20;   PnL

&#x20;   Returns

&#x20;   Drawdown

&#x20;   Win Rate

&#x20;   Profit Factor

&#x20;   Trade Count

&#x20;   Performance Metrics



====================================================================

33\. BACKTEST LOOP

====================================================================



&#x20;   Load Dataset

&#x20;       ↓

&#x20;   Initialize Portfolio

&#x20;       ↓

&#x20;   Initialize Strategy

&#x20;       ↓

&#x20;   Initialize Risk Engine

&#x20;       ↓

&#x20;   Initialize Simulation

&#x20;       ↓

&#x20;   For each market event:

&#x20;       ↓

&#x20;   Update Market State

&#x20;       ↓

&#x20;   Calculate Features

&#x20;       ↓

&#x20;   Evaluate Strategy

&#x20;       ↓

&#x20;   Generate Signal

&#x20;       ↓

&#x20;   Apply Risk

&#x20;       ↓

&#x20;   Create Order

&#x20;       ↓

&#x20;   Simulate Execution

&#x20;       ↓

&#x20;   Update Trade

&#x20;       ↓

&#x20;   Update Position

&#x20;       ↓

&#x20;   Update Portfolio

&#x20;       ↓

&#x20;   Record Event

&#x20;       ↓

&#x20;   Calculate Metrics

&#x20;       ↓

&#x20;   Generate Report



====================================================================

34\. LOOKAHEAD BIAS

====================================================================



Backtesting MUST prevent lookahead bias.



At timestamp T, strategy may only access information available

at or before T.



Forbidden:



&#x20;   future candle values

&#x20;   future close

&#x20;   future indicators

&#x20;   future portfolio state



====================================================================

35\. PORTFOLIO

====================================================================



Portfolio must track:



&#x20;   cash

&#x20;   equity

&#x20;   positions

&#x20;   exposure

&#x20;   unrealized PnL

&#x20;   realized PnL

&#x20;   fees

&#x20;   returns

&#x20;   drawdown



Portfolio state must be reproducible.



====================================================================

36\. PERFORMANCE METRICS

====================================================================



Minimum:



&#x20;   Total Return

&#x20;   Net PnL

&#x20;   Gross Profit

&#x20;   Gross Loss

&#x20;   Win Rate

&#x20;   Loss Rate

&#x20;   Trade Count

&#x20;   Average Trade

&#x20;   Maximum Drawdown

&#x20;   Profit Factor



Optional:



&#x20;   Sharpe Ratio

&#x20;   Sortino Ratio

&#x20;   Calmar Ratio

&#x20;   CAGR

&#x20;   Volatility



Every metric must have a documented definition.



====================================================================

37\. EVENT SYSTEM

====================================================================



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



Events should contain:



&#x20;   event\_id

&#x20;   event\_type

&#x20;   occurred\_at

&#x20;   source

&#x20;   correlation\_id

&#x20;   payload

&#x20;   metadata



====================================================================

38\. CORRELATION

====================================================================



Trading workflows must be traceable.



Example:



&#x20;   Signal

&#x20;       correlation\_id = X



&#x20;   RiskDecision

&#x20;       correlation\_id = X



&#x20;   Order

&#x20;       correlation\_id = X



&#x20;   Trade

&#x20;       correlation\_id = X



This allows complete workflow tracing.



====================================================================

39\. AUDIT

====================================================================



Important operations must be auditable.



At minimum:



&#x20;   Signal

&#x20;   Risk Decision

&#x20;   Order

&#x20;   Execution

&#x20;   Trade

&#x20;   Position Change



Audit information:



&#x20;   action

&#x20;   timestamp

&#x20;   reason

&#x20;   result

&#x20;   correlation\_id



====================================================================

40\. PERSISTENCE

====================================================================



Persistence must be abstracted.



Required repository concepts:



&#x20;   MarketDataRepository

&#x20;   OrderRepository

&#x20;   TradeRepository

&#x20;   PositionRepository

&#x20;   PortfolioRepository



Domain must not know the database technology.



====================================================================

41\. DATABASE

====================================================================



Possible database technologies:



&#x20;   SQL Server

&#x20;   PostgreSQL

&#x20;   SQLite



The architecture must not depend on one database.



Possible tables:



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



====================================================================

42\. CONFIGURATION

====================================================================



Recommended:



&#x20;   configs/

&#x20;       development.yaml

&#x20;       test.yaml

&#x20;       simulation.yaml

&#x20;       paper.yaml

&#x20;       production.yaml



Secrets must come from:



&#x20;   environment variables



or:



&#x20;   secure secret management



Never commit secrets.



====================================================================

43\. LOGGING

====================================================================



Major operations should log:



&#x20;   start

&#x20;   completion

&#x20;   failure

&#x20;   duration



Trading logs should include where applicable:



&#x20;   order\_id

&#x20;   symbol

&#x20;   strategy\_id

&#x20;   account\_id

&#x20;   correlation\_id



Never log:



&#x20;   passwords

&#x20;   API keys

&#x20;   broker secrets

&#x20;   tokens



====================================================================

44\. CLOCK

====================================================================



Time should be abstracted.



Required conceptual implementations:



&#x20;   SystemClock

&#x20;   FixedClock

&#x20;   SimulationClock



Backtesting must use SimulationClock.



====================================================================

45\. DETERMINISM

====================================================================



Simulation and backtesting must be deterministic.



Given the same:



&#x20;   Dataset

&#x20;   Strategy

&#x20;   Configuration

&#x20;   Starting Capital

&#x20;   Fees

&#x20;   Slippage

&#x20;   Seed



the system must produce equivalent results.



====================================================================

46\. RANDOMNESS

====================================================================



If randomness is required:



&#x20;   use an explicit seed.



Never use uncontrolled randomness in deterministic tests.



====================================================================

47\. DATA

====================================================================



Market dataset minimum fields:



&#x20;   timestamp

&#x20;   symbol

&#x20;   timeframe

&#x20;   open

&#x20;   high

&#x20;   low

&#x20;   close

&#x20;   volume



Supported storage formats may include:



&#x20;   CSV

&#x20;   Parquet

&#x20;   Database



The domain must not depend on the storage format.



====================================================================

48\. DATA VALIDATION

====================================================================



Validate:



&#x20;   timestamp

&#x20;   symbol

&#x20;   timeframe

&#x20;   OHLC

&#x20;   volume

&#x20;   chronological ordering

&#x20;   duplicates

&#x20;   missing values



Invalid data must be rejected or explicitly quarantined.



====================================================================

49\. TESTING

====================================================================



Testing is a mandatory architectural component.



Structure:



&#x20;   tests/

&#x20;       unit/

&#x20;       integration/

&#x20;       contract/

&#x20;       simulation/

&#x20;       backtesting/

&#x20;       architecture/

&#x20;       e2e/



====================================================================

50\. UNIT TESTS

====================================================================



Unit tests must cover:



&#x20;   Value Objects

&#x20;   Domain Entities

&#x20;   Order lifecycle

&#x20;   Position lifecycle

&#x20;   Risk rules

&#x20;   Strategy calculations

&#x20;   Features

&#x20;   Portfolio calculations

&#x20;   Metrics



====================================================================

51\. INTEGRATION TESTS

====================================================================



Integration tests must cover:



&#x20;   Application + Domain

&#x20;   Repository implementations

&#x20;   Event system

&#x20;   Market data adapters

&#x20;   Execution adapters

&#x20;   Persistence



====================================================================

52\. CONTRACT TESTS

====================================================================



All implementations of:



&#x20;   MarketDataProvider

&#x20;   OrderExecutor

&#x20;   Repositories

&#x20;   EventPublisher



must pass the corresponding contract tests.



====================================================================

53\. SIMULATION TESTS

====================================================================



Must verify:



&#x20;   market progression

&#x20;   market order fill

&#x20;   limit order fill

&#x20;   rejected order

&#x20;   partial fill

&#x20;   fees

&#x20;   slippage

&#x20;   position creation

&#x20;   position reduction

&#x20;   position closure

&#x20;   PnL

&#x20;   portfolio updates



====================================================================

54\. BACKTEST TESTS

====================================================================



Must verify:



&#x20;   deterministic output

&#x20;   chronological execution

&#x20;   no lookahead bias

&#x20;   correct PnL

&#x20;   correct fees

&#x20;   correct drawdown

&#x20;   correct trade sequence



====================================================================

55\. ARCHITECTURE TESTS

====================================================================



Architecture tests must prevent:



&#x20;   Domain → Infrastructure



&#x20;   Domain → Broker SDK



&#x20;   Domain → Database Driver



&#x20;   Domain → CLI



&#x20;   Application → Concrete Broker



&#x20;   Circular Dependencies



====================================================================

56\. QUALITY GATE

====================================================================



Every implementation milestone must pass:



&#x20;   python -m ruff check .



&#x20;   python -m black .



&#x20;   python -m mypy src



&#x20;   python -m pytest



No milestone is complete while the quality gate is red.



====================================================================

57\. CODE QUALITY

====================================================================



Required:



&#x20;   Type annotations

&#x20;   Explicit contracts

&#x20;   Clear names

&#x20;   Small cohesive classes

&#x20;   Small cohesive functions

&#x20;   Dependency injection

&#x20;   Deterministic tests

&#x20;   Proper error handling



Forbidden:



&#x20;   giant classes

&#x20;   giant functions

&#x20;   global mutable state

&#x20;   hidden dependencies

&#x20;   duplicated business logic

&#x20;   magic numbers

&#x20;   dead code

&#x20;   fake implementations



====================================================================

58\. NO PLACEHOLDER CODE

====================================================================



Do NOT use:



&#x20;   pass



as a substitute for implementation.



Do NOT use:



&#x20;   fake return values



Do NOT use:



&#x20;   hardcoded successful results



Do NOT leave:



&#x20;   NotImplementedError



in required production paths.



If a capability is intentionally not available yet:



&#x20;   define the contract

&#x20;   document the limitation

&#x20;   fail explicitly and safely



====================================================================

59\. ERROR HANDLING

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



Business failures should not be represented only by generic

exceptions.



====================================================================

60\. ORDER SAFETY

====================================================================



Order execution must be protected by:



&#x20;   validation

&#x20;   risk management

&#x20;   execution mode

&#x20;   idempotency

&#x20;   audit logging



Signal must never directly invoke execution.



====================================================================

61\. IDEMPOTENCY

====================================================================



Execution operations must be idempotent.



Repeated processing of the same execution event must not create

duplicate trades.



Use:



&#x20;   event\_id



and/or:



&#x20;   execution\_id



====================================================================

62\. RETRY POLICY

====================================================================



Retries may be used for safe technical failures.



Never blindly retry a financial order submission.



Financial operations require idempotency protection.



====================================================================

63\. STARTUP

====================================================================



Startup sequence:



&#x20;   Load Configuration

&#x20;       ↓

&#x20;   Validate Configuration

&#x20;       ↓

&#x20;   Initialize Logging

&#x20;       ↓

&#x20;   Build Dependencies

&#x20;       ↓

&#x20;   Validate Infrastructure

&#x20;       ↓

&#x20;   Initialize Application

&#x20;       ↓

&#x20;   Start Runtime



====================================================================

64\. SHUTDOWN

====================================================================



Shutdown must:



&#x20;   stop new operations

&#x20;   flush events

&#x20;   persist required state

&#x20;   close repositories

&#x20;   close execution adapters

&#x20;   release resources

&#x20;   log completion



====================================================================

65\. CLI

====================================================================



Recommended commands:



&#x20;   start

&#x20;   simulate

&#x20;   backtest

&#x20;   validate

&#x20;   status



Examples:



&#x20;   python -m shadbottrader start



&#x20;   python -m shadbottrader simulate



&#x20;   python -m shadbottrader backtest



&#x20;   python -m shadbottrader validate



CLI must call Application services.



CLI must not contain business logic.



====================================================================

66\. MAIN.PY

====================================================================



main.py responsibilities:



&#x20;   Load configuration

&#x20;   Initialize application

&#x20;   Start selected runtime

&#x20;   Handle errors

&#x20;   Shutdown cleanly



main.py must remain thin.



====================================================================

67\. BOOTSTRAP

====================================================================



Bootstrap constructs:



&#x20;   Configuration

&#x20;   Logger

&#x20;   Event Bus

&#x20;   Repositories

&#x20;   Market Data Provider

&#x20;   Execution Adapter

&#x20;   Risk Service

&#x20;   Strategy Service

&#x20;   Portfolio Service

&#x20;   Runtime



Dependency construction should be centralized.



====================================================================

68\. DEPENDENCY INJECTION

====================================================================



Prefer constructor injection.



Example:



&#x20;   OrderService(

&#x20;       order\_repository,

&#x20;       risk\_service,

&#x20;       execution\_service,

&#x20;       event\_publisher

&#x20;   )



Avoid:



&#x20;   hidden service locators

&#x20;   module-level singleton state

&#x20;   direct infrastructure construction inside domain/application

&#x20;   functions that secretly access global services



====================================================================

69\. STRATEGY CONFIGURATION

====================================================================



Example:



&#x20;   strategy:

&#x20;       name: moving\_average\_cross

&#x20;       fast\_period: 20

&#x20;       slow\_period: 50



Configuration must be validated.



====================================================================

70\. RISK CONFIGURATION

====================================================================



Example conceptual configuration:



&#x20;   risk:

&#x20;       max\_position\_size: ...

&#x20;       max\_exposure: ...

&#x20;       max\_daily\_loss: ...

&#x20;       max\_drawdown: ...



No hardcoded production risk limits.



====================================================================

71\. EXECUTION CONFIGURATION

====================================================================



Execution configuration may define:



&#x20;   mode

&#x20;   fees

&#x20;   slippage

&#x20;   latency

&#x20;   broker

&#x20;   retry\_policy



====================================================================

72\. ENVIRONMENT SAFETY

====================================================================



The test environment must NEVER accidentally connect to:



&#x20;   production database

&#x20;   production broker

&#x20;   live account



Production mode must be explicitly selected.



====================================================================

73\. PROJECT INTELLIGENCE COMPATIBILITY

====================================================================



ShadBotTrader must remain easy for ShadBot Project Intelligence

to inspect.



Project Intelligence must be able to discover:



&#x20;   source files

&#x20;   packages

&#x20;   classes

&#x20;   functions

&#x20;   dependencies

&#x20;   configuration

&#x20;   Git history

&#x20;   tests

&#x20;   documentation

&#x20;   TODOs

&#x20;   statistics

&#x20;   architecture



Avoid excessive dynamic code that makes static inspection difficult.



====================================================================

74\. GENERATED PROJECT KNOWLEDGE

====================================================================



The project should eventually be compatible with generated:



&#x20;   ProjectSnapshot

&#x20;   ProjectSnapshot.json

&#x20;   ChatGPT\_Context.md

&#x20;   Architecture.md

&#x20;   Roadmap.md

&#x20;   Decisions.md

&#x20;   Todo.md

&#x20;   Statistics.json

&#x20;   DependencyGraph.json



These artifacts are generated knowledge, not the primary source

code.



====================================================================

75\. DOCUMENTATION

====================================================================



Required documentation:



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



Documentation must describe actual behavior.



Documentation must be updated when architecture changes.



====================================================================

76\. PROJECT METADATA

====================================================================



The application should expose:



&#x20;   project\_name

&#x20;   version

&#x20;   environment

&#x20;   build\_version

&#x20;   git\_commit

&#x20;   execution\_mode



====================================================================

77\. VERSIONING

====================================================================



Application versions should use:



&#x20;   MAJOR.MINOR.PATCH



Architecture version is separate.



====================================================================

78\. DEVELOPMENT ROADMAP

====================================================================



Implementation must proceed in dependency order.



\------------------------------------------------------------

MILESTONE 01

\------------------------------------------------------------



Repository foundation.



Implement:



&#x20;   package structure

&#x20;   main entry point

&#x20;   tests structure

&#x20;   tooling

&#x20;   configuration foundation



\------------------------------------------------------------

MILESTONE 02

\------------------------------------------------------------



Core abstractions.



Implement:



&#x20;   Result

&#x20;   Errors

&#x20;   Events

&#x20;   Lifecycle

&#x20;   Logging

&#x20;   Types



\------------------------------------------------------------

MILESTONE 03

\------------------------------------------------------------



Domain Common.



Implement:



&#x20;   Entity

&#x20;   ValueObject

&#x20;   IDs

&#x20;   timestamps

&#x20;   shared domain rules



\------------------------------------------------------------

MILESTONE 04

\------------------------------------------------------------



Market Domain.



Implement:



&#x20;   Symbol

&#x20;   TimeFrame

&#x20;   Price

&#x20;   Candle

&#x20;   MarketData



\------------------------------------------------------------

MILESTONE 05

\------------------------------------------------------------



Trading Domain.



Implement:



&#x20;   Order

&#x20;   OrderSide

&#x20;   OrderType

&#x20;   Trade

&#x20;   Position



\------------------------------------------------------------

MILESTONE 06

\------------------------------------------------------------



Portfolio Domain.



Implement:



&#x20;   Account

&#x20;   Balance

&#x20;   Portfolio

&#x20;   PnL

&#x20;   Equity



\------------------------------------------------------------

MILESTONE 07

\------------------------------------------------------------



Risk Domain.



Implement:



&#x20;   RiskDecision

&#x20;   RiskRule

&#x20;   RiskEngine



\------------------------------------------------------------

MILESTONE 08

\------------------------------------------------------------



Application Contracts.



Implement:



&#x20;   MarketDataProvider

&#x20;   OrderExecutor

&#x20;   Repositories

&#x20;   EventPublisher

&#x20;   Clock



\------------------------------------------------------------

MILESTONE 09

\------------------------------------------------------------



Application Services.



Implement:



&#x20;   MarketDataService

&#x20;   SignalService

&#x20;   RiskService

&#x20;   OrderService

&#x20;   ExecutionService

&#x20;   PortfolioService



\------------------------------------------------------------

MILESTONE 10

\------------------------------------------------------------



In-memory infrastructure.



Implement:



&#x20;   in-memory repositories

&#x20;   in-memory event publisher

&#x20;   test market provider



\------------------------------------------------------------

MILESTONE 11

\------------------------------------------------------------



Simulation.



Implement:



&#x20;   SimulationClock

&#x20;   MarketSimulator

&#x20;   SimulatedExecution



\------------------------------------------------------------

MILESTONE 12

\------------------------------------------------------------



Strategy Framework.



Implement:



&#x20;   Strategy contract

&#x20;   Strategy registry

&#x20;   Strategy lifecycle



\------------------------------------------------------------

MILESTONE 13

\------------------------------------------------------------



First Strategy.



Implement:



&#x20;   MovingAverageCrossStrategy



It must be deterministic.



\------------------------------------------------------------

MILESTONE 14

\------------------------------------------------------------



Complete Simulation.



The following must work:



&#x20;   Market Data

&#x20;       ↓

&#x20;   Strategy

&#x20;       ↓

&#x20;   Signal

&#x20;       ↓

&#x20;   Risk

&#x20;       ↓

&#x20;   Order

&#x20;       ↓

&#x20;   Simulation

&#x20;       ↓

&#x20;   Trade

&#x20;       ↓

&#x20;   Position

&#x20;       ↓

&#x20;   Portfolio



\------------------------------------------------------------

MILESTONE 15

\------------------------------------------------------------



Backtesting.



Implement:



&#x20;   BacktestEngine

&#x20;   BacktestResult

&#x20;   Metrics

&#x20;   Equity Curve

&#x20;   Report



\------------------------------------------------------------

MILESTONE 16

\------------------------------------------------------------



Persistence.



Implement repository adapters.



\------------------------------------------------------------

MILESTONE 17

\------------------------------------------------------------



Event Infrastructure.



Implement event persistence / dispatching where required.



\------------------------------------------------------------

MILESTONE 18

\------------------------------------------------------------



Configuration System.



Implement:



&#x20;   YAML configuration

&#x20;   environment overrides

&#x20;   validation

&#x20;   mode separation



\------------------------------------------------------------

MILESTONE 19

\------------------------------------------------------------



CLI.



Implement:



&#x20;   start

&#x20;   simulate

&#x20;   backtest

&#x20;   validate

&#x20;   status



\------------------------------------------------------------

MILESTONE 20

\------------------------------------------------------------



Architecture Tests.



Enforce dependency rules automatically.



\------------------------------------------------------------

MILESTONE 21

\------------------------------------------------------------



Project Intelligence Compatibility.



Ensure the project can be fully scanned and understood.



\------------------------------------------------------------

MILESTONE 22

\------------------------------------------------------------



Paper Execution.



Implement safe paper execution adapter.



\------------------------------------------------------------

MILESTONE 23

\------------------------------------------------------------



Broker Adapter.



Implement broker integration through OrderExecutor.



\------------------------------------------------------------

MILESTONE 24

\------------------------------------------------------------



Production Hardening.



Implement:



&#x20;   audit

&#x20;   observability

&#x20;   reliability

&#x20;   idempotency

&#x20;   recovery

&#x20;   operational safeguards



====================================================================

79\. FIRST END-TO-END DEMO

====================================================================



Before implementing live broker integration, the project must

demonstrate:



&#x20;   1. Load deterministic market data.



&#x20;   2. Initialize strategy.



&#x20;   3. Calculate features.



&#x20;   4. Generate signal.



&#x20;   5. Apply risk.



&#x20;   6. Create order.



&#x20;   7. Execute simulated order.



&#x20;   8. Record trade.



&#x20;   9. Update position.



&#x20;   10. Update portfolio.



&#x20;   11. Calculate PnL.



&#x20;   12. Generate final metrics.



This demo must work without external services.



====================================================================

80\. EXAMPLE FINAL FLOW

====================================================================



Example:



&#x20;   EURUSD

&#x20;       |

&#x20;       v

&#x20;   Historical Candles

&#x20;       |

&#x20;       v

&#x20;   Data Validation

&#x20;       |

&#x20;       v

&#x20;   SMA(20)

&#x20;   SMA(50)

&#x20;       |

&#x20;       v

&#x20;   Moving Average Cross

&#x20;       |

&#x20;       v

&#x20;   BUY Signal

&#x20;       |

&#x20;       v

&#x20;   Risk Engine

&#x20;       |

&#x20;       v

&#x20;   APPROVED

&#x20;       |

&#x20;       v

&#x20;   BUY Order

&#x20;       |

&#x20;       v

&#x20;   Simulated Execution

&#x20;       |

&#x20;       v

&#x20;   Trade

&#x20;       |

&#x20;       v

&#x20;   Long Position

&#x20;       |

&#x20;       v

&#x20;   Portfolio

&#x20;       |

&#x20;       v

&#x20;   PnL / Equity / Drawdown



====================================================================

81\. FAILURE SCENARIOS

====================================================================



The application must correctly handle:



&#x20;   invalid configuration

&#x20;   invalid symbol

&#x20;   invalid timeframe

&#x20;   invalid candle

&#x20;   missing market data

&#x20;   duplicate market data

&#x20;   invalid quantity

&#x20;   insufficient balance

&#x20;   excessive exposure

&#x20;   risk rejection

&#x20;   invalid order transition

&#x20;   execution failure

&#x20;   persistence failure

&#x20;   strategy failure

&#x20;   event failure



Failures must be observable and testable.



====================================================================

82\. REPRODUCIBILITY

====================================================================



Every backtest should record:



&#x20;   dataset identifier

&#x20;   dataset version

&#x20;   strategy identifier

&#x20;   strategy version

&#x20;   configuration

&#x20;   starting capital

&#x20;   fees

&#x20;   slippage

&#x20;   execution mode

&#x20;   application version

&#x20;   Git commit

&#x20;   execution timestamp



====================================================================

83\. BACKTEST REPORT

====================================================================



Report should contain:



&#x20;   Summary

&#x20;   Dataset

&#x20;   Configuration

&#x20;   Strategy

&#x20;   Risk Configuration

&#x20;   Execution Configuration

&#x20;   Trades

&#x20;   Equity Curve

&#x20;   Metrics

&#x20;   Drawdown

&#x20;   Warnings

&#x20;   Errors



====================================================================

84\. SIMULATION REPORT

====================================================================



Simulation report should contain:



&#x20;   Start

&#x20;   End

&#x20;   Initial Balance

&#x20;   Final Balance

&#x20;   Trades

&#x20;   Positions

&#x20;   Realized PnL

&#x20;   Unrealized PnL

&#x20;   Fees

&#x20;   Drawdown

&#x20;   Execution Statistics



====================================================================

85\. GIT WORKFLOW

====================================================================



Before committing:



&#x20;   git status



&#x20;   git diff



&#x20;   python -m ruff check .



&#x20;   python -m black .



&#x20;   python -m mypy src



&#x20;   python -m pytest



Then:



&#x20;   git add .



&#x20;   git commit -m "Meaningful implementation message"



Each commit should represent one coherent change.



====================================================================

86\. BRANCHING

====================================================================



Recommended branches:



&#x20;   main



&#x20;   feature/domain

&#x20;   feature/risk

&#x20;   feature/simulation

&#x20;   feature/backtesting

&#x20;   feature/persistence

&#x20;   feature/execution



Do not merge failing work.



====================================================================

87\. DEFINITION OF DONE

====================================================================



A feature is DONE only when:



&#x20;   implementation exists

&#x20;   contracts exist

&#x20;   types exist

&#x20;   tests exist

&#x20;   error handling exists

&#x20;   logging exists where necessary

&#x20;   documentation exists

&#x20;   Ruff passes

&#x20;   Black passes

&#x20;   Mypy passes

&#x20;   Pytest passes

&#x20;   architecture checks pass

&#x20;   runtime verification succeeds

&#x20;   Git commit exists



====================================================================

88\. AGENT RULES

====================================================================



Any coding agent working on this repository MUST:



&#x20;   inspect the workspace first



&#x20;   inspect existing code before changing it



&#x20;   understand the current architecture



&#x20;   identify the current milestone



&#x20;   implement only the required scope



&#x20;   preserve valid existing contracts



&#x20;   write tests



&#x20;   run the quality gate



&#x20;   fix all failures



&#x20;   update documentation



&#x20;   update project state



&#x20;   commit completed work



====================================================================

89\. AGENT MUST NOT

====================================================================



The coding agent MUST NOT:



&#x20;   redesign the architecture without approval



&#x20;   invent new requirements



&#x20;   duplicate existing domain concepts



&#x20;   put business logic in infrastructure



&#x20;   put business logic in CLI



&#x20;   bypass risk management



&#x20;   allow signals to execute orders



&#x20;   allow AI to bypass risk



&#x20;   allow simulation to access live execution



&#x20;   introduce hidden global state



&#x20;   commit secrets



&#x20;   use placeholder implementations



&#x20;   ignore failing tests



&#x20;   ignore typing errors



&#x20;   silently change architectural decisions



====================================================================

90\. SECURITY

====================================================================



Never commit:



&#x20;   API keys

&#x20;   passwords

&#x20;   broker credentials

&#x20;   access tokens

&#x20;   database passwords

&#x20;   private secrets



Use:



&#x20;   .env



or:



&#x20;   environment variables



or:



&#x20;   secure secret management



====================================================================

91\. LIVE TRADING SAFETY

====================================================================



The default execution mode MUST be:



&#x20;   SIMULATION



LIVE must require explicit configuration.



No test may execute a live order.



No development command should silently activate LIVE mode.



====================================================================

92\. ARCHITECTURAL INVARIANTS

====================================================================



The following are permanent rules:



&#x20;   Domain remains independent.



&#x20;   Signals do not execute orders.



&#x20;   Risk is mandatory.



&#x20;   Execution is abstracted.



&#x20;   Simulation is isolated from live trading.



&#x20;   Backtesting is deterministic.



&#x20;   AI is optional.



&#x20;   Persistence is abstracted.



&#x20;   External providers are adapters.



&#x20;   Configuration is externalized.



&#x20;   Tests are mandatory.



&#x20;   Architecture is enforced automatically.



====================================================================

93\. EXPECTED FINAL CAPABILITY

====================================================================



At completion, a developer should be able to run:



&#x20;   python -m shadbottrader simulate



and execute a complete deterministic trading workflow.



The developer should also be able to run:



&#x20;   python -m shadbottrader backtest



and receive a reproducible backtest report.



The system should later support:



&#x20;   python -m shadbottrader start



with explicit:



&#x20;   SIMULATION

&#x20;   PAPER

&#x20;   LIVE



configuration.



====================================================================

94\. PROJECT INTELLIGENCE TARGET

====================================================================



The project must be complex enough to serve as a realistic

Project Intelligence test target.



ShadBot Project Intelligence should be able to discover:



&#x20;   package tree

&#x20;   classes

&#x20;   functions

&#x20;   dependencies

&#x20;   domain model

&#x20;   application services

&#x20;   infrastructure adapters

&#x20;   tests

&#x20;   Git history

&#x20;   configuration

&#x20;   roadmap

&#x20;   TODOs

&#x20;   architecture

&#x20;   statistics



The project must therefore favor explicit, statically inspectable

Python code.



====================================================================

95\. EXPECTED PROJECT KNOWLEDGE

====================================================================



The project should eventually generate:



&#x20;   ProjectSnapshot.md



&#x20;   ProjectSnapshot.json



&#x20;   ChatGPT\_Context.md



&#x20;   Architecture.md



&#x20;   Roadmap.md



&#x20;   Decisions.md



&#x20;   Todo.md



&#x20;   Statistics.json



&#x20;   DependencyGraph.json



These artifacts allow an external AI agent to understand the

current state of the project without reading every source file

manually.



====================================================================

96\. IMPLEMENTATION PHILOSOPHY

====================================================================



Build from the inside out:



&#x20;   Domain

&#x20;       ↓

&#x20;   Application Contracts

&#x20;       ↓

&#x20;   Application Services

&#x20;       ↓

&#x20;   Infrastructure

&#x20;       ↓

&#x20;   Simulation

&#x20;       ↓

&#x20;   Backtesting

&#x20;       ↓

&#x20;   Interfaces

&#x20;       ↓

&#x20;   Production Integrations



Do not start with:



&#x20;   GUI

&#x20;   Broker API

&#x20;   AI model

&#x20;   Production database



before the core trading model is stable.



====================================================================

97\. WHY SIMULATION COMES FIRST

====================================================================



Simulation provides a safe environment for validating:



&#x20;   Order lifecycle

&#x20;   Execution

&#x20;   Risk

&#x20;   Position management

&#x20;   Portfolio accounting

&#x20;   Strategy behavior

&#x20;   PnL

&#x20;   Fees

&#x20;   Slippage



Only after this works should external execution be trusted.



====================================================================

98\. WHY BACKTESTING COMES BEFORE LIVE

====================================================================



A strategy must demonstrate deterministic behavior in historical

data before it is considered eligible for paper or live execution.



Backtesting does NOT prove profitability.



It proves that the system behaves according to its defined

methodology.



====================================================================

99\. PROFITABILITY DISCLAIMER

====================================================================



ShadBotTrader does not guarantee profitability.



Backtest performance is not proof of future performance.



The software must prioritize:



&#x20;   correctness

&#x20;   risk control

&#x20;   reproducibility

&#x20;   transparency



over claims of profitability.



====================================================================

100\. FINAL SYSTEM GRAPH

====================================================================



&#x20;                   +----------------+

&#x20;                   |  MARKET DATA   |

&#x20;                   +-------+--------+

&#x20;                           |

&#x20;                           v

&#x20;                   +---------------+

&#x20;                   |  VALIDATION   |

&#x20;                   +-------+-------+

&#x20;                           |

&#x20;                           v

&#x20;                   +---------------+

&#x20;                   |   FEATURES    |

&#x20;                   +-------+-------+

&#x20;                           |

&#x20;                           v

&#x20;                   +---------------+

&#x20;                   | STRATEGY / AI |

&#x20;                   +-------+-------+

&#x20;                           |

&#x20;                           v

&#x20;                   +---------------+

&#x20;                   |    SIGNAL     |

&#x20;                   +-------+-------+

&#x20;                           |

&#x20;                           v

&#x20;                   +---------------+

&#x20;                   |     RISK      |

&#x20;                   +-------+-------+

&#x20;                      /          \\

&#x20;                     /            \\

&#x20;                REJECT            APPROVE

&#x20;                  |                  |

&#x20;                  v                  v

&#x20;               AUDIT              ORDER

&#x20;                                     |

&#x20;                                     v

&#x20;                             +---------------+

&#x20;                             | EXECUTION PORT|

&#x20;                             +-------+-------+

&#x20;                                     |

&#x20;                      +--------------+--------------+

&#x20;                      |              |              |

&#x20;                      v              v              v

&#x20;                 SIMULATION        PAPER          LIVE

&#x20;                      |              |              |

&#x20;                      +--------------+--------------+

&#x20;                                     |

&#x20;                                     v

&#x20;                                  TRADE

&#x20;                                     |

&#x20;                                     v

&#x20;                                 POSITION

&#x20;                                     |

&#x20;                                     v

&#x20;                                 PORTFOLIO

&#x20;                                     |

&#x20;                                     v

&#x20;                                 METRICS

&#x20;                                     |

&#x20;                                     v

&#x20;                             EVENTS / AUDIT



====================================================================

101\. FINAL ACCEPTANCE CHECKLIST

====================================================================



&#x20;   \[ ] Repository structure exists.



&#x20;   \[ ] Application starts.



&#x20;   \[ ] Configuration loads.



&#x20;   \[ ] Configuration validates.



&#x20;   \[ ] Core abstractions exist.



&#x20;   \[ ] Domain model exists.



&#x20;   \[ ] Market model works.



&#x20;   \[ ] Trading model works.



&#x20;   \[ ] Portfolio model works.



&#x20;   \[ ] Risk engine works.



&#x20;   \[ ] Application services work.



&#x20;   \[ ] Market data abstraction works.



&#x20;   \[ ] Execution abstraction works.



&#x20;   \[ ] In-memory infrastructure works.



&#x20;   \[ ] Simulation works.



&#x20;   \[ ] Strategy framework works.



&#x20;   \[ ] At least one strategy works.



&#x20;   \[ ] End-to-end simulation works.



&#x20;   \[ ] Backtesting works.



&#x20;   \[ ] Metrics work.



&#x20;   \[ ] Persistence works.



&#x20;   \[ ] Events work.



&#x20;   \[ ] Configuration environments work.



&#x20;   \[ ] CLI works.



&#x20;   \[ ] Architecture tests work.



&#x20;   \[ ] Project Intelligence can inspect the project.



&#x20;   \[ ] Paper execution works.



&#x20;   \[ ] Broker abstraction exists.



&#x20;   \[ ] Production safeguards exist.



&#x20;   \[ ] Documentation is complete.



&#x20;   \[ ] No secrets are committed.



&#x20;   \[ ] No placeholder implementation remains.



&#x20;   \[ ] Ruff passes.



&#x20;   \[ ] Black passes.



&#x20;   \[ ] Mypy passes.



&#x20;   \[ ] Pytest passes.



====================================================================

102\. FINAL DEFINITION OF SHADBOTTRADER

====================================================================



ShadBotTrader is a modular enterprise trading runtime designed

around explicit domain models, deterministic simulation,

backtesting, strict risk management, abstract execution,

portfolio accounting, persistence, event processing and strong

automated testing.



Its architecture deliberately separates:



&#x20;   WHAT THE SYSTEM MEANS

&#x20;       =

&#x20;   DOMAIN



from:



&#x20;   WHAT THE SYSTEM DOES

&#x20;       =

&#x20;   APPLICATION



from:



&#x20;   HOW EXTERNAL SYSTEMS ARE ACCESSED

&#x20;       =

&#x20;   INFRASTRUCTURE



and:



&#x20;   HOW TRADING IS SAFELY TESTED

&#x20;       =

&#x20;   SIMULATION / BACKTESTING



The final system must be understandable by:



&#x20;   Human Developers

&#x20;   Coding Agents

&#x20;   ShadBot Project Intelligence

&#x20;   Future AI Agents



without requiring the architecture to be reverse-engineered from

implementation details.



====================================================================

103\. FINAL IMPLEMENTATION COMMAND

====================================================================



When a coding agent receives this README together with:



&#x20;   SHADBOTTRADER\_MASTER\_IMPLEMENTATION\_SPECIFICATION

&#x20;   ARCHITECTURE\_HANDOFF

&#x20;   DATA\_FLOW\_DOCUMENTATION

&#x20;   DEVELOPMENT\_RULES

&#x20;   EXECUTION\_GUIDE

&#x20;   Handoff



it must treat those documents as the project's implementation

contract.



The agent must:



&#x20;   READ ALL DOCUMENTATION



&#x20;       ↓



&#x20;   INSPECT ACTUAL WORKSPACE



&#x20;       ↓



&#x20;   DETERMINE CURRENT IMPLEMENTATION STATE



&#x20;       ↓



&#x20;   IDENTIFY FIRST INCOMPLETE MILESTONE



&#x20;       ↓



&#x20;   IMPLEMENT THAT MILESTONE



&#x20;       ↓



&#x20;   WRITE TESTS



&#x20;       ↓



&#x20;   RUN QUALITY GATE



&#x20;       ↓



&#x20;   FIX FAILURES



&#x20;       ↓



&#x20;   VERIFY RUNTIME



&#x20;       ↓



&#x20;   UPDATE DOCUMENTATION



&#x20;       ↓



&#x20;   UPDATE PROJECT STATE



&#x20;       ↓



&#x20;   COMMIT



&#x20;       ↓



&#x20;   CONTINUE TO NEXT MILESTONE



====================================================================

END OF README

====================================================================

