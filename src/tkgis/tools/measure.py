"""Measurement tools — geodesic distance and area for tkgis MapCanvas."""
from __future__ import annotations

import math
from typing import TYPE_CHECKING

from tkgis.models.tools import BaseTool, ToolMode

if TYPE_CHECKING:
    from tkgis.canvas.map_canvas import MapCanvas
    from tkgis.crs.engine import CRSEngine, CRSLike


class DistanceTool(BaseTool):
    """Click to add vertices along a polyline, double-click to finish.

    Computes geodesic distance between consecutive vertices via
    :class:`CRSEngine` and accumulates a running total.
    """

    name = "measure_distance"
    mode = ToolMode.MEASURE_DISTANCE
    cursor = "crosshair"

    def __init__(
        self,
        crs_engine: CRSEngine,
        crs: CRSLike = 4326,
        map_canvas: MapCanvas | None = None,
    ) -> None:
        self._engine = crs_engine
        self._crs = crs
        self._canvas = map_canvas
        self._vertices: list[tuple[float, float]] = []
        self._segment_distances: list[float] = []
        self._total_distance: float = 0.0
        self._finished: bool = False
        self._canvas_items: list[int] = []

    # ------------------------------------------------------------------
    # Public read-only accessors
    # ------------------------------------------------------------------

    @property
    def vertices(self) -> list[tuple[float, float]]:
        """Return a copy of the current vertex list (map coordinates)."""
        return list(self._vertices)

    @property
    def segment_distances(self) -> list[float]:
        """Return geodesic distance of each segment in meters."""
        return list(self._segment_distances)

    @property
    def total_distance(self) -> float:
        """Total geodesic distance in meters."""
        return self._total_distance

    @property
    def finished(self) -> bool:
        return self._finished

    # ------------------------------------------------------------------
    # Tool handlers
    # ------------------------------------------------------------------

    def on_press(self, x: float, y: float, map_x: float, map_y: float) -> None:
        """Add a vertex.  If the measurement is finished, start a new one."""
        if self._finished:
            self.reset()

        self._vertices.append((map_x, map_y))

        if len(self._vertices) >= 2:
            prev = self._vertices[-2]
            cur = self._vertices[-1]
            seg = self._engine.compute_distance(
                prev[0], prev[1], cur[0], cur[1], self._crs,
            )
            self._segment_distances.append(seg)
            self._total_distance += seg

        self._draw_overlay()

    def on_drag(self, x: float, y: float, map_x: float, map_y: float) -> None:
        pass  # No drag behaviour for measurement

    def on_release(self, x: float, y: float, map_x: float, map_y: float) -> None:
        pass

    def on_key(self, key: str) -> None:
        """Finish on Enter/Return; cancel on Escape."""
        if key in ("Return", "KP_Enter"):
            self._finished = True
        elif key == "Escape":
            self.reset()

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

    def finish(self) -> None:
        """Programmatically finish the current measurement."""
        if len(self._vertices) >= 2:
            self._finished = True

    def reset(self) -> None:
        """Clear all vertices and accumulated distance."""
        self._vertices.clear()
        self._segment_distances.clear()
        self._total_distance = 0.0
        self._finished = False
        self._clear_overlay()

    # ------------------------------------------------------------------
    # Canvas overlay drawing
    # ------------------------------------------------------------------

    def _clear_overlay(self) -> None:
        if self._canvas is not None:
            self._canvas.delete("measure_distance")
        self._canvas_items.clear()

    def _draw_overlay(self) -> None:
        if self._canvas is None or len(self._vertices) < 1:
            return
        self._clear_overlay()

        view = self._canvas.view
        screen_pts = [view.map_to_screen(mx, my) for mx, my in self._vertices]

        # Draw lines between vertices
        if len(screen_pts) >= 2:
            flat = []
            for sx, sy in screen_pts:
                flat.extend([sx, sy])
            item = self._canvas.create_line(
                *flat,
                fill="#ff4444",
                width=2,
                tags=("measure_distance",),
            )
            self._canvas_items.append(item)

        # Draw vertex dots
        for sx, sy in screen_pts:
            item = self._canvas.create_oval(
                sx - 4, sy - 4, sx + 4, sy + 4,
                fill="#ff4444",
                outline="#ffffff",
                tags=("measure_distance",),
            )
            self._canvas_items.append(item)

        # Distance label at last vertex
        if self._total_distance > 0 and screen_pts:
            label = _format_distance(self._total_distance)
            sx, sy = screen_pts[-1]
            item = self._canvas.create_text(
                sx + 10, sy - 10,
                text=label,
                anchor="sw",
                fill="#ff4444",
                font=("TkDefaultFont", 10, "bold"),
                tags=("measure_distance",),
            )
            self._canvas_items.append(item)


class AreaTool(BaseTool):
    """Click to add polygon vertices, double-click/Enter to close and compute area.

    Computes geodesic area via :class:`CRSEngine`.
    """

    name = "measure_area"
    mode = ToolMode.MEASURE_AREA
    cursor = "crosshair"

    def __init__(
        self,
        crs_engine: CRSEngine,
        crs: CRSLike = 4326,
        map_canvas: MapCanvas | None = None,
    ) -> None:
        self._engine = crs_engine
        self._crs = crs
        self._canvas = map_canvas
        self._vertices: list[tuple[float, float]] = []
        self._total_area: float = 0.0
        self._perimeter: float = 0.0
        self._finished: bool = False
        self._canvas_items: list[int] = []

    # ------------------------------------------------------------------
    # Public read-only accessors
    # ------------------------------------------------------------------

    @property
    def vertices(self) -> list[tuple[float, float]]:
        return list(self._vertices)

    @property
    def total_area(self) -> float:
        """Geodesic area in square meters."""
        return self._total_area

    @property
    def perimeter(self) -> float:
        """Perimeter in meters (sum of geodesic segment lengths)."""
        return self._perimeter

    @property
    def finished(self) -> bool:
        return self._finished

    # ------------------------------------------------------------------
    # Tool handlers
    # ------------------------------------------------------------------

    def on_press(self, x: float, y: float, map_x: float, map_y: float) -> None:
        if self._finished:
            self.reset()

        self._vertices.append((map_x, map_y))
        self._draw_overlay()

    def on_drag(self, x: float, y: float, map_x: float, map_y: float) -> None:
        pass

    def on_release(self, x: float, y: float, map_x: float, map_y: float) -> None:
        pass

    def on_key(self, key: str) -> None:
        if key in ("Return", "KP_Enter"):
            self.finish()
        elif key == "Escape":
            self.reset()

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

    def finish(self) -> None:
        """Close the polygon and compute geodesic area."""
        if len(self._vertices) < 3:
            return
        self._total_area = self._engine.compute_area(self._vertices, self._crs)
        # Compute perimeter
        self._perimeter = 0.0
        verts = self._vertices + [self._vertices[0]]  # close the ring
        for i in range(len(verts) - 1):
            seg = self._engine.compute_distance(
                verts[i][0], verts[i][1],
                verts[i + 1][0], verts[i + 1][1],
                self._crs,
            )
            self._perimeter += seg
        self._finished = True
        self._draw_overlay()

    def reset(self) -> None:
        self._vertices.clear()
        self._total_area = 0.0
        self._perimeter = 0.0
        self._finished = False
        self._clear_overlay()

    # ------------------------------------------------------------------
    # Canvas overlay drawing
    # ------------------------------------------------------------------

    def _clear_overlay(self) -> None:
        if self._canvas is not None:
            self._canvas.delete("measure_area")
        self._canvas_items.clear()

    def _draw_overlay(self) -> None:
        if self._canvas is None or len(self._vertices) < 1:
            return
        self._clear_overlay()

        view = self._canvas.view
        screen_pts = [view.map_to_screen(mx, my) for mx, my in self._vertices]

        # Draw filled polygon when closed
        if self._finished and len(screen_pts) >= 3:
            flat = []
            for sx, sy in screen_pts:
                flat.extend([sx, sy])
            item = self._canvas.create_polygon(
                *flat,
                fill="#4488ff",
                stipple="gray25",
                outline="#4488ff",
                width=2,
                tags=("measure_area",),
            )
            self._canvas_items.append(item)
        elif len(screen_pts) >= 2:
            # Draw open polyline while sketching
            flat = []
            for sx, sy in screen_pts:
                flat.extend([sx, sy])
            item = self._canvas.create_line(
                *flat,
                fill="#4488ff",
                width=2,
                tags=("measure_area",),
            )
            self._canvas_items.append(item)

        # Vertex dots
        for sx, sy in screen_pts:
            item = self._canvas.create_oval(
                sx - 4, sy - 4, sx + 4, sy + 4,
                fill="#4488ff",
                outline="#ffffff",
                tags=("measure_area",),
            )
            self._canvas_items.append(item)

        # Area label at centroid
        if self._finished and self._total_area > 0:
            cx = sum(s[0] for s in screen_pts) / len(screen_pts)
            cy = sum(s[1] for s in screen_pts) / len(screen_pts)
            label = _format_area(self._total_area)
            item = self._canvas.create_text(
                cx, cy,
                text=label,
                anchor="center",
                fill="#4488ff",
                font=("TkDefaultFont", 10, "bold"),
                tags=("measure_area",),
            )
            self._canvas_items.append(item)


# ------------------------------------------------------------------
# Formatting helpers
# ------------------------------------------------------------------

def _format_distance(meters: float) -> str:
    """Format a distance in meters to a human-readable string."""
    if meters >= 1000.0:
        return f"{meters / 1000.0:.3f} km"
    return f"{meters:.2f} m"


def _format_area(sq_meters: float) -> str:
    """Format an area in square meters to a human-readable string."""
    if sq_meters >= 1e6:
        return f"{sq_meters / 1e6:.3f} km\u00b2"
    return f"{sq_meters:.1f} m\u00b2"
