"""Demo of the Execution & Portfolio Platform (Sprint P5).

Runs the complete chain

    prediction -> strategy -> risk gate -> intent
              -> resolve -> venue -> fills -> portfolio

over a short price path, then prints the resulting book: positions,
realised and unrealised PnL, fees and the transaction history.

    python scripts/run_execution.py
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ShadBotTrader.application.services.execution_service import (  # noqa: E402
    ExecutionService,
)
from ShadBotTrader.application.services.trading_decision_service import (  # noqa: E402
    TradingDecisionService,
)
from ShadBotTrader.domain.execution.market_view import (  # noqa: E402
    ExecutionContext,
    MarketQuote,
)
from ShadBotTrader.domain.market.price import Price  # noqa: E402
from ShadBotTrader.domain.market.symbol import Symbol  # noqa: E402
from ShadBotTrader.domain.market.timeframe import Timeframe  # noqa: E402
from ShadBotTrader.domain.market.timestamp import Timestamp  # noqa: E402
from ShadBotTrader.domain.strategy.risk_policy import RiskPolicy  # noqa: E402
from ShadBotTrader.domain.strategy.strategy_context import (  # noqa: E402
    PortfolioView,
    PredictionView,
    StrategyContext,
)
from ShadBotTrader.infrastructure.execution import (  # noqa: E402
    DefaultIntentResolver,
    InMemoryExecutionJournal,
    InMemoryPortfolioLedger,
    SimulatedExecutionVenue,
)
from ShadBotTrader.infrastructure.trading import (  # noqa: E402
    AiDirectionalStrategy,
    DefaultIntentFactory,
    DefaultSignalValidator,
    InMemoryDecisionJournal,
    PolicyRiskGate,
    PositionAwareDecisionEngine,
)

START = datetime(2026, 8, 16, 12, 0, tzinfo=timezone.utc)
SYMBOL = Symbol("XAUUSD_i")
TIMEFRAME = Timeframe("5M")
SPREAD = Decimal("2")
STARTING_CASH = Decimal("100000")

# (minutes, mid price, model value, model confidence)
PATH = [
    (0, "2000", 0.95, 0.90),  # confident up  -> enter long
    (5, "2020", 0.92, 0.88),  # still up      -> already long, hold
    (10, "2050", 0.05, 0.93),  # flips down   -> exit the long (profit)
    (15, "2040", 0.03, 0.91),  # still down   -> enter short
    (20, "2010", 0.96, 0.94),  # flips up     -> exit the short (profit)
]


def main() -> int:
    print("=== Execution & Portfolio demo (Sprint P5) ===")
    print("prediction -> strategy -> risk gate -> intent -> venue -> portfolio\n")

    ledger = InMemoryPortfolioLedger(currency="USD", starting_cash=STARTING_CASH)
    venue = SimulatedExecutionVenue(
        slippage_rate=Decimal("0.0002"),
        commission_rate=Decimal("0.0001"),
        currency="USD",
    )
    decision_journal = InMemoryDecisionJournal()
    execution_journal = InMemoryExecutionJournal()

    trading = TradingDecisionService(
        strategies=[AiDirectionalStrategy(min_confidence=0.55)],
        decision_engine=PositionAwareDecisionEngine(),
        risk_gate=PolicyRiskGate(RiskPolicy(max_open_positions=3, min_confidence=0.5)),
        intent_factory=DefaultIntentFactory(base_quantity=Decimal("2")),
        validator=DefaultSignalValidator(max_signal_age_seconds=600),
        journal=decision_journal,
    )
    execution = ExecutionService(
        resolver=DefaultIntentResolver(),
        venue=venue,
        ledger=ledger,
        journal=execution_journal,
    )

    print(f"Starting cash : {STARTING_CASH} USD")
    print(f"Venue         : {venue.name} (spread {SPREAD}, slippage 0.02%, fee 0.01%)\n")

    header = (
        f"{'time':<6} {'mid':<7} {'signal':<7} {'decision':<8} "
        f"{'executed':<20} {'position':<22} {'realised'}"
    )
    print(header)
    print("-" * len(header))

    for minutes, mid_text, value, confidence in PATH:
        now = Timestamp(START + timedelta(minutes=minutes))
        mid = Price(Decimal(mid_text))
        quote = MarketQuote.from_mid(SYMBOL, mid, SPREAD, now)
        position = ledger.position(SYMBOL)

        strategy_context = StrategyContext(
            timestamp=now,
            symbol=SYMBOL,
            timeframe=TIMEFRAME,
            predictions=[
                PredictionView(
                    model_id="gold_direction",
                    model_version=1,
                    value=value,
                    confidence=confidence,
                    generated_at=now,
                )
            ],
            portfolio=PortfolioView(
                equity=ledger.cash.amount,
                open_position_quantity=position.signed_quantity,
                open_position_count=0 if position.is_flat else 1,
            ),
        )

        outcome = trading.evaluate(strategy_context)
        signal = outcome.signal.signal_type.value if outcome.signal else "-"
        decision = outcome.decision.decision_type.value if outcome.decision else "-"
        executed_text = "-"

        if outcome.intent is not None:
            execution_context = ExecutionContext(
                timestamp=now,
                quote=quote,
                position=position,
                equity=ledger.cash.amount,
                currency="USD",
            )
            result = execution.execute(outcome.intent, execution_context)
            if result.executed and result.result is not None:
                average = result.result.average_fill_price
                executed_text = (
                    f"{outcome.intent.side.value} " f"{result.result.filled_quantity} @ {average}"
                )
            else:
                executed_text = f"blocked: {result.rejected_reason[:14]}"

        book = ledger.position(SYMBOL)
        position_text = "flat" if book.is_flat else str(book)
        print(
            f"{minutes:<6} {mid_text:<7} {signal:<7} {decision:<8} "
            f"{executed_text:<20} {position_text:<22} {ledger.realized_pnl.amount:.2f}"
        )

    # ------------------------------------------------------------------
    final_mid = Price(Decimal(PATH[-1][1]))
    prices = {str(SYMBOL): final_mid}

    print("\n=== Portfolio ===")
    print(f"  cash              : {ledger.cash}")
    print(f"  realised PnL      : {ledger.realized_pnl}")
    print(f"  fees              : {ledger.total_fees}")
    print(f"  net realised PnL  : {ledger.net_realized_pnl}")
    print(f"  unrealised PnL    : {ledger.unrealized_pnl(prices)}")
    print(f"  equity            : {ledger.equity(prices)}")

    open_positions = ledger.positions()
    print(f"  open positions    : {len(open_positions)}")
    for state in open_positions:
        print(f"      {state}")

    print("\n=== Transactions ===")
    for transaction in ledger.transactions:
        print(f"  {transaction}")

    print("\n=== Audit ===")
    print(f"  decisions recorded : {len(decision_journal.entries())}")
    print(f"  intents produced   : {len(decision_journal.intents)}")
    print(f"  execution attempts : {len(execution_journal.entries())}")
    print(f"  filled             : {len(execution_journal.executed)}")
    print(f"  not filled         : {len(execution_journal.failed)}")
    counts = execution_journal.rejection_counts()
    if counts:
        for reason, count in sorted(counts.items()):
            print(f"      {reason:<24} {count}")

    # Invariants this sprint is built around.
    for entry in decision_journal.entries():
        if entry.intent is not None:
            assert entry.verdict is not None and entry.verdict.approved
    for entry in execution_journal.entries():
        if entry.executed:
            assert entry.result is not None and entry.result.filled_quantity > 0

    print("\nInvariants verified:")
    print("  * every intent passed the risk gate")
    print("  * every booked position came from a real fill")
    print("\nExecution demo finished successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
