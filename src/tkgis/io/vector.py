"""Vector layer data wrapper around geopandas GeoDataFrame."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import geopandas as gpd
import numpy as np
from shapely.geometry import box, Point

from tkgis.models.crs import CRSDefinition
from tkgis.models.geometry import BoundingBox

logger = logging.getLogger(__name__)


class VectorLayerData:
    """Wraps a geopandas GeoDataFrame with convenience methods for tkgis.

    Provides CRS detection, spatial queries, reprojection, and file I/O
    through the geopandas/pyogrio stack.
    """

    def __init__(
        self,
        gdf: gpd.GeoDataFrame,
        source_path: str | None = None,
    ) -> None:
        if not isinstance(gdf, gpd.GeoDataFrame):
            raise TypeError(f"Expected GeoDataFrame, got {type(gdf).__name__}")
        self._gdf = gdf
        self._source_path = source_path

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def gdf(self) -> gpd.GeoDataFrame:
        """The underlying GeoDataFrame."""
        return self._gdf

    @property
    def source_path(self) -> str | None:
        """Original file path, if loaded from disk."""
        return self._source_path

    @property
    def crs(self) -> CRSDefinition:
        """Return a CRSDefinition derived from the GeoDataFrame CRS."""
        gdf_crs = self._gdf.crs
        if gdf_crs is None:
            return CRSDefinition(name="Unknown", is_geographic=True, units="degrees")
        epsg = gdf_crs.to_epsg()
        if epsg is not None:
            return CRSDefinition.from_epsg(epsg)
        # Fallback: build from WKT/proj4
        return CRSDefinition(
            proj_string=gdf_crs.to_proj4() if hasattr(gdf_crs, "to_proj4") else None,
            wkt=gdf_crs.to_wkt(),
            name=gdf_crs.name if hasattr(gdf_crs, "name") else "Unknown",
            is_geographic=gdf_crs.is_geographic,
            units="degrees" if gdf_crs.is_geographic else "meters",
        )

    @property
    def bounds(self) -> BoundingBox:
        """Axis-aligned bounding box of all features."""
        total = self._gdf.total_bounds  # (xmin, ymin, xmax, ymax)
        epsg = self._gdf.crs.to_epsg() if self._gdf.crs else 4326
        crs_str = f"EPSG:{epsg}" if epsg else "EPSG:4326"
        return BoundingBox(
            xmin=float(total[0]),
            ymin=float(total[1]),
            xmax=float(total[2]),
            ymax=float(total[3]),
            crs=crs_str,
        )

    @property
    def feature_count(self) -> int:
        """Number of features in the dataset."""
        return len(self._gdf)

    @property
    def geometry_types(self) -> list[str]:
        """Unique geometry type names present in the dataset."""
        return sorted(self._gdf.geom_type.dropna().unique().tolist())

    @property
    def columns(self) -> list[str]:
        """Non-geometry column names."""
        return [c for c in self._gdf.columns if c != self._gdf.geometry.name]

    @property
    def gdf_4326(self) -> gpd.GeoDataFrame:
        """Return the GeoDataFrame reprojected to EPSG:4326, cached."""
        if not hasattr(self, "_gdf_4326"):
            epsg = self._gdf.crs.to_epsg() if self._gdf.crs else None
            if epsg != 4326:
                self._gdf_4326 = self._gdf.to_crs("EPSG:4326")
            else:
                self._gdf_4326 = self._gdf
        return self._gdf_4326

    # ------------------------------------------------------------------
    # Spatial queries
    # ------------------------------------------------------------------

    def get_features_in_bbox_4326(self, bbox: BoundingBox, buffer: float = 0.0) -> gpd.GeoDataFrame:
        """Return EPSG:4326 features whose geometry intersects *bbox*."""
        query_box = box(bbox.xmin - buffer, bbox.ymin - buffer, bbox.xmax + buffer, bbox.ymax + buffer)
        gdf = self.gdf_4326
        sindex = gdf.sindex
        possible_matches_index = list(sindex.intersection(query_box.bounds))
        possible_matches = gdf.iloc[possible_matches_index]
        mask = possible_matches.intersects(query_box)
        return possible_matches[mask].copy()

    def get_features_in_bbox(self, bbox: BoundingBox) -> gpd.GeoDataFrame:
        """Return features whose geometry intersects *bbox*."""
        query_box = box(bbox.xmin, bbox.ymin, bbox.xmax, bbox.ymax)
        mask = self._gdf.intersects(query_box)
        return self._gdf[mask].copy()

    def get_features_at_point(
        self,
        x: float,
        y: float,
        tolerance: float = 0.0,
    ) -> gpd.GeoDataFrame:
        """Return features within *tolerance* of the point (x, y).

        If tolerance is 0, uses exact intersection (only works for polygons
        or features that contain the point).
        """
        pt = Point(x, y)
        if tolerance > 0:
            query_geom = pt.buffer(tolerance)
        else:
            query_geom = pt
        mask = self._gdf.intersects(query_geom)
        return self._gdf[mask].copy()

    # ------------------------------------------------------------------
    # Reprojection
    # ------------------------------------------------------------------

    def reproject(self, target_crs: int | str) -> VectorLayerData:
        """Return a new VectorLayerData reprojected to *target_crs*.

        Parameters
        ----------
        target_crs : int or str
            EPSG code (int) or any string accepted by ``geopandas.GeoDataFrame.to_crs``.
        """
        if isinstance(target_crs, int):
            crs_arg = f"EPSG:{target_crs}"
        else:
            crs_arg = target_crs
        reprojected = self._gdf.to_crs(crs_arg)
        return VectorLayerData(reprojected, source_path=self._source_path)

    # ------------------------------------------------------------------
    # File I/O
    # ------------------------------------------------------------------

    @classmethod
    def from_file(cls, path: str | Path) -> VectorLayerData:
        """Load vector data from a file using geopandas.

        Supports Shapefile, GeoJSON, GeoPackage, KML, GML, FlatGeobuf,
        CSV (with geometry), and Parquet.
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Vector file not found: {path}")

        suffix = path.suffix.lower()
        if suffix == ".parquet":
            gdf = gpd.read_parquet(path)
        else:
            gdf = gpd.read_file(path)

        logger.info(
            "Loaded %d features from %s (CRS: %s)",
            len(gdf),
            path.name,
            gdf.crs,
        )
        return cls(gdf, source_path=str(path))

    def to_file(self, path: str | Path, driver: str | None = None) -> None:
        """Write the vector data to *path*.

        If *driver* is ``None``, geopandas infers the driver from the file
        extension.
        """
        path = Path(path)
        suffix = path.suffix.lower()

        if suffix == ".parquet":
            self._gdf.to_parquet(path)
        elif driver is not None:
            self._gdf.to_file(path, driver=driver)
        else:
            self._gdf.to_file(path)

        logger.info("Wrote %d features to %s", len(self._gdf), path)

    # ------------------------------------------------------------------
    # Dunder
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        src = self._source_path or "in-memory"
        return (
            f"VectorLayerData(features={self.feature_count}, "
            f"crs={self.crs.name}, source={src})"
        )

    def __len__(self) -> int:
        return self.feature_count
