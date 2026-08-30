"""Maps calculator families to calculator implementations."""

from __future__ import annotations

from typing import Dict

from ShadBotTrader.domain.feature.ports import FeatureCalculator
from ShadBotTrader.infrastructure.feature.calculators.adaptive_filters import (
    AdaptiveFiltersCalculator,
)
from ShadBotTrader.infrastructure.feature.calculators.atr import AtrCalculator
from ShadBotTrader.infrastructure.feature.calculators.balance import BalanceCalculator
from ShadBotTrader.infrastructure.feature.calculators.bollinger import BollingerCalculator
from ShadBotTrader.infrastructure.feature.calculators.bollinger_bands import (
    BollingerBandsCalculator,
)
from ShadBotTrader.infrastructure.feature.calculators.candle_pattern import CandlePatternCalculator
from ShadBotTrader.infrastructure.feature.calculators.divergence import DivergenceCalculator
from ShadBotTrader.infrastructure.feature.calculators.ehlers_advanced import (
    EhlersAdvancedCalculator,
)
from ShadBotTrader.infrastructure.feature.calculators.ehlers_cycle import EhlersCycleCalculator
from ShadBotTrader.infrastructure.feature.calculators.ema import EmaCalculator
from ShadBotTrader.infrastructure.feature.calculators.fourier import FourierCalculator
from ShadBotTrader.infrastructure.feature.calculators.fractal_stats import FractalStatsCalculator
from ShadBotTrader.infrastructure.feature.calculators.ichimoku import IchimokuCalculator
from ShadBotTrader.infrastructure.feature.calculators.macd import MacdCalculator
from ShadBotTrader.infrastructure.feature.calculators.market_regime import MarketRegimeCalculator
from ShadBotTrader.infrastructure.feature.calculators.mean_reversion import MeanReversionCalculator
from ShadBotTrader.infrastructure.feature.calculators.momentum_advanced import (
    MomentumAdvancedCalculator,
)
from ShadBotTrader.infrastructure.feature.calculators.noise_filter import (
    NoiseFilterCalculator,
)
from ShadBotTrader.infrastructure.feature.calculators.pca import PcaCalculator
from ShadBotTrader.infrastructure.feature.calculators.prado_features import PradoFeaturesCalculator
from ShadBotTrader.infrastructure.feature.calculators.price_context import PriceContextCalculator
from ShadBotTrader.infrastructure.feature.calculators.price_filter import PriceFilterCalculator
from ShadBotTrader.infrastructure.feature.calculators.returns import ReturnsCalculator
from ShadBotTrader.infrastructure.feature.calculators.rsi import RsiCalculator
from ShadBotTrader.infrastructure.feature.calculators.session_time import SessionTimeCalculator
from ShadBotTrader.infrastructure.feature.calculators.sma import SmaCalculator
from ShadBotTrader.infrastructure.feature.calculators.stochastic import StochasticCalculator
from ShadBotTrader.infrastructure.feature.calculators.structure_features import (
    StructureFeaturesCalculator,
)
from ShadBotTrader.infrastructure.feature.calculators.target import TargetCalculator
from ShadBotTrader.infrastructure.feature.calculators.trend_strength import TrendStrengthCalculator
from ShadBotTrader.infrastructure.feature.calculators.volatility_breakout import (
    VolatilityBreakoutCalculator,
)
from ShadBotTrader.infrastructure.feature.calculators.volume_analysis import (
    VolumeAnalysisCalculator,
)


class CalculatorRegistry:
    """Resolves the calculator for a computation family name.

    Families: ``sma``, ``ema``, ``rsi``, ``atr``, ``macd``,
    ``returns``, ``bollinger``, ``bband``, ``stochastic``,
    ``ichimoku``, ``target``, ``noise_filter``, ``fourier``,
    ``balance``, ``pca``, ``divergence``,
    ``volatility_breakout``, ``trend_strength``,
    ``mean_reversion``, ``candle_pattern``, ``market_regime``,
    ``price_filter``, ``volume_analysis``,
    ``momentum_advanced``, ``session_time``.
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
            # --- فیچرهای جدید (استراتژی‌محور) ---
            "volatility_breakout": VolatilityBreakoutCalculator(),
            "trend_strength": TrendStrengthCalculator(),
            "mean_reversion": MeanReversionCalculator(),
            "candle_pattern": CandlePatternCalculator(),
            "market_regime": MarketRegimeCalculator(),
            # --- فیچرهای جدید (دور دوم) ---
            "price_filter": PriceFilterCalculator(),
            "volume_analysis": VolumeAnalysisCalculator(),
            "momentum_advanced": MomentumAdvancedCalculator(),
            "session_time": SessionTimeCalculator(),
            # --- فیچرهای جدید (دور سوم — عمقی) ---
            "adaptive_filters": AdaptiveFiltersCalculator(),
            "ehlers_cycle": EhlersCycleCalculator(),
            "fractal_stats": FractalStatsCalculator(),
            # --- فیچرهای جدید (دور چهارم — کتاب‌محور) ---
            "ehlers_advanced": EhlersAdvancedCalculator(),
            "prado_features": PradoFeaturesCalculator(),
            "structure_features": StructureFeaturesCalculator(),
            # --- فاز ۹۴: فیچرهای موقعیت قیمت (scale-invariant ratio) ---
            "price_context": PriceContextCalculator(),
        }

    def resolve(self, family: str) -> FeatureCalculator | None:
        """Return the calculator for ``family``, or None."""
        return self._calculators.get(family)

    def register_custom(self, family: str, calculator: FeatureCalculator) -> None:
        """Register a custom calculator for a family name."""
        self._calculators[family] = calculator
