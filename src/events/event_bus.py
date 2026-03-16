"""
FinClaw - Event Bus
Pub/sub event system for loose coupling between components.
Supports sync handlers, wildcard subscriptions, and event history.
"""

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Callable, Optional

logger = logging.getLogger(__name__)

# Standard event types
TRADE_EXECUTED = "trade_executed"
SIGNAL_GENERATED = "signal_generated"
ALERT_TRIGGERED = "alert_triggered"
REBALANCE_NEEDED = "rebalance_needed"
DRAWDOWN_EXCEEDED = "drawdown_exceeded"
REGIME_CHANGED = "regime_changed"

ALL_EVENTS = [
    TRADE_EXECUTED, SIGNAL_GENERATED, ALERT_TRIGGERED,
    REBALANCE_NEEDED, DRAWDOWN_EXCEEDED, REGIME_CHANGED,
]


@dataclass
class Event:
    """Immutable event payload."""
    event_type: str
    data: dict
    timestamp: float = field(default_factory=time.time)
    source: str = ""


class EventBus:
    """
    Simple synchronous pub/sub event bus.

    Usage:
        bus = EventBus()
        bus.subscribe('trade_executed', my_handler)
        bus.publish('trade_executed', {'ticker': 'AAPL', 'side': 'buy'})
    """

    def __init__(self, max_history: int = 1000):
        self._handlers: dict[str, list[Callable]] = defaultdict(list)
        self._history: list[Event] = []
        self._max_history = max_history

    def subscribe(self, event_type: str, handler: Callable) -> None:
        """Subscribe a handler to an event type. Use '*' for all events."""
        if handler not in self._handlers[event_type]:
            self._handlers[event_type].append(handler)
            logger.debug("Subscribed %s to '%s'", handler.__name__, event_type)

    def unsubscribe(self, event_type: str, handler: Callable) -> bool:
        """Remove a handler. Returns True if it was found."""
        try:
            self._handlers[event_type].remove(handler)
            return True
        except ValueError:
            return False

    def publish(self, event_type: str, data: dict, source: str = "") -> Event:
        """
        Publish an event. Calls all subscribed handlers synchronously.
        Also calls '*' (wildcard) handlers.
        Returns the Event object.
        """
        event = Event(event_type=event_type, data=data, source=source)
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        handlers = list(self._handlers.get(event_type, []))
        handlers += list(self._handlers.get("*", []))

        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error("Handler %s failed on '%s': %s", handler.__name__, event_type, e)

        return event

    def get_history(self, event_type: Optional[str] = None, limit: int = 50) -> list[Event]:
        """Get recent events, optionally filtered by type."""
        events = self._history
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        return events[-limit:]

    def clear(self) -> None:
        """Remove all handlers and history."""
        self._handlers.clear()
        self._history.clear()

    @property
    def handler_count(self) -> int:
        return sum(len(h) for h in self._handlers.values())
