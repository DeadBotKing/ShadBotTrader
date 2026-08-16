"""Deterministic simulated execution venue (Phase 16 §7, Phase 15 §21-23).

Models the parts of real execution that change accounting outcomes:

* **spread** — buys lift the ask, sells hit the bid
* **slippage** — a configurable adverse move on top of the touch price
* **commission** — a fee per fill, tracked separately from PnL
* **partial fills** — capped by available liquidity, native by design

The venue is fully deterministic: identical inputs always produce
identical fills, which is what makes backtests and replays reproducible
(Phase 15, section 21 and the architecture's determinism rule).
"""

from __future__ import annotations

from decimal import Decimal
from typing import List

from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.execution.execution_types import (
    ExecutionRejectionReason,
    ExecutionStatus,
)
from ShadBotTrader.domain.execution.fill import ExecutionResult, Fill
from ShadBotTrader.domain.execution.market_view import ExecutionContext
from ShadBotTrader.domain.execution.money import Money
from ShadBotTrader.domain.execution.ports import ExecutionVenue
from ShadBotTrader.domain.execution.resolved_order import ResolvedOrder
from ShadBotTrader.domain.market.price import Price
from ShadBotTrader.domain.trading.order import OrderSide, OrderType


class SimulatedExecutionVenue(ExecutionVenue):
    """Fills orders against a quote with spread, slippage and fees."""

    def __init__(
        self,
        slippage_rate: Decimal = Decimal("0"),
        commission_rate: Decimal = Decimal("0"),
        currency: str = "USD",
        max_fill_ratio: Decimal = Decimal("1"),
        reject_unfillable_limits: bool = True,
    ) -> None:
        if slippage_rate < 0:
            raise ValidationError("slippage_rate must not be negative")
        if commission_rate < 0:
            raise ValidationError("commission_rate must not be negative")
        if not 0 < max_fill_ratio <= 1:
            raise ValidationError("max_fill_ratio must be in (0, 1]")

        self._slippage_rate = slippage_rate
        self._commission_rate = commission_rate
        self._currency = currency.strip().upper()
        self._max_fill_ratio = max_fill_ratio
        self._reject_unfillable_limits = reject_unfillable_limits

    @property
    def name(self) -> str:
        return "simulated"

    def submit(self, order: ResolvedOrder, context: ExecutionContext) -> ExecutionResult:
        quote = context.quote

        # --- how much can actually trade -------------------------------
        fillable = order.quantity * self._max_fill_ratio
        liquidity = context.available_liquidity
        if liquidity is not None:
            fillable = min(fillable, liquidity)

        if fillable <= 0:
            return ExecutionResult.rejected(
                intent_id=order.intent_id,
                requested_quantity=order.quantity,
                reason=ExecutionRejectionReason.INSUFFICIENT_LIQUIDITY,
                message="no liquidity available at this venue",
                order_id=order.order_id,
            )

        # --- price the fill --------------------------------------------
        touch = quote.ask if order.side is OrderSide.BUY else quote.bid
        execution_price = self._apply_slippage(touch, order.side)

        if order.order_type is OrderType.LIMIT and order.limit_price is not None:
            crossed = (
                execution_price.amount <= order.limit_price.amount
                if order.side is OrderSide.BUY
                else execution_price.amount >= order.limit_price.amount
            )
            if not crossed:
                if self._reject_unfillable_limits:
                    return ExecutionResult.rejected(
                        intent_id=order.intent_id,
                        requested_quantity=order.quantity,
                        reason=ExecutionRejectionReason.NO_MARKET_PRICE,
                        message=(
                            f"limit {order.limit_price} not reachable "
                            f"(market {execution_price})"
                        ),
                        order_id=order.order_id,
                    )
                execution_price = order.limit_price

        # --- build the fill --------------------------------------------
        fee_amount = fillable * execution_price.amount * self._commission_rate
        fill = Fill(
            fill_id=f"fill:{order.order_id}",
            order_id=order.order_id,
            symbol=order.symbol,
            side=order.side,
            quantity=fillable,
            price=execution_price,
            executed_at=context.timestamp,
            fee=Money(fee_amount, self._currency) if fee_amount > 0 else None,
        )

        fills: List[Fill] = [fill]
        status = (
            ExecutionStatus.FILLED
            if fillable >= order.quantity
            else ExecutionStatus.PARTIALLY_FILLED
        )

        return ExecutionResult(
            intent_id=order.intent_id,
            order_id=order.order_id,
            status=status,
            requested_quantity=order.quantity,
            fills=fills,
            metadata={
                "venue": self.name,
                "bid": str(quote.bid),
                "ask": str(quote.ask),
                "slippage_rate": str(self._slippage_rate),
            },
        )

    # -- helpers ----------------------------------------------------------
    def _apply_slippage(self, touch: Price, side: OrderSide) -> Price:
        """Move the price against the trader by ``slippage_rate``."""
        if self._slippage_rate == 0:
            return touch
        drift = touch.amount * self._slippage_rate
        if side is OrderSide.BUY:
            return Price(touch.amount + drift)
        return Price(touch.amount - drift)
