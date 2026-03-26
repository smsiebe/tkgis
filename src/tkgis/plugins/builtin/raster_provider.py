"""Built-in raster data provider plugin using GRDL for I/O.

Registers a DataProvider that handles GeoTIFF, NITF, HDF5, and JP2 files
through GRDL's reader infrastructure.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from tkgis.models.crs import CRSDefinition
from tkgis.models.geometry import BoundingBox
from tkgis.models.layers import Layer, LayerStyle, LayerType
from tkgis.plugins.base import PluginContext, TkGISPlugin
from tkgis.plugins.manifest import PluginManifest
from tkgis.plugins.providers import DataProvider

logger = logging.getLogger(__name__)

# Guard GRDL imports
try:
    from grdl.IO import open_image, open_sar

    _HAS_GRDL = True
except ImportError:
    _HAS_GRDL = False
    open_image = None  # type: ignore[assignment]
    open_sar = None  # type: ignore[assignment]

# SAR-specific extensions
_SAR_EXTENSIONS = {".nitf", ".ntf"}


class RasterDataProvider(DataProvider):
    """DataProvider for raster imagery backed by GRDL."""

    _EXTENSIONS = [".tif", ".tiff", ".nitf", ".ntf", ".h5", ".hdf5", ".jp2"]

    @property
    def name(self) -> str:
        return "grdl-raster"

    @property
    def supported_extensions(self) -> list[str]:
        return [ext.lstrip(".") for ext in self._EXTENSIONS]

    @property
    def supported_modalities(self) -> list[str]:
        return ["raster"]

    def can_open(self, path: Path) -> bool:
        """Check if *path* has a supported extension and GRDL is available."""
        if not _HAS_GRDL:
            return False
        return path.suffix.lower() in self._EXTENSIONS

    def open(self, path: Path) -> Layer:
        """Open *path* and return a configured Layer.

        Uses GRDL's ``open_image`` (or ``open_sar`` for NITF) to create
        a reader, then populates metadata, geolocation, and a tile
        provider on the layer.
        """
        if not _HAS_GRDL:
            raise ImportError("GRDL is required to open raster files")

        from tkgis.io.raster_geoloc import RasterGeolocationBridge
        from tkgis.io.raster_metadata import RasterMetadataExtractor
        from tkgis.io.raster_tiles import RasterTileProvider

        # Choose SAR vs generic opener
        suffix = path.suffix.lower()
        if suffix in _SAR_EXTENSIONS:
            try:
                reader = open_sar(path)
            except Exception:
                logger.debug("open_sar failed for %s; trying open_image", path)
                reader = open_image(path)
        else:
            reader = open_image(path)

        # Extract metadata
        meta = RasterMetadataExtractor.extract(reader)

        # Geolocation
        geoloc = RasterGeolocationBridge.extract_geolocation(reader)
        bounds = RasterGeolocationBridge.compute_bounds(reader, geoloc)
        crs = RasterGeolocationBridge.extract_crs(reader, geoloc)

        # Build layer
        layer = Layer(
            name=path.stem,
            layer_type=LayerType.RASTER,
            source_path=str(path),
            crs=crs,
            bounds=bounds,
            style=LayerStyle(),
            metadata=meta,
        )

        # Attach tile provider as a metadata entry so the canvas can
        # retrieve it.  This avoids coupling Layer to TileProvider.
        tile_provider = RasterTileProvider(reader, geoloc, layer)
        layer.metadata["_tile_provider"] = tile_provider
        layer.metadata["_reader"] = reader

        return layer

    def get_file_filter(self) -> str:
        exts = " ".join(f"*{e}" for e in self._EXTENSIONS)
        return f"Raster Images ({exts})"


class RasterProviderPlugin(TkGISPlugin):
    """Plugin that registers the GRDL-backed raster data provider."""

    _MANIFEST = PluginManifest(
        name="grdl-raster",
        display_name="GRDL Raster Provider",
        version="0.1.0",
        description="Raster data provider using GRDL for GeoTIFF, NITF, HDF5, JP2.",
        author="tkgis",
        license="MIT",
        capabilities=["data_provider"],
        dependencies=["grdl"],
    )

    def __init__(self) -> None:
        self._provider: RasterDataProvider | None = None

    @property
    def manifest(self) -> PluginManifest:
        return self._MANIFEST

    def activate(self, context: PluginContext) -> None:
        """Register the raster data provider."""
        self._provider = RasterDataProvider()
        context.register_data_provider(self._provider)
        logger.info("RasterProviderPlugin activated")

    def deactivate(self) -> None:
        """Clean up."""
        self._provider = None
        logger.info("RasterProviderPlugin deactivated")


def get_plugin() -> RasterProviderPlugin:
    """Factory function for plugin discovery."""
    return RasterProviderPlugin()
