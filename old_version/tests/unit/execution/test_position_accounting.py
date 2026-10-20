"""Position & PnL accounting tests (Phase 15, sections 24-27, 30).

These are the numbers that decide whether the platform is telling the
truth about money, so every case is checked against a hand-computed
expected value rather than against the implementation.
"""

from decimal import Decimal

import pytest

from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.execution.execution_types import PositionSide
from ShadBotTrader.domain.execution.money import Money
from ShadBotTrader.domain.execution.position_state import PositionState
from ShadBotTrader.domain.market.price import Price

from .conftest import XAU, buy, d, sell


# ------------------------------------------------------------------ Money ---
class TestMoney:
    def test_arithmetic_is_exact(self):
        total = Money(d("0.1"), "USD").add(Money(d("0.2"), "USD"))
        assert total.amount == d("0.3")  # exact: no float error

    def test_currency_mismatch_is_rejected(self):
        with pytest.raises(ValidationError, match="Currency mismatch"):
            Money(d("1"), "USD").add(Money(d("1"), "EUR"))

    def test_money_may_be_negative_unlike_balance(self):
        loss = Money(d("-50"), "USD")
        assert loss.is_negative
        assert loss.negate().amount == d("50")

    def test_subtraction_and_scaling(self):
        assert Money(d("100"), "USD").subtract(Money(d("30"), "USD")).amount == d("70")
        assert Money(d("100"), "USD").scale(d("0.5")).amount == d("50")


# --------------------------------------------------------- opening/closing ---
class TestPositionLifecycle:
    def test_flat_position_has_no_entry(self):
        state = PositionState.flat(XAU)
        assert state.is_flat
        assert state.side is PositionSide.FLAT
        assert state.average_entry_price is None
        assert state.cost_basis is None

    def test_opening_long_sets_entry_price(self):
        state, realized = PositionState.flat(XAU).apply_fill(buy("2", "2000"))
        assert state.is_long
        assert state.quantity == d("2")
        assert state.average_entry_price == Price(d("2000"))
        assert realized.is_zero  # opening realises nothing

    def test_opening_short_sets_negative_quantity(self):
        state, realized = PositionState.flat(XAU).apply_fill(sell("3", "2000"))
        assert state.is_short
        assert state.signed_quantity == d("-3")
        assert state.quantity == d("3")
        assert realized.is_zero

    def test_original_state_is_never_mutated(self):
        original = PositionState.flat(XAU)
        original.apply_fill(buy("1", "2000"))
        assert original.is_flat  # unchanged


# --------------------------------------------------------- average pricing ---
class TestAverageEntryPrice:
    def test_scaling_in_reaverages(self):
        """2 @ 2000 then 2 @ 2100 -> average 2050."""
        state, _ = PositionState.flat(XAU).apply_fill(buy("2", "2000"))
        state, realized = state.apply_fill(buy("2", "2100", fill_id="f2"))
        assert state.quantity == d("4")
        assert state.average_entry_price == Price(d("2050"))
        assert realized.is_zero  # increasing realises nothing

    def test_weighted_average_with_unequal_sizes(self):
        """1 @ 2000 + 3 @ 2100 -> (2000 + 6300) / 4 = 2075."""
        state, _ = PositionState.flat(XAU).apply_fill(buy("1", "2000"))
        state, _ = state.apply_fill(buy("3", "2100", fill_id="f2"))
        assert state.average_entry_price == Price(d("2075"))

    def test_partial_reduction_keeps_entry_price(self):
        state, _ = PositionState.flat(XAU).apply_fill(buy("4", "2000"))
        state, _ = state.apply_fill(sell("1", "2100"))
        assert state.quantity == d("3")
        assert state.average_entry_price == Price(d("2000"))  # unchanged


# ------------------------------------------------------------ realized PnL ---
class TestRealizedPnl:
    def test_long_profit(self):
        """Buy 2 @ 2000, sell 2 @ 2100 -> +200."""
        state, _ = PositionState.flat(XAU).apply_fill(buy("2", "2000"))
        state, realized = state.apply_fill(sell("2", "2100"))
        assert realized.amount == d("200")
        assert state.is_flat
        assert state.realized_pnl.amount == d("200")

    def test_long_loss(self):
        """Buy 2 @ 2000, sell 2 @ 1950 -> -100."""
        state, _ = PositionState.flat(XAU).apply_fill(buy("2", "2000"))
        state, realized = state.apply_fill(sell("2", "1950"))
        assert realized.amount == d("-100")

    def test_short_profit(self):
        """Sell 2 @ 2000, buy back 2 @ 1900 -> +200."""
        state, _ = PositionState.flat(XAU).apply_fill(sell("2", "2000"))
        state, realized = state.apply_fill(buy("2", "1900"))
        assert realized.amount == d("200")
        assert state.is_flat

    def test_short_loss(self):
        """Sell 2 @ 2000, buy back 2 @ 2100 -> -200."""
        state, _ = PositionState.flat(XAU).apply_fill(sell("2", "2000"))
        state, realized = state.apply_fill(buy("2", "2100"))
        assert realized.amount == d("-200")

    def test_partial_close_realises_only_the_closed_part(self):
        """Buy 4 @ 2000, sell 1 @ 2100 -> +100 on the 1 unit only."""
        state, _ = PositionState.flat(XAU).apply_fill(buy("4", "2000"))
        state, realized = state.apply_fill(sell("1", "2100"))
        assert realized.amount == d("100")
        assert state.quantity == d("3")

    def test_realized_pnl_accumulates(self):
        state, _ = PositionState.flat(XAU).apply_fill(buy("4", "2000"))
        state, _ = state.apply_fill(sell("1", "2100"))  # +100
        state, _ = state.apply_fill(sell("1", "2050"))  # +50
        assert state.realized_pnl.amount == d("150")


# ---------------------------------------------------------------- reversal ---
class TestReversal:
    def test_reversal_realises_only_the_closing_leg(self):
        """Long 2 @ 2000, then sell 5 @ 2100.

        Closes 2 (+200 realised) and opens a short 3 at 2100.
        """
        state, _ = PositionState.flat(XAU).apply_fill(buy("2", "2000"))
        state, realized = state.apply_fill(sell("5", "2100"))

        assert realized.amount == d("200")  # only the 2 closed units
        assert state.is_short
        assert state.quantity == d("3")
        assert state.average_entry_price == Price(d("2100"))  # fresh entry

    def test_short_to_long_reversal(self):
        state, _ = PositionState.flat(XAU).apply_fill(sell("1", "2000"))
        state, realized = state.apply_fill(buy("4", "1900"))
        assert realized.amount == d("100")  # short profit on 1 unit
        assert state.is_long
        assert state.quantity == d("3")
        assert state.average_entry_price == Price(d("1900"))


# -------------------------------------------------------------------- fees ---
class TestFees:
    def test_fees_are_tracked_separately_from_pnl(self):
        """Gross PnL and fees must never be conflated (Phase 15 §27)."""
        state, _ = PositionState.flat(XAU).apply_fill(buy("2", "2000", fee="4"))
        state, _ = state.apply_fill(sell("2", "2100", fee="4.2"))

        assert state.realized_pnl.amount == d("200")  # gross
        assert state.total_fees.amount == d("8.2")
        assert state.net_realized_pnl.amount == d("191.8")  # net

    def test_fees_accumulate_even_without_realised_pnl(self):
        state, _ = PositionState.flat(XAU).apply_fill(buy("1", "2000", fee="2"))
        assert state.realized_pnl.is_zero
        assert state.total_fees.amount == d("2")


# -------------------------------------------------------- unrealized / MTM ---
class TestUnrealizedPnl:
    def test_long_unrealized_follows_market(self):
        state, _ = PositionState.flat(XAU).apply_fill(buy("2", "2000"))
        assert state.unrealized_pnl(Price(d("2100"))).amount == d("200")
        assert state.unrealized_pnl(Price(d("1900"))).amount == d("-200")

    def test_short_unrealized_is_inverted(self):
        state, _ = PositionState.flat(XAU).apply_fill(sell("2", "2000"))
        assert state.unrealized_pnl(Price(d("1900"))).amount == d("200")
        assert state.unrealized_pnl(Price(d("2100"))).amount == d("-200")

    def test_flat_position_has_no_unrealized_pnl(self):
        assert PositionState.flat(XAU).unrealized_pnl(Price(d("2000"))).is_zero

    def test_total_pnl_combines_realised_unrealised_and_fees(self):
        """Buy 4 @ 2000 (fee 4), sell 2 @ 2100 (fee 2), mark at 2050.

        realised  = +200, fees = 6, unrealised on 2 units = +100
        total     = 200 - 6 + 100 = 294
        """
        state, _ = PositionState.flat(XAU).apply_fill(buy("4", "2000", fee="4"))
        state, _ = state.apply_fill(sell("2", "2100", fee="2"))
        assert state.total_pnl(Price(d("2050"))).amount == d("294")


# -------------------------------------------------------------- cost basis ---
def test_cost_basis_reflects_committed_capital():
    state, _ = PositionState.flat(XAU).apply_fill(buy("3", "2000"))
    basis = state.cost_basis
    assert basis is not None
    assert basis.amount == d("6000")


def test_round_trip_returns_to_flat_with_correct_books():
    """A full cycle must leave no exposure but keep the P&L history."""
    state = PositionState.flat(XAU)
    for fill in (buy("2", "2000", fee="4"), sell("2", "2100", fee="4.2")):
        state, _ = state.apply_fill(fill)

    assert state.is_flat
    assert state.quantity == Decimal("0")
    assert state.average_entry_price is None
    assert state.realized_pnl.amount == d("200")
    assert state.total_fees.amount == d("8.2")
