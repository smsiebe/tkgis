"""Map interaction tool abstractions for tkgis."""
from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

from tkgis.models.events import EventBus, EventType


class ToolMode(Enum):
    """Available tool modes for map interaction."""

    PAN = "pan"
    ZOOM_IN = "zoom_in"
    ZOOM_OUT = "zoom_out"
    SELECT = "select"
    MEASURE_DISTANCE = "measure_distance"
    MEASURE_AREA = "measure_area"
    DRAW_POINT = "draw_point"
    DRAW_LINE = "draw_line"
    DRAW_POLYGON = "draw_polygon"
    IDENTIFY = "identify"


class BaseTool(ABC):
    """Abstract base class for map interaction tools.

    Subclasses must implement press/drag/release handlers.  Optional
    handlers (move, scroll, key) have no-op defaults.
    """

    name: str
    mode: ToolMode
    cursor: str = "arrow"

    @abstractmethod
    def on_press(self, x: float, y: float, map_x: float, map_y: float) -> None:
        """Called when the mouse button is pressed."""

    @abstractmethod
    def on_drag(self, x: float, y: float, map_x: float, map_y: float) -> None:
        """Called while the mouse is dragged."""

    @abstractmethod
    def on_release(self, x: float, y: float, map_x: float, map_y: float) -> None:
        """Called when the mouse button is released."""

    def on_move(self, x: float, y: float, map_x: float, map_y: float) -> None:
        """Called when the mouse moves (no button pressed)."""

    def on_scroll(self, x: float, y: float, delta: float) -> None:
        """Called on mouse scroll."""

    def on_key(self, key: str) -> None:
        """Called on key press."""

    def activate(self) -> None:
        """Called when the tool becomes the active tool."""

    def deactivate(self) -> None:
        """Called when the tool is replaced by another tool."""


class ToolManager:
    """Manages registration and activation of map interaction tools."""

    def __init__(self, event_bus: EventBus | None = None) -> None:
        self._tools: dict[str, BaseTool] = {}
        self._active: BaseTool | None = None
        self._event_bus = event_bus

    def register_tool(self, tool: BaseTool) -> None:
        """Register a tool by its *name* attribute."""
        self._tools[tool.name] = tool

    def set_active(self, tool_name: str) -> None:
        """Activate the tool identified by *tool_name*.

        Deactivates the currently active tool first, then emits
        ``TOOL_CHANGED`` if an event bus is available.
        """
        if tool_name not in self._tools:
            raise KeyError(f"Unknown tool: {tool_name!r}")

        if self._active is not None:
            self._active.deactivate()

        self._active = self._tools[tool_name]
        self._active.activate()

        if self._event_bus is not None:
            self._event_bus.emit(
                EventType.TOOL_CHANGED,
                tool_name=tool_name,
                tool=self._active,
            )

    def get_active(self) -> BaseTool | None:
        """Return the currently active tool, or ``None``."""
        return self._active
