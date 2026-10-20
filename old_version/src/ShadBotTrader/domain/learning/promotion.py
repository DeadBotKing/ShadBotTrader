"""Promotion policy and gate (Phase 17: Promotion Gate).

The gate is the reason this platform can search parameters without
fooling itself. A candidate may only be promoted when it beats the
incumbent **out of sample**, on evidence that is broad enough to mean
something, and without the in-sample/out-of-sample divergence that
signals overfitting.

Every rejection carries a machine-readable reason so the learning memory
can avoid re-exploring the same dead end.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Optional

from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.common.value_object import ValueObject
from ShadBotTrader.domain.learning.candidate import Candidate
from ShadBotTrader.domain.learning.learning_types import RejectionReason
from ShadBotTrader.domain.learning.objective import is_penalty


class PromotionPolicy(ValueObject):
    """The bar a candidate must clear to replace the incumbent."""

    def __init__(
        self,
        min_improvement: Decimal = Decimal("0"),
        min_out_of_sample_trades: int = 10,
        min_validation_folds: int = 2,
        max_drawdown_percent: Decimal = Decimal("25"),
        require_positive_return: bool = True,
        min_positive_fold_ratio: Decimal = Decimal("0.5"),
        max_overfit_gap: Optional[Decimal] = None,
    ) -> None:
        if min_out_of_sample_trades < 0:
            raise ValidationError("min_out_of_sample_trades must be >= 0")
        if min_validation_folds < 1:
            raise ValidationError("min_validation_folds must be >= 1")
        if not 0 <= min_positive_fold_ratio <= 1:
            raise ValidationError("min_positive_fold_ratio must be in [0, 1]")
        if max_drawdown_percent < 0:
            raise ValidationError("max_drawdown_percent must be >= 0")

        self._min_improvement = min_improvement
        self._min_out_of_sample_trades = min_out_of_sample_trades
        self._min_validation_folds = min_validation_folds
        self._max_drawdown_percent = max_drawdown_percent
        self._require_positive_return = require_positive_return
        self._min_positive_fold_ratio = min_positive_fold_ratio
        self._max_overfit_gap = max_overfit_gap

    @property
    def min_improvement(self) -> Decimal:
        return self._min_improvement

    @property
    def min_out_of_sample_trades(self) -> int:
        return self._min_out_of_sample_trades

    @property
    def min_validation_folds(self) -> int:
        return self._min_validation_folds

    @property
    def max_drawdown_percent(self) -> Decimal:
        return self._max_drawdown_percent

    @property
    def require_positive_return(self) -> bool:
        return self._require_positive_return

    @property
    def min_positive_fold_ratio(self) -> Decimal:
        return self._min_positive_fold_ratio

    @property
    def max_overfit_gap(self) -> Optional[Decimal]:
        return self._max_overfit_gap

    def _value(self) -> tuple[Any, ...]:
        return (
            self._min_improvement,
            self._min_out_of_sample_trades,
            self._min_validation_folds,
            self._max_drawdown_percent,
            self._require_positive_return,
            self._min_positive_fold_ratio,
            self._max_overfit_gap,
        )


class PromotionVerdict(ValueObject):
    """Approved, or rejected with an explicit cause."""

    def __init__(
        self,
        approved: bool,
        reason: str = "",
        rejection_reason: Optional[RejectionReason] = None,
    ) -> None:
        if not approved and rejection_reason is None:
            raise ValidationError("A rejected PromotionVerdict must carry a reason")
        self._approved = approved
        self._reason = reason
        self._rejection_reason = rejection_reason

    @classmethod
    def approve(cls, reason: str = "beats the baseline out of sample") -> "PromotionVerdict":
        return cls(approved=True, reason=reason)

    @classmethod
    def reject(cls, rejection_reason: RejectionReason, reason: str = "") -> "PromotionVerdict":
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


class PromotionGate:
    """Evaluates a candidate against the incumbent under a policy."""

    def __init__(self, policy: Optional[PromotionPolicy] = None) -> None:
        self._policy = policy or PromotionPolicy()

    @property
    def policy(self) -> PromotionPolicy:
        return self._policy

    def evaluate(
        self,
        candidate: Candidate,
        baseline_score: Optional[Decimal] = None,
    ) -> PromotionVerdict:
        """Decide whether ``candidate`` may replace the incumbent."""
        policy = self._policy

        # --- evidence must exist ------------------------------------------
        folds = candidate.out_of_sample
        if len(folds) < policy.min_validation_folds:
            return PromotionVerdict.reject(
                RejectionReason.FAILED_VALIDATION_FOLD,
                f"only {len(folds)} validation fold(s), " f"{policy.min_validation_folds} required",
            )

        score = candidate.out_of_sample_score
        if score is None:
            return PromotionVerdict.reject(
                RejectionReason.EVALUATION_FAILED,
                "candidate has no out-of-sample score",
            )

        # A sentinel score means at least one fold produced no usable
        # evidence (typically too few trades). That is not a bad result
        # to be weighed against others — it is an absent result.
        if is_penalty(score) or candidate.has_penalised_folds:
            return PromotionVerdict.reject(
                RejectionReason.INSUFFICIENT_TRADES,
                f"{candidate.penalised_fold_count}/{len(folds)} validation fold(s) "
                f"produced too little activity to judge",
            )

        # --- evidence must be broad enough --------------------------------
        trades = candidate.total_out_of_sample_trades
        if trades < policy.min_out_of_sample_trades:
            return PromotionVerdict.reject(
                RejectionReason.INSUFFICIENT_TRADES,
                f"{trades} out-of-sample trade(s), " f"{policy.min_out_of_sample_trades} required",
            )

        # --- the result must be acceptable in absolute terms ---------------
        worst_drawdown = max(
            (record.metrics.max_drawdown_percent for record in folds),
            default=Decimal("0"),
        )
        if worst_drawdown > policy.max_drawdown_percent:
            return PromotionVerdict.reject(
                RejectionReason.EXCESSIVE_DRAWDOWN,
                f"worst fold drawdown {worst_drawdown:.2f}% > "
                f"limit {policy.max_drawdown_percent}%",
            )

        if policy.require_positive_return:
            total_return = sum((record.metrics.total_return for record in folds), Decimal("0"))
            if total_return <= 0:
                return PromotionVerdict.reject(
                    RejectionReason.NEGATIVE_RETURN,
                    f"aggregate out-of-sample return {total_return:.4f} is not positive",
                )

        # --- the result must be consistent, not a single lucky fold --------
        positive_ratio = Decimal(candidate.positive_fold_count) / Decimal(len(folds))
        if positive_ratio < policy.min_positive_fold_ratio:
            return PromotionVerdict.reject(
                RejectionReason.UNSTABLE_OUT_OF_SAMPLE,
                f"only {candidate.positive_fold_count}/{len(folds)} folds positive "
                f"(need {policy.min_positive_fold_ratio})",
            )

        # --- and it must not look overfit ----------------------------------
        if policy.max_overfit_gap is not None:
            gap = candidate.overfit_gap
            if gap is not None and gap > policy.max_overfit_gap:
                return PromotionVerdict.reject(
                    RejectionReason.OVERFIT_SUSPECTED,
                    f"in-sample exceeds out-of-sample by {gap:.4f} "
                    f"(limit {policy.max_overfit_gap})",
                )

        # --- finally, it must actually beat the incumbent -------------------
        if baseline_score is not None:
            required = baseline_score + policy.min_improvement
            if score <= required:
                return PromotionVerdict.reject(
                    RejectionReason.WORSE_THAN_BASELINE,
                    f"out-of-sample score {score:.4f} does not beat "
                    f"baseline {baseline_score:.4f} by {policy.min_improvement}",
                )

        return PromotionVerdict.approve(
            f"out-of-sample score {score:.4f} over {len(folds)} folds, {trades} trades"
        )
