"""Policy-based risk gate (Phase 14, sections 34-36).

The gate is the mandatory checkpoint between a decision and a trading
intent. Every rejection carries a machine-readable reason so a blocked
trade can always be explained.

Risk-reducing decisions (EXIT / REDUCE) are always allowed: refusing to
let a position be closed would itself be a risk.
"""

from __future__ import annotations

from ShadBotTrader.domain.strategy.decision import TradingDecision
from ShadBotTrader.domain.strategy.ports import RiskGate
from ShadBotTrader.domain.strategy.risk_policy import RiskPolicy, RiskVerdict
from ShadBotTrader.domain.strategy.strategy_context import StrategyContext
from ShadBotTrader.domain.strategy.strategy_types import DecisionType, RejectionReason

# Decisions that reduce exposure are never blocked by exposure limits.
_RISK_REDUCING = (DecisionType.EXIT, DecisionType.REDUCE, DecisionType.CANCEL)


class PolicyRiskGate(RiskGate):
    """Validates a decision against a :class:`RiskPolicy`."""

    def __init__(self, policy: RiskPolicy | None = None) -> None:
        self._policy = policy or RiskPolicy()

    @property
    def policy(self) -> RiskPolicy:
        return self._policy

    def evaluate(self, decision: TradingDecision, context: StrategyContext) -> RiskVerdict:
        # A HOLD never reaches execution; nothing to check.
        if not decision.is_actionable:
            return RiskVerdict.approve("no action requested")

        risk_reducing = decision.decision_type in _RISK_REDUCING

        risk_state = context.risk_state
        if risk_state is not None:
            # Drawdown and daily-loss limits are absolute: once breached
            # the account must not increase exposure at all.
            if risk_state.max_drawdown_percent > self._policy.max_drawdown_percent:
                if not risk_reducing:
                    return RiskVerdict.reject(
                        RejectionReason.RISK_MAX_DRAWDOWN,
                        f"drawdown {risk_state.max_drawdown_percent}% > "
                        f"limit {self._policy.max_drawdown_percent}%",
                    )
            if risk_state.max_daily_loss_percent > self._policy.max_daily_loss_percent:
                if not risk_reducing:
                    return RiskVerdict.reject(
                        RejectionReason.RISK_DAILY_LOSS,
                        f"daily loss {risk_state.max_daily_loss_percent}% > "
                        f"limit {self._policy.max_daily_loss_percent}%",
                    )
            if risk_state.exposure_ratio > self._policy.max_exposure_ratio:
                if not risk_reducing:
                    return RiskVerdict.reject(
                        RejectionReason.RISK_EXPOSURE,
                        f"exposure {risk_state.exposure_ratio} > "
                        f"limit {self._policy.max_exposure_ratio}",
                    )

        portfolio = context.portfolio
        if (
            portfolio is not None
            and not risk_reducing
            and portfolio.open_position_count >= self._policy.max_open_positions
        ):
            return RiskVerdict.reject(
                RejectionReason.RISK_POSITION_LIMIT,
                f"{portfolio.open_position_count} open positions >= "
                f"limit {self._policy.max_open_positions}",
            )

        if not risk_reducing and decision.confidence < self._policy.min_confidence:
            return RiskVerdict.reject(
                RejectionReason.LOW_CONFIDENCE,
                f"confidence {decision.confidence:.3f} < "
                f"minimum {self._policy.min_confidence:.3f}",
            )

        return RiskVerdict.approve()
