"""Trading Platform infrastructure — Phase 14 implementations.

Concrete adapters for the ports in ``domain.strategy.ports``:

* :class:`AiDirectionalStrategy` — prediction-driven signal generation
* :class:`DefaultSignalValidator` — structural / freshness validation
* :class:`ConfidenceWeightedAggregator` — multi-strategy ensembles
* :class:`PositionAwareDecisionEngine` — signal + position -> decision
* :class:`PolicyRiskGate` — the mandatory risk checkpoint
* :class:`DefaultIntentFactory` — approved decision -> execution contract
* :class:`InMemoryDecisionJournal` — the audit trail
"""

from ShadBotTrader.infrastructure.trading.ai_directional_strategy import AiDirectionalStrategy
from ShadBotTrader.infrastructure.trading.bracket_exit_strategy import BracketExitStrategy
from ShadBotTrader.infrastructure.trading.decision_engine import PositionAwareDecisionEngine
from ShadBotTrader.infrastructure.trading.decision_journal import InMemoryDecisionJournal
from ShadBotTrader.infrastructure.trading.intent_factory import DefaultIntentFactory
from ShadBotTrader.infrastructure.trading.risk_gate import PolicyRiskGate
from ShadBotTrader.infrastructure.trading.signal_aggregator import ConfidenceWeightedAggregator
from ShadBotTrader.infrastructure.trading.signal_validator import DefaultSignalValidator

__all__ = [
    "AiDirectionalStrategy",
    "BracketExitStrategy",
    "ConfidenceWeightedAggregator",
    "DefaultIntentFactory",
    "DefaultSignalValidator",
    "InMemoryDecisionJournal",
    "PolicyRiskGate",
    "PositionAwareDecisionEngine",
]
