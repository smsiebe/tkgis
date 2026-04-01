"""EventBus and EventType for decoupled publish-subscribe messaging."""
from __future__ import annotations

import logging
import time
from collections import defaultdict
from enum import Enum
from typing import Any, Callable

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Events emitted by the domain model layer."""

    LAYER_ADDED = "layer_added"
    LAYER_REMOVED = "layer_removed"
    LAYER_VISIBILITY_CHANGED = "layer_visibility_changed"
    LAYER_STYLE_CHANGED = "layer_style_changed"
    LAYER_ORDER_CHANGED = "layer_order_changed"
    LAYER_SELECTED = "layer_selected"
    PROJECT_LOADED = "project_loaded"
    PROJECT_SAVED = "project_saved"
    PROJECT_MODIFIED = "project_modified"
    VIEW_CHANGED = "view_changed"
    CRS_CHANGED = "crs_changed"
    TOOL_CHANGED = "tool_changed"
    PROGRESS_UPDATED = "progress_updated"
    TIME_STEP_CHANGED = "time_step_changed"
    ALL = "all"  # Wildcard event for debugging


class EventBus:
    """Simple synchronous publish-subscribe event bus.

    GUI layers subscribe to domain events and react without tight coupling.
    """

    def __init__(self) -> None:
        self._subscribers: dict[EventType, list[Callable[..., Any]]] = defaultdict(list)
        self._invoke_later: Callable[[Callable[[], None]], None] | None = None

    def set_invoke_later(self, invoke_later: Callable[[Callable[[], None]], None]) -> None:
        """Register a function to execute callbacks on the main GUI thread."""
        self._invoke_later = invoke_later

    def subscribe(self, event_type: EventType, callback: Callable[..., Any]) -> None:
        """Register *callback* to be called when *event_type* is emitted."""
        if callback not in self._subscribers[event_type]:
            self._subscribers[event_type].append(callback)

    def unsubscribe(self, event_type: EventType, callback: Callable[..., Any]) -> None:
        """Remove *callback* from the subscriber list for *event_type*."""
        try:
            self._subscribers[event_type].remove(callback)
        except ValueError:
            pass  # Silently ignore if not subscribed

    def emit(self, event_type: EventType, **kwargs: Any) -> None:
        """Invoke all subscribers for *event_type* with the given keyword args."""
        callbacks = list(self._subscribers.get(event_type, []))
        if event_type != EventType.ALL:
            callbacks.extend(self._subscribers.get(EventType.ALL, []))

        for callback in callbacks:
            t0 = time.perf_counter()
            try:
                if event_type == EventType.ALL:
                    callback(event_type=event_type, **kwargs)
                else:
                    callback(**kwargs)
            except Exception:
                logger.exception("Error in event handler for %s", event_type.value)
            finally:
                t1 = time.perf_counter()
                elapsed_ms = (t1 - t0) * 1000.0
                if elapsed_ms > 50:
                    logger.warning(
                        "Slow event handler for %s: %s took %.1f ms",
                        event_type.value,
                        callback.__name__ if hasattr(callback, "__name__") else repr(callback),
                        elapsed_ms,
                    )

    def thread_safe_emit(self, event_type: EventType, **kwargs: Any) -> None:
        """Emit an event safely from a background thread."""
        if self._invoke_later is not None:
            self._invoke_later(lambda: self.emit(event_type, **kwargs))
        else:
            logger.warning("No invoke_later configured; thread_safe_emit falling back to emit")
            self.emit(event_type, **kwargs)
