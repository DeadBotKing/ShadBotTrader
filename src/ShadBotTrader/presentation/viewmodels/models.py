"""View models — UI-friendly state (Phase 19, sections 9-10).

A ViewModel turns application data into something a view can render:
formatted numbers, currency strings, percentages, status labels and
chart series.

Rules enforced by construction here:

* a ViewModel is a plain, immutable value — no behaviour beyond
  formatting
* it never touches a repository, database, exchange or domain
  infrastructure (§10); the Gateway hands it finished data
* every number is formatted once, in one place, so the whole UI is
  consistent
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Dict, List, Optional


def money(value: Decimal | float | str | None, digits: int = 2) -> str:
    """Format a monetary amount for display."""
    if value is None:
        return "—"
    return f"{Decimal(str(value)):,.{digits}f}"


def signed(value: Decimal | float | str | None, digits: int = 2) -> str:
    """Format a value that can be a gain or a loss, with an explicit sign."""
    if value is None:
        return "—"
    amount = Decimal(str(value))
    return f"{'+' if amount > 0 else ''}{amount:,.{digits}f}"


def percent(value: Decimal | float | str | None, digits: int = 2) -> str:
    if value is None:
        return "—"
    return f"{Decimal(str(value)):,.{digits}f}%"


def ratio(value: Decimal | float | str | None, digits: int = 4) -> str:
    """Format a dimensionless ratio, or the honest 'n/a' when undefined."""
    if value is None:
        return "n/a"
    return f"{Decimal(str(value)):.{digits}f}"


def tone(value: Decimal | float | str | None) -> str:
    """Semantic class for colouring: positive, negative or neutral."""
    if value is None:
        return "neutral"
    amount = Decimal(str(value))
    if amount > 0:
        return "positive"
    if amount < 0:
        return "negative"
    return "neutral"


@dataclass(frozen=True)
class PositionView:
    """One open (or closed) position, ready to render."""

    symbol: str
    side: str
    quantity: str
    average_price: str
    realized_pnl: str
    realized_tone: str
    fees: str
    currency: str
    is_flat: bool

    @property
    def side_tone(self) -> str:
        if self.side == "long":
            return "positive"
        if self.side == "short":
            return "negative"
        return "neutral"


@dataclass(frozen=True)
class PortfolioView:
    """Headline portfolio numbers."""

    session_id: str
    cash: str
    realized_pnl: str
    realized_tone: str
    total_fees: str
    net_realized: str
    net_tone: str
    currency: str
    open_positions: int
    positions: List[PositionView] = field(default_factory=list)

    @property
    def has_positions(self) -> bool:
        return bool(self.positions)


@dataclass(frozen=True)
class DecisionView:
    """One row of the decision audit trail."""

    symbol: str
    decision_type: str
    confidence: str
    risk_verdict: str
    risk_tone: str
    rejection: str
    intent_id: str
    recorded_at: str

    @property
    def produced_intent(self) -> bool:
        return bool(self.intent_id and self.intent_id != "—")


@dataclass(frozen=True)
class ExecutionView:
    """One row of the execution history."""

    symbol: str
    side: str
    status: str
    status_tone: str
    filled_quantity: str
    average_price: str
    rejection: str
    recorded_at: str


@dataclass(frozen=True)
class CandidateView:
    """One remembered optimisation candidate."""

    candidate_id: str
    configuration: str
    status: str
    status_tone: str
    in_sample: str
    out_of_sample: str
    overfit_gap: str
    rejection: str


@dataclass(frozen=True)
class SessionView:
    """Summary of one recorded trading session."""

    session_id: str
    decisions: int
    approved: int
    started: str
    ended: str

    @property
    def approval_rate(self) -> str:
        if not self.decisions:
            return "n/a"
        return f"{self.approved / self.decisions * 100:.0f}%"


@dataclass(frozen=True)
class EquityPointView:
    """One point of an equity curve, for charting."""

    timestamp: str
    equity: float
    drawdown: float


@dataclass(frozen=True)
class CashPoint:
    """One point of the realised cash-flow series."""

    timestamp: str
    value: float


@dataclass(frozen=True)
class ChartSeries:
    """A named series ready for an inline SVG chart."""

    label: str
    points: List[EquityPointView] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return not self.points

    @property
    def minimum(self) -> float:
        return min((point.equity for point in self.points), default=0.0)

    @property
    def maximum(self) -> float:
        return max((point.equity for point in self.points), default=0.0)


@dataclass(frozen=True)
class SystemView:
    """Database and platform health."""

    database_path: str
    schema_version: int
    environment: str
    initialized_at: str
    updated_at: str
    table_counts: Dict[str, int] = field(default_factory=dict)

    @property
    def total_rows(self) -> int:
        return sum(self.table_counts.values())

    @property
    def populated_tables(self) -> Dict[str, int]:
        return {name: count for name, count in self.table_counts.items() if count}


@dataclass(frozen=True)
class DashboardView:
    """Everything the dashboard page needs, assembled once."""

    generated_at: str
    system: SystemView
    sessions: List[SessionView] = field(default_factory=list)
    portfolio: Optional[PortfolioView] = None
    decisions: List[DecisionView] = field(default_factory=list)
    executions: List[ExecutionView] = field(default_factory=list)
    candidates: List[CandidateView] = field(default_factory=list)
    rejection_counts: Dict[str, int] = field(default_factory=dict)

    @property
    def is_empty(self) -> bool:
        """True when nothing at all has been recorded.

        A portfolio with positions counts as content even when no
        decisions were journalled — a ledger can be written to directly,
        and hiding it behind the "nothing yet" placeholder would make
        real stored state invisible.
        """
        has_portfolio = self.portfolio is not None and bool(self.portfolio.positions)
        return not (self.sessions or self.candidates or has_portfolio or self.executions)

    def to_dict(self) -> Dict[str, Any]:
        """A JSON-serialisable snapshot, for the API endpoint."""
        return {
            "generated_at": self.generated_at,
            "system": {
                "database": self.system.database_path,
                "schema_version": self.system.schema_version,
                "environment": self.system.environment,
                "total_rows": self.system.total_rows,
                "tables": self.system.table_counts,
            },
            "sessions": [
                {
                    "session_id": item.session_id,
                    "decisions": item.decisions,
                    "approved": item.approved,
                    "started": item.started,
                }
                for item in self.sessions
            ],
            "portfolio": (
                {
                    "session_id": self.portfolio.session_id,
                    "cash": self.portfolio.cash,
                    "realized_pnl": self.portfolio.realized_pnl,
                    "total_fees": self.portfolio.total_fees,
                    "net_realized": self.portfolio.net_realized,
                    "open_positions": self.portfolio.open_positions,
                    "positions": [
                        {
                            "symbol": position.symbol,
                            "side": position.side,
                            "quantity": position.quantity,
                            "average_price": position.average_price,
                            "realized_pnl": position.realized_pnl,
                        }
                        for position in self.portfolio.positions
                    ],
                }
                if self.portfolio is not None
                else None
            ),
            "decisions": [
                {
                    "symbol": item.symbol,
                    "decision_type": item.decision_type,
                    "confidence": item.confidence,
                    "risk": item.risk_verdict,
                    "rejection": item.rejection,
                }
                for item in self.decisions
            ],
            "candidates": [
                {
                    "candidate_id": item.candidate_id,
                    "configuration": item.configuration,
                    "status": item.status,
                    "in_sample": item.in_sample,
                    "out_of_sample": item.out_of_sample,
                }
                for item in self.candidates
            ],
            "rejection_counts": self.rejection_counts,
        }
