"""Integration tests for the backtest engine (Phase 16).

The engine must orchestrate the *real* trading, risk, execution and
portfolio components — never a parallel implementation. These tests
assert that, and that the results are reproducible.
"""

from decimal import Decimal

import pytest

from ShadBotTrader.application.services.backtest_service import BacktestService
from ShadBotTrader.domain.simulation.session import SimulationConfiguration
from ShadBotTrader.domain.simulation.simulation_types import SessionStatus
from ShadBotTrader.domain.strategy.risk_policy import RiskPolicy
from ShadBotTrader.infrastructure.simulation import ScriptedPredictionSource
from tests.simulation_fixtures import (
    TF,
    XAU,
    candles_from,
    falling,
    flat_series,
    rising,
)


def d(value: str) -> Decimal:
    return Decimal(value)


def config(**overrides) -> SimulationConfiguration:
    defaults = dict(
        initial_capital=d("100000"),
        spread=d("4"),
        commission_rate=d("0.0001"),
        warmup_bars=4,
    )
    defaults.update(overrides)
    return SimulationConfiguration(**defaults)


def service(**overrides) -> BacktestService:
    return BacktestService(
        configuration=overrides.pop("configuration", config()),
        base_quantity=overrides.pop("base_quantity", d("1")),
        **overrides,
    )


# ------------------------------------------------------------- basic runs ---
def test_backtest_completes_and_reports():
    result = service().run("s1", XAU, TF, rising(40))

    assert result.session.status is SessionStatus.COMPLETED
    assert result.bars_processed == 40
    assert len(result.equity_curve) == 40
    assert result.metrics.starting_equity > 0


def test_warmup_bars_suppress_early_trading():
    """No intent may be produced before the warmup window has passed."""
    result = service(configuration=config(warmup_bars=30)).run("s2", XAU, TF, rising(35))
    # only 5 tradable bars remain, and momentum needs history on top
    assert result.intents_created <= 5


def test_flat_market_completes_no_round_trip():
    """A market that never moves never gives a reason to close.

    Momentum returns exactly 0.5 on a flat series, which the strategy
    reads as a (very weak) BUY, so one position is opened and then held
    for the rest of the run. What matters is that no round trip is
    completed and therefore no PnL is realised — the only change to
    equity is the spread and fee paid on entry.
    """
    backtest = service()
    result = backtest.run("s3", XAU, TF, flat_series(30))

    assert result.metrics.trade_count == 0  # nothing was ever closed
    assert backtest.ledger is not None
    assert backtest.ledger.realized_pnl.amount == d("0")
    # equity only moved by the cost of entering
    assert result.metrics.total_return < 0
    assert abs(result.metrics.total_return_percent) < d("0.1")


def test_rising_market_opens_a_long():
    backtest = service()
    result = backtest.run("s4", XAU, TF, rising(30))

    assert result.intents_created > 0
    assert backtest.ledger is not None
    assert backtest.ledger.position(XAU).is_long


def test_empty_candles_are_rejected():
    with pytest.raises(ValueError, match="at least one candle"):
        service().run("s5", XAU, TF, [])


# ------------------------------------------------------------ determinism ---
def test_identical_inputs_produce_identical_results():
    """Phase 16 §10: same data + config + seed -> same result."""
    candles = rising(40)

    first = service().run("run-a", XAU, TF, candles)
    second = service().run("run-b", XAU, TF, candles)

    assert first.bars_processed == second.bars_processed
    assert first.fills == second.fills
    assert first.metrics.final_equity == second.metrics.final_equity
    assert first.metrics.total_return == second.metrics.total_return
    assert first.metrics.trade_count == second.metrics.trade_count
    assert [point.equity for point in first.equity_curve.points] == [
        point.equity for point in second.equity_curve.points
    ]


def test_step_mode_matches_a_full_run():
    """Stepping bar by bar must reach the same state as run()."""
    candles = rising(25)

    stepped_service = service()
    engine = stepped_service.build("stepped", XAU, TF, candles)
    engine.session.start()
    bars = 0
    while engine.step() is not None:
        bars += 1
    engine.session.complete()

    full = service().run("full", XAU, TF, candles)

    assert bars == full.bars_processed
    assert engine.equity_curve.final_equity == full.metrics.final_equity


# ------------------------------------------------------------------ clock ---
def test_clock_follows_event_time_only():
    """The clock must end on the last bar, not on wall-clock time."""
    candles = rising(20)
    engine = service().build("clocked", XAU, TF, candles)

    assert engine.clock.current_time == candles[0].open_time
    engine.session.start()
    while engine.step() is not None:
        pass

    assert engine.clock.current_time == candles[-1].open_time
    assert engine.clock.is_finished


def test_equity_is_recorded_on_every_bar():
    result = service().run("curve", XAU, TF, rising(18))
    assert len(result.equity_curve) == 18
    timestamps = [point.timestamp.value for point in result.equity_curve.points]
    assert timestamps == sorted(timestamps)


# --------------------------------------------------------------- costs ---
def test_costs_reduce_the_result():
    """A wider spread and a fee must never improve the outcome."""
    candles = rising(40)

    cheap = BacktestService(
        configuration=config(spread=d("0"), commission_rate=d("0")),
        base_quantity=d("1"),
    ).run("cheap", XAU, TF, candles)

    expensive = BacktestService(
        configuration=config(spread=d("20"), commission_rate=d("0.002")),
        base_quantity=d("1"),
    ).run("expensive", XAU, TF, candles)

    assert expensive.metrics.total_fees >= cheap.metrics.total_fees
    assert expensive.metrics.final_equity <= cheap.metrics.final_equity


def test_fees_are_tracked_when_a_commission_is_charged():
    result = BacktestService(
        configuration=config(commission_rate=d("0.001")),
        base_quantity=d("1"),
    ).run("fees", XAU, TF, rising(40))

    if result.fills:
        assert result.metrics.total_fees > 0


# ------------------------------------------------------- scripted control ---
def test_scripted_predictions_drive_the_pipeline():
    """A controlled schedule must produce a controlled sequence of trades."""
    closes = [str(2000 + i) for i in range(20)]
    # buy at bar 6, exit at bar 12
    scripted = ScriptedPredictionSource({6: 0.95, 12: 0.05}, default_confidence=0.9)

    backtest = service(configuration=config(warmup_bars=2))
    result = backtest.run("scripted", XAU, TF, candles_from(closes), prediction_source=scripted)

    assert result.intents_created == 2
    assert result.fills == 2
    assert result.metrics.trade_count == 1  # one completed round trip
    assert backtest.ledger is not None
    assert backtest.ledger.position(XAU).is_flat


def test_scripted_losing_trade_is_reported_as_a_loss():
    """Buy high, sell low -> the books must show a loss."""
    closes = [str(2100 - i * 5) for i in range(20)]  # falling market
    scripted = ScriptedPredictionSource({5: 0.95, 11: 0.05}, default_confidence=0.9)

    result = service(configuration=config(warmup_bars=2)).run(
        "losing", XAU, TF, candles_from(closes), prediction_source=scripted
    )

    assert result.metrics.trade_count == 1
    assert result.metrics.loss_count == 1
    assert result.metrics.total_return < 0
    assert result.metrics.max_drawdown > 0


# ------------------------------------------------------------ risk gating ---
def test_risk_policy_blocks_trading_in_a_backtest():
    """The same risk gate used live must apply during a backtest."""
    backtest = BacktestService(
        configuration=config(),
        risk_policy=RiskPolicy(min_confidence=Decimal("0.999") and 0.999),
        base_quantity=d("1"),
    )
    result = backtest.run("risk", XAU, TF, rising(40))

    assert result.fills == 0
    assert backtest.ledger is not None
    assert backtest.ledger.position(XAU).is_flat


# ------------------------------------------------- orchestration invariant ---
class TestOrchestrationInvariants:
    def test_backtest_reuses_the_production_components(self):
        """Phase 16 §2-3: simulation orchestrates, it does not reimplement."""
        from ShadBotTrader.application.services.execution_service import ExecutionService
        from ShadBotTrader.application.services.trading_decision_service import (
            TradingDecisionService,
        )

        backtest = service()
        engine = backtest.build("wiring", XAU, TF, rising(10))

        assert isinstance(engine._trading, TradingDecisionService)
        assert isinstance(engine._execution, ExecutionService)

    def test_every_fill_is_journalled_and_risk_approved(self):
        backtest = service()
        backtest.run("audit", XAU, TF, rising(40))

        assert backtest.decision_journal is not None
        assert backtest.execution_journal is not None

        for entry in backtest.decision_journal.entries():
            if entry.intent is not None:
                assert entry.verdict is not None and entry.verdict.approved

        for entry in backtest.execution_journal.entries():
            if entry.executed:
                assert entry.result is not None and entry.result.filled_quantity > 0

    def test_ledger_and_metrics_agree(self):
        """The reported return must match the books, not a separate tally."""
        backtest = service()
        result = backtest.run("agree", XAU, TF, falling(40))

        assert backtest.ledger is not None
        final_point = result.equity_curve.points[-1]
        assert final_point.realized_pnl == backtest.ledger.realized_pnl.amount
        assert final_point.cash == backtest.ledger.cash.amount

    def test_no_lookahead_the_clock_never_precedes_the_bar(self):
        candles = rising(20)
        engine = service().build("causal", XAU, TF, candles)
        engine.session.start()

        seen = []
        while True:
            event = engine.step()
            if event is None:
                break
            # the clock is exactly at the bar being processed, never ahead
            assert engine.clock.current_time == event.event_time
            seen.append(event.event_time.value)

        assert seen == sorted(seen)


def test_result_to_dict_is_serialisable():
    result = service().run("dict", XAU, TF, rising(20))
    payload = result.to_dict()
    assert payload["status"] == "completed"
    assert payload["bars_processed"] == 20
    assert "max_drawdown_percent" in payload
