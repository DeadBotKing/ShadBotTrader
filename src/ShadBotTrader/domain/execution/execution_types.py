"""Execution domain enumerations (Phase 14 §51, Phase 15 §21-23)."""

from __future__ import annotations

from enum import Enum


class IntentStatus(str, Enum):
    """Lifecycle of a trading intent (Phase 14, section 51)."""

    CREATED = "created"
    VALIDATING = "validating"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUBMITTED_TO_EXECUTION = "submitted_to_execution"
    COMPLETED = "completed"
    EXPIRED = "expired"


class ExecutionStatus(str, Enum):
    """Outcome of submitting a resolved order to a venue."""

    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class ExecutionRejectionReason(str, Enum):
    """Why an execution attempt did not (fully) succeed."""

    INTENT_EXPIRED = "intent_expired"
    DUPLICATE_INTENT = "duplicate_intent"
    NO_MARKET_PRICE = "no_market_price"
    INSUFFICIENT_LIQUIDITY = "insufficient_liquidity"
    INSUFFICIENT_FUNDS = "insufficient_funds"
    INVALID_QUANTITY = "invalid_quantity"
    NOTHING_TO_CLOSE = "nothing_to_close"
    VENUE_ERROR = "venue_error"


class PositionSide(str, Enum):
    """Direction of an open position (Phase 15, section 14)."""

    LONG = "long"
    SHORT = "short"
    FLAT = "flat"


class TransactionType(str, Enum):
    """Financial transaction kinds (Phase 15, section 20)."""

    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    TRADE = "trade"
    FEE = "fee"
    FUNDING = "funding"
    INTEREST = "interest"
    ADJUSTMENT = "adjustment"
    TRANSFER = "transfer"
