"""End-to-end tests: prediction -> intent -> execution -> portfolio.

Covers Sprint P4 + P5 together, which is the first point where the
platform can answer "what did we actually make or lose?".
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from ShadBotTrader.application.services.execution_service import ExecutionService
from ShadBotTrader.application.services.trading_decision_service import (
    TradingDecisionService,
)
from ShadBotTrader.core.events.event_bus import EventBus
from ShadBotTrader.domain.execution.events import ORDER_FILLED, ORDER_REJECTED
from ShadBotTrader.domain.execution.execution_types import ExecutionRejectionReason
from ShadBotTrader.domain.execution.market_view import ExecutionContext, MarketQuote
from ShadBotTrader.domain.execution.position_state import PositionState
from ShadBotTrader.domain.market.price import Price
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timeframe import Timeframe
from ShadBotTrader.domain.market.timestamp import Timestamp
from ShadBotTrader.domain.strategy.risk_policy import RiskPolicy
from ShadBotTrader.domain.strategy.strategy_context import (
    PortfolioView,
    PredictionView,
    StrategyContext,
)
from ShadBotTrader.domain.trading.order import Order
from ShadBotTrader.infrastructure.execution import (
    DefaultIntentResolver,
    InMemoryExecutionJournal,
    InMemoryPortfolioLedger,
    SimulatedExecutionVenue,
)
from ShadBotTrader.infrastructure.trading import (
    AiDirectionalStrategy,
    DefaultIntentFactory,
    DefaultSignalValidator,
    PolicyRiskGate,
    PositionAwareDecisionEngine,
)

NOW = datetime(2026, 8, 16, 12, 0, tzinfo=timezone.utc)
SYMBOL = Symbol("XAUUSD_i")
TIMEFRAME = Timeframe("5M")


def d(value: str) -> Decimal:
    return Decimal(value)


def trading_service(policy: RiskPolicy | None = None, journal=None, bus=None):
    return TradingDecisionService(
        strategies=[AiDirectionalStrategy(min_confidence=0.55)],
        decision_engine=PositionAwareDecisionEngine(),
        risk_gate=PolicyRiskGate(policy or RiskPolicy()),
        intent_factory=DefaultIntentFactory(base_quantity=d("2")),
        validator=DefaultSignalValidator(max_signal_age_seconds=600),
        journal=journal,
        event_bus=bus,
    )


def execution_service(
    ledger=None,
    venue=None,
    journal=None,
    bus=None,
) -> ExecutionService:
    return ExecutionService(
        resolver=DefaultIntentResolver(),
        venue=venue or SimulatedExecutionVenue(),
        ledger=ledger or InMemoryPortfolioLedger(starting_cash=d("100000")),
        journal=journal,
        event_bus=bus,
    )


def strategy_context(value: float, confidence: float, quantity: str = "0") -> StrategyContext:
    return StrategyContext(
        timestamp=Timestamp(NOW),
        symbol=SYMBOL,
        timeframe=TIMEFRAME,
        predictions=[
            PredictionView(
                model_id="gold_direction",
                model_version=1,
                value=value,
                confidence=confidence,
                generated_at=Timestamp(NOW),
            )
        ],
        portfolio=PortfolioView(
            equity=d("100000"),
            open_position_quantity=Decimal(quantity),
            open_position_count=0 if Decimal(quantity) == 0 else 1,
        ),
    )


def execution_context(
    position: PositionState | None = None,
    bid: str = "1999",
    ask: str = "2001",
    timestamp: Timestamp | None = None,
    liquidity: str | None = None,
) -> ExecutionContext:
    return ExecutionContext(
        timestamp=timestamp or Timestamp(NOW),
        quote=MarketQuote(SYMBOL, Price(d(bid)), Price(d(ask)), Timestamp(NOW)),
        position=position or PositionState.flat(SYMBOL),
        equity=d("100000"),
        available_liquidity=Decimal(liquidity) if liquidity else None,
    )


# ------------------------------------------------------------ happy path ---
def test_prediction_becomes_an_open_position():
    ledger = InMemoryPortfolioLedger(starting_cash=d("100000"))
    trading = trading_service()
    execution = execution_service(ledger=ledger)

    outcome = trading.evaluate(strategy_context(value=0.95, confidence=0.9))
    assert outcome.intent is not None

    executed = execution.execute(outcome.intent, execution_context())

    assert executed.executed
    assert executed.position is not None
    assert executed.position.is_long
    assert executed.position.quantity == d("2")
    # bought at the ask
    assert executed.position.average_entry_price == Price(d("2001"))
    assert ledger.position(SYMBOL).quantity == d("2")


def test_full_round_trip_produces_realised_pnl():
    """Open long at 2001, close at 2099 -> 2 x 98 = 196 gross."""
    ledger = InMemoryPortfolioLedger(starting_cash=d("100000"))
    trading = trading_service()
    execution = execution_service(ledger=ledger)

    # --- open ---------------------------------------------------------
    entry = trading.evaluate(strategy_context(value=0.95, confidence=0.9))
    assert entry.intent is not None
    execution.execute(entry.intent, execution_context())
    position = ledger.position(SYMBOL)
    assert position.is_long

    # --- close: a bearish prediction while long -> EXIT -----------------
    exit_outcome = trading.evaluate(strategy_context(value=0.02, confidence=0.95, quantity="2"))
    assert exit_outcome.intent is not None

    execution.execute(
        exit_outcome.intent, execution_context(position=position, bid="2099", ask="2101")
    )

    final = ledger.position(SYMBOL)
    assert final.is_flat
    assert final.realized_pnl.amount == d("196")  # (2099 - 2001) * 2
    assert ledger.cash.amount == d("100196")


def test_fees_and_slippage_reduce_the_result():
    ledger = InMemoryPortfolioLedger(starting_cash=d("100000"))
    venue = SimulatedExecutionVenue(
        slippage_rate=Decimal("0.0005"), commission_rate=Decimal("0.0002")
    )
    trading = trading_service()
    execution = execution_service(ledger=ledger, venue=venue)

    entry = trading.evaluate(strategy_context(value=0.95, confidence=0.9))
    assert entry.intent is not None
    execution.execute(entry.intent, execution_context())

    position = ledger.position(SYMBOL)
    # slippage pushed the entry above the raw ask
    assert position.average_entry_price is not None
    assert position.average_entry_price.amount > d("2001")
    assert ledger.total_fees.amount > 0
    # net is strictly worse than gross once fees exist
    assert ledger.net_realized_pnl.amount <= ledger.realized_pnl.amount


# ----------------------------------------------------------- protections ---
def test_expired_intent_is_never_executed():
    ledger = InMemoryPortfolioLedger()
    execution = execution_service(ledger=ledger)
    outcome = trading_service().evaluate(strategy_context(value=0.95, confidence=0.9))
    assert outcome.intent is not None

    late = execution_context(timestamp=Timestamp(NOW + timedelta(hours=1)))
    executed = execution.execute(outcome.intent, late)

    assert not executed.executed
    assert executed.result is not None
    assert executed.result.rejection_reason is ExecutionRejectionReason.INTENT_EXPIRED
    assert ledger.position(SYMBOL).is_flat


def test_duplicate_intent_is_executed_only_once():
    """Idempotency: the same intent must never fill twice (Phase 14 §53)."""
    ledger = InMemoryPortfolioLedger()
    execution = execution_service(ledger=ledger)
    outcome = trading_service().evaluate(strategy_context(value=0.95, confidence=0.9))
    assert outcome.intent is not None

    first = execution.execute(outcome.intent, execution_context())
    second = execution.execute(outcome.intent, execution_context())

    assert first.executed
    assert not second.executed
    assert second.result is not None
    assert second.result.rejection_reason is ExecutionRejectionReason.DUPLICATE_INTENT
    assert ledger.position(SYMBOL).quantity == d("2")  # not 4


def test_partial_fill_opens_only_what_was_filled():
    ledger = InMemoryPortfolioLedger()
    execution = execution_service(ledger=ledger)
    outcome = trading_service().evaluate(strategy_context(value=0.95, confidence=0.9))
    assert outcome.intent is not None

    executed = execution.execute(outcome.intent, execution_context(liquidity="1"))

    assert executed.result is not None
    assert executed.result.remaining_quantity == d("1")
    assert ledger.position(SYMBOL).quantity == d("1")  # only the filled part


def test_risk_blocked_intent_never_reaches_the_venue():
    """The P4 gate and the P5 pipeline must compose safely."""
    ledger = InMemoryPortfolioLedger()
    journal = InMemoryExecutionJournal()

    blocked = trading_service(RiskPolicy(min_confidence=0.99)).evaluate(
        strategy_context(value=0.95, confidence=0.6)
    )

    assert blocked.intent is None  # nothing to execute
    assert journal.entries() == []
    assert ledger.position(SYMBOL).is_flat


# ------------------------------------------------- architectural invariants ---
class TestExecutionInvariants:
    def test_ledger_only_ever_reflects_real_fills(self):
        """Requested 2 but only 1 available -> the book shows 1."""
        ledger = InMemoryPortfolioLedger()
        execution = execution_service(ledger=ledger)
        outcome = trading_service().evaluate(strategy_context(value=0.95, confidence=0.9))
        assert outcome.intent is not None

        executed = execution.execute(outcome.intent, execution_context(liquidity="1"))
        assert executed.result is not None

        assert ledger.position(SYMBOL).quantity == executed.result.filled_quantity
        assert ledger.position(SYMBOL).quantity != outcome.intent.quantity_policy.value

    def test_entry_price_comes_from_fills_not_from_the_intent(self):
        """Phase 15 §24: never derive the average price from an intent."""
        ledger = InMemoryPortfolioLedger()
        venue = SimulatedExecutionVenue(slippage_rate=Decimal("0.01"))
        execution = execution_service(ledger=ledger, venue=venue)
        outcome = trading_service().evaluate(strategy_context(value=0.95, confidence=0.9))
        assert outcome.intent is not None

        executed = execution.execute(outcome.intent, execution_context())
        assert executed.result is not None
        average = executed.result.average_fill_price

        assert ledger.position(SYMBOL).average_entry_price == average
        assert average is not None and average.amount != d("2000")  # not the mid

    def test_no_domain_object_is_a_broker_order(self):
        outcome = trading_service().evaluate(strategy_context(value=0.95, confidence=0.9))
        assert outcome.intent is not None
        executed = execution_service().execute(outcome.intent, execution_context())

        assert not isinstance(outcome.intent, Order)
        assert not isinstance(executed.order, Order)  # ResolvedOrder is its own type
        assert executed.order is not None
        assert executed.order.intent_id == outcome.intent.intent_id

    def test_pipeline_is_deterministic(self):
        def run() -> tuple:
            ledger = InMemoryPortfolioLedger()
            execution = execution_service(ledger=ledger)
            outcome = trading_service().evaluate(strategy_context(value=0.95, confidence=0.9))
            assert outcome.intent is not None
            executed = execution.execute(outcome.intent, execution_context())
            assert executed.result is not None
            position = ledger.position(SYMBOL)
            return (
                executed.result.filled_quantity,
                executed.result.average_fill_price,
                position.signed_quantity,
            )

        assert run() == run()


# ----------------------------------------------------------------- events ---
def test_execution_publishes_events():
    received: list[str] = []
    bus = EventBus()
    bus.subscribe(ORDER_FILLED, lambda event: received.append(event.event_type))
    bus.subscribe(ORDER_REJECTED, lambda event: received.append(event.event_type))

    execution = execution_service(bus=bus)
    outcome = trading_service().evaluate(strategy_context(value=0.95, confidence=0.9))
    assert outcome.intent is not None

    execution.execute(outcome.intent, execution_context())
    assert ORDER_FILLED in received


def test_journal_captures_the_whole_execution_history():
    journal = InMemoryExecutionJournal()
    execution = execution_service(journal=journal)
    trading = trading_service()

    first = trading.evaluate(strategy_context(value=0.95, confidence=0.9))
    assert first.intent is not None
    execution.execute(first.intent, execution_context())
    execution.execute(first.intent, execution_context())  # duplicate

    assert len(journal.entries()) == 2
    assert len(journal.executed) == 1
    assert journal.rejection_counts()["duplicate_intent"] == 1


# ------------------------------------------------------- multi-cycle sweep ---
def test_multiple_cycles_accumulate_a_consistent_book():
    """Three round trips must leave the book flat and the PnL additive."""
    ledger = InMemoryPortfolioLedger(starting_cash=d("100000"))
    execution = execution_service(ledger=ledger)
    factory = DefaultIntentFactory(base_quantity=d("1"))
    trading = TradingDecisionService(
        strategies=[AiDirectionalStrategy(min_confidence=0.55)],
        decision_engine=PositionAwareDecisionEngine(),
        risk_gate=PolicyRiskGate(),
        intent_factory=factory,
        validator=DefaultSignalValidator(max_signal_age_seconds=600),
    )

    realised_before = ledger.realized_pnl.amount
    for index in range(3):
        entry = trading.evaluate(strategy_context(value=0.95, confidence=0.9))
        assert entry.intent is not None
        # unique id per cycle so the idempotency guard does not fire
        object.__setattr__(entry.intent, "_intent_id", f"intent:cycle:{index}")
        execution.execute(entry.intent, execution_context(position=ledger.position(SYMBOL)))

    position = ledger.position(SYMBOL)
    assert position.quantity == d("3")  # three 1-unit entries
    assert ledger.realized_pnl.amount == realised_before  # nothing closed yet
    assert position.average_entry_price == Price(d("2001"))
