"""Command-line interface for the Self-Learning Platform (Sprint P7).

python -m ShadBotTrader.learning_cli optimise --folds 3
python -m ShadBotTrader.learning_cli objectives
python -m ShadBotTrader.learning_cli policy
"""

from __future__ import annotations

import argparse
import sys
from decimal import Decimal
from pathlib import Path
from typing import List

from ShadBotTrader.application.services.optimisation_service import (
    OptimisationService,
    default_baseline,
)
from ShadBotTrader.data_cli import build_service as build_data_service
from ShadBotTrader.data_cli import generate_sample
from ShadBotTrader.domain.learning.objective import (
    MaxDrawdownObjective,
    RiskAdjustedObjective,
    SharpeObjective,
    TotalReturnObjective,
)
from ShadBotTrader.domain.learning.promotion import PromotionPolicy
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timeframe import Timeframe
from ShadBotTrader.domain.simulation.session import SimulationConfiguration
from ShadBotTrader.infrastructure.learning import (
    ConsoleOptimisationReporter,
    GridSearchGenerator,
    RandomSearchGenerator,
)

DEFAULT_STORAGE_ROOT = Path.cwd() / "datasets"

OBJECTIVES = {
    "risk_adjusted": lambda: RiskAdjustedObjective(min_trades=3),
    "total_return": TotalReturnObjective,
    "sharpe": SharpeObjective,
    "max_drawdown": MaxDrawdownObjective,
}


def cmd_objectives(args: argparse.Namespace) -> int:
    """Explain the available definitions of 'better'."""
    print("Learning objectives — each is a different definition of 'better':\n")
    descriptions = {
        "risk_adjusted": "net return divided by drawdown; penalises thin samples (default)",
        "total_return": "raw return only — ignores risk entirely, use with care",
        "sharpe": "return per unit of volatility; penalised when undefined",
        "max_drawdown": "minimise the worst peak-to-trough decline",
    }
    for name in sorted(OBJECTIVES):
        objective = OBJECTIVES[name]()
        print(f"  {name:<16} [{objective.direction.value}] {descriptions[name]}")
    return 0


def cmd_policy(args: argparse.Namespace) -> int:
    """Show the promotion gate a candidate must clear."""
    policy = PromotionPolicy(
        min_out_of_sample_trades=args.min_trades,
        min_validation_folds=args.min_folds,
        max_drawdown_percent=Decimal(str(args.max_drawdown)),
        min_positive_fold_ratio=Decimal(str(args.min_positive_ratio)),
        max_overfit_gap=Decimal(str(args.max_overfit_gap)),
    )
    print("Promotion policy (a candidate must clear ALL of these):\n")
    print(f"  min out-of-sample trades : {policy.min_out_of_sample_trades}")
    print(f"  min validation folds     : {policy.min_validation_folds}")
    print(f"  max drawdown             : {policy.max_drawdown_percent}%")
    print(f"  require positive return  : {policy.require_positive_return}")
    print(f"  min positive fold ratio  : {policy.min_positive_fold_ratio}")
    print(f"  max overfit gap          : {policy.max_overfit_gap}")
    print(f"  min improvement          : {policy.min_improvement}")
    print("\nAll checks are applied to OUT-OF-SAMPLE folds only.")
    return 0


def cmd_optimise(args: argparse.Namespace) -> int:
    """Run a walk-forward parameter search."""
    storage_root = Path(args.storage_root)
    sample_path = storage_root / "samples" / f"{args.symbol}_{args.timeframe}.csv"
    if not sample_path.exists():
        generate_sample(args.symbol, args.timeframe, 400, sample_path)

    data_service, candle_store, _ = build_data_service(storage_root)
    candles = candle_store.query(Symbol(args.symbol), Timeframe(args.timeframe))
    if not candles:
        data_service.ingest(args.symbol, args.timeframe, str(sample_path))
        candles = candle_store.query(Symbol(args.symbol), Timeframe(args.timeframe))

    generator = (
        RandomSearchGenerator(count=args.random, seed=args.seed)
        if args.random > 0
        else GridSearchGenerator(max_candidates=args.max_candidates)
    )

    service = OptimisationService(
        symbol=Symbol(args.symbol),
        timeframe=Timeframe(args.timeframe),
        simulation_config=SimulationConfiguration(
            initial_capital=Decimal(str(args.capital)),
            spread=Decimal(str(args.spread)),
            commission_rate=Decimal(str(args.commission)),
            seed=args.seed,
            warmup_bars=args.warmup,
        ),
        objective=OBJECTIVES[args.objective](),
        promotion_policy=PromotionPolicy(
            min_out_of_sample_trades=args.min_trades,
            min_validation_folds=max(args.folds - 1, 1),
            max_drawdown_percent=Decimal(str(args.max_drawdown)),
            max_overfit_gap=Decimal(str(args.max_overfit_gap)),
        ),
        generator=generator,
        validate_top_n=args.top,
    )

    result = service.run(
        experiment_id=args.experiment_id,
        parameter_values={
            "lookback": [int(value) for value in args.lookbacks.split(",")],
            "strategy_min_confidence": [float(value) for value in args.confidences.split(",")],
        },
        candles=candles,
        baseline=default_baseline(),
        in_sample_ratio=args.in_sample,
        fold_count=args.folds,
        reporter=ConsoleOptimisationReporter(show_candidates=not args.quiet),
    )

    print("=== Promotion gate ===")
    if result.verdict is None:
        print("  no candidate reached the gate")
    elif result.verdict.approved:
        print(f"  APPROVED — {result.verdict.reason}")
    else:
        reason = result.verdict.rejection_reason
        print(f"  REJECTED ({reason.value if reason else 'unknown'})")
        print(f"  {result.verdict.reason}")
    return 0


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ShadBotTrader Self-Learning CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    objectives = subparsers.add_parser("objectives", help="list learning objectives")
    objectives.set_defaults(func=cmd_objectives)

    policy = subparsers.add_parser("policy", help="show the promotion gate")
    policy.add_argument("--min-trades", type=int, default=5)
    policy.add_argument("--min-folds", type=int, default=2)
    policy.add_argument("--max-drawdown", type=float, default=25.0)
    policy.add_argument("--min-positive-ratio", type=float, default=0.5)
    policy.add_argument("--max-overfit-gap", type=float, default=5.0)
    policy.set_defaults(func=cmd_policy)

    optimise = subparsers.add_parser("optimise", help="run a walk-forward search")
    optimise.add_argument("--symbol", default="XAUUSD_i")
    optimise.add_argument("--timeframe", default="5M")
    optimise.add_argument("--storage-root", default=str(DEFAULT_STORAGE_ROOT))
    optimise.add_argument("--experiment-id", default="cli")
    optimise.add_argument("--capital", type=float, default=100.0)
    optimise.add_argument("--spread", type=float, default=4.0)
    optimise.add_argument("--commission", type=float, default=0.0001)
    optimise.add_argument("--warmup", type=int, default=10)
    optimise.add_argument("--folds", type=int, default=3)
    optimise.add_argument("--in-sample", type=float, default=0.5)
    optimise.add_argument("--top", type=int, default=3)
    optimise.add_argument("--objective", choices=sorted(OBJECTIVES), default="risk_adjusted")
    optimise.add_argument("--lookbacks", default="3,6,12")
    optimise.add_argument("--confidences", default="0.55,0.65,0.75")
    optimise.add_argument("--random", type=int, default=0)
    optimise.add_argument("--max-candidates", type=int, default=None)
    optimise.add_argument("--min-trades", type=int, default=5)
    optimise.add_argument("--max-drawdown", type=float, default=25.0)
    optimise.add_argument("--max-overfit-gap", type=float, default=5.0)
    optimise.add_argument("--seed", type=int, default=42)
    optimise.add_argument("--quiet", action="store_true")
    optimise.set_defaults(func=cmd_optimise)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
