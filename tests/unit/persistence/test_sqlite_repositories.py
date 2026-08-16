"""Tests for the SQLite adapters of every domain port.

The behaviour that matters is durability: data written by one instance
must be readable by a fresh one, exactly as it would be after a restart.
"""

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from ShadBotTrader.domain.ai.model_definition import ModelDefinition
from ShadBotTrader.domain.ai.model_identity import ModelId, ModelVersion
from ShadBotTrader.domain.ai.model_types import ModelFamily, ModelType
from ShadBotTrader.domain.ai.ports import ModelRegistry, TrainingRunRepository
from ShadBotTrader.domain.ai.training_run import TrainingRun
from ShadBotTrader.domain.execution.execution_types import ExecutionStatus
from ShadBotTrader.domain.execution.fill import ExecutionResult, Fill
from ShadBotTrader.domain.execution.money import Money
from ShadBotTrader.domain.execution.ports import (
    ExecutionJournal,
    PortfolioLedger,
)
from ShadBotTrader.domain.learning.learning_types import (
    CandidateStatus,
    RejectionReason,
)
from ShadBotTrader.domain.learning.ports import LearningMemory
from ShadBotTrader.domain.market.price import Price
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timestamp import Timestamp
from ShadBotTrader.domain.strategy.ports import DecisionJournal
from ShadBotTrader.domain.strategy.risk_policy import RiskVerdict
from ShadBotTrader.domain.trading.order import OrderSide
from ShadBotTrader.infrastructure.persistence import (
    Database,
    SqliteDecisionJournal,
    SqliteExecutionJournal,
    SqliteExperimentRepository,
    SqliteLearningMemory,
    SqliteModelRegistry,
    SqlitePortfolioLedger,
    SqliteTrainingRunRepository,
    load_ledger,
)
from tests.learning_fixtures import make_candidate, winning_fold

XAU = Symbol("XAUUSD_i")
NOW = datetime(2026, 8, 16, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
def database(tmp_path) -> Database:
    """A file-backed database so reopening can be tested."""
    return Database(tmp_path / "test.db")


def d(value: str) -> Decimal:
    return Decimal(value)


def make_fill(
    side: OrderSide = OrderSide.BUY,
    quantity: str = "2",
    price: str = "2000",
    fee: str | None = None,
    fill_id: str = "f1",
) -> Fill:
    return Fill(
        fill_id=fill_id,
        order_id="o1",
        symbol=XAU,
        side=side,
        quantity=d(quantity),
        price=Price(d(price)),
        executed_at=Timestamp(NOW),
        fee=Money(d(fee), "USD") if fee else None,
    )


def make_result(*fills: Fill, requested: str = "2") -> ExecutionResult:
    return ExecutionResult(
        intent_id="i1",
        order_id="o1",
        status=ExecutionStatus.FILLED,
        requested_quantity=d(requested),
        fills=list(fills),
    )


# ============================================================== ledger ======
class TestSqlitePortfolioLedger:
    def test_implements_the_port(self, database):
        assert isinstance(SqlitePortfolioLedger(database), PortfolioLedger)

    def test_position_survives_a_restart(self, database):
        """The core promise of Sprint P8."""
        first = SqlitePortfolioLedger(database, session_id="s1", starting_cash=d("1000"))
        first.apply(make_result(make_fill(quantity="2", price="2000")))
        assert first.position(XAU).quantity == d("2")

        # a completely fresh object, as if the process restarted
        second = SqlitePortfolioLedger(database, session_id="s1", starting_cash=d("1000"))
        assert second.position(XAU).quantity == d("2")
        assert second.position(XAU).average_entry_price == Price(d("2000"))

    def test_realised_pnl_survives_a_restart(self, database):
        first = SqlitePortfolioLedger(database, session_id="s1", starting_cash=d("1000"))
        first.apply(make_result(make_fill(OrderSide.BUY, "2", "2000", fee="4")))
        first.apply(make_result(make_fill(OrderSide.SELL, "2", "2100", fee="4.2", fill_id="f2")))
        assert first.realized_pnl.amount == d("200")

        second = SqlitePortfolioLedger(database, session_id="s1", starting_cash=d("1000"))
        assert second.realized_pnl.amount == d("200")
        assert second.total_fees.amount == d("8.2")
        assert second.net_realized_pnl.amount == d("191.8")

    def test_cash_is_rebuilt_from_transactions(self, database):
        first = SqlitePortfolioLedger(database, session_id="s1", starting_cash=d("1000"))
        first.apply(make_result(make_fill(OrderSide.BUY, "2", "2000", fee="4")))
        first.apply(make_result(make_fill(OrderSide.SELL, "2", "2100", fee="4.2", fill_id="f2")))
        expected = first.cash.amount

        second = SqlitePortfolioLedger(database, session_id="s1", starting_cash=d("1000"))
        assert second.cash.amount == expected
        assert second.cash.amount == d("1191.8")  # 1000 + 200 - 8.2

    def test_positions_can_be_rebuilt_from_stored_fills(self, database):
        """State must be a consequence of recorded events, not a memory."""
        ledger = SqlitePortfolioLedger(database, session_id="s1")
        ledger.apply(make_result(make_fill(OrderSide.BUY, "2", "2000")))
        ledger.apply(make_result(make_fill(OrderSide.BUY, "2", "2100", fill_id="f2")))

        rebuilt = ledger.rebuild_from_fills()
        assert rebuilt[str(XAU)].quantity == ledger.position(XAU).quantity
        assert rebuilt[str(XAU)].average_entry_price == Price(d("2050"))

    def test_sessions_are_isolated(self, database):
        first = SqlitePortfolioLedger(database, session_id="run-a")
        first.apply(make_result(make_fill(quantity="5")))

        second = SqlitePortfolioLedger(database, session_id="run-b")
        assert second.position(XAU).is_flat
        assert first.position(XAU).quantity == d("5")

    def test_fills_and_transactions_are_stored(self, database):
        ledger = SqlitePortfolioLedger(database, session_id="s1")
        ledger.apply(make_result(make_fill(OrderSide.BUY, "2", "2000", fee="4")))
        ledger.apply(make_result(make_fill(OrderSide.SELL, "2", "2100", fee="4.2", fill_id="f2")))

        assert len(ledger.stored_fills()) == 2
        kinds = [entry["transaction_type"] for entry in ledger.transactions()]
        assert kinds.count("fee") == 2
        assert kinds.count("trade") == 1  # only the close realised PnL

    def test_load_ledger_returns_none_for_unknown_session(self, database):
        assert load_ledger(database, "never-existed") is None

    def test_load_ledger_reopens_a_known_session(self, database):
        SqlitePortfolioLedger(database, session_id="s1").apply(make_result(make_fill(quantity="3")))
        reopened = load_ledger(database, "s1")
        assert reopened is not None
        assert reopened.position(XAU).quantity == d("3")


# ============================================================= journals =====
class TestSqliteJournals:
    def _decision(self):
        from ShadBotTrader.domain.market.timeframe import Timeframe
        from ShadBotTrader.domain.strategy.strategy_types import SignalType
        from ShadBotTrader.infrastructure.trading import PositionAwareDecisionEngine
        from tests.unit.strategy.conftest import flat_portfolio, make_context, make_signal

        timeframe = Timeframe("5M")
        return PositionAwareDecisionEngine().decide(
            make_signal(XAU, timeframe, SignalType.BUY),
            make_context(XAU, timeframe, portfolio=flat_portfolio()),
        )

    def test_decision_journal_implements_the_port(self, database):
        assert isinstance(SqliteDecisionJournal(database), DecisionJournal)

    def test_decisions_survive_a_restart(self, database):
        first = SqliteDecisionJournal(database, session_id="s1")
        first.record(self._decision(), RiskVerdict.approve(), None)
        assert len(first.entries()) == 1

        second = SqliteDecisionJournal(database, session_id="s1")
        assert second.entries() == []  # live buffer is per-instance
        assert second.stored_count() == 1  # but the record persisted

    def test_rejections_are_counted_by_the_database(self, database):
        journal = SqliteDecisionJournal(database, session_id="s1")
        decision = self._decision()
        journal.record(decision, RiskVerdict.reject(RejectionReason.NEGATIVE_RETURN))
        journal.record(decision, RiskVerdict.reject(RejectionReason.NEGATIVE_RETURN))
        journal.record(decision, RiskVerdict.approve())

        counts = journal.rejection_counts()
        assert counts["negative_return"] == 2

    def test_sessions_are_listed(self, database):
        SqliteDecisionJournal(database, "run-a").record(self._decision())
        SqliteDecisionJournal(database, "run-b").record(self._decision())
        assert SqliteDecisionJournal(database).sessions() == ["run-a", "run-b"]

    def test_execution_journal_implements_the_port(self, database):
        assert isinstance(SqliteExecutionJournal(database), ExecutionJournal)


# ============================================================== learning ====
class TestSqliteLearningMemory:
    def test_implements_the_port(self, database):
        assert isinstance(SqliteLearningMemory(database), LearningMemory)

    def test_candidates_survive_a_restart(self, database):
        """Without this, every run re-explores the same dead ends."""
        first = SqliteLearningMemory(database)
        candidate = make_candidate(
            "c1", in_sample="5", folds=[winning_fold("2"), winning_fold("3")]
        )
        first.remember(candidate)

        second = SqliteLearningMemory(database)
        recalled = second.recall(candidate.configuration.signature)
        assert recalled is not None
        assert recalled.candidate_id == "c1"
        assert recalled.in_sample_score == d("5")
        assert recalled.out_of_sample_score == d("2.5")

    def test_rejection_reason_is_preserved(self, database):
        memory = SqliteLearningMemory(database)
        candidate = make_candidate("bad", folds=[winning_fold()])
        candidate.reject(RejectionReason.OVERFIT_SUSPECTED, "gap too wide")
        memory.remember(candidate)

        recalled = SqliteLearningMemory(database).recall(candidate.configuration.signature)
        assert recalled is not None
        assert recalled.status is CandidateStatus.REJECTED
        assert recalled.rejection_reason is RejectionReason.OVERFIT_SUSPECTED
        assert "gap too wide" in recalled.notes

    def test_already_tried_detects_a_repeat(self, database):
        memory = SqliteLearningMemory(database)
        candidate = make_candidate("c1", folds=[winning_fold()])
        assert not memory.already_tried(candidate.configuration)
        memory.remember(candidate)
        assert memory.already_tried(candidate.configuration)

    def test_remember_is_idempotent_per_configuration(self, database):
        memory = SqliteLearningMemory(database)
        candidate = make_candidate("c1", folds=[winning_fold()])
        memory.remember(candidate)
        memory.remember(candidate)
        assert len(memory) == 1

    def test_known_failures_and_counts(self, database):
        memory = SqliteLearningMemory(database)
        good = make_candidate("good", folds=[winning_fold()], config={"lookback": 1})
        bad = make_candidate("bad", folds=[winning_fold()], config={"lookback": 2})
        bad.reject(RejectionReason.INSUFFICIENT_TRADES)
        memory.remember(good)
        memory.remember(bad)

        assert len(memory.known_failures()) == 1
        assert memory.rejection_counts()["insufficient_trades"] == 1

    def test_best_recorded_ranks_on_out_of_sample(self, database):
        memory = SqliteLearningMemory(database)
        memory.remember(make_candidate("weak", folds=[winning_fold("1")], config={"lookback": 1}))
        memory.remember(make_candidate("strong", folds=[winning_fold("9")], config={"lookback": 2}))
        best = memory.best_recorded()
        assert best is not None and best.candidate_id == "strong"


class TestSqliteExperimentRepository:
    def test_experiment_payload_is_stored(self, database):
        from ShadBotTrader.domain.learning.experiment import (
            LearningExperiment,
            WalkForwardPlan,
        )

        repository = SqliteExperimentRepository(database)
        experiment = LearningExperiment(
            experiment_id="e1",
            objective_name="risk_adjusted_return",
            plan=WalkForwardPlan.split(100, 0.5, 2),
            hypothesis="a tuned lookback wins",
        )
        repository.save(experiment)

        row = SqliteExperimentRepository(database).stored_row("e1")
        assert row is not None
        assert row["objective"] == "risk_adjusted_return"
        assert row["hypothesis"] == "a tuned lookback wins"


# ============================================================ registries ====
class TestSqliteRegistries:
    def _definition(self, version: int = 1) -> ModelDefinition:
        return ModelDefinition(
            model_id=ModelId("gold_direction"),
            version=ModelVersion(version),
            name="Gold direction",
            model_type=ModelType.CLASSIFICATION,
            family=ModelFamily.WAVENET,
            feature_set_name="FXTradingFeatureSetV1",
            feature_set_version=1,
            target_name="direction",
            hyperparameters={"window_size": 16, "learning_rate": 0.00015},
        )

    def test_model_registry_implements_the_port(self, database):
        assert isinstance(SqliteModelRegistry(database), ModelRegistry)

    def test_model_survives_a_restart_with_its_hyperparameters(self, database):
        SqliteModelRegistry(database).register(self._definition())

        reopened = SqliteModelRegistry(database).get(ModelId("gold_direction"), ModelVersion(1))
        assert reopened is not None
        assert reopened.name == "Gold direction"
        assert reopened.family is ModelFamily.WAVENET
        assert reopened.hyperparameters["window_size"] == 16

    def test_latest_version_is_tracked(self, database):
        registry = SqliteModelRegistry(database)
        registry.register(self._definition(1))
        registry.register(self._definition(3))
        registry.register(self._definition(2))

        latest = registry.latest_version(ModelId("gold_direction"))
        assert latest is not None and latest.number == 3

    def test_unknown_model_returns_none(self, database):
        registry = SqliteModelRegistry(database)
        assert registry.get(ModelId("nope"), ModelVersion(1)) is None
        assert registry.latest_version(ModelId("nope")) is None

    def test_training_run_repository_implements_the_port(self, database):
        assert isinstance(SqliteTrainingRunRepository(database), TrainingRunRepository)

    def test_training_run_survives_a_restart(self, database):
        run = TrainingRun(
            run_id="r1",
            model_id=ModelId("gold_direction"),
            model_version=ModelVersion(1),
            dataset_version=2,
            feature_set_name="FXTradingFeatureSetV1",
            feature_set_version=1,
            seed=42,
            hyperparameters={"epochs": 2},
        )
        SqliteTrainingRunRepository(database).record(run)

        reopened = SqliteTrainingRunRepository(database).get("r1")
        assert reopened is not None
        assert reopened.seed == 42
        assert reopened.dataset_version == 2
        assert reopened.hyperparameters["epochs"] == 2

    def test_runs_are_listed_per_model(self, database):
        repository = SqliteTrainingRunRepository(database)
        for index in range(3):
            repository.record(
                TrainingRun(
                    run_id=f"r{index}",
                    model_id=ModelId("gold_direction"),
                    model_version=ModelVersion(1),
                    dataset_version=1,
                    feature_set_name="fs",
                    feature_set_version=1,
                    seed=index,
                )
            )
        assert len(repository.list_for_model(ModelId("gold_direction"))) == 3
