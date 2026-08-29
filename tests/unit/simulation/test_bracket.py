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


# ----------------------- فاز ۷۶ — SL بازسازی · TP ادعا: رد اگر سمت غلط --
def test_long_inverted_sl_is_recentered_but_tp_still_model_level():
    """فاز ۷۶: entry زیر رنج → SL بازسازی زیر entry · TP همان high مدل.

    رنج دیروز 4536–4594 (عرض 57.91) · entry=4482 زیر رنج.
    SL جدید = 4482.34 − 57.91 = 4424.43 · TP = 4594.28 (دست‌نخورده).
    """
    bracket = TradeBracket.from_model_levels(
        side=OrderSide.BUY,
        entry_reference=Price(Decimal("4482.34")),
        predicted_high=4594.28,
        predicted_low=4536.37,
        created_at=_moment(),
    )
    width = Decimal("4594.28") - Decimal("4536.37")
    assert bracket.recentered is True
    assert bracket.stop_loss.amount == Decimal("4482.34") - width
    assert bracket.take_profit.amount == Decimal("4594.28")  # TP مدل، دست‌نخورده
    assert bracket.stop_loss.amount < bracket.entry_reference.amount < bracket.take_profit.amount


def test_short_inverted_sl_is_recentered_above_entry():
    """SHORT با entry بالای رنج: SL = entry + width · TP = low مدل."""
    bracket = TradeBracket.from_model_levels(
        side=OrderSide.SELL,
        entry_reference=Price(Decimal("4610.00")),
        predicted_high=4594.28,
        predicted_low=4536.37,
        created_at=_moment(),
    )
    width = Decimal("57.91")
    assert bracket.recentered is True
    assert bracket.stop_loss.amount == Decimal("4610.00") + width
    assert bracket.take_profit.amount == Decimal("4536.37")  # TP مدل
    assert bracket.take_profit.amount < bracket.entry_reference.amount < bracket.stop_loss.amount


def test_long_with_tp_below_entry_is_refused():
    """فاز ۷۶ (خواستهٔ اپراتور): BUY که TP زیر entry است نباید باز شود.

    رنج دیروز 4536–4594 حول 4563؛ قیمت فردا 4620 (بالای رنج):
    برای BUY، TP=predicted_high=4594 زیر entry=4620 است → رد.
    (SL هم بالای entry است و recenter می‌شد — ولی TP بی‌اعتبار است.)
    """
    with pytest.raises(ValidationError, match="Take-profit on the wrong side"):
        TradeBracket.from_model_levels(
            side=OrderSide.BUY,
            entry_reference=Price(Decimal("4620.00")),
            predicted_high=4594.28,
            predicted_low=4536.37,
            created_at=_moment(),
        )


def test_short_with_tp_above_entry_is_refused():
    """SHORT که TP (predicted_low) بالای entry است → رد."""
    with pytest.raises(ValidationError, match="Take-profit on the wrong side"):
        TradeBracket.from_model_levels(
            side=OrderSide.SELL,
            entry_reference=Price(Decimal("4520.00")),  # entry زیر رنج
            predicted_high=4594.28,
            predicted_low=4536.37,  # TP بالای entry برای short → نامعتبر
            created_at=_moment(),
        )


def test_valid_bracket_is_not_marked_recentered():
    """براکت سالم: بدون بازسازی."""
    bracket = TradeBracket.from_model_levels(
        side=OrderSide.BUY,
        entry_reference=Price(Decimal("2000")),
        predicted_high=2020.0,
        predicted_low=1990.0,
        created_at=_moment(),
    )
    assert bracket.recentered is False
    assert bracket.to_dict()["recentered"] is False


def test_zero_width_range_still_rejected():
    """رنجِ صفر قابل بازسازی نیست."""
    with pytest.raises(ValidationError, match="zero width"):
        TradeBracket.from_model_levels(
            side=OrderSide.BUY,
            entry_reference=Price(Decimal("4482.34")),
            predicted_high=4536.37,
            predicted_low=4536.37,
            created_at=_moment(),
        )


def test_touching_the_boundary_still_passes():
    """SL چسبیده به entry (زیر آن) — نزدیک‌ترین فاصلهٔ مجاز."""
    bracket = TradeBracket.from_model_levels(
        side=OrderSide.BUY,
        entry_reference=Price(Decimal("2000")),
        predicted_high=2024.0,  # TP بالای entry
        predicted_low=1999.99,  # SL زیر entry (سمت درست — مرز معتبر)
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


# ------------------------------------------------------ باگ ۵۴ (فاز ۷۷) --
def test_gate7_uses_dollar_distance_not_fraction():
    """باگ ۵۴: min_sl_distance با فاصلهٔ دلاری سنجیده شود، نه fraction×ref.

    قبلاً ``risk`` (دلاری از RangeForecast) در reference ضرب می‌شد:
    $25 × $4104 = $104,975 → گیت همیشه pass می‌شد.
    """
    from datetime import datetime, timezone
    from decimal import Decimal as D

    from ShadBotTrader.domain.ai.prediction_target import RangeForecast, SignalForecast
    from ShadBotTrader.domain.market.symbol import Symbol
    from ShadBotTrader.domain.market.timeframe import Timeframe
    from ShadBotTrader.domain.market.timestamp import Timestamp
    from ShadBotTrader.domain.strategy.strategy_context import (
        PortfolioView,
        PredictionView,
        StrategyContext,
    )
    from ShadBotTrader.infrastructure.trading.dual_model_strategy import (
        DualModelStrategy,
    )

    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    sf = SignalForecast.from_vector((0.85, 0.15), horizon=0, timeframe="5M")
    rf = RangeForecast(
        reference_close=4104.87,
        high_offset=0.00623,
        low_offset=-0.00598,
        horizon=1,
        timeframe="1D",
    )
    sym = Symbol("XAUUSD")

    def ctx():
        return StrategyContext(
            timestamp=Timestamp(base),
            symbol=sym,
            timeframe=Timeframe("5M"),
            predictions=[
                PredictionView(
                    model_id="m",
                    model_version=1,
                    value=0.85,
                    confidence=0.85,
                    generated_at=Timestamp(base),
                    metadata={"signal_forecast": sf, "range_forecast": rf},
                )
            ],
            portfolio=PortfolioView(
                equity=D("100"), open_position_quantity=0, open_position_count=0
            ),
        )

    # risk دلاری = $25.57
    s40 = DualModelStrategy(
        min_confidence=0.6,
        min_reward_risk=None,
        min_move_fraction=0.0,
        min_sl_distance=40.0,
    ).evaluate(ctx())
    assert s40.signal_type.name == "HOLD"
    assert "25.57" in s40.reason

    s10 = DualModelStrategy(
        min_confidence=0.6,
        min_reward_risk=None,
        min_move_fraction=0.0,
        min_sl_distance=10.0,
    ).evaluate(ctx())
    assert s10.signal_type.name == "SELL"
