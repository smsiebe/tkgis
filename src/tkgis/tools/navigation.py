"""Navigation tools — pan, zoom-in, zoom-out for tkgis MapCanvas."""
from __future__ import annotations

from typing import TYPE_CHECKING

from tkgis.models.tools import BaseTool, ToolMode

if TYPE_CHECKING:
    from tkgis.canvas.map_canvas import MapCanvas

_ZOOM_FACTOR = 1.2


class PanTool(BaseTool):
    """Click-and-drag panning tool.

    Dragging translates the view so the map follows the cursor.
    """

    name = "pan"
    mode = ToolMode.PAN
    cursor = "fleur"

    def __init__(self, map_canvas: MapCanvas | None = None) -> None:
        self._canvas = map_canvas
        self._last_x: float = 0.0
        self._last_y: float = 0.0

    def on_press(self, x: float, y: float, map_x: float, map_y: float) -> None:
        self._last_x = x
        self._last_y = y

    def on_drag(self, x: float, y: float, map_x: float, map_y: float) -> None:
        if self._canvas is None:
            return
        dx = x - self._last_x
        dy = y - self._last_y
        self._canvas.view.pan(dx, dy)
        self._last_x = x
        self._last_y = y
        self._canvas.refresh()

    def on_release(self, x: float, y: float, map_x: float, map_y: float) -> None:
        pass

    def activate(self) -> None:
        if self._canvas is not None:
            self._canvas.config(cursor=self.cursor)

    def deactivate(self) -> None:
        if self._canvas is not None:
            self._canvas.config(cursor="arrow")


class ZoomInTool(BaseTool):
    """Click to zoom in, centred on the click location."""

    name = "zoom_in"
    mode = ToolMode.ZOOM_IN
    cursor = "plus"

    def __init__(self, map_canvas: MapCanvas | None = None) -> None:
        self._canvas = map_canvas

    def on_press(self, x: float, y: float, map_x: float, map_y: float) -> None:
        if self._canvas is None:
            return
        self._canvas.view.zoom(1.0 / _ZOOM_FACTOR, x, y)
        self._canvas.refresh()

    def on_drag(self, x: float, y: float, map_x: float, map_y: float) -> None:
        pass

    def on_release(self, x: float, y: float, map_x: float, map_y: float) -> None:
        pass

    def activate(self) -> None:
        if self._canvas is not None:
            self._canvas.config(cursor=self.cursor)

    def deactivate(self) -> None:
        if self._canvas is not None:
            self._canvas.config(cursor="arrow")


class ZoomOutTool(BaseTool):
    """Click to zoom out, centred on the click location."""

    name = "zoom_out"
    mode = ToolMode.ZOOM_OUT
    cursor = "minus"

    def __init__(self, map_canvas: MapCanvas | None = None) -> None:
        self._canvas = map_canvas

    def on_press(self, x: float, y: float, map_x: float, map_y: float) -> None:
        if self._canvas is None:
            return
        self._canvas.view.zoom(_ZOOM_FACTOR, x, y)
        self._canvas.refresh()

    def on_drag(self, x: float, y: float, map_x: float, map_y: float) -> None:
        pass

    def on_release(self, x: float, y: float, map_x: float, map_y: float) -> None:
        pass

    def activate(self) -> None:
        if self._canvas is not None:
            self._canvas.config(cursor=self.cursor)

    def deactivate(self) -> None:
        if self._canvas is not None:
            self._canvas.config(cursor="arrow")
