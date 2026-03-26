"""Tests for the tkgis.crs engine and formatting modules."""

from __future__ import annotations

import math
from types import SimpleNamespace

import numpy as np
import pytest

from tkgis.crs.engine import CRSEngine
from tkgis.crs.formatting import CoordinateFormatter
from tkgis.models.crs import CRSDefinition
from tkgis.models.geometry import BoundingBox


@pytest.fixture
def engine() -> CRSEngine:
    return CRSEngine()


@pytest.fixture
def formatter() -> CoordinateFormatter:
    return CoordinateFormatter()


# ------------------------------------------------------------------
# Transform tests
# ------------------------------------------------------------------


class TestTransformWGS84ToUTM:
    """test_transform_wgs84_to_utm"""

    def test_known_point(self, engine: CRSEngine) -> None:
        # Washington DC area — lon/lat to UTM zone 18N (EPSG:32618).
        lon, lat = -77.0365, 38.8977
        x, y = engine.transform_point(lon, lat, 4326, 32618)
        # UTM easting should be near 323 km, northing near 4 307 km.
        assert 300_000 < x < 400_000
        assert 4_200_000 < y < 4_400_000

    def test_with_crs_definition(self, engine: CRSEngine) -> None:
        src = CRSDefinition.from_epsg(4326)
        dst = CRSDefinition.from_epsg(32618)
        x, y = engine.transform_point(-77.0365, 38.8977, src, dst)
        assert 300_000 < x < 400_000


class TestTransformRoundtrip:
    """test_transform_roundtrip"""

    def test_roundtrip(self, engine: CRSEngine) -> None:
        lon, lat = -105.0, 40.0
        # WGS 84 -> UTM 13N -> WGS 84
        x, y = engine.transform_point(lon, lat, 4326, 32613)
        lon2, lat2 = engine.transform_point(x, y, 32613, 4326)
        assert abs(lon2 - lon) < 1e-8
        assert abs(lat2 - lat) < 1e-8

    def test_roundtrip_arrays(self, engine: CRSEngine) -> None:
        lons = np.array([-105.0, -104.0])
        lats = np.array([40.0, 41.0])
        xs, ys = engine.transform_points(lons, lats, 4326, 32613)
        lons2, lats2 = engine.transform_points(xs, ys, 32613, 4326)
        np.testing.assert_allclose(lons2, lons, atol=1e-8)
        np.testing.assert_allclose(lats2, lats, atol=1e-8)


class TestBBoxReprojection:
    """test_bbox_reprojection"""

    def test_wgs84_to_utm(self, engine: CRSEngine) -> None:
        bbox = BoundingBox(
            xmin=-77.5, ymin=38.5, xmax=-76.5, ymax=39.5, crs="EPSG:4326"
        )
        result = engine.transform_bbox(bbox, 32618)
        assert result.crs == "EPSG:32618"
        # Width in meters should be roughly 85–95 km for 1° longitude at ~39° N.
        assert 80_000 < result.width < 100_000
        # Height should be roughly 111 km for 1° latitude.
        assert 100_000 < result.height < 120_000

    def test_preserves_containment(self, engine: CRSEngine) -> None:
        bbox = BoundingBox(
            xmin=-78.0, ymin=38.0, xmax=-76.0, ymax=40.0, crs="EPSG:4326"
        )
        result = engine.transform_bbox(bbox, 32618)
        # The center of the original bbox, transformed, should lie inside.
        cx, cy = engine.transform_point(-77.0, 39.0, 4326, 32618)
        assert result.contains(cx, cy)


class TestGeodesicDistance:
    """test_geodesic_distance"""

    def test_known_distance(self, engine: CRSEngine) -> None:
        # New York to London — roughly 5 570 km.
        d = engine.compute_distance(-74.006, 40.7128, -0.1276, 51.5074, 4326)
        assert 5_500_000 < d < 5_700_000

    def test_zero_distance(self, engine: CRSEngine) -> None:
        d = engine.compute_distance(10.0, 20.0, 10.0, 20.0, 4326)
        assert d < 0.01

    def test_projected_crs(self, engine: CRSEngine) -> None:
        # Two points in UTM 18N — distance should still be geodesic meters.
        d = engine.compute_distance(
            500_000, 4_300_000, 510_000, 4_300_000, 32618
        )
        # ~10 km easting difference.
        assert 9_000 < d < 11_000


# ------------------------------------------------------------------
# Formatting tests
# ------------------------------------------------------------------


class TestCoordinateFormattingDD:
    """test_coordinate_formatting_dd"""

    def test_north_west(self, formatter: CoordinateFormatter) -> None:
        s = formatter.format_dd(-77.0365, 38.8977)
        assert "38.8977" in s
        assert "77.0365" in s
        assert "N" in s
        assert "W" in s

    def test_south_east(self, formatter: CoordinateFormatter) -> None:
        s = formatter.format_dd(151.2093, -33.8688)
        assert "S" in s
        assert "E" in s


class TestCoordinateFormattingDMS:
    """test_coordinate_formatting_dms"""

    def test_dms_format(self, formatter: CoordinateFormatter) -> None:
        s = formatter.format_dms(-77.0365, 38.8977)
        assert "38" in s
        assert "53" in s  # minutes
        assert "N" in s
        assert "W" in s

    def test_projected_format(self, formatter: CoordinateFormatter) -> None:
        s = formatter.format_projected(500000, 4649776.22, "m")
        assert "500000.00" in s
        assert "4649776.22" in s
        assert "m" in s


# ------------------------------------------------------------------
# Scale computation
# ------------------------------------------------------------------


class TestScaleComputation:
    """test_scale_computation"""

    def test_projected_scale(self, engine: CRSEngine) -> None:
        # Simulate a 1-meter pixel in UTM.
        transform = SimpleNamespace(pixel_width=1.0, pixel_height=-1.0)
        scale = engine.compute_scale(transform, 32618)
        # At 96 DPI, 1 m ground -> scale ~ 3780.
        assert 3_000 < scale < 5_000

    def test_geographic_scale(self, engine: CRSEngine) -> None:
        # A ~0.001° pixel in WGS 84 ≈ 111 m ground.
        transform = SimpleNamespace(pixel_width=0.001, pixel_height=-0.001)
        scale = engine.compute_scale(transform, 4326)
        assert scale > 100_000  # Should be a large-ish denominator.

    def test_zero_pixel(self, engine: CRSEngine) -> None:
        transform = SimpleNamespace(pixel_width=0.0, pixel_height=0.0)
        scale = engine.compute_scale(transform, 4326)
        assert scale == 0.0


# ------------------------------------------------------------------
# Cache test
# ------------------------------------------------------------------


class TestCaching:
    def test_transformer_cache(self, engine: CRSEngine) -> None:
        engine.transform_point(0, 0, 4326, 3857)
        engine.transform_point(1, 1, 4326, 3857)
        assert len(engine._cache) == 1
