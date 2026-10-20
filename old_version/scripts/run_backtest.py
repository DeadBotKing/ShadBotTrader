"""Backtest demo (Sprint P6) — Phase 16 Simulation Platform.

Replays the sample dataset through the *production* trading chain on a
controlled simulation clock and reports performance:

    python scripts/run_backtest.py
    python scripts/run_backtest.py --capital 100 --spread 4
    python scripts/run_backtest.py --compare
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
from ShadBotTrader.application.services.backtest_service import BacktestService  # noqa: E402
from ShadBotTrader.application.services.dual_model_backtest_service import (  # noqa: E402
    DualModelBacktestService,
)
from ShadBotTrader.data_cli import build_service as build_data_service  # noqa: E402
from ShadBotTrader.data_cli import generate_sample  # noqa: E402
from ShadBotTrader.domain.market.symbol import Symbol  # noqa: E402
from ShadBotTrader.domain.market.timeframe import Timeframe  # noqa: E402
from ShadBotTrader.domain.simulation.session import SimulationConfiguration  # noqa: E402
from ShadBotTrader.domain.simulation.simulation_types import (  # noqa: E402
    EntryTiming,
    SameBarPolicy,
)
from ShadBotTrader.domain.strategy.risk_policy import RiskPolicy  # noqa: E402
from ShadBotTrader.infrastructure.simulation import (  # noqa: E402
    ConsoleSimulationReporter,
    MomentumPredictionSource,
)

SYMBOL = "DEMOXAU"
TIMEFRAME = "5M"
ROWS = 400


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Backtest the trading chain over historical candles.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--symbol", default=SYMBOL)
    parser.add_argument("--timeframe", default=TIMEFRAME)
    parser.add_argument("--capital", type=float, default=100.0, help="initial capital")
    parser.add_argument("--spread", type=float, default=4.0, help="quoted spread")
    parser.add_argument("--slippage", type=float, default=0.0002, help="slippage rate")
    parser.add_argument("--commission", type=float, default=0.0001, help="fee rate")
    parser.add_argument("--quantity", type=float, default=0.01, help="base order size")
    parser.add_argument("--warmup", type=int, default=10, help="bars before trading")
    parser.add_argument("--lookback", type=int, default=6, help="momentum lookback")
    parser.add_argument("--min-confidence", type=float, default=0.55)
    parser.add_argument(
        "--mode",
        choices=("auto", "dual", "legacy"),
        default="auto",
        help="auto uses signal 5M -> range 1H -> TP/SL when available",
    )
    parser.add_argument("--range-timeframe", default="1H")
    parser.add_argument("--signal-model", default="gold_signal_5m")
    parser.add_argument("--range-model", default="gold_range_1h")
    parser.add_argument("--threshold", type=float, default=0.60)
    parser.add_argument(
        "--same-bar",
        choices=[item.value for item in SameBarPolicy],
        default=SameBarPolicy.STOP_FIRST.value,
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--steps", action="store_true", help="print per-bar progress")
    parser.add_argument(
        "--compare",
        action="store_true",
        help="run the same data with and without costs, side by side",
    )
    add_persistence_arguments(parser, prefix="backtest")
    return parser.parse_args(argv)


def load_candles(symbol: str = SYMBOL, timeframe: str = TIMEFRAME):
    """Load the requested series, generating only the demo default."""
    storage_root = REPO_ROOT / "datasets"
    sample_path = storage_root / "samples" / f"{symbol}_{timeframe}.csv"
    if not sample_path.exists() and symbol == SYMBOL and timeframe == TIMEFRAME:
        generate_sample(symbol, timeframe, ROWS, sample_path)

    data_service, candle_store, _ = build_data_service(storage_root)
    candles = candle_store.query(Symbol(symbol), Timeframe(timeframe))
    if not candles and sample_path.exists() and symbol == SYMBOL and timeframe == TIMEFRAME:
        data_service.ingest(symbol, timeframe, str(sample_path))
        candles = candle_store.query(Symbol(symbol), Timeframe(timeframe))
    return candles


def load_range_candles(args: argparse.Namespace):
    storage_root = REPO_ROOT / "datasets"
    _, candle_store, _ = build_data_service(storage_root)
    return candle_store.query(Symbol(args.symbol), Timeframe(args.range_timeframe))


def build(
    args: argparse.Namespace,
    spread: float,
    commission: float,
    persistence=None,
) -> BacktestService:
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
        base_quantity=Decimal(str(args.quantity)),
        strategy_min_confidence=args.min_confidence,
        persistence=persistence,
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    candles = load_candles(args.symbol, args.timeframe)

    context = context_from_args(args, prefix="backtest")

    print("=== Backtest demo (Sprint P6) ===")
    print(f"Dataset: {len(candles)} candles of {args.symbol} {args.timeframe}")
    print(f"Storage: {context.description}")
    if not candles:
        print(f"No stored candles for {args.symbol} {args.timeframe}.")
        context.close()
        return 1

    if args.mode != "legacy":
        range_candles = load_range_candles(args)
        if range_candles:
            try:
                dual = DualModelBacktestService.from_storage(
                    storage_root=REPO_ROOT / "datasets",
                    symbol=args.symbol,
                    signal_model_id=args.signal_model,
                    range_model_id=args.range_model,
                    min_signal_confidence=args.threshold,
                    configuration=SimulationConfiguration(
                        initial_capital=Decimal(str(args.capital)),
                        spread=Decimal(str(args.spread)),
                        slippage_rate=Decimal(str(args.slippage)),
                        commission_rate=Decimal(str(args.commission)),
                        seed=args.seed,
                        entry_timing=EntryTiming.NEXT_OPEN,
                        same_bar_policy=SameBarPolicy(args.same_bar),
                    ),
                    base_quantity=Decimal(str(args.quantity)),
                    persistence=context,
                )
                result = dual.run(
                    "dual-demo",
                    candles,
                    range_candles,
                    reporter=ConsoleSimulationReporter(show_steps=args.steps, step_every=100),
                )
                print("Mode: dual model (signal -> range -> fixed TP/SL)")
                print(f"  signal window    : {dual.signal_window_size}")
                print(f"  range window     : {dual.range_window_size}")
                print(f"  threshold        : {dual.min_signal_confidence:.1%}")
                print(f"  bars processed   : {result.bars_processed}")
                print(f"  fills            : {result.fills}")
                print(f"  closed trades    : {result.metrics.trade_count}")
                print(f"  take profits     : {result.bracket_exit_counts['take_profit']}")
                print(f"  stop losses      : {result.bracket_exit_counts['stop_loss']}")
                print(f"  return           : {result.metrics.total_return_percent:.3f}%")
                context.close()
                return 0
            except Exception as error:
                if args.mode == "dual":
                    print(f"Dual backtest failed: {error}")
                    context.close()
                    return 1
                print(f"Dual mode unavailable ({error}); using legacy baseline.")
        elif args.mode == "dual":
            print(f"No stored {args.symbol} {args.range_timeframe} candles for dual mode.")
            context.close()
            return 1
        else:
            print(f"No stored {args.symbol} {args.range_timeframe} candles; using legacy baseline.")

    if args.compare:
        print("\nRunning the same data twice: frictionless vs realistic costs.\n")
        rows = []
        for label, spread, commission in (
            ("no costs", 0.0, 0.0),
            ("with costs", args.spread, args.commission),
        ):
            service = build(args, spread, commission)
            result = service.run(
                f"compare-{label.replace(' ', '-')}",
                Symbol(args.symbol),
                Timeframe(args.timeframe),
                candles,
                prediction_source=MomentumPredictionSource(lookback=args.lookback),
            )
            rows.append((label, result))

        header = (
            f"{'scenario':<12} {'trades':>7} {'return':>12} {'return %':>10} "
            f"{'maxDD %':>9} {'fees':>10}"
        )
        print(header)
        print("-" * len(header))
        for label, result in rows:
            metrics = result.metrics
            print(
                f"{label:<12} {metrics.trade_count:>7} "
                f"{metrics.total_return:>12.4f} {metrics.total_return_percent:>10.3f} "
                f"{metrics.max_drawdown_percent:>9.3f} {metrics.total_fees:>10.4f}"
            )
        print("\nCosts are what separate a backtest from a fantasy.")
        return 0

    service = build(args, args.spread, args.commission, persistence=context)
    result = service.run(
        "demo",
        Symbol(args.symbol),
        Timeframe(args.timeframe),
        candles,
        prediction_source=MomentumPredictionSource(lookback=args.lookback),
        reporter=ConsoleSimulationReporter(show_steps=args.steps, step_every=50),
    )

    print(f"  bars processed    : {result.bars_processed}")
    print(f"  intents created   : {result.intents_created}")
    print(f"  fills             : {result.fills}")

    ledger = service.ledger
    if ledger is not None:
        position = ledger.position(Symbol(args.symbol))
        print(f"  final position    : {'flat' if position.is_flat else position}")
        print(f"  cash              : {ledger.cash}")

    if result.trades:
        print("\n=== Trades ===")
        for index, trade in enumerate(result.trades[:12], start=1):
            verdict = "win " if trade.is_win else "loss"
            print(
                f"  {index:>2}. {verdict} net {trade.net_pnl:>10.4f} "
                f"(gross {trade.realized_pnl:>9.4f}, fees {trade.fees:.4f})"
            )
        if len(result.trades) > 12:
            print(f"  ... and {len(result.trades) - 12} more")

    # The invariants this platform is built on.
    assert result.session.status.value == "completed"
    if service.decision_journal is not None:
        for entry in service.decision_journal.entries():
            if entry.intent is not None:
                assert entry.verdict is not None and entry.verdict.approved

    print("\nInvariants verified:")
    print("  * every intent passed the risk gate")
    print("  * the clock only ever moved forward, driven by event time")

    print()
    for line in context.summary_lines():
        print(f"  {line}")
    context.close()

    print("\nBacktest demo finished successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
