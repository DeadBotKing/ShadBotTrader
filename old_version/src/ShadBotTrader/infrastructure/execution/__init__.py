"""Execution & Portfolio infrastructure — Phase 14 §19-24, Phase 15.

Concrete adapters for the ports in ``domain.execution.ports``:

* :class:`DefaultIntentResolver` — policies -> concrete order
* :class:`SimulatedExecutionVenue` — deterministic fills with spread,
  slippage, commission and partial execution
* :class:`InMemoryPortfolioLedger` — fill-based position & PnL accounting
* :class:`InMemoryExecutionJournal` — the execution audit trail
"""

from ShadBotTrader.infrastructure.execution.execution_journal import (
    InMemoryExecutionJournal,
)
from ShadBotTrader.infrastructure.execution.intent_resolver import DefaultIntentResolver
from ShadBotTrader.infrastructure.execution.portfolio_ledger import (
    InMemoryPortfolioLedger,
    Transaction,
)
from ShadBotTrader.infrastructure.execution.simulated_venue import SimulatedExecutionVenue

__all__ = [
    "DefaultIntentResolver",
    "InMemoryExecutionJournal",
    "InMemoryPortfolioLedger",
    "SimulatedExecutionVenue",
    "Transaction",
]
