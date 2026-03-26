"""Spatial interpolation methods."""
from __future__ import annotations

import logging

import geopandas as gpd
import numpy as np

logger = logging.getLogger(__name__)


class SpatialInterpolator:
    """Interpolate scattered point data onto a regular grid."""

    def idw(
        self,
        points: gpd.GeoDataFrame,
        value_column: str,
        resolution: float,
        power: float = 2.0,
        *,
        bounds: tuple[float, float, float, float] | None = None,
    ) -> np.ndarray:
        """Inverse Distance Weighting interpolation.

        Parameters
        ----------
        points:
            A :class:`GeoDataFrame` with point geometries and a numeric
            attribute column.
        value_column:
            Name of the column in *points* containing the values to
            interpolate.
        resolution:
            Output cell size (in the units of the point CRS).
        power:
            Distance weighting exponent.  Higher values give more weight
            to the nearest neighbours.
        bounds:
            Optional ``(xmin, ymin, xmax, ymax)`` extent for the output
            grid.  Defaults to the bounding box of *points*.

        Returns
        -------
        np.ndarray
            2-D float64 array of interpolated values.
        """
        if value_column not in points.columns:
            raise ValueError(f"Column '{value_column}' not found in points")

        coords = np.array(
            [(geom.x, geom.y) for geom in points.geometry], dtype=np.float64
        )
        values = points[value_column].to_numpy(dtype=np.float64)

        if bounds is None:
            xmin, ymin, xmax, ymax = points.total_bounds
        else:
            xmin, ymin, xmax, ymax = bounds

        n_cols = max(1, int(np.ceil((xmax - xmin) / resolution)))
        n_rows = max(1, int(np.ceil((ymax - ymin) / resolution)))

        # Build grid of cell-center coordinates
        x_centers = xmin + (np.arange(n_cols) + 0.5) * resolution
        y_centers = ymin + (np.arange(n_rows) + 0.5) * resolution
        grid_x, grid_y = np.meshgrid(x_centers, y_centers)

        result = np.zeros((n_rows, n_cols), dtype=np.float64)

        for i in range(n_rows):
            for j in range(n_cols):
                dx = coords[:, 0] - grid_x[i, j]
                dy = coords[:, 1] - grid_y[i, j]
                dist = np.sqrt(dx * dx + dy * dy)

                # If a point coincides with the cell center, use its value
                zero_mask = dist < 1e-12
                if np.any(zero_mask):
                    result[i, j] = values[zero_mask][0]
                else:
                    weights = 1.0 / np.power(dist, power)
                    result[i, j] = np.sum(weights * values) / np.sum(weights)

        return result
