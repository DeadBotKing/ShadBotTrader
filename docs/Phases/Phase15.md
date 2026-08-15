================================================================================

SHADBOT

ENTERPRISE AI TRADING PLATFORM

================================================================================



PHASE 15 — PORTFOLIO PLATFORM ARCHITECTURE

================================================================================



STATUS:

&#x20;   ARCHITECTURE DESIGN



DEPENDS ON:

&#x20;   Phase 01 — Architecture Principles

&#x20;   Phase 02 — Dependency Rules

&#x20;   Phase 03 — Domain Model

&#x20;   Phase 04 — Project Tree

&#x20;   Phase 05 — Framework Design

&#x20;   Phase 06 — Pipeline Design

&#x20;   Phase 07 — Engine Design

&#x20;   Phase 08 — Service Design

&#x20;   Phase 09 — Plugin Architecture

&#x20;   Phase 10 — Event Bus

&#x20;   Phase 11 — Data Platform

&#x20;   Phase 12 — Feature Platform

&#x20;   Phase 13 — AI Platform

&#x20;   Phase 14 — Trading Platform



================================================================================

1\. PURPOSE

================================================================================



Portfolio Platform مالک وضعیت مالی و سرمایه‌ای سیستم است.



مسئول مدیریت:



&#x20;   Account

&#x20;   Balance

&#x20;   Equity

&#x20;   Cash

&#x20;   Margin

&#x20;   Exposure

&#x20;   Position

&#x20;   Portfolio

&#x20;   PnL

&#x20;   Realized PnL

&#x20;   Unrealized PnL

&#x20;   Fees

&#x20;   Funding

&#x20;   Capital Allocation

&#x20;   Portfolio Constraints

&#x20;   Portfolio Valuation

&#x20;   Performance Metrics

&#x20;   Portfolio History



================================================================================

2\. CORE BOUNDARY

================================================================================



Trading Platform:



&#x20;   تصمیم می‌گیرد چه معامله‌ای باید انجام شود.



Execution Platform:



&#x20;   معامله را اجرا می‌کند.



Portfolio Platform:



&#x20;   نتیجه اجرای معامله را به وضعیت مالی و Position تبدیل می‌کند.



Flow:



&#x20;   Trading Intent

&#x20;         |

&#x20;         v

&#x20;   Execution

&#x20;         |

&#x20;         v

&#x20;   Execution Result

&#x20;         |

&#x20;         v

&#x20;   Portfolio

&#x20;         |

&#x20;         v

&#x20;   Position / Balance / PnL / Equity



================================================================================

3\. PORTFOLIO IS NOT TRADING

================================================================================



Trading:



&#x20;   "Should we trade?"



Portfolio:



&#x20;   "What do we currently own and what is our financial state?"



================================================================================

4\. PORTFOLIO IS NOT EXECUTION

================================================================================



Execution:



&#x20;   "What happened at broker/exchange?"



Portfolio:



&#x20;   "What does that execution mean for our financial state?"



================================================================================

5\. CORE ENTITIES

================================================================================



&#x20;   Portfolio

&#x20;   Account

&#x20;   Position

&#x20;   Balance

&#x20;   AssetBalance

&#x20;   Transaction

&#x20;   Fill

&#x20;   Cost

&#x20;   Fee

&#x20;   PnLRecord

&#x20;   EquitySnapshot

&#x20;   Exposure

&#x20;   Allocation



================================================================================

6\. PORTFOLIO

================================================================================



Portfolio aggregate root.



شامل:



&#x20;   portfolio\_id

&#x20;   account\_id

&#x20;   base\_currency

&#x20;   status

&#x20;   positions

&#x20;   balances

&#x20;   valuation

&#x20;   constraints



================================================================================

7\. ACCOUNT

================================================================================



Account نماینده حساب معاملاتی است.



شامل:



&#x20;   account\_id

&#x20;   broker\_account\_id

&#x20;   account\_type

&#x20;   base\_currency

&#x20;   status

&#x20;   permissions



Portfolio می‌تواند به یک Account وابسته باشد.



================================================================================

8\. ACCOUNT STATUS

================================================================================



&#x20;   ACTIVE

&#x20;   DISABLED

&#x20;   SUSPENDED

&#x20;   CLOSED

&#x20;   READ\_ONLY



================================================================================

9\. BALANCE

================================================================================



Balance وضعیت یک Asset/Currency را نگه می‌دارد.



مثلاً:



&#x20;   USD

&#x20;   EUR

&#x20;   USDT

&#x20;   XAU



================================================================================

10\. BALANCE COMPONENTS

================================================================================



Balance:



&#x20;   total

&#x20;   available

&#x20;   reserved

&#x20;   locked



Invariant:



&#x20;   available + reserved + locked

&#x20;   must follow account-specific accounting rules.



================================================================================

11\. CASH

================================================================================



Cash سرمایه نقدشونده است.



مثال:



&#x20;   USD Cash

&#x20;   EUR Cash



Cash بخشی از Portfolio Valuation است.



================================================================================

12\. EQUITY

================================================================================



Equity:



&#x20;   Cash

&#x20;   +

&#x20;   Unrealized PnL

&#x20;   +

&#x20;   Other Valuation Components



فرمول دقیق بر اساس Account Model تعریف می‌شود.



================================================================================

13\. POSITION

================================================================================



Position نماینده Exposure روی یک Instrument است.



شامل:



&#x20;   position\_id

&#x20;   portfolio\_id

&#x20;   symbol

&#x20;   side

&#x20;   quantity

&#x20;   average\_entry\_price

&#x20;   current\_price

&#x20;   realized\_pnl

&#x20;   unrealized\_pnl

&#x20;   fees

&#x20;   opened\_at

&#x20;   updated\_at



================================================================================

14\. POSITION SIDE

================================================================================



&#x20;   LONG

&#x20;   SHORT

&#x20;   FLAT



================================================================================

15\. POSITION QUANTITY

================================================================================



Quantity باید:



&#x20;   Decimal



باشد.



استفاده از float برای financial accounting ممنوع.



================================================================================

16\. PRICE

================================================================================



Price در accounting باید با precision مناسب بازار ذخیره شود.



نوع عددی:



&#x20;   Decimal



================================================================================

17\. MONEY

================================================================================



تمام مقادیر مالی:



&#x20;   Money



Value Object دارند.



شامل:



&#x20;   amount

&#x20;   currency



================================================================================

18\. CURRENCY

================================================================================



Currency باید Value Object یا استاندارد مرکزی باشد.



مثال:



&#x20;   USD

&#x20;   EUR

&#x20;   GBP

&#x20;   USDT



================================================================================

19\. TRANSACTION

================================================================================



هر تغییر مالی باید قابل ردیابی باشد.



Transaction:



&#x20;   transaction\_id

&#x20;   account\_id

&#x20;   timestamp

&#x20;   type

&#x20;   amount

&#x20;   currency

&#x20;   reference



================================================================================

20\. TRANSACTION TYPES

================================================================================



&#x20;   DEPOSIT

&#x20;   WITHDRAWAL

&#x20;   TRADE

&#x20;   FEE

&#x20;   FUNDING

&#x20;   INTEREST

&#x20;   ADJUSTMENT

&#x20;   TRANSFER



================================================================================

21\. EXECUTION RESULT

================================================================================



Portfolio Execution Result را مصرف می‌کند.



مثال:



&#x20;   Fill

&#x20;   quantity

&#x20;   price

&#x20;   fee

&#x20;   currency

&#x20;   timestamp



Portfolio نباید فرض کند Order حتماً کامل اجرا شده است.



================================================================================

22\. FILL

================================================================================



یک Order می‌تواند چند Fill داشته باشد.



مثال:



&#x20;   Order 100 units



&#x20;   Fill 40

&#x20;   Fill 30

&#x20;   Fill 30



Portfolio باید همه Fillها را aggregate کند.



================================================================================

23\. PARTIAL FILL

================================================================================



Partial Fill باید native باشد.



مثلاً:



&#x20;   ordered = 100

&#x20;   filled = 40

&#x20;   remaining = 60



================================================================================

24\. AVERAGE ENTRY PRICE

================================================================================



Average Entry Price بر اساس Fillهای واقعی محاسبه می‌شود.



نباید از:



&#x20;   Trading Intent



محاسبه شود.



================================================================================

25\. REALIZED PNL

================================================================================



Realized PnL زمانی ثبت می‌شود که Position کاهش یا بسته شود.



محاسبه باید:



&#x20;   Fill-based



باشد.



================================================================================

26\. UNREALIZED PNL

================================================================================



Unrealized PnL بر اساس:



&#x20;   Current Market Price

&#x20;   Position Quantity

&#x20;   Entry Cost



محاسبه می‌شود.



================================================================================

27\. PNL

================================================================================



Portfolio باید تفکیک کند:



&#x20;   Gross PnL

&#x20;   Net PnL

&#x20;   Realized PnL

&#x20;   Unrealized PnL

&#x20;   Fees

&#x20;   Funding

&#x20;   Other Costs



================================================================================

28\. FEES

================================================================================



Fee باید مستقل ثبت شود.



مثلاً:



&#x20;   trading fee

&#x20;   commission

&#x20;   exchange fee

&#x20;   broker fee



================================================================================

29\. FUNDING

================================================================================



برای Instrumentهایی که Funding دارند:



&#x20;   Funding Payment



باید به صورت Transaction ثبت شود.



================================================================================

30\. COST BASIS

================================================================================



Portfolio باید Cost Basis Position را حفظ کند.



روش محاسبه:



&#x20;   weighted average

&#x20;   FIFO

&#x20;   strategy-specific



باید Policy-controlled باشد.



================================================================================

31\. PORTFOLIO VALUATION

================================================================================



Valuation Engine:



&#x20;   Balances

&#x20;      +

&#x20;   Positions

&#x20;      +

&#x20;   Market Prices

&#x20;      |

&#x20;      v

&#x20;   Portfolio Value



================================================================================

32\. VALUATION CURRENCY

================================================================================



Portfolio یک:



&#x20;   Base Currency



دارد.



مثلاً:



&#x20;   USD



تمام Assetها برای Equity باید به Base Currency تبدیل شوند.



================================================================================

33\. FX CONVERSION

================================================================================



برای Assetهایی که Currency متفاوت دارند:



&#x20;   FX Rate Provider



استفاده می‌شود.



مثلاً:



&#x20;   EUR -> USD



================================================================================

34\. VALUATION TIMESTAMP

================================================================================



هر Valuation باید:



&#x20;   timestamp



داشته باشد.



Price بدون timestamp قابل اعتماد نیست.



================================================================================

35\. STALE PRICE

================================================================================



اگر Price قدیمی باشد:



&#x20;   valuation quality



باید مشخص شود.



Policy می‌تواند:



&#x20;   reject

&#x20;   warn

&#x20;   use last known



باشد.



================================================================================

36\. PORTFOLIO SNAPSHOT

================================================================================



PortfolioSnapshot شامل:



&#x20;   balances

&#x20;   positions

&#x20;   equity

&#x20;   exposure

&#x20;   pnl

&#x20;   valuation

&#x20;   timestamp



است.



================================================================================

37\. EQUITY SNAPSHOT

================================================================================



برای performance history:



&#x20;   EquitySnapshot



ذخیره می‌شود.



شامل:



&#x20;   equity

&#x20;   cash

&#x20;   exposure

&#x20;   realized\_pnl

&#x20;   unrealized\_pnl

&#x20;   timestamp



================================================================================

38\. PORTFOLIO HISTORY

================================================================================



Portfolio باید تاریخچه قابل بازسازی داشته باشد.



حداقل:



&#x20;   Transaction History

&#x20;   Fill History

&#x20;   Position History

&#x20;   Equity History



================================================================================

39\. LEDGER

================================================================================



Portfolio باید Ledger-based باشد.



اصل مهم:



&#x20;   Financial State

&#x20;       =

&#x20;   derived state

&#x20;       from

&#x20;   immutable financial events/transactions



================================================================================

40\. IMMUTABILITY

================================================================================



Financial transactions بعد از ثبت:



&#x20;   immutable



هستند.



اصلاح با:



&#x20;   compensating transaction



انجام می‌شود.



================================================================================

41\. DOUBLE ENTRY

================================================================================



در صورت نیاز به Accounting دقیق:



&#x20;   Double-entry Ledger



به عنوان معماری داخلی Portfolio Accounting استفاده می‌شود.



هر تغییر مالی باید:



&#x20;   debit

&#x20;   credit



قابل ردیابی داشته باشد.



================================================================================

42\. ACCOUNTING ENGINE

================================================================================



&#x20;   AccountingEngine



مسئول:



&#x20;   balance updates

&#x20;   transaction recording

&#x20;   fee accounting

&#x20;   PnL accounting

&#x20;   adjustments



================================================================================

43\. POSITION ENGINE

================================================================================



&#x20;   PositionEngine



مسئول:



&#x20;   open

&#x20;   increase

&#x20;   reduce

&#x20;   close

&#x20;   reverse



Position است.



================================================================================

44\. PNL ENGINE

================================================================================



&#x20;   PnLEngine



مسئول:



&#x20;   realized

&#x20;   unrealized

&#x20;   gross

&#x20;   net



PnL است.



================================================================================

45\. VALUATION ENGINE

================================================================================



&#x20;   ValuationEngine



مسئول:



&#x20;   asset valuation

&#x20;   FX conversion

&#x20;   equity calculation

&#x20;   portfolio NAV



================================================================================

46\. EXPOSURE ENGINE

================================================================================



&#x20;   ExposureEngine



محاسبه می‌کند:



&#x20;   symbol exposure

&#x20;   asset exposure

&#x20;   currency exposure

&#x20;   long exposure

&#x20;   short exposure

&#x20;   gross exposure

&#x20;   net exposure



================================================================================

47\. MARGIN ENGINE

================================================================================



برای حساب‌های Margin:



&#x20;   used margin

&#x20;   available margin

&#x20;   maintenance margin

&#x20;   initial margin



را مدیریت می‌کند.



================================================================================

48\. LEVERAGE

================================================================================



Portfolio می‌تواند:



&#x20;   current leverage

&#x20;   maximum leverage



را محاسبه و expose کند.



اما Policy محدودیت را تعیین می‌کند.



================================================================================

49\. RESERVED CAPITAL

================================================================================



Capital می‌تواند برای:



&#x20;   pending orders

&#x20;   margin

&#x20;   risk reserve



رزرو شود.



Execution/Trading از این state برای validation استفاده می‌کنند.



================================================================================

50\. ALLOCATION

================================================================================



Portfolio Allocation:



&#x20;   target weight

&#x20;   current weight

&#x20;   deviation



را نگه می‌دارد.



================================================================================

51\. CAPITAL ALLOCATION

================================================================================



مثلاً:



&#x20;   EURUSD = 20%

&#x20;   Gold   = 15%

&#x20;   Cash   = 30%



Allocation Target متعلق به Portfolio Policy است.



================================================================================

52\. REBALANCING

================================================================================



Rebalancing:



&#x20;   Current Allocation

&#x20;         |

&#x20;         v

&#x20;   Target Allocation

&#x20;         |

&#x20;         v

&#x20;   Required Changes

&#x20;         |

&#x20;         v

&#x20;   Trading Intents



Portfolio خودش Order اجرا نمی‌کند.



================================================================================

53\. PORTFOLIO CONSTRAINTS

================================================================================



مثال:



&#x20;   max exposure

&#x20;   max position

&#x20;   max asset weight

&#x20;   max leverage

&#x20;   max drawdown

&#x20;   minimum cash



================================================================================

54\. RISK INTEGRATION

================================================================================



Portfolio اطلاعات زیر را به Trading/Risk می‌دهد:



&#x20;   equity

&#x20;   exposure

&#x20;   positions

&#x20;   leverage

&#x20;   margin

&#x20;   drawdown

&#x20;   available capital



Portfolio خودش Strategy را اجرا نمی‌کند.



================================================================================

55\. DRAWDOWN

================================================================================



Portfolio باید بتواند:



&#x20;   peak equity

&#x20;   current equity

&#x20;   drawdown

&#x20;   maximum drawdown



را محاسبه کند.



================================================================================

56\. PERFORMANCE METRICS

================================================================================



Portfolio Metrics می‌تواند شامل:



&#x20;   total return

&#x20;   daily return

&#x20;   cumulative return

&#x20;   volatility

&#x20;   Sharpe ratio

&#x20;   Sortino ratio

&#x20;   max drawdown

&#x20;   win rate

&#x20;   profit factor



باشد.



محاسبات پیچیده Performance در Performance Analytics layer

قابل جداسازی هستند.



================================================================================

57\. RETURN SERIES

================================================================================



Portfolio باید بتواند:



&#x20;   equity curve



تولید کند.



================================================================================

58\. BENCHMARK

================================================================================



Portfolio Performance می‌تواند با:



&#x20;   benchmark



مقایسه شود.



مثلاً:



&#x20;   Buy \& Hold

&#x20;   Market Index



================================================================================

59\. MULTI-ACCOUNT

================================================================================



Platform باید از چند Account پشتیبانی کند.



مثلاً:



&#x20;   Account A

&#x20;   Account B

&#x20;   Account C



هر Account state مستقل دارد.



================================================================================

60\. MULTI-PORTFOLIO

================================================================================



یک Account می‌تواند:



&#x20;   multiple portfolios



داشته باشد.



مثلاً:



&#x20;   AI Portfolio

&#x20;   Manual Portfolio

&#x20;   Research Portfolio



================================================================================

61\. PORTFOLIO HIERARCHY

================================================================================



&#x20;   User

&#x20;     |

&#x20;     v

&#x20;   Account

&#x20;     |

&#x20;     +---- Portfolio A

&#x20;     |

&#x20;     +---- Portfolio B

&#x20;     |

&#x20;     +---- Portfolio C



================================================================================

62\. PORTFOLIO STATUS

================================================================================



&#x20;   ACTIVE

&#x20;   PAUSED

&#x20;   FROZEN

&#x20;   CLOSED

&#x20;   READ\_ONLY



================================================================================

63\. FREEZE

================================================================================



Frozen Portfolio:



&#x20;   no new financial mutations



مگر عملیات recovery/administrative.



================================================================================

64\. RECONCILIATION

================================================================================



Portfolio باید بتواند با External Account مقایسه شود.



Flow:



&#x20;   Internal State

&#x20;        |

&#x20;        v

&#x20;   External Broker State

&#x20;        |

&#x20;        v

&#x20;   Reconciliation

&#x20;        |

&#x20;        +--> MATCH

&#x20;        |

&#x20;        +--> MISMATCH



================================================================================

65\. RECONCILIATION ENGINE

================================================================================



مقایسه:



&#x20;   balances

&#x20;   positions

&#x20;   fills

&#x20;   fees

&#x20;   transactions



================================================================================

66\. RECONCILIATION MISMATCH

================================================================================



Mismatch باید:



&#x20;   detected

&#x20;   classified

&#x20;   audited

&#x20;   resolved



شود.



================================================================================

67\. EXTERNAL SOURCE OF TRUTH

================================================================================



در Live Trading:



&#x20;   Broker/Exchange



ممکن است Source of Truth برای Execution State باشد.



Portfolio باید قابلیت:



&#x20;   reconciliation



داشته باشد.



================================================================================

68\. POSITION RECONCILIATION

================================================================================



مثال:



Internal:

&#x20;   EURUSD +1000



Broker:

&#x20;   EURUSD +900



=> POSITION\_MISMATCH



================================================================================

69\. BALANCE RECONCILIATION

================================================================================



مثال:



Internal:

&#x20;   USD 10000



Broker:

&#x20;   USD 9985



=> BALANCE\_MISMATCH



================================================================================

70\. ADJUSTMENT

================================================================================



Adjustment باید:



&#x20;   explicit

&#x20;   authorized

&#x20;   audited



باشد.



نباید State مستقیماً overwrite شود.



================================================================================

71\. PORTFOLIO EVENTS

================================================================================



&#x20;   DepositRecorded

&#x20;   WithdrawalRecorded

&#x20;   FillRecorded

&#x20;   PositionOpened

&#x20;   PositionIncreased

&#x20;   PositionReduced

&#x20;   PositionClosed

&#x20;   FeeRecorded

&#x20;   FundingRecorded

&#x20;   PnLRealized

&#x20;   EquityUpdated

&#x20;   PortfolioValued

&#x20;   ReconciliationStarted

&#x20;   ReconciliationMismatch

&#x20;   ReconciliationCompleted

&#x20;   PortfolioFrozen

&#x20;   PortfolioResumed



================================================================================

72\. EVENT SOURCES

================================================================================



Portfolio Events می‌توانند از:



&#x20;   Execution Platform

&#x20;   Market Data

&#x20;   Account Provider

&#x20;   Administrative Operations



بیایند.



================================================================================

73\. EXECUTION → PORTFOLIO

================================================================================



ExecutionResult:



&#x20;   order\_id

&#x20;   fill\_id

&#x20;   symbol

&#x20;   side

&#x20;   quantity

&#x20;   price

&#x20;   fee

&#x20;   timestamp



&#x20;       |

&#x20;       v



&#x20;   Portfolio



================================================================================

74\. PORTFOLIO → TRADING

================================================================================



Portfolio Context:



&#x20;   equity

&#x20;   cash

&#x20;   positions

&#x20;   exposure

&#x20;   margin

&#x20;   drawdown



&#x20;       |

&#x20;       v



&#x20;   Trading / Risk



================================================================================

75\. PORTFOLIO → GUI

================================================================================



GUI می‌تواند ببیند:



&#x20;   balances

&#x20;   equity

&#x20;   positions

&#x20;   PnL

&#x20;   exposure

&#x20;   performance

&#x20;   drawdown



GUI مستقیماً Portfolio را mutate نمی‌کند.



================================================================================

76\. PORTFOLIO → SIMULATION

================================================================================



Simulation می‌تواند Portfolio را اجرا کند.



Flow:



&#x20;   Simulated Fill

&#x20;        |

&#x20;        v

&#x20;   Portfolio Accounting

&#x20;        |

&#x20;        v

&#x20;   Simulated Portfolio State



================================================================================

77\. BACKTEST PORTFOLIO

================================================================================



Backtest باید از همان Portfolio Accounting استفاده کند.



اصل:



&#x20;   Live Accounting

&#x20;       ≈

&#x20;   Simulation Accounting



تفاوت فقط در Source of Execution Events است.



================================================================================

78\. REPLAY

================================================================================



Replay باید بتواند:



&#x20;   historical execution events



را به Portfolio بدهد.



================================================================================

79\. PORTFOLIO STATE MACHINE

================================================================================



ACTIVE

&#x20; |

&#x20; +--> PAUSED

&#x20; |

&#x20; +--> FROZEN

&#x20; |

&#x20; +--> CLOSED



================================================================================

80\. POSITION STATE MACHINE

================================================================================



FLAT

&#x20; |

&#x20; v

OPENING

&#x20; |

&#x20; v

OPEN

&#x20; |

&#x20; +--> INCREASING

&#x20; |

&#x20; +--> REDUCING

&#x20; |

&#x20; v

CLOSING

&#x20; |

&#x20; v

CLOSED



================================================================================

81\. POSITION REVERSAL

================================================================================



LONG

&#x20; |

&#x20; v

CLOSE LONG

&#x20; |

&#x20; v

OPEN SHORT



یا طبق Execution semantics:



&#x20;   direct reversal



اما Accounting باید نتیجه Fillهای واقعی را ثبت کند.



================================================================================

82\. POSITION AGGREGATION

================================================================================



چند Fill:



&#x20;   Fill A

&#x20;   Fill B

&#x20;   Fill C



&#x20;      |

&#x20;      v



&#x20;   Position State



================================================================================

83\. COST AGGREGATION

================================================================================



Position Cost:



&#x20;   entry cost

&#x20;   exit proceeds

&#x20;   fees

&#x20;   funding



باید قابل تفکیک باشد.



================================================================================

84\. TAX / FISCAL EXTENSION

================================================================================



Architecture باید قابلیت افزودن:



&#x20;   tax lots

&#x20;   tax reporting

&#x20;   fiscal events



را بدون تغییر Core Portfolio داشته باشد.



================================================================================

85\. CORPORATE ACTIONS

================================================================================



در صورت نیاز:



&#x20;   split

&#x20;   dividend

&#x20;   merger

&#x20;   symbol change



به عنوان Portfolio Events قابل اضافه شدن هستند.



================================================================================

86\. ASSET LIFECYCLE

================================================================================



Asset می‌تواند:



&#x20;   ACTIVE

&#x20;   SUSPENDED

&#x20;   DELISTED



باشد.



Portfolio باید Positionهای موجود را مدیریت کند.



================================================================================

87\. PORTFOLIO SNAPSHOT CONSISTENCY

================================================================================



Snapshot باید atomic یا versioned باشد.



نباید:



&#x20;   balance از timestamp A

&#x20;   position از timestamp B

&#x20;   equity از timestamp C



بدون مشخص بودن consistency model



ترکیب شود.



================================================================================

88\. STATE VERSION

================================================================================



Portfolio State باید:



&#x20;   version



داشته باشد.



هدف:



&#x20;   concurrency control

&#x20;   optimistic locking

&#x20;   audit

&#x20;   replay



================================================================================

89\. CONCURRENCY

================================================================================



دو Execution Event همزمان نباید باعث:



&#x20;   lost update



شوند.



استفاده از:



&#x20;   optimistic concurrency

&#x20;   event ordering

&#x20;   transactional boundaries



مجاز است.



================================================================================

90\. IDEMPOTENCY

================================================================================



یک Fill با:



&#x20;   fill\_id



نباید دوبار Accounting شود.



================================================================================

91\. DUPLICATE FILL

================================================================================



اگر:



&#x20;   fill\_id already processed



باشد:



&#x20;   ignore duplicate



و Event Audit ثبت شود.



================================================================================

92\. ORDER / FILL DISTINCTION

================================================================================



Portfolio بیشتر به:



&#x20;   Fill



وابسته است.



Order Intent صرفاً قصد است.



Fill واقعیت مالی است.



================================================================================

93\. FINANCIAL TRUTH

================================================================================



اصل:



&#x20;   Intent = intention

&#x20;   Order = request

&#x20;   Fill = execution fact

&#x20;   Transaction = accounting fact

&#x20;   Position = derived financial state



================================================================================

94\. SOURCE OF TRUTH

================================================================================



Portfolio Ledger:



&#x20;   financial accounting truth



Position:



&#x20;   derived state



Equity:



&#x20;   derived valuation



================================================================================

95\. AUDIT TRAIL

================================================================================



هر mutation باید:



&#x20;   actor

&#x20;   source

&#x20;   timestamp

&#x20;   event

&#x20;   reference

&#x20;   previous state/version

&#x20;   resulting state/version



را تا حد ممکن قابل ردیابی کند.



================================================================================

96\. PORTFOLIO SERVICES

================================================================================



PortfolioService

AccountService

BalanceService

PositionService

TransactionService

PnLService

ValuationService

ExposureService

AllocationService

ReconciliationService

PortfolioSnapshotService

PerformanceService



================================================================================

97\. PORTFOLIO ENGINES

================================================================================



AccountingEngine

PositionEngine

PnLEngine

ValuationEngine

ExposureEngine

AllocationEngine

ReconciliationEngine

PerformanceEngine



================================================================================

98\. PORTFOLIO REPOSITORIES

================================================================================



PortfolioRepository

AccountRepository

BalanceRepository

PositionRepository

TransactionRepository

FillRepository

SnapshotRepository

EquityHistoryRepository



================================================================================

99\. PORTFOLIO CONTRACTS

================================================================================



ExecutionResultConsumer

PortfolioValuationProvider

PortfolioStateProvider

PositionProvider

ExposureProvider

EquityProvider

ReconciliationProvider



================================================================================

100\. PORTFOLIO PLUGINS

================================================================================



AccountingPolicyPlugin

ValuationPolicyPlugin

CostBasisPlugin

AllocationPolicyPlugin

PerformanceMetricPlugin

ReconciliationPlugin



================================================================================

101\. PORTFOLIO DATA FLOW

================================================================================



&#x20;                 EXECUTION RESULT

&#x20;                        |

&#x20;                        v

&#x20;                   FILL EVENT

&#x20;                        |

&#x20;                        v

&#x20;                ACCOUNTING ENGINE

&#x20;                        |

&#x20;             +----------+----------+

&#x20;             |                     |

&#x20;             v                     v

&#x20;       POSITION ENGINE       LEDGER ENGINE

&#x20;             |                     |

&#x20;             v                     v

&#x20;         POSITIONS            TRANSACTIONS

&#x20;             |                     |

&#x20;             +----------+----------+

&#x20;                        |

&#x20;                        v

&#x20;                 VALUATION ENGINE

&#x20;                        |

&#x20;                        v

&#x20;                    EQUITY

&#x20;                        |

&#x20;                        v

&#x20;                 EXPOSURE / RISK

&#x20;                        |

&#x20;                        v

&#x20;                   TRADING CONTEXT



================================================================================

102\. COMPLETE SYSTEM GRAPH

================================================================================



MARKET DATA

&#x20;   |

&#x20;   v

FEATURE

&#x20;   |

&#x20;   v

AI

&#x20;   |

&#x20;   v

TRADING

&#x20;   |

&#x20;   | TradingIntent

&#x20;   v

EXECUTION

&#x20;   |

&#x20;   | ExecutionResult / Fill

&#x20;   v

PORTFOLIO

&#x20;   |

&#x20;   +----> Balance

&#x20;   |

&#x20;   +----> Position

&#x20;   |

&#x20;   +----> Ledger

&#x20;   |

&#x20;   +----> PnL

&#x20;   |

&#x20;   +----> Equity

&#x20;   |

&#x20;   +----> Exposure

&#x20;   |

&#x20;   +----> Performance

&#x20;   |

&#x20;   +----> Risk Context

&#x20;   |

&#x20;   +----> Trading Context



================================================================================

103\. CRITICAL INVARIANTS

================================================================================



INVARIANT 01:

&#x20;   Financial values use Decimal.



INVARIANT 02:

&#x20;   Money has explicit Currency.



INVARIANT 03:

&#x20;   Fill is the execution fact.



INVARIANT 04:

&#x20;   Intent is not execution.



INVARIANT 05:

&#x20;   Portfolio accounting uses execution facts.



INVARIANT 06:

&#x20;   Financial transactions are immutable.



INVARIANT 07:

&#x20;   Corrections use compensating transactions.



INVARIANT 08:

&#x20;   Duplicate Fill must not mutate Portfolio twice.



INVARIANT 09:

&#x20;   Position is derived from financial events/fills.



INVARIANT 10:

&#x20;   PnL is derived from accounting state.



INVARIANT 11:

&#x20;   Equity is derived from valuation.



INVARIANT 12:

&#x20;   Portfolio does not call Broker APIs directly.



INVARIANT 13:

&#x20;   Portfolio does not execute Strategy.



INVARIANT 14:

&#x20;   Portfolio does not create Broker Orders.



INVARIANT 15:

&#x20;   Portfolio can consume Simulation events.



INVARIANT 16:

&#x20;   Portfolio can consume Live Execution events.



INVARIANT 17:

&#x20;   Live and Simulation accounting semantics should remain aligned.



INVARIANT 18:

&#x20;   Portfolio State is versioned.



INVARIANT 19:

&#x20;   Financial mutations are auditable.



INVARIANT 20:

&#x20;   Reconciliation never silently overwrites state.



INVARIANT 21:

&#x20;   External mismatch must be explicitly recorded.



INVARIANT 22:

&#x20;   Portfolio snapshots have a defined consistency boundary.



INVARIANT 23:

&#x20;   Account isolation is mandatory.



INVARIANT 24:

&#x20;   Portfolio isolation is mandatory.



INVARIANT 25:

&#x20;   Closed Portfolio cannot accept normal mutations.



================================================================================

104\. CONCEPTUAL MODULE STRUCTURE

================================================================================



portfolio/

&#x20;   accounts/

&#x20;   balances/

&#x20;   positions/

&#x20;   ledger/

&#x20;   transactions/

&#x20;   fills/

&#x20;   pnl/

&#x20;   valuation/

&#x20;   exposure/

&#x20;   allocation/

&#x20;   performance/

&#x20;   reconciliation/

&#x20;   snapshots/

&#x20;   policies/

&#x20;   state/

&#x20;   events/

&#x20;   audit/

&#x20;   plugins/



================================================================================

105\. PHASE 15 ARCHITECTURAL CONTRACT

================================================================================



Trading Platform says:



&#x20;   "I want to perform this trading action."



Execution Platform says:



&#x20;   "This is what actually happened."



Portfolio Platform says:



&#x20;   "Based on what actually happened,

&#x20;    this is the financial state of the system."



================================================================================

106\. PHASE 15 COMPLETION CRITERIA

================================================================================



&#x20;   \[OK] Account Architecture

&#x20;   \[OK] Portfolio Architecture

&#x20;   \[OK] Balance Architecture

&#x20;   \[OK] Position Architecture

&#x20;   \[OK] Transaction Architecture

&#x20;   \[OK] Ledger Architecture

&#x20;   \[OK] Fill Architecture

&#x20;   \[OK] PnL Architecture

&#x20;   \[OK] Equity Architecture

&#x20;   \[OK] Valuation Architecture

&#x20;   \[OK] Exposure Architecture

&#x20;   \[OK] Allocation Architecture

&#x20;   \[OK] Performance Architecture

&#x20;   \[OK] Margin Boundary

&#x20;   \[OK] Leverage Boundary

&#x20;   \[OK] Reconciliation

&#x20;   \[OK] Snapshot System

&#x20;   \[OK] State Versioning

&#x20;   \[OK] Idempotency

&#x20;   \[OK] Partial Fills

&#x20;   \[OK] Multi Account

&#x20;   \[OK] Multi Portfolio

&#x20;   \[OK] Multi Asset

&#x20;   \[OK] Multi Currency

&#x20;   \[OK] Backtest Integration

&#x20;   \[OK] Replay Integration

&#x20;   \[OK] Simulation Integration

&#x20;   \[OK] Live Integration

&#x20;   \[OK] Execution Boundary

&#x20;   \[OK] Risk Integration

&#x20;   \[OK] Audit

&#x20;   \[OK] Observability

&#x20;   \[OK] Recovery

&#x20;   \[OK] Financial Invariants



================================================================================

END OF PHASE 15 — PORTFOLIO PLATFORM ARCHITECTURE

================================================================================

