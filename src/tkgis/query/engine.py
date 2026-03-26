"""Spatial query engine for tkgis layers."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

import geopandas as gpd
from shapely.geometry import Point, box, shape
from shapely.geometry.base import BaseGeometry

from tkgis.models.geometry import BoundingBox
from tkgis.models.layers import Layer
from tkgis.query.expression import ExpressionParser

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


@dataclass
class QueryResult:
    """Result of a spatial query against a single layer."""

    layer: Layer
    features: gpd.GeoDataFrame
    count: int


def _get_gdf(layer: Layer) -> gpd.GeoDataFrame | None:
    """Extract the GeoDataFrame from a layer's metadata.

    Layers store their VectorLayerData (or raw GeoDataFrame) in
    ``layer.metadata["vector_data"]`` or ``layer.metadata["gdf"]``.
    Returns None if unavailable.
    """
    md = layer.metadata
    # Check for VectorLayerData first
    vld = md.get("vector_data")
    if vld is not None:
        if isinstance(vld, gpd.GeoDataFrame):
            return vld
        # VectorLayerData wraps a .gdf attribute
        gdf = getattr(vld, "gdf", None)
        if isinstance(gdf, gpd.GeoDataFrame):
            return gdf
    # Check for raw GeoDataFrame
    gdf = md.get("gdf")
    if isinstance(gdf, gpd.GeoDataFrame):
        return gdf
    return None


class SpatialQueryEngine:
    """Execute spatial queries across one or more layers.

    Uses geopandas spatial predicates internally — no custom spatial
    indexing structures.
    """

    def __init__(self) -> None:
        self._expression_parser = ExpressionParser()

    # ------------------------------------------------------------------
    # Public query methods
    # ------------------------------------------------------------------

    def query_point(
        self,
        layers: list[Layer],
        x: float,
        y: float,
        tolerance: float = 10.0,
    ) -> list[QueryResult]:
        """Find features near a point across *layers*.

        Parameters
        ----------
        layers : list[Layer]
            Layers to query.
        x, y : float
            Query point coordinates (in the layer CRS).
        tolerance : float
            Buffer radius around the point (in CRS units).

        Returns
        -------
        list[QueryResult]
            One entry per layer that had matching features.
        """
        pt = Point(x, y)
        query_geom = pt.buffer(tolerance) if tolerance > 0 else pt
        return self._query_geometry(layers, query_geom)

    def query_bbox(
        self,
        layers: list[Layer],
        bbox: BoundingBox,
    ) -> list[QueryResult]:
        """Find features intersecting a bounding box.

        Parameters
        ----------
        layers : list[Layer]
            Layers to query.
        bbox : BoundingBox
            Axis-aligned bounding box.
        """
        query_geom = box(bbox.xmin, bbox.ymin, bbox.xmax, bbox.ymax)
        return self._query_geometry(layers, query_geom)

    def query_polygon(
        self,
        layers: list[Layer],
        polygon: BaseGeometry | dict,
    ) -> list[QueryResult]:
        """Find features intersecting an arbitrary polygon.

        Parameters
        ----------
        layers : list[Layer]
            Layers to query.
        polygon : BaseGeometry or dict
            A Shapely geometry or a GeoJSON-like dict.
        """
        if isinstance(polygon, dict):
            polygon = shape(polygon)
        return self._query_geometry(layers, polygon)

    def query_buffer(
        self,
        layers: list[Layer],
        geometry: BaseGeometry | dict,
        distance_m: float,
    ) -> list[QueryResult]:
        """Find features within a buffered distance of *geometry*.

        Parameters
        ----------
        layers : list[Layer]
            Layers to query.
        geometry : BaseGeometry or dict
            Source geometry to buffer.
        distance_m : float
            Buffer distance (in CRS units — typically meters or degrees
            depending on the layer CRS).
        """
        if isinstance(geometry, dict):
            geometry = shape(geometry)
        buffered = geometry.buffer(distance_m)
        return self._query_geometry(layers, buffered)

    def query_expression(
        self,
        layer: Layer,
        expression: str,
    ) -> QueryResult:
        """Filter a single layer by an attribute expression.

        Parameters
        ----------
        layer : Layer
            The layer to filter.
        expression : str
            A safe SQL-like WHERE expression (e.g. ``"value > 5"``).

        Returns
        -------
        QueryResult
        """
        gdf = _get_gdf(layer)
        if gdf is None or gdf.empty:
            empty = gpd.GeoDataFrame()
            return QueryResult(layer=layer, features=empty, count=0)

        mask = self._expression_parser.parse(expression, gdf)
        filtered = gdf[mask].copy()
        return QueryResult(layer=layer, features=filtered, count=len(filtered))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _query_geometry(
        self,
        layers: list[Layer],
        query_geom: BaseGeometry,
    ) -> list[QueryResult]:
        """Run an intersection query against all *layers*."""
        results: list[QueryResult] = []
        for layer in layers:
            gdf = _get_gdf(layer)
            if gdf is None or gdf.empty:
                continue
            mask = gdf.intersects(query_geom)
            matched = gdf[mask].copy()
            if not matched.empty:
                results.append(
                    QueryResult(layer=layer, features=matched, count=len(matched))
                )
        return results
