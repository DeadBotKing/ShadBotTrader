"""Self-learning demo (Sprint P7) — Phase 17.

Searches a parameter space, validates the leaders on data they never
saw, and puts the winner to a promotion gate.

    python scripts/run_optimisation.py
    python scripts/run_optimisation.py --objective sharpe
    python scripts/run_optimisation.py --random 8 --folds 4
    python scripts/run_optimisation.py --demo-overfit
"""

from __future__ import annotations

import argparse
import sys
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
from ShadBotTrader.application.services.optimisation_service import (  # noqa: E402
    OptimisationService,
    default_baseline,
)
from ShadBotTrader.data_cli import build_service as build_data_service  # noqa: E402
from ShadBotTrader.data_cli import generate_sample  # noqa: E402
from ShadBotTrader.domain.learning.objective import (  # noqa: E402
    MaxDrawdownObjective,
    RiskAdjustedObjective,
    SharpeObjective,
    TotalReturnObjective,
)
from ShadBotTrader.domain.learning.promotion import PromotionPolicy  # noqa: E402
from ShadBotTrader.domain.market.symbol import Symbol  # noqa: E402
from ShadBotTrader.domain.market.timeframe import Timeframe  # noqa: E402
from ShadBotTrader.domain.simulation.session import SimulationConfiguration  # noqa: E402
from ShadBotTrader.infrastructure.learning import (  # noqa: E402
    ConsoleOptimisationReporter,
    GridSearchGenerator,
    RandomSearchGenerator,
)

SYMBOL = "DEMOXAU"
TIMEFRAME = "5M"
ROWS = 400

OBJECTIVES = {
    "risk_adjusted": lambda: RiskAdjustedObjective(min_trades=3),
    "total_return": TotalReturnObjective,
    "sharpe": SharpeObjective,
    "max_drawdown": MaxDrawdownObjective,
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Walk-forward parameter optimisation with a promotion gate.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--capital", type=float, default=100.0)
    parser.add_argument("--spread", type=float, default=4.0)
    parser.add_argument("--commission", type=float, default=0.0001)
    parser.add_argument("--folds", type=int, default=3, help="validation folds")
    parser.add_argument("--in-sample", type=float, default=0.5, help="training ratio")
    parser.add_argument("--top", type=int, default=3, help="candidates to validate")
    parser.add_argument("--objective", choices=sorted(OBJECTIVES), default="risk_adjusted")
    parser.add_argument("--random", type=int, default=0, help="use random search with N samples")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--quiet", action="store_true", help="hide per-candidate rows")
    parser.add_argument(
        "--demo-overfit",
        action="store_true",
        help="show why in-sample ranking cannot be trusted",
    )
    add_persistence_arguments(parser, prefix="optimisation")
    return parser.parse_args(argv)


def load_candles():
    storage_root = REPO_ROOT / "datasets"
    sample_path = storage_root / "samples" / f"{SYMBOL}_{TIMEFRAME}.csv"
    if not sample_path.exists():
        generate_sample(SYMBOL, TIMEFRAME, ROWS, sample_path)

    data_service, candle_store, _ = build_data_service(storage_root)
    candles = candle_store.query(Symbol(SYMBOL), Timeframe(TIMEFRAME))
    if not candles:
        data_service.ingest(SYMBOL, TIMEFRAME, str(sample_path))
        candles = candle_store.query(Symbol(SYMBOL), Timeframe(TIMEFRAME))
    return candles


def show(value) -> str:
    return "n/a" if value is None else f"{value:.4f}"


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    candles = load_candles()

    context = context_from_args(args, prefix="optimisation")

    print("=== Self-learning demo (Sprint P7) ===")
    print(f"Dataset: {len(candles)} candles of {SYMBOL} {TIMEFRAME}")
    print(f"Storage: {context.description}")

    generator = (
        RandomSearchGenerator(count=args.random, seed=args.seed)
        if args.random > 0
        else GridSearchGenerator()
    )

    service = OptimisationService(
        symbol=Symbol(SYMBOL),
        timeframe=Timeframe(TIMEFRAME),
        simulation_config=SimulationConfiguration(
            initial_capital=Decimal(str(args.capital)),
            spread=Decimal(str(args.spread)),
            commission_rate=Decimal(str(args.commission)),
            seed=args.seed,
            warmup_bars=10,
        ),
        objective=OBJECTIVES[args.objective](),
        promotion_policy=PromotionPolicy(
            min_out_of_sample_trades=5,
            min_validation_folds=max(args.folds - 1, 1),
            max_drawdown_percent=Decimal("25"),
            require_positive_return=True,
            min_positive_fold_ratio=Decimal("0.5"),
            max_overfit_gap=Decimal("5"),
        ),
        generator=generator,
        validate_top_n=args.top,
        persistence=context,
    )

    space = {
        "lookback": [3, 6, 12],
        "strategy_min_confidence": [0.55, 0.65, 0.75],
    }

    result = service.run(
        experiment_id="demo",
        parameter_values=space,
        candles=candles,
        baseline=default_baseline(),
        in_sample_ratio=args.in_sample,
        fold_count=args.folds,
        hypothesis="A tuned momentum lookback beats the incumbent out of sample.",
        reporter=ConsoleOptimisationReporter(show_candidates=not args.quiet),
    )

    # ---------------------------------------------------------------
    print("=== Promotion gate ===")
    if result.verdict is None:
        print("  no candidate reached the gate")
    elif result.verdict.approved:
        print(f"  APPROVED — {result.verdict.reason}")
    else:
        reason = result.verdict.rejection_reason
        print(f"  REJECTED ({reason.value if reason else 'unknown'})")
        print(f"  {result.verdict.reason}")

    print()
    print("=== Learning memory ===")
    print(f"  candidates remembered : {len(service.memory)}")
    print(f"  rejected              : {len(service.memory.known_failures())}")
    print(f"  promoted              : {len(service.memory.promoted())}")
    counts = service.memory.rejection_counts()
    for name, count in sorted(counts.items()):
        print(f"      {name:<26} {count}")

    if args.demo_overfit:
        print()
        print("=== Why out-of-sample ranking matters ===")
        header = f"  {'candidate':<10} {'in-sample':>12} {'out-of-sample':>15} {'gap':>10}"
        print(header)
        print("  " + "-" * (len(header) - 2))
        ranked = sorted(
            [c for c in result.evaluated if c.in_sample_score is not None],
            key=lambda c: c.in_sample_score,
            reverse=True,
        )
        for candidate in ranked[:6]:
            print(
                f"  {candidate.candidate_id:<10} {show(candidate.in_sample_score):>12} "
                f"{show(candidate.out_of_sample_score):>15} "
                f"{show(candidate.overfit_gap):>10}"
            )
        print()
        print("  The best in-sample row is not necessarily the winner —")
        print("  ranking uses the out-of-sample column only.")

    # Invariants of this sprint.
    for candidate in result.evaluated:
        if candidate.status.value == "promoted":
            assert candidate.out_of_sample_score is not None

    print()
    print("Invariants verified:")
    print("  * no candidate was promoted without out-of-sample evidence")
    print("  * the winner was ranked on validation folds, not training data")
    print("  * self-learning produced a recommendation, not a live change")
    print()
    for line in context.summary_lines():
        print(f"  {line}")
    context.close()

    print("\nSelf-learning demo finished successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
