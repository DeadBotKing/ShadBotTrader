"""Tests for the Execution Platform components (Phase 14 §19-24, Phase 15)."""

from datetime import timedelta
from decimal import Decimal

import pytest

from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.execution.execution_types import (
    ExecutionRejectionReason,
    ExecutionStatus,
)
from ShadBotTrader.domain.execution.fill import ExecutionResult
from ShadBotTrader.domain.execution.market_view import MarketQuote
from ShadBotTrader.domain.execution.position_state import PositionState
from ShadBotTrader.domain.market.price import Price
from ShadBotTrader.domain.market.timestamp import Timestamp
from ShadBotTrader.domain.strategy.strategy_identity import StrategyId, StrategyVersion
from ShadBotTrader.domain.strategy.strategy_types import (
    IntentType,
    PricePolicyType,
    QuantityPolicyType,
)
from ShadBotTrader.domain.strategy.trading_intent import (
    PricePolicy,
    QuantityPolicy,
    TradingIntent,
)
from ShadBotTrader.domain.trading.order import OrderSide, OrderType
from ShadBotTrader.infrastructure.execution import (
    DefaultIntentResolver,
    InMemoryExecutionJournal,
    InMemoryPortfolioLedger,
    SimulatedExecutionVenue,
)

from .conftest import BASE_TIME, XAU, buy, d, make_context, sell


def make_intent(
    intent_type: IntentType = IntentType.ENTER_POSITION,
    side: OrderSide = OrderSide.BUY,
    quantity: str = "2",
    policy_type: QuantityPolicyType = QuantityPolicyType.FIXED,
    price_policy: PricePolicy | None = None,
    expires_in: float | None = 60.0,
    intent_id: str = "i1",
    max_quantity: str | None = None,
) -> TradingIntent:
    return TradingIntent(
        intent_id=intent_id,
        decision_id="d1",
        strategy_id=StrategyId("ai_directional"),
        strategy_version=StrategyVersion(1),
        symbol=XAU,
        intent_type=intent_type,
        side=side,
        quantity_policy=QuantityPolicy(
            policy_type,
            value=Decimal(quantity),
            max_quantity=Decimal(max_quantity) if max_quantity else None,
        ),
        price_policy=price_policy or PricePolicy.market(),
        timestamp=Timestamp(BASE_TIME),
        expires_at=(
            Timestamp(BASE_TIME + timedelta(seconds=expires_in)) if expires_in is not None else None
        ),
    )


# ------------------------------------------------------------ MarketQuote ---
class TestMarketQuote:
    def test_rejects_inverted_spread(self):
        with pytest.raises(ValidationError, match="Ask must not be below bid"):
            MarketQuote(XAU, Price(d("2001")), Price(d("1999")), Timestamp(BASE_TIME))

    def test_mid_and_spread(self):
        quote = MarketQuote(XAU, Price(d("1999")), Price(d("2001")), Timestamp(BASE_TIME))
        assert quote.mid == Price(d("2000"))
        assert quote.spread == d("2")

    def test_from_mid_is_symmetric(self):
        quote = MarketQuote.from_mid(XAU, Price(d("2000")), d("4"), Timestamp(BASE_TIME))
        assert quote.bid == Price(d("1998"))
        assert quote.ask == Price(d("2002"))


# --------------------------------------------------------- IntentResolver ---
class TestDefaultIntentResolver:
    def test_fixed_quantity_passes_through(self):
        order = DefaultIntentResolver().resolve(make_intent(quantity="3"), make_context())
        assert order is not None
        assert order.quantity == d("3")
        assert order.order_type is OrderType.MARKET
        assert order.side is OrderSide.BUY

    def test_percent_equity_uses_live_equity_and_price(self):
        """10% of 100000 equity at mid 2000 -> 5 units."""
        intent = make_intent(quantity="10", policy_type=QuantityPolicyType.PERCENT_EQUITY)
        order = DefaultIntentResolver().resolve(intent, make_context(equity="100000"))
        assert order is not None
        assert order.quantity == d("5")

    def test_risk_amount_divides_by_price(self):
        """A 4000 risk budget at mid 2000 -> 2 units."""
        intent = make_intent(quantity="4000", policy_type=QuantityPolicyType.RISK_AMOUNT)
        order = DefaultIntentResolver().resolve(intent, make_context())
        assert order is not None
        assert order.quantity == d("2")

    def test_max_quantity_caps_the_result(self):
        intent = make_intent(
            quantity="10",
            policy_type=QuantityPolicyType.PERCENT_EQUITY,
            max_quantity="2",
        )
        order = DefaultIntentResolver().resolve(intent, make_context())
        assert order is not None
        assert order.quantity == d("2")

    def test_liquidity_is_the_venues_concern_not_the_resolvers(self):
        """The resolver states the desired size; the venue decides how

        much of it can trade. If the resolver capped it too, a liquidity
        shortfall would look like a complete fill.
        """
        order = DefaultIntentResolver().resolve(
            make_intent(quantity="10"), make_context(liquidity="3")
        )
        assert order is not None
        assert order.quantity == d("10")

    def test_exit_uses_the_actual_open_quantity(self):
        """A close can never exceed what is held."""
        held, _ = PositionState.flat(XAU).apply_fill(buy("7", "2000"))
        intent = make_intent(
            intent_type=IntentType.EXIT_POSITION, side=OrderSide.SELL, quantity="999"
        )
        order = DefaultIntentResolver().resolve(intent, make_context(position=held))
        assert order is not None
        assert order.quantity == d("7")

    def test_reduce_takes_a_fraction_of_the_position(self):
        held, _ = PositionState.flat(XAU).apply_fill(buy("8", "2000"))
        intent = make_intent(
            intent_type=IntentType.REDUCE_POSITION, side=OrderSide.SELL, quantity="99"
        )
        resolver = DefaultIntentResolver(reduce_fraction=Decimal("0.25"))
        order = resolver.resolve(intent, make_context(position=held))
        assert order is not None
        assert order.quantity == d("2")

    def test_exit_while_flat_resolves_to_nothing(self):
        intent = make_intent(intent_type=IntentType.EXIT_POSITION, side=OrderSide.SELL)
        assert DefaultIntentResolver().resolve(intent, make_context()) is None

    def test_below_minimum_quantity_resolves_to_nothing(self):
        resolver = DefaultIntentResolver(min_quantity=Decimal("1"))
        assert resolver.resolve(make_intent(quantity="0.001"), make_context()) is None

    def test_limit_policy_produces_a_limit_order(self):
        intent = make_intent(
            price_policy=PricePolicy(PricePolicyType.LIMIT, reference_price=Price(d("1995")))
        )
        order = DefaultIntentResolver().resolve(intent, make_context())
        assert order is not None
        assert order.order_type is OrderType.LIMIT
        assert order.limit_price == Price(d("1995"))


# ----------------------------------------------------------------- venue ---
class TestSimulatedExecutionVenue:
    def _order(self, resolver=None, **kwargs):
        resolver = resolver or DefaultIntentResolver()
        return resolver.resolve(make_intent(**kwargs), make_context())

    def test_buy_lifts_the_ask(self):
        order = self._order()
        result = SimulatedExecutionVenue().submit(order, make_context())
        assert result.status is ExecutionStatus.FILLED
        assert result.fills[0].price == Price(d("2001"))  # the ask

    def test_sell_hits_the_bid(self):
        order = self._order(side=OrderSide.SELL)
        result = SimulatedExecutionVenue().submit(order, make_context())
        assert result.fills[0].price == Price(d("1999"))  # the bid

    def test_slippage_moves_price_against_the_trader(self):
        venue = SimulatedExecutionVenue(slippage_rate=Decimal("0.001"))
        buy_result = venue.submit(self._order(), make_context())
        sell_result = venue.submit(self._order(side=OrderSide.SELL), make_context())
        assert buy_result.fills[0].price.amount > d("2001")  # worse for a buy
        assert sell_result.fills[0].price.amount < d("1999")  # worse for a sell

    def test_commission_is_charged_per_fill(self):
        venue = SimulatedExecutionVenue(commission_rate=Decimal("0.001"))
        result = venue.submit(self._order(quantity="2"), make_context())
        fee = result.fills[0].fee
        assert fee is not None
        assert fee.amount == d("2") * d("2001") * d("0.001")

    def test_partial_fill_when_liquidity_is_short(self):
        venue = SimulatedExecutionVenue()
        order = DefaultIntentResolver().resolve(make_intent(quantity="10"), make_context())
        result = venue.submit(order, make_context(liquidity="4"))
        assert result.status is ExecutionStatus.PARTIALLY_FILLED
        assert result.filled_quantity == d("4")
        assert result.remaining_quantity == d("6")

    def test_max_fill_ratio_forces_partial_execution(self):
        venue = SimulatedExecutionVenue(max_fill_ratio=Decimal("0.5"))
        result = venue.submit(self._order(quantity="4"), make_context())
        assert result.status is ExecutionStatus.PARTIALLY_FILLED
        assert result.filled_quantity == d("2")

    def test_unreachable_limit_is_rejected(self):
        resolver = DefaultIntentResolver()
        intent = make_intent(
            price_policy=PricePolicy(PricePolicyType.LIMIT, reference_price=Price(d("1900")))
        )
        order = resolver.resolve(intent, make_context())
        result = SimulatedExecutionVenue().submit(order, make_context())
        assert result.status is ExecutionStatus.REJECTED
        assert result.rejection_reason is ExecutionRejectionReason.NO_MARKET_PRICE

    def test_is_deterministic(self):
        venue = SimulatedExecutionVenue(slippage_rate=Decimal("0.0005"))
        order = self._order()
        first = venue.submit(order, make_context())
        second = venue.submit(order, make_context())
        assert first.fills[0].price == second.fills[0].price
        assert first.filled_quantity == second.filled_quantity


# --------------------------------------------------------- ExecutionResult ---
class TestExecutionResult:
    def test_average_fill_price_is_quantity_weighted(self):
        """1 @ 2000 and 3 @ 2100 -> (2000 + 6300) / 4 = 2075."""
        result = ExecutionResult(
            intent_id="i1",
            order_id="o1",
            status=ExecutionStatus.FILLED,
            requested_quantity=d("4"),
            fills=[buy("1", "2000", fill_id="a"), buy("3", "2100", fill_id="b")],
        )
        assert result.average_fill_price == Price(d("2075"))
        assert result.filled_quantity == d("4")

    def test_total_fees_sum_across_fills(self):
        result = ExecutionResult(
            intent_id="i1",
            order_id="o1",
            status=ExecutionStatus.FILLED,
            requested_quantity=d("2"),
            fills=[buy("1", "2000", fee="2", fill_id="a"), buy("1", "2000", fee="3", fill_id="b")],
        )
        fees = result.total_fees
        assert fees is not None
        assert fees.amount == d("5")

    def test_rejected_result_requires_a_reason(self):
        with pytest.raises(ValidationError):
            ExecutionResult(
                intent_id="i1",
                order_id="o1",
                status=ExecutionStatus.REJECTED,
                requested_quantity=d("1"),
            )

    def test_remaining_quantity_never_negative(self):
        result = ExecutionResult(
            intent_id="i1",
            order_id="o1",
            status=ExecutionStatus.FILLED,
            requested_quantity=d("1"),
            fills=[buy("2", "2000")],
        )
        assert result.remaining_quantity == d("0")


# ---------------------------------------------------------------- ledger ---
class TestInMemoryPortfolioLedger:
    def _result(self, *fills, requested="2"):
        return ExecutionResult(
            intent_id="i1",
            order_id="o1",
            status=ExecutionStatus.FILLED,
            requested_quantity=Decimal(requested),
            fills=list(fills),
        )

    def test_applying_fills_opens_a_position(self):
        ledger = InMemoryPortfolioLedger()
        state = ledger.apply(self._result(buy("2", "2000")))
        assert state.is_long
        assert ledger.position(XAU).quantity == d("2")
        assert len(ledger.positions()) == 1

    def test_round_trip_books_pnl_and_goes_flat(self):
        ledger = InMemoryPortfolioLedger()
        ledger.apply(self._result(buy("2", "2000", fee="4")))
        ledger.apply(self._result(sell("2", "2100", fee="4.2")))

        assert ledger.position(XAU).is_flat
        assert ledger.positions() == []  # flat positions are not "open"
        assert ledger.realized_pnl.amount == d("200")
        assert ledger.total_fees.amount == d("8.2")
        assert ledger.net_realized_pnl.amount == d("191.8")

    def test_cash_tracks_pnl_and_fees(self):
        ledger = InMemoryPortfolioLedger(starting_cash=d("10000"))
        ledger.apply(self._result(buy("2", "2000", fee="4")))
        ledger.apply(self._result(sell("2", "2100", fee="4.2")))
        # 10000 + 200 realised - 8.2 fees
        assert ledger.cash.amount == d("10191.8")

    def test_transactions_record_pnl_and_fees_separately(self):
        ledger = InMemoryPortfolioLedger()
        ledger.apply(self._result(buy("2", "2000", fee="4")))
        ledger.apply(self._result(sell("2", "2100", fee="4.2")))

        kinds = [txn.transaction_type.value for txn in ledger.transactions]
        assert kinds.count("fee") == 2
        assert kinds.count("trade") == 1  # only the closing fill realised PnL

    def test_equity_marks_open_positions_to_market(self):
        ledger = InMemoryPortfolioLedger(starting_cash=d("10000"))
        ledger.apply(self._result(buy("2", "2000")))
        equity = ledger.equity({str(XAU): Price(d("2100"))})
        assert equity.amount == d("10200")  # 10000 cash + 200 unrealised

    def test_aggregates_multiple_fills_of_one_result(self):
        ledger = InMemoryPortfolioLedger()
        state = ledger.apply(
            self._result(
                buy("1", "2000", fill_id="a"), buy("3", "2100", fill_id="b"), requested="4"
            )
        )
        assert state.quantity == d("4")
        assert state.average_entry_price == Price(d("2075"))


# --------------------------------------------------------------- journal ---
def test_execution_journal_separates_success_from_failure():
    journal = InMemoryExecutionJournal()
    intent = make_intent()

    journal.record(
        intent,
        None,
        ExecutionResult.rejected("i1", d("1"), ExecutionRejectionReason.INTENT_EXPIRED),
    )
    journal.record(
        intent,
        None,
        ExecutionResult(
            intent_id="i2",
            order_id="o2",
            status=ExecutionStatus.FILLED,
            requested_quantity=d("1"),
            fills=[buy("1", "2000")],
        ),
    )

    assert len(journal.entries()) == 2
    assert len(journal.executed) == 1
    assert len(journal.failed) == 1
    assert journal.rejection_counts()["intent_expired"] == 1
