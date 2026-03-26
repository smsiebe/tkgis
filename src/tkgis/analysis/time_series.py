"""Pixel-level time-series extraction and statistics."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from tkgis.temporal.raster_stack import TemporalRasterStack

logger = logging.getLogger(__name__)


class PixelTimeSeriesAnalyzer:
    """Extract and analyze pixel-level time series from raster stacks."""

    def extract_point(
        self, stack: TemporalRasterStack, row: int, col: int
    ) -> pd.DataFrame:
        """Extract a single-pixel time series from *stack*.

        Parameters
        ----------
        stack:
            A :class:`TemporalRasterStack` containing time-indexed raster layers.
        row, col:
            Pixel coordinates to extract.

        Returns
        -------
        pd.DataFrame
            DataFrame with columns ``time`` and ``value``, one row per frame.
        """
        values = stack.get_time_series_at_pixel(row, col)
        return pd.DataFrame({"time": stack.times, "value": values})

    def extract_region(
        self, stack: TemporalRasterStack, bbox: tuple[int, int, int, int]
    ) -> pd.DataFrame:
        """Extract spatially-averaged time series over a pixel bounding box.

        Parameters
        ----------
        stack:
            A :class:`TemporalRasterStack`.
        bbox:
            ``(row_min, col_min, row_max, col_max)`` in pixel coordinates
            (inclusive on both ends).

        Returns
        -------
        pd.DataFrame
            DataFrame with columns ``time`` and ``value`` (spatial mean per frame).
        """
        row_min, col_min, row_max, col_max = bbox
        n_rows = row_max - row_min + 1
        n_cols = col_max - col_min + 1

        # Collect all pixel series and average
        accumulator = np.zeros(len(stack), dtype=np.float64)
        count = 0
        for r in range(row_min, row_max + 1):
            for c in range(col_min, col_max + 1):
                vals = stack.get_time_series_at_pixel(r, c)
                accumulator += np.nan_to_num(vals, nan=0.0)
                count += 1

        if count > 0:
            accumulator /= count

        return pd.DataFrame({"time": stack.times, "value": accumulator})

    @staticmethod
    def compute_statistics(series: pd.DataFrame) -> dict:
        """Compute summary statistics on a time-series DataFrame.

        Parameters
        ----------
        series:
            DataFrame with a ``value`` column (as returned by
            :meth:`extract_point` or :meth:`extract_region`).

        Returns
        -------
        dict
            Keys: ``mean``, ``std``, ``min``, ``max``, ``trend``
            (slope of a simple linear regression over the integer index).
        """
        values = series["value"].to_numpy(dtype=np.float64)
        valid = values[~np.isnan(values)]

        if len(valid) == 0:
            return {"mean": np.nan, "std": np.nan, "min": np.nan, "max": np.nan, "trend": np.nan}

        stats: dict = {
            "mean": float(np.mean(valid)),
            "std": float(np.std(valid, ddof=0)),
            "min": float(np.min(valid)),
            "max": float(np.max(valid)),
        }

        # Trend: slope of OLS fit  value = trend * index + intercept
        if len(valid) >= 2:
            x = np.arange(len(valid), dtype=np.float64)
            coeffs = np.polyfit(x, valid, 1)
            stats["trend"] = float(coeffs[0])
        else:
            stats["trend"] = 0.0

        return stats
