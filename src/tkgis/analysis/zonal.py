"""Zonal statistics — summarize raster values within vector zones."""
from __future__ import annotations

import logging
from typing import Sequence

import geopandas as gpd
import numpy as np
from shapely.geometry import box, mapping

logger = logging.getLogger(__name__)


class ZonalStatistics:
    """Compute raster statistics for each polygon zone in a vector dataset."""

    def compute(
        self,
        raster_data: np.ndarray,
        vector_zones: gpd.GeoDataFrame,
        stats: Sequence[str] = ("mean", "std", "min", "max", "count"),
        *,
        transform: tuple[float, float, float, float] | None = None,
    ) -> gpd.GeoDataFrame:
        """Compute zonal statistics.

        Parameters
        ----------
        raster_data:
            2-D NumPy array of raster values.
        vector_zones:
            A :class:`GeoDataFrame` where each row is a polygon zone.
        stats:
            Statistic names to compute.  Supported:
            ``mean``, ``std``, ``min``, ``max``, ``count``, ``sum``, ``median``.
        transform:
            Optional affine-like tuple ``(x_origin, y_origin, pixel_width, pixel_height)``
            mapping pixel coordinates to the vector CRS.  If ``None`` a simple
            identity mapping is assumed (pixel coords = spatial coords).

        Returns
        -------
        gpd.GeoDataFrame
            Copy of *vector_zones* with additional columns for each stat.
        """
        raster_data = np.asarray(raster_data, dtype=np.float64)
        n_rows, n_cols = raster_data.shape

        if transform is not None:
            x0, y0, pw, ph = transform
        else:
            x0, y0, pw, ph = 0.0, 0.0, 1.0, 1.0

        result = vector_zones.copy()
        for stat_name in stats:
            result[stat_name] = np.nan

        for idx in result.index:
            geom = result.loc[idx, "geometry"]
            if geom is None or geom.is_empty:
                continue

            # Determine the pixel window that overlaps this geometry's bounds
            gxmin, gymin, gxmax, gymax = geom.bounds

            # Convert spatial bounds to pixel indices
            col_min = max(0, int(np.floor((gxmin - x0) / pw)))
            col_max = min(n_cols - 1, int(np.floor((gxmax - x0) / pw)))
            row_min = max(0, int(np.floor((gymin - y0) / ph)))
            row_max = min(n_rows - 1, int(np.floor((gymax - y0) / ph)))

            # Gather pixel values whose center falls inside the polygon
            from shapely.geometry import Point

            values: list[float] = []
            for r in range(row_min, row_max + 1):
                for c in range(col_min, col_max + 1):
                    px = x0 + (c + 0.5) * pw
                    py = y0 + (r + 0.5) * ph
                    if geom.contains(Point(px, py)):
                        val = raster_data[r, c]
                        if not np.isnan(val):
                            values.append(val)

            if not values:
                continue

            arr = np.array(values, dtype=np.float64)
            stat_funcs = {
                "mean": np.mean,
                "std": lambda a: np.std(a, ddof=0),
                "min": np.min,
                "max": np.max,
                "count": lambda a: float(len(a)),
                "sum": np.sum,
                "median": np.median,
            }
            for stat_name in stats:
                func = stat_funcs.get(stat_name)
                if func is not None:
                    result.at[idx, stat_name] = float(func(arr))

        return result
