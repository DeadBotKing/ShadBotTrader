"""Backtesting driven by the trained model (Phase 31, part B).

The prize here is not the return figure — it is causality. A source that
lets the model glimpse bar t+1 while deciding at bar t produces a
beautiful equity curve and loses money live, so most of these tests are
about what the model is *not* allowed to see.
"""

import math
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from ShadBotTrader.application.services.backtest_service import BacktestService
from ShadBotTrader.domain.ai.prediction_target import SignalForecast
from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.market.candle import Candle
from ShadBotTrader.domain.market.price import Price
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timeframe import Timeframe
from ShadBotTrader.domain.market.timestamp import Timestamp
from ShadBotTrader.domain.simulation.market_event import MarketEvent
from ShadBotTrader.domain.simulation.session import SimulationConfiguration
from ShadBotTrader.infrastructure.simulation import ModelPredictionSource

SYM = Symbol("XAUUSD")
TF = Timeframe("5M")


def candles(count: int):
    out = []
    price = 2000.0
    start = datetime(2026, 1, 5, tzinfo=timezone.utc)
    for index in range(count):
        move = math.sin(index / 25.0) * 3.5 + ((index % 7) - 3) * 0.35
        open_, close = price, price + move
        out.append(
            Candle(
                symbol=SYM,
                timeframe=TF,
                open_time=Timestamp(start + timedelta(minutes=5 * index)),
                open_price=Price(Decimal(str(round(open_, 2)))),
                high=Price(Decimal(str(round(max(open_, close) + 1.1, 2)))),
                low=Price(Decimal(str(round(min(open_, close) - 1.1, 2)))),
                close=Price(Decimal(str(round(close, 2)))),
                volume=Decimal("100"),
            )
        )
        price = close
    return out


class RecordingPredictor:
    """Returns a fixed forecast and remembers every window it saw."""

    def __init__(self, vector=(0.05, 0.95)):
        self.vector = vector
        self.windows = []

    def forecast(self, artifact, rows, generated_at=""):
        self.windows.append([list(row) for row in rows])
        return SignalForecast.from_vector(self.vector, horizon=5, timeframe="5M")


def source(window_size=40, predictor=None, **kwargs):
    return ModelPredictionSource(
        artifact=object(),
        predictor=predictor or RecordingPredictor(),
        symbol=SYM,
        timeframe=TF,
        window_size=window_size,
        **kwargs,
    )


def feed(prediction_source, series):
    """Drive the source the way the engine does: observe, then predict."""
    values = []
    for candle in series:
        event = MarketEvent.from_candle(SYM, candle)
        prediction_source.observe(event)
        values.append(prediction_source.predict(event))
    return values


# ------------------------------------------------------------- causality ---
class TestCausality:
    def test_the_source_abstains_until_the_window_is_full(self):
        """Padding a short window would be inventing history."""
        prediction_source = source(window_size=40)
        values = feed(prediction_source, candles(60))

        assert all(value is None for value in values[:39])
        assert prediction_source.abstentions >= 39

    def test_a_window_only_ever_contains_delivered_bars(self):
        predictor = RecordingPredictor()
        prediction_source = source(window_size=40, predictor=predictor)
        series = candles(60)
        feed(prediction_source, series)

        assert predictor.windows
        # every window has exactly the requested height — never more
        assert all(len(window) == 40 for window in predictor.windows)

    def test_the_number_of_windows_never_exceeds_the_bars_seen(self):
        predictor = RecordingPredictor()
        prediction_source = source(window_size=40, predictor=predictor)
        feed(prediction_source, candles(60))

        assert len(predictor.windows) <= 60 - 40 + 1

    def test_resetting_clears_all_history(self):
        prediction_source = source(window_size=40)
        feed(prediction_source, candles(60))
        prediction_source.reset()

        assert prediction_source.predictions_made == 0
        assert prediction_source.last_forecast is None
        assert prediction_source.predict(MarketEvent.from_candle(SYM, candles(1)[0])) is None


# ---------------------------------------------------------------- output ---
class TestPredictionMapping:
    def test_a_confident_buy_maps_above_neutral(self):
        prediction_source = source(window_size=30, predictor=RecordingPredictor((0.05, 0.95)))
        values = [value for value in feed(prediction_source, candles(50)) if value is not None]

        assert values
        assert all(value > 0.5 for value in values)

    def test_a_confident_sell_maps_below_neutral(self):
        prediction_source = source(window_size=30, predictor=RecordingPredictor((0.90, 0.10)))
        values = [value for value in feed(prediction_source, candles(50)) if value is not None]

        assert values
        assert all(value < 0.5 for value in values)

    def test_an_even_binary_split_is_below_the_probability_gate(self):
        prediction_source = source(window_size=30, predictor=RecordingPredictor((0.50, 0.50)))
        values = [value for value in feed(prediction_source, candles(50)) if value is not None]

        assert all(value == pytest.approx(0.5, abs=0.01) for value in values)
        assert prediction_source.confidence(None) == pytest.approx(0.5)

    def test_binary_forecast_has_no_hold_probability(self):
        prediction_source = source(window_size=30, predictor=RecordingPredictor((0.10, 0.90)))
        feed(prediction_source, candles(50))

        forecast = prediction_source.last_forecast
        assert forecast is not None
        assert not hasattr(forecast, "hold_probability")

    def test_the_full_forecast_stays_available(self):
        prediction_source = source(window_size=30)
        feed(prediction_source, candles(50))

        forecast = prediction_source.last_forecast
        assert forecast is not None
        assert forecast.describe() == "buy 95.0%"


# ------------------------------------------------------------ efficiency ---
class TestRecomputeInterval:
    def test_recomputing_every_bar_calls_the_model_each_time(self):
        predictor = RecordingPredictor()
        prediction_source = source(window_size=30, predictor=predictor, recompute_every=1)
        feed(prediction_source, candles(60))

        assert prediction_source.predictions_made == len(predictor.windows)
        assert prediction_source.predictions_made > 20

    def test_a_larger_interval_calls_the_model_far_less(self):
        frequent = source(window_size=30, recompute_every=1)
        sparse = source(window_size=30, recompute_every=10)
        feed(frequent, candles(80))
        feed(sparse, candles(80))

        assert sparse.predictions_made < frequent.predictions_made

    def test_skipped_bars_reuse_the_previous_value_not_a_new_guess(self):
        prediction_source = source(window_size=30, recompute_every=5)
        values = [value for value in feed(prediction_source, candles(60)) if value is not None]

        # the same forecast repeats between recomputes
        assert len(set(values)) < len(values)

    def test_invalid_configuration_is_refused(self):
        with pytest.raises(ValidationError):
            source(window_size=1)
        with pytest.raises(ValidationError):
            source(recompute_every=0)


# -------------------------------------------------------------- end-to-end ---
class TestBacktestIntegration:
    def test_a_backtest_runs_on_the_model_source(self):
        series = candles(300)
        prediction_source = source(window_size=40, recompute_every=5)

        service = BacktestService(
            configuration=SimulationConfiguration(
                initial_capital=Decimal("100"),
                spread=Decimal("4"),
                commission_rate=Decimal("0.0001"),
                warmup_bars=40,
            ),
            base_quantity=Decimal("0.01"),
        )
        result = service.run("model-source", SYM, TF, series, prediction_source=prediction_source)

        assert result.bars_processed == len(series)
        assert prediction_source.predictions_made > 0

    def test_the_engine_and_the_source_agree_on_how_many_bars_ran(self):
        series = candles(200)
        prediction_source = source(window_size=40)

        service = BacktestService(
            configuration=SimulationConfiguration(initial_capital=Decimal("100"), warmup_bars=40),
            base_quantity=Decimal("0.01"),
        )
        result = service.run("count", SYM, TF, series, prediction_source=prediction_source)

        assert prediction_source.stats()["bars_seen"] == result.bars_processed

    def test_a_replay_can_be_recorded_from_a_model_run(self):
        series = candles(200)
        service = BacktestService(
            configuration=SimulationConfiguration(initial_capital=Decimal("100"), warmup_bars=40),
            base_quantity=Decimal("0.01"),
        )
        result = service.run(
            "replayed",
            SYM,
            TF,
            series,
            prediction_source=source(window_size=40, recompute_every=5),
            record_replay=True,
        )

        assert result.tape is not None
        assert len(result.tape.bars) == len(series)
