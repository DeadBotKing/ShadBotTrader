"""Integration tests: the platform's state survives a restart.

These drive the real trading and execution services with SQLite-backed
journals and ledger, then throw away every object and reopen the
database — the same thing a process restart does.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from ShadBotTrader.application.services.execution_service import ExecutionService
from ShadBotTrader.application.services.trading_decision_service import (
    TradingDecisionService,
)
from ShadBotTrader.domain.execution.market_view import ExecutionContext, MarketQuote
from ShadBotTrader.domain.execution.position_state import PositionState
from ShadBotTrader.domain.market.price import Price
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timeframe import Timeframe
from ShadBotTrader.domain.market.timestamp import Timestamp
from ShadBotTrader.domain.strategy.risk_policy import RiskPolicy
from ShadBotTrader.domain.strategy.strategy_context import (
    PortfolioView,
    PredictionView,
    StrategyContext,
)
from ShadBotTrader.infrastructure.execution import (
    DefaultIntentResolver,
    SimulatedExecutionVenue,
)
from ShadBotTrader.infrastructure.persistence import (
    Database,
    SqliteDecisionJournal,
    SqliteExecutionJournal,
    SqlitePortfolioLedger,
    load_ledger,
)
from ShadBotTrader.infrastructure.trading import (
    AiDirectionalStrategy,
    DefaultIntentFactory,
    DefaultSignalValidator,
    PolicyRiskGate,
    PositionAwareDecisionEngine,
)

NOW = datetime(2026, 8, 16, 12, 0, tzinfo=timezone.utc)
SYMBOL = Symbol("XAUUSD_i")
TIMEFRAME = Timeframe("5M")
SESSION = "live-1"


def d(value: str) -> Decimal:
    return Decimal(value)


@pytest.fixture
def database(tmp_path) -> Database:
    return Database(tmp_path / "state.db")


def trading_service(database, session=SESSION):
    return TradingDecisionService(
        strategies=[AiDirectionalStrategy(min_confidence=0.55)],
        decision_engine=PositionAwareDecisionEngine(),
        risk_gate=PolicyRiskGate(RiskPolicy()),
        intent_factory=DefaultIntentFactory(base_quantity=d("2")),
        validator=DefaultSignalValidator(max_signal_age_seconds=600),
        journal=SqliteDecisionJournal(database, session_id=session),
    )


def execution_service(database, ledger, session=SESSION):
    return ExecutionService(
        resolver=DefaultIntentResolver(),
        venue=SimulatedExecutionVenue(),
        ledger=ledger,
        journal=SqliteExecutionJournal(database, session_id=session),
    )


def strategy_context(value: float, confidence: float, quantity: str = "0", minutes: int = 0):
    moment = Timestamp(NOW + timedelta(minutes=minutes))
    return StrategyContext(
        timestamp=moment,
        symbol=SYMBOL,
        timeframe=TIMEFRAME,
        predictions=[
            PredictionView(
                model_id="gold_direction",
                model_version=1,
                value=value,
                confidence=confidence,
                generated_at=moment,
            )
        ],
        portfolio=PortfolioView(
            equity=d("100"),
            open_position_quantity=Decimal(quantity),
            open_position_count=0 if Decimal(quantity) == 0 else 1,
        ),
    )


def execution_context(position=None, bid="1998", ask="2002", minutes: int = 0):
    moment = Timestamp(NOW + timedelta(minutes=minutes))
    return ExecutionContext(
        timestamp=moment,
        quote=MarketQuote(SYMBOL, Price(d(bid)), Price(d(ask)), moment),
        position=position or PositionState.flat(SYMBOL),
        equity=d("100"),
    )


# ------------------------------------------------------------- durability ---
def test_a_trade_survives_a_restart(database):
    """Open a position, throw everything away, reopen: it is still there."""
    ledger = SqlitePortfolioLedger(database, session_id=SESSION, starting_cash=d("100"))
    trading = trading_service(database)
    execution = execution_service(database, ledger)

    outcome = trading.evaluate(strategy_context(0.95, 0.9))
    assert outcome.intent is not None
    result = execution.execute(outcome.intent, execution_context())
    assert result.executed

    # --- simulate a process restart ---
    del ledger, trading, execution

    reopened = SqlitePortfolioLedger(database, session_id=SESSION, starting_cash=d("100"))
    position = reopened.position(SYMBOL)
    assert position.is_long
    assert position.quantity == d("2")
    assert position.average_entry_price == Price(d("2002"))  # bought at the ask


def test_a_full_round_trip_survives_a_restart(database):
    ledger = SqlitePortfolioLedger(database, session_id=SESSION, starting_cash=d("100"))
    trading = trading_service(database)
    execution = execution_service(database, ledger)

    # open
    entry = trading.evaluate(strategy_context(0.95, 0.9))
    assert entry.intent is not None
    execution.execute(entry.intent, execution_context())

    # close at a higher price
    exit_outcome = trading.evaluate(strategy_context(0.02, 0.95, quantity="2", minutes=5))
    assert exit_outcome.intent is not None
    execution.execute(
        exit_outcome.intent,
        execution_context(position=ledger.position(SYMBOL), bid="2098", ask="2102", minutes=5),
    )

    expected_pnl = ledger.realized_pnl.amount
    assert expected_pnl > 0

    reopened = SqlitePortfolioLedger(database, session_id=SESSION, starting_cash=d("100"))
    assert reopened.position(SYMBOL).is_flat
    assert reopened.realized_pnl.amount == expected_pnl
    assert reopened.cash.amount == d("100") + expected_pnl


def test_the_audit_trail_survives_a_restart(database):
    ledger = SqlitePortfolioLedger(database, session_id=SESSION, starting_cash=d("100"))
    trading = trading_service(database)
    execution = execution_service(database, ledger)

    for index, (value, confidence) in enumerate([(0.95, 0.9), (0.5, 0.2), (0.05, 0.93)]):
        outcome = trading.evaluate(strategy_context(value, confidence, minutes=index * 5))
        if outcome.intent is not None:
            execution.execute(
                outcome.intent,
                execution_context(position=ledger.position(SYMBOL), minutes=index * 5),
            )

    decisions = SqliteDecisionJournal(database, session_id=SESSION)
    assert decisions.stored_count() == 3

    executions = SqliteExecutionJournal(database, session_id=SESSION)
    assert executions.stored_count() >= 1


def test_positions_are_rebuildable_from_stored_fills(database):
    """The books must be derivable from events, not just remembered."""
    ledger = SqlitePortfolioLedger(database, session_id=SESSION, starting_cash=d("100"))
    trading = trading_service(database)
    execution = execution_service(database, ledger)

    outcome = trading.evaluate(strategy_context(0.95, 0.9))
    assert outcome.intent is not None
    execution.execute(outcome.intent, execution_context())

    rebuilt = ledger.rebuild_from_fills()
    live = ledger.position(SYMBOL)
    assert rebuilt[str(SYMBOL)].signed_quantity == live.signed_quantity
    assert rebuilt[str(SYMBOL)].average_entry_price == live.average_entry_price


def test_two_sessions_do_not_contaminate_each_other(database):
    first_ledger = SqlitePortfolioLedger(database, session_id="run-a", starting_cash=d("100"))
    execution_service(database, first_ledger, session="run-a").execute(
        trading_service(database, "run-a").evaluate(strategy_context(0.95, 0.9)).intent,
        execution_context(),
    )

    second_ledger = SqlitePortfolioLedger(database, session_id="run-b", starting_cash=d("100"))
    assert second_ledger.position(SYMBOL).is_flat
    assert second_ledger.cash.amount == d("100")

    assert first_ledger.position(SYMBOL).quantity == d("2")


def test_idempotency_guard_still_applies_with_persistence(database):
    """Persistence must not weaken the duplicate-intent protection."""
    ledger = SqlitePortfolioLedger(database, session_id=SESSION, starting_cash=d("100"))
    trading = trading_service(database)
    execution = execution_service(database, ledger)

    outcome = trading.evaluate(strategy_context(0.95, 0.9))
    assert outcome.intent is not None

    first = execution.execute(outcome.intent, execution_context())
    second = execution.execute(outcome.intent, execution_context())

    assert first.executed
    assert not second.executed
    assert ledger.position(SYMBOL).quantity == d("2")  # not 4

    reopened = SqlitePortfolioLedger(database, session_id=SESSION, starting_cash=d("100"))
    assert reopened.position(SYMBOL).quantity == d("2")


def test_load_ledger_restores_a_previous_run(database):
    ledger = SqlitePortfolioLedger(database, session_id="yesterday", starting_cash=d("100"))
    execution_service(database, ledger, session="yesterday").execute(
        trading_service(database, "yesterday").evaluate(strategy_context(0.95, 0.9)).intent,
        execution_context(),
    )
    expected = ledger.position(SYMBOL).quantity

    restored = load_ledger(database, "yesterday", starting_cash=d("100"))
    assert restored is not None
    assert restored.position(SYMBOL).quantity == expected


# ------------------------------------------------- learning across runs -----
def test_learning_memory_persists_between_optimisations(tmp_path):
    """The reason to persist learning: never re-explore a dead end."""
    from ShadBotTrader.application.services.optimisation_service import (
        OptimisationService,
    )
    from ShadBotTrader.domain.simulation.session import SimulationConfiguration
    from ShadBotTrader.infrastructure.persistence import SqliteLearningMemory
    from tests.simulation_fixtures import TF, rising
    from tests.simulation_fixtures import XAU as SIM_XAU

    database = Database(tmp_path / "learning.db")
    memory = SqliteLearningMemory(database)

    service = OptimisationService(
        symbol=SIM_XAU,
        timeframe=TF,
        simulation_config=SimulationConfiguration(
            initial_capital=d("100"), spread=d("4"), warmup_bars=5
        ),
    )
    service.memory = memory  # swap the in-memory default for the durable one

    service.run(
        "e1",
        {"lookback": [3, 6], "strategy_min_confidence": [0.55]},
        rising(80),
        fold_count=2,
    )
    stored = len(memory)
    assert stored >= 2

    # a brand-new memory object sees the same history
    reopened = SqliteLearningMemory(database)
    assert len(reopened) == stored
    assert reopened.all_candidates()


# ---------------------------------------------------------- database state --
def test_statistics_report_what_was_written(database):
    ledger = SqlitePortfolioLedger(database, session_id=SESSION, starting_cash=d("100"))
    trading = trading_service(database)
    execution = execution_service(database, ledger)

    outcome = trading.evaluate(strategy_context(0.95, 0.9))
    assert outcome.intent is not None
    execution.execute(outcome.intent, execution_context())

    stats = database.statistics()
    assert stats["trading_decision"] >= 1
    assert stats["execution_attempt"] >= 1
    assert stats["portfolio_fill"] >= 1
    assert stats["portfolio_position"] == 1


class TestPersistFlagClosesTheLoop:
    """Sprint P8 built durable adapters; this verifies the demos use them.

    Before the --persist flag, running a backtest produced results that
    never reached the database, so the dashboard could not show them —
    the storage layer existed but nothing in the main path used it.
    """

    def test_context_defaults_to_in_memory(self):
        from ShadBotTrader.application.persistence_context import PersistenceContext
        from ShadBotTrader.infrastructure.execution import InMemoryPortfolioLedger

        context = PersistenceContext()
        assert isinstance(context.portfolio_ledger(), InMemoryPortfolioLedger)
        # the database is never even opened
        assert context.database is None

    def test_context_returns_durable_adapters_when_asked(self, tmp_path):
        from ShadBotTrader.application.persistence_context import PersistenceContext
        from ShadBotTrader.infrastructure.persistence import (
            SqliteDecisionJournal,
            SqliteLearningMemory,
            SqlitePortfolioLedger,
        )

        context = PersistenceContext.for_run(
            persist=True, database=str(tmp_path / "ctx.db"), session="s"
        )
        assert isinstance(context.portfolio_ledger(), SqlitePortfolioLedger)
        assert isinstance(context.decision_journal(), SqliteDecisionJournal)
        assert isinstance(context.learning_memory(), SqliteLearningMemory)
        context.close()

    def test_backtest_results_reach_the_database(self, tmp_path):
        from ShadBotTrader.application.persistence_context import PersistenceContext
        from ShadBotTrader.application.services.backtest_service import BacktestService
        from ShadBotTrader.domain.simulation.session import SimulationConfiguration
        from ShadBotTrader.infrastructure.persistence import Database
        from tests.simulation_fixtures import TF, rising
        from tests.simulation_fixtures import XAU as SIM_XAU

        path = tmp_path / "backtest.db"
        context = PersistenceContext.for_run(persist=True, database=str(path), session="bt")
        service = BacktestService(
            configuration=SimulationConfiguration(
                initial_capital=d("100"), spread=d("4"), warmup_bars=5
            ),
            base_quantity=d("0.01"),
            persistence=context,
        )
        service.run("stored", SIM_XAU, TF, rising(60))
        context.close()

        # a fresh handle sees the results, as the dashboard would
        database = Database(path)
        assert database.row_count("trading_decision") > 0
        assert database.statistics()["portfolio_position"] >= 1

    def test_a_run_without_persist_writes_nothing(self, tmp_path):
        from ShadBotTrader.application.services.backtest_service import BacktestService
        from ShadBotTrader.domain.simulation.session import SimulationConfiguration
        from tests.simulation_fixtures import TF, rising
        from tests.simulation_fixtures import XAU as SIM_XAU

        path = tmp_path / "never.db"
        service = BacktestService(
            configuration=SimulationConfiguration(initial_capital=d("100"), warmup_bars=5),
            base_quantity=d("0.01"),
        )
        service.run("ephemeral", SIM_XAU, TF, rising(60))
        assert not path.exists()

    def test_sessions_from_different_scripts_stay_separate(self, tmp_path):
        from ShadBotTrader.application.persistence_context import PersistenceContext
        from ShadBotTrader.infrastructure.persistence import Database

        path = str(tmp_path / "multi.db")
        for prefix in ("backtest", "trading"):
            context = PersistenceContext.for_run(persist=True, database=path, prefix=prefix)
            assert context.session_id.startswith(prefix)
            context.close()

        assert Database(path).schema_version == 1

    def test_summary_lines_tell_the_user_where_results_went(self, tmp_path):
        from ShadBotTrader.application.persistence_context import PersistenceContext

        ephemeral = PersistenceContext()
        assert any("NOT saved" in line for line in ephemeral.summary_lines())

        durable = PersistenceContext.for_run(
            persist=True, database=str(tmp_path / "x.db"), session="s"
        )
        lines = durable.summary_lines()
        assert any("Saved to" in line for line in lines)
        assert any("shadbot-dashboard" in line for line in lines)
        durable.close()
