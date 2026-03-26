"""EventBus and EventType for decoupled publish-subscribe messaging."""
from __future__ import annotations

import logging
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


class EventBus:
    """Simple synchronous publish-subscribe event bus.

    GUI layers subscribe to domain events and react without tight coupling.
    """

    def __init__(self) -> None:
        self._subscribers: dict[EventType, list[Callable[..., Any]]] = defaultdict(list)

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
        for callback in self._subscribers.get(event_type, []):
            try:
                callback(**kwargs)
            except Exception:
                logger.exception(
                    "Error in event handler for %s", event_type.value
                )
