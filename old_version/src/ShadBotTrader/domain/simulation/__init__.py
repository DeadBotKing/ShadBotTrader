"""Simulation domain — Phase 16.

Orchestrates the existing platforms over historical data on a controlled
clock::

    MarketEvent -> Strategy -> RiskGate -> Intent
                -> SimulatedVenue -> Fills -> Portfolio
                -> EquityPoint -> PerformanceMetrics

Core rules: no ``datetime.now()`` inside a simulation (the clock is the
only source of time), events are totally ordered, and the same dataset +
configuration + seed must always produce the same result.
"""

from ShadBotTrader.domain.simulation.clock import ClockSnapshot, SimulationClock
from ShadBotTrader.domain.simulation.equity_curve import EquityCurve, EquityPoint
from ShadBotTrader.domain.simulation.market_event import MarketEvent, SimulationEventQueue
from ShadBotTrader.domain.simulation.performance import (
    PerformanceMetrics,
    TradeRecord,
    sharpe_ratio,
    standard_deviation,
    summarise_trades,
)
from ShadBotTrader.domain.simulation.ports import (
    NullSimulationReporter,
    PredictionSource,
    SimulationMarketDataProvider,
    SimulationReporter,
)
from ShadBotTrader.domain.simulation.replay import (
    MARKER_ADJUST,
    MARKER_ENTRY,
    MARKER_EXIT,
    ReplayBar,
    ReplayRecorder,
    ReplayTape,
    TradeMarker,
)
from ShadBotTrader.domain.simulation.session import (
    SimulationConfiguration,
    SimulationSession,
)
from ShadBotTrader.domain.simulation.simulation_types import (
    EventPriority,
    MarketEventType,
    SessionStatus,
    SimulationMode,
)

__all__ = [
    "MARKER_ADJUST",
    "MARKER_ENTRY",
    "MARKER_EXIT",
    "ClockSnapshot",
    "EquityCurve",
    "EquityPoint",
    "EventPriority",
    "MarketEvent",
    "MarketEventType",
    "NullSimulationReporter",
    "PerformanceMetrics",
    "PredictionSource",
    "ReplayBar",
    "ReplayRecorder",
    "ReplayTape",
    "SessionStatus",
    "SimulationClock",
    "SimulationConfiguration",
    "SimulationEventQueue",
    "SimulationMarketDataProvider",
    "SimulationMode",
    "SimulationReporter",
    "SimulationSession",
    "TradeMarker",
    "TradeRecord",
    "sharpe_ratio",
    "standard_deviation",
    "summarise_trades",
]
