"""Integration tests for the live decision loop (Phase 31).

The loop runs unattended every five minutes, so the properties that
matter are: it completes a real trade when conditions are right, it
refuses politely when they are not, and — above all — it never raises.
A crash in an unattended loop is an outage.

Model inference is stubbed deliberately. These tests verify the *wiring*
(buffer -> features -> models -> strategy -> risk -> execution); model
quality is tested in the Phase 29 suite.
"""

import math
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from ShadBotTrader.application.services.execution_service import ExecutionService
from ShadBotTrader.application.services.live_decision_service import LiveDecisionService
from ShadBotTrader.application.services.trading_decision_service import (
    TradingDecisionService,
)
from ShadBotTrader.domain.ai.prediction_target import RangeForecast, SignalForecast
from ShadBotTrader.domain.market.candle import Candle
from ShadBotTrader.domain.market.price import Price
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timeframe import Timeframe
from ShadBotTrader.domain.market.timestamp import Timestamp
from ShadBotTrader.domain.strategy.risk_policy import RiskPolicy
from ShadBotTrader.infrastructure.ai.live_matrix import LiveMatrixBuilder
from ShadBotTrader.infrastructure.data.live_buffer import LiveMarketData
from ShadBotTrader.infrastructure.execution import (
    DefaultIntentResolver,
    InMemoryPortfolioLedger,
    SimulatedExecutionVenue,
)
from ShadBotTrader.infrastructure.trading import (
    DefaultIntentFactory,
    DefaultSignalValidator,
    PolicyRiskGate,
    PositionAwareDecisionEngine,
)
from ShadBotTrader.infrastructure.trading.dual_model_strategy import DualModelStrategy

SYMBOL = "XAUUSD"
SYM = Symbol(SYMBOL)
NOW = datetime(2026, 2, 1, tzinfo=timezone.utc)


def candles(count: int, timeframe: str = "5M", minutes: int = 5):
    tf = Timeframe(timeframe)
    out = []
    price = 2000.0
    start = datetime(2026, 1, 5, tzinfo=timezone.utc)
    for index in range(count):
        move = math.sin(index / 30.0) * 4.0 + ((index % 7) - 3) * 0.3
        open_, close = price, price + move
        out.append(
            Candle(
                symbol=SYM,
                timeframe=tf,
                open_time=Timestamp(start + timedelta(minutes=minutes * index)),
                open_price=Price(Decimal(str(round(open_, 2)))),
                high=Price(Decimal(str(round(max(open_, close) + 1.1, 2)))),
                low=Price(Decimal(str(round(min(open_, close) - 1.1, 2)))),
                close=Price(Decimal(str(round(close, 2)))),
                volume=Decimal("100"),
            )
        )
        price = close
    return out


class StubSignal:
    """A signal model with a fixed opinion."""

    def __init__(self, vector=(0.05, 0.95)):
        self.vector = vector
        self.calls = 0

    def forecast(self, artifact, rows, generated_at=""):
        self.calls += 1
        return SignalForecast.from_vector(
            self.vector, horizon=5, timeframe="5M", generated_at=generated_at
        )


class StubRange:
    def __init__(self, high=0.010, low=-0.003):
        self.high, self.low = high, low
        self.calls = 0

    def forecast(self, artifact, rows, reference_close, generated_at=""):
        self.calls += 1
        return RangeForecast(
            reference_close=reference_close,
            high_offset=self.high,
            low_offset=self.low,
            horizon=5,
            timeframe="1H",
            generated_at=generated_at,
        )


class ExplodingSignal:
    """A model that fails, to prove the loop survives it."""

    def forecast(self, *args, **kwargs):
        raise RuntimeError("model backend died")


def build(signal_stub=None, range_stub=None, primed=800, strategy=None):
    market = LiveMarketData(timeframes=("5M", "1H"))
    if primed:
        market.prime("5M", candles(primed, "5M", 5))
        market.prime("1H", candles(primed, "1H", 60))

    ledger = InMemoryPortfolioLedger(starting_cash=Decimal("100"))
    trading = TradingDecisionService(
        strategies=[strategy or DualModelStrategy(min_confidence=0.6, min_reward_risk=1.2)],
        decision_engine=PositionAwareDecisionEngine(),
        risk_gate=PolicyRiskGate(RiskPolicy(max_open_positions=3, min_confidence=0.5)),
        intent_factory=DefaultIntentFactory(base_quantity=Decimal("0.01")),
        validator=DefaultSignalValidator(max_signal_age_seconds=86400),
    )
    execution = ExecutionService(
        resolver=DefaultIntentResolver(),
        venue=SimulatedExecutionVenue(commission_rate=Decimal("0.0001"), currency="USD"),
        ledger=ledger,
    )
    service = LiveDecisionService(
        symbol=SYMBOL,
        market=market,
        matrix_builder=LiveMatrixBuilder(SYMBOL, window_rows=500),
        trading_service=trading,
        execution_service=execution,
        ledger=ledger,
        range_predictor=range_stub if range_stub is not None else StubRange(),
        signal_predictor=signal_stub if signal_stub is not None else StubSignal(),
        range_artifact=object(),
        signal_artifact=object(),
    )
    return service, ledger, market


# ---------------------------------------------------------------- trade ---
class TestSuccessfulTick:
    def test_a_confident_signal_produces_a_real_fill(self):
        service, ledger, _ = build()

        result = service.tick(now=NOW)

        assert result.status == "traded"
        assert result.executed
        assert result.filled_quantity == Decimal("0.01")
        assert ledger.position(SYM).signed_quantity != 0

    def test_both_models_are_consulted(self):
        signal_stub, range_stub = StubSignal(), StubRange()
        service, _, _ = build(signal_stub, range_stub)

        service.tick(now=NOW)

        assert signal_stub.calls == 1
        assert range_stub.calls == 1

    def test_the_result_carries_both_forecasts(self):
        service, _, _ = build()

        result = service.tick(now=NOW)

        assert result.signal_forecast is not None
        assert result.range_forecast is not None
        assert result.signal_forecast.describe() == "buy 95.0%"

    def test_the_summary_is_human_readable(self):
        service, _, _ = build()

        lines = service.tick(now=NOW).summary_lines()

        assert any("signal" in line for line in lines)
        assert any("range" in line for line in lines)
        assert any("filled" in line for line in lines)

    def test_the_tick_is_json_serialisable(self):
        import json

        service, _, _ = build()
        payload = json.loads(json.dumps(service.tick(now=NOW).to_dict()))

        assert payload["status"] == "traded"
        assert payload["signal"]["predicted_class"] == "buy"


# ------------------------------------------------------------- no trade ---
class TestRefusedTick:
    def test_a_hold_signal_does_not_trade(self):
        service, ledger, _ = build(signal_stub=StubSignal((0.5, 0.5)))

        result = service.tick(now=NOW)

        assert result.status == "no_trade"
        assert not result.executed
        assert ledger.position(SYM).signed_quantity == 0

    def test_a_poor_reward_risk_does_not_trade(self):
        service, _, _ = build(range_stub=StubRange(high=0.002, low=-0.020))

        result = service.tick(now=NOW)

        assert result.status == "no_trade"
        assert "reward/risk" in result.reason

    def test_an_unprimed_buffer_skips_with_an_explanation(self):
        service, _, _ = build(primed=0)

        result = service.tick(now=NOW)

        assert result.status == "skipped"
        assert "buffer is empty" in result.reason

    def test_a_partially_filled_buffer_skips_rather_than_padding(self):
        service, _, _ = build(primed=300)

        result = service.tick(now=NOW)

        assert result.status == "skipped"
        assert "500" in result.reason


# ------------------------------------------------------------ resilience ---
class TestResilience:
    def test_a_failing_model_does_not_crash_the_loop(self):
        """An unattended loop must degrade, not die."""
        service, _, _ = build(signal_stub=ExplodingSignal())

        result = service.tick(now=NOW)

        assert result.status == "failed"
        assert "model backend died" in result.reason

    def test_the_loop_recovers_on_the_next_tick(self):
        service, _, _ = build(signal_stub=ExplodingSignal())
        assert service.tick(now=NOW).status == "failed"

        # swap in a working model, as a restart or reconnect would
        service._signal_predictor = StubSignal()
        assert service.tick(now=NOW + timedelta(minutes=5)).status == "traded"

    def test_every_tick_is_recorded_in_history(self):
        service, _, _ = build(signal_stub=StubSignal((0.3, 0.7)))

        for index in range(3):
            service.tick(now=NOW + timedelta(minutes=5 * index))

        assert len(service.history) == 3


# --------------------------------------------------------- buffer motion ---
class TestBufferMotion:
    def test_a_new_candle_advances_the_buffer_without_growing_it(self):
        service, _, market = build()
        before = market.buffer("5M").newest

        service.ingest("5M", candles(801, "5M", 5)[-1])

        after = market.buffer("5M").newest
        assert market.buffer("5M").size == 800
        assert after.open_time.value > before.open_time.value

    def test_repeating_the_current_candle_does_not_fabricate_history(self):
        """The forming bar is re-fetched constantly; it must not accumulate."""
        service, _, market = build()
        latest = market.buffer("5M").newest

        for _ in range(5):
            service.ingest("5M", latest)

        assert market.buffer("5M").size == 800

    def test_successive_ticks_keep_working_as_candles_arrive(self):
        service, _, _ = build(signal_stub=StubSignal((0.45, 0.55)))
        history = candles(810, "5M", 5)

        statuses = []
        for index in range(801, 805):
            service.ingest("5M", history[index])
            statuses.append(service.tick(now=NOW + timedelta(minutes=5 * index)).status)

        assert all(status == "no_trade" for status in statuses)
