"""Integration tests for the Trading Platform pipeline (Phase 14).

Verifies the end-to-end flow

    prediction -> strategy -> validation -> decision -> RISK GATE -> intent

and, most importantly, the architectural invariants that must hold no
matter how the pipeline is configured.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from ShadBotTrader.application.services.trading_decision_service import (
    TradingDecisionService,
)
from ShadBotTrader.core.events.event_bus import EventBus
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timeframe import Timeframe
from ShadBotTrader.domain.market.timestamp import Timestamp
from ShadBotTrader.domain.risk.risk_state import RiskState
from ShadBotTrader.domain.strategy.events import INTENT_CREATED, RISK_REJECTED
from ShadBotTrader.domain.strategy.risk_policy import RiskPolicy
from ShadBotTrader.domain.strategy.strategy_context import (
    PortfolioView,
    PredictionView,
    StrategyContext,
)
from ShadBotTrader.domain.strategy.strategy_types import (
    DecisionType,
    IntentType,
    RejectionReason,
    SignalType,
)
from ShadBotTrader.domain.trading.order import Order, OrderSide
from ShadBotTrader.infrastructure.trading import (
    AiDirectionalStrategy,
    ConfidenceWeightedAggregator,
    DefaultIntentFactory,
    DefaultSignalValidator,
    InMemoryDecisionJournal,
    PolicyRiskGate,
    PositionAwareDecisionEngine,
)

NOW = datetime(2026, 8, 16, 12, 0, tzinfo=timezone.utc)
SYMBOL = Symbol("XAUUSD_i")
TIMEFRAME = Timeframe("5M")


def build_service(
    policy: RiskPolicy | None = None,
    strategies=None,
    journal=None,
    event_bus=None,
) -> TradingDecisionService:
    strategies = strategies or [AiDirectionalStrategy(min_confidence=0.55)]
    return TradingDecisionService(
        strategies=strategies,
        decision_engine=PositionAwareDecisionEngine(),
        risk_gate=PolicyRiskGate(policy or RiskPolicy()),
        intent_factory=DefaultIntentFactory(base_quantity=Decimal("1")),
        validator=DefaultSignalValidator(max_signal_age_seconds=600),
        aggregator=ConfidenceWeightedAggregator() if strategies and len(strategies) > 1 else None,
        journal=journal,
        event_bus=event_bus,
    )


def context(
    value: float = 0.9,
    confidence: float = 0.9,
    age_seconds: float = 0.0,
    quantity: str = "0",
    positions: int = 0,
    risk: RiskState | None = None,
) -> StrategyContext:
    return StrategyContext(
        timestamp=Timestamp(NOW),
        symbol=SYMBOL,
        timeframe=TIMEFRAME,
        predictions=[
            PredictionView(
                model_id="gold_direction",
                model_version=1,
                value=value,
                confidence=confidence,
                generated_at=Timestamp(NOW - timedelta(seconds=age_seconds)),
            )
        ],
        portfolio=PortfolioView(
            equity=Decimal("10000"),
            open_position_quantity=Decimal(quantity),
            open_position_count=positions,
        ),
        risk_state=risk,
    )


# ------------------------------------------------------------ happy paths ---
def test_confident_up_prediction_produces_a_buy_intent():
    outcome = build_service().evaluate(context(value=0.9, confidence=0.9))

    assert outcome.signal is not None
    assert outcome.signal.signal_type is SignalType.BUY
    assert outcome.decision is not None
    assert outcome.decision.decision_type is DecisionType.ENTER
    assert outcome.verdict is not None and outcome.verdict.approved
    assert outcome.intent is not None
    assert outcome.intent.intent_type is IntentType.ENTER_POSITION
    assert outcome.intent.side is OrderSide.BUY


def test_confident_down_prediction_produces_a_sell_intent():
    outcome = build_service().evaluate(context(value=0.1, confidence=0.9))
    assert outcome.intent is not None
    assert outcome.intent.side is OrderSide.SELL


def test_exit_intent_when_signal_reverses_against_a_long():
    # long position + confident DOWN prediction -> flatten
    outcome = build_service().evaluate(context(value=0.05, confidence=0.95, quantity="1"))
    assert outcome.decision is not None
    assert outcome.decision.decision_type is DecisionType.EXIT
    assert outcome.intent is not None
    assert outcome.intent.intent_type is IntentType.EXIT_POSITION
    assert outcome.intent.side is OrderSide.SELL


# ------------------------------------------------------------- rejections ---
def test_low_confidence_never_reaches_an_intent():
    outcome = build_service().evaluate(context(confidence=0.2))
    assert outcome.intent is None
    assert outcome.decision is not None
    assert outcome.decision.decision_type is DecisionType.HOLD


def test_stale_prediction_never_reaches_an_intent():
    outcome = build_service().evaluate(context(age_seconds=99999))
    assert outcome.intent is None


def test_breached_risk_blocks_the_intent():
    breached = RiskState(
        max_drawdown_percent=Decimal("60"),
        max_daily_loss_percent=Decimal("40"),
        exposure_ratio=Decimal("0.95"),
    )
    outcome = build_service(RiskPolicy(max_drawdown_percent=Decimal("10"))).evaluate(
        context(risk=breached)
    )

    assert outcome.decision is not None
    assert outcome.decision.decision_type is DecisionType.ENTER  # decision was made
    assert outcome.verdict is not None
    assert not outcome.verdict.approved  # but the gate blocked it
    assert outcome.verdict.rejection_reason is RejectionReason.RISK_MAX_DRAWDOWN
    assert outcome.intent is None  # and no intent exists


def test_position_limit_blocks_new_entries():
    outcome = build_service(RiskPolicy(max_open_positions=1)).evaluate(context(positions=5))
    assert outcome.intent is None
    assert outcome.verdict is not None
    assert outcome.verdict.rejection_reason is RejectionReason.RISK_POSITION_LIMIT


# ------------------------------------------------- ARCHITECTURAL INVARIANTS --
class TestArchitecturalInvariants:
    """Guards for the boundaries Phase 14 declares non-negotiable."""

    def test_no_intent_is_ever_produced_without_an_approving_verdict(self):
        """The single most important rule: nothing bypasses the risk gate."""
        scenarios = [
            context(confidence=0.9),
            context(confidence=0.1),
            context(age_seconds=99999),
            context(quantity="1"),
            context(quantity="-1"),
            context(positions=99),
            context(
                risk=RiskState(
                    max_drawdown_percent=Decimal("99"),
                    max_daily_loss_percent=Decimal("99"),
                    exposure_ratio=Decimal("1"),
                )
            ),
        ]
        policies = [
            RiskPolicy(),
            RiskPolicy(max_drawdown_percent=Decimal("1")),
            RiskPolicy(max_open_positions=0),
            RiskPolicy(min_confidence=0.99),
        ]
        for policy in policies:
            service = build_service(policy)
            for scenario in scenarios:
                outcome = service.evaluate(scenario)
                if outcome.intent is not None:
                    assert outcome.verdict is not None, "intent without a risk verdict"
                    assert outcome.verdict.approved, "intent produced despite rejection"

    def test_strategy_output_is_never_an_order(self):
        strategy = AiDirectionalStrategy()
        signal = strategy.evaluate(context())
        assert signal is not None
        assert not isinstance(signal, Order)

    def test_decision_is_never_an_order(self):
        outcome = build_service().evaluate(context())
        assert outcome.decision is not None
        assert not isinstance(outcome.decision, Order)

    def test_intent_is_never_an_order(self):
        """The intent is a contract for the executor, not a broker order."""
        outcome = build_service().evaluate(context())
        assert outcome.intent is not None
        assert not isinstance(outcome.intent, Order)
        # it carries policies, not resolved values
        assert hasattr(outcome.intent, "quantity_policy")
        assert hasattr(outcome.intent, "price_policy")

    def test_pipeline_is_deterministic(self):
        service = build_service()
        scenario = context()
        first = service.evaluate(scenario)
        second = service.evaluate(scenario)
        assert first.signal == second.signal
        assert first.decision == second.decision
        assert first.intent == second.intent


# ----------------------------------------------------------------- audit ---
def test_journal_records_both_approvals_and_rejections():
    journal = InMemoryDecisionJournal()
    service = build_service(RiskPolicy(max_open_positions=1), journal=journal)

    service.evaluate(context())  # approved
    service.evaluate(context(positions=9))  # rejected by the gate

    assert len(journal.entries()) == 2
    assert len(journal.intents) == 1
    assert len(journal.rejected) == 1
    assert journal.rejection_counts()["risk_position_limit"] == 1


def test_pipeline_publishes_events():
    received: list[str] = []
    bus = EventBus()
    bus.subscribe(INTENT_CREATED, lambda event: received.append(event.event_type))
    bus.subscribe(RISK_REJECTED, lambda event: received.append(event.event_type))

    service = build_service(RiskPolicy(max_open_positions=1), event_bus=bus)
    service.evaluate(context())
    service.evaluate(context(positions=9))

    assert INTENT_CREATED in received
    assert RISK_REJECTED in received


# --------------------------------------------------------------- ensemble ---
def test_multiple_strategies_require_an_aggregator():
    with pytest.raises(ValueError, match="Aggregator"):
        TradingDecisionService(
            strategies=[AiDirectionalStrategy(), AiDirectionalStrategy(version=2)],
            decision_engine=PositionAwareDecisionEngine(),
            risk_gate=PolicyRiskGate(),
            intent_factory=DefaultIntentFactory(),
        )


def test_service_requires_at_least_one_strategy():
    with pytest.raises(ValueError, match="at least one strategy"):
        TradingDecisionService(
            strategies=[],
            decision_engine=PositionAwareDecisionEngine(),
            risk_gate=PolicyRiskGate(),
            intent_factory=DefaultIntentFactory(),
        )


def test_ensemble_of_agreeing_strategies_produces_an_intent():
    service = build_service(
        strategies=[
            AiDirectionalStrategy(min_confidence=0.55, version=1),
            AiDirectionalStrategy(min_confidence=0.50, version=2),
        ]
    )
    outcome = service.evaluate(context(value=0.95, confidence=0.9))
    assert outcome.signal is not None
    assert outcome.signal.signal_type is SignalType.BUY
    assert outcome.intent is not None


def test_evaluate_series_processes_every_context():
    service = build_service()
    outcomes = service.evaluate_series([context(), context(confidence=0.1), context(value=0.05)])
    assert len(outcomes) == 3
    assert sum(1 for outcome in outcomes if outcome.produced_intent) == 2
