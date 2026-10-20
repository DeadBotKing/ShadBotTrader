"""Fill-based position accounting (Phase 15, sections 13, 24-27, 30).

``PositionState`` is an immutable snapshot of the exposure on one symbol.
Applying a fill returns a NEW state plus the realized PnL that the fill
crystallised, so the whole history is reconstructible and auditable.

Accounting rules implemented here:

* average entry price comes from real fills only (section 24)
* realized PnL is booked when a position is reduced or closed (§25)
* unrealized PnL is marked against the current market price (§26)
* fees are tracked separately from gross PnL (§27-28)
* a reversal is decomposed into close + open, and only the closing part
  realises PnL (Phase 14, section 57)
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Optional, Tuple

from ShadBotTrader.domain.common.value_object import ValueObject
from ShadBotTrader.domain.execution.execution_types import PositionSide
from ShadBotTrader.domain.execution.fill import Fill
from ShadBotTrader.domain.execution.money import Money
from ShadBotTrader.domain.market.price import Price
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.trading.order import OrderSide


class PositionState(ValueObject):
    """Immutable snapshot of the position held on one symbol.

    ``signed_quantity`` is positive for long, negative for short and zero
    when flat, which keeps the arithmetic uniform in both directions.
    """

    def __init__(
        self,
        symbol: Symbol,
        signed_quantity: Decimal = Decimal("0"),
        average_entry_price: Optional[Price] = None,
        realized_pnl: Optional[Money] = None,
        total_fees: Optional[Money] = None,
        currency: str = "USD",
    ) -> None:
        self._symbol = symbol
        self._signed_quantity = signed_quantity
        self._average_entry_price = average_entry_price
        self._currency = currency.strip().upper()
        self._realized_pnl = realized_pnl or Money.zero(self._currency)
        self._total_fees = total_fees or Money.zero(self._currency)

    # -- factories --------------------------------------------------------
    @classmethod
    def flat(cls, symbol: Symbol, currency: str = "USD") -> "PositionState":
        """A position holding nothing."""
        return cls(symbol=symbol, currency=currency)

    # -- state ------------------------------------------------------------
    @property
    def symbol(self) -> Symbol:
        return self._symbol

    @property
    def signed_quantity(self) -> Decimal:
        return self._signed_quantity

    @property
    def quantity(self) -> Decimal:
        """Absolute size of the position."""
        return abs(self._signed_quantity)

    @property
    def side(self) -> PositionSide:
        if self._signed_quantity > 0:
            return PositionSide.LONG
        if self._signed_quantity < 0:
            return PositionSide.SHORT
        return PositionSide.FLAT

    @property
    def is_flat(self) -> bool:
        return self._signed_quantity == 0

    @property
    def is_long(self) -> bool:
        return self._signed_quantity > 0

    @property
    def is_short(self) -> bool:
        return self._signed_quantity < 0

    @property
    def average_entry_price(self) -> Optional[Price]:
        return self._average_entry_price

    @property
    def realized_pnl(self) -> Money:
        """Gross realized PnL (fees excluded, Phase 15 section 27)."""
        return self._realized_pnl

    @property
    def total_fees(self) -> Money:
        return self._total_fees

    @property
    def net_realized_pnl(self) -> Money:
        """Realized PnL after fees."""
        return self._realized_pnl.subtract(self._total_fees)

    @property
    def currency(self) -> str:
        return self._currency

    @property
    def cost_basis(self) -> Optional[Money]:
        """Capital committed to the open position (section 30)."""
        if self.is_flat or self._average_entry_price is None:
            return None
        return Money(self.quantity * self._average_entry_price.amount, self._currency)

    # -- valuation --------------------------------------------------------
    def unrealized_pnl(self, current_price: Price) -> Money:
        """Mark-to-market PnL of the open position (section 26)."""
        if self.is_flat or self._average_entry_price is None:
            return Money.zero(self._currency)
        difference = current_price.amount - self._average_entry_price.amount
        return Money(self._signed_quantity * difference, self._currency)

    def total_pnl(self, current_price: Price) -> Money:
        """Realized + unrealized, net of fees."""
        return self.net_realized_pnl.add(self.unrealized_pnl(current_price))

    # -- mutation (returns a new state) -----------------------------------
    def apply_fill(self, fill: Fill) -> Tuple["PositionState", Money]:
        """Apply ``fill`` and return ``(new_state, realized_pnl_of_this_fill)``.

        The state is never mutated in place: accounting history must be
        reconstructible from the sequence of fills alone.
        """
        delta = fill.quantity if fill.side is OrderSide.BUY else -fill.quantity
        fee = fill.fee or Money.zero(self._currency)
        new_fees = self._total_fees.add(fee)

        current = self._signed_quantity
        new_signed = current + delta

        # --- opening from flat -------------------------------------------
        if current == 0:
            return (
                PositionState(
                    symbol=self._symbol,
                    signed_quantity=new_signed,
                    average_entry_price=fill.price,
                    realized_pnl=self._realized_pnl,
                    total_fees=new_fees,
                    currency=self._currency,
                ),
                Money.zero(self._currency),
            )

        entry = self._average_entry_price
        same_direction = (current > 0 and delta > 0) or (current < 0 and delta < 0)

        # --- increasing an existing position: re-average, nothing realised -
        if same_direction:
            assert entry is not None  # a non-flat position always has an entry
            total_cost = abs(current) * entry.amount + fill.quantity * fill.price.amount
            reaveraged = Price(total_cost / abs(new_signed))
            return (
                PositionState(
                    symbol=self._symbol,
                    signed_quantity=new_signed,
                    average_entry_price=reaveraged,
                    realized_pnl=self._realized_pnl,
                    total_fees=new_fees,
                    currency=self._currency,
                ),
                Money.zero(self._currency),
            )

        # --- reducing / closing / reversing: realise PnL on the closed part
        assert entry is not None
        closed_quantity = min(abs(delta), abs(current))
        direction = Decimal("1") if current > 0 else Decimal("-1")
        realized_amount = closed_quantity * (fill.price.amount - entry.amount) * direction
        realized = Money(realized_amount, self._currency)

        new_average: Optional[Price]
        if new_signed == 0:
            # fully closed
            new_average = None
        elif (current > 0) == (new_signed > 0):
            # partially reduced, direction unchanged -> entry price stays
            new_average = entry
        else:
            # reversed: the remainder is a fresh position at the fill price
            new_average = fill.price

        return (
            PositionState(
                symbol=self._symbol,
                signed_quantity=new_signed,
                average_entry_price=new_average,
                realized_pnl=self._realized_pnl.add(realized),
                total_fees=new_fees,
                currency=self._currency,
            ),
            realized,
        )

    def _value(self) -> tuple[Any, ...]:
        return (
            self._symbol,
            self._signed_quantity,
            self._average_entry_price,
            self._realized_pnl,
            self._total_fees,
        )

    def __str__(self) -> str:
        if self.is_flat:
            return f"{self._symbol} FLAT"
        entry = self._average_entry_price
        return f"{self._symbol} {self.side.value.upper()} {self.quantity} @ {entry}"
