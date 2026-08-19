"""Simulation domain enumerations (Phase 16, sections 7, 16, 20)."""

from __future__ import annotations

from enum import Enum


class SessionStatus(str, Enum):
    """Lifecycle of a simulation session (Phase 16, section 7)."""

    CREATED = "created"
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SimulationMode(str, Enum):
    """What the session is being used for (Phase 16, section 4).

    Backtest is only one use case of the Simulation Platform.
    """

    BACKTEST = "backtest"
    REPLAY = "replay"
    PAPER = "paper"
    SCENARIO = "scenario"


class EntryTiming(str, Enum):
    """When an order created from a candle decision may be filled."""

    SIGNAL_CLOSE = "signal_close"
    NEXT_OPEN = "next_open"


class SameBarPolicy(str, Enum):
    """How OHLC ambiguity is resolved when TP and SL share one candle."""

    STOP_FIRST = "stop_first"
    TARGET_FIRST = "target_first"
    SKIP_AMBIGUOUS = "skip_ambiguous"


class MarketEventType(str, Enum):
    """Kinds of market event a simulation can consume (section 16)."""

    CANDLE = "candle"
    TICK = "tick"
    QUOTE = "quote"
    TRADE = "trade"


class EventPriority(int, Enum):
    """Deterministic ordering of events sharing a timestamp (section 18).

    Lower values are processed first. Market data must always be seen
    before the decisions it triggers, and fills must settle before the
    step is closed — otherwise a run would not be reproducible.
    """

    MARKET = 0
    SIGNAL = 1
    DECISION = 2
    ORDER = 3
    FILL = 4
    PORTFOLIO = 5
    STEP_COMPLETED = 6
