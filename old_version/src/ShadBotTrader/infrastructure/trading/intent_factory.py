"""Builds trading intents from approved decisions (Phase 14, sections 19-24).

The factory only expresses POLICY (how to size, how to price). Resolving
a policy into a concrete broker order belongs to the Execution Platform.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from typing import Optional

from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.market.timestamp import Timestamp
from ShadBotTrader.domain.strategy.decision import TradingDecision
from ShadBotTrader.domain.strategy.ports import IntentFactory
from ShadBotTrader.domain.strategy.strategy_context import StrategyContext
from ShadBotTrader.domain.strategy.strategy_types import (
    DecisionType,
    IntentType,
    QuantityPolicyType,
    SignalType,
)
from ShadBotTrader.domain.strategy.trading_intent import (
    PricePolicy,
    QuantityPolicy,
    TradingIntent,
)
from ShadBotTrader.domain.trading.order import OrderSide

_DECISION_TO_INTENT = {
    DecisionType.ENTER: IntentType.ENTER_POSITION,
    DecisionType.EXIT: IntentType.EXIT_POSITION,
    DecisionType.REDUCE: IntentType.REDUCE_POSITION,
    DecisionType.INCREASE: IntentType.INCREASE_POSITION,
    DecisionType.CANCEL: IntentType.CANCEL_INTENT,
}


class DefaultIntentFactory(IntentFactory):
    """Creates market-priced intents with a configurable sizing policy.

    ``confidence_weighted`` scales the base quantity by the decision's
    confidence, so a marginal signal commits less capital than a strong
    one — while never exceeding ``base_quantity``.
    """

    def __init__(
        self,
        base_quantity: Decimal = Decimal("1"),
        quantity_policy_type: QuantityPolicyType = QuantityPolicyType.FIXED,
        expiration_seconds: Optional[float] = 60.0,
    ) -> None:
        if base_quantity <= 0:
            raise ValidationError("base_quantity must be positive")
        if expiration_seconds is not None and expiration_seconds <= 0:
            raise ValidationError("expiration_seconds must be positive")
        self._base_quantity = base_quantity
        self._quantity_policy_type = quantity_policy_type
        self._expiration_seconds = expiration_seconds

    def build(
        self,
        decision: TradingDecision,
        context: StrategyContext,
    ) -> Optional[TradingIntent]:
        if not decision.is_actionable:
            return None

        intent_type = _DECISION_TO_INTENT.get(decision.decision_type)
        if intent_type is None:
            return None

        side = self._side(decision, context)
        if side is None:
            return None

        return TradingIntent(
            intent_id=f"intent:{decision.decision_id}",
            decision_id=decision.decision_id,
            strategy_id=decision.strategy_id,
            strategy_version=decision.strategy_version,
            symbol=decision.symbol,
            intent_type=intent_type,
            side=side,
            quantity_policy=self._quantity_policy(decision),
            price_policy=PricePolicy.market(),
            timestamp=decision.timestamp,
            expires_at=self._expiry(decision.timestamp),
            reason=decision.reason,
            risk_constraints={"source_decision": decision.decision_id},
            context=decision.context,
        )

    # -- helpers ----------------------------------------------------------
    def _side(self, decision: TradingDecision, context: StrategyContext) -> Optional[OrderSide]:
        """Resolve the order side for the decision.

        For an EXIT the side is the opposite of the open position; for an
        ENTER it comes from the originating signal recorded in context.
        """
        portfolio = context.portfolio

        if decision.decision_type in (DecisionType.EXIT, DecisionType.REDUCE):
            if portfolio is None or portfolio.is_flat:
                return None
            return OrderSide.SELL if portfolio.is_long else OrderSide.BUY

        signal_type = decision.context.get("signal_type")
        if signal_type == SignalType.BUY.value:
            return OrderSide.BUY
        if signal_type == SignalType.SELL.value:
            return OrderSide.SELL

        # Fall back to the direction implied by the prediction value.
        predicted = decision.context.get("prediction_value")
        if isinstance(predicted, (int, float)):
            return OrderSide.BUY if float(predicted) >= 0.5 else OrderSide.SELL
        return None

    def _quantity_policy(self, decision: TradingDecision) -> QuantityPolicy:
        if self._quantity_policy_type is QuantityPolicyType.CONFIDENCE_WEIGHTED:
            scaled = self._base_quantity * Decimal(str(max(decision.confidence, 0.01)))
            return QuantityPolicy(
                QuantityPolicyType.CONFIDENCE_WEIGHTED,
                value=scaled,
                max_quantity=self._base_quantity,
            )
        return QuantityPolicy(self._quantity_policy_type, value=self._base_quantity)

    def _expiry(self, timestamp: Timestamp) -> Optional[Timestamp]:
        if self._expiration_seconds is None:
            return None
        return Timestamp(timestamp.value + timedelta(seconds=self._expiration_seconds))
