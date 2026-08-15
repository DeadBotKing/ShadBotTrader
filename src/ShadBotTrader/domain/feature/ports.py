"""Ports (contracts) of the feature domain."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from ShadBotTrader.domain.feature.feature_definition import FeatureDefinition
from ShadBotTrader.domain.feature.feature_result import FeatureResult
from ShadBotTrader.domain.market.candle import Candle
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timeframe import Timeframe


class FeatureInputContext:
    """The input a calculator receives (Phase 12, section 19)."""

    def __init__(self, symbol: Symbol, timeframe: Timeframe, candles: List[Candle]) -> None:
        self._symbol = symbol
        self._timeframe = timeframe
        self._candles = candles

    @property
    def symbol(self) -> Symbol:
        return self._symbol

    @property
    def timeframe(self) -> Timeframe:
        return self._timeframe

    @property
    def candles(self) -> List[Candle]:
        """The candle series, ordered ascending by open time."""
        return self._candles


class FeatureCalculator(ABC):
    """Computes one feature from a candle input context.

    Every calculator must be deterministic and, unless its definition
    declares ``NON_CAUSAL``, strictly causal: it may only use candles up
    to and including the current point (Phase 12, sections 26-28).
    """

    @abstractmethod
    def compute(self, definition: FeatureDefinition, context: FeatureInputContext) -> FeatureResult:
        """Compute ``definition`` over ``context`` and return the result."""


class FeatureRepository(ABC):
    """Persistence contract for computed feature results (section 37-38)."""

    @abstractmethod
    def save(self, feature_id: str, version: int, result: FeatureResult) -> None:
        """Persist a computed feature result immutably."""

    @abstractmethod
    def load(self, feature_id: str, version: int) -> Optional[FeatureResult]:
        """Load a computed feature result, or None when absent."""

    @abstractmethod
    def exists(self, feature_id: str, version: int) -> bool:
        """Return True when the version exists in storage."""

    @abstractmethod
    def next_version(self, feature_id: str) -> int:
        """Return the next available persisted version for ``feature_id``."""


class FeatureRegistry(ABC):
    """Catalog contract for feature definitions (sections 13-14)."""

    @abstractmethod
    def register(self, definition: FeatureDefinition) -> None:
        """Record a feature definition."""

    @abstractmethod
    def get(self, feature_id: str) -> Optional[FeatureDefinition]:
        """Return the definition for ``feature_id``, or None."""

    @abstractmethod
    def list_all(self) -> List[FeatureDefinition]:
        """Return every registered definition."""
