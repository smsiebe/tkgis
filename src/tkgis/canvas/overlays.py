"""Canvas overlay widgets — coordinate grid and scale bar."""
from __future__ import annotations

import math
import tkinter as tk
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from tkgis.canvas.transform import ViewTransform


def _nice_interval(raw: float) -> float:
    """Round *raw* to a 'nice' grid interval (1, 2, 5 × 10^n)."""
    if raw <= 0:
        return 1.0
    exponent = math.floor(math.log10(raw))
    fraction = raw / (10 ** exponent)
    if fraction < 1.5:
        nice = 1.0
    elif fraction < 3.5:
        nice = 2.0
    elif fraction < 7.5:
        nice = 5.0
    else:
        nice = 10.0
    return nice * (10 ** exponent)


class CoordinateGrid:
    """Draws a coordinate grid with labels on a tk.Canvas.

    Auto-selects spacing so there are roughly 4-8 grid lines per axis.
    Lines are drawn as thin semi-transparent gray strokes.
    """

    GRID_COLOR = "#555555"
    LABEL_COLOR = "#aaaaaa"
    LABEL_FONT = ("TkDefaultFont", 8)

    def draw(self, canvas: tk.Canvas, view: ViewTransform) -> None:
        """Render grid lines and edge labels on *canvas*."""
        canvas.delete("grid")
        extent = view.get_visible_extent()

        # Horizontal interval (X axis)
        x_interval = _nice_interval(extent.width / 6.0)
        y_interval = _nice_interval(extent.height / 6.0)

        if x_interval <= 0 or y_interval <= 0:
            return

        # Vertical lines (constant X)
        x_start = math.floor(extent.xmin / x_interval) * x_interval
        x = x_start
        while x <= extent.xmax:
            sx, _ = view.map_to_screen(x, 0)
            canvas.create_line(
                sx, 0, sx, view.canvas_height,
                fill=self.GRID_COLOR, dash=(2, 4), tags=("grid",),
            )
            # Label at top edge
            label = f"{x:.6g}"
            canvas.create_text(
                sx + 2, 2, text=label, anchor="nw",
                fill=self.LABEL_COLOR, font=self.LABEL_FONT, tags=("grid",),
            )
            x += x_interval

        # Horizontal lines (constant Y)
        y_start = math.floor(extent.ymin / y_interval) * y_interval
        y = y_start
        while y <= extent.ymax:
            _, sy = view.map_to_screen(0, y)
            canvas.create_line(
                0, sy, view.canvas_width, sy,
                fill=self.GRID_COLOR, dash=(2, 4), tags=("grid",),
            )
            # Label at left edge
            label = f"{y:.6g}"
            canvas.create_text(
                2, sy - 2, text=label, anchor="sw",
                fill=self.LABEL_COLOR, font=self.LABEL_FONT, tags=("grid",),
            )
            y += y_interval


class ScaleBar:
    """Draws an auto-adjusting scale bar in the bottom-left corner.

    Picks a round distance (100 m, 500 m, 1 km, 5 km, …) and renders
    a horizontal bar with a label.
    """

    BAR_COLOR = "#cccccc"
    LABEL_COLOR = "#cccccc"
    LABEL_FONT = ("TkDefaultFont", 9)
    MARGIN = 20
    BAR_HEIGHT = 6

    # Candidate bar widths in map units (meters / degrees)
    _NICE_DISTANCES = [
        0.00001, 0.00005, 0.0001, 0.0005, 0.001, 0.005,
        0.01, 0.05, 0.1, 0.5,
        1, 2, 5, 10, 20, 50,
        100, 200, 500, 1000, 2000, 5000,
        10_000, 20_000, 50_000, 100_000, 200_000, 500_000,
        1_000_000, 2_000_000, 5_000_000,
    ]

    def draw(self, canvas: tk.Canvas, view: ViewTransform, units: str = "meters") -> None:
        """Render the scale bar on *canvas*."""
        canvas.delete("scalebar")

        # Target bar length in pixels
        target_px = 120
        map_span = target_px * view.scale

        if map_span <= 0:
            return

        # Pick the largest nice distance that fits within map_span
        chosen = self._NICE_DISTANCES[0]
        for d in self._NICE_DISTANCES:
            if d <= map_span:
                chosen = d
            else:
                break

        bar_px = chosen / view.scale if view.scale > 0 else 0
        if bar_px < 5:
            return

        x0 = self.MARGIN
        y0 = view.canvas_height - self.MARGIN
        x1 = x0 + bar_px

        # Bar rectangle
        canvas.create_rectangle(
            x0, y0 - self.BAR_HEIGHT, x1, y0,
            fill=self.BAR_COLOR, outline=self.BAR_COLOR, tags=("scalebar",),
        )

        # Label
        label = self._format_distance(chosen, units)
        canvas.create_text(
            (x0 + x1) / 2, y0 - self.BAR_HEIGHT - 3,
            text=label, anchor="s",
            fill=self.LABEL_COLOR, font=self.LABEL_FONT, tags=("scalebar",),
        )

    @staticmethod
    def _format_distance(value: float, units: str) -> str:
        if units == "degrees":
            if value < 1:
                return f"{value * 60:.4g} arcmin"
            return f"{value:.4g} deg"
        # Assume meters
        if value >= 1000:
            return f"{value / 1000:.4g} km"
        if value >= 1:
            return f"{value:.4g} m"
        return f"{value * 100:.4g} cm"
