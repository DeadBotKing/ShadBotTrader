"""Enumerations of the trading domain (Phase 14, sections 11-21, 33)."""

from __future__ import annotations

from enum import Enum


class StrategyState(str, Enum):
    """Explicit lifecycle state of a strategy (Phase 14, section 11)."""

    IDLE = "idle"
    WATCHING = "watching"
    READY = "ready"
    ENTERED = "entered"
    EXITING = "exiting"
    PAUSED = "paused"
    DISABLED = "disabled"


class SignalType(str, Enum):
    """The kind of signal a strategy emits (Phase 14, section 12).

    A signal is never an order; it is an opinion about the market.
    """

    BUY = "buy"
    SELL = "sell"
    EXIT = "exit"
    HOLD = "hold"


class SignalStrength(str, Enum):
    """How strongly a strategy believes in a signal (section 14)."""

    WEAK = "weak"
    NORMAL = "normal"
    STRONG = "strong"
    VERY_STRONG = "very_strong"


class DecisionType(str, Enum):
    """The outcome of decision making (Phase 14, section 17).

    A decision is NOT an order (section 18).
    """

    ENTER = "enter"
    EXIT = "exit"
    REDUCE = "reduce"
    INCREASE = "increase"
    HOLD = "hold"
    CANCEL = "cancel"


class IntentType(str, Enum):
    """The type of a trading intent (Phase 14, section 21)."""

    ENTER_POSITION = "enter_position"
    EXIT_POSITION = "exit_position"
    REDUCE_POSITION = "reduce_position"
    INCREASE_POSITION = "increase_position"
    REVERSE_POSITION = "reverse_position"
    CANCEL_INTENT = "cancel_intent"


class QuantityPolicyType(str, Enum):
    """How the executor should size the position (section 23)."""

    FIXED = "fixed"
    PERCENT_EQUITY = "percent_equity"
    RISK_AMOUNT = "risk_amount"
    VOLATILITY = "volatility"
    CONFIDENCE_WEIGHTED = "confidence_weighted"


class PricePolicyType(str, Enum):
    """How the executor should price the order (section 24).

    Trading only expresses a policy; the Execution Platform builds the
    concrete broker order.
    """

    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"
    REFERENCE_PRICE = "reference_price"


class MarketRegime(str, Enum):
    """Coarse market regime classification (section 33)."""

    TRENDING = "trending"
    RANGING = "ranging"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    UNKNOWN = "unknown"


class RejectionReason(str, Enum):
    """Why a signal or decision was rejected.

    Recorded for decision auditability (Phase 14, section 2).
    """

    STALE_PREDICTION = "stale_prediction"
    LOW_CONFIDENCE = "low_confidence"
    SCHEMA_MISMATCH = "schema_mismatch"
    SYMBOL_MISMATCH = "symbol_mismatch"
    TIMEFRAME_MISMATCH = "timeframe_mismatch"
    STRATEGY_DISABLED = "strategy_disabled"
    RISK_MAX_DRAWDOWN = "risk_max_drawdown"
    RISK_DAILY_LOSS = "risk_daily_loss"
    RISK_EXPOSURE = "risk_exposure"
    RISK_POSITION_LIMIT = "risk_position_limit"
    NO_SIGNAL = "no_signal"
