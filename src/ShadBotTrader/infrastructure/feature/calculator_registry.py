"""Maps feature id prefixes to calculator implementations."""

from __future__ import annotations

from typing import Dict

from ShadBotTrader.domain.feature.ports import FeatureCalculator
from ShadBotTrader.infrastructure.feature.calculators.atr import AtrCalculator
from ShadBotTrader.infrastructure.feature.calculators.bollinger import BollingerCalculator
from ShadBotTrader.infrastructure.feature.calculators.ema import EmaCalculator
from ShadBotTrader.infrastructure.feature.calculators.macd import MacdCalculator
from ShadBotTrader.infrastructure.feature.calculators.returns import ReturnsCalculator
from ShadBotTrader.infrastructure.feature.calculators.rsi import RsiCalculator
from ShadBotTrader.infrastructure.feature.calculators.sma import SmaCalculator
from ShadBotTrader.infrastructure.feature.calculators.stochastic import StochasticCalculator


class CalculatorRegistry:
    """Resolves the calculator for a feature id (by base name).

    The base name of ``sma_20`` is ``sma``; of ``macd_12_26_9`` is
    ``macd``. Feature ids are stable even if the calculator behind a
    base name changes (Phase 12, section 5).
    """

    def __init__(self) -> None:
        self._calculators: Dict[str, FeatureCalculator] = {
            "sma": SmaCalculator(),
            "ema": EmaCalculator(),
            "rsi": RsiCalculator(),
            "atr": AtrCalculator(),
            "macd": MacdCalculator(),
            "returns": ReturnsCalculator(),
            "bollinger": BollingerCalculator(),
            "stochastic": StochasticCalculator(),
        }

    def resolve(self, feature_id: str) -> FeatureCalculator | None:
        """Return the calculator for ``feature_id``, or None."""
        base = feature_id.split("_", 1)[0]
        return self._calculators.get(base)

    def register_custom(self, base: str, calculator: FeatureCalculator) -> None:
        """Register a custom calculator for a base name."""
        self._calculators[base] = calculator
