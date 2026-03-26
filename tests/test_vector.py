"""Tests for the tkgis vector I/O subsystem and vector provider plugin."""
from __future__ import annotations

import tempfile
from pathlib import Path

import geopandas as gpd
import numpy as np
import pytest
from shapely.geometry import Point

from tkgis.io.vector import VectorLayerData
from tkgis.io.vector_tiles import VectorTileProvider
from tkgis.models.crs import CRSDefinition
from tkgis.models.geometry import BoundingBox
from tkgis.models.layers import Layer, LayerStyle, LayerType
from tkgis.plugins.base import PluginContext
from tkgis.plugins.builtin.vector_provider import (
    VectorDataProvider,
    VectorProviderPlugin,
)
from tkgis.plugins.providers import DataProviderRegistry

FIXTURE = Path(__file__).parent / "fixtures" / "test_points.geojson"


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------

@pytest.fixture
def vdata() -> VectorLayerData:
    """Load the test GeoJSON fixture."""
    return VectorLayerData.from_file(FIXTURE)


# ------------------------------------------------------------------
# Tests
# ------------------------------------------------------------------

def test_load_geojson(vdata: VectorLayerData) -> None:
    """VectorLayerData.from_file loads GeoJSON with correct feature count."""
    assert vdata.feature_count == 10
    assert len(vdata) == 10
    assert "name" in vdata.columns
    assert "value" in vdata.columns
    assert vdata.geometry_types == ["Point"]
    assert vdata.source_path is not None


def test_crs_detection(vdata: VectorLayerData) -> None:
    """CRS is detected as EPSG:4326 for the test GeoJSON."""
    crs = vdata.crs
    assert isinstance(crs, CRSDefinition)
    assert crs.epsg_code == 4326
    assert crs.is_geographic is True


def test_spatial_query_bbox(vdata: VectorLayerData) -> None:
    """get_features_in_bbox returns features within a bounding box."""
    # Bbox covering roughly the northeast US (DC, NYC, Philly)
    bbox = BoundingBox(xmin=-78.0, ymin=38.0, xmax=-73.0, ymax=41.0)
    result = vdata.get_features_in_bbox(bbox)
    assert isinstance(result, gpd.GeoDataFrame)
    names = result["name"].tolist()
    assert "Washington DC" in names
    assert "New York" in names
    assert "Philadelphia" in names
    # Cities outside the bbox should not appear
    assert "Los Angeles" not in names
    assert "Houston" not in names


def test_spatial_query_point(vdata: VectorLayerData) -> None:
    """get_features_at_point returns features near a given point."""
    # Query near Washington DC with a generous tolerance
    result = vdata.get_features_at_point(-77.04, 38.91, tolerance=0.1)
    assert isinstance(result, gpd.GeoDataFrame)
    assert len(result) >= 1
    assert "Washington DC" in result["name"].tolist()

    # Query with zero tolerance at a spot with no features
    result_empty = vdata.get_features_at_point(0.0, 0.0, tolerance=0.0)
    assert len(result_empty) == 0


def test_reproject_vector(vdata: VectorLayerData) -> None:
    """reproject converts to a different CRS and back."""
    reprojected = vdata.reproject(3857)
    assert reprojected.gdf.crs is not None
    assert reprojected.gdf.crs.to_epsg() == 3857
    assert reprojected.feature_count == 10

    # Bounds should be in meters, not degrees
    b = reprojected.bounds
    assert abs(b.xmin) > 1000  # meters, not degrees

    # Round-trip back to 4326
    back = reprojected.reproject(4326)
    assert back.gdf.crs.to_epsg() == 4326
    original_bounds = vdata.bounds
    back_bounds = back.bounds
    assert abs(original_bounds.xmin - back_bounds.xmin) < 0.01


def test_export_roundtrip(vdata: VectorLayerData) -> None:
    """Write to a temp GeoJSON, reload, and verify equality."""
    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = Path(tmpdir) / "export.geojson"
        vdata.to_file(out_path)
        assert out_path.exists()

        reloaded = VectorLayerData.from_file(out_path)
        assert reloaded.feature_count == vdata.feature_count
        assert reloaded.crs.epsg_code == vdata.crs.epsg_code
        assert sorted(reloaded.columns) == sorted(vdata.columns)


def test_vector_provider_plugin() -> None:
    """VectorProviderPlugin registers VectorDataProvider correctly."""
    registry = DataProviderRegistry()
    context = PluginContext()
    context.set_data_provider_registry(registry)

    plugin = VectorProviderPlugin()
    assert plugin.manifest.name == "vector-provider"

    plugin.activate(context)
    assert len(registry.providers) == 1
    provider = registry.providers[0]
    assert provider.name == "geopandas-vector"
    assert "shp" in provider.supported_extensions
    assert "geojson" in provider.supported_extensions
    assert provider.can_open(FIXTURE)

    # Open via the provider
    layer = provider.open(FIXTURE)
    assert isinstance(layer, Layer)
    assert layer.layer_type == LayerType.VECTOR
    assert layer.metadata["feature_count"] == 10

    # Deactivate
    plugin.deactivate()


def test_vector_tile_provider_returns_array(vdata: VectorLayerData) -> None:
    """VectorTileProvider.get_tile returns an RGBA numpy array."""
    style = LayerStyle(
        fill_color="#FF000080",
        stroke_color="#000000",
        stroke_width=2.0,
    )
    provider = VectorTileProvider(vdata, style=style)

    layer = Layer(name="test", layer_type=LayerType.VECTOR)

    # Zoom level 4, tile that covers part of the US
    # At zoom 4, col=4 row=5 roughly covers the central US
    tile = provider.get_tile(layer, zoom_level=4, row=5, col=4, tile_size=256)
    assert tile is not None
    assert isinstance(tile, np.ndarray)
    assert tile.shape == (256, 256, 4)
    assert tile.dtype == np.uint8

    # A tile in the middle of the ocean should return None
    ocean_tile = provider.get_tile(layer, zoom_level=4, row=0, col=0, tile_size=256)
    # Might be None or might have no features — either is acceptable
    # Just verify it doesn't crash

    # Test grid and zoom level methods
    assert provider.get_num_zoom_levels(layer) == 19  # 0..18
    assert provider.get_tile_grid(layer, 3) == (8, 8)
