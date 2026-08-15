"""Tests for the trading domain entities."""

from decimal import Decimal

import pytest

from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.trading.order import Order, OrderSide, OrderStatus, OrderType


def make_order() -> Order:
    return Order(
        symbol=Symbol("XAUUSD_i"),
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=Decimal("0.1"),
    )


def test_order_lifecycle():
    order = make_order()
    assert order.status is OrderStatus.CREATED
    order.submit()
    assert order.status is OrderStatus.SUBMITTED
    order.fill()
    assert order.status is OrderStatus.FILLED


def test_order_requires_positive_quantity():
    with pytest.raises(ValidationError):
        Order(
            symbol=Symbol("XAUUSD_i"),
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("0"),
        )


def test_order_cannot_fill_before_submit():
    order = make_order()
    with pytest.raises(ValidationError):
        order.fill()
