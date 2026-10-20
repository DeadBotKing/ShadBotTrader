"""Resolved order — a TradingIntent with its policies turned into numbers.

Phase 14, sections 23-24: the Trading Platform only expresses policy
(`QuantityPolicy`, `PricePolicy`); the Execution Platform resolves them
against live account and market state. This value object is the result
of that resolution and the last step before a venue is contacted.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, Mapping, Optional

from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.common.value_object import ValueObject
from ShadBotTrader.domain.market.price import Price
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timestamp import Timestamp
from ShadBotTrader.domain.trading.order import OrderSide, OrderType


class ResolvedOrder(ValueObject):
    """A concrete, executable order derived from an approved intent."""

    def __init__(
        self,
        order_id: str,
        intent_id: str,
        symbol: Symbol,
        side: OrderSide,
        order_type: OrderType,
        quantity: Decimal,
        timestamp: Timestamp,
        limit_price: Optional[Price] = None,
        stop_price: Optional[Price] = None,
        reference_price: Optional[Price] = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        if not order_id.strip():
            raise ValidationError("order_id must not be empty")
        if not intent_id.strip():
            raise ValidationError("A resolved order must reference an intent_id")
        if quantity <= 0:
            raise ValidationError("Resolved order quantity must be positive")
        if order_type is OrderType.LIMIT and limit_price is None:
            raise ValidationError("A LIMIT order requires a limit price")
        if order_type is OrderType.STOP and stop_price is None:
            raise ValidationError("A STOP order requires a stop price")

        self._order_id = order_id.strip()
        self._intent_id = intent_id.strip()
        self._symbol = symbol
        self._side = side
        self._order_type = order_type
        self._quantity = quantity
        self._timestamp = timestamp
        self._limit_price = limit_price
        self._stop_price = stop_price
        self._reference_price = reference_price
        self._metadata: Dict[str, Any] = dict(metadata or {})

    @property
    def order_id(self) -> str:
        return self._order_id

    @property
    def intent_id(self) -> str:
        return self._intent_id

    @property
    def symbol(self) -> Symbol:
        return self._symbol

    @property
    def side(self) -> OrderSide:
        return self._side

    @property
    def order_type(self) -> OrderType:
        return self._order_type

    @property
    def quantity(self) -> Decimal:
        return self._quantity

    @property
    def timestamp(self) -> Timestamp:
        return self._timestamp

    @property
    def limit_price(self) -> Optional[Price]:
        return self._limit_price

    @property
    def stop_price(self) -> Optional[Price]:
        return self._stop_price

    @property
    def reference_price(self) -> Optional[Price]:
        return self._reference_price

    @property
    def metadata(self) -> Dict[str, Any]:
        return dict(self._metadata)

    def _value(self) -> tuple[Any, ...]:
        return (
            self._order_id,
            self._intent_id,
            self._symbol,
            self._side,
            self._order_type,
            self._quantity,
            self._timestamp,
            self._limit_price,
            self._stop_price,
        )
