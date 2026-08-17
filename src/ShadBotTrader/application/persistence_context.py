"""Choosing between in-memory and durable adapters (Sprint P8 + Phase 20).

Every port has two implementations: a fast in-memory one and a
SQLite-backed one. Deciding between them is a composition-root concern,
so it lives here rather than being repeated in each script.

    context = PersistenceContext.for_run(persist=True, database="shadbot.db")
    ledger = context.portfolio_ledger(starting_cash=Decimal("100"))

When ``persist`` is False nothing touches the disk and the database is
never even opened — a backtest sweep should not litter storage unless
the caller asked for it.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Optional

from ShadBotTrader.domain.execution.ports import ExecutionJournal, ReportingLedger
from ShadBotTrader.domain.learning.ports import ExperimentRepository, LearningMemory
from ShadBotTrader.domain.strategy.ports import DecisionJournal

DEFAULT_DATABASE = "shadbot.db"


def default_session_id(prefix: str) -> str:
    """A readable, unique session name, e.g. ``backtest-20260816-1612``."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"{prefix}-{stamp}"


@dataclass
class PersistenceContext:
    """Builds either in-memory or durable adapters, consistently.

    The methods return the *port* types, so callers cannot accidentally
    depend on which implementation they got.
    """

    persist: bool = False
    database_path: str = DEFAULT_DATABASE
    session_id: str = "default"
    currency: str = "USD"

    _database: Optional[object] = None

    @classmethod
    def for_run(
        cls,
        persist: bool = False,
        database: str = DEFAULT_DATABASE,
        session: Optional[str] = None,
        prefix: str = "run",
        currency: str = "USD",
    ) -> "PersistenceContext":
        """Build a context for one script invocation."""
        return cls(
            persist=persist,
            database_path=database,
            session_id=session or default_session_id(prefix),
            currency=currency,
        )

    # -- database ------------------------------------------------------------
    @property
    def database(self):
        """The shared database handle; opened lazily, only when persisting."""
        if not self.persist:
            return None
        if self._database is None:
            from ShadBotTrader.infrastructure.persistence import Database

            self._database = Database(self.database_path)
        return self._database

    def close(self) -> None:
        if self._database is not None:
            self._database.close()  # type: ignore[attr-defined]
            self._database = None

    # -- adapters -------------------------------------------------------------
    def portfolio_ledger(self, starting_cash: Decimal = Decimal("0")) -> ReportingLedger:
        if not self.persist:
            from ShadBotTrader.infrastructure.execution import InMemoryPortfolioLedger

            return InMemoryPortfolioLedger(currency=self.currency, starting_cash=starting_cash)

        from ShadBotTrader.infrastructure.persistence import SqlitePortfolioLedger

        return SqlitePortfolioLedger(
            self.database,  # type: ignore[arg-type]
            session_id=self.session_id,
            currency=self.currency,
            starting_cash=starting_cash,
            autoload=False,
        )

    def decision_journal(self) -> DecisionJournal:
        if not self.persist:
            from ShadBotTrader.infrastructure.trading import InMemoryDecisionJournal

            return InMemoryDecisionJournal()

        from ShadBotTrader.infrastructure.persistence import SqliteDecisionJournal

        return SqliteDecisionJournal(
            self.database,  # type: ignore[arg-type]
            session_id=self.session_id,
        )

    def execution_journal(self) -> ExecutionJournal:
        if not self.persist:
            from ShadBotTrader.infrastructure.execution import InMemoryExecutionJournal

            return InMemoryExecutionJournal()

        from ShadBotTrader.infrastructure.persistence import SqliteExecutionJournal

        return SqliteExecutionJournal(
            self.database,  # type: ignore[arg-type]
            session_id=self.session_id,
        )

    def learning_memory(self) -> LearningMemory:
        if not self.persist:
            from ShadBotTrader.infrastructure.learning import InMemoryLearningMemory

            return InMemoryLearningMemory()

        from ShadBotTrader.infrastructure.persistence import SqliteLearningMemory

        return SqliteLearningMemory(self.database)  # type: ignore[arg-type]

    def experiment_repository(self) -> ExperimentRepository:
        if not self.persist:
            from ShadBotTrader.infrastructure.learning import (
                InMemoryExperimentRepository,
            )

            return InMemoryExperimentRepository()

        from ShadBotTrader.infrastructure.persistence import SqliteExperimentRepository

        return SqliteExperimentRepository(self.database)  # type: ignore[arg-type]

    # -- reporting -------------------------------------------------------------
    @property
    def description(self) -> str:
        """One line describing where results will go."""
        if not self.persist:
            return "in-memory (results are discarded when this run ends)"
        return f"persisted to {self.database_path} as session '{self.session_id}'"

    def summary_lines(self) -> list[str]:
        """Closing advice for a script that just finished."""
        if not self.persist:
            return [
                "Results were NOT saved. Re-run with --persist to keep them",
                "and see them on the dashboard.",
            ]
        return [
            f"Saved to {self.database_path} (session '{self.session_id}').",
            "View it with:",
            f"    shadbot-db --db {self.database_path} positions",
            f"    shadbot-dashboard --db {self.database_path} serve",
        ]

    def __enter__(self) -> "PersistenceContext":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()


def add_persistence_arguments(parser, prefix: str = "run") -> None:
    """Add the standard ``--persist`` flags to an argparse parser.

    Kept here so every script offers the identical interface.
    """
    group = parser.add_argument_group("persistence")
    group.add_argument(
        "--persist",
        action="store_true",
        help="save results to the database so they appear on the dashboard",
    )
    group.add_argument(
        "--db",
        default=DEFAULT_DATABASE,
        help="database file (used with --persist)",
    )
    group.add_argument(
        "--session",
        default=None,
        help=f"session name (default: {prefix}-<timestamp>)",
    )


def context_from_args(args, prefix: str = "run", currency: str = "USD") -> PersistenceContext:
    """Build a context from parsed CLI arguments."""
    return PersistenceContext.for_run(
        persist=getattr(args, "persist", False),
        database=getattr(args, "db", DEFAULT_DATABASE),
        session=getattr(args, "session", None),
        prefix=prefix,
        currency=currency,
    )


def resolve_path(database: str) -> Path:
    return Path(database)
