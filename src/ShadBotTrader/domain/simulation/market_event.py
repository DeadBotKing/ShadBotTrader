"""Simulation market events and their deterministic queue.

Phase 16, sections 16-19. Every event carries an ``event_time``; the
clock follows event time, never wall time. When several events share a
timestamp, ordering falls back to priority and then to an insertion
sequence, so the queue is *totally* ordered — a prerequisite for
reproducible runs (section 18).
"""

from __future__ import annotations

import heapq
from typing import Any, Dict, List, Mapping, Optional, Tuple

from ShadBotTrader.domain.market.candle import Candle
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timestamp import Timestamp
from ShadBotTrader.domain.simulation.simulation_types import EventPriority, MarketEventType


class MarketEvent:
    """One thing that happened in the (historical) market."""

    def __init__(
        self,
        event_type: MarketEventType,
        symbol: Symbol,
        event_time: Timestamp,
        candle: Optional[Candle] = None,
        payload: Mapping[str, Any] | None = None,
        priority: EventPriority = EventPriority.MARKET,
    ) -> None:
        self._event_type = event_type
        self._symbol = symbol
        self._event_time = event_time
        self._candle = candle
        self._payload: Dict[str, Any] = dict(payload or {})
        self._priority = priority

    @classmethod
    def from_candle(cls, symbol: Symbol, candle: Candle) -> "MarketEvent":
        """Build a candle event timed at the candle's open time."""
        return cls(
            event_type=MarketEventType.CANDLE,
            symbol=symbol,
            event_time=candle.open_time,
            candle=candle,
        )

    @property
    def event_type(self) -> MarketEventType:
        return self._event_type

    @property
    def symbol(self) -> Symbol:
        return self._symbol

    @property
    def event_time(self) -> Timestamp:
        return self._event_time

    @property
    def candle(self) -> Optional[Candle]:
        return self._candle

    @property
    def payload(self) -> Dict[str, Any]:
        return dict(self._payload)

    @property
    def priority(self) -> EventPriority:
        return self._priority

    def __str__(self) -> str:
        return f"{self._event_type.value}@{self._event_time} {self._symbol}"


class SimulationEventQueue:
    """A priority queue ordered by (time, priority, sequence).

    The sequence counter is the tie-breaker of last resort: two events
    with the same timestamp *and* priority are processed in the order
    they were pushed, never arbitrarily.
    """

    def __init__(self) -> None:
        self._heap: List[Tuple[Any, int, int, MarketEvent]] = []
        self._sequence = 0

    def push(self, event: MarketEvent) -> None:
        """Add an event to the queue."""
        heapq.heappush(
            self._heap,
            (event.event_time.value, int(event.priority), self._sequence, event),
        )
        self._sequence += 1

    def push_all(self, events: List[MarketEvent]) -> None:
        """Add many events, preserving their relative order on ties."""
        for event in events:
            self.push(event)

    def pop(self) -> MarketEvent:
        """Remove and return the earliest event."""
        if not self._heap:
            raise IndexError("pop from an empty SimulationEventQueue")
        return heapq.heappop(self._heap)[3]

    def peek(self) -> Optional[MarketEvent]:
        """Return the earliest event without removing it."""
        return self._heap[0][3] if self._heap else None

    @property
    def is_empty(self) -> bool:
        return not self._heap

    def __len__(self) -> int:
        return len(self._heap)
