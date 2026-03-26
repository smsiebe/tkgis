"""Screen-to-map coordinate transform for the tkgis map canvas."""
from __future__ import annotations

from tkgis.models.geometry import BoundingBox


class ViewTransform:
    """Bidirectional screen/map coordinate conversion.

    Screen coordinates: origin at top-left, Y increases downward.
    Map coordinates: origin at lower-left, Y increases upward (projected CRS).

    The transform is defined by:
    - ``center_x``, ``center_y`` — map coordinates of canvas center
    - ``scale`` — map units per screen pixel
    - ``canvas_width``, ``canvas_height`` — pixel dimensions of the canvas
    """

    def __init__(
        self,
        center_x: float = 0.0,
        center_y: float = 0.0,
        scale: float = 1.0,
        canvas_width: int = 800,
        canvas_height: int = 600,
    ) -> None:
        self.center_x = center_x
        self.center_y = center_y
        self.scale = scale
        self.canvas_width = canvas_width
        self.canvas_height = canvas_height

    # ------------------------------------------------------------------
    # Coordinate conversion
    # ------------------------------------------------------------------

    def screen_to_map(self, sx: float, sy: float) -> tuple[float, float]:
        """Convert screen pixel (sx, sy) to map coordinates."""
        mx = self.center_x + (sx - self.canvas_width / 2.0) * self.scale
        my = self.center_y - (sy - self.canvas_height / 2.0) * self.scale
        return mx, my

    def map_to_screen(self, mx: float, my: float) -> tuple[float, float]:
        """Convert map coordinates (mx, my) to screen pixel."""
        sx = (mx - self.center_x) / self.scale + self.canvas_width / 2.0
        sy = -(my - self.center_y) / self.scale + self.canvas_height / 2.0
        return sx, sy

    # ------------------------------------------------------------------
    # Visible extent
    # ------------------------------------------------------------------

    def get_visible_extent(self) -> BoundingBox:
        """Return the map-space bounding box currently visible on screen."""
        half_w = (self.canvas_width / 2.0) * self.scale
        half_h = (self.canvas_height / 2.0) * self.scale
        return BoundingBox(
            xmin=self.center_x - half_w,
            ymin=self.center_y - half_h,
            xmax=self.center_x + half_w,
            ymax=self.center_y + half_h,
        )

    # ------------------------------------------------------------------
    # View manipulation
    # ------------------------------------------------------------------

    def zoom(self, factor: float, anchor_sx: float, anchor_sy: float) -> None:
        """Zoom by *factor* centred on the screen point (*anchor_sx*, *anchor_sy*).

        factor < 1 zooms in (less map per pixel), factor > 1 zooms out.
        """
        # Map point under the anchor before zoom
        mx, my = self.screen_to_map(anchor_sx, anchor_sy)

        self.scale *= factor

        # After changing scale the anchor must still map to the same map point.
        # new_mx = center_x + (anchor_sx - w/2) * new_scale
        # We want new_mx == mx, so solve for center_x.
        self.center_x = mx - (anchor_sx - self.canvas_width / 2.0) * self.scale
        self.center_y = my + (anchor_sy - self.canvas_height / 2.0) * self.scale

    def pan(self, dx_screen: float, dy_screen: float) -> None:
        """Pan the view by a screen-space delta.

        Positive *dx_screen* moves the view to the right (map shifts left),
        positive *dy_screen* moves the view downward (map shifts up).
        """
        self.center_x -= dx_screen * self.scale
        self.center_y += dy_screen * self.scale

    def fit_extent(self, bbox: BoundingBox) -> None:
        """Adjust center and scale so that *bbox* fills the canvas."""
        self.center_x, self.center_y = bbox.center

        if self.canvas_width <= 0 or self.canvas_height <= 0:
            return

        scale_x = bbox.width / self.canvas_width
        scale_y = bbox.height / self.canvas_height
        self.scale = max(scale_x, scale_y) if max(scale_x, scale_y) > 0 else 1.0

    def resize(self, new_width: int, new_height: int) -> None:
        """Update canvas dimensions (e.g. after a window resize)."""
        self.canvas_width = new_width
        self.canvas_height = new_height
