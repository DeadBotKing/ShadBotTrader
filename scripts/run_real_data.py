"""Guided end-to-end run on REAL broker data (MetaTrader 5).

Walks the whole chain and stops with a clear message at the first step
that is not ready, instead of failing deep inside the pipeline:

    check terminal -> find symbol -> ingest -> backtest -> optimise

    python scripts/run_real_data.py --symbol XAUUSD
    python scripts/run_real_data.py --symbol XAUUSD --bars 20000 --timeframe 15M
    python scripts/run_real_data.py --symbol XAUUSD --skip-optimise

Windows only: the MetaTrader5 package talks to a running MT5 terminal
over local IPC. On Linux/macOS use the CSV path instead.
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

STORAGE_ROOT = REPO_ROOT / "datasets"


def rule(title: str) -> None:
    print()
    print("=" * 72)
    print(f"  {title}")
    print("=" * 72)


def fail(message: str, hint: str = "") -> int:
    print(f"\n  [X] {message}")
    if hint:
        print(f"\n  {hint}")
    return 1


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the full platform on real MetaTrader 5 data.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--symbol", default="XAUUSD", help="broker symbol")
    parser.add_argument("--timeframe", default="5M")
    parser.add_argument("--range-timeframe", default="1H")
    parser.add_argument("--mode", choices=("auto", "dual", "legacy"), default="auto")
    parser.add_argument("--threshold", type=float, default=0.60)
    parser.add_argument("--bars", type=int, default=5000)
    parser.add_argument("--capital", type=float, default=100.0)
    parser.add_argument("--spread", type=float, default=4.0)
    parser.add_argument("--commission", type=float, default=0.0001)
    parser.add_argument("--quantity", type=float, default=0.01)
    parser.add_argument("--folds", type=int, default=3)
    parser.add_argument("--login", type=int, default=None)
    parser.add_argument("--password", default=None)
    parser.add_argument("--server", default=None)
    parser.add_argument("--terminal-path", default=None)
    parser.add_argument(
        "--skip-ingest", action="store_true", help="reuse data already stored locally"
    )
    parser.add_argument("--skip-optimise", action="store_true", help="stop after the backtest")
    parser.add_argument(
        "--auto-symbol",
        action="store_true",
        help="accept the closest broker symbol when the exact name is absent",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    from ShadBotTrader.data_cli import build_service
    from ShadBotTrader.domain.market.symbol import Symbol
    from ShadBotTrader.domain.market.timeframe import Timeframe
    from ShadBotTrader.infrastructure.data import mt5_market_data_provider as mt5mod

    symbol = Symbol(args.symbol)
    timeframe = Timeframe(args.timeframe)

    print("=== ShadBotTrader - real market data run ===")
    print(f"symbol {args.symbol} | timeframe {args.timeframe} | bars {args.bars}")

    # ---------------------------------------------------------- step 1 ---
    if not args.skip_ingest:
        rule("STEP 1/5 - MetaTrader 5 connection")

        if not mt5mod.is_available():
            return fail(
                "The MetaTrader5 package is not installed.",
                "Install it (Windows only):\n"
                "      pip install -r requirements-mt5.txt\n\n"
                "  On Linux/macOS there is no MT5 build. Use the CSV path:\n"
                "      python scripts/run_backtest.py",
            )
        print("  [OK] package installed")

        provider = mt5mod.Mt5MarketDataProvider(
            login=args.login,
            password=args.password,
            server=args.server,
            terminal_path=args.terminal_path,
        )

        try:
            summary = provider.account_summary()
        except Exception as error:
            provider.shutdown()
            return fail(
                f"Cannot reach the terminal: {error}",
                "Open MetaTrader 5, log in, and leave it running.",
            )

        print("  [OK] terminal connected")
        print(f"       account : {summary.get('login')} @ {summary.get('server')}")
        print(f"       balance : {summary.get('balance')} {summary.get('currency')}")

        # ------------------------------------------------------ step 2 ---
        rule("STEP 2/5 - Symbol check")
        from ShadBotTrader.infrastructure.data.mt5_symbol_resolver import resolve

        try:
            everything = provider.available_symbols()
        except Exception as error:
            provider.shutdown()
            return fail(f"Symbol lookup failed: {error}")

        report = resolve(args.symbol, everything)
        best = report.best

        if best is not None and best.is_exact:
            print(f"  [OK] '{args.symbol}' is available")
        elif best is not None and args.auto_symbol:
            # Brokers rename instruments freely; with --auto-symbol the
            # closest match is used, but never silently — it is printed.
            print(f"  [!]  '{args.symbol}' not found; using '{best.name}'")
            print(f"       reason : {best.reason}")
            args.symbol = best.name
        else:
            provider.shutdown()
            hint = "\n  ".join(report.advice())
            if best is not None:
                hint += "\n\n  Or re-run with --auto-symbol to accept it automatically."
            return fail(f"'{args.symbol}' was not found at this broker.", hint)

        # ------------------------------------------------------ step 3 ---
        rule("STEP 3/5 - Ingest real price history")
        try:
            service, _, _ = build_service(STORAGE_ROOT, provider=provider)
            print(f"  fetching {args.bars} bars ...")
            result = service.ingest(args.symbol, args.timeframe, str(args.bars))
        except Exception as error:
            return fail(f"Ingestion failed: {error}")
        finally:
            provider.shutdown()

        print(f"  [OK] ingested as version v{result.version}")
        print(f"       raw rows      : {result.raw_row_count}")
        print(f"       valid candles : {result.candle_count}")
        print(f"       quality score : {result.quality_report.score.overall}")
        print(f"       quarantined   : {result.quarantined}")
        for issue in result.quality_report.issues[:5]:
            print(f"         [{issue.severity.value}] {issue.code}: {issue.message}")
        if result.quarantined:
            print("\n  ! The dataset was quarantined - inspect the issues above.")
    else:
        rule("STEP 1-3/5 - Skipped (using stored data)")

    # ---------------------------------------------------------- step 4 ---
    rule("STEP 4/5 - Backtest on real prices")

    symbol = Symbol(args.symbol)
    _, store, _ = build_service(STORAGE_ROOT)
    candles = store.query(symbol, timeframe)
    if not candles:
        return fail(
            f"No stored candles for {args.symbol} {args.timeframe}.",
            "Run without --skip-ingest first.",
        )
    print(f"  {len(candles)} candles available")
    print(f"       first : {candles[0].open_time}  close {candles[0].close}")
    print(f"       last  : {candles[-1].open_time}  close {candles[-1].close}")

    from ShadBotTrader.application.services.backtest_service import BacktestService
    from ShadBotTrader.application.services.dual_model_backtest_service import (
        DualModelBacktestService,
    )
    from ShadBotTrader.domain.simulation.session import SimulationConfiguration
    from ShadBotTrader.domain.simulation.simulation_types import EntryTiming, SameBarPolicy
    from ShadBotTrader.infrastructure.simulation import (
        ConsoleSimulationReporter,
        MomentumPredictionSource,
    )

    simulation_config = SimulationConfiguration(
        initial_capital=Decimal(str(args.capital)),
        spread=Decimal(str(args.spread)),
        commission_rate=Decimal(str(args.commission)),
        warmup_bars=0,
        entry_timing=EntryTiming.NEXT_OPEN,
        same_bar_policy=SameBarPolicy.STOP_FIRST,
    )
    mode = args.mode
    range_candles = store.query(Symbol(args.symbol), Timeframe(args.range_timeframe))
    if mode != "legacy" and range_candles:
        try:
            dual = DualModelBacktestService.from_storage(
                storage_root=STORAGE_ROOT,
                symbol=args.symbol,
                min_signal_confidence=args.threshold,
                configuration=simulation_config,
                base_quantity=Decimal(str(args.quantity)),
            )
            result = dual.run(
                f"real-dual-{args.symbol}-{args.timeframe}",
                candles,
                range_candles,
                reporter=ConsoleSimulationReporter(),
            )
            print("  engine         : dual model (signal -> range -> fixed TP/SL)")
            print(f"  signal window  : {dual.signal_window_size}")
            print(f"  range window   : {dual.range_window_size}")
            print(f"  threshold      : {dual.min_signal_confidence:.1%}")
            print(f"  bars processed : {result.bars_processed}")
            print(f"  fills          : {result.fills}")
            print(f"  take profits   : {result.bracket_exit_counts['take_profit']}")
            print(f"  stop losses    : {result.bracket_exit_counts['stop_loss']}")
        except Exception as error:
            if mode == "dual":
                return fail(f"Dual-model backtest failed: {error}")
            print(f"  dual mode unavailable ({error}); using legacy baseline")
            mode = "legacy"
    elif mode == "dual":
        return fail(
            f"No stored {args.symbol} {args.range_timeframe} candles or saved dual models.",
            "Fetch both 5M and 1H datasets, then train/save both models first.",
        )

    if mode == "legacy":
        simulation_config = SimulationConfiguration(
            initial_capital=Decimal(str(args.capital)),
            spread=Decimal(str(args.spread)),
            commission_rate=Decimal(str(args.commission)),
            warmup_bars=20,
        )
        backtest = BacktestService(
            configuration=simulation_config,
            base_quantity=Decimal(str(args.quantity)),
        )
        result = backtest.run(
            f"real-{args.symbol}-{args.timeframe}",
            Symbol(args.symbol),
            timeframe,
            candles,
            prediction_source=MomentumPredictionSource(lookback=6),
            reporter=ConsoleSimulationReporter(),
        )
        print("  engine         : legacy momentum baseline")
        print(f"  bars processed : {result.bars_processed}")
        print(f"  fills          : {result.fills}")

    # ---------------------------------------------------------- step 5 ---
    if args.skip_optimise:
        rule("STEP 5/5 - Skipped")
    else:
        rule("STEP 5/5 - Walk-forward optimisation")
        print("  Searching parameters on the training window, then validating")
        print("  on folds the search never saw. This takes a minute.\n")

        from ShadBotTrader.application.services.optimisation_service import (
            OptimisationService,
            default_baseline,
        )
        from ShadBotTrader.domain.learning.promotion import PromotionPolicy
        from ShadBotTrader.infrastructure.learning import ConsoleOptimisationReporter

        optimiser = OptimisationService(
            symbol=symbol,
            timeframe=timeframe,
            simulation_config=simulation_config,
            promotion_policy=PromotionPolicy(
                min_out_of_sample_trades=10,
                min_validation_folds=max(args.folds - 1, 1),
                max_drawdown_percent=Decimal("25"),
                max_overfit_gap=Decimal("5"),
            ),
        )
        optimisation = optimiser.run(
            experiment_id=f"real-{args.symbol}",
            parameter_values={
                "lookback": [3, 6, 12],
                "strategy_min_confidence": [0.55, 0.65, 0.75],
            },
            candles=candles,
            baseline=default_baseline(),
            fold_count=args.folds,
            reporter=ConsoleOptimisationReporter(show_candidates=False),
        )

        print("=== Promotion gate ===")
        if optimisation.verdict is None:
            print("  no candidate reached the gate")
        elif optimisation.verdict.approved:
            print(f"  APPROVED - {optimisation.verdict.reason}")
            winner = optimisation.winner
            if winner is not None:
                print(f"  configuration: {winner.configuration.signature}")
        else:
            reason = optimisation.verdict.rejection_reason
            print(f"  REJECTED ({reason.value if reason else 'unknown'})")
            print(f"  {optimisation.verdict.reason}")
            print()
            print("  A rejection is a valid outcome. The gate refuses anything")
            print("  that cannot prove itself out of sample - that is the point.")

    # ------------------------------------------------------------------
    rule("Done")
    print("  Inspect the stored data:")
    print("      python scripts/parquet_view.py list")
    print(
        f"      python scripts/parquet_view.py show "
        f"datasets/raw/{args.symbol.upper()}/{args.timeframe.upper()}/v1.parquet"
    )
    print()
    print("  Re-run without re-downloading:")
    print(f"      python scripts/run_real_data.py --symbol {args.symbol} --skip-ingest")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
