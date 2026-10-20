"""Trading intent — the contract with the Execution Platform.

Phase 14, sections 19-24. An intent expresses WHAT should happen and
under WHICH policies, never a concrete broker order. The Execution
Platform resolves the policies into an actual order.

An intent may only be produced from a decision that passed the risk
gate; see ``domain.strategy.ports.RiskGate``.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, Mapping, Optional

from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.common.value_object import ValueObject
from ShadBotTrader.domain.market.price import Price
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timestamp import Timestamp
from ShadBotTrader.domain.strategy.strategy_identity import StrategyId, StrategyVersion
from ShadBotTrader.domain.strategy.strategy_types import (
    IntentType,
    PricePolicyType,
    QuantityPolicyType,
)
from ShadBotTrader.domain.trading.order import OrderSide


class QuantityPolicy(ValueObject):
    """How the executor should size the position (section 23)."""

    def __init__(
        self,
        policy_type: QuantityPolicyType,
        value: Decimal,
        max_quantity: Optional[Decimal] = None,
    ) -> None:
        if value <= 0:
            raise ValidationError("QuantityPolicy value must be positive")
        if max_quantity is not None and max_quantity <= 0:
            raise ValidationError("QuantityPolicy max_quantity must be positive")
        self._policy_type = policy_type
        self._quantity = value
        self._max_quantity = max_quantity

    @classmethod
    def fixed(cls, quantity: Decimal) -> "QuantityPolicy":
        """A fixed-size policy."""
        return cls(QuantityPolicyType.FIXED, quantity)

    @property
    def policy_type(self) -> QuantityPolicyType:
        return self._policy_type

    @property
    def value(self) -> Decimal:
        return self._quantity

    @property
    def max_quantity(self) -> Optional[Decimal]:
        return self._max_quantity

    def _value(self) -> tuple[Any, ...]:
        return (self._policy_type, self._quantity, self._max_quantity)


class PricePolicy(ValueObject):
    """How the executor should price the order (section 24)."""

    def __init__(
        self,
        policy_type: PricePolicyType,
        reference_price: Optional[Price] = None,
        offset: Decimal = Decimal("0"),
    ) -> None:
        needs_reference = policy_type in (
            PricePolicyType.LIMIT,
            PricePolicyType.STOP,
            PricePolicyType.STOP_LIMIT,
            PricePolicyType.REFERENCE_PRICE,
        )
        if needs_reference and reference_price is None:
            raise ValidationError(f"PricePolicy {policy_type.value} requires a reference price")
        self._policy_type = policy_type
        self._reference_price = reference_price
        self._offset = offset

    @classmethod
    def market(cls) -> "PricePolicy":
        """A market-price policy."""
        return cls(PricePolicyType.MARKET)

    @property
    def policy_type(self) -> PricePolicyType:
        return self._policy_type

    @property
    def reference_price(self) -> Optional[Price]:
        return self._reference_price

    @property
    def offset(self) -> Decimal:
        return self._offset

    def _value(self) -> tuple[Any, ...]:
        return (self._policy_type, self._reference_price, self._offset)


class TradingIntent(ValueObject):
    """A risk-approved instruction for the Execution Platform."""

    def __init__(
        self,
        intent_id: str,
        decision_id: str,
        strategy_id: StrategyId,
        strategy_version: StrategyVersion,
        symbol: Symbol,
        intent_type: IntentType,
        side: OrderSide,
        quantity_policy: QuantityPolicy,
        price_policy: PricePolicy,
        timestamp: Timestamp,
        expires_at: Optional[Timestamp] = None,
        reason: str = "",
        risk_constraints: Mapping[str, Any] | None = None,
        context: Mapping[str, Any] | None = None,
    ) -> None:
        if not intent_id.strip():
            raise ValidationError("intent_id must not be empty")
        if not decision_id.strip():
            raise ValidationError("intent must reference a decision_id")
        if expires_at is not None and expires_at.value <= timestamp.value:
            raise ValidationError("Intent expiration must be after its timestamp")

        self._intent_id = intent_id.strip()
        self._decision_id = decision_id.strip()
        self._strategy_id = strategy_id
        self._strategy_version = strategy_version
        self._symbol = symbol
        self._intent_type = intent_type
        self._side = side
        self._quantity_policy = quantity_policy
        self._price_policy = price_policy
        self._timestamp = timestamp
        self._expires_at = expires_at
        self._reason = reason
        self._risk_constraints: Dict[str, Any] = dict(risk_constraints or {})
        self._context: Dict[str, Any] = dict(context or {})

    @property
    def intent_id(self) -> str:
        return self._intent_id

    @property
    def decision_id(self) -> str:
        return self._decision_id

    @property
    def strategy_id(self) -> StrategyId:
        return self._strategy_id

    @property
    def strategy_version(self) -> StrategyVersion:
        return self._strategy_version

    @property
    def symbol(self) -> Symbol:
        return self._symbol

    @property
    def intent_type(self) -> IntentType:
        return self._intent_type

    @property
    def side(self) -> OrderSide:
        return self._side

    @property
    def quantity_policy(self) -> QuantityPolicy:
        return self._quantity_policy

    @property
    def price_policy(self) -> PricePolicy:
        return self._price_policy

    @property
    def timestamp(self) -> Timestamp:
        return self._timestamp

    @property
    def expires_at(self) -> Optional[Timestamp]:
        return self._expires_at

    @property
    def reason(self) -> str:
        return self._reason

    @property
    def risk_constraints(self) -> Dict[str, Any]:
        return dict(self._risk_constraints)

    @property
    def context(self) -> Dict[str, Any]:
        return dict(self._context)

    def is_expired(self, now: Timestamp) -> bool:
        """True when ``now`` is at or past the expiration."""
        if self._expires_at is None:
            return False
        return now.value >= self._expires_at.value

    def _value(self) -> tuple[Any, ...]:
        return (
            self._intent_id,
            self._decision_id,
            self._strategy_id,
            self._strategy_version,
            self._symbol,
            self._intent_type,
            self._side,
            self._quantity_policy,
            self._price_policy,
            self._timestamp,
        )
