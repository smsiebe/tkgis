"""Selection tool — click or drag-rectangle to select features."""
from __future__ import annotations

from typing import Any, TYPE_CHECKING

from tkgis.models.geometry import BoundingBox
from tkgis.models.tools import BaseTool, ToolMode

if TYPE_CHECKING:
    from tkgis.canvas.map_canvas import MapCanvas


class SelectTool(BaseTool):
    """Click to select the nearest feature; drag for rubber-band rectangle selection.

    The tool maintains a :attr:`selected_features` set of
    ``(layer_id, feature_id)`` tuples.  An optional *query_callback* is
    invoked to perform the actual spatial query; the tool itself is
    backend-agnostic.

    Parameters
    ----------
    query_callback:
        Called with ``(bbox, layers) -> list[(layer_id, feature_id)]``
        for rectangle selection, or
        ``(map_x, map_y, layers) -> list[(layer_id, feature_id)]``
        for point selection (when bbox is ``None``).
    layers:
        Callable returning the current list of visible layers.
    map_canvas:
        Optional reference for cursor management and rubber-band drawing.
    """

    name = "select"
    mode = ToolMode.SELECT
    cursor = "arrow"

    _CLICK_THRESHOLD_PX = 4  # max drag pixels to treat as a click

    def __init__(
        self,
        query_callback: Any | None = None,
        layers: Any | None = None,
        map_canvas: MapCanvas | None = None,
    ) -> None:
        self._query_callback = query_callback
        self._layers = layers
        self._canvas = map_canvas
        self._selected_features: set[tuple[str, Any]] = set()

        # Drag state
        self._press_sx: float = 0.0
        self._press_sy: float = 0.0
        self._press_mx: float = 0.0
        self._press_my: float = 0.0
        self._dragging: bool = False
        self._rect_item: int | None = None

    # ------------------------------------------------------------------
    # Public accessors
    # ------------------------------------------------------------------

    @property
    def selected_features(self) -> set[tuple[str, Any]]:
        """Set of (layer_id, feature_id) currently selected."""
        return set(self._selected_features)

    @property
    def selection_count(self) -> int:
        return len(self._selected_features)

    # ------------------------------------------------------------------
    # Tool handlers
    # ------------------------------------------------------------------

    def on_press(self, x: float, y: float, map_x: float, map_y: float) -> None:
        self._press_sx = x
        self._press_sy = y
        self._press_mx = map_x
        self._press_my = map_y
        self._dragging = False

    def on_drag(self, x: float, y: float, map_x: float, map_y: float) -> None:
        dx = abs(x - self._press_sx)
        dy = abs(y - self._press_sy)
        if dx > self._CLICK_THRESHOLD_PX or dy > self._CLICK_THRESHOLD_PX:
            self._dragging = True
            self._draw_rubber_band(self._press_sx, self._press_sy, x, y)

    def on_release(self, x: float, y: float, map_x: float, map_y: float) -> None:
        self._clear_rubber_band()

        if self._dragging:
            # Rectangle selection
            x_min = min(self._press_mx, map_x)
            y_min = min(self._press_my, map_y)
            x_max = max(self._press_mx, map_x)
            y_max = max(self._press_my, map_y)
            bbox = BoundingBox(xmin=x_min, ymin=y_min, xmax=x_max, ymax=y_max)
            self._do_rect_select(bbox)
        else:
            # Point (click) selection
            self._do_point_select(map_x, map_y)

        self._dragging = False

    def on_key(self, key: str) -> None:
        if key == "Escape":
            self.clear_selection()

    # ------------------------------------------------------------------
    # Selection logic
    # ------------------------------------------------------------------

    def _get_layers(self) -> list[Any]:
        if callable(self._layers):
            return self._layers()
        return self._layers or []

    def _do_point_select(self, map_x: float, map_y: float) -> None:
        if self._query_callback is None:
            return
        layers = self._get_layers()
        hits = self._query_callback(map_x, map_y, layers)
        self._selected_features = set(hits) if hits else set()

    def _do_rect_select(self, bbox: BoundingBox) -> None:
        if self._query_callback is None:
            return
        layers = self._get_layers()
        hits = self._query_callback(bbox, layers)
        self._selected_features = set(hits) if hits else set()

    def clear_selection(self) -> None:
        """Clear all selected features."""
        self._selected_features.clear()
        self._clear_rubber_band()

    def add_to_selection(self, layer_id: str, feature_id: Any) -> None:
        """Manually add a feature to the selection."""
        self._selected_features.add((layer_id, feature_id))

    def remove_from_selection(self, layer_id: str, feature_id: Any) -> None:
        """Manually remove a feature from the selection."""
        self._selected_features.discard((layer_id, feature_id))

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def activate(self) -> None:
        if self._canvas is not None:
            self._canvas.config(cursor=self.cursor)

    def deactivate(self) -> None:
        self._clear_rubber_band()
        if self._canvas is not None:
            self._canvas.config(cursor="arrow")

    # ------------------------------------------------------------------
    # Rubber-band overlay
    # ------------------------------------------------------------------

    def _draw_rubber_band(
        self, x0: float, y0: float, x1: float, y1: float,
    ) -> None:
        if self._canvas is None:
            return
        self._clear_rubber_band()
        self._rect_item = self._canvas.create_rectangle(
            x0, y0, x1, y1,
            outline="#00ccff",
            width=2,
            dash=(4, 4),
            tags=("select_rect",),
        )

    def _clear_rubber_band(self) -> None:
        if self._canvas is not None:
            self._canvas.delete("select_rect")
        self._rect_item = None
