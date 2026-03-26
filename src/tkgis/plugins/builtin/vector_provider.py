"""Built-in vector data provider plugin (geopandas backend)."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from tkgis.io.vector import VectorLayerData
from tkgis.models.crs import CRSDefinition
from tkgis.models.layers import Layer, LayerType, LayerStyle
from tkgis.plugins.base import PluginContext, TkGISPlugin
from tkgis.plugins.manifest import PluginManifest
from tkgis.plugins.providers import DataProvider

logger = logging.getLogger(__name__)

_SUPPORTED_EXTENSIONS = [
    "shp", "geojson", "json", "gpkg", "kml", "gml", "fgb", "csv", "parquet",
]


class VectorDataProvider(DataProvider):
    """DataProvider for vector formats via geopandas."""

    @property
    def name(self) -> str:
        return "geopandas-vector"

    @property
    def supported_extensions(self) -> list[str]:
        return list(_SUPPORTED_EXTENSIONS)

    @property
    def supported_modalities(self) -> list[str]:
        return ["vector"]

    def can_open(self, path: Path) -> bool:
        """Return True if the file extension is supported."""
        suffix = path.suffix.lower().lstrip(".")
        return suffix in _SUPPORTED_EXTENSIONS

    def open(self, path: Path) -> Layer:
        """Open a vector file and return a Layer."""
        vdata = VectorLayerData.from_file(path)
        layer = Layer(
            name=path.stem,
            layer_type=LayerType.VECTOR,
            source_path=str(path),
            crs=vdata.crs,
            bounds=vdata.bounds,
            style=LayerStyle(
                fill_color="#4682B480",
                stroke_color="#000000",
                stroke_width=1.0,
            ),
            metadata={
                "feature_count": vdata.feature_count,
                "geometry_types": vdata.geometry_types,
                "columns": vdata.columns,
                "provider": self.name,
            },
        )
        # Attach the VectorLayerData for downstream consumers
        layer.metadata["_vector_data"] = vdata
        return layer

    def get_file_filter(self) -> str:
        """Return a file-dialog filter string for vector formats."""
        exts = " ".join(f"*.{e}" for e in _SUPPORTED_EXTENSIONS)
        return f"Vector files ({exts})"


class VectorProviderPlugin(TkGISPlugin):
    """Plugin that registers the geopandas vector data provider."""

    def __init__(self) -> None:
        self._provider: VectorDataProvider | None = None

    @property
    def manifest(self) -> PluginManifest:
        return PluginManifest(
            name="vector-provider",
            display_name="Vector Data Provider",
            version="0.1.0",
            description="Geopandas-based vector file I/O (Shapefile, GeoJSON, GeoPackage, etc.)",
            author="tkgis",
            license="MIT",
            capabilities=["data-provider"],
            dependencies=["geopandas"],
        )

    def activate(self, context: PluginContext) -> None:
        """Register the VectorDataProvider with the application."""
        self._provider = VectorDataProvider()
        context.register_data_provider(self._provider)
        logger.info("VectorProviderPlugin activated")

    def deactivate(self) -> None:
        """Clean up resources."""
        self._provider = None
        logger.info("VectorProviderPlugin deactivated")


def get_plugin() -> VectorProviderPlugin:
    """Factory function for plugin discovery."""
    return VectorProviderPlugin()
