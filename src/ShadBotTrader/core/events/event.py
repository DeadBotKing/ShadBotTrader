"""The immutable Event envelope used across the event-driven system."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from types import MappingProxyType
from typing import Any, Mapping
from uuid import uuid4

from ShadBotTrader.core.errors import EventError


@dataclass(frozen=True)
class Event:
    """A single immutable domain/system event.

    Attributes:
        event_type: The stable, past-tense name of the event
            (for example ``MarketDataReceived``).
        payload: The event body, exposed as a read-only mapping.
        event_id: A unique identifier for this specific occurrence.
        occurred_at: The UTC timestamp of the occurrence.
        source: The component that produced the event.
        correlation_id: Links events that belong to one logical flow.
        causation_id: Identifies the event that caused this one.
        metadata: Additional read-only contextual data.
    """

    event_type: str
    payload: Mapping[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: str(uuid4()))
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source: str = ""
    correlation_id: str = ""
    causation_id: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.event_type.strip():
            raise EventError("event_type must not be empty")
        object.__setattr__(self, "payload", MappingProxyType(dict(self.payload)))
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))
