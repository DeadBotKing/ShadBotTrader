"""Backtest replay demo — watch the simulation bar by bar (Phase 16 §23).

Runs the *same* backtest the other scripts run, with recording switched
on, then produces a player you can step through:

    python scripts/run_replay.py                    # writes replay.html
    python scripts/run_replay.py --console          # prints it instead
    python scripts/run_replay.py --console --all-bars --delay 0.05
    python scripts/run_replay.py --spread 0 --capital 1000

Recording is an observer: the numbers are identical to
``scripts/run_backtest.py`` with the same arguments.
"""

from __future__ import annotations

import argparse
import sys
import webbrowser
from decimal import Decimal
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ShadBotTrader.application.services.backtest_service import BacktestService  # noqa: E402
from ShadBotTrader.data_cli import build_service as build_data_service  # noqa: E402
from ShadBotTrader.data_cli import generate_sample  # noqa: E402
from ShadBotTrader.domain.market.symbol import Symbol  # noqa: E402
from ShadBotTrader.domain.market.timeframe import Timeframe  # noqa: E402
from ShadBotTrader.domain.simulation.session import SimulationConfiguration  # noqa: E402
from ShadBotTrader.domain.strategy.risk_policy import RiskPolicy  # noqa: E402
from ShadBotTrader.infrastructure.simulation import (  # noqa: E402
    ConsoleReplayPlayer,
    MomentumPredictionSource,
)
from ShadBotTrader.presentation.web.replay_renderer import render_replay  # noqa: E402

SYMBOL = "XAUUSD_i"
TIMEFRAME = "5M"
ROWS = 400


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Replay a backtest bar by bar.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--symbol", default=SYMBOL)
    parser.add_argument("--timeframe", default=TIMEFRAME)
    parser.add_argument("--capital", type=float, default=100.0)
    parser.add_argument("--spread", type=float, default=4.0)
    parser.add_argument("--slippage", type=float, default=0.0002)
    parser.add_argument("--commission", type=float, default=0.0001)
    parser.add_argument("--quantity", type=float, default=0.01)
    parser.add_argument("--warmup", type=int, default=10)
    parser.add_argument("--lookback", type=int, default=6)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", default="replay.html", help="HTML player to write")
    parser.add_argument("--console", action="store_true", help="print instead of writing HTML")
    parser.add_argument("--all-bars", action="store_true", help="print every bar (--console)")
    parser.add_argument("--every", type=int, default=10, help="print 1 in N quiet bars")
    parser.add_argument("--delay", type=float, default=0.0, help="seconds between bars")
    parser.add_argument("--autoplay", action="store_true", help="start the player immediately")
    parser.add_argument("--open", action="store_true", help="open the player in a browser")
    return parser.parse_args(argv)


def load_candles(args: argparse.Namespace):
    """Reuse the stored dataset, generating the sample only if missing."""
    storage_root = REPO_ROOT / "datasets"
    sample = storage_root / "samples" / f"{args.symbol}_{args.timeframe}.csv"
    if not sample.exists():
        generate_sample(args.symbol, args.timeframe, ROWS, sample)

    service, store, _ = build_data_service(storage_root)
    candles = store.query(Symbol(args.symbol), Timeframe(args.timeframe))
    if not candles:
        service.ingest(args.symbol, args.timeframe, str(sample))
        candles = store.query(Symbol(args.symbol), Timeframe(args.timeframe))
    return candles


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    candles = load_candles(args)

    service = BacktestService(
        configuration=SimulationConfiguration(
            initial_capital=Decimal(str(args.capital)),
            base_currency="USD",
            spread=Decimal(str(args.spread)),
            slippage_rate=Decimal(str(args.slippage)),
            commission_rate=Decimal(str(args.commission)),
            seed=args.seed,
            warmup_bars=args.warmup,
        ),
        risk_policy=RiskPolicy(max_open_positions=3, min_confidence=0.5),
        base_quantity=Decimal(str(args.quantity)),
    )

    result = service.run(
        "replay",
        Symbol(args.symbol),
        Timeframe(args.timeframe),
        candles,
        prediction_source=MomentumPredictionSource(lookback=args.lookback),
        record_replay=True,
    )

    tape = result.tape
    if tape is None:  # pragma: no cover - recording was requested
        print("No replay was recorded.")
        return 1

    if args.console:
        ConsoleReplayPlayer(
            delay=args.delay,
            show_all_bars=args.all_bars,
            every=args.every,
        ).play(tape)
        return 0

    markup = render_replay(tape, result.metrics, autoplay=args.autoplay)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(markup, encoding="utf-8")

    trips = tape.round_trips()
    wins = sum(1 for trip in trips if trip["result"] == "win")
    print(f"Wrote {out} ({len(markup) / 1024:.1f} KB)")
    print(f"  bars recorded : {len(tape.bars)}")
    print(f"  fills         : {len(tape.markers)}")
    print(f"  closed trades : {len(trips)} ({wins} win / {len(trips) - wins} loss)")
    print(
        f"  return        : {result.metrics.total_return:.4f} "
        f"({result.metrics.total_return_percent:.2f}%)"
    )
    print(f"\nOpen it in a browser:  {out.resolve()}")

    if args.open:
        webbrowser.open(out.resolve().as_uri())
    return 0


if __name__ == "__main__":
    sys.exit(main())
