"""CRS transformation engine backed by pyproj."""

from __future__ import annotations

from typing import Union

import numpy as np
from numpy import ndarray
import pyproj
from pyproj import Geod, Transformer

from tkgis.models.crs import CRSDefinition
from tkgis.models.geometry import BoundingBox

# Accepted CRS argument: either a CRSDefinition or a bare EPSG int.
CRSLike = Union[CRSDefinition, int]


def _resolve_crs(crs: CRSLike) -> pyproj.CRS:
    """Convert a *CRSLike* value to a ``pyproj.CRS``."""
    if isinstance(crs, int):
        return pyproj.CRS.from_epsg(crs)
    return crs.to_pyproj()


def _epsg_key(crs: CRSLike) -> int | str:
    """Return a hashable key for caching. Prefer EPSG code when available."""
    if isinstance(crs, int):
        return crs
    if crs.epsg_code is not None:
        return crs.epsg_code
    # Fall back to WKT or proj string for exotic CRS definitions.
    return crs.wkt or crs.proj_string or id(crs)


class CRSEngine:
    """Manages CRS transformations. Caches ``pyproj.Transformer`` instances."""

    def __init__(self) -> None:
        self._cache: dict[tuple, Transformer] = {}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_transformer(self, from_crs: CRSLike, to_crs: CRSLike) -> Transformer:
        key = (_epsg_key(from_crs), _epsg_key(to_crs))
        if key not in self._cache:
            src = _resolve_crs(from_crs)
            dst = _resolve_crs(to_crs)
            self._cache[key] = Transformer.from_crs(src, dst, always_xy=True)
        return self._cache[key]

    # ------------------------------------------------------------------
    # Point transforms
    # ------------------------------------------------------------------

    def transform_point(
        self, x: float, y: float, from_crs: CRSLike, to_crs: CRSLike
    ) -> tuple[float, float]:
        """Transform a single (x, y) point between two CRS."""
        t = self._get_transformer(from_crs, to_crs)
        rx, ry = t.transform(x, y)
        return (float(rx), float(ry))

    def transform_points(
        self,
        xs: ndarray,
        ys: ndarray,
        from_crs: CRSLike,
        to_crs: CRSLike,
    ) -> tuple[ndarray, ndarray]:
        """Transform arrays of coordinates between two CRS."""
        t = self._get_transformer(from_crs, to_crs)
        rx, ry = t.transform(xs, ys)
        return (np.asarray(rx), np.asarray(ry))

    # ------------------------------------------------------------------
    # BoundingBox transform
    # ------------------------------------------------------------------

    def transform_bbox(self, bbox: BoundingBox, to_crs: CRSLike) -> BoundingBox:
        """Reproject a *BoundingBox* into *to_crs*.

        Samples all four corners (and edge midpoints) for better accuracy
        with non-linear projections.
        """
        # Determine the source EPSG from the bbox.crs string ("EPSG:XXXX").
        from_epsg = int(bbox.crs.split(":")[1])

        # Build a dense sample along the bbox edges for accuracy.
        xs = [
            bbox.xmin, bbox.xmax, bbox.xmin, bbox.xmax,
            (bbox.xmin + bbox.xmax) / 2, (bbox.xmin + bbox.xmax) / 2,
            bbox.xmin, bbox.xmax,
        ]
        ys = [
            bbox.ymin, bbox.ymin, bbox.ymax, bbox.ymax,
            bbox.ymin, bbox.ymax,
            (bbox.ymin + bbox.ymax) / 2, (bbox.ymin + bbox.ymax) / 2,
        ]

        t = self._get_transformer(from_epsg, to_crs)
        tx, ty = t.transform(xs, ys)

        to_epsg = _epsg_key(to_crs)
        return BoundingBox(
            xmin=min(tx),
            ymin=min(ty),
            xmax=max(tx),
            ymax=max(ty),
            crs=f"EPSG:{to_epsg}",
        )

    # ------------------------------------------------------------------
    # CRS metadata
    # ------------------------------------------------------------------

    def get_units(self, crs: CRSLike) -> str:
        """Return the linear/angular unit name for *crs*."""
        c = _resolve_crs(crs)
        if c.is_geographic:
            return "degrees"
        axis_info = c.axis_info
        if axis_info:
            return axis_info[0].unit_name
        return "unknown"

    # ------------------------------------------------------------------
    # Scale / measurement
    # ------------------------------------------------------------------

    def compute_scale(self, transform: object, crs: CRSLike) -> float:
        """Compute approximate map scale denominator.

        *transform* must expose ``.pixel_width`` and ``.pixel_height``
        attributes (e.g. an affine transform from rasterio or similar).
        The returned value is the denominator of the representative
        fraction (1 : N), assuming a 96-DPI display.
        """
        DPI = 96
        METERS_PER_INCH = 0.0254
        pixel_m = DPI / METERS_PER_INCH  # pixels per meter on screen ≈ 3780

        pw = abs(getattr(transform, "pixel_width", getattr(transform, "a", 0)))
        ph = abs(getattr(transform, "pixel_height", getattr(transform, "e", 0)))
        avg_pixel = (pw + ph) / 2.0

        c = _resolve_crs(crs)
        if c.is_geographic:
            # Rough conversion: 1° ≈ 111_320 m at the equator.
            ground_m = avg_pixel * 111_320.0
        else:
            ground_m = avg_pixel  # already in meters (assumed)

        if ground_m == 0:
            return 0.0
        return ground_m * pixel_m

    def compute_distance(
        self, x1: float, y1: float, x2: float, y2: float, crs: CRSLike
    ) -> float:
        """Return geodesic distance in meters between two points.

        Points are given in the native units of *crs*; they are first
        reprojected to WGS 84 for geodesic computation.
        """
        lon1, lat1 = self.transform_point(x1, y1, crs, 4326)
        lon2, lat2 = self.transform_point(x2, y2, crs, 4326)
        geod = Geod(ellps="WGS84")
        _, _, dist = geod.inv(lon1, lat1, lon2, lat2)
        return float(dist)

    def compute_area(
        self, coords: list[tuple[float, float]], crs: CRSLike
    ) -> float:
        """Return geodesic area in square meters of a polygon.

        *coords* is a list of (x, y) vertices in *crs* coordinates.
        The polygon is automatically closed if necessary.
        """
        if len(coords) < 3:
            return 0.0

        # Reproject to WGS 84.
        xs = [c[0] for c in coords]
        ys = [c[1] for c in coords]
        lons, lats = self.transform_points(
            np.array(xs), np.array(ys), crs, 4326
        )
        geod = Geod(ellps="WGS84")
        area, _ = geod.polygon_area_perimeter(lons.tolist(), lats.tolist())
        return abs(float(area))
