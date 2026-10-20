"""Application gateway for the GUI (Phase 19, sections 2, 5, 10).

This is the **only** door between the presentation layer and the rest of
the platform. Views and ViewModels talk to this class; they never reach
a repository, a database or a domain object directly.

The gateway is deliberately **read-only**. Phase 19 §4 forbids the GUI
from executing orders, training models or modifying domain objects, and
the cheapest way to guarantee that is to expose no method that can.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional

from ShadBotTrader.domain.learning.objective import is_penalty
from ShadBotTrader.infrastructure.persistence.database import Database
from ShadBotTrader.infrastructure.persistence.sqlite_journals import (
    SqliteDecisionJournal,
    SqliteExecutionJournal,
)
from ShadBotTrader.infrastructure.persistence.sqlite_learning import SqliteLearningMemory
from ShadBotTrader.presentation.viewmodels.models import (
    CandidateView,
    CashPoint,
    DashboardView,
    DecisionView,
    ExecutionView,
    PortfolioView,
    PositionView,
    SessionView,
    SystemView,
    money,
    percent,
    ratio,
    signed,
    tone,
)

_STATUS_TONES = {
    "promoted": "positive",
    "validated": "positive",
    "filled": "positive",
    "partially_filled": "warning",
    "rejected": "negative",
    "proposed": "neutral",
    "evaluated": "neutral",
    "rolled_back": "warning",
}


class DashboardGateway:
    """Read-only access to stored platform state, shaped for the UI."""

    def __init__(self, database: Database) -> None:
        self._database = database

    @classmethod
    def open(cls, path: str | Path = "shadbot.db") -> "DashboardGateway":
        """Open (and migrate) a database at ``path``."""
        return cls(Database(path))

    @property
    def database(self) -> Database:
        return self._database

    # ------------------------------------------------------------- system --
    def system(self) -> SystemView:
        state = self._database.system_state()
        return SystemView(
            database_path=str(self._database.path),
            schema_version=self._database.schema_version,
            environment=str(state["environment"]) if state else "unknown",
            initialized_at=str(state["initialized_at"]) if state else "—",
            updated_at=str(state["updated_at"]) if state else "—",
            table_counts=self._database.statistics(),
        )

    # ----------------------------------------------------------- sessions --
    def sessions(self) -> List[SessionView]:
        rows = self._database.query("""
            SELECT session_id,
                   COUNT(*) AS decisions,
                   SUM(CASE WHEN approved = 1 THEN 1 ELSE 0 END) AS approved,
                   MIN(recorded_at) AS started,
                   MAX(recorded_at) AS ended
            FROM trading_decision
            GROUP BY session_id
            ORDER BY started DESC
            """)
        return [
            SessionView(
                session_id=str(row["session_id"]),
                decisions=int(row["decisions"]),
                approved=int(row["approved"] or 0),
                started=_short_time(row["started"]),
                ended=_short_time(row["ended"]),
            )
            for row in rows
        ]

    def default_session(self) -> Optional[str]:
        """The most recently active session, if any."""
        row = self._database.query_one(
            "SELECT session_id FROM trading_decision "
            "GROUP BY session_id ORDER BY MAX(recorded_at) DESC LIMIT 1"
        )
        if row is not None:
            return str(row["session_id"])
        row = self._database.query_one("SELECT session_id FROM portfolio_position LIMIT 1")
        return str(row["session_id"]) if row is not None else None

    # ---------------------------------------------------------- portfolio --
    def portfolio(self, session_id: str) -> PortfolioView:
        rows = self._database.query(
            "SELECT * FROM portfolio_position WHERE session_id = ? ORDER BY symbol",
            (session_id,),
        )

        positions: List[PositionView] = []
        realized_total = Decimal("0")
        fees_total = Decimal("0")
        currency = "USD"

        for row in rows:
            quantity = Decimal(str(row["signed_quantity"]))
            realized = Decimal(str(row["realized_pnl"]))
            fees = Decimal(str(row["total_fees"]))
            currency = str(row["currency"])
            realized_total += realized
            fees_total += fees

            positions.append(
                PositionView(
                    symbol=str(row["symbol"]),
                    side=_side_of(quantity),
                    quantity=money(abs(quantity), 4),
                    average_price=money(row["average_price"], 5) if row["average_price"] else "—",
                    realized_pnl=signed(realized),
                    realized_tone=tone(realized),
                    fees=money(fees, 4),
                    currency=currency,
                    is_flat=quantity == 0,
                )
            )

        cash = self._cash_for(session_id, currency)
        net = realized_total - fees_total

        return PortfolioView(
            session_id=session_id,
            cash=money(cash),
            realized_pnl=signed(realized_total),
            realized_tone=tone(realized_total),
            total_fees=money(fees_total, 4),
            net_realized=signed(net),
            net_tone=tone(net),
            currency=currency,
            open_positions=sum(1 for item in positions if not item.is_flat),
            positions=positions,
        )

    def _cash_for(self, session_id: str, currency: str) -> Decimal:
        """Cash implied by the recorded transactions.

        The starting balance is not stored on its own, so this reports the
        net movement — which is what the UI labels it.
        """
        rows = self._database.query(
            "SELECT amount FROM portfolio_transaction WHERE session_id = ?",
            (session_id,),
        )
        total = Decimal("0")
        for row in rows:
            total += Decimal(str(row["amount"]))
        return total

    # ----------------------------------------------------------- journals --
    def decisions(self, session_id: str, limit: int = 50) -> List[DecisionView]:
        rows = self._database.query(
            "SELECT * FROM trading_decision WHERE session_id = ? " "ORDER BY id DESC LIMIT ?",
            (session_id, limit),
        )
        views: List[DecisionView] = []
        for row in rows:
            approved = row["approved"]
            if approved is None:
                verdict, verdict_tone = "—", "neutral"
            elif approved:
                verdict, verdict_tone = "pass", "positive"
            else:
                verdict, verdict_tone = "blocked", "negative"

            views.append(
                DecisionView(
                    symbol=str(row["symbol"]),
                    decision_type=str(row["decision_type"]),
                    confidence=ratio(row["confidence"], 3),
                    risk_verdict=verdict,
                    risk_tone=verdict_tone,
                    rejection=str(row["rejection"] or "—"),
                    intent_id=_short_id(row["intent_id"]),
                    recorded_at=_short_time(row["recorded_at"]),
                )
            )
        return views

    def executions(self, session_id: str, limit: int = 50) -> List[ExecutionView]:
        rows = self._database.query(
            "SELECT * FROM execution_attempt WHERE session_id = ? " "ORDER BY id DESC LIMIT ?",
            (session_id, limit),
        )
        views: List[ExecutionView] = []
        for row in rows:
            status = str(row["status"] or row["rejection"] or "—")
            views.append(
                ExecutionView(
                    symbol=str(row["symbol"]),
                    side=str(row["side"]),
                    status=status,
                    status_tone=_STATUS_TONES.get(status, "neutral"),
                    filled_quantity=str(row["filled_qty"] or "—"),
                    average_price=money(row["avg_price"], 5) if row["avg_price"] else "—",
                    rejection=str(row["rejection"] or "—"),
                    recorded_at=_short_time(row["recorded_at"]),
                )
            )
        return views

    def rejection_counts(self, session_id: str) -> Dict[str, int]:
        journal = SqliteDecisionJournal(self._database, session_id=session_id)
        counts = dict(journal.rejection_counts())
        execution_journal = SqliteExecutionJournal(self._database, session_id=session_id)
        for reason, total in execution_journal.rejection_counts().items():
            counts[reason] = counts.get(reason, 0) + total
        return counts

    # ----------------------------------------------------------- learning --
    def candidates(self, limit: int = 50) -> List[CandidateView]:
        memory = SqliteLearningMemory(self._database)
        views: List[CandidateView] = []
        for candidate in memory.all_candidates()[:limit]:
            status = candidate.status.value
            views.append(
                CandidateView(
                    candidate_id=candidate.candidate_id,
                    configuration=candidate.configuration.signature,
                    status=status,
                    status_tone=_STATUS_TONES.get(status, "neutral"),
                    in_sample=_score(candidate.in_sample_score),
                    out_of_sample=_score(candidate.out_of_sample_score),
                    overfit_gap=ratio(candidate.overfit_gap),
                    rejection=(
                        candidate.rejection_reason.value
                        if candidate.rejection_reason is not None
                        else "—"
                    ),
                )
            )
        return views

    # ---------------------------------------------------------- dashboard --
    def dashboard(self, session_id: Optional[str] = None, limit: int = 25) -> DashboardView:
        """Assemble every panel of the dashboard in one call."""
        target = session_id or self.default_session()

        return DashboardView(
            generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            system=self.system(),
            sessions=self.sessions(),
            portfolio=self.portfolio(target) if target else None,
            decisions=self.decisions(target, limit) if target else [],
            executions=self.executions(target, limit) if target else [],
            candidates=self.candidates(limit),
            rejection_counts=self.rejection_counts(target) if target else {},
        )

    # ------------------------------------------------------------- extras --
    def fills(self, session_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        rows = self._database.query(
            "SELECT * FROM portfolio_fill WHERE session_id = ? ORDER BY id LIMIT ?",
            (session_id, limit),
        )
        return [dict(row) for row in rows]

    def equity_points(self, session_id: str) -> List[CashPoint]:
        """A cumulative cash series derived from the stored transactions.

        This is a genuine series computed from recorded events — not a
        placeholder curve. It shows realised cash over time; unrealised
        marks are not stored per-bar, so they are honestly absent.
        """
        rows = self._database.query(
            "SELECT amount, occurred_at FROM portfolio_transaction "
            "WHERE session_id = ? ORDER BY id",
            (session_id,),
        )
        running = Decimal("0")
        series: List[CashPoint] = []
        for row in rows:
            running += Decimal(str(row["amount"]))
            series.append(CashPoint(timestamp=str(row["occurred_at"]), value=float(running)))
        return series

    def summary_line(self) -> str:
        """One-line health summary, used by the CLI."""
        system = self.system()
        return (
            f"schema v{system.schema_version} | "
            f"{len(self.sessions())} session(s) | "
            f"{system.total_rows} rows"
        )


# ---------------------------------------------------------------- helpers ---
def _score(value: Optional[Decimal]) -> str:
    """Format a learning score, hiding the sentinel penalty.

    ``RiskAdjustedObjective`` returns -1,000,000 to mean "this run had
    too little activity to judge". Showing that number to a user implies
    a catastrophic result rather than an absent one.
    """
    if value is None:
        return "n/a"
    if is_penalty(value):
        return "insufficient"
    return ratio(value)


def _side_of(quantity: Decimal) -> str:
    if quantity > 0:
        return "long"
    if quantity < 0:
        return "short"
    return "flat"


def _short_time(value: Any) -> str:
    """Trim an ISO timestamp to minutes for display."""
    if not value:
        return "—"
    text = str(value)
    try:
        return datetime.fromisoformat(text).strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return text[:16]


def _short_id(value: Any) -> str:
    """Shorten a long identifier so a table stays readable."""
    if not value:
        return "—"
    text = str(value)
    return text if len(text) <= 28 else f"{text[:12]}…{text[-12:]}"


__all__ = ["DashboardGateway", "percent"]
