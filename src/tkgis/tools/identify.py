"""Identify tool — click to query features at a map location."""
from __future__ import annotations

from typing import Any, TYPE_CHECKING

from tkgis.models.tools import BaseTool, ToolMode

if TYPE_CHECKING:
    from tkgis.canvas.map_canvas import MapCanvas
    from tkgis.models.events import EventBus
    from tkgis.models.layers import Layer


class IdentifyResult:
    """Container for features identified at a click location."""

    def __init__(
        self,
        map_x: float,
        map_y: float,
        results: dict[str, list[dict[str, Any]]] | None = None,
    ) -> None:
        self.map_x = map_x
        self.map_y = map_y
        # Keyed by layer id -> list of feature attribute dicts
        self.results: dict[str, list[dict[str, Any]]] = results or {}

    @property
    def total_features(self) -> int:
        return sum(len(v) for v in self.results.values())

    def __repr__(self) -> str:
        return (
            f"IdentifyResult(x={self.map_x:.4f}, y={self.map_y:.4f}, "
            f"features={self.total_features})"
        )


class IdentifyTool(BaseTool):
    """Click on the map to query all visible layers at that point.

    The tool stores the most recent :class:`IdentifyResult` on
    :attr:`last_result`.  An optional *query_callback* is invoked on
    each click so the host application can perform the actual spatial
    query (the tool itself is layer-backend agnostic).

    Parameters
    ----------
    query_callback:
        ``(map_x, map_y, layers) -> dict[layer_id, list[feature_dict]]``.
        When ``None``, no query is performed and :attr:`last_result` will
        contain an empty result.
    layers:
        Callable returning the current list of visible layers.
    map_canvas:
        Optional reference for cursor management and overlay drawing.
    """

    name = "identify"
    mode = ToolMode.IDENTIFY
    cursor = "question_arrow"

    def __init__(
        self,
        query_callback: Any | None = None,
        layers: Any | None = None,
        map_canvas: MapCanvas | None = None,
    ) -> None:
        self._query_callback = query_callback
        self._layers = layers  # callable returning list[Layer]
        self._canvas = map_canvas
        self._last_result: IdentifyResult | None = None
        self._canvas_items: list[int] = []

    @property
    def last_result(self) -> IdentifyResult | None:
        """Most recent identify result, or ``None`` if nothing queried yet."""
        return self._last_result

    # ------------------------------------------------------------------
    # Tool handlers
    # ------------------------------------------------------------------

    def on_press(self, x: float, y: float, map_x: float, map_y: float) -> None:
        results: dict[str, list[dict[str, Any]]] = {}

        if self._query_callback is not None:
            layers = self._layers() if callable(self._layers) else (self._layers or [])
            results = self._query_callback(map_x, map_y, layers)

        self._last_result = IdentifyResult(map_x, map_y, results)
        self._draw_marker(x, y)

    def on_drag(self, x: float, y: float, map_x: float, map_y: float) -> None:
        pass

    def on_release(self, x: float, y: float, map_x: float, map_y: float) -> None:
        pass

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def activate(self) -> None:
        if self._canvas is not None:
            self._canvas.config(cursor=self.cursor)

    def deactivate(self) -> None:
        self._clear_overlay()
        if self._canvas is not None:
            self._canvas.config(cursor="arrow")

    def reset(self) -> None:
        """Clear the last result and any overlay."""
        self._last_result = None
        self._clear_overlay()

    # ------------------------------------------------------------------
    # Overlay
    # ------------------------------------------------------------------

    def _clear_overlay(self) -> None:
        if self._canvas is not None:
            self._canvas.delete("identify")
        self._canvas_items.clear()

    def _draw_marker(self, sx: float, sy: float) -> None:
        """Draw a small crosshair at the identify location."""
        if self._canvas is None:
            return
        self._clear_overlay()
        r = 8
        items = [
            self._canvas.create_line(
                sx - r, sy, sx + r, sy,
                fill="#ffcc00", width=2, tags=("identify",),
            ),
            self._canvas.create_line(
                sx, sy - r, sx, sy + r,
                fill="#ffcc00", width=2, tags=("identify",),
            ),
            self._canvas.create_oval(
                sx - r, sy - r, sx + r, sy + r,
                outline="#ffcc00", width=2, tags=("identify",),
            ),
        ]
        self._canvas_items.extend(items)
