"""Dataset identity and kind value objects."""

from __future__ import annotations

from enum import Enum
from typing import Any

from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.common.value_object import ValueObject


class DataKind(str, Enum):
    """The kind of data a dataset holds."""

    MARKET_CANDLE = "market_candle"
    TICK = "tick"
    ORDER_BOOK = "order_book"
    NEWS = "news"


class DatasetId(ValueObject):
    """The immutable identity of a dataset.

    Identity is the combination of provider, kind, symbol, timeframe and
    layer, so the same market data ingested twice by different providers
    (or into different layers) yields distinct datasets.
    """

    def __init__(
        self,
        provider: str,
        kind: DataKind,
        symbol: str,
        timeframe: str,
        layer: str,
    ) -> None:
        provider_norm = provider.strip()
        symbol_norm = symbol.strip().upper()
        timeframe_norm = timeframe.strip().upper()
        if not provider_norm:
            raise ValidationError("DatasetId provider must not be empty")
        if not symbol_norm:
            raise ValidationError("DatasetId symbol must not be empty")
        if not timeframe_norm:
            raise ValidationError("DatasetId timeframe must not be empty")
        if not layer.strip():
            raise ValidationError("DatasetId layer must not be empty")
        self._provider = provider_norm
        self._kind = kind
        self._symbol = symbol_norm
        self._timeframe = timeframe_norm
        self._layer = layer.strip()

    @property
    def provider(self) -> str:
        return self._provider

    @property
    def kind(self) -> DataKind:
        return self._kind

    @property
    def symbol(self) -> str:
        return self._symbol

    @property
    def timeframe(self) -> str:
        return self._timeframe

    @property
    def layer(self) -> str:
        return self._layer

    @property
    def label(self) -> str:
        """A human-readable, stable label for the dataset."""
        return f"{self._provider}.{self._kind.value}.{self._symbol}.{self._timeframe}.{self._layer}"

    def _value(self) -> tuple[Any, ...]:
        return (
            self._provider,
            self._kind,
            self._symbol,
            self._timeframe,
            self._layer,
        )

    def __str__(self) -> str:
        return self.label
