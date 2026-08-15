"""Tests for the in-memory event bus."""

from ShadBotTrader.core.events.event import Event
from ShadBotTrader.core.events.event_bus import EventBus


def test_dispatch_in_subscription_order():
    bus = EventBus()
    order: list[str] = []
    bus.subscribe("T", lambda event: order.append("first"))
    bus.subscribe("T", lambda event: order.append("second"))
    bus.publish(Event("T"))
    assert order == ["first", "second"]


def test_wildcard_handlers_receive_everything():
    bus = EventBus()
    received: list[str] = []
    bus.subscribe("*", lambda event: received.append(event.event_type))
    bus.publish(Event("A"))
    bus.publish(Event("B"))
    assert received == ["A", "B"]


def test_duplicate_publish_is_ignored():
    bus = EventBus()
    counter: list[int] = []
    bus.subscribe("T", lambda event: counter.append(1))
    event = Event("T")
    bus.publish(event)
    bus.publish(event)
    assert counter == [1]
    assert bus.published_count == 1


def test_handler_failure_is_isolated():
    bus = EventBus()
    seen: list[int] = []

    def failing_handler(event: Event) -> None:
        raise RuntimeError("boom")

    bus.subscribe("T", failing_handler)
    bus.subscribe("T", lambda event: seen.append(1))
    bus.publish(Event("T"))
    assert seen == [1]
    assert bus.failed_count == 1


def test_unsubscribe_removes_handler():
    bus = EventBus()
    seen: list[int] = []
    handler = lambda event: seen.append(1)  # noqa: E731
    bus.subscribe("T", handler)
    bus.unsubscribe("T", handler)
    bus.publish(Event("T"))
    assert seen == []
