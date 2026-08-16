"""Shared builders for the execution / portfolio tests."""

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from ShadBotTrader.domain.execution.fill import Fill
from ShadBotTrader.domain.execution.market_view import ExecutionContext, MarketQuote
from ShadBotTrader.domain.execution.money import Money
from ShadBotTrader.domain.execution.position_state import PositionState
from ShadBotTrader.domain.market.price import Price
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timestamp import Timestamp
from ShadBotTrader.domain.trading.order import OrderSide

BASE_TIME = datetime(2026, 8, 16, 12, 0, tzinfo=timezone.utc)
XAU = Symbol("XAUUSD_i")


@pytest.fixture
def symbol() -> Symbol:
    return XAU


@pytest.fixture
def now() -> Timestamp:
    return Timestamp(BASE_TIME)


def d(value: str) -> Decimal:
    """Shorthand for an exact Decimal."""
    return Decimal(value)


def make_fill(
    side: OrderSide,
    quantity: str,
    price: str,
    fee: str | None = None,
    fill_id: str = "f1",
    symbol: Symbol = XAU,
) -> Fill:
    return Fill(
        fill_id=fill_id,
        order_id="o1",
        symbol=symbol,
        side=side,
        quantity=Decimal(quantity),
        price=Price(Decimal(price)),
        executed_at=Timestamp(BASE_TIME),
        fee=Money(Decimal(fee), "USD") if fee is not None else None,
    )


def buy(quantity: str, price: str, fee: str | None = None, fill_id: str = "f1") -> Fill:
    return make_fill(OrderSide.BUY, quantity, price, fee, fill_id)


def sell(quantity: str, price: str, fee: str | None = None, fill_id: str = "f2") -> Fill:
    return make_fill(OrderSide.SELL, quantity, price, fee, fill_id)


def quote(bid: str = "1999", ask: str = "2001") -> MarketQuote:
    return MarketQuote(
        symbol=XAU,
        bid=Price(Decimal(bid)),
        ask=Price(Decimal(ask)),
        timestamp=Timestamp(BASE_TIME),
    )


def make_context(
    position: PositionState | None = None,
    equity: str = "100000",
    liquidity: str | None = None,
    bid: str = "1999",
    ask: str = "2001",
) -> ExecutionContext:
    return ExecutionContext(
        timestamp=Timestamp(BASE_TIME),
        quote=quote(bid, ask),
        position=position or PositionState.flat(XAU),
        equity=Decimal(equity),
        available_liquidity=Decimal(liquidity) if liquidity is not None else None,
    )
