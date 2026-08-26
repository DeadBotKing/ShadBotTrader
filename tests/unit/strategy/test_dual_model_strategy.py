"""Tests for the dual-model strategy with a binary signal model."""

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from ShadBotTrader.domain.ai.prediction_target import RangeForecast, SignalForecast
from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timeframe import Timeframe
from ShadBotTrader.domain.market.timestamp import Timestamp
from ShadBotTrader.domain.strategy.strategy_context import (
    PortfolioView,
    PredictionView,
    StrategyContext,
)
from ShadBotTrader.domain.strategy.strategy_types import SignalType, StrategyState
from ShadBotTrader.infrastructure.trading.dual_model_strategy import (
    RANGE_FORECAST_KEY,
    SIGNAL_FORECAST_KEY,
    DualModelStrategy,
)

MOMENT = Timestamp(datetime(2026, 2, 1, tzinfo=timezone.utc))


def signal(sell: float, buy: float) -> SignalForecast:
    return SignalForecast.from_vector((sell, buy), horizon=5, timeframe="5M")


def price_range(high: float = 0.010, low: float = -0.003, close: float = 2000.0):
    return RangeForecast(
        reference_close=close, high_offset=high, low_offset=low, horizon=5, timeframe="1H"
    )


def context(signal_forecast, range_forecast) -> StrategyContext:
    return StrategyContext(
        timestamp=MOMENT,
        symbol=Symbol("XAUUSD"),
        timeframe=Timeframe("5M"),
        predictions=[
            PredictionView(
                model_id="dual_model",
                model_version=1,
                value=(signal_forecast.buy_probability if signal_forecast else 0.5),
                confidence=(signal_forecast.confidence if signal_forecast else 0.0),
                generated_at=MOMENT,
                metadata={
                    SIGNAL_FORECAST_KEY: signal_forecast,
                    RANGE_FORECAST_KEY: range_forecast,
                },
            )
        ],
        portfolio=PortfolioView(equity=Decimal("100")),
    )


@pytest.fixture
def strategy():
    return DualModelStrategy(min_confidence=0.60, min_reward_risk=1.2, min_move_fraction=0.0008)


class TestAcceptedTrades:
    def test_a_confident_buy_with_good_reward_risk_trades(self, strategy):
        result = strategy.evaluate(context(signal(0.05, 0.95), price_range()))
        assert result.signal_type is SignalType.BUY
        assert result.confidence == pytest.approx(0.95)
        assert "buy 95.0%" in result.reason

    def test_a_confident_sell_trades(self, strategy):
        result = strategy.evaluate(context(signal(0.88, 0.12), price_range(high=0.003, low=-0.012)))
        assert result.signal_type is SignalType.SELL
        assert "sell 88.0%" in result.reason

    def test_the_reported_ratio_matches_the_gate_that_passed_it(self, strategy):
        result = strategy.evaluate(context(signal(0.88, 0.12), price_range(high=0.003, low=-0.012)))
        assert result.context["reward_risk"] == pytest.approx(4.0)
        assert "r/r 4.00" in result.reason

    def test_only_sell_and_buy_probabilities_are_recorded(self, strategy):
        result = strategy.evaluate(context(signal(0.05, 0.95), price_range()))
        assert result.context["buy_probability"] == pytest.approx(0.95)
        assert result.context["sell_probability"] == pytest.approx(0.05)
        assert "hold_probability" not in result.context


class TestRejectedTrades:
    def test_low_confidence_becomes_strategy_hold_not_model_hold(self, strategy):
        result = strategy.evaluate(context(signal(0.50, 0.50), price_range()))
        assert result.signal_type is SignalType.HOLD
        assert "50.0%" in result.reason and "60.0%" in result.reason

    def test_a_poor_reward_to_risk_is_deferred_to_the_bracket(self, strategy):
        # فاز ۵۲: گیت reward/risk از Strategy حذف شد چون entry_price در لحظهٔ
        # تصمیم معلوم نیست (ورود روی بازشدن کندل بعدی است). R/R اکنون توسط
        # TradeBracket.from_model_levels با entry_price واقعی و
        # reward_risk_multiplier اعمال می‌شود. اینجا فقط تأیید می‌کنیم که
        # استراتژی تصمیم را عبور می‌دهد و نسبت را گزارش می‌کند.
        result = strategy.evaluate(context(signal(0.05, 0.95), price_range(high=0.002, low=-0.020)))
        assert result.signal_type is SignalType.BUY
        assert result.context["reward_risk"] == pytest.approx(0.1)

    def test_a_move_too_small_to_pay_costs_is_rejected(self, strategy):
        result = strategy.evaluate(
            context(signal(0.05, 0.95), price_range(high=0.0002, low=-0.0001))
        )
        assert result.signal_type is SignalType.HOLD
        assert "cost floor" in result.reason

    def test_an_incoherent_range_forecast_blocks_the_trade(self, strategy):
        result = strategy.evaluate(context(signal(0.05, 0.95), price_range(high=-0.01, low=0.01)))
        assert result.signal_type is SignalType.HOLD
        assert "below its own low" in result.reason

    def test_a_missing_range_forecast_blocks_by_default(self, strategy):
        result = strategy.evaluate(context(signal(0.05, 0.95), None))
        assert result.signal_type is SignalType.HOLD
        assert "no range forecast" in result.reason

    def test_a_missing_signal_forecast_holds(self, strategy):
        result = strategy.evaluate(context(None, price_range()))
        assert result.signal_type is SignalType.HOLD
        assert "no signal forecast" in result.reason


class TestConfiguration:
    def test_the_range_model_can_be_made_optional(self):
        strategy = DualModelStrategy(require_range_model=False, min_confidence=0.6)
        result = strategy.evaluate(context(signal(0.05, 0.95), None))
        assert result.signal_type is SignalType.BUY

    def test_a_disabled_strategy_emits_nothing(self):
        strategy = DualModelStrategy(state=StrategyState.DISABLED)
        assert strategy.evaluate(context(signal(0.05, 0.95), price_range())) is None

    def test_a_stricter_threshold_rejects_what_a_looser_one_accepts(self):
        loose = DualModelStrategy(min_confidence=0.60)
        strict = DualModelStrategy(min_confidence=0.95)
        payload = context(signal(0.20, 0.80), price_range())
        assert loose.evaluate(payload).signal_type is SignalType.BUY
        assert strict.evaluate(payload).signal_type is SignalType.HOLD

    def test_invalid_configuration_is_refused(self):
        with pytest.raises(ValidationError):
            DualModelStrategy(min_confidence=1.5)
        with pytest.raises(ValidationError):
            DualModelStrategy(min_reward_risk=0)
