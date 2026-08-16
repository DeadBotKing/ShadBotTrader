"""Maps calculator families to calculator implementations."""

from __future__ import annotations

from typing import Dict

from ShadBotTrader.domain.feature.ports import FeatureCalculator
from ShadBotTrader.infrastructure.feature.calculators.atr import AtrCalculator
from ShadBotTrader.infrastructure.feature.calculators.balance import BalanceCalculator
from ShadBotTrader.infrastructure.feature.calculators.bollinger import BollingerCalculator
from ShadBotTrader.infrastructure.feature.calculators.bollinger_bands import (
    BollingerBandsCalculator,
)
from ShadBotTrader.infrastructure.feature.calculators.divergence import DivergenceCalculator
from ShadBotTrader.infrastructure.feature.calculators.ema import EmaCalculator
from ShadBotTrader.infrastructure.feature.calculators.fourier import FourierCalculator
from ShadBotTrader.infrastructure.feature.calculators.ichimoku import IchimokuCalculator
from ShadBotTrader.infrastructure.feature.calculators.macd import MacdCalculator
from ShadBotTrader.infrastructure.feature.calculators.noise_filter import (
    NoiseFilterCalculator,
)
from ShadBotTrader.infrastructure.feature.calculators.pca import PcaCalculator
from ShadBotTrader.infrastructure.feature.calculators.returns import ReturnsCalculator
from ShadBotTrader.infrastructure.feature.calculators.rsi import RsiCalculator
from ShadBotTrader.infrastructure.feature.calculators.sma import SmaCalculator
from ShadBotTrader.infrastructure.feature.calculators.stochastic import StochasticCalculator
from ShadBotTrader.infrastructure.feature.calculators.target import TargetCalculator


class CalculatorRegistry:
    """Resolves the calculator for a computation family name.

    Families: ``sma``, ``ema``, ``rsi``, ``atr``, ``macd``,
    ``returns``, ``bollinger``, ``bband``, ``stochastic``,
    ``ichimoku``, ``target``, ``noise_filter``, ``fourier``,
    ``balance``, ``pca``, ``divergence``.
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
            "bband": BollingerBandsCalculator(),
            "stochastic": StochasticCalculator(),
            "ichimoku": IchimokuCalculator(),
            "target": TargetCalculator(),
            "noise_filter": NoiseFilterCalculator(),
            "fourier": FourierCalculator(),
            "balance": BalanceCalculator(),
            "pca": PcaCalculator(),
            "divergence": DivergenceCalculator(),
        }

    def resolve(self, family: str) -> FeatureCalculator | None:
        """Return the calculator for ``family``, or None."""
        return self._calculators.get(family)

    def register_custom(self, family: str, calculator: FeatureCalculator) -> None:
        """Register a custom calculator for a family name."""
        self._calculators[family] = calculator
