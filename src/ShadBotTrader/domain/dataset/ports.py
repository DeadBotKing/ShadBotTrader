"""Ports (contracts) of the dataset domain.

These abstract interfaces are the only thing application code depends
on. Concrete implementations (Parquet storage, CSV providers, in-memory
catalogs) live in ``ShadBotTrader.infrastructure.data``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional

from ShadBotTrader.domain.dataset.dataset_descriptor import DatasetDescriptor
from ShadBotTrader.domain.dataset.dataset_identity import DatasetId
from ShadBotTrader.domain.dataset.raw_record import RawCandleRecord
from ShadBotTrader.domain.market.candle import Candle
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timeframe import Timeframe


class MarketDataProvider(ABC):
    """A data source: produces raw market records.

    Implementations must never validate or transform the data — that is
    the Data Platform's job. This contract only moves raw bytes/rows
    from a source (broker, API, file) into raw records.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """The stable name of this provider."""

    @abstractmethod
    def fetch_candles(self, symbol: str, timeframe: str, source: str) -> List[RawCandleRecord]:
        """Fetch raw candle rows from ``source`` for the given instrument."""


class CandleRepository(ABC):
    """Persistence contract for candle data (raw + normalized)."""

    @abstractmethod
    def save_raw(self, dataset_id: DatasetId, version: int, records: List[RawCandleRecord]) -> None:
        """Persist raw records immutably under ``dataset_id`` + ``version``."""

    @abstractmethod
    def save_normalized(self, dataset_id: DatasetId, version: int, candles: List[Candle]) -> None:
        """Persist normalized candles under ``dataset_id`` + ``version``."""

    @abstractmethod
    def query(
        self,
        symbol: Symbol,
        timeframe: Timeframe,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> List[Candle]:
        """Return normalized candles for a symbol/timeframe within a range."""

    @abstractmethod
    def next_version(self, dataset_id: DatasetId) -> int:
        """Return the next available persisted version for ``dataset_id``.

        The repository is the source of truth for what already exists on
        disk: the next version must never collide with a persisted one.
        """


class DatasetRepository(ABC):
    """Catalog contract: register and look up dataset descriptors."""

    @abstractmethod
    def register(self, descriptor: DatasetDescriptor) -> None:
        """Record a dataset descriptor in the catalog."""

    @abstractmethod
    def get(self, dataset_id: DatasetId) -> Optional[DatasetDescriptor]:
        """Return the latest descriptor for ``dataset_id``, or None."""

    @abstractmethod
    def list_all(self) -> List[DatasetDescriptor]:
        """Return every registered descriptor."""

    @abstractmethod
    def next_version(self, dataset_id: DatasetId) -> int:
        """Return the next available version number for ``dataset_id``."""
