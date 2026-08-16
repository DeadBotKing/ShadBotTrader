"""Ports (contracts) of the simulation domain — Phase 16.

The Simulation Platform *orchestrates* the existing platforms; it never
reimplements them (section 2). Trading logic, portfolio accounting and
risk rules are used exactly as they are in live operation — only the
market data source and the execution venue are swapped.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from ShadBotTrader.domain.execution.market_view import MarketQuote
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timestamp import Timestamp
from ShadBotTrader.domain.simulation.market_event import MarketEvent
from ShadBotTrader.domain.simulation.performance import PerformanceMetrics, TradeRecord
from ShadBotTrader.domain.simulation.session import SimulationSession


class SimulationMarketDataProvider(ABC):
    """Supplies the market events a simulation replays (section 15).

    The simulation must not know whether the data came from CSV, a
    database, a recorded stream or a synthetic generator.
    """

    @abstractmethod
    def events(self) -> List[MarketEvent]:
        """Return every event to replay, ordered by event time."""

    @abstractmethod
    def quote_at(self, symbol: Symbol, moment: Timestamp) -> Optional[MarketQuote]:
        """The tradable quote for ``symbol`` at ``moment``, if known."""


class PredictionSource(ABC):
    """Supplies predictions to the simulated strategy.

    Kept abstract so a backtest can be driven by a trained model, by
    recorded predictions, or by a deterministic synthetic rule without
    the engine caring which.
    """

    @abstractmethod
    def predict(self, event: MarketEvent) -> Optional[float]:
        """Directional value in [0, 1] for ``event``, or None to abstain."""

    @abstractmethod
    def confidence(self, event: MarketEvent) -> float:
        """Confidence in [0, 1] attached to the prediction."""


class SimulationReporter(ABC):
    """Receives progress and results of a simulation run."""

    @abstractmethod
    def on_session_start(self, session: SimulationSession) -> None:
        """Called once before the first event."""

    @abstractmethod
    def on_step(self, event: MarketEvent, equity: str) -> None:
        """Called after each processed market event."""

    @abstractmethod
    def on_session_end(
        self,
        session: SimulationSession,
        metrics: PerformanceMetrics,
        trades: List[TradeRecord],
    ) -> None:
        """Called once the run has finished."""


class NullSimulationReporter(SimulationReporter):
    """A reporter that stays silent (the default)."""

    def on_session_start(self, session: SimulationSession) -> None:
        return None

    def on_step(self, event: MarketEvent, equity: str) -> None:
        return None

    def on_session_end(
        self,
        session: SimulationSession,
        metrics: PerformanceMetrics,
        trades: List[TradeRecord],
    ) -> None:
        return None
