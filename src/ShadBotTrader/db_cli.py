"""Command-line interface for the persistence layer (Sprint P8).

python -m ShadBotTrader.db_cli init
python -m ShadBotTrader.db_cli status
python -m ShadBotTrader.db_cli sessions
python -m ShadBotTrader.db_cli positions --session live-1
python -m ShadBotTrader.db_cli decisions --session live-1 --limit 20
python -m ShadBotTrader.db_cli candidates
python -m ShadBotTrader.db_cli query "SELECT * FROM portfolio_fill LIMIT 5"
"""

from __future__ import annotations

import argparse
import sys
from typing import List

from ShadBotTrader.infrastructure.persistence import (
    Database,
    SqliteDecisionJournal,
    SqliteExecutionJournal,
    SqliteLearningMemory,
)

DEFAULT_DB = "shadbot.db"


def _database(args: argparse.Namespace) -> Database:
    return Database(args.db)


def cmd_init(args: argparse.Namespace) -> int:
    """Create the database and apply every migration."""
    database = _database(args)
    print(f"Database  : {database.path}")
    print(f"Schema    : v{database.schema_version}")
    print(f"Tables    : {len(database.table_names())}")
    print("\nApplied migrations:")
    for row in database.applied_migrations():
        print(f"  v{row['version']:<3} {row['name']:<20} {row['applied_at']}")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    """Show schema version and row counts."""
    database = _database(args)
    state = database.system_state()

    print(f"Database    : {database.path}")
    if database.path.exists():
        print(f"Size        : {database.path.stat().st_size / 1024:.1f} KB")
    print(f"Schema      : v{database.schema_version}")
    if state is not None:
        print(f"Environment : {state['environment']}")
        print(f"Initialised : {state['initialized_at']}")
        print(f"Updated     : {state['updated_at']}")

    print("\nContents:")
    stats = database.statistics()
    populated = {name: count for name, count in stats.items() if count}
    if not populated:
        print("  (empty)")
    for name, count in sorted(populated.items()):
        print(f"  {name:<26} {count:>8}")
    empty = [name for name, count in stats.items() if not count]
    if empty:
        print(f"\n  empty tables: {', '.join(sorted(empty))}")
    return 0


def cmd_sessions(args: argparse.Namespace) -> int:
    """List every recorded trading session."""
    database = _database(args)
    rows = database.query("""
        SELECT session_id,
               COUNT(*)                      AS decisions,
               SUM(CASE WHEN approved = 1 THEN 1 ELSE 0 END) AS approved,
               MIN(recorded_at)              AS started,
               MAX(recorded_at)              AS ended
        FROM trading_decision
        GROUP BY session_id ORDER BY started
        """)
    if not rows:
        print("No sessions recorded yet.")
        return 0

    header = f"{'session':<24} {'decisions':>10} {'approved':>9}  started"
    print(header)
    print("-" * len(header))
    for row in rows:
        print(
            f"{row['session_id']:<24} {row['decisions']:>10} "
            f"{row['approved'] or 0:>9}  {row['started']}"
        )
    return 0


def cmd_positions(args: argparse.Namespace) -> int:
    """Show stored positions, optionally for one session."""
    database = _database(args)
    if args.session:
        rows = database.query(
            "SELECT * FROM portfolio_position WHERE session_id = ? ORDER BY symbol",
            (args.session,),
        )
    else:
        rows = database.query("SELECT * FROM portfolio_position ORDER BY session_id, symbol")

    if not rows:
        print("No positions stored.")
        return 0

    header = (
        f"{'session':<18} {'symbol':<12} {'qty':>12} {'avg price':>14} "
        f"{'realised':>12} {'fees':>10}"
    )
    print(header)
    print("-" * len(header))
    for row in rows:
        print(
            f"{row['session_id']:<18} {row['symbol']:<12} "
            f"{row['signed_quantity']:>12} {row['average_price'] or '-':>14} "
            f"{row['realized_pnl']:>12} {row['total_fees']:>10}"
        )
    return 0


def cmd_decisions(args: argparse.Namespace) -> int:
    """Show the decision audit trail."""
    database = _database(args)
    journal = SqliteDecisionJournal(database, session_id=args.session or "default")

    rows = (
        journal.stored_rows()
        if args.session
        else [
            dict(row)
            for row in database.query(
                "SELECT * FROM trading_decision ORDER BY id DESC LIMIT ?", (args.limit,)
            )
        ]
    )
    if not rows:
        print("No decisions stored.")
        return 0

    header = f"{'symbol':<12} {'decision':<9} {'conf':>6} {'risk':<7} " f"{'rejection':<24} intent"
    print(header)
    print("-" * len(header))
    for row in rows[: args.limit]:
        approved = row["approved"]
        verdict = "-" if approved is None else ("pass" if approved else "BLOCK")
        print(
            f"{row['symbol']:<12} {row['decision_type']:<9} "
            f"{row['confidence']:>6.2f} {verdict:<7} "
            f"{row['rejection'] or '':<24} {row['intent_id'] or '-'}"
        )

    counts = journal.rejection_counts() if args.session else {}
    if counts:
        print("\nRejection reasons:")
        for reason, total in sorted(counts.items(), key=lambda item: -item[1]):
            print(f"  {reason:<26} {total}")
    return 0


def cmd_executions(args: argparse.Namespace) -> int:
    """Show execution attempts."""
    database = _database(args)
    journal = SqliteExecutionJournal(database, session_id=args.session or "default")
    rows = (
        journal.stored_rows()
        if args.session
        else [
            dict(row)
            for row in database.query(
                "SELECT * FROM execution_attempt ORDER BY id DESC LIMIT ?", (args.limit,)
            )
        ]
    )
    if not rows:
        print("No execution attempts stored.")
        return 0

    header = f"{'symbol':<12} {'side':<5} {'status':<18} {'filled':>10} {'avg price':>14}"
    print(header)
    print("-" * len(header))
    for row in rows[: args.limit]:
        print(
            f"{row['symbol']:<12} {row['side']:<5} "
            f"{row['status'] or row['rejection'] or '-':<18} "
            f"{row['filled_qty'] or '-':>10} {row['avg_price'] or '-':>14}"
        )
    return 0


def cmd_candidates(args: argparse.Namespace) -> int:
    """Show remembered optimisation candidates."""
    database = _database(args)
    memory = SqliteLearningMemory(database)
    candidates = memory.all_candidates()
    if not candidates:
        print("No candidates remembered yet.")
        return 0

    header = (
        f"{'status':<11} {'in-sample':>12} {'out-of-sample':>14} " f"{'gap':>10}  configuration"
    )
    print(f"{len(candidates)} candidate(s) remembered\n")
    print(header)
    print("-" * len(header))

    def show(value) -> str:
        return "n/a" if value is None else f"{value:.4f}"

    for candidate in candidates[: args.limit]:
        print(
            f"{candidate.status.value:<11} {show(candidate.in_sample_score):>12} "
            f"{show(candidate.out_of_sample_score):>14} "
            f"{show(candidate.overfit_gap):>10}  "
            f"{candidate.configuration.signature}"
        )

    counts = memory.rejection_counts()
    if counts:
        print("\nRejection reasons:")
        for reason, total in sorted(counts.items(), key=lambda item: -item[1]):
            print(f"  {reason:<26} {total}")

    best = memory.best_recorded()
    if best is not None:
        print(f"\nBest out-of-sample: {best.configuration.signature}")
    return 0


def cmd_query(args: argparse.Namespace) -> int:
    """Run a read-only SQL query."""
    statement = args.sql.strip()
    if not statement.lower().startswith("select"):
        print("Only SELECT statements are allowed here.")
        print("Schema changes must go through a migration (Phase 20 rule).")
        return 1

    database = _database(args)
    try:
        rows = database.query(statement)
    except Exception as error:
        print(f"Query failed: {error}")
        return 1

    if not rows:
        print("(no rows)")
        return 0

    columns = list(rows[0].keys())
    widths = {
        name: max(len(name), max(len(str(row[name])) for row in rows[: args.limit]))
        for name in columns
    }
    print("  ".join(name.ljust(widths[name]) for name in columns))
    print("  ".join("-" * widths[name] for name in columns))
    for row in rows[: args.limit]:
        print("  ".join(str(row[name]).ljust(widths[name]) for name in columns))
    if len(rows) > args.limit:
        print(f"\n({args.limit} of {len(rows)} rows - use --limit)")
    return 0


def cmd_vacuum(args: argparse.Namespace) -> int:
    """Compact the database file."""
    database = _database(args)
    before = database.path.stat().st_size if database.path.exists() else 0
    database.connection.execute("VACUUM")
    after = database.path.stat().st_size if database.path.exists() else 0
    print(f"Vacuumed {database.path}")
    print(f"  {before / 1024:.1f} KB -> {after / 1024:.1f} KB")
    return 0


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ShadBotTrader database CLI")
    parser.add_argument("--db", default=DEFAULT_DB, help="database file")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init", help="create/migrate the database")
    init.set_defaults(func=cmd_init)

    status = subparsers.add_parser("status", help="schema version and row counts")
    status.set_defaults(func=cmd_status)

    sessions = subparsers.add_parser("sessions", help="list trading sessions")
    sessions.set_defaults(func=cmd_sessions)

    positions = subparsers.add_parser("positions", help="show stored positions")
    positions.add_argument("--session", default=None)
    positions.set_defaults(func=cmd_positions)

    decisions = subparsers.add_parser("decisions", help="decision audit trail")
    decisions.add_argument("--session", default=None)
    decisions.add_argument("--limit", type=int, default=30)
    decisions.set_defaults(func=cmd_decisions)

    executions = subparsers.add_parser("executions", help="execution attempts")
    executions.add_argument("--session", default=None)
    executions.add_argument("--limit", type=int, default=30)
    executions.set_defaults(func=cmd_executions)

    candidates = subparsers.add_parser("candidates", help="remembered candidates")
    candidates.add_argument("--limit", type=int, default=30)
    candidates.set_defaults(func=cmd_candidates)

    query = subparsers.add_parser("query", help="run a read-only SELECT")
    query.add_argument("sql")
    query.add_argument("--limit", type=int, default=30)
    query.set_defaults(func=cmd_query)

    vacuum = subparsers.add_parser("vacuum", help="compact the database file")
    vacuum.set_defaults(func=cmd_vacuum)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
