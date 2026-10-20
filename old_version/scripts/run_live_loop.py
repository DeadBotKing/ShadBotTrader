"""Phase 31 — the five-minute live decision loop.

    python scripts/run_live_loop.py --demo            # stubbed models
    python scripts/run_live_loop.py --demo --ticks 5
    python scripts/run_live_loop.py --mt5 --interval 300

One tick:

    fetch 1 x 5M + 1 x 1H candle
      -> 800-candle rolling buffers
      -> features -> newest 500 rows -> (500, 123)
      -> range model (1H)  + signal model (5M)
      -> DualModelStrategy -> risk gate -> execution

A tick never raises: a broker hiccup skips a cycle with a reason, it does
not stop the loop.
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

STORAGE_ROOT = REPO_ROOT / "datasets"


def rule(title: str) -> None:
    print()
    print("=" * 76)
    print(f"  {title}")
    print("=" * 76)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Live five-minute decision loop (Phase 31).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--ticks", type=int, default=3, help="cycles to run")
    parser.add_argument("--interval", type=int, default=0, help="seconds between ticks")
    parser.add_argument("--capital", type=float, default=100.0)
    parser.add_argument("--quantity", type=float, default=0.01)
    parser.add_argument("--window", type=int, default=500)
    parser.add_argument("--min-confidence", type=float, default=0.60)
    parser.add_argument("--min-reward-risk", type=float, default=1.2)
    parser.add_argument(
        "--demo",
        action="store_true",
        help="run with stubbed models to exercise the wiring",
    )
    parser.add_argument("--mt5", action="store_true", help="fetch candles from MetaTrader 5")
    parser.add_argument("--storage-root", default=str(STORAGE_ROOT))
    return parser.parse_args(argv)


def build_quote_source(args: argparse.Namespace):
    """A live quote reader when MT5 is reachable, else None.

    Phase 45: the spread used to be hard-coded at 4.00, which on gold at
    4,376 is 0.09% — wider than the 0.08% move the signal model is
    trained to call a BUY. Every such trade was loss-making before it
    started. Real gold spreads float, so they are read from the broker.

    Returning None is fine: the service falls back to a realistic retail
    spread and records that it did so.
    """
    from ShadBotTrader.infrastructure.data import mt5_market_data_provider as mt5mod

    if not mt5mod.is_available():
        return None
    try:
        return mt5mod.Mt5MarketDataProvider()
    except Exception:
        return None


def load_history(args: argparse.Namespace, timeframe: str, wanted: int = 900):
    """Candles to prime the buffer with.

    Phase 35: stored real candles are used when they exist. When they do
    not, ``--demo`` still runs — it exists to exercise the wiring — but
    the substitute candles are built **in memory only** and never
    ingested into the store. The old code wrote them to disk under the
    real symbol, where the next run could not tell them from broker
    history.
    """
    from ShadBotTrader.data_cli import build_service
    from ShadBotTrader.domain.market.symbol import Symbol
    from ShadBotTrader.domain.market.timeframe import Timeframe
    from ShadBotTrader.infrastructure.data.symbol_scope import resolve_stored_symbol

    storage = Path(args.storage_root)
    _, store, _ = build_service(storage)

    resolved = resolve_stored_symbol(store, args.symbol, timeframe)
    if resolved.found:
        candles = store.query(Symbol(resolved.resolved), Timeframe(timeframe))
        if len(candles) >= wanted:
            return candles[-wanted:]
        print(
            f"  [i] {timeframe}: only {len(candles)} stored candles "
            f"(want {wanted}); the buffer will hold what exists."
        )
        if candles:
            return candles

    if not args.demo:
        raise SystemExit(
            f"\n  [X] No stored candles for {args.symbol} {timeframe}.\n"
            f"      Run Data -> Fetch market data with Timeframes = 5M,1H."
        )

    print(f"  [!] {timeframe}: no stored candles — using IN-MEMORY demo candles.")
    print("      They are not written to disk and are not market data.")
    return synthetic_candles(args.symbol, timeframe, wanted)


def synthetic_candles(symbol: str, timeframe: str, count: int):
    """Throwaway candles for --demo. In memory, never persisted."""
    import math
    from datetime import datetime, timedelta, timezone
    from decimal import Decimal

    from ShadBotTrader.domain.market.candle import Candle
    from ShadBotTrader.domain.market.price import Price
    from ShadBotTrader.domain.market.symbol import Symbol
    from ShadBotTrader.domain.market.timeframe import Timeframe
    from ShadBotTrader.domain.market.timestamp import Timestamp

    frame = Timeframe(timeframe)
    step = timedelta(minutes=60 if timeframe.upper() == "1H" else 5)
    start = datetime.now(timezone.utc) - step * count

    candles = []
    for index in range(count):
        base = 2000.0 + 20.0 * math.sin(index / 40.0)
        close = base + 0.5 * math.sin(index / 7.0)
        high = max(base, close) + 1.0
        low = min(base, close) - 1.0
        candles.append(
            Candle(
                symbol=Symbol(symbol),
                timeframe=frame,
                open_time=Timestamp(start + step * index),
                open_price=Price(Decimal(f"{base:.2f}")),
                high=Price(Decimal(f"{high:.2f}")),
                low=Price(Decimal(f"{low:.2f}")),
                close=Price(Decimal(f"{close:.2f}")),
                volume=Decimal("100"),
            )
        )
    return candles


class DemoSignalModel:
    """Stubbed signal model — alternates so both paths are visible."""

    def __init__(self) -> None:
        self.calls = 0

    def forecast(self, artifact, rows, generated_at=""):
        from ShadBotTrader.domain.ai.prediction_target import SignalForecast

        self.calls += 1
        vectors = [(0.05, 0.95), (0.45, 0.55), (0.90, 0.10)]
        return SignalForecast.from_vector(
            vectors[self.calls % len(vectors)],
            horizon=5,
            timeframe="5M",
            generated_at=generated_at,
        )


class DemoRangeModel:
    def forecast(self, artifact, rows, reference_close, generated_at=""):
        from ShadBotTrader.domain.ai.prediction_target import RangeForecast

        return RangeForecast(
            reference_close=reference_close,
            high_offset=0.010,
            low_offset=-0.003,
            horizon=5,
            timeframe="1H",
            generated_at=generated_at,
        )


def build_service(args: argparse.Namespace):
    from ShadBotTrader.application.services.execution_service import ExecutionService
    from ShadBotTrader.application.services.live_decision_service import (
        LiveDecisionService,
    )
    from ShadBotTrader.application.services.trading_decision_service import (
        TradingDecisionService,
    )
    from ShadBotTrader.domain.strategy.risk_policy import RiskPolicy
    from ShadBotTrader.infrastructure.ai.live_matrix import LiveMatrixBuilder
    from ShadBotTrader.infrastructure.data.live_buffer import LiveMarketData
    from ShadBotTrader.infrastructure.execution import (
        DefaultIntentResolver,
        InMemoryPortfolioLedger,
        SimulatedExecutionVenue,
    )
    from ShadBotTrader.infrastructure.feature.calculator_registry import (
        CalculatorRegistry,
    )
    from ShadBotTrader.infrastructure.feature.standard_catalog import (
        standard_feature_set,
    )
    from ShadBotTrader.infrastructure.trading import (
        DefaultIntentFactory,
        DefaultSignalValidator,
        PolicyRiskGate,
        PositionAwareDecisionEngine,
    )
    from ShadBotTrader.infrastructure.trading.dual_model_strategy import (
        DualModelStrategy,
    )

    market = LiveMarketData(timeframes=("5M", "1H"))
    builder = LiveMatrixBuilder(
        args.symbol,
        feature_set=standard_feature_set(),
        resolver=CalculatorRegistry(),
        window_rows=args.window,
    )
    ledger = InMemoryPortfolioLedger(starting_cash=Decimal(str(args.capital)))

    trading = TradingDecisionService(
        strategies=[
            DualModelStrategy(
                min_confidence=args.min_confidence,
                min_reward_risk=args.min_reward_risk,
            )
        ],
        decision_engine=PositionAwareDecisionEngine(),
        risk_gate=PolicyRiskGate(RiskPolicy(max_open_positions=3, min_confidence=0.5)),
        intent_factory=DefaultIntentFactory(base_quantity=Decimal(str(args.quantity))),
        validator=DefaultSignalValidator(max_signal_age_seconds=86400),
    )
    execution = ExecutionService(
        resolver=DefaultIntentResolver(),
        venue=SimulatedExecutionVenue(commission_rate=Decimal("0.0001"), currency="USD"),
        ledger=ledger,
    )

    service = LiveDecisionService(
        symbol=args.symbol,
        market=market,
        matrix_builder=builder,
        trading_service=trading,
        execution_service=execution,
        ledger=ledger,
        range_predictor=DemoRangeModel(),
        signal_predictor=DemoSignalModel(),
        range_artifact=object(),
        signal_artifact=object(),
        quote_source=build_quote_source(args),
    )
    return service, ledger, market


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    print("=== ShadBotTrader — Phase 31 live decision loop ===")
    print(f"symbol {args.symbol} | window {args.window} rows | {args.ticks} tick(s)")

    if not args.demo and not args.mt5:
        print("\n  Choose a data source: --demo (stubbed) or --mt5 (real broker).")
        return 1
    if args.mt5:
        print("\n  MetaTrader 5 mode needs Windows with the terminal running.")
        print("  Verify first:  shadbot-data mt5-check")
        print("  Falling back to stored candles for this run.\n")

    service, ledger, market = build_service(args)

    rule("PRIMING THE BUFFERS")
    history = {}
    for timeframe in ("5M", "1H"):
        candles = load_history(args, timeframe)
        history[timeframe] = candles
        tally = service.prime(timeframe, candles)
        buffer = market.buffer(timeframe)
        print(f"  {timeframe}: {tally} -> holds {buffer.size}/{buffer.capacity}")

    if args.demo:
        print("\n  [i] Using STUBBED models — this exercises the wiring, not")
        print("      model quality. Train real ones with run_dual_models.py.")

    rule("TICKS")
    moment = datetime.now(timezone.utc)
    traded = 0

    for index in range(args.ticks):
        # Simulate the arrival of the next 5M candle.
        source = history["5M"]
        if index < len(source):
            service.ingest("5M", source[-(index + 1)])

        result = service.tick(now=moment + timedelta(minutes=5 * index))
        print(f"\n  tick {index + 1}/{args.ticks}  {result.timestamp}")
        for line in result.summary_lines():
            print(f"  {line}")
        if result.acted:
            traded += 1

        if args.interval and index < args.ticks - 1:
            time.sleep(args.interval)

    from ShadBotTrader.domain.market.symbol import Symbol

    rule("SUMMARY")
    print(f"  ticks run     : {args.ticks}")
    print(f"  trades taken  : {traded}")
    print(f"  position      : {ledger.position(Symbol(args.symbol)).signed_quantity}")
    print(f"  cash          : {ledger.cash.amount}")
    print("\n  In production this runs every 5 minutes. A failed tick is")
    print("  logged and skipped — the loop keeps going.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
