"""Tests for tkgis.analysis spatiotemporal tools."""
from __future__ import annotations

from datetime import datetime
from unittest.mock import patch

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
from shapely.geometry import Point, box

from tkgis.analysis.change_detection import ChangeDetector
from tkgis.analysis.interpolation import SpatialInterpolator
from tkgis.analysis.time_series import PixelTimeSeriesAnalyzer
from tkgis.analysis.zonal import ZonalStatistics
from tkgis.models.layers import Layer, LayerType
from tkgis.temporal.raster_stack import TemporalRasterStack


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_layer(name: str, time_iso: str, data: np.ndarray | None = None) -> Layer:
    """Create a Layer with temporal metadata and optional raster data."""
    meta = {}
    if data is not None:
        meta["data"] = data
    return Layer(
        name=name,
        layer_type=LayerType.TEMPORAL_RASTER,
        time_start=time_iso,
        time_end=time_iso,
        metadata=meta,
    )


def _make_stack(n_frames: int = 5) -> TemporalRasterStack:
    """Create a small TemporalRasterStack with deterministic pixel values.

    Each frame i has pixel values filled with float(i + 1) so the time
    series at any pixel is [1.0, 2.0, ..., n_frames].
    """
    layers = []
    for i in range(n_frames):
        dt = datetime(2024, 1, 1 + i)
        layers.append(
            _make_layer(f"frame_{i}", dt.isoformat())
        )
    return layers, np.arange(1, n_frames + 1, dtype=np.float64)


# ---------------------------------------------------------------------------
# Time Series
# ---------------------------------------------------------------------------

class TestPixelTimeSeriesExtraction:
    """test_pixel_time_series_extraction"""

    def test_extract_point(self):
        layers, expected_values = _make_stack(5)
        stack = TemporalRasterStack(layers)

        # Patch get_time_series_at_pixel to return deterministic values
        with patch.object(
            stack, "get_time_series_at_pixel", return_value=expected_values
        ):
            analyzer = PixelTimeSeriesAnalyzer()
            df = analyzer.extract_point(stack, row=0, col=0)

        assert isinstance(df, pd.DataFrame)
        assert list(df.columns) == ["time", "value"]
        assert len(df) == 5
        np.testing.assert_array_equal(df["value"].values, expected_values)
        # Times should be sorted
        assert list(df["time"]) == sorted(df["time"])

    def test_extract_region(self):
        layers, expected_values = _make_stack(4)
        stack = TemporalRasterStack(layers)

        with patch.object(
            stack, "get_time_series_at_pixel", return_value=expected_values
        ):
            analyzer = PixelTimeSeriesAnalyzer()
            df = analyzer.extract_region(stack, bbox=(0, 0, 1, 1))

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 4
        # All pixels return the same values, so the spatial average equals
        # the per-pixel values.
        np.testing.assert_array_almost_equal(
            df["value"].values, expected_values
        )


class TestTimeSeriesStatistics:
    """test_time_series_statistics"""

    def test_compute_statistics(self):
        series = pd.DataFrame({
            "time": pd.date_range("2024-01-01", periods=5),
            "value": [1.0, 2.0, 3.0, 4.0, 5.0],
        })
        stats = PixelTimeSeriesAnalyzer.compute_statistics(series)

        assert stats["mean"] == pytest.approx(3.0)
        assert stats["std"] == pytest.approx(np.std([1, 2, 3, 4, 5], ddof=0))
        assert stats["min"] == pytest.approx(1.0)
        assert stats["max"] == pytest.approx(5.0)
        # Perfectly linear series → trend = 1.0 per index step
        assert stats["trend"] == pytest.approx(1.0)

    def test_compute_statistics_all_nan(self):
        series = pd.DataFrame({
            "time": pd.date_range("2024-01-01", periods=3),
            "value": [np.nan, np.nan, np.nan],
        })
        stats = PixelTimeSeriesAnalyzer.compute_statistics(series)
        assert np.isnan(stats["mean"])
        assert np.isnan(stats["trend"])


# ---------------------------------------------------------------------------
# Change Detection
# ---------------------------------------------------------------------------

class TestChangeDetectionDifference:
    """test_change_detection_difference"""

    def test_simple_difference(self):
        a = np.array([[1.0, 2.0], [3.0, 4.0]])
        b = np.array([[5.0, 6.0], [7.0, 8.0]])
        layer_a = _make_layer("t1", "2024-01-01", data=a)
        layer_b = _make_layer("t2", "2024-01-02", data=b)

        detector = ChangeDetector()
        result = detector.difference(layer_a, layer_b)

        expected = b - a
        np.testing.assert_array_equal(result.metadata["data"], expected)

    def test_difference_shape_mismatch(self):
        layer_a = _make_layer("t1", "2024-01-01", data=np.zeros((2, 2)))
        layer_b = _make_layer("t2", "2024-01-02", data=np.zeros((3, 3)))
        detector = ChangeDetector()
        with pytest.raises(ValueError, match="Shape mismatch"):
            detector.difference(layer_a, layer_b)


class TestChangeDetectionRatio:
    """test_change_detection_ratio"""

    def test_log_ratio(self):
        a = np.array([[1.0, 2.0], [4.0, 8.0]])
        b = np.array([[2.0, 4.0], [8.0, 16.0]])
        layer_a = _make_layer("t1", "2024-01-01", data=a)
        layer_b = _make_layer("t2", "2024-01-02", data=b)

        detector = ChangeDetector()
        result = detector.ratio(layer_a, layer_b)

        # All ratios are 2.0, so log-ratio = ln(2) everywhere
        expected = np.full((2, 2), np.log(2.0))
        np.testing.assert_array_almost_equal(result.metadata["data"], expected)

    def test_log_ratio_handles_zero(self):
        a = np.array([[0.0, 1.0]])
        b = np.array([[1.0, 1.0]])
        layer_a = _make_layer("t1", "2024-01-01", data=a)
        layer_b = _make_layer("t2", "2024-01-02", data=b)

        detector = ChangeDetector()
        result = detector.ratio(layer_a, layer_b)
        # Should not raise or produce inf
        assert np.all(np.isfinite(result.metadata["data"]))


class TestThresholdChange:
    """test_threshold_change"""

    def test_binary_mask(self):
        diff = np.array([[-3.0, 0.5], [2.0, -0.1]])
        diff_layer = _make_layer("diff", "2024-01-01", data=diff)

        detector = ChangeDetector()
        result = detector.threshold_change(diff_layer, threshold=1.0)
        mask = result.metadata["data"]

        expected = np.array([[1, 0], [1, 0]], dtype=np.uint8)
        np.testing.assert_array_equal(mask, expected)


# ---------------------------------------------------------------------------
# Zonal Statistics
# ---------------------------------------------------------------------------

class TestZonalStatistics:
    """test_zonal_statistics"""

    def test_compute(self):
        # 10x10 raster with value = row index
        raster = np.tile(np.arange(10, dtype=np.float64).reshape(10, 1), (1, 10))

        # Two polygon zones covering different row ranges
        zone_a = box(0, 0, 10, 5)   # rows 0-4
        zone_b = box(0, 5, 10, 10)  # rows 5-9
        zones = gpd.GeoDataFrame(
            {"zone_id": ["A", "B"]},
            geometry=[zone_a, zone_b],
        )

        zs = ZonalStatistics()
        result = zs.compute(raster, zones, stats=["mean", "std", "min", "max", "count"])

        assert "mean" in result.columns
        assert "count" in result.columns

        # Zone A covers rows 0-4: values 0..4 → mean=2.0
        row_a = result.iloc[0]
        assert row_a["mean"] == pytest.approx(2.0)
        assert row_a["min"] == pytest.approx(0.0)
        assert row_a["max"] == pytest.approx(4.0)
        assert row_a["count"] > 0

        # Zone B covers rows 5-9: values 5..9 → mean=7.0
        row_b = result.iloc[1]
        assert row_b["mean"] == pytest.approx(7.0)
        assert row_b["min"] == pytest.approx(5.0)
        assert row_b["max"] == pytest.approx(9.0)


# ---------------------------------------------------------------------------
# IDW Interpolation
# ---------------------------------------------------------------------------

class TestIDWInterpolation:
    """test_idw_interpolation"""

    def test_basic_interpolation(self):
        # Four corner points with known values
        points = gpd.GeoDataFrame(
            {"value": [0.0, 10.0, 10.0, 20.0]},
            geometry=[
                Point(0.0, 0.0),
                Point(10.0, 0.0),
                Point(0.0, 10.0),
                Point(10.0, 10.0),
            ],
        )

        interp = SpatialInterpolator()
        grid = interp.idw(
            points,
            value_column="value",
            resolution=5.0,
            power=2.0,
            bounds=(0, 0, 10, 10),
        )

        assert grid.shape == (2, 2)
        assert grid.dtype == np.float64
        # All values should be between the min and max input values
        assert np.all(grid >= 0.0)
        assert np.all(grid <= 20.0)

    def test_exact_at_point(self):
        """IDW should reproduce the exact value at a data point location."""
        points = gpd.GeoDataFrame(
            {"value": [42.0, 10.0]},
            geometry=[Point(0.5, 0.5), Point(5.0, 5.0)],
        )
        interp = SpatialInterpolator()
        grid = interp.idw(
            points,
            value_column="value",
            resolution=1.0,
            power=2.0,
            bounds=(0, 0, 1, 1),
        )
        # Single cell centered at (0.5, 0.5) — coincides with first point
        assert grid.shape == (1, 1)
        assert grid[0, 0] == pytest.approx(42.0)

    def test_missing_column_raises(self):
        points = gpd.GeoDataFrame(
            {"val": [1.0]},
            geometry=[Point(0, 0)],
        )
        interp = SpatialInterpolator()
        with pytest.raises(ValueError, match="Column 'z' not found"):
            interp.idw(points, value_column="z", resolution=1.0)
