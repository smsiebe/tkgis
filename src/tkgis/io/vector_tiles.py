"""Vector tile provider — rasterizes vector features into map tiles."""
from __future__ import annotations

import logging
import math
from typing import TYPE_CHECKING

import numpy as np
from PIL import Image, ImageDraw
from shapely.geometry import box

from tkgis.canvas.tiles import TileProvider
from tkgis.io.vector import VectorLayerData
from tkgis.models.geometry import BoundingBox

if TYPE_CHECKING:
    from tkgis.canvas.transform import ViewTransform
    from tkgis.models.layers import Layer, LayerStyle

logger = logging.getLogger(__name__)

# Web Mercator constants
_EARTH_CIRCUMFERENCE = 2 * math.pi * 6378137  # meters


def _tile_bounds_epsg4326(zoom: int, row: int, col: int) -> BoundingBox:
    """Return the EPSG:4326 bounding box of a slippy-map tile."""
    n = 2 ** zoom
    lon_min = col / n * 360.0 - 180.0
    lon_max = (col + 1) / n * 360.0 - 180.0
    lat_max = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * row / n))))
    lat_min = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (row + 1) / n))))
    return BoundingBox(xmin=lon_min, ymin=lat_min, xmax=lon_max, ymax=lat_max, crs="EPSG:4326")


def _parse_color(color_str: str | None, default: tuple[int, ...]) -> tuple[int, ...]:
    """Parse a CSS-style hex color string to an RGBA tuple."""
    if color_str is None:
        return default
    color_str = color_str.strip().lstrip("#")
    if len(color_str) == 6:
        r, g, b = int(color_str[0:2], 16), int(color_str[2:4], 16), int(color_str[4:6], 16)
        return (r, g, b, 255)
    if len(color_str) == 8:
        r, g, b, a = (
            int(color_str[0:2], 16),
            int(color_str[2:4], 16),
            int(color_str[4:6], 16),
            int(color_str[6:8], 16),
        )
        return (r, g, b, a)
    return default


class VectorTileProvider(TileProvider):
    """Rasterizes vector features into RGBA tile arrays using PIL.

    Each tile is rendered by:
    1. Computing the geographic extent of the tile.
    2. Querying features that intersect the tile bbox.
    3. Transforming feature coordinates to pixel space.
    4. Drawing with PIL.ImageDraw.
    """

    def __init__(
        self,
        vector_data: VectorLayerData,
        style: LayerStyle | None = None,
        transform: ViewTransform | None = None,
        max_zoom: int = 18,
    ) -> None:
        self._vector_data = vector_data
        self._style = style
        self._transform = transform
        self._max_zoom = max_zoom

    # ------------------------------------------------------------------
    # TileProvider interface
    # ------------------------------------------------------------------

    def get_tile(
        self,
        layer: Layer,
        zoom_level: int,
        row: int,
        col: int,
        tile_size: int = 256,
    ) -> np.ndarray | None:
        """Render vector features into an RGBA tile array."""
        tile_bbox = _tile_bounds_epsg4326(zoom_level, row, col)

        # Ensure vector data is in EPSG:4326 for tile math
        vdata = self._vector_data
        if vdata.gdf.crs is not None:
            epsg = vdata.gdf.crs.to_epsg()
            if epsg is not None and epsg != 4326:
                vdata = vdata.reproject(4326)

        features = vdata.get_features_in_bbox(tile_bbox)
        if features.empty:
            return None

        # Create transparent RGBA image
        img = Image.new("RGBA", (tile_size, tile_size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        style = self._style or (layer.style if layer else None)
        fill_color = _parse_color(
            style.fill_color if style else None,
            (70, 130, 180, 128),
        )
        stroke_color = _parse_color(
            style.stroke_color if style else None,
            (0, 0, 0, 255),
        )
        stroke_width = int(style.stroke_width) if style else 1

        dx = tile_bbox.xmax - tile_bbox.xmin
        dy = tile_bbox.ymax - tile_bbox.ymin
        if dx == 0 or dy == 0:
            return None

        def to_pixel(x: float, y: float) -> tuple[float, float]:
            px = (x - tile_bbox.xmin) / dx * tile_size
            py = (1.0 - (y - tile_bbox.ymin) / dy) * tile_size
            return px, py

        for _, feat in features.iterrows():
            geom = feat.geometry
            if geom is None or geom.is_empty:
                continue
            gtype = geom.geom_type

            if gtype == "Point":
                px, py = to_pixel(geom.x, geom.y)
                r = max(3, stroke_width + 1)
                draw.ellipse(
                    [px - r, py - r, px + r, py + r],
                    fill=fill_color,
                    outline=stroke_color,
                    width=stroke_width,
                )
            elif gtype == "MultiPoint":
                for pt in geom.geoms:
                    px, py = to_pixel(pt.x, pt.y)
                    r = max(3, stroke_width + 1)
                    draw.ellipse(
                        [px - r, py - r, px + r, py + r],
                        fill=fill_color,
                        outline=stroke_color,
                        width=stroke_width,
                    )
            elif gtype in ("LineString",):
                coords = [to_pixel(x, y) for x, y in geom.coords]
                if len(coords) >= 2:
                    draw.line(coords, fill=stroke_color, width=stroke_width)
            elif gtype == "MultiLineString":
                for line in geom.geoms:
                    coords = [to_pixel(x, y) for x, y in line.coords]
                    if len(coords) >= 2:
                        draw.line(coords, fill=stroke_color, width=stroke_width)
            elif gtype == "Polygon":
                exterior = [to_pixel(x, y) for x, y in geom.exterior.coords]
                if len(exterior) >= 3:
                    draw.polygon(exterior, fill=fill_color, outline=stroke_color)
            elif gtype == "MultiPolygon":
                for poly in geom.geoms:
                    exterior = [to_pixel(x, y) for x, y in poly.exterior.coords]
                    if len(exterior) >= 3:
                        draw.polygon(exterior, fill=fill_color, outline=stroke_color)

        return np.array(img, dtype=np.uint8)

    def get_num_zoom_levels(self, layer: Layer) -> int:
        """Return the maximum number of zoom levels."""
        return self._max_zoom + 1

    def get_tile_grid(self, layer: Layer, zoom_level: int) -> tuple[int, int]:
        """Return (num_rows, num_cols) for a slippy-map tile grid."""
        n = 2 ** zoom_level
        return (n, n)
