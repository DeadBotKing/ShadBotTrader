"""Command-line interface for the dashboard (Phase 19).

python -m ShadBotTrader.dashboard_cli serve --db shadbot.db
python -m ShadBotTrader.dashboard_cli export --out dashboard.html
python -m ShadBotTrader.dashboard_cli show
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List

from ShadBotTrader.presentation.gateway.dashboard_gateway import DashboardGateway
from ShadBotTrader.presentation.web.renderer import render_dashboard
from ShadBotTrader.presentation.web.server import serve

DEFAULT_DB = "shadbot.db"


def cmd_serve(args: argparse.Namespace) -> int:
    """Run the read-only dashboard server."""
    if not Path(args.db).exists():
        print(f"Database not found: {args.db}")
        print("Create one first, for example:")
        print("    python scripts/run_persistence.py --keep --db " + args.db)
        return 1
    serve(args.db, host=args.host, port=args.port)
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    """Write the dashboard to a standalone HTML file.

    Everything is inlined, so the file works offline and can be emailed
    or archived as a point-in-time record.
    """
    gateway = DashboardGateway.open(args.db)
    view = gateway.dashboard(args.session)
    points = gateway.equity_points(view.portfolio.session_id) if view.portfolio is not None else []
    markup = render_dashboard(view, points)
    gateway.database.close()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(markup, encoding="utf-8")
    print(f"Wrote {out} ({len(markup) / 1024:.1f} KB)")
    print("Self-contained: no network, scripts or external assets required.")
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    """Print the dashboard contents as text."""
    gateway = DashboardGateway.open(args.db)
    view = gateway.dashboard(args.session)

    print("=== ShadBotTrader dashboard ===")
    print(f"generated {view.generated_at}")
    print(f"database  {view.system.database_path} (schema v{view.system.schema_version})")

    if view.is_empty:
        print("\nNothing recorded yet.")
        gateway.database.close()
        return 0

    portfolio = view.portfolio
    if portfolio is not None:
        print(f"\n--- Portfolio ({portfolio.session_id}) ---")
        print(f"  net cash flow  : {portfolio.cash} {portfolio.currency}")
        print(f"  realised PnL   : {portfolio.realized_pnl}")
        print(f"  fees           : {portfolio.total_fees}")
        print(f"  net realised   : {portfolio.net_realized}")
        print(f"  open positions : {portfolio.open_positions}")
        for position in portfolio.positions:
            print(
                f"      {position.symbol:<12} {position.side:<6} "
                f"{position.quantity:>10} @ {position.average_price:>12} "
                f"realised {position.realized_pnl}"
            )

    if view.decisions:
        print(f"\n--- Decisions (latest {len(view.decisions)}) ---")
        for decision in view.decisions[:10]:
            print(
                f"  {decision.symbol:<12} {decision.decision_type:<7} "
                f"conf={decision.confidence:<7} risk={decision.risk_verdict:<8} "
                f"{decision.rejection}"
            )

    if view.candidates:
        print(f"\n--- Learning memory ({len(view.candidates)}) ---")
        for candidate in view.candidates[:10]:
            print(
                f"  {candidate.status:<11} in={candidate.in_sample:<10} "
                f"out={candidate.out_of_sample:<10} {candidate.configuration}"
            )

    if view.rejection_counts:
        print("\n--- Why trades were refused ---")
        for reason, total in sorted(view.rejection_counts.items(), key=lambda item: -item[1]):
            print(f"  {reason:<26} {total}")

    print("\n--- Sessions ---")
    for entry in view.sessions:
        print(
            f"  {entry.session_id:<20} {entry.decisions:>4} decisions, "
            f"{entry.approved:>3} approved ({entry.approval_rate})"
        )

    gateway.database.close()
    return 0


def cmd_state(args: argparse.Namespace) -> int:
    """Print the dashboard state as JSON."""
    gateway = DashboardGateway.open(args.db)
    view = gateway.dashboard(args.session)
    payload = view.to_dict()
    gateway.database.close()
    print(json.dumps(payload, indent=2, default=str))
    return 0


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ShadBotTrader read-only dashboard (Phase 19)")
    parser.add_argument("--db", default=DEFAULT_DB, help="database file")
    subparsers = parser.add_subparsers(dest="command", required=True)

    serve_parser = subparsers.add_parser("serve", help="run the dashboard server")
    serve_parser.add_argument("--host", default="0.0.0.0")
    serve_parser.add_argument("--port", type=int, default=8080)
    serve_parser.set_defaults(func=cmd_serve)

    export = subparsers.add_parser("export", help="write a standalone HTML file")
    export.add_argument("--out", default="dashboard.html")
    export.add_argument("--session", default=None)
    export.set_defaults(func=cmd_export)

    show = subparsers.add_parser("show", help="print the dashboard as text")
    show.add_argument("--session", default=None)
    show.set_defaults(func=cmd_show)

    state = subparsers.add_parser("state", help="print the dashboard as JSON")
    state.add_argument("--session", default=None)
    state.set_defaults(func=cmd_state)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
