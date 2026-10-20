"""Fills and execution results (Phase 15, sections 21-23).

A ``Fill`` is what actually happened at the venue. An order may produce
several fills, and the Portfolio must never assume an order was filled
completely — partial fills are native (section 23).

Average entry price is derived from real fills, never from a trading
intent (section 24).
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List, Mapping, Optional, Sequence

from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.common.value_object import ValueObject
from ShadBotTrader.domain.execution.execution_types import (
    ExecutionRejectionReason,
    ExecutionStatus,
)
from ShadBotTrader.domain.execution.money import Money
from ShadBotTrader.domain.market.price import Price
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timestamp import Timestamp
from ShadBotTrader.domain.trading.order import OrderSide


class Fill(ValueObject):
    """One execution event: a quantity traded at a price, with its fee."""

    def __init__(
        self,
        fill_id: str,
        order_id: str,
        symbol: Symbol,
        side: OrderSide,
        quantity: Decimal,
        price: Price,
        executed_at: Timestamp,
        fee: Optional[Money] = None,
    ) -> None:
        if not fill_id.strip():
            raise ValidationError("fill_id must not be empty")
        if quantity <= 0:
            raise ValidationError("Fill quantity must be positive")

        self._fill_id = fill_id.strip()
        self._order_id = order_id
        self._symbol = symbol
        self._side = side
        self._quantity = quantity
        self._price = price
        self._executed_at = executed_at
        self._fee = fee

    @property
    def fill_id(self) -> str:
        return self._fill_id

    @property
    def order_id(self) -> str:
        return self._order_id

    @property
    def symbol(self) -> Symbol:
        return self._symbol

    @property
    def side(self) -> OrderSide:
        return self._side

    @property
    def quantity(self) -> Decimal:
        return self._quantity

    @property
    def price(self) -> Price:
        return self._price

    @property
    def executed_at(self) -> Timestamp:
        return self._executed_at

    @property
    def fee(self) -> Optional[Money]:
        return self._fee

    @property
    def notional(self) -> Decimal:
        """Quantity times price (fees excluded)."""
        return self._quantity * self._price.amount

    def _value(self) -> tuple[Any, ...]:
        return (
            self._fill_id,
            self._order_id,
            self._symbol,
            self._side,
            self._quantity,
            self._price,
            self._executed_at,
            self._fee,
        )


class ExecutionResult(ValueObject):
    """What the venue reported back for one submitted intent.

    Carries every fill produced, so the Portfolio can aggregate them
    (Phase 15, section 22) and detect partial execution (section 23).
    """

    def __init__(
        self,
        intent_id: str,
        order_id: str,
        status: ExecutionStatus,
        requested_quantity: Decimal,
        fills: Sequence[Fill] = (),
        rejection_reason: Optional[ExecutionRejectionReason] = None,
        message: str = "",
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        if not intent_id.strip():
            raise ValidationError("intent_id must not be empty")
        if requested_quantity <= 0:
            raise ValidationError("requested_quantity must be positive")
        if status is ExecutionStatus.REJECTED and rejection_reason is None:
            raise ValidationError("A rejected ExecutionResult must carry a rejection_reason")

        self._intent_id = intent_id.strip()
        self._order_id = order_id
        self._status = status
        self._requested_quantity = requested_quantity
        self._fills: List[Fill] = list(fills)
        self._rejection_reason = rejection_reason
        self._message = message
        self._metadata: Dict[str, Any] = dict(metadata or {})

    @classmethod
    def rejected(
        cls,
        intent_id: str,
        requested_quantity: Decimal,
        reason: ExecutionRejectionReason,
        message: str = "",
        order_id: str = "",
    ) -> "ExecutionResult":
        """Build a rejection result carrying an explicit cause."""
        return cls(
            intent_id=intent_id,
            order_id=order_id,
            status=ExecutionStatus.REJECTED,
            requested_quantity=requested_quantity,
            rejection_reason=reason,
            message=message or reason.value,
        )

    @property
    def intent_id(self) -> str:
        return self._intent_id

    @property
    def order_id(self) -> str:
        return self._order_id

    @property
    def status(self) -> ExecutionStatus:
        return self._status

    @property
    def requested_quantity(self) -> Decimal:
        return self._requested_quantity

    @property
    def fills(self) -> List[Fill]:
        return list(self._fills)

    @property
    def rejection_reason(self) -> Optional[ExecutionRejectionReason]:
        return self._rejection_reason

    @property
    def message(self) -> str:
        return self._message

    @property
    def metadata(self) -> Dict[str, Any]:
        return dict(self._metadata)

    @property
    def filled_quantity(self) -> Decimal:
        """Total quantity across every fill."""
        return sum((fill.quantity for fill in self._fills), Decimal("0"))

    @property
    def remaining_quantity(self) -> Decimal:
        """Requested minus filled (never negative)."""
        remaining = self._requested_quantity - self.filled_quantity
        return remaining if remaining > 0 else Decimal("0")

    @property
    def is_successful(self) -> bool:
        """True when at least part of the order was filled."""
        return self._status in (ExecutionStatus.FILLED, ExecutionStatus.PARTIALLY_FILLED)

    @property
    def average_fill_price(self) -> Optional[Price]:
        """Quantity-weighted average price of the fills (section 24)."""
        filled = self.filled_quantity
        if filled <= 0:
            return None
        total = sum((fill.notional for fill in self._fills), Decimal("0"))
        return Price(total / filled)

    @property
    def total_fees(self) -> Optional[Money]:
        """Sum of every fill fee, or None when no fees were charged."""
        fees = [fill.fee for fill in self._fills if fill.fee is not None]
        if not fees:
            return None
        total = fees[0]
        for fee in fees[1:]:
            total = total.add(fee)
        return total

    def _value(self) -> tuple[Any, ...]:
        return (
            self._intent_id,
            self._order_id,
            self._status,
            self._requested_quantity,
            tuple(self._fills),
            self._rejection_reason,
        )
