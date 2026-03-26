"""Tests for the spatial query engine and expression parser."""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pandas as pd
import pytest

from tkgis.models.geometry import BoundingBox
from tkgis.models.layers import Layer, LayerType
from tkgis.query.engine import QueryResult, SpatialQueryEngine
from tkgis.query.expression import ExpressionError, ExpressionParser

FIXTURES = Path(__file__).parent / "fixtures"


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _make_layer(gdf: gpd.GeoDataFrame, name: str = "test") -> Layer:
    """Wrap a GeoDataFrame in a Layer for query engine consumption."""
    return Layer(
        name=name,
        layer_type=LayerType.VECTOR,
        metadata={"gdf": gdf},
    )


@pytest.fixture()
def points_gdf() -> gpd.GeoDataFrame:
    return gpd.read_file(FIXTURES / "test_points.geojson")


@pytest.fixture()
def points_layer(points_gdf: gpd.GeoDataFrame) -> Layer:
    return _make_layer(points_gdf, name="cities")


@pytest.fixture()
def engine() -> SpatialQueryEngine:
    return SpatialQueryEngine()


@pytest.fixture()
def parser() -> ExpressionParser:
    return ExpressionParser()


# ------------------------------------------------------------------
# Spatial query tests
# ------------------------------------------------------------------

class TestPointQuery:
    """test_point_query — querying features near a point."""

    def test_finds_nearby_feature(
        self, engine: SpatialQueryEngine, points_layer: Layer
    ) -> None:
        # Washington DC is at (-77.0369, 38.9072)
        results = engine.query_point([points_layer], -77.0369, 38.9072, tolerance=0.1)
        assert len(results) == 1
        qr = results[0]
        assert isinstance(qr, QueryResult)
        assert qr.count >= 1
        names = qr.features["name"].tolist()
        assert "Washington DC" in names

    def test_no_match_with_small_tolerance(
        self, engine: SpatialQueryEngine, points_layer: Layer
    ) -> None:
        # Point far from any city, tiny tolerance
        results = engine.query_point([points_layer], 0.0, 0.0, tolerance=0.001)
        assert results == []

    def test_returns_geodataframe(
        self, engine: SpatialQueryEngine, points_layer: Layer
    ) -> None:
        results = engine.query_point([points_layer], -77.0369, 38.9072, tolerance=0.5)
        assert len(results) >= 1
        assert isinstance(results[0].features, gpd.GeoDataFrame)


class TestBboxQuery:
    """test_bbox_query — querying features within a bounding box."""

    def test_bbox_finds_features(
        self, engine: SpatialQueryEngine, points_layer: Layer
    ) -> None:
        # Bbox covering the northeast US (should include DC, NYC, Philly)
        bbox = BoundingBox(xmin=-78, ymin=38, xmax=-73, ymax=41)
        results = engine.query_bbox([points_layer], bbox)
        assert len(results) == 1
        names = set(results[0].features["name"].tolist())
        assert "Washington DC" in names
        assert "New York" in names
        assert "Philadelphia" in names

    def test_bbox_no_match(
        self, engine: SpatialQueryEngine, points_layer: Layer
    ) -> None:
        # Bbox in the middle of the ocean
        bbox = BoundingBox(xmin=10, ymin=10, xmax=11, ymax=11)
        results = engine.query_bbox([points_layer], bbox)
        assert results == []

    def test_bbox_all_features(
        self, engine: SpatialQueryEngine, points_layer: Layer
    ) -> None:
        # Bbox covering all of CONUS
        bbox = BoundingBox(xmin=-130, ymin=20, xmax=-60, ymax=50)
        results = engine.query_bbox([points_layer], bbox)
        assert len(results) == 1
        assert results[0].count == 10


# ------------------------------------------------------------------
# Expression parser tests
# ------------------------------------------------------------------

class TestExpressionParserSimple:
    """test_expression_parser_simple — basic comparisons."""

    def test_greater_than(
        self, parser: ExpressionParser, points_gdf: gpd.GeoDataFrame
    ) -> None:
        mask = parser.parse("value > 5", points_gdf)
        assert isinstance(mask, pd.Series)
        # All cities have value > 5 in our fixture
        assert mask.all()

    def test_greater_than_filters(
        self, parser: ExpressionParser, points_gdf: gpd.GeoDataFrame
    ) -> None:
        mask = parser.parse("value > 60", points_gdf)
        filtered = points_gdf[mask]
        # Should include NYC (88.1), Chicago (65.3), LA (72.9), San Diego (61.8)
        assert len(filtered) == 4
        names = set(filtered["name"].tolist())
        assert "New York" in names
        assert "Chicago" in names

    def test_equals_string(
        self, parser: ExpressionParser, points_gdf: gpd.GeoDataFrame
    ) -> None:
        mask = parser.parse("name = 'Chicago'", points_gdf)
        filtered = points_gdf[mask]
        assert len(filtered) == 1
        assert filtered.iloc[0]["name"] == "Chicago"

    def test_not_equals(
        self, parser: ExpressionParser, points_gdf: gpd.GeoDataFrame
    ) -> None:
        mask = parser.parse("category != 'capital'", points_gdf)
        filtered = points_gdf[mask]
        # All except Washington DC
        assert len(filtered) == 9


class TestExpressionParserAndOr:
    """test_expression_parser_and_or — AND/OR combinations."""

    def test_and(
        self, parser: ExpressionParser, points_gdf: gpd.GeoDataFrame
    ) -> None:
        mask = parser.parse("value > 5 AND name = 'Chicago'", points_gdf)
        filtered = points_gdf[mask]
        assert len(filtered) == 1
        assert filtered.iloc[0]["name"] == "Chicago"

    def test_or(
        self, parser: ExpressionParser, points_gdf: gpd.GeoDataFrame
    ) -> None:
        mask = parser.parse(
            "name = 'Chicago' OR name = 'New York'", points_gdf
        )
        filtered = points_gdf[mask]
        assert len(filtered) == 2
        names = set(filtered["name"].tolist())
        assert names == {"Chicago", "New York"}

    def test_and_or_combined(
        self, parser: ExpressionParser, points_gdf: gpd.GeoDataFrame
    ) -> None:
        mask = parser.parse(
            "value > 50 AND category = 'metro' OR name = 'Washington DC'",
            points_gdf,
        )
        filtered = points_gdf[mask]
        names = set(filtered["name"].tolist())
        # DC comes in via OR; metros with value > 50 come via AND
        assert "Washington DC" in names
        assert "New York" in names


class TestExpressionParserLike:
    """test_expression_parser_like — LIKE pattern matching."""

    def test_like_prefix(
        self, parser: ExpressionParser, points_gdf: gpd.GeoDataFrame
    ) -> None:
        mask = parser.parse("name LIKE 'New%'", points_gdf)
        filtered = points_gdf[mask]
        assert len(filtered) == 1
        assert filtered.iloc[0]["name"] == "New York"

    def test_like_contains(
        self, parser: ExpressionParser, points_gdf: gpd.GeoDataFrame
    ) -> None:
        mask = parser.parse("name LIKE '%an%'", points_gdf)
        filtered = points_gdf[mask]
        names = set(filtered["name"].tolist())
        # San Antonio, San Diego contain "an"
        assert "San Antonio" in names
        assert "San Diego" in names

    def test_like_suffix(
        self, parser: ExpressionParser, points_gdf: gpd.GeoDataFrame
    ) -> None:
        mask = parser.parse("name LIKE '%go'", points_gdf)
        filtered = points_gdf[mask]
        names = set(filtered["name"].tolist())
        assert "Chicago" in names
        assert "San Diego" in names


class TestExpressionParserIsNull:
    """test_expression_parser_is_null — NULL handling."""

    def test_is_null(self, parser: ExpressionParser) -> None:
        df = pd.DataFrame({"a": [1, None, 3], "b": ["x", "y", None]})
        mask = parser.parse("a IS NULL", df)
        assert mask.tolist() == [False, True, False]

    def test_is_not_null(self, parser: ExpressionParser) -> None:
        df = pd.DataFrame({"a": [1, None, 3], "b": ["x", "y", None]})
        mask = parser.parse("b IS NOT NULL", df)
        assert mask.tolist() == [True, True, False]


class TestExpressionParserSafety:
    """test_expression_parser_rejects_dangerous_input."""

    @pytest.mark.parametrize(
        "dangerous",
        [
            "__import__('os').system('rm -rf /')",
            "eval('bad')",
            "exec('bad')",
            "os.system('cmd')",
            "import os",
            "__class__.__bases__",
            "lambda x: x",
        ],
    )
    def test_rejects_dangerous(
        self, parser: ExpressionParser, dangerous: str
    ) -> None:
        df = pd.DataFrame({"a": [1, 2, 3]})
        with pytest.raises(ExpressionError):
            parser.parse(dangerous, df)

    def test_rejects_empty(self, parser: ExpressionParser) -> None:
        df = pd.DataFrame({"a": [1, 2, 3]})
        with pytest.raises(ExpressionError):
            parser.parse("", df)

    def test_rejects_unknown_column(self, parser: ExpressionParser) -> None:
        df = pd.DataFrame({"a": [1, 2, 3]})
        with pytest.raises(ExpressionError):
            parser.parse("nonexistent > 5", df)
