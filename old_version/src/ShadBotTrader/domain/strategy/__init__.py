"""Trading (strategy) domain — Phase 14.

The pipeline this package models::

    StrategyContext -> Strategy -> TradingSignal
                                      |
                                 SignalValidator
                                      |
                                 DecisionEngine -> TradingDecision
                                      |
                                   RiskGate  (mandatory)
                                      |
                                 IntentFactory -> TradingIntent
                                      |
                              Execution Platform (future)

Invariants: a strategy emits signals, not orders; a decision is not an
order; and nothing becomes an intent without passing the risk gate.
"""

from ShadBotTrader.domain.strategy.decision import TradingDecision
from ShadBotTrader.domain.strategy.ports import (
    DecisionEngine,
    DecisionJournal,
    IntentFactory,
    JournalEntry,
    RiskGate,
    SignalAggregator,
    SignalValidator,
    Strategy,
)
from ShadBotTrader.domain.strategy.risk_policy import RiskPolicy, RiskVerdict
from ShadBotTrader.domain.strategy.signal import TradingSignal
from ShadBotTrader.domain.strategy.strategy_context import (
    PortfolioView,
    PredictionView,
    StrategyContext,
)
from ShadBotTrader.domain.strategy.strategy_identity import StrategyId, StrategyVersion
from ShadBotTrader.domain.strategy.strategy_types import (
    DecisionType,
    IntentType,
    MarketRegime,
    PricePolicyType,
    QuantityPolicyType,
    RejectionReason,
    SignalStrength,
    SignalType,
    StrategyState,
)
from ShadBotTrader.domain.strategy.trading_intent import (
    PricePolicy,
    QuantityPolicy,
    TradingIntent,
)

__all__ = [
    "DecisionEngine",
    "DecisionJournal",
    "DecisionType",
    "IntentFactory",
    "IntentType",
    "JournalEntry",
    "MarketRegime",
    "PortfolioView",
    "PredictionView",
    "PricePolicy",
    "PricePolicyType",
    "QuantityPolicy",
    "QuantityPolicyType",
    "RejectionReason",
    "RiskGate",
    "RiskPolicy",
    "RiskVerdict",
    "SignalAggregator",
    "SignalStrength",
    "SignalType",
    "SignalValidator",
    "Strategy",
    "StrategyContext",
    "StrategyId",
    "StrategyState",
    "StrategyVersion",
    "TradingDecision",
    "TradingIntent",
    "TradingSignal",
]
