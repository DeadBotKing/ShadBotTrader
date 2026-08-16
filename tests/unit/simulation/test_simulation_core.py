"""Tests for the simulation core: clock, queue, session, curves, metrics."""

from datetime import timedelta
from decimal import Decimal

import pytest

from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.simulation.clock import SimulationClock
from ShadBotTrader.domain.simulation.equity_curve import EquityCurve, EquityPoint
from ShadBotTrader.domain.simulation.market_event import (
    MarketEvent,
    SimulationEventQueue,
)
from ShadBotTrader.domain.simulation.performance import (
    PerformanceMetrics,
    TradeRecord,
    sharpe_ratio,
    standard_deviation,
    summarise_trades,
)
from ShadBotTrader.domain.simulation.session import (
    SimulationConfiguration,
    SimulationSession,
)
from ShadBotTrader.domain.simulation.simulation_types import (
    EventPriority,
    MarketEventType,
    SessionStatus,
)
from tests.simulation_fixtures import XAU, make_candle, ts


def d(value: str) -> Decimal:
    return Decimal(value)


# ------------------------------------------------------------------ clock ---
class TestSimulationClock:
    def test_starts_at_the_window_start(self):
        clock = SimulationClock(ts(0), ts(100))
        assert clock.current_time == ts(0)
        assert clock.steps == 0
        assert not clock.is_finished

    def test_cannot_move_backwards(self):
        """A clock that could rewind would let a simulation see the future."""
        clock = SimulationClock(ts(0), ts(100))
        clock.advance_to(ts(50))
        with pytest.raises(ValidationError, match="cannot move backwards"):
            clock.advance_to(ts(20))

    def test_cannot_move_past_the_end(self):
        clock = SimulationClock(ts(0), ts(100))
        with pytest.raises(ValidationError, match="cannot move past end_time"):
            clock.advance_to(ts(200))

    def test_rejects_an_inverted_window(self):
        with pytest.raises(ValidationError, match="must not precede"):
            SimulationClock(ts(100), ts(0))

    def test_counts_only_real_moves(self):
        clock = SimulationClock(ts(0), ts(100))
        clock.advance_to(ts(10))
        clock.advance_to(ts(10))  # same instant: not a step
        clock.advance_to(ts(20))
        assert clock.steps == 2

    def test_advance_by_delta(self):
        clock = SimulationClock(ts(0), ts(100))
        clock.advance_by(timedelta(minutes=30))
        assert clock.current_time == ts(30)
        with pytest.raises(ValidationError, match="negative delta"):
            clock.advance_by(timedelta(minutes=-1))

    def test_is_finished_at_the_end(self):
        clock = SimulationClock(ts(0), ts(50))
        clock.advance_to(ts(50))
        assert clock.is_finished

    def test_snapshot_and_restore(self):
        """Checkpoint / restore keeps a long run resumable (§25-26)."""
        clock = SimulationClock(ts(0), ts(100))
        clock.advance_to(ts(40))
        snapshot = clock.snapshot()

        clock.advance_to(ts(80))
        assert clock.current_time == ts(80)

        clock.restore(snapshot)
        assert clock.current_time == ts(40)
        assert clock.steps == snapshot.steps

    def test_reset_returns_to_start(self):
        clock = SimulationClock(ts(0), ts(100))
        clock.advance_to(ts(60))
        clock.reset()
        assert clock.current_time == ts(0)
        assert clock.steps == 0


# ------------------------------------------------------------- event queue ---
class TestSimulationEventQueue:
    def _event(self, minutes: int, priority: EventPriority = EventPriority.MARKET):
        return MarketEvent(
            event_type=MarketEventType.CANDLE,
            symbol=XAU,
            event_time=ts(minutes),
            priority=priority,
        )

    def test_pops_in_chronological_order(self):
        queue = SimulationEventQueue()
        for minutes in (30, 10, 20):
            queue.push(self._event(minutes))
        assert [queue.pop().event_time for queue_index in range(3)] == [
            ts(10),
            ts(20),
            ts(30),
        ]

    def test_priority_breaks_timestamp_ties(self):
        """Market data must be seen before the decisions it triggers."""
        queue = SimulationEventQueue()
        queue.push(self._event(10, EventPriority.FILL))
        queue.push(self._event(10, EventPriority.MARKET))
        assert queue.pop().priority is EventPriority.MARKET
        assert queue.pop().priority is EventPriority.FILL

    def test_insertion_order_breaks_remaining_ties(self):
        """Same time and priority -> FIFO, never arbitrary."""
        queue = SimulationEventQueue()
        first = self._event(10)
        second = self._event(10)
        queue.push(first)
        queue.push(second)
        assert queue.pop() is first
        assert queue.pop() is second

    def test_peek_does_not_consume(self):
        queue = SimulationEventQueue()
        queue.push(self._event(10))
        assert queue.peek() is not None
        assert len(queue) == 1

    def test_pop_from_empty_raises(self):
        with pytest.raises(IndexError):
            SimulationEventQueue().pop()

    def test_from_candle_uses_the_candle_time(self):
        candle = make_candle(3, "2000")
        event = MarketEvent.from_candle(XAU, candle)
        assert event.event_time == candle.open_time
        assert event.candle is candle


# ---------------------------------------------------------------- session ---
class TestSimulationSession:
    def _session(self) -> SimulationSession:
        return SimulationSession(
            session_id="s1",
            configuration=SimulationConfiguration(),
            start_time=ts(0),
            end_time=ts(100),
        )

    def test_lifecycle_happy_path(self):
        session = self._session()
        assert session.status is SessionStatus.CREATED
        session.start()
        assert session.status is SessionStatus.RUNNING
        session.complete()
        assert session.status is SessionStatus.COMPLETED
        assert session.is_terminal

    def test_pause_and_resume_keep_state(self):
        session = self._session()
        session.start()
        session.count_event()
        session.pause()
        assert session.status is SessionStatus.PAUSED
        session.resume()
        assert session.status is SessionStatus.RUNNING
        assert session.events_processed == 1

    def test_illegal_transition_is_rejected(self):
        session = self._session()
        with pytest.raises(ValidationError, match="Invalid session transition"):
            session.pause()  # not running yet

    def test_failure_records_a_reason(self):
        session = self._session()
        session.start()
        session.fail("boom")
        assert session.status is SessionStatus.FAILED
        assert session.failure_reason == "boom"

    def test_configuration_validates_inputs(self):
        with pytest.raises(ValidationError):
            SimulationConfiguration(initial_capital=Decimal("0"))
        with pytest.raises(ValidationError):
            SimulationConfiguration(spread=Decimal("-1"))
        with pytest.raises(ValidationError):
            SimulationConfiguration(warmup_bars=-1)


# ----------------------------------------------------------- equity curve ---
class TestEquityCurve:
    def _curve(self, values) -> EquityCurve:
        curve = EquityCurve()
        for index, value in enumerate(values):
            curve.record(EquityPoint(timestamp=ts(index * 5), equity=d(value), cash=d(value)))
        return curve

    def test_tracks_start_and_end(self):
        curve = self._curve(["100", "120", "110"])
        assert curve.starting_equity == d("100")
        assert curve.final_equity == d("110")
        assert curve.total_return == d("10")
        assert curve.total_return_percent == d("10")

    def test_rejects_out_of_order_points(self):
        curve = EquityCurve()
        curve.record(EquityPoint(ts(10), d("100"), d("100")))
        with pytest.raises(ValidationError, match="chronological"):
            curve.record(EquityPoint(ts(5), d("100"), d("100")))

    def test_max_drawdown_from_running_peak(self):
        """100 -> 150 -> 90: the worst decline is 60 from the peak of 150."""
        curve = self._curve(["100", "150", "90", "120"])
        assert curve.max_drawdown == d("60")
        assert curve.max_drawdown_percent == d("40")

    def test_no_drawdown_on_a_rising_curve(self):
        curve = self._curve(["100", "110", "120"])
        assert curve.max_drawdown == d("0")
        assert curve.max_drawdown_percent == d("0")

    def test_drawdown_series_length_matches_points(self):
        curve = self._curve(["100", "150", "90"])
        assert curve.drawdown_series() == [d("0"), d("0"), d("60")]

    def test_empty_curve_reports_none(self):
        curve = EquityCurve()
        assert curve.is_empty
        assert curve.starting_equity is None
        assert curve.total_return is None
        assert curve.max_drawdown == d("0")

    def test_returns_are_period_over_period(self):
        curve = self._curve(["100", "110"])
        assert curve.returns() == [d("0.1")]


# ---------------------------------------------------------------- metrics ---
class TestPerformanceMetrics:
    def _metrics(self, **overrides) -> PerformanceMetrics:
        defaults = dict(
            starting_equity=d("1000"),
            final_equity=d("1100"),
            total_return=d("100"),
            total_return_percent=d("10"),
            max_drawdown=d("50"),
            max_drawdown_percent=d("5"),
            trade_count=4,
            win_count=3,
            loss_count=1,
            gross_profit=d("150"),
            gross_loss=d("50"),
        )
        defaults.update(overrides)
        return PerformanceMetrics(**defaults)

    def test_hit_rate(self):
        assert self._metrics().hit_rate == d("0.75")

    def test_profit_factor(self):
        assert self._metrics().profit_factor == d("3")

    def test_profit_factor_is_none_without_losses(self):
        """An infinite ratio must not be reported as a number."""
        assert self._metrics(gross_loss=d("0")).profit_factor is None

    def test_metrics_are_none_without_trades(self):
        metrics = self._metrics(trade_count=0, win_count=0, loss_count=0)
        assert metrics.hit_rate is None
        assert metrics.expectancy is None
        assert metrics.average_win is None

    def test_expectancy_is_net_per_trade(self):
        assert self._metrics().expectancy == d("25")  # (150 - 50) / 4

    def test_recovery_factor(self):
        assert self._metrics().recovery_factor == d("2")  # 100 / 50
        assert self._metrics(max_drawdown=d("0")).recovery_factor is None

    def test_to_dict_is_serialisable(self):
        payload = self._metrics().to_dict()
        assert payload["trade_count"] == 4
        assert payload["hit_rate"] == "0.75"


class TestTradeStatistics:
    def test_summarise_splits_wins_and_losses(self):
        trades = [
            TradeRecord("XAU", d("100"), d("2")),  # net +98
            TradeRecord("XAU", d("-40"), d("2")),  # net -42
            TradeRecord("XAU", d("30"), d("1")),  # net +29
        ]
        summary = summarise_trades(trades)
        assert summary["wins"] == d("2")
        assert summary["losses"] == d("1")
        assert summary["gross_profit"] == d("127")
        assert summary["gross_loss"] == d("42")
        assert summary["fees"] == d("5")

    def test_fees_can_flip_a_win_into_a_loss(self):
        trade = TradeRecord("XAU", d("5"), d("8"))
        assert trade.realized_pnl > 0
        assert trade.net_pnl == d("-3")
        assert trade.is_loss

    def test_standard_deviation_needs_two_points(self):
        assert standard_deviation([d("1")]) is None
        assert standard_deviation([d("1"), d("3")]) == d("2").sqrt()

    def test_sharpe_is_none_without_dispersion(self):
        """A flat return series has no risk, so Sharpe is undefined."""
        assert sharpe_ratio([d("0.01"), d("0.01"), d("0.01")]) is None
        assert sharpe_ratio([d("0.01")]) is None

    def test_sharpe_is_positive_for_a_profitable_series(self):
        result = sharpe_ratio([d("0.02"), d("0.01"), d("0.03")])
        assert result is not None and result > 0
