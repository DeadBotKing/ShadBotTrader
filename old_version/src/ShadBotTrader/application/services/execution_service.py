"""Application service: execute approved trading intents.

Phase 14 §19-24 + Phase 15 §2. This service is the composition point of
the Execution Platform and enforces its invariants:

    intent -> [expiry + idempotency guard] -> resolve -> venue -> ledger

Guarantees:

* an expired intent is never executed (Phase 14, section 52)
* the same intent is never executed twice (section 53, idempotency key)
* the ledger only ever sees real fills (Phase 15, section 24)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence, Set

from ShadBotTrader.core.events.event import Event
from ShadBotTrader.core.events.event_bus import EventBus
from ShadBotTrader.domain.execution.events import (
    INTENT_EXPIRED,
    ORDER_FILLED,
    ORDER_PARTIALLY_FILLED,
    ORDER_REJECTED,
    ORDER_RESOLVED,
)
from ShadBotTrader.domain.execution.execution_types import (
    ExecutionRejectionReason,
    ExecutionStatus,
)
from ShadBotTrader.domain.execution.fill import ExecutionResult
from ShadBotTrader.domain.execution.market_view import ExecutionContext
from ShadBotTrader.domain.execution.ports import (
    ExecutionJournal,
    ExecutionVenue,
    IntentResolver,
    PortfolioLedger,
)
from ShadBotTrader.domain.execution.position_state import PositionState
from ShadBotTrader.domain.execution.resolved_order import ResolvedOrder
from ShadBotTrader.domain.strategy.trading_intent import TradingIntent

_SOURCE = "ExecutionService"


@dataclass(frozen=True)
class ExecutionOutcome:
    """The auditable result of executing one intent."""

    intent: TradingIntent
    order: Optional[ResolvedOrder]
    result: Optional[ExecutionResult]
    position: Optional[PositionState]
    rejected_reason: str = ""

    @property
    def executed(self) -> bool:
        return self.result is not None and self.result.is_successful


class ExecutionService:
    """Executes risk-approved intents and updates the portfolio."""

    def __init__(
        self,
        resolver: IntentResolver,
        venue: ExecutionVenue,
        ledger: PortfolioLedger,
        journal: Optional[ExecutionJournal] = None,
        event_bus: Optional[EventBus] = None,
    ) -> None:
        self._resolver = resolver
        self._venue = venue
        self._ledger = ledger
        self._journal = journal
        self._event_bus = event_bus
        self._seen_intents: Set[str] = set()

    def execute(self, intent: TradingIntent, context: ExecutionContext) -> ExecutionOutcome:
        """Run one intent through the execution pipeline."""

        # --- duplicate protection (Phase 14, section 53) -----------------
        if intent.intent_id in self._seen_intents:
            result = ExecutionResult.rejected(
                intent_id=intent.intent_id,
                requested_quantity=intent.quantity_policy.value,
                reason=ExecutionRejectionReason.DUPLICATE_INTENT,
                message="intent has already been submitted",
            )
            return self._fail(intent, None, result, "duplicate intent")

        # --- expiry (Phase 14, section 52) --------------------------------
        if intent.is_expired(context.timestamp):
            result = ExecutionResult.rejected(
                intent_id=intent.intent_id,
                requested_quantity=intent.quantity_policy.value,
                reason=ExecutionRejectionReason.INTENT_EXPIRED,
                message=f"intent expired at {intent.expires_at}",
            )
            self._publish(INTENT_EXPIRED, {"intent_id": intent.intent_id})
            return self._fail(intent, None, result, "intent expired")

        self._seen_intents.add(intent.intent_id)

        # --- resolve policies into a concrete order -----------------------
        order = self._resolver.resolve(intent, context)
        if order is None:
            reason = (
                ExecutionRejectionReason.NOTHING_TO_CLOSE
                if context.position.is_flat
                else ExecutionRejectionReason.INVALID_QUANTITY
            )
            result = ExecutionResult.rejected(
                intent_id=intent.intent_id,
                requested_quantity=intent.quantity_policy.value,
                reason=reason,
                message="intent could not be resolved into an executable order",
            )
            return self._fail(intent, None, result, result.message)

        self._publish(
            ORDER_RESOLVED,
            {
                "order_id": order.order_id,
                "intent_id": intent.intent_id,
                "symbol": str(order.symbol),
                "side": order.side.value,
                "quantity": str(order.quantity),
            },
        )

        # --- submit to the venue -------------------------------------------
        result = self._venue.submit(order, context)

        if not result.is_successful:
            self._publish(
                ORDER_REJECTED,
                {
                    "order_id": order.order_id,
                    "intent_id": intent.intent_id,
                    "reason": result.message,
                },
            )
            return self._fail(intent, order, result, result.message)

        # --- book the fills into the portfolio ------------------------------
        position = self._ledger.apply(result)

        event_type = (
            ORDER_FILLED if result.status is ExecutionStatus.FILLED else ORDER_PARTIALLY_FILLED
        )
        average = result.average_fill_price
        self._publish(
            event_type,
            {
                "order_id": order.order_id,
                "intent_id": intent.intent_id,
                "symbol": str(order.symbol),
                "filled_quantity": str(result.filled_quantity),
                "average_price": str(average) if average else "",
            },
        )
        self._record(intent, order, result)

        return ExecutionOutcome(
            intent=intent,
            order=order,
            result=result,
            position=position,
            rejected_reason="",
        )

    def execute_all(
        self,
        intents: Sequence[TradingIntent],
        contexts: Sequence[ExecutionContext],
    ) -> List[ExecutionOutcome]:
        """Execute a batch of intents against their matching contexts."""
        if len(intents) != len(contexts):
            raise ValueError("intents and contexts must have the same length")
        return [
            self.execute(intent, context) for intent, context in zip(intents, contexts, strict=True)
        ]

    # -- helpers ------------------------------------------------------------
    def _fail(
        self,
        intent: TradingIntent,
        order: Optional[ResolvedOrder],
        result: ExecutionResult,
        reason: str,
    ) -> ExecutionOutcome:
        self._record(intent, order, result)
        return ExecutionOutcome(
            intent=intent,
            order=order,
            result=result,
            position=None,
            rejected_reason=reason,
        )

    def _record(
        self,
        intent: TradingIntent,
        order: Optional[ResolvedOrder],
        result: Optional[ExecutionResult],
    ) -> None:
        if self._journal is not None:
            self._journal.record(intent, order, result)

    def _publish(self, event_type: str, payload: dict) -> None:
        if self._event_bus is not None:
            self._event_bus.publish(Event(event_type=event_type, payload=payload, source=_SOURCE))
