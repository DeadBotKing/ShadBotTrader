"""Persistence demo (Sprint P8) — Phase 20.

Runs two separate "processes" against one database to show that state
survives a restart:

    session 1 : open a position, then stop
    session 2 : reopen the database and see the position, cash and audit
                trail exactly as they were

    python scripts/run_persistence.py
    python scripts/run_persistence.py --db mystate.db --keep
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ShadBotTrader.application.services.execution_service import (  # noqa: E402
    ExecutionService,
)
from ShadBotTrader.application.services.trading_decision_service import (  # noqa: E402
    TradingDecisionService,
)
from ShadBotTrader.domain.execution.market_view import (  # noqa: E402
    ExecutionContext,
    MarketQuote,
)
from ShadBotTrader.domain.market.price import Price  # noqa: E402
from ShadBotTrader.domain.market.symbol import Symbol  # noqa: E402
from ShadBotTrader.domain.market.timeframe import Timeframe  # noqa: E402
from ShadBotTrader.domain.market.timestamp import Timestamp  # noqa: E402
from ShadBotTrader.domain.strategy.risk_policy import RiskPolicy  # noqa: E402
from ShadBotTrader.domain.strategy.strategy_context import (  # noqa: E402
    PortfolioView,
    PredictionView,
    StrategyContext,
)
from ShadBotTrader.infrastructure.execution import (  # noqa: E402
    DefaultIntentResolver,
    SimulatedExecutionVenue,
)
from ShadBotTrader.infrastructure.persistence import (  # noqa: E402
    Database,
    SqliteDecisionJournal,
    SqliteExecutionJournal,
    SqlitePortfolioLedger,
)
from ShadBotTrader.infrastructure.trading import (  # noqa: E402
    AiDirectionalStrategy,
    DefaultIntentFactory,
    DefaultSignalValidator,
    PolicyRiskGate,
    PositionAwareDecisionEngine,
)

START = datetime(2026, 8, 16, 12, 0, tzinfo=timezone.utc)
SYMBOL = Symbol("DEMOXAU")
TIMEFRAME = Timeframe("5M")
SESSION = "demo-session"
CASH = Decimal("100")


def rule(title: str) -> None:
    print()
    print("=" * 70)
    print(f"  {title}")
    print("=" * 70)


def build(database: Database, ledger: SqlitePortfolioLedger):
    trading = TradingDecisionService(
        strategies=[AiDirectionalStrategy(min_confidence=0.55)],
        decision_engine=PositionAwareDecisionEngine(),
        risk_gate=PolicyRiskGate(RiskPolicy()),
        intent_factory=DefaultIntentFactory(base_quantity=Decimal("2")),
        validator=DefaultSignalValidator(max_signal_age_seconds=86400),
        journal=SqliteDecisionJournal(database, session_id=SESSION),
    )
    execution = ExecutionService(
        resolver=DefaultIntentResolver(),
        venue=SimulatedExecutionVenue(commission_rate=Decimal("0.0001")),
        ledger=ledger,
        journal=SqliteExecutionJournal(database, session_id=SESSION),
    )
    return trading, execution


def strategy_context(value: float, confidence: float, quantity: str, minutes: int):
    moment = Timestamp(START + timedelta(minutes=minutes))
    return StrategyContext(
        timestamp=moment,
        symbol=SYMBOL,
        timeframe=TIMEFRAME,
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
            equity=CASH,
            open_position_quantity=Decimal(quantity),
            open_position_count=0 if Decimal(quantity) == 0 else 1,
        ),
    )


def execution_context(position, mid: str, minutes: int) -> ExecutionContext:
    moment = Timestamp(START + timedelta(minutes=minutes))
    return ExecutionContext(
        timestamp=moment,
        quote=MarketQuote.from_mid(SYMBOL, Price(Decimal(mid)), Decimal("4"), moment),
        position=position,
        equity=CASH,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Show that platform state persists.")
    parser.add_argument("--db", default="demo_state.db", help="database file")
    parser.add_argument("--keep", action="store_true", help="do not delete afterwards")
    args = parser.parse_args(argv)

    path = Path(args.db)
    if path.exists():
        path.unlink()

    print("=== Persistence demo (Sprint P8) ===")
    print(f"database: {path}")

    # ================================================== session 1 =========
    rule("SESSION 1 - trade, then 'shut down'")

    database = Database(path)
    print(f"  schema version : {database.schema_version}")
    print(f"  tables         : {len(database.table_names())}")

    ledger = SqlitePortfolioLedger(database, session_id=SESSION, starting_cash=CASH, autoload=False)
    trading, execution = build(database, ledger)

    for index, (value, confidence, held, mid) in enumerate(
        [
            (0.95, 0.90, "0", "2000"),
            (0.55, 0.20, "2", "2010"),  # too weak -> no trade
            (0.92, 0.88, "2", "2020"),  # already long -> hold
        ]
    ):
        outcome = trading.evaluate(strategy_context(value, confidence, held, index * 5))
        label = outcome.decision.decision_type.value if outcome.decision else "-"
        if outcome.intent is not None:
            result = execution.execute(
                outcome.intent,
                execution_context(ledger.position(SYMBOL), mid, index * 5),
            )
            note = "filled" if result.executed else result.rejected_reason[:28]
        else:
            note = outcome.rejected_reason[:40] or "no intent"
        print(f"  bar {index}: decision={label:<6} -> {note}")

    position = ledger.position(SYMBOL)
    print(f"\n  position : {position}")
    print(f"  cash     : {ledger.cash}")
    print(f"  fees     : {ledger.total_fees}")

    database.close()
    del ledger, trading, execution, database
    print("\n  [process ended - every object destroyed]")

    # ================================================== session 2 =========
    rule("SESSION 2 - reopen the database")

    reopened_db = Database(path)
    reopened = SqlitePortfolioLedger(reopened_db, session_id=SESSION, starting_cash=CASH)

    restored = reopened.position(SYMBOL)
    print(f"  position : {restored}")
    print(f"  cash     : {reopened.cash}")
    print(f"  fees     : {reopened.total_fees}")
    print(f"  realised : {reopened.realized_pnl}")

    if restored.is_flat:
        print("\n  ! nothing was restored")
        return 1
    print("\n  [OK] the position came back from disk")

    # -- rebuild check --------------------------------------------------
    rule("Reconstruction check")
    rebuilt = reopened.rebuild_from_fills()
    key = str(SYMBOL)
    print("  Recomputing the position by replaying stored fills:")
    print(f"      stored state : {restored.signed_quantity} @ {restored.average_entry_price}")
    print(
        f"      rebuilt      : {rebuilt[key].signed_quantity} "
        f"@ {rebuilt[key].average_entry_price}"
    )
    assert rebuilt[key].signed_quantity == restored.signed_quantity
    assert rebuilt[key].average_entry_price == restored.average_entry_price
    print("  [OK] the books are a consequence of recorded events, not a memory")

    # -- audit trail ----------------------------------------------------
    rule("Audit trail (from disk)")
    decisions = SqliteDecisionJournal(reopened_db, session_id=SESSION)
    executions = SqliteExecutionJournal(reopened_db, session_id=SESSION)

    print(f"  decisions recorded : {decisions.stored_count()}")
    print(f"  execution attempts : {executions.stored_count()}")
    for row in decisions.stored_rows():
        verdict = "-" if row["approved"] is None else ("pass" if row["approved"] else "block")
        print(
            f"      {row['decision_type']:<6} conf={row['confidence']:.2f} "
            f"risk={verdict:<5} {row['rejection'] or ''}"
        )

    counts = decisions.rejection_counts()
    if counts:
        print("  rejection reasons  :")
        for reason, total in sorted(counts.items()):
            print(f"      {reason:<24} {total}")

    # -- database contents ------------------------------------------------
    rule("Database contents")
    for table, count in sorted(reopened_db.statistics().items()):
        if count:
            print(f"  {table:<24} {count}")

    reopened_db.close()

    if not args.keep:
        path.unlink(missing_ok=True)
        for suffix in ("-wal", "-shm"):
            Path(str(path) + suffix).unlink(missing_ok=True)
        print(f"\n  (removed {path}; use --keep to inspect it)")
    else:
        print(f"\n  database kept at {path}")
        print("  inspect it with:  sqlite3 " + str(path) + " .tables")

    print("\nPersistence demo finished successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
