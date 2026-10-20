"""Persistence infrastructure — Phase 20, SQLite adapters.

Everything the platform used to keep in memory now has a durable
implementation behind the *same* domain ports:

===========================  =========================================
port                         SQLite adapter
===========================  =========================================
``DecisionJournal``          :class:`SqliteDecisionJournal`
``ExecutionJournal``         :class:`SqliteExecutionJournal`
``PortfolioLedger``          :class:`SqlitePortfolioLedger`
``LearningMemory``           :class:`SqliteLearningMemory`
``ExperimentRepository``     :class:`SqliteExperimentRepository`
``ModelRegistry``            :class:`SqliteModelRegistry`
``TrainingRunRepository``    :class:`SqliteTrainingRunRepository`
``DatasetRepository``        :class:`SqliteDatasetRepository`
``FeatureRegistry``          :class:`SqliteFeatureRegistry`
===========================  =========================================

SQLite is used rather than SQL Server because it ships inside Python:
no server, no driver, no connection string. Every Phase 20 rule that
matters — migrations, transactions, integrity, audit, and a Domain that
never sees the database — still holds, and a SQL Server adapter can be
added later as a sibling of these classes.
"""

from ShadBotTrader.infrastructure.persistence.database import (
    MIGRATIONS,
    SCHEMA_VERSION,
    Database,
)
from ShadBotTrader.infrastructure.persistence.sqlite_journals import (
    SqliteDecisionJournal,
    SqliteExecutionJournal,
)
from ShadBotTrader.infrastructure.persistence.sqlite_learning import (
    SqliteExperimentRepository,
    SqliteLearningMemory,
)
from ShadBotTrader.infrastructure.persistence.sqlite_ledger import (
    SqlitePortfolioLedger,
    load_ledger,
)
from ShadBotTrader.infrastructure.persistence.sqlite_registries import (
    SqliteDatasetRepository,
    SqliteFeatureRegistry,
    SqliteModelRegistry,
    SqliteTrainingRunRepository,
)

__all__ = [
    "MIGRATIONS",
    "SCHEMA_VERSION",
    "Database",
    "SqliteDatasetRepository",
    "SqliteDecisionJournal",
    "SqliteExecutionJournal",
    "SqliteExperimentRepository",
    "SqliteFeatureRegistry",
    "SqliteLearningMemory",
    "SqliteModelRegistry",
    "SqlitePortfolioLedger",
    "SqliteTrainingRunRepository",
    "load_ledger",
]
