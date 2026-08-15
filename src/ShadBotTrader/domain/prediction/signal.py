"""Trading signal value object."""

from __future__ import annotations

from enum import Enum
from typing import Any

from ShadBotTrader.domain.common.value_object import ValueObject
from ShadBotTrader.domain.market.symbol import Symbol


class TradingAction(str, Enum):
    """The action a strategy suggests."""

    BUY = "buy"
    SELL = "sell"
    NO_TRADE = "no_trade"


class SignalStrength(str, Enum):
    """How strongly a strategy believes in its signal."""

    WEAK = "weak"
    MEDIUM = "medium"
    STRONG = "strong"


class Signal(ValueObject):
    """A strategy output: what to do with a symbol and how strongly."""

    def __init__(self, symbol: Symbol, action: TradingAction, strength: SignalStrength) -> None:
        self._symbol = symbol
        self._action = action
        self._strength = strength

    @property
    def symbol(self) -> Symbol:
        return self._symbol

    @property
    def action(self) -> TradingAction:
        return self._action

    @property
    def strength(self) -> SignalStrength:
        return self._strength

    def _value(self) -> tuple[Any, ...]:
        return (self._symbol, self._action, self._strength)
