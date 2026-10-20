"""Durable decision and execution journals (Phase 20).

The audit trail is the part of the platform that most needs to survive a
restart: it is the record of what the system decided, why it was allowed
or refused, and what actually happened at the venue.

Both classes implement the existing domain ports, so swapping them in is
a one-line change at the composition root. Each keeps an in-memory
mirror of the current session for fast reads while writing every entry
to SQLite for durability.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ShadBotTrader.domain.execution.fill import ExecutionResult
from ShadBotTrader.domain.execution.ports import ExecutionJournal, ExecutionJournalEntry
from ShadBotTrader.domain.execution.resolved_order import ResolvedOrder
from ShadBotTrader.domain.strategy.decision import TradingDecision
from ShadBotTrader.domain.strategy.ports import DecisionJournal, JournalEntry
from ShadBotTrader.domain.strategy.risk_policy import RiskVerdict
from ShadBotTrader.domain.strategy.trading_intent import TradingIntent
from ShadBotTrader.infrastructure.persistence.database import Database


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SqliteDecisionJournal(DecisionJournal):
    """Persists every trading decision, approved or refused."""

    def __init__(self, database: Database, session_id: str = "default") -> None:
        self._database = database
        self._session_id = session_id
        self._entries: List[JournalEntry] = []

    @property
    def session_id(self) -> str:
        return self._session_id

    def record(
        self,
        decision: TradingDecision,
        verdict: Optional[RiskVerdict] = None,
        intent: Optional[TradingIntent] = None,
    ) -> None:
        self._entries.append(JournalEntry(decision=decision, verdict=verdict, intent=intent))

        rejection = None
        if verdict is not None and verdict.rejection_reason is not None:
            rejection = verdict.rejection_reason.value
        elif decision.rejection_reason is not None:
            rejection = decision.rejection_reason.value

        payload = {
            "decision": {
                "decision_id": decision.decision_id,
                "strategy_id": str(decision.strategy_id),
                "strategy_version": decision.strategy_version.number,
                "symbol": str(decision.symbol),
                "timestamp": str(decision.timestamp),
                "decision_type": decision.decision_type.value,
                "confidence": decision.confidence,
                "reason": decision.reason,
                "source_signal_id": decision.source_signal_id,
                "context": _jsonable(decision.context),
            },
            "verdict": (
                {"approved": verdict.approved, "reason": verdict.reason}
                if verdict is not None
                else None
            ),
            "intent": (
                {
                    "intent_id": intent.intent_id,
                    "intent_type": intent.intent_type.value,
                    "side": intent.side.value,
                    "quantity_policy": intent.quantity_policy.policy_type.value,
                    "quantity": str(intent.quantity_policy.value),
                    "price_policy": intent.price_policy.policy_type.value,
                }
                if intent is not None
                else None
            ),
        }

        self._database.execute(
            """
            INSERT INTO trading_decision
                (session_id, decision_id, strategy_id, symbol, decision_type,
                 confidence, approved, rejection, intent_id, payload, recorded_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                self._session_id,
                decision.decision_id,
                str(decision.strategy_id),
                str(decision.symbol),
                decision.decision_type.value,
                decision.confidence,
                None if verdict is None else int(verdict.approved),
                rejection,
                intent.intent_id if intent is not None else None,
                json.dumps(payload, default=str),
                _now(),
            ),
        )

    def entries(self) -> List[JournalEntry]:
        """Entries recorded by *this* instance (the live session)."""
        return list(self._entries)

    # -- durable reads --------------------------------------------------------
    def stored_rows(self, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Every decision ever stored, including previous runs."""
        target = session_id or self._session_id
        rows = self._database.query(
            "SELECT * FROM trading_decision WHERE session_id = ? ORDER BY id",
            (target,),
        )
        return [dict(row) for row in rows]

    def stored_count(self, session_id: Optional[str] = None) -> int:
        target = session_id or self._session_id
        row = self._database.query_one(
            "SELECT COUNT(*) AS total FROM trading_decision WHERE session_id = ?",
            (target,),
        )
        return int(row["total"]) if row else 0

    def rejection_counts(self, session_id: Optional[str] = None) -> Dict[str, int]:
        """Histogram of rejection reasons, computed by the database."""
        target = session_id or self._session_id
        rows = self._database.query(
            """
            SELECT rejection, COUNT(*) AS total
            FROM trading_decision
            WHERE session_id = ? AND rejection IS NOT NULL
            GROUP BY rejection ORDER BY total DESC
            """,
            (target,),
        )
        return {row["rejection"]: int(row["total"]) for row in rows}

    def sessions(self) -> List[str]:
        """Every session id present in storage."""
        rows = self._database.query(
            "SELECT DISTINCT session_id FROM trading_decision ORDER BY session_id"
        )
        return [row["session_id"] for row in rows]

    @property
    def intents(self) -> List[TradingIntent]:
        return [entry.intent for entry in self._entries if entry.intent is not None]

    @property
    def rejected(self) -> List[JournalEntry]:
        return [
            entry
            for entry in self._entries
            if entry.verdict is not None and not entry.verdict.approved
        ]


class SqliteExecutionJournal(ExecutionJournal):
    """Persists every execution attempt, filled or refused."""

    def __init__(self, database: Database, session_id: str = "default") -> None:
        self._database = database
        self._session_id = session_id
        self._entries: List[ExecutionJournalEntry] = []

    @property
    def session_id(self) -> str:
        return self._session_id

    def record(
        self,
        intent: TradingIntent,
        order: Optional[ResolvedOrder] = None,
        result: Optional[ExecutionResult] = None,
    ) -> None:
        self._entries.append(ExecutionJournalEntry(intent=intent, order=order, result=result))

        average = result.average_fill_price if result is not None else None
        payload = {
            "intent": {
                "intent_id": intent.intent_id,
                "decision_id": intent.decision_id,
                "strategy_id": str(intent.strategy_id),
                "intent_type": intent.intent_type.value,
            },
            "order": (
                {
                    "order_id": order.order_id,
                    "order_type": order.order_type.value,
                    "quantity": str(order.quantity),
                }
                if order is not None
                else None
            ),
            "result": (
                {
                    "status": result.status.value,
                    "requested": str(result.requested_quantity),
                    "filled": str(result.filled_quantity),
                    "remaining": str(result.remaining_quantity),
                    "message": result.message,
                    "fills": len(result.fills),
                }
                if result is not None
                else None
            ),
        }

        self._database.execute(
            """
            INSERT INTO execution_attempt
                (session_id, intent_id, order_id, symbol, side, status,
                 filled_qty, avg_price, rejection, payload, recorded_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                self._session_id,
                intent.intent_id,
                order.order_id if order is not None else None,
                str(intent.symbol),
                intent.side.value,
                result.status.value if result is not None else None,
                str(result.filled_quantity) if result is not None else None,
                str(average) if average is not None else None,
                (
                    result.rejection_reason.value
                    if result is not None and result.rejection_reason is not None
                    else None
                ),
                json.dumps(payload, default=str),
                _now(),
            ),
        )

    def entries(self) -> List[ExecutionJournalEntry]:
        return list(self._entries)

    # -- durable reads --------------------------------------------------------
    def stored_rows(self, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        target = session_id or self._session_id
        rows = self._database.query(
            "SELECT * FROM execution_attempt WHERE session_id = ? ORDER BY id",
            (target,),
        )
        return [dict(row) for row in rows]

    def stored_count(self, session_id: Optional[str] = None) -> int:
        target = session_id or self._session_id
        row = self._database.query_one(
            "SELECT COUNT(*) AS total FROM execution_attempt WHERE session_id = ?",
            (target,),
        )
        return int(row["total"]) if row else 0

    def rejection_counts(self, session_id: Optional[str] = None) -> Dict[str, int]:
        target = session_id or self._session_id
        rows = self._database.query(
            """
            SELECT rejection, COUNT(*) AS total
            FROM execution_attempt
            WHERE session_id = ? AND rejection IS NOT NULL
            GROUP BY rejection ORDER BY total DESC
            """,
            (target,),
        )
        return {row["rejection"]: int(row["total"]) for row in rows}

    @property
    def executed(self) -> List[ExecutionJournalEntry]:
        return [entry for entry in self._entries if entry.executed]

    @property
    def failed(self) -> List[ExecutionJournalEntry]:
        return [entry for entry in self._entries if not entry.executed]


def _jsonable(value: Any) -> Any:
    """Best-effort conversion of arbitrary context data to JSON types."""
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)
