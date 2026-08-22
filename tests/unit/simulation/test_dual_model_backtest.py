"""Regression tests for the signal-first dual-model backtest."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from ShadBotTrader.application.services.dual_model_backtest_service import (
    DualModelBacktestService,
)
from ShadBotTrader.domain.ai.prediction_target import RangeForecast, SignalForecast
from ShadBotTrader.domain.market.candle import Candle
from ShadBotTrader.domain.market.price import Price
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timeframe import Timeframe
from ShadBotTrader.domain.market.timestamp import Timestamp
from ShadBotTrader.domain.simulation.session import SimulationConfiguration
from ShadBotTrader.domain.simulation.simulation_types import EntryTiming, SameBarPolicy

SYMBOL = Symbol("XAUUSD")
SIGNAL_TF = Timeframe("5M")
RANGE_TF = Timeframe("1H")


class FixedSignalPredictor:
    def __init__(self, forecast: SignalForecast) -> None:
        self.forecast_value = forecast
        self.calls = 0
        self.windows = []

    def forecast(self, artifact, window, generated_at=""):
        self.calls += 1
        self.windows.append(window)
        return self.forecast_value


class FixedRangePredictor:
    def __init__(self, forecast: RangeForecast) -> None:
        self.forecast_value = forecast
        self.calls = 0
        self.windows = []

    def forecast(self, artifact, window, reference_close, generated_at=""):
        self.calls += 1
        self.windows.append(window)
        return self.forecast_value


def make_candle(
    moment: datetime,
    timeframe: Timeframe,
    open_price: str,
    high: str,
    low: str,
    close: str,
) -> Candle:
    return Candle(
        symbol=SYMBOL,
        timeframe=timeframe,
        open_time=Timestamp(moment),
        open_price=Price(Decimal(open_price)),
        high=Price(Decimal(high)),
        low=Price(Decimal(low)),
        close=Price(Decimal(close)),
        volume=Decimal("10"),
    )


def signal_series() -> list[Candle]:
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    values = [
        ("100", "101", "99", "100"),
        ("100", "101", "99", "100"),
        ("100", "101", "99", "100"),
        ("101", "102", "100", "101"),  # next-open entry
        ("101", "106", "100", "105"),  # target touched
        ("105", "106", "104", "105"),
    ]
    return [
        make_candle(start + timedelta(minutes=5 * index), SIGNAL_TF, *row)
        for index, row in enumerate(values)
    ]


def range_series() -> list[Candle]:
    start = datetime(2025, 12, 31, 21, tzinfo=timezone.utc)
    return [
        make_candle(start + timedelta(hours=index), RANGE_TF, "100", "101", "99", "100")
        for index in range(3)
    ]


def build_service(signal_predictor, range_predictor):
    return DualModelBacktestService(
        symbol=SYMBOL,
        signal_artifact=object(),
        signal_predictor=signal_predictor,
        range_artifact=object(),
        range_predictor=range_predictor,
        signal_window_size=2,
        range_window_size=2,
        min_signal_confidence=0.60,
        configuration=SimulationConfiguration(
            initial_capital=Decimal("1000"),
            spread=Decimal("0"),
            commission_rate=Decimal("0"),
            entry_timing=EntryTiming.NEXT_OPEN,
            same_bar_policy=SameBarPolicy.STOP_FIRST,
        ),
        base_quantity=Decimal("1"),
    )


def test_signal_is_checked_before_range_and_low_confidence_does_not_call_range():
    signal = FixedSignalPredictor(SignalForecast.from_vector((0.45, 0.55), 5, "5M"))
    ranged = FixedRangePredictor(RangeForecast(100.0, 0.05, -0.05, 5, "1H"))
    result = build_service(signal, ranged).run("low-confidence", signal_series(), range_series())

    assert signal.calls >= 1
    assert ranged.calls == 0
    assert result.fills == 0
    assert result.metrics.trade_count == 0


def test_probability_threshold_blocks_range_model():
    signal = FixedSignalPredictor(SignalForecast.from_vector((0.3, 0.7), 5, "5M"))
    ranged = FixedRangePredictor(RangeForecast(100.0, 0.05, -0.05, 5, "1H"))
    service = DualModelBacktestService(
        symbol=SYMBOL,
        signal_artifact=object(),
        signal_predictor=signal,
        range_artifact=object(),
        range_predictor=ranged,
        signal_window_size=2,
        range_window_size=2,
        min_signal_confidence=0.75,
        configuration=SimulationConfiguration(
            initial_capital=Decimal("1000"),
            spread=Decimal("0"),
            commission_rate=Decimal("0"),
            entry_timing=EntryTiming.NEXT_OPEN,
        ),
        base_quantity=Decimal("1"),
    )

    result = service.run("threshold", signal_series(), range_series())

    assert ranged.calls == 0
    assert result.fills == 0


def test_next_open_entry_gets_fixed_model_bracket_and_target_exit():
    signal = FixedSignalPredictor(SignalForecast.from_vector((0.05, 0.95), 5, "5M"))
    ranged = FixedRangePredictor(RangeForecast(100.0, 0.05, -0.05, 5, "1H"))

    result = build_service(signal, ranged).run("target", signal_series(), range_series())

    assert result.fills == 2
    assert result.bracket_exit_counts["take_profit"] == 1
    assert result.bracket_exit_counts["stop_loss"] == 0
    assert result.metrics.trade_count == 1
    assert result.trades[0].realized_pnl == Decimal("5")
    assert result.trades[0].fees == Decimal("0")


def test_sell_uses_predicted_low_as_target_and_high_as_stop():
    signal = FixedSignalPredictor(SignalForecast.from_vector((0.90, 0.10), 5, "5M"))
    ranged = FixedRangePredictor(RangeForecast(100.0, 0.05, -0.05, 5, "1H"))
    series = signal_series()
    series[4] = make_candle(series[4].open_time.value, SIGNAL_TF, "99", "100", "94", "95")

    result = build_service(signal, ranged).run("sell", series, range_series())

    assert result.bracket_exit_counts["take_profit"] == 1
    assert result.bracket_exit_counts["stop_loss"] == 0
    assert result.trades[0].realized_pnl == Decimal("5")


def test_stop_first_is_used_when_both_levels_are_touched():
    signal = FixedSignalPredictor(SignalForecast.from_vector((0.05, 0.95), 5, "5M"))
    ranged = FixedRangePredictor(RangeForecast(100.0, 0.05, -0.05, 5, "1H"))
    series = signal_series()
    series[4] = make_candle(series[4].open_time.value, SIGNAL_TF, "101", "106", "94", "105")

    result = build_service(signal, ranged).run("collision", series, range_series())

    assert result.bracket_exit_counts["stop_loss"] == 1
    assert result.bracket_exit_counts["take_profit"] == 0
    assert result.trades[0].realized_pnl == Decimal("-5")


def test_recording_does_not_change_dual_model_result():
    plain = build_service(
        FixedSignalPredictor(SignalForecast.from_vector((0.05, 0.95), 5, "5M")),
        FixedRangePredictor(RangeForecast(100.0, 0.05, -0.05, 5, "1H")),
    ).run("plain", signal_series(), range_series(), record_replay=False)
    recorded = build_service(
        FixedSignalPredictor(SignalForecast.from_vector((0.05, 0.95), 5, "5M")),
        FixedRangePredictor(RangeForecast(100.0, 0.05, -0.05, 5, "1H")),
    ).run("recorded", signal_series(), range_series(), record_replay=True)

    assert recorded.metrics.total_return == plain.metrics.total_return
    assert recorded.metrics.trade_count == plain.metrics.trade_count
    assert recorded.bracket_exit_counts == plain.bracket_exit_counts
    assert recorded.tape is not None
    assert recorded.tape.final_equity == recorded.metrics.final_equity
    trips = recorded.tape.round_trips()
    assert trips and trips[0]["bracket"]["take_profit"] == "105.0"
    assert trips[0]["exit_reason"] == "take_profit"
