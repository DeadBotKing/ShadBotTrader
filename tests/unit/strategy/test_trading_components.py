"""Tests for the Trading Platform infrastructure components (Phase 14)."""

from datetime import timedelta
from decimal import Decimal

from ShadBotTrader.domain.market.symbol import Symbol as _Symbol
from ShadBotTrader.domain.market.timeframe import Timeframe as _Timeframe
from ShadBotTrader.domain.market.timestamp import Timestamp
from ShadBotTrader.domain.strategy.risk_policy import RiskPolicy
from ShadBotTrader.domain.strategy.strategy_types import (
    DecisionType,
    IntentType,
    QuantityPolicyType,
    RejectionReason,
    SignalStrength,
    SignalType,
    StrategyState,
)
from ShadBotTrader.domain.trading.order import OrderSide
from ShadBotTrader.infrastructure.trading import (
    AiDirectionalStrategy,
    ConfidenceWeightedAggregator,
    DefaultIntentFactory,
    DefaultSignalValidator,
    InMemoryDecisionJournal,
    PolicyRiskGate,
    PositionAwareDecisionEngine,
)

from .conftest import (
    BASE_TIME,
    breached_risk,
    flat_portfolio,
    long_portfolio,
    make_context,
    make_prediction,
    make_signal,
    short_portfolio,
)

XAU_SYMBOL = _Symbol("XAUUSD_i")
TF = _Timeframe("5M")


# =============================================================== strategy ===
class TestAiDirectionalStrategy:
    def test_buy_on_confident_up_prediction(self, symbol, timeframe):
        strategy = AiDirectionalStrategy(min_confidence=0.55)
        context = make_context(symbol, timeframe, [make_prediction(value=0.9, confidence=0.9)])
        signal = strategy.evaluate(context)
        assert signal is not None
        assert signal.signal_type is SignalType.BUY
        assert signal.confidence == 0.9

    def test_sell_on_confident_down_prediction(self, symbol, timeframe):
        strategy = AiDirectionalStrategy(min_confidence=0.55)
        context = make_context(symbol, timeframe, [make_prediction(value=0.1, confidence=0.9)])
        signal = strategy.evaluate(context)
        assert signal is not None
        assert signal.signal_type is SignalType.SELL

    def test_hold_when_no_prediction(self, symbol, timeframe):
        strategy = AiDirectionalStrategy()
        signal = strategy.evaluate(make_context(symbol, timeframe, []))
        assert signal is not None
        assert signal.signal_type is SignalType.HOLD
        assert "no prediction" in signal.reason

    def test_hold_on_stale_prediction(self, symbol, timeframe):
        strategy = AiDirectionalStrategy(max_prediction_age_seconds=60)
        context = make_context(symbol, timeframe, [make_prediction(age_seconds=600)])
        signal = strategy.evaluate(context)
        assert signal is not None
        assert signal.signal_type is SignalType.HOLD
        assert "stale" in signal.reason

    def test_hold_on_low_confidence(self, symbol, timeframe):
        strategy = AiDirectionalStrategy(min_confidence=0.8)
        context = make_context(symbol, timeframe, [make_prediction(confidence=0.5)])
        signal = strategy.evaluate(context)
        assert signal is not None
        assert signal.signal_type is SignalType.HOLD
        assert "confidence" in signal.reason

    def test_rejects_prediction_from_the_future(self, symbol, timeframe):
        """A prediction generated after the decision time is lookahead."""
        strategy = AiDirectionalStrategy()
        context = make_context(symbol, timeframe, [make_prediction(age_seconds=-60)])
        signal = strategy.evaluate(context)
        assert signal is not None
        assert signal.signal_type is SignalType.HOLD
        assert "after the decision" in signal.reason

    def test_disabled_strategy_emits_nothing(self, symbol, timeframe):
        strategy = AiDirectionalStrategy(state=StrategyState.DISABLED)
        context = make_context(symbol, timeframe, [make_prediction()])
        assert strategy.evaluate(context) is None

    def test_strength_scales_with_confidence(self, symbol, timeframe):
        strategy = AiDirectionalStrategy(min_confidence=0.5)
        weak = strategy.evaluate(
            make_context(symbol, timeframe, [make_prediction(confidence=0.55)])
        )
        strong = strategy.evaluate(
            make_context(symbol, timeframe, [make_prediction(confidence=0.99)])
        )
        assert weak is not None and strong is not None
        assert weak.strength is SignalStrength.WEAK
        assert strong.strength is SignalStrength.VERY_STRONG

    def test_is_deterministic(self, symbol, timeframe):
        strategy = AiDirectionalStrategy()
        context = make_context(symbol, timeframe, [make_prediction()])
        assert strategy.evaluate(context) == strategy.evaluate(context)


# ============================================================== validator ===
class TestDefaultSignalValidator:
    def test_approves_a_well_formed_signal(self, symbol, timeframe):
        validator = DefaultSignalValidator()
        signal = make_signal(symbol, timeframe)
        assert validator.validate(signal, make_context(symbol, timeframe)).approved

    def test_rejects_symbol_mismatch(self, symbol, timeframe):
        from ShadBotTrader.domain.market.symbol import Symbol

        validator = DefaultSignalValidator()
        signal = make_signal(Symbol("EURUSD"), timeframe)
        verdict = validator.validate(signal, make_context(symbol, timeframe))
        assert not verdict.approved
        assert verdict.rejection_reason is RejectionReason.SYMBOL_MISMATCH

    def test_rejects_stale_signal(self, symbol, timeframe):
        validator = DefaultSignalValidator(max_signal_age_seconds=60)
        old = Timestamp(BASE_TIME - timedelta(seconds=600))
        verdict = validator.validate(
            make_signal(symbol, timeframe, timestamp=old),
            make_context(symbol, timeframe),
        )
        assert not verdict.approved
        assert verdict.rejection_reason is RejectionReason.STALE_PREDICTION

    def test_rejects_future_signal(self, symbol, timeframe):
        validator = DefaultSignalValidator()
        future = Timestamp(BASE_TIME + timedelta(seconds=60))
        verdict = validator.validate(
            make_signal(symbol, timeframe, timestamp=future),
            make_context(symbol, timeframe),
        )
        assert not verdict.approved

    def test_rejects_low_confidence_actionable_signal(self, symbol, timeframe):
        validator = DefaultSignalValidator(min_confidence=0.8)
        verdict = validator.validate(
            make_signal(symbol, timeframe, confidence=0.2),
            make_context(symbol, timeframe),
        )
        assert not verdict.approved
        assert verdict.rejection_reason is RejectionReason.LOW_CONFIDENCE


# ======================================================== decision engine ===
class TestPositionAwareDecisionEngine:
    def test_flat_plus_buy_enters(self, symbol, timeframe):
        engine = PositionAwareDecisionEngine()
        decision = engine.decide(
            make_signal(symbol, timeframe, SignalType.BUY),
            make_context(symbol, timeframe, portfolio=flat_portfolio()),
        )
        assert decision.decision_type is DecisionType.ENTER

    def test_long_plus_buy_holds(self, symbol, timeframe):
        engine = PositionAwareDecisionEngine()
        decision = engine.decide(
            make_signal(symbol, timeframe, SignalType.BUY),
            make_context(symbol, timeframe, portfolio=long_portfolio()),
        )
        assert decision.decision_type is DecisionType.HOLD

    def test_long_plus_sell_exits_by_default(self, symbol, timeframe):
        engine = PositionAwareDecisionEngine(allow_reversal=False)
        decision = engine.decide(
            make_signal(symbol, timeframe, SignalType.SELL),
            make_context(symbol, timeframe, portfolio=long_portfolio()),
        )
        assert decision.decision_type is DecisionType.EXIT

    def test_reversal_can_be_enabled(self, symbol, timeframe):
        engine = PositionAwareDecisionEngine(allow_reversal=True)
        decision = engine.decide(
            make_signal(symbol, timeframe, SignalType.SELL),
            make_context(symbol, timeframe, portfolio=long_portfolio()),
        )
        assert decision.decision_type is DecisionType.ENTER

    def test_short_plus_sell_holds(self, symbol, timeframe):
        engine = PositionAwareDecisionEngine()
        decision = engine.decide(
            make_signal(symbol, timeframe, SignalType.SELL),
            make_context(symbol, timeframe, portfolio=short_portfolio()),
        )
        assert decision.decision_type is DecisionType.HOLD

    def test_exit_while_flat_holds(self, symbol, timeframe):
        engine = PositionAwareDecisionEngine()
        decision = engine.decide(
            make_signal(symbol, timeframe, SignalType.EXIT),
            make_context(symbol, timeframe, portfolio=flat_portfolio()),
        )
        assert decision.decision_type is DecisionType.HOLD

    def test_hold_signal_yields_hold_decision(self, symbol, timeframe):
        engine = PositionAwareDecisionEngine()
        decision = engine.decide(
            make_signal(symbol, timeframe, SignalType.HOLD),
            make_context(symbol, timeframe, portfolio=flat_portfolio()),
        )
        assert decision.decision_type is DecisionType.HOLD
        assert decision.rejection_reason is RejectionReason.NO_SIGNAL

    def test_decision_carries_signal_direction(self, symbol, timeframe):
        engine = PositionAwareDecisionEngine()
        decision = engine.decide(
            make_signal(symbol, timeframe, SignalType.BUY),
            make_context(symbol, timeframe, portfolio=flat_portfolio()),
        )
        assert decision.context["signal_type"] == SignalType.BUY.value


# =============================================================== risk gate ===
class TestPolicyRiskGate:
    def _enter(self, symbol, timeframe, confidence=0.9):
        return PositionAwareDecisionEngine().decide(
            make_signal(symbol, timeframe, SignalType.BUY, confidence=confidence),
            make_context(symbol, timeframe, portfolio=flat_portfolio()),
        )

    def test_approves_within_policy(self, symbol, timeframe):
        gate = PolicyRiskGate()
        decision = self._enter(symbol, timeframe)
        context = make_context(symbol, timeframe, portfolio=flat_portfolio())
        assert gate.evaluate(decision, context).approved

    def test_blocks_entry_on_breached_drawdown(self, symbol, timeframe):
        gate = PolicyRiskGate(RiskPolicy(max_drawdown_percent=Decimal("10")))
        decision = self._enter(symbol, timeframe)
        context = make_context(
            symbol, timeframe, portfolio=flat_portfolio(), risk_state=breached_risk()
        )
        verdict = gate.evaluate(decision, context)
        assert not verdict.approved
        assert verdict.rejection_reason is RejectionReason.RISK_MAX_DRAWDOWN

    def test_always_allows_exit_even_when_risk_is_breached(self, symbol, timeframe):
        """Refusing to let a position close would itself be a risk."""
        gate = PolicyRiskGate(RiskPolicy(max_drawdown_percent=Decimal("1")))
        decision = PositionAwareDecisionEngine().decide(
            make_signal(symbol, timeframe, SignalType.EXIT),
            make_context(symbol, timeframe, portfolio=long_portfolio()),
        )
        context = make_context(
            symbol, timeframe, portfolio=long_portfolio(), risk_state=breached_risk()
        )
        assert decision.decision_type is DecisionType.EXIT
        assert gate.evaluate(decision, context).approved

    def test_blocks_when_position_limit_reached(self, symbol, timeframe):
        from ShadBotTrader.domain.strategy.strategy_context import PortfolioView

        gate = PolicyRiskGate(RiskPolicy(max_open_positions=1))
        decision = self._enter(symbol, timeframe)
        crowded = PortfolioView(
            equity=Decimal("10000"),
            open_position_quantity=Decimal("0"),
            open_position_count=3,
        )
        verdict = gate.evaluate(decision, make_context(symbol, timeframe, portfolio=crowded))
        assert not verdict.approved
        assert verdict.rejection_reason is RejectionReason.RISK_POSITION_LIMIT

    def test_blocks_on_low_confidence(self, symbol, timeframe):
        gate = PolicyRiskGate(RiskPolicy(min_confidence=0.9))
        decision = self._enter(symbol, timeframe, confidence=0.3)
        verdict = gate.evaluate(
            decision, make_context(symbol, timeframe, portfolio=flat_portfolio())
        )
        assert not verdict.approved
        assert verdict.rejection_reason is RejectionReason.LOW_CONFIDENCE

    def test_hold_needs_no_risk_check(self, symbol, timeframe):
        gate = PolicyRiskGate(RiskPolicy(max_drawdown_percent=Decimal("0")))
        decision = PositionAwareDecisionEngine().decide(
            make_signal(symbol, timeframe, SignalType.HOLD),
            make_context(symbol, timeframe, portfolio=flat_portfolio()),
        )
        assert gate.evaluate(decision, make_context(symbol, timeframe)).approved


# ========================================================== intent factory ===
class TestDefaultIntentFactory:
    def _enter(self, symbol, timeframe, signal_type=SignalType.BUY):
        return PositionAwareDecisionEngine().decide(
            make_signal(symbol, timeframe, signal_type),
            make_context(symbol, timeframe, portfolio=flat_portfolio()),
        )

    def test_builds_enter_intent_with_correct_side(self, symbol, timeframe):
        factory = DefaultIntentFactory(base_quantity=Decimal("2"))
        intent = factory.build(
            self._enter(symbol, timeframe, SignalType.BUY),
            make_context(symbol, timeframe, portfolio=flat_portfolio()),
        )
        assert intent is not None
        assert intent.intent_type is IntentType.ENTER_POSITION
        assert intent.side is OrderSide.BUY
        assert intent.quantity_policy.value == Decimal("2")

    def test_sell_signal_produces_sell_side(self, symbol, timeframe):
        factory = DefaultIntentFactory()
        intent = factory.build(
            self._enter(symbol, timeframe, SignalType.SELL),
            make_context(symbol, timeframe, portfolio=flat_portfolio()),
        )
        assert intent is not None
        assert intent.side is OrderSide.SELL

    def test_exit_side_is_opposite_of_open_position(self, symbol, timeframe):
        factory = DefaultIntentFactory()
        decision = PositionAwareDecisionEngine().decide(
            make_signal(symbol, timeframe, SignalType.EXIT),
            make_context(symbol, timeframe, portfolio=long_portfolio()),
        )
        intent = factory.build(
            decision, make_context(symbol, timeframe, portfolio=long_portfolio())
        )
        assert intent is not None
        assert intent.intent_type is IntentType.EXIT_POSITION
        assert intent.side is OrderSide.SELL  # closing a long

    def test_hold_produces_no_intent(self, symbol, timeframe):
        factory = DefaultIntentFactory()
        decision = PositionAwareDecisionEngine().decide(
            make_signal(symbol, timeframe, SignalType.HOLD),
            make_context(symbol, timeframe, portfolio=flat_portfolio()),
        )
        assert factory.build(decision, make_context(symbol, timeframe)) is None

    def test_confidence_weighted_sizing_is_capped(self, symbol, timeframe):
        factory = DefaultIntentFactory(
            base_quantity=Decimal("10"),
            quantity_policy_type=QuantityPolicyType.CONFIDENCE_WEIGHTED,
        )
        intent = factory.build(
            self._enter(symbol, timeframe),
            make_context(symbol, timeframe, portfolio=flat_portfolio()),
        )
        assert intent is not None
        assert intent.quantity_policy.policy_type is QuantityPolicyType.CONFIDENCE_WEIGHTED
        assert intent.quantity_policy.value < Decimal("10")
        assert intent.quantity_policy.max_quantity == Decimal("10")

    def test_intent_expires(self, symbol, timeframe):
        factory = DefaultIntentFactory(expiration_seconds=30)
        intent = factory.build(
            self._enter(symbol, timeframe),
            make_context(symbol, timeframe, portfolio=flat_portfolio()),
        )
        assert intent is not None
        assert intent.expires_at is not None
        assert intent.is_expired(Timestamp(BASE_TIME + timedelta(seconds=31)))


# ============================================================= aggregator ===
class TestConfidenceWeightedAggregator:
    def test_majority_direction_wins(self, symbol, timeframe):
        aggregator = ConfidenceWeightedAggregator()
        signals = [
            make_signal(symbol, timeframe, SignalType.BUY, 0.9, strategy_id="a"),
            make_signal(symbol, timeframe, SignalType.BUY, 0.8, strategy_id="b"),
            make_signal(symbol, timeframe, SignalType.SELL, 0.6, strategy_id="c"),
        ]
        result = aggregator.aggregate(signals, make_context(symbol, timeframe))
        assert result is not None
        assert result.signal_type is SignalType.BUY

    def test_tie_yields_hold(self, symbol, timeframe):
        aggregator = ConfidenceWeightedAggregator()
        signals = [
            make_signal(symbol, timeframe, SignalType.BUY, 0.7, strategy_id="a"),
            make_signal(symbol, timeframe, SignalType.SELL, 0.7, strategy_id="b"),
        ]
        result = aggregator.aggregate(signals, make_context(symbol, timeframe))
        assert result is not None
        assert result.signal_type is SignalType.HOLD

    def test_all_hold_yields_hold(self, symbol, timeframe):
        aggregator = ConfidenceWeightedAggregator()
        signals = [make_signal(symbol, timeframe, SignalType.HOLD, 0.0, strategy_id="a")]
        result = aggregator.aggregate(signals, make_context(symbol, timeframe))
        assert result is not None
        assert result.signal_type is SignalType.HOLD

    def test_empty_input_yields_none(self, symbol, timeframe):
        assert ConfidenceWeightedAggregator().aggregate([], make_context(symbol, timeframe)) is None

    def test_minimum_total_confidence_is_enforced(self, symbol, timeframe):
        aggregator = ConfidenceWeightedAggregator(min_total_confidence=5.0)
        signals = [make_signal(symbol, timeframe, SignalType.BUY, 0.9, strategy_id="a")]
        result = aggregator.aggregate(signals, make_context(symbol, timeframe))
        assert result is not None
        assert result.signal_type is SignalType.HOLD


# ================================================================ journal ===
class TestInMemoryDecisionJournal:
    def test_records_and_reports(self, symbol, timeframe):
        from ShadBotTrader.domain.strategy.risk_policy import RiskVerdict

        journal = InMemoryDecisionJournal()
        decision = PositionAwareDecisionEngine().decide(
            make_signal(symbol, timeframe, SignalType.BUY),
            make_context(symbol, timeframe, portfolio=flat_portfolio()),
        )
        journal.record(decision, RiskVerdict.approve(), None)
        journal.record(decision, RiskVerdict.reject(RejectionReason.RISK_EXPOSURE), None)

        assert len(journal.entries()) == 2
        assert len(journal.rejected) == 1
        assert journal.rejection_counts()["risk_exposure"] == 1

        journal.clear()
        assert journal.entries() == []


class TestDecisionIdentity:
    """Regression guards for decision/intent identity collisions."""

    def test_enter_and_exit_from_the_same_bar_get_distinct_ids(self):
        """An ENTER and an EXIT must never share a decision id.

        They previously did, because the id was derived from the signal
        alone. The resulting intents collided, and the executor's
        idempotency guard silently refused to close the position —
        leaving it stuck open. The decision type is now part of the id.
        """
        engine = PositionAwareDecisionEngine()
        enter = engine.decide(
            make_signal(XAU_SYMBOL, TF, SignalType.BUY),
            make_context(XAU_SYMBOL, TF, portfolio=flat_portfolio()),
        )
        exit_ = engine.decide(
            make_signal(XAU_SYMBOL, TF, SignalType.SELL),
            make_context(XAU_SYMBOL, TF, portfolio=long_portfolio()),
        )

        assert enter.decision_type is DecisionType.ENTER
        assert exit_.decision_type is DecisionType.EXIT
        assert enter.decision_id != exit_.decision_id

    def test_distinct_decisions_yield_distinct_intents(self):
        factory = DefaultIntentFactory()
        engine = PositionAwareDecisionEngine()

        enter = engine.decide(
            make_signal(XAU_SYMBOL, TF, SignalType.BUY),
            make_context(XAU_SYMBOL, TF, portfolio=flat_portfolio()),
        )
        exit_ = engine.decide(
            make_signal(XAU_SYMBOL, TF, SignalType.SELL),
            make_context(XAU_SYMBOL, TF, portfolio=long_portfolio()),
        )

        enter_intent = factory.build(
            enter, make_context(XAU_SYMBOL, TF, portfolio=flat_portfolio())
        )
        exit_intent = factory.build(exit_, make_context(XAU_SYMBOL, TF, portfolio=long_portfolio()))

        assert enter_intent is not None and exit_intent is not None
        assert enter_intent.intent_id != exit_intent.intent_id

    def test_same_decision_is_stable(self):
        """Determinism: identical input must still give an identical id."""
        engine = PositionAwareDecisionEngine()
        signal = make_signal(XAU_SYMBOL, TF, SignalType.BUY)
        context = make_context(XAU_SYMBOL, TF, portfolio=flat_portfolio())
        assert engine.decide(signal, context).decision_id == (
            engine.decide(signal, context).decision_id
        )
