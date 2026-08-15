"""Pipeline-stage contracts and intermediate results of the Data Platform.

These are the domain-level ports for the three core stages of ingestion.
The concrete implementations live in infrastructure; application code
depends only on these interfaces and the intermediate result types.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import List

from ShadBotTrader.domain.dataset.data_schema import DataSchema
from ShadBotTrader.domain.dataset.quality_report import QualityIssue, QualityReport
from ShadBotTrader.domain.dataset.raw_record import RawCandleRecord
from ShadBotTrader.domain.market.candle import Candle
from ShadBotTrader.domain.market.timeframe import Timeframe


@dataclass(frozen=True)
class ValidatedCandleRecord:
    """A raw record that passed schema, type and range checks (L2).

    Prices are ``Decimal`` and the timestamp is timezone-aware, but no
    canonicalisation has happened yet (that is L3).
    """

    symbol: str
    timeframe: str
    open_time: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal


@dataclass(frozen=True)
class ValidationResult:
    """The output of the validation stage (L2)."""

    records: List[ValidatedCandleRecord] = field(default_factory=list)
    issues: List[QualityIssue] = field(default_factory=list)


@dataclass(frozen=True)
class NormalizationResult:
    """The output of the normalization stage (L3)."""

    candles: List[Candle] = field(default_factory=list)
    issues: List[QualityIssue] = field(default_factory=list)


class CandleValidatorPort(ABC):
    """Validates raw candle records (L2)."""

    @property
    @abstractmethod
    def schema(self) -> DataSchema:
        """The schema used for validation."""

    @abstractmethod
    def validate(self, records: List[RawCandleRecord]) -> ValidationResult:
        """Validate raw records and return the validated subset."""


class CandleNormalizerPort(ABC):
    """Canonicalises validated records into domain candles (L3)."""

    @abstractmethod
    def normalize(self, records: List[ValidatedCandleRecord]) -> NormalizationResult:
        """Normalize validated records into domain candles."""


class QualityAnalyzerPort(ABC):
    """Runs the quality engine over a normalized candle list."""

    @abstractmethod
    def analyze(self, candles: List[Candle], timeframe: Timeframe) -> QualityReport:
        """Produce a quality report for ``candles``."""
