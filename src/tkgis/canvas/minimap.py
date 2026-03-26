"""MiniMap — overview widget with view rectangle for tkgis."""
from __future__ import annotations

import tkinter as tk
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from tkgis.canvas.map_canvas import MapCanvas
    from tkgis.models.geometry import BoundingBox


class MiniMap(tk.Canvas):
    """Small overview widget (200x150) showing the full map extent.

    Draws a rectangle representing the current viewport of the main
    :class:`MapCanvas`.  Click to reposition the main view.
    """

    RECT_COLOR = "#ff4444"
    BG_COLOR = "#0f0f23"
    FILL_COLOR = "#1a1a2e"

    def __init__(
        self,
        parent: tk.Widget,
        map_canvas: MapCanvas,
        width: int = 200,
        height: int = 150,
        **kwargs: Any,
    ) -> None:
        kwargs.setdefault("bg", self.BG_COLOR)
        kwargs.setdefault("highlightthickness", 1)
        kwargs.setdefault("highlightbackground", "#333333")
        super().__init__(parent, width=width, height=height, **kwargs)

        self._map_canvas = map_canvas
        self._width = width
        self._height = height
        self._full_extent: BoundingBox | None = None

        self.bind("<ButtonPress-1>", self._on_click)
        self.bind("<B1-Motion>", self._on_click)

    def set_full_extent(self, bbox: BoundingBox) -> None:
        """Set the total extent that the minimap represents."""
        self._full_extent = bbox

    def update_view(self) -> None:
        """Redraw the minimap and the current viewport rectangle."""
        self.delete("all")

        if self._full_extent is None:
            return

        fe = self._full_extent
        if fe.width <= 0 or fe.height <= 0:
            return

        # Draw background fill representing the full extent
        self.create_rectangle(
            0, 0, self._width, self._height,
            fill=self.FILL_COLOR, outline="", tags=("bg",),
        )

        # Map main canvas viewport into minimap pixel space
        view = self._map_canvas.view
        visible = view.get_visible_extent()

        x0 = (visible.xmin - fe.xmin) / fe.width * self._width
        x1 = (visible.xmax - fe.xmin) / fe.width * self._width
        # Y is inverted (screen Y down)
        y0 = (fe.ymax - visible.ymax) / fe.height * self._height
        y1 = (fe.ymax - visible.ymin) / fe.height * self._height

        self.create_rectangle(
            x0, y0, x1, y1,
            outline=self.RECT_COLOR, width=2, tags=("viewport",),
        )

    def _on_click(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        """Recenter the main canvas on the clicked minimap location."""
        if self._full_extent is None:
            return

        fe = self._full_extent
        # Convert minimap pixel to map coordinate
        mx = fe.xmin + (event.x / self._width) * fe.width
        my = fe.ymax - (event.y / self._height) * fe.height

        self._map_canvas.view.center_x = mx
        self._map_canvas.view.center_y = my
        self._map_canvas.refresh()
        self.update_view()
