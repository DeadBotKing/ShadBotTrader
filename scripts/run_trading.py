"""Demo run of the Trading Platform (Phase 14) without installing the package.

Walks a sequence of market situations through the full pipeline

    prediction -> strategy -> validation -> decision -> RISK GATE -> intent

and prints what happened at every step, including why a trade was
blocked. No orders are ever created: the pipeline stops at a
``TradingIntent``, which is the contract handed to the (future)
Execution Platform.

    python scripts/run_trading.py
    python scripts/run_trading.py --persist    # keep the decisions
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ShadBotTrader.application.persistence_context import (  # noqa: E402
    add_persistence_arguments,
    context_from_args,
)
from ShadBotTrader.application.services.trading_decision_service import (  # noqa: E402
    TradingDecisionService,
)
from ShadBotTrader.core.events.event_bus import EventBus  # noqa: E402
from ShadBotTrader.domain.market.symbol import Symbol  # noqa: E402
from ShadBotTrader.domain.market.timeframe import Timeframe  # noqa: E402
from ShadBotTrader.domain.market.timestamp import Timestamp  # noqa: E402
from ShadBotTrader.domain.risk.risk_state import RiskState  # noqa: E402
from ShadBotTrader.domain.strategy.risk_policy import RiskPolicy  # noqa: E402
from ShadBotTrader.domain.strategy.strategy_context import (  # noqa: E402
    PortfolioView,
    PredictionView,
    StrategyContext,
)
from ShadBotTrader.infrastructure.trading import (  # noqa: E402
    AiDirectionalStrategy,
    DefaultIntentFactory,
    DefaultSignalValidator,
    PolicyRiskGate,
    PositionAwareDecisionEngine,
)

NOW = datetime(2026, 8, 16, 12, 0, tzinfo=timezone.utc)
SYMBOL = Symbol("XAUUSD_i")
TIMEFRAME = Timeframe("5M")


def scenario(
    title: str,
    value: float,
    confidence: float,
    age_seconds: float = 0.0,
    quantity: str = "0",
    positions: int = 0,
    risk: RiskState | None = None,
) -> tuple[str, StrategyContext]:
    context = StrategyContext(
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
    return title, context


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Trading Platform demo.")
    add_persistence_arguments(parser, prefix="trading")
    args = parser.parse_args(argv)
    storage = context_from_args(args, prefix="trading")

    print("=== Trading Platform demo (Phase 14) ===")
    print("Pipeline: strategy -> validate -> decide -> RISK GATE -> intent")
    print("No orders are produced; the pipeline stops at a TradingIntent.")
    print(f"Storage: {storage.description}\n")

    policy = RiskPolicy(
        max_drawdown_percent=Decimal("15"),
        max_daily_loss_percent=Decimal("5"),
        max_exposure_ratio=Decimal("0.5"),
        max_open_positions=3,
        min_confidence=0.5,
    )
    journal = storage.decision_journal()
    events: list[str] = []
    bus = EventBus()
    for event_name in ("SignalGenerated", "DecisionMade", "RiskRejected", "IntentCreated"):
        bus.subscribe(event_name, lambda event: events.append(event.event_type))

    service = TradingDecisionService(
        strategies=[AiDirectionalStrategy(min_confidence=0.55)],
        decision_engine=PositionAwareDecisionEngine(),
        risk_gate=PolicyRiskGate(policy),
        intent_factory=DefaultIntentFactory(base_quantity=Decimal("1")),
        validator=DefaultSignalValidator(max_signal_age_seconds=600),
        journal=journal,
        event_bus=bus,
    )

    print("Risk policy:")
    print(f"  max drawdown    : {policy.max_drawdown_percent}%")
    print(f"  max daily loss  : {policy.max_daily_loss_percent}%")
    print(f"  max exposure    : {policy.max_exposure_ratio}")
    print(f"  max positions   : {policy.max_open_positions}")
    print(f"  min confidence  : {policy.min_confidence}")
    print()

    scenarios = [
        scenario("confident UP, flat", value=0.92, confidence=0.88),
        scenario("confident DOWN, flat", value=0.08, confidence=0.91),
        scenario("weak signal, flat", value=0.55, confidence=0.30),
        scenario("stale prediction", value=0.95, confidence=0.95, age_seconds=3600),
        scenario("UP while already long", value=0.90, confidence=0.85, quantity="1"),
        scenario("DOWN while long (reversal)", value=0.05, confidence=0.93, quantity="1"),
        scenario(
            "confident UP but drawdown breached",
            value=0.95,
            confidence=0.95,
            risk=RiskState(
                max_drawdown_percent=Decimal("40"),
                max_daily_loss_percent=Decimal("2"),
                exposure_ratio=Decimal("0.2"),
            ),
        ),
        scenario("confident UP but too many positions", 0.93, 0.9, positions=9),
    ]

    header = f"{'scenario':<34} {'signal':<7} {'decision':<9} {'risk':<9} {'intent'}"
    print(header)
    print("-" * len(header))

    for title, context in scenarios:
        outcome = service.evaluate(context)

        signal = outcome.signal.signal_type.value if outcome.signal else "-"
        decision = outcome.decision.decision_type.value if outcome.decision else "-"
        if outcome.verdict is None:
            risk = "-"
        else:
            risk = "PASS" if outcome.verdict.approved else "BLOCKED"
        if outcome.intent is None:
            intent = "none"
        else:
            intent = f"{outcome.intent.intent_type.value} {outcome.intent.side.value}"

        print(f"{title:<34} {signal:<7} {decision:<9} {risk:<9} {intent}")
        if outcome.intent is None and outcome.rejected_reason:
            print(f"{'':<34} -> {outcome.rejected_reason}")

    print()
    print("=== Audit trail ===")
    print(f"  decisions recorded : {len(journal.entries())}")
    print(f"  intents produced   : {len(journal.intents)}")
    print(f"  blocked by risk    : {len(journal.rejected)}")
    counts = journal.rejection_counts()
    if counts:
        print("  rejection reasons  :")
        for reason, count in sorted(counts.items()):
            print(f"      {reason:<24} {count}")

    print()
    print(f"=== Events published: {len(events)} ===")
    for name in sorted(set(events)):
        print(f"  {name:<20} x{events.count(name)}")

    # The invariant this whole platform is built around.
    for entry in journal.entries():
        if entry.intent is not None:
            assert entry.verdict is not None and entry.verdict.approved

    print("\nInvariant verified: every intent passed the risk gate.")
    print()
    for line in storage.summary_lines():
        print(f"  {line}")
    storage.close()

    print("\nTrading Platform demo finished successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
