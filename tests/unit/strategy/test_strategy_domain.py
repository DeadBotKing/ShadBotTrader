"""Tests for the trading domain value objects (Phase 14)."""

from datetime import timedelta
from decimal import Decimal

import pytest

from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.market.price import Price
from ShadBotTrader.domain.market.timestamp import Timestamp
from ShadBotTrader.domain.strategy.decision import TradingDecision
from ShadBotTrader.domain.strategy.risk_policy import RiskPolicy, RiskVerdict
from ShadBotTrader.domain.strategy.strategy_identity import StrategyId, StrategyVersion
from ShadBotTrader.domain.strategy.strategy_types import (
    DecisionType,
    IntentType,
    PricePolicyType,
    QuantityPolicyType,
    RejectionReason,
    SignalType,
)
from ShadBotTrader.domain.strategy.trading_intent import (
    PricePolicy,
    QuantityPolicy,
    TradingIntent,
)
from ShadBotTrader.domain.trading.order import OrderSide

from .conftest import BASE_TIME, make_signal


# --- identity ---------------------------------------------------------------
def test_strategy_id_normalises_and_rejects_empty():
    assert StrategyId("  AI_Directional  ").value == "ai_directional"
    with pytest.raises(ValidationError):
        StrategyId("   ")
    with pytest.raises(ValidationError):
        StrategyId("has space")


def test_strategy_version_is_positive_and_immutable():
    version = StrategyVersion(1)
    assert version.number == 1
    assert version.next().number == 2
    assert version.number == 1  # unchanged
    with pytest.raises(ValidationError):
        StrategyVersion(0)


# --- signal -----------------------------------------------------------------
def test_signal_requires_valid_confidence(symbol, timeframe):
    with pytest.raises(ValidationError):
        make_signal(symbol, timeframe, confidence=1.5)
    with pytest.raises(ValidationError):
        make_signal(symbol, timeframe, confidence=-0.1)


def test_hold_signal_is_not_actionable(symbol, timeframe):
    assert make_signal(symbol, timeframe, SignalType.BUY).is_actionable
    assert not make_signal(symbol, timeframe, SignalType.HOLD).is_actionable


def test_signal_context_is_copied(symbol, timeframe):
    signal = make_signal(symbol, timeframe)
    context = signal.context
    context["injected"] = True
    assert "injected" not in signal.context


# --- decision ---------------------------------------------------------------
def test_decision_is_not_an_order(symbol, timeframe):
    """The core Phase 14 invariant (section 18)."""
    from ShadBotTrader.domain.trading.order import Order

    decision = TradingDecision(
        decision_id="d1",
        strategy_id=StrategyId("ai_directional"),
        strategy_version=StrategyVersion(1),
        symbol=symbol,
        timestamp=Timestamp(BASE_TIME),
        decision_type=DecisionType.ENTER,
    )
    assert not isinstance(decision, Order)
    assert not hasattr(decision, "quantity")
    assert not hasattr(decision, "submit")


def test_hold_decision_carries_reason(symbol, timeframe):
    signal = make_signal(symbol, timeframe, SignalType.HOLD)
    decision = TradingDecision.hold(
        "d1", signal, reason="nothing to do", rejection_reason=RejectionReason.NO_SIGNAL
    )
    assert decision.decision_type is DecisionType.HOLD
    assert not decision.is_actionable
    assert decision.rejection_reason is RejectionReason.NO_SIGNAL
    assert decision.source_signal_id == signal.signal_id


def test_decision_rejects_empty_id(symbol):
    with pytest.raises(ValidationError):
        TradingDecision(
            decision_id="  ",
            strategy_id=StrategyId("s"),
            strategy_version=StrategyVersion(1),
            symbol=symbol,
            timestamp=Timestamp(BASE_TIME),
            decision_type=DecisionType.ENTER,
        )


# --- policies ---------------------------------------------------------------
def test_quantity_policy_rejects_non_positive():
    assert QuantityPolicy.fixed(Decimal("1")).value == Decimal("1")
    with pytest.raises(ValidationError):
        QuantityPolicy.fixed(Decimal("0"))


def test_price_policy_requires_reference_where_needed():
    assert PricePolicy.market().policy_type is PricePolicyType.MARKET
    with pytest.raises(ValidationError):
        PricePolicy(PricePolicyType.LIMIT)
    policy = PricePolicy(PricePolicyType.LIMIT, reference_price=Price(Decimal("2000")))
    assert policy.reference_price is not None


# --- intent -----------------------------------------------------------------
def _intent(symbol, **overrides):
    defaults = dict(
        intent_id="i1",
        decision_id="d1",
        strategy_id=StrategyId("ai_directional"),
        strategy_version=StrategyVersion(1),
        symbol=symbol,
        intent_type=IntentType.ENTER_POSITION,
        side=OrderSide.BUY,
        quantity_policy=QuantityPolicy.fixed(Decimal("1")),
        price_policy=PricePolicy.market(),
        timestamp=Timestamp(BASE_TIME),
    )
    defaults.update(overrides)
    return TradingIntent(**defaults)


def test_intent_must_reference_a_decision(symbol):
    with pytest.raises(ValidationError):
        _intent(symbol, decision_id="")


def test_intent_expiration_must_follow_timestamp(symbol):
    with pytest.raises(ValidationError):
        _intent(symbol, expires_at=Timestamp(BASE_TIME - timedelta(seconds=1)))


def test_intent_expiry_check(symbol):
    intent = _intent(symbol, expires_at=Timestamp(BASE_TIME + timedelta(seconds=60)))
    assert not intent.is_expired(Timestamp(BASE_TIME))
    assert intent.is_expired(Timestamp(BASE_TIME + timedelta(seconds=60)))
    assert not _intent(symbol).is_expired(Timestamp(BASE_TIME + timedelta(days=1)))


def test_intent_carries_no_broker_details(symbol):
    """An intent expresses policy, never a concrete broker order."""
    intent = _intent(symbol)
    assert not hasattr(intent, "order_id")
    assert not hasattr(intent, "broker")
    assert intent.quantity_policy.policy_type is QuantityPolicyType.FIXED


# --- risk policy / verdict ---------------------------------------------------
def test_risk_policy_validates_bounds():
    RiskPolicy()
    with pytest.raises(ValidationError):
        RiskPolicy(max_drawdown_percent=Decimal("101"))
    with pytest.raises(ValidationError):
        RiskPolicy(max_exposure_ratio=Decimal("2"))
    with pytest.raises(ValidationError):
        RiskPolicy(min_confidence=1.5)
    with pytest.raises(ValidationError):
        RiskPolicy(max_open_positions=-1)


def test_rejected_verdict_requires_a_reason():
    with pytest.raises(ValidationError):
        RiskVerdict(approved=False)


def test_verdict_is_truthy_when_approved():
    assert RiskVerdict.approve()
    assert not RiskVerdict.reject(RejectionReason.RISK_EXPOSURE)
    assert RiskVerdict.reject(RejectionReason.RISK_EXPOSURE).rejection_reason is (
        RejectionReason.RISK_EXPOSURE
    )
