"""Unit tests for the fixed TP/SL bracket (TradeBracket).

The reward/risk decision was moved out of the strategy in Phase 52 because
the executable entry price is not known at decision time (the trade opens on
the next bar). It is enforced here, in ``TradeBracket.from_model_levels``,
against the real entry reference and the configured ``reward_risk_multiplier``.
"""

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.market.price import Price
from ShadBotTrader.domain.market.timestamp import Timestamp
from ShadBotTrader.domain.simulation.bracket import BracketExitReason, TradeBracket
from ShadBotTrader.domain.trading.order import OrderSide


def _moment() -> Timestamp:
    return Timestamp(datetime(2026, 2, 1, tzinfo=timezone.utc))


def test_an_enough_reward_to_risk_clears_the_gate():
    bracket = TradeBracket.from_model_levels(
        side=OrderSide.BUY,
        entry_reference=Price(Decimal("2000")),
        predicted_high=2020.0,  # TP distance 20
        predicted_low=1990.0,  # SL distance 10  -> r/r = 2.0
        created_at=_moment(),
        reward_risk_multiplier=2.0,
    )
    assert bracket.take_profit.amount == Decimal("2020")
    assert bracket.stop_loss.amount == Decimal("1990")


def test_a_poor_reward_to_risk_is_rejected():
    """The guarantee that poor R/R trades are rejected now lives here."""
    with pytest.raises(ValidationError) as exc:
        TradeBracket.from_model_levels(
            side=OrderSide.BUY,
            entry_reference=Price(Decimal("2000")),
            predicted_high=2004.0,  # +4 upside
            predicted_low=1960.0,  # -40 downside  -> r/r = 0.1 < 2.0
            created_at=_moment(),
            reward_risk_multiplier=2.0,
        )
    assert "R/R condition not met" in str(exc.value)


def test_a_poor_reward_to_risk_passes_when_the_multiplier_is_disabled():
    bracket = TradeBracket.from_model_levels(
        side=OrderSide.BUY,
        entry_reference=Price(Decimal("2000")),
        predicted_high=2004.0,
        predicted_low=1960.0,
        created_at=_moment(),
        reward_risk_multiplier=None,
    )
    assert bracket.take_profit.amount == Decimal("2004")


def test_spread_widens_the_stop_not_the_target():
    """Phase 57: the spread is added to the SL distance so a live spread
    does not trigger an early stop on the entry bar."""
    bracket = TradeBracket.from_model_levels(
        side=OrderSide.BUY,
        entry_reference=Price(Decimal("2000")),
        predicted_high=2010.0,
        predicted_low=1990.0,
        created_at=_moment(),
        spread=Decimal("2"),
    )
    assert bracket.take_profit.amount == Decimal("2010")
    assert bracket.stop_loss.amount == Decimal("1988")


def test_same_bar_policy_stop_first_resolves_ambiguous_touch():
    from ShadBotTrader.domain.market.candle import Candle
    from ShadBotTrader.domain.market.symbol import Symbol
    from ShadBotTrader.domain.market.timeframe import Timeframe

    bracket = TradeBracket.from_model_levels(
        side=OrderSide.BUY,
        entry_reference=Price(Decimal("2000")),
        predicted_high=2010.0,
        predicted_low=1990.0,
        created_at=_moment(),
    )
    candle = Candle(
        symbol=Symbol("XAUUSD"),
        timeframe=Timeframe("5M"),
        open_time=_moment(),
        open_price=Price(Decimal("2000")),
        high=Price(Decimal("2012")),
        low=Price(Decimal("1988")),
        close=Price(Decimal("2005")),
        volume=Decimal("100"),
    )
    assert bracket.trigger(candle) is BracketExitReason.STOP_LOSS


# ---------------------------------------------------------- باگ ۵۲ (فاز ۷۳) --
def test_long_bracket_with_stop_above_entry_is_refused():
    """باگ ۵۲: entry زیر رنجِ پیش‌بینی → SL بالای entry → باید رد شود.

    سناریوی واقعی (۲۰۲۶-۰۸-۲۷): رنج دیروز 4536–4594 حول 4563؛ قیمت فردا
    4482. براکتِ خام: SL=4533 (بالای entry!) · TP=4594. بررسی R/R با
    فاصلهٔ مطلق آن را «تأیید» می‌کرد و ۱٬۷۱۹ ترید وارونه ساخته می‌شد.
    """
    with pytest.raises(ValidationError, match="wrong side"):
        TradeBracket.from_model_levels(
            side=OrderSide.BUY,
            entry_reference=Price(Decimal("4482.34")),
            predicted_high=4594.28,
            predicted_low=4536.37,
            created_at=_moment(),
        )


def test_short_bracket_with_stop_below_entry_is_refused():
    """SHORT وارونه: قیمت بالای رنج رفته → SL (predicted_high+spread) زیر entry."""
    with pytest.raises(ValidationError, match="wrong side"):
        TradeBracket.from_model_levels(
            side=OrderSide.SELL,
            entry_reference=Price(Decimal("4610.00")),   # entry بالای رنج!
            predicted_high=4594.28,   # SL برای short = high+spread → زیر entry
            predicted_low=4536.37,
            created_at=_moment(),
        )


def test_touching_the_boundary_still_passes():
    """SL چسبیده به entry (زیر آن) — نزدیک‌ترین فاصلهٔ مجاز."""
    bracket = TradeBracket.from_model_levels(
        side=OrderSide.BUY,
        entry_reference=Price(Decimal("2000")),
        predicted_high=2024.0,   # TP بالای entry
        predicted_low=1999.99,   # SL زیر entry (سمت درست — مرز معتبر)
        created_at=_moment(),
    )
    assert bracket.stop_loss.amount == Decimal("1999.99")


def test_valid_long_bracket_still_builds():
    bracket = TradeBracket.from_model_levels(
        side=OrderSide.BUY,
        entry_reference=Price(Decimal("2000")),
        predicted_high=2020.0,
        predicted_low=1990.0,
        created_at=_moment(),
    )
    assert bracket.stop_loss.amount == Decimal("1990")
    assert bracket.take_profit.amount == Decimal("2020")
