"""Dashboard demo (Sprint P9) — Phase 19.

Generates some state, then serves a read-only dashboard over it.

    python scripts/run_dashboard.py                 # seed + serve
    python scripts/run_dashboard.py --port 9000
    python scripts/run_dashboard.py --no-seed       # use an existing db
    python scripts/run_dashboard.py --export out.html   # write a file instead
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

from ShadBotTrader.presentation.gateway.dashboard_gateway import (  # noqa: E402
    DashboardGateway,
)
from ShadBotTrader.presentation.web.renderer import render_dashboard  # noqa: E402
from ShadBotTrader.presentation.web.server import serve  # noqa: E402


def seed(database_path: Path) -> None:
    """Produce a session with trades, refusals and learning history."""
    from datetime import datetime, timedelta, timezone

    from ShadBotTrader.application.services.execution_service import ExecutionService
    from ShadBotTrader.application.services.optimisation_service import (
        OptimisationService,
    )
    from ShadBotTrader.application.services.trading_decision_service import (
        TradingDecisionService,
    )
    from ShadBotTrader.domain.execution.market_view import ExecutionContext, MarketQuote
    from ShadBotTrader.domain.market.price import Price
    from ShadBotTrader.domain.market.symbol import Symbol
    from ShadBotTrader.domain.market.timeframe import Timeframe
    from ShadBotTrader.domain.market.timestamp import Timestamp
    from ShadBotTrader.domain.simulation.session import SimulationConfiguration
    from ShadBotTrader.domain.strategy.risk_policy import RiskPolicy
    from ShadBotTrader.domain.strategy.strategy_context import (
        PortfolioView,
        PredictionView,
        StrategyContext,
    )
    from ShadBotTrader.infrastructure.execution import (
        DefaultIntentResolver,
        SimulatedExecutionVenue,
    )
    from ShadBotTrader.infrastructure.persistence import (
        Database,
        SqliteDecisionJournal,
        SqliteExecutionJournal,
        SqliteLearningMemory,
        SqlitePortfolioLedger,
    )
    from ShadBotTrader.infrastructure.trading import (
        AiDirectionalStrategy,
        DefaultIntentFactory,
        DefaultSignalValidator,
        PolicyRiskGate,
        PositionAwareDecisionEngine,
    )

    start = datetime(2026, 8, 16, 12, 0, tzinfo=timezone.utc)
    symbol = Symbol("XAUUSD_i")
    timeframe = Timeframe("5M")
    session = "demo"

    database = Database(database_path)
    ledger = SqlitePortfolioLedger(
        database, session_id=session, starting_cash=Decimal("100"), autoload=False
    )
    trading = TradingDecisionService(
        strategies=[AiDirectionalStrategy(min_confidence=0.55)],
        decision_engine=PositionAwareDecisionEngine(),
        risk_gate=PolicyRiskGate(RiskPolicy(max_open_positions=2, min_confidence=0.5)),
        intent_factory=DefaultIntentFactory(base_quantity=Decimal("2")),
        validator=DefaultSignalValidator(max_signal_age_seconds=86400),
        journal=SqliteDecisionJournal(database, session_id=session),
    )
    execution = ExecutionService(
        resolver=DefaultIntentResolver(),
        venue=SimulatedExecutionVenue(commission_rate=Decimal("0.0001")),
        ledger=ledger,
        journal=SqliteExecutionJournal(database, session_id=session),
    )

    # a path with an entry, a hold, a weak signal and a profitable exit
    path = [
        (0.95, 0.90, "2000"),
        (0.55, 0.20, "2010"),
        (0.92, 0.88, "2030"),
        (0.03, 0.94, "2060"),
    ]
    for index, (value, confidence, mid) in enumerate(path):
        moment = Timestamp(start + timedelta(minutes=index * 5))
        position = ledger.position(symbol)
        context = StrategyContext(
            timestamp=moment,
            symbol=symbol,
            timeframe=timeframe,
            predictions=[
                PredictionView(
                    model_id="gold_direction",
                    model_version=1,
                    value=value,
                    confidence=confidence,
                    generated_at=moment,
                )
            ],
            portfolio=PortfolioView(
                equity=ledger.cash.amount,
                open_position_quantity=position.signed_quantity,
                open_position_count=0 if position.is_flat else 1,
            ),
        )
        outcome = trading.evaluate(context)
        if outcome.intent is not None:
            execution.execute(
                outcome.intent,
                ExecutionContext(
                    timestamp=moment,
                    quote=MarketQuote.from_mid(symbol, Price(Decimal(mid)), Decimal("4"), moment),
                    position=position,
                    equity=ledger.cash.amount,
                ),
            )

    # a small optimisation so the learning panel has content
    sys.path.insert(0, str(REPO_ROOT))
    from tests.simulation_fixtures import rising  # noqa: E402

    optimiser = OptimisationService(
        symbol=symbol,
        timeframe=timeframe,
        simulation_config=SimulationConfiguration(
            initial_capital=Decimal("100"), spread=Decimal("4"), warmup_bars=5
        ),
    )
    optimiser.memory = SqliteLearningMemory(database)
    optimiser.run(
        "dashboard-demo",
        {"lookback": [3, 6], "strategy_min_confidence": [0.55, 0.7]},
        rising(80),
        fold_count=2,
    )
    database.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Serve the read-only dashboard.")
    parser.add_argument("--db", default="dashboard.db")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--no-seed", action="store_true", help="use the db as-is")
    parser.add_argument("--export", default=None, help="write HTML and exit")
    args = parser.parse_args(argv)

    path = Path(args.db)

    print("=== Dashboard demo (Phase 19) ===")
    if not args.no_seed:
        if path.exists():
            path.unlink()
            for suffix in ("-wal", "-shm"):
                Path(str(path) + suffix).unlink(missing_ok=True)
        print(f"seeding {path} ...")
        seed(path)

    if not path.exists():
        print(f"\nDatabase not found: {path}")
        print("Drop --no-seed to create one.")
        return 1

    gateway = DashboardGateway.open(path)
    view = gateway.dashboard()
    print(f"  {gateway.summary_line()}")
    if view.portfolio is not None:
        print(f"  session   : {view.portfolio.session_id}")
        print(f"  realised  : {view.portfolio.realized_pnl}")
        print(f"  positions : {view.portfolio.open_positions}")
    print(f"  decisions : {len(view.decisions)}")
    print(f"  candidates: {len(view.candidates)}")

    if args.export:
        points = (
            gateway.equity_points(view.portfolio.session_id) if view.portfolio is not None else []
        )
        markup = render_dashboard(view, points)
        out = Path(args.export)
        out.write_text(markup, encoding="utf-8")
        gateway.database.close()
        print(f"\nWrote {out} ({len(markup) / 1024:.1f} KB)")
        print("Open it in a browser — it is fully self-contained.")
        return 0

    gateway.database.close()
    print()
    serve(path, host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    sys.exit(main())
