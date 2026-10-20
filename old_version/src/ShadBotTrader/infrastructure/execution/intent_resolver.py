"""Resolves intent policies into executable orders (Phase 14, §23-24).

This is where a `QuantityPolicy` such as "2% of equity" or a
`PricePolicy` such as "market" becomes a concrete number, using live
account and market state. Trading never does this — it has no access to
equity or quotes.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Optional

from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.execution.market_view import ExecutionContext
from ShadBotTrader.domain.execution.ports import IntentResolver
from ShadBotTrader.domain.execution.resolved_order import ResolvedOrder
from ShadBotTrader.domain.strategy.strategy_types import (
    IntentType,
    PricePolicyType,
    QuantityPolicyType,
)
from ShadBotTrader.domain.strategy.trading_intent import TradingIntent
from ShadBotTrader.domain.trading.order import OrderType

_PRICE_POLICY_TO_ORDER_TYPE = {
    PricePolicyType.MARKET: OrderType.MARKET,
    PricePolicyType.LIMIT: OrderType.LIMIT,
    PricePolicyType.STOP: OrderType.STOP,
    PricePolicyType.STOP_LIMIT: OrderType.STOP,
    PricePolicyType.REFERENCE_PRICE: OrderType.LIMIT,
}

# Intents that close or shrink an existing position.
_CLOSING = (IntentType.EXIT_POSITION, IntentType.REDUCE_POSITION)


class DefaultIntentResolver(IntentResolver):
    """Resolves quantity and price policies against live state.

    Quantity resolution:

    * ``FIXED``               -> the policy value as-is
    * ``PERCENT_EQUITY``      -> equity * pct / price
    * ``RISK_AMOUNT``         -> risk budget / price
    * ``CONFIDENCE_WEIGHTED`` -> the pre-scaled value from Trading
    * ``VOLATILITY``          -> the policy value (a volatility model is
      out of scope for this sprint; documented rather than faked)

    Closing intents ignore the sizing policy and use the actual open
    quantity: you can never close more than you hold.
    """

    def __init__(
        self,
        min_quantity: Decimal = Decimal("0.01"),
        reduce_fraction: Decimal = Decimal("0.5"),
    ) -> None:
        if min_quantity <= 0:
            raise ValidationError("min_quantity must be positive")
        if not 0 < reduce_fraction <= 1:
            raise ValidationError("reduce_fraction must be in (0, 1]")
        self._min_quantity = min_quantity
        self._reduce_fraction = reduce_fraction

    def resolve(
        self,
        intent: TradingIntent,
        context: ExecutionContext,
    ) -> Optional[ResolvedOrder]:
        quantity = self._quantity(intent, context)
        if quantity is None or quantity < self._min_quantity:
            return None

        cap = intent.quantity_policy.max_quantity
        if cap is not None and quantity > cap:
            quantity = cap

        # NOTE: available liquidity is deliberately NOT applied here.
        # The resolver states the size the strategy *wants*; how much of
        # it the market can absorb is the venue's business. Capping here
        # too would silently turn every liquidity shortfall into a full
        # fill and make partial execution unobservable.

        price_policy = intent.price_policy
        order_type = _PRICE_POLICY_TO_ORDER_TYPE.get(price_policy.policy_type, OrderType.MARKET)
        reference = price_policy.reference_price

        return ResolvedOrder(
            order_id=f"order:{intent.intent_id}",
            intent_id=intent.intent_id,
            symbol=intent.symbol,
            side=intent.side,
            order_type=order_type,
            quantity=quantity,
            timestamp=context.timestamp,
            limit_price=reference if order_type is OrderType.LIMIT else None,
            stop_price=reference if order_type is OrderType.STOP else None,
            reference_price=context.quote.mid,
            metadata={
                "strategy_id": str(intent.strategy_id),
                "intent_type": intent.intent_type.value,
                "quantity_policy": intent.quantity_policy.policy_type.value,
                "price_policy": price_policy.policy_type.value,
            },
        )

    # -- helpers ----------------------------------------------------------
    def _quantity(
        self,
        intent: TradingIntent,
        context: ExecutionContext,
    ) -> Optional[Decimal]:
        position = context.position

        # Closing intents are bounded by what is actually held.
        if intent.intent_type in _CLOSING:
            if position.is_flat:
                return None
            held = position.quantity
            if intent.intent_type is IntentType.REDUCE_POSITION:
                return held * self._reduce_fraction
            return held

        policy = intent.quantity_policy
        price = context.quote.mid.amount
        if price <= 0:
            return None

        if policy.policy_type is QuantityPolicyType.PERCENT_EQUITY:
            if context.equity <= 0:
                return None
            return (context.equity * policy.value / Decimal("100")) / price

        if policy.policy_type is QuantityPolicyType.RISK_AMOUNT:
            if policy.value <= 0:
                return None
            return policy.value / price

        # FIXED, CONFIDENCE_WEIGHTED and VOLATILITY all carry an absolute
        # size already computed by the Trading Platform.
        return policy.value
