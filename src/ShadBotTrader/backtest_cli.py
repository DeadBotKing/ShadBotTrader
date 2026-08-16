"""Command-line interface for the Simulation Platform (Sprint P6).

python -m ShadBotTrader.backtest_cli run --capital 100 --spread 4
python -m ShadBotTrader.backtest_cli sweep --param spread --values 0,2,4,10
"""

from __future__ import annotations

import argparse
import sys
from decimal import Decimal
from pathlib import Path
from typing import List, Sequence

from ShadBotTrader.application.services.backtest_service import BacktestService
from ShadBotTrader.data_cli import build_service as build_data_service
from ShadBotTrader.data_cli import generate_sample
from ShadBotTrader.domain.market.candle import Candle
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timeframe import Timeframe
from ShadBotTrader.domain.simulation.session import SimulationConfiguration
from ShadBotTrader.domain.strategy.risk_policy import RiskPolicy
from ShadBotTrader.infrastructure.simulation import (
    ConsoleSimulationReporter,
    MomentumPredictionSource,
)

DEFAULT_STORAGE_ROOT = Path.cwd() / "datasets"


def _load_candles(args: argparse.Namespace) -> Sequence[Candle]:
    storage_root = Path(args.storage_root)
    sample_path = storage_root / "samples" / f"{args.symbol}_{args.timeframe}.csv"
    if not sample_path.exists():
        generate_sample(args.symbol, args.timeframe, 400, sample_path)

    data_service, candle_store, _ = build_data_service(storage_root)
    candles = candle_store.query(Symbol(args.symbol), Timeframe(args.timeframe))
    if not candles:
        data_service.ingest(args.symbol, args.timeframe, str(sample_path))
        candles = candle_store.query(Symbol(args.symbol), Timeframe(args.timeframe))
    return candles


def _service(args: argparse.Namespace, **overrides) -> BacktestService:
    spread = overrides.get("spread", args.spread)
    commission = overrides.get("commission", args.commission)
    quantity = overrides.get("quantity", args.quantity)

    return BacktestService(
        configuration=SimulationConfiguration(
            initial_capital=Decimal(str(args.capital)),
            base_currency="USD",
            spread=Decimal(str(spread)),
            slippage_rate=Decimal(str(args.slippage)),
            commission_rate=Decimal(str(commission)),
            seed=args.seed,
            warmup_bars=args.warmup,
        ),
        risk_policy=RiskPolicy(max_open_positions=3, min_confidence=0.5),
        base_quantity=Decimal(str(quantity)),
    )


def cmd_run(args: argparse.Namespace) -> int:
    """Run a single backtest and print the full report."""
    candles = _load_candles(args)
    service = _service(args)
    result = service.run(
        "cli",
        Symbol(args.symbol),
        Timeframe(args.timeframe),
        candles,
        prediction_source=MomentumPredictionSource(lookback=args.lookback),
        reporter=ConsoleSimulationReporter(show_steps=args.steps, step_every=50),
    )
    print(f"  bars processed    : {result.bars_processed}")
    print(f"  intents created   : {result.intents_created}")
    print(f"  fills             : {result.fills}")
    return 0


def cmd_sweep(args: argparse.Namespace) -> int:
    """Re-run the same data across a range of one parameter."""
    candles = _load_candles(args)
    values = [value.strip() for value in args.values.split(",") if value.strip()]
    if not values:
        print("no values to sweep")
        return 1

    header = (
        f"{args.param:>10} {'trades':>7} {'return':>12} {'return %':>10} "
        f"{'maxDD %':>9} {'hit':>7} {'fees':>10}"
    )
    print(f"Sweeping '{args.param}' over {len(candles)} candles\n")
    print(header)
    print("-" * len(header))

    for raw in values:
        service = _service(args, **{args.param: float(raw)})
        result = service.run(
            f"sweep-{args.param}-{raw}",
            Symbol(args.symbol),
            Timeframe(args.timeframe),
            candles,
            prediction_source=MomentumPredictionSource(lookback=args.lookback),
        )
        metrics = result.metrics
        hit = metrics.hit_rate
        print(
            f"{raw:>10} {metrics.trade_count:>7} "
            f"{metrics.total_return:>12.4f} {metrics.total_return_percent:>10.3f} "
            f"{metrics.max_drawdown_percent:>9.3f} "
            f"{(f'{hit:.3f}' if hit is not None else 'n/a'):>7} "
            f"{metrics.total_fees:>10.4f}"
        )
    return 0


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ShadBotTrader Simulation Platform CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    def common(sub: argparse.ArgumentParser) -> None:
        sub.add_argument("--symbol", default="XAUUSD_i")
        sub.add_argument("--timeframe", default="5M")
        sub.add_argument("--storage-root", default=str(DEFAULT_STORAGE_ROOT))
        sub.add_argument("--capital", type=float, default=100.0)
        sub.add_argument("--spread", type=float, default=4.0)
        sub.add_argument("--slippage", type=float, default=0.0002)
        sub.add_argument("--commission", type=float, default=0.0001)
        sub.add_argument("--quantity", type=float, default=0.01)
        sub.add_argument("--warmup", type=int, default=10)
        sub.add_argument("--lookback", type=int, default=6)
        sub.add_argument("--seed", type=int, default=42)

    run = subparsers.add_parser("run", help="run one backtest")
    common(run)
    run.add_argument("--steps", action="store_true", help="print per-bar progress")
    run.set_defaults(func=cmd_run)

    sweep = subparsers.add_parser("sweep", help="sweep one parameter")
    common(sweep)
    sweep.add_argument(
        "--param",
        choices=("spread", "commission", "quantity"),
        default="spread",
    )
    sweep.add_argument("--values", default="0,2,4,10")
    sweep.set_defaults(func=cmd_sweep)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
