"""Command-line interface for the Trading Platform (Phase 14).

Inspect the decision pipeline without writing code::

    python -m ShadBotTrader.trading_cli policy
    python -m ShadBotTrader.trading_cli evaluate --value 0.9 --confidence 0.85
    python -m ShadBotTrader.trading_cli evaluate --value 0.1 --confidence 0.9 --position 1
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import List

from ShadBotTrader.application.services.trading_decision_service import (
    TradingDecisionService,
)
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timeframe import Timeframe
from ShadBotTrader.domain.market.timestamp import Timestamp
from ShadBotTrader.domain.risk.risk_state import RiskState
from ShadBotTrader.domain.strategy.risk_policy import RiskPolicy
from ShadBotTrader.domain.strategy.strategy_context import (
    PortfolioView,
    PredictionView,
    StrategyContext,
)
from ShadBotTrader.infrastructure.trading import (
    AiDirectionalStrategy,
    DefaultIntentFactory,
    DefaultSignalValidator,
    InMemoryDecisionJournal,
    PolicyRiskGate,
    PositionAwareDecisionEngine,
)


def _policy(args: argparse.Namespace) -> RiskPolicy:
    return RiskPolicy(
        max_drawdown_percent=Decimal(str(args.max_drawdown)),
        max_daily_loss_percent=Decimal(str(args.max_daily_loss)),
        max_exposure_ratio=Decimal(str(args.max_exposure)),
        max_open_positions=args.max_positions,
        min_confidence=args.min_confidence,
    )


def cmd_policy(args: argparse.Namespace) -> int:
    """Print the effective risk policy."""
    policy = _policy(args)
    print("Risk policy (the mandatory gate between decision and intent):")
    print(f"  max_drawdown_percent   : {policy.max_drawdown_percent}%")
    print(f"  max_daily_loss_percent : {policy.max_daily_loss_percent}%")
    print(f"  max_exposure_ratio     : {policy.max_exposure_ratio}")
    print(f"  max_open_positions     : {policy.max_open_positions}")
    print(f"  min_confidence         : {policy.min_confidence}")
    return 0


def cmd_evaluate(args: argparse.Namespace) -> int:
    """Run one prediction through the full decision pipeline."""
    now = datetime.now(timezone.utc)
    journal = InMemoryDecisionJournal()

    service = TradingDecisionService(
        strategies=[
            AiDirectionalStrategy(
                model_id=args.model,
                min_confidence=args.strategy_min_confidence,
                max_prediction_age_seconds=args.max_age,
            )
        ],
        decision_engine=PositionAwareDecisionEngine(allow_reversal=args.allow_reversal),
        risk_gate=PolicyRiskGate(_policy(args)),
        intent_factory=DefaultIntentFactory(base_quantity=Decimal(str(args.quantity))),
        validator=DefaultSignalValidator(max_signal_age_seconds=args.max_age),
        journal=journal,
    )

    risk_state = None
    if args.drawdown is not None or args.daily_loss is not None or args.exposure is not None:
        risk_state = RiskState(
            max_drawdown_percent=Decimal(str(args.drawdown or 0)),
            max_daily_loss_percent=Decimal(str(args.daily_loss or 0)),
            exposure_ratio=Decimal(str(args.exposure or 0)),
        )

    context = StrategyContext(
        timestamp=Timestamp(now),
        symbol=Symbol(args.symbol),
        timeframe=Timeframe(args.timeframe),
        predictions=[
            PredictionView(
                model_id=args.model,
                model_version=1,
                value=args.value,
                confidence=args.confidence,
                generated_at=Timestamp(now - timedelta(seconds=args.age)),
            )
        ],
        portfolio=PortfolioView(
            equity=Decimal(str(args.equity)),
            open_position_quantity=Decimal(str(args.position)),
            open_position_count=args.open_positions,
        ),
        risk_state=risk_state,
    )

    outcome = service.evaluate(context)

    print(f"=== {args.symbol} {args.timeframe} ===")
    print(f"prediction : value={args.value} confidence={args.confidence} age={args.age}s")
    print(f"position   : {args.position} ({args.open_positions} open)")
    print()

    if outcome.signal is None:
        print("signal     : (none)")
    else:
        print(
            f"signal     : {outcome.signal.signal_type.value.upper()} "
            f"[{outcome.signal.strength.value}] confidence={outcome.signal.confidence:.3f}"
        )
        print(f"             {outcome.signal.reason}")

    if outcome.decision is None:
        print("decision   : (none)")
    else:
        print(f"decision   : {outcome.decision.decision_type.value.upper()}")
        print(f"             {outcome.decision.reason}")

    if outcome.verdict is None:
        print("risk gate  : (not reached)")
    elif outcome.verdict.approved:
        print("risk gate  : PASS")
    else:
        reason = outcome.verdict.rejection_reason
        print(f"risk gate  : BLOCKED ({reason.value if reason else 'unknown'})")
        print(f"             {outcome.verdict.reason}")

    if outcome.intent is None:
        print("intent     : none")
        if outcome.rejected_reason:
            print(f"             {outcome.rejected_reason}")
    else:
        intent = outcome.intent
        print(f"intent     : {intent.intent_type.value} {intent.side.value.upper()}")
        print(
            f"             quantity_policy={intent.quantity_policy.policy_type.value}"
            f"({intent.quantity_policy.value}) "
            f"price_policy={intent.price_policy.policy_type.value}"
        )
        print(f"             expires_at={intent.expires_at}")

    return 0


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ShadBotTrader Trading Platform CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_policy_args(sub: argparse.ArgumentParser) -> None:
        sub.add_argument("--max-drawdown", type=float, default=20.0)
        sub.add_argument("--max-daily-loss", type=float, default=5.0)
        sub.add_argument("--max-exposure", type=float, default=0.5)
        sub.add_argument("--max-positions", type=int, default=5)
        sub.add_argument("--min-confidence", type=float, default=0.0)

    policy_parser = subparsers.add_parser("policy", help="show the risk policy")
    add_policy_args(policy_parser)
    policy_parser.set_defaults(func=cmd_policy)

    evaluate = subparsers.add_parser("evaluate", help="run one prediction through the pipeline")
    evaluate.add_argument("--symbol", default="XAUUSD")
    evaluate.add_argument("--timeframe", default="5M")
    evaluate.add_argument("--model", default="gold_direction")
    evaluate.add_argument("--value", type=float, default=0.9, help="prediction value in [0,1]")
    evaluate.add_argument("--confidence", type=float, default=0.85)
    evaluate.add_argument("--age", type=float, default=0.0, help="prediction age in seconds")
    evaluate.add_argument("--max-age", type=float, default=300.0)
    evaluate.add_argument("--strategy-min-confidence", type=float, default=0.55)
    evaluate.add_argument("--position", type=float, default=0.0, help="signed open quantity")
    evaluate.add_argument("--open-positions", type=int, default=0)
    evaluate.add_argument("--equity", type=float, default=10000.0)
    evaluate.add_argument("--quantity", type=float, default=1.0, help="base order size")
    evaluate.add_argument("--allow-reversal", action="store_true")
    evaluate.add_argument("--drawdown", type=float, default=None)
    evaluate.add_argument("--daily-loss", type=float, default=None)
    evaluate.add_argument("--exposure", type=float, default=None)
    add_policy_args(evaluate)
    evaluate.set_defaults(func=cmd_evaluate)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
