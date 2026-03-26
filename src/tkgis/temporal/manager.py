"""TemporalLayerManager — coordinates temporal state across layers."""
from __future__ import annotations

import bisect
import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from tkgis.models.events import EventType

if TYPE_CHECKING:
    from tkgis.models.events import EventBus
    from tkgis.models.layers import Layer

logger = logging.getLogger(__name__)


def _parse_iso(s: str) -> datetime:
    """Parse an ISO 8601 string to a datetime."""
    return datetime.fromisoformat(s)


class TemporalLayerManager:
    """Manages temporal state for layers and emits time-step events.

    Parameters
    ----------
    event_bus:
        The application event bus used to emit ``TIME_STEP_CHANGED``.
    """

    def __init__(self, event_bus: EventBus) -> None:
        self._event_bus = event_bus
        self._current_time: datetime | None = None
        self._time_window: timedelta | None = None

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def current_time(self) -> datetime | None:
        """The current global time cursor."""
        return self._current_time

    @property
    def time_window(self) -> timedelta | None:
        """Half-width of the active time window around *current_time*."""
        return self._time_window

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    def get_time_range(self, layer: Layer) -> tuple[datetime, datetime] | None:
        """Return ``(start, end)`` for a layer, or ``None`` if non-temporal."""
        if layer.time_start is None or layer.time_end is None:
            # Fall back to deriving from time_steps if available.
            steps = self.get_time_steps(layer)
            if not steps:
                return None
            return (steps[0], steps[-1])
        return (_parse_iso(layer.time_start), _parse_iso(layer.time_end))

    def get_time_steps(self, layer: Layer) -> list[datetime]:
        """Return the sorted list of discrete time steps for *layer*."""
        if layer.time_steps is None:
            return []
        return sorted(_parse_iso(s) for s in layer.time_steps)

    def get_nearest_step(self, layer: Layer, target: datetime) -> datetime:
        """Return the time step in *layer* closest to *target*.

        Raises
        ------
        ValueError
            If the layer has no time steps.
        """
        steps = self.get_time_steps(layer)
        if not steps:
            raise ValueError(f"Layer '{layer.name}' has no time steps")

        idx = bisect.bisect_left(steps, target)

        # Edge cases: target before first or after last step.
        if idx == 0:
            return steps[0]
        if idx >= len(steps):
            return steps[-1]

        # Compare the two candidates surrounding the insertion point.
        before = steps[idx - 1]
        after = steps[idx]
        if (target - before) <= (after - target):
            return before
        return after

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def set_current_time(self, t: datetime) -> None:
        """Set the global time cursor and emit ``TIME_STEP_CHANGED``."""
        self._current_time = t
        self._event_bus.emit(EventType.TIME_STEP_CHANGED, time=t)

    def set_time_window(self, window: timedelta) -> None:
        """Set the half-width of the active time window."""
        self._time_window = window

    # ------------------------------------------------------------------
    # Index lookup
    # ------------------------------------------------------------------

    def get_active_data_index(self, layer: Layer) -> int | None:
        """Return the index into *layer.time_steps* for the current time.

        Uses :meth:`get_nearest_step` to snap the global cursor to the
        closest discrete step, then returns its position.  Returns ``None``
        if the layer has no time steps or no current time is set.
        """
        if self._current_time is None:
            return None
        steps = self.get_time_steps(layer)
        if not steps:
            return None
        nearest = self.get_nearest_step(layer, self._current_time)
        return steps.index(nearest)
