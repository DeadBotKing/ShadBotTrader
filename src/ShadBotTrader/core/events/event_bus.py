"""A deterministic in-memory event bus with synchronous dispatch."""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Callable, DefaultDict, List

from ShadBotTrader.core.errors import EventError
from ShadBotTrader.core.events.event import Event

EventHandler = Callable[[Event], None]
WILDCARD = "*"
logger = logging.getLogger("ShadBotTrader.core.events")


class EventBus:
    """Synchronous, deterministic in-memory event bus.

    Dispatch is synchronous and handlers run in subscription order so
    behaviour is fully reproducible. Each handler is isolated: an
    exception raised by one handler never prevents the remaining
    handlers from running, and every failure is logged and counted.
    """

    def __init__(self) -> None:
        self._handlers: DefaultDict[str, List[EventHandler]] = defaultdict(list)
        self._seen_event_ids: set[str] = set()
        self._published_count = 0
        self._failed_count = 0

    @property
    def published_count(self) -> int:
        """Number of unique events published so far."""
        return self._published_count

    @property
    def failed_count(self) -> int:
        """Number of handler invocations that raised an exception."""
        return self._failed_count

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """Register ``handler`` for ``event_type`` (or ``"*"`` for all)."""
        if not event_type.strip():
            raise EventError("event_type must not be empty")
        if handler in self._handlers[event_type]:
            return
        self._handlers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        """Remove a previously registered handler."""
        handlers = self._handlers.get(event_type)
        if handlers is None:
            return
        if handler in handlers:
            handlers.remove(handler)

    def publish(self, event: Event) -> None:
        """Dispatch ``event`` to every matching handler exactly once.

        Duplicate delivery is prevented by the event id, so publishing
        the same ``Event`` object twice is a no-op the second time.
        """
        if event.event_id in self._seen_event_ids:
            return
        self._seen_event_ids.add(event.event_id)
        self._published_count += 1
        for handler in list(self._handlers[event.event_type]):
            self._dispatch(event, handler)
        if event.event_type != WILDCARD:
            for handler in list(self._handlers[WILDCARD]):
                self._dispatch(event, handler)

    def _dispatch(self, event: Event, handler: EventHandler) -> None:
        try:
            handler(event)
        except Exception:
            self._failed_count += 1
            logger.exception("Event handler failed for event_type=%s", event.event_type)
