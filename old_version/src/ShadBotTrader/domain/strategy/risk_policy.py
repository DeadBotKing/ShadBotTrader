"""Risk policy and the risk gate verdict (Phase 14, sections 34-36).

The risk gate is mandatory: no decision may become a trading intent
without passing it. Its verdict is an explicit value object so that the
reason for any rejection is auditable.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Optional

from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.common.value_object import ValueObject
from ShadBotTrader.domain.strategy.strategy_types import RejectionReason


class RiskPolicy(ValueObject):
    """Hard limits a decision must respect before it can be executed."""

    def __init__(
        self,
        max_drawdown_percent: Decimal = Decimal("20"),
        max_daily_loss_percent: Decimal = Decimal("5"),
        max_exposure_ratio: Decimal = Decimal("0.5"),
        max_open_positions: int = 5,
        min_confidence: float = 0.0,
    ) -> None:
        if not 0 <= max_drawdown_percent <= 100:
            raise ValidationError("max_drawdown_percent must be in [0, 100]")
        if not 0 <= max_daily_loss_percent <= 100:
            raise ValidationError("max_daily_loss_percent must be in [0, 100]")
        if not 0 <= max_exposure_ratio <= 1:
            raise ValidationError("max_exposure_ratio must be in [0, 1]")
        if max_open_positions < 0:
            raise ValidationError("max_open_positions must be >= 0")
        if not 0.0 <= min_confidence <= 1.0:
            raise ValidationError("min_confidence must be in [0, 1]")

        self._max_drawdown_percent = max_drawdown_percent
        self._max_daily_loss_percent = max_daily_loss_percent
        self._max_exposure_ratio = max_exposure_ratio
        self._max_open_positions = max_open_positions
        self._min_confidence = float(min_confidence)

    @property
    def max_drawdown_percent(self) -> Decimal:
        return self._max_drawdown_percent

    @property
    def max_daily_loss_percent(self) -> Decimal:
        return self._max_daily_loss_percent

    @property
    def max_exposure_ratio(self) -> Decimal:
        return self._max_exposure_ratio

    @property
    def max_open_positions(self) -> int:
        return self._max_open_positions

    @property
    def min_confidence(self) -> float:
        return self._min_confidence

    def _value(self) -> tuple[Any, ...]:
        return (
            self._max_drawdown_percent,
            self._max_daily_loss_percent,
            self._max_exposure_ratio,
            self._max_open_positions,
            self._min_confidence,
        )


class RiskVerdict(ValueObject):
    """The result of the risk gate: approved, or rejected with a reason."""

    def __init__(
        self,
        approved: bool,
        reason: str = "",
        rejection_reason: Optional[RejectionReason] = None,
    ) -> None:
        if not approved and rejection_reason is None:
            raise ValidationError("A rejected RiskVerdict must carry a rejection_reason")
        self._approved = approved
        self._reason = reason
        self._rejection_reason = rejection_reason

    @classmethod
    def approve(cls, reason: str = "within risk policy") -> "RiskVerdict":
        """Build an approving verdict."""
        return cls(approved=True, reason=reason)

    @classmethod
    def reject(cls, rejection_reason: RejectionReason, reason: str = "") -> "RiskVerdict":
        """Build a rejecting verdict with an explicit machine-readable cause."""
        return cls(
            approved=False,
            reason=reason or rejection_reason.value,
            rejection_reason=rejection_reason,
        )

    @property
    def approved(self) -> bool:
        return self._approved

    @property
    def reason(self) -> str:
        return self._reason

    @property
    def rejection_reason(self) -> Optional[RejectionReason]:
        return self._rejection_reason

    def __bool__(self) -> bool:
        return self._approved

    def _value(self) -> tuple[Any, ...]:
        return (self._approved, self._reason, self._rejection_reason)
