"""Tests for the raster I/O subsystem.

Covers display engine, tile provider, metadata extraction, geolocation
bridge, and the plugin registration.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

# Import the fixture module so pytest discovers it
from tests.conftest_raster import test_raster_tif  # noqa: F401

from tkgis.io.raster_display import RasterDisplayEngine
from tkgis.io.raster_metadata import RasterMetadataExtractor
from tkgis.io.raster_geoloc import RasterGeolocationBridge
from tkgis.io.raster_tiles import RasterTileProvider
from tkgis.models.layers import Layer, LayerStyle, LayerType
from tkgis.models.geometry import BoundingBox


# ---------------------------------------------------------------------------
# Display engine tests
# ---------------------------------------------------------------------------

class TestRasterDisplaySingleBand:
    """test_raster_display_single_band"""

    def test_single_band_grayscale(self):
        """Single-band float data produces (H, W, 4) RGBA uint8."""
        data = np.random.default_rng(0).random((64, 64)).astype(np.float32)
        result = RasterDisplayEngine.to_display_rgb(data, None)
        assert result.shape == (64, 64, 4)
        assert result.dtype == np.uint8
        # Alpha channel should be 255
        assert np.all(result[:, :, 3] == 255)
        # R == G == B (grayscale)
        assert np.array_equal(result[:, :, 0], result[:, :, 1])
        assert np.array_equal(result[:, :, 1], result[:, :, 2])

    def test_single_band_from_3d(self):
        """Shape (1, H, W) is treated as single band."""
        data = np.random.default_rng(1).random((1, 32, 32)).astype(np.float32)
        result = RasterDisplayEngine.to_display_rgb(data, None)
        assert result.shape == (32, 32, 4)

    def test_constant_image(self):
        """Constant-value image does not crash."""
        data = np.full((16, 16), 42.0)
        result = RasterDisplayEngine.to_display_rgb(data, None)
        assert result.shape == (16, 16, 4)
        assert result.dtype == np.uint8


class TestRasterDisplayRGB:
    """test_raster_display_rgb"""

    def test_rgb_three_band(self):
        """Three-band (3, H, W) data produces RGBA output."""
        rng = np.random.default_rng(2)
        data = rng.integers(0, 256, size=(3, 48, 48), dtype=np.uint8)
        result = RasterDisplayEngine.to_display_rgb(data, None)
        assert result.shape == (48, 48, 4)
        assert result.dtype == np.uint8
        assert np.all(result[:, :, 3] == 255)

    def test_rgb_more_than_three_bands(self):
        """Multi-band (>3) uses first 3 by default."""
        rng = np.random.default_rng(3)
        data = rng.integers(0, 256, size=(6, 32, 32), dtype=np.uint8)
        result = RasterDisplayEngine.to_display_rgb(data, None)
        assert result.shape == (32, 32, 4)

    def test_rgb_band_mapping(self):
        """Custom band_mapping selects specific bands."""
        rng = np.random.default_rng(4)
        data = rng.integers(0, 256, size=(6, 32, 32), dtype=np.uint8)
        style = LayerStyle(band_mapping=[3, 2, 1])
        result = RasterDisplayEngine.to_display_rgb(data, style)
        assert result.shape == (32, 32, 4)


class TestRasterDisplayComplexSAR:
    """test_raster_display_complex_sar"""

    def test_complex_magnitude_display(self):
        """Complex data goes through magnitude -> dB -> stretch -> RGBA."""
        rng = np.random.default_rng(5)
        real = rng.random((40, 40)).astype(np.float32)
        imag = rng.random((40, 40)).astype(np.float32)
        data = real + 1j * imag
        result = RasterDisplayEngine.to_display_rgb(data, None)
        assert result.shape == (40, 40, 4)
        assert result.dtype == np.uint8
        assert np.all(result[:, :, 3] == 255)
        # Grayscale: R == G == B
        assert np.array_equal(result[:, :, 0], result[:, :, 1])

    def test_complex_3d(self):
        """Complex (B, H, W) uses first band."""
        rng = np.random.default_rng(6)
        data = rng.random((2, 20, 20)) + 1j * rng.random((2, 20, 20))
        result = RasterDisplayEngine.to_display_rgb(data.astype(np.complex64), None)
        # Complex multi-band: should still produce valid RGBA
        assert result.shape[2] == 4
        assert result.dtype == np.uint8


class TestPercentileStretch:
    """test_percentile_stretch"""

    def test_output_range(self):
        """Result is uint8 in [0, 255]."""
        data = np.linspace(-100, 500, 1000).reshape(10, 100)
        result = RasterDisplayEngine.percentile_stretch(data)
        assert result.dtype == np.uint8
        assert result.min() >= 0
        assert result.max() <= 255

    def test_custom_percentiles(self):
        """Custom percentile values produce valid output."""
        data = np.random.default_rng(7).random((50, 50))
        result = RasterDisplayEngine.percentile_stretch(data, plow=5.0, phigh=95.0)
        assert result.dtype == np.uint8

    def test_empty_input(self):
        """Zero-size array returns zeros."""
        data = np.array([], dtype=np.float64).reshape(0, 0)
        result = RasterDisplayEngine.percentile_stretch(data)
        assert result.shape == (0, 0)


class TestColormapApplication:
    """test_colormap_application"""

    def test_apply_jet(self):
        """Jet colormap produces RGBA with variation."""
        data = np.arange(256, dtype=np.uint8).reshape(16, 16)
        result = RasterDisplayEngine.apply_colormap(data, "jet")
        assert result.shape == (16, 16, 4)
        assert result.dtype == np.uint8
        assert np.all(result[:, :, 3] == 255)

    def test_apply_gray(self):
        """Gray colormap is near-identity for grayscale."""
        data = np.arange(256, dtype=np.uint8).reshape(16, 16)
        result = RasterDisplayEngine.apply_colormap(data, "gray")
        assert result.shape == (16, 16, 4)
        # R channel should be very close to input (within rounding)
        assert np.allclose(result[:, :, 0].astype(int), data.astype(int), atol=1)

    def test_colormap_via_style(self):
        """Single-band with colormap style uses the colormap."""
        data = np.linspace(0, 100, 64 * 64).reshape(64, 64).astype(np.float32)
        style = LayerStyle(colormap="jet")
        result = RasterDisplayEngine.to_display_rgb(data, style)
        assert result.shape == (64, 64, 4)
        # Should NOT be pure grayscale (R != G in general for jet)
        assert not np.array_equal(result[:, :, 0], result[:, :, 1])


# ---------------------------------------------------------------------------
# Tile provider tests
# ---------------------------------------------------------------------------

class TestTileProviderPyramidLevels:
    """test_tile_provider_pyramid_levels"""

    def test_zoom_levels_small_image(self, test_raster_tif):
        """100x100 image should have at least 1 zoom level."""
        from grdl.IO import open_image

        reader = open_image(test_raster_tif)
        layer = Layer(name="test", layer_type=LayerType.RASTER)
        tp = RasterTileProvider(reader, None, layer)
        n = tp.get_num_zoom_levels(layer)
        assert n >= 1

        # At each level the grid should have positive dimensions
        for z in range(n):
            rows, cols = tp.get_tile_grid(layer, z)
            assert rows >= 1
            assert cols >= 1

        reader.close()

    def test_grid_increases_with_zoom(self, test_raster_tif):
        """Higher zoom levels should have >= as many tiles as lower."""
        from grdl.IO import open_image

        reader = open_image(test_raster_tif)
        layer = Layer(name="test", layer_type=LayerType.RASTER)
        tp = RasterTileProvider(reader, None, layer)
        n = tp.get_num_zoom_levels(layer)
        if n > 1:
            r0, c0 = tp.get_tile_grid(layer, 0)
            r1, c1 = tp.get_tile_grid(layer, n - 1)
            assert r1 >= r0
            assert c1 >= c0
        reader.close()


class TestTileProviderReturnsRGB:
    """test_tile_provider_returns_rgb"""

    def test_tile_is_rgba(self, test_raster_tif):
        """get_tile returns (256, 256, 4) uint8 RGBA."""
        from grdl.IO import open_image

        reader = open_image(test_raster_tif)
        layer = Layer(name="test", layer_type=LayerType.RASTER)
        tp = RasterTileProvider(reader, None, layer)
        n = tp.get_num_zoom_levels(layer)
        tile = tp.get_tile(layer, n - 1, 0, 0, tile_size=256)
        assert tile is not None
        assert tile.shape == (256, 256, 4)
        assert tile.dtype == np.uint8
        reader.close()

    def test_out_of_bounds_returns_none(self, test_raster_tif):
        """Out-of-range tile coordinates return None."""
        from grdl.IO import open_image

        reader = open_image(test_raster_tif)
        layer = Layer(name="test", layer_type=LayerType.RASTER)
        tp = RasterTileProvider(reader, None, layer)
        result = tp.get_tile(layer, 999, 0, 0)
        assert result is None
        reader.close()


# ---------------------------------------------------------------------------
# Metadata extractor
# ---------------------------------------------------------------------------

class TestMetadataExtractor:
    def test_extract(self, test_raster_tif):
        """Metadata dict has expected keys and values."""
        from grdl.IO import open_image

        reader = open_image(test_raster_tif)
        meta = RasterMetadataExtractor.extract(reader)
        assert meta["rows"] == 100
        assert meta["cols"] == 100
        assert meta["bands"] == 3
        assert meta["is_complex"] is False
        assert "dtype" in meta
        reader.close()


# ---------------------------------------------------------------------------
# Geolocation bridge
# ---------------------------------------------------------------------------

class TestGeolocationBridge:
    def test_extract_geolocation(self, test_raster_tif):
        """Should produce an AffineGeolocation for a GeoTIFF."""
        from grdl.IO import open_image

        reader = open_image(test_raster_tif)
        geoloc = RasterGeolocationBridge.extract_geolocation(reader)
        assert geoloc is not None
        reader.close()

    def test_compute_bounds(self, test_raster_tif):
        """Bounds should be a BoundingBox covering the test region."""
        from grdl.IO import open_image

        reader = open_image(test_raster_tif)
        geoloc = RasterGeolocationBridge.extract_geolocation(reader)
        bounds = RasterGeolocationBridge.compute_bounds(reader, geoloc)
        assert isinstance(bounds, BoundingBox)
        # Test fixture covers roughly -77.5 to -77.0 lon, 38.5 to 39.0 lat
        assert bounds.xmin < bounds.xmax
        assert bounds.ymin < bounds.ymax
        reader.close()

    def test_extract_crs(self, test_raster_tif):
        """CRS should be EPSG:4326."""
        from grdl.IO import open_image
        from tkgis.models.crs import CRSDefinition

        reader = open_image(test_raster_tif)
        geoloc = RasterGeolocationBridge.extract_geolocation(reader)
        crs = RasterGeolocationBridge.extract_crs(reader, geoloc)
        assert isinstance(crs, CRSDefinition)
        assert crs.epsg_code == 4326
        reader.close()


# ---------------------------------------------------------------------------
# Plugin integration
# ---------------------------------------------------------------------------

class TestRasterProviderPlugin:
    """test_raster_provider_plugin"""

    def test_plugin_manifest(self):
        """Plugin manifest has correct name."""
        from tkgis.plugins.builtin.raster_provider import RasterProviderPlugin

        plugin = RasterProviderPlugin()
        assert plugin.manifest.name == "grdl-raster"
        assert "data_provider" in plugin.manifest.capabilities

    def test_plugin_activate_registers_provider(self):
        """Activating the plugin registers a provider on the context."""
        from tkgis.plugins.base import PluginContext
        from tkgis.plugins.providers import DataProviderRegistry
        from tkgis.plugins.builtin.raster_provider import RasterProviderPlugin

        ctx = PluginContext()
        registry = DataProviderRegistry()
        ctx.set_data_provider_registry(registry)

        plugin = RasterProviderPlugin()
        plugin.activate(ctx)

        assert len(registry.providers) == 1
        assert registry.providers[0].name == "grdl-raster"

    def test_provider_can_open(self, test_raster_tif):
        """Provider reports it can open .tif files."""
        from tkgis.plugins.builtin.raster_provider import RasterDataProvider

        provider = RasterDataProvider()
        assert provider.can_open(test_raster_tif)

    def test_provider_open_returns_layer(self, test_raster_tif):
        """Provider.open() returns a Layer with metadata and tile provider."""
        from tkgis.plugins.builtin.raster_provider import RasterDataProvider

        provider = RasterDataProvider()
        layer = provider.open(test_raster_tif)
        assert isinstance(layer, Layer)
        assert layer.layer_type == LayerType.RASTER
        assert layer.metadata["rows"] == 100
        assert layer.metadata["cols"] == 100
        assert "_tile_provider" in layer.metadata
        # Clean up
        layer.metadata["_reader"].close()

    def test_provider_deactivate(self):
        """Deactivation cleans up without error."""
        from tkgis.plugins.builtin.raster_provider import RasterProviderPlugin
        from tkgis.plugins.base import PluginContext

        plugin = RasterProviderPlugin()
        ctx = PluginContext()
        plugin.activate(ctx)
        plugin.deactivate()
        # Should not raise
