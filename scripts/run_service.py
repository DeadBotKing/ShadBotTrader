"""Phase 24 — run ShadBotTrader continuously as a supervised service.

    python scripts/run_service.py --demo --cycles 3 --interval 2
    python scripts/run_service.py --demo --interval 300        # every 5 min
    python scripts/run_service.py --demo --backup-every 12     # hourly backup

Press Ctrl+C to stop: the runner finishes the cycle in progress, drains,
persists its state and exits cleanly. It never cuts into a tick, because
interrupting a half-executed order is worse than waiting.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
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
        description="Run ShadBotTrader continuously (Phase 24).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--symbol", default="XAUUSD_i")
    parser.add_argument("--interval", type=float, default=300.0, help="seconds per cycle")
    parser.add_argument("--cycles", type=int, default=None, help="stop after N cycles")
    parser.add_argument("--environment", default="development")
    parser.add_argument("--db", default="shadbot.db")
    parser.add_argument("--state", default="runner_state.json")
    parser.add_argument(
        "--backup-every", type=int, default=0, help="back up every N cycles (0 = never)"
    )
    parser.add_argument(
        "--max-failures", type=int, default=5, help="stop after N consecutive failures"
    )
    parser.add_argument("--capital", type=float, default=100.0)
    parser.add_argument("--quantity", type=float, default=0.01)
    parser.add_argument("--demo", action="store_true", help="stubbed models — exercises the wiring")
    parser.add_argument("--storage-root", default=str(STORAGE_ROOT))
    return parser.parse_args(argv)


def build_live_service(args: argparse.Namespace):
    """Wire the live decision loop (reuses the Phase 31 composition)."""
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    from run_live_loop import DemoRangeModel, DemoSignalModel, load_history

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
    ledger = InMemoryPortfolioLedger(starting_cash=Decimal(str(args.capital)))

    trading = TradingDecisionService(
        strategies=[DualModelStrategy(min_confidence=0.6, min_reward_risk=1.2)],
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
        matrix_builder=LiveMatrixBuilder(
            args.symbol,
            feature_set=standard_feature_set(),
            resolver=CalculatorRegistry(),
            window_rows=500,
        ),
        trading_service=trading,
        execution_service=execution,
        ledger=ledger,
        range_predictor=DemoRangeModel(),
        signal_predictor=DemoSignalModel(),
        range_artifact=object(),
        signal_artifact=object(),
    )

    for timeframe in ("5M", "1H"):
        service.prime(timeframe, load_history(args, timeframe))

    return service, ledger


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    from ShadBotTrader import __version__
    from ShadBotTrader.application.services.runner_service import (
        RunnerConfig,
        RunnerService,
    )
    from ShadBotTrader.infrastructure.deployment.backup import BackupService
    from ShadBotTrader.infrastructure.deployment.health_checks import default_monitor

    print("=== ShadBotTrader service runner (Phase 24) ===")
    print(f"version {__version__} | environment {args.environment}")
    print(f"interval {args.interval}s | cycles {args.cycles or 'unlimited'}")

    if not args.demo:
        print("\n  Only --demo is wired for now: a live broker venue is a")
        print("  separate decision with real money attached.")
        return 1

    rule("PRE-FLIGHT")
    monitor = default_monitor(
        version=__version__,
        environment=args.environment,
        database_path=args.db if Path(args.db).exists() else None,
        storage_root=args.storage_root,
    )
    report = monitor.run()
    for line in report.summary_lines():
        print(f"  {line}")
    if not report.is_ready:
        print("\n  [X] Not ready — a critical dependency is unavailable.")
        return 1

    rule("STARTING")
    service, ledger = build_live_service(args)
    print("  live decision loop primed")

    backup = BackupService(args.db) if Path(args.db).exists() else None
    if backup and args.backup_every:
        print(f"  backups every {args.backup_every} cycle(s) -> {backup.backup_root}")

    def on_event(event: str, payload: dict) -> None:
        stamp = datetime.now(timezone.utc).strftime("%H:%M:%S")
        print(f"  [{stamp}] {event}: {payload}")

    runner = RunnerService(
        tick=lambda: service.tick(equity=Decimal(str(args.capital))),
        config=RunnerConfig(
            interval_seconds=args.interval,
            max_cycles=args.cycles,
            max_consecutive_failures=args.max_failures,
            state_path=args.state,
            backup_every=args.backup_every,
        ),
        monitor=monitor,
        backup=backup,
        on_event=on_event,
    )
    runner.install_signal_handlers()

    rule("RUNNING — Ctrl+C to stop gracefully")
    state = runner.run()

    rule("STOPPED")
    print(f"  cycles   : {state.cycles}")
    print(f"  trades   : {state.trades}")
    print(f"  failures : {state.failures}")
    print(f"  reason   : {state.stop_reason or 'completed'}")
    print(f"  shutdown : {' -> '.join(runner.shutdown.steps)}")
    print(f"\n  state saved to {args.state} — a restart resumes from here.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
