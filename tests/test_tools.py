"""Tests for measurement, identify, and selection tools."""
from __future__ import annotations

import math

import pytest

from tkgis.crs.engine import CRSEngine
from tkgis.models.events import EventBus
from tkgis.models.tools import ToolManager
from tkgis.tools.measure import DistanceTool, AreaTool
from tkgis.tools.identify import IdentifyTool, IdentifyResult
from tkgis.tools.select import SelectTool


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------

@pytest.fixture()
def crs_engine() -> CRSEngine:
    return CRSEngine()


@pytest.fixture()
def event_bus() -> EventBus:
    return EventBus()


# ------------------------------------------------------------------
# DistanceTool
# ------------------------------------------------------------------

class TestDistanceTool:
    """Tests for DistanceTool (geodesic distance measurement)."""

    def test_distance_tool_two_points(self, crs_engine: CRSEngine) -> None:
        """Two WGS-84 points separated by ~1 degree of longitude at the equator."""
        tool = DistanceTool(crs_engine=crs_engine, crs=4326)

        # Point A: lon=0, lat=0
        tool.on_press(0, 0, 0.0, 0.0)
        assert len(tool.vertices) == 1
        assert tool.total_distance == 0.0

        # Point B: lon=1, lat=0  (~111 km along the equator)
        tool.on_press(0, 0, 1.0, 0.0)
        assert len(tool.vertices) == 2
        assert len(tool.segment_distances) == 1

        # Geodesic distance at the equator for 1 degree ≈ 111_195 m
        dist = tool.total_distance
        assert dist > 111_000, f"Expected >111 km, got {dist:.0f} m"
        assert dist < 112_000, f"Expected <112 km, got {dist:.0f} m"

    def test_distance_tool_multiple_segments(self, crs_engine: CRSEngine) -> None:
        """Three points should produce two segments with correct total."""
        tool = DistanceTool(crs_engine=crs_engine, crs=4326)

        tool.on_press(0, 0, 0.0, 0.0)
        tool.on_press(0, 0, 1.0, 0.0)
        seg1 = tool.total_distance

        tool.on_press(0, 0, 1.0, 1.0)
        assert len(tool.segment_distances) == 2
        assert tool.total_distance > seg1

        # Total should equal sum of segments
        assert abs(tool.total_distance - sum(tool.segment_distances)) < 0.01

    def test_distance_tool_reset(self, crs_engine: CRSEngine) -> None:
        """Resetting the tool clears all state."""
        tool = DistanceTool(crs_engine=crs_engine, crs=4326)

        tool.on_press(0, 0, 0.0, 0.0)
        tool.on_press(0, 0, 1.0, 0.0)
        assert tool.total_distance > 0

        tool.reset()
        assert tool.vertices == []
        assert tool.segment_distances == []
        assert tool.total_distance == 0.0
        assert not tool.finished

    def test_distance_tool_finish(self, crs_engine: CRSEngine) -> None:
        """Finishing marks the tool as done."""
        tool = DistanceTool(crs_engine=crs_engine, crs=4326)
        tool.on_press(0, 0, 0.0, 0.0)
        tool.on_press(0, 0, 1.0, 0.0)
        tool.finish()
        assert tool.finished

    def test_distance_tool_restart_after_finish(self, crs_engine: CRSEngine) -> None:
        """Pressing after finish auto-resets and starts fresh."""
        tool = DistanceTool(crs_engine=crs_engine, crs=4326)
        tool.on_press(0, 0, 0.0, 0.0)
        tool.on_press(0, 0, 1.0, 0.0)
        tool.finish()

        # New press should reset and start a fresh measurement
        tool.on_press(0, 0, 5.0, 5.0)
        assert len(tool.vertices) == 1
        assert tool.total_distance == 0.0
        assert not tool.finished


# ------------------------------------------------------------------
# AreaTool
# ------------------------------------------------------------------

class TestAreaTool:
    """Tests for AreaTool (geodesic area measurement)."""

    def test_area_tool_triangle(self, crs_engine: CRSEngine) -> None:
        """A small triangle near the equator should have non-zero area."""
        tool = AreaTool(crs_engine=crs_engine, crs=4326)

        # ~1-degree triangle at the equator
        tool.on_press(0, 0, 0.0, 0.0)
        tool.on_press(0, 0, 1.0, 0.0)
        tool.on_press(0, 0, 0.5, 1.0)

        assert len(tool.vertices) == 3
        assert not tool.finished

        tool.finish()
        assert tool.finished
        # Area of ~1-degree triangle ≈ 6.1e9 m² (half of 1° x 1° cell)
        assert tool.total_area > 1e9, f"Expected >1e9 m², got {tool.total_area:.2e}"
        assert tool.total_area < 1e11, f"Expected <1e11 m², got {tool.total_area:.2e}"
        assert tool.perimeter > 0

    def test_area_tool_too_few_vertices(self, crs_engine: CRSEngine) -> None:
        """Fewer than 3 vertices should not compute area."""
        tool = AreaTool(crs_engine=crs_engine, crs=4326)
        tool.on_press(0, 0, 0.0, 0.0)
        tool.on_press(0, 0, 1.0, 0.0)
        tool.finish()
        assert not tool.finished
        assert tool.total_area == 0.0

    def test_area_tool_reset(self, crs_engine: CRSEngine) -> None:
        """Reset clears vertices and computed area."""
        tool = AreaTool(crs_engine=crs_engine, crs=4326)
        tool.on_press(0, 0, 0.0, 0.0)
        tool.on_press(0, 0, 1.0, 0.0)
        tool.on_press(0, 0, 0.5, 1.0)
        tool.finish()

        tool.reset()
        assert tool.vertices == []
        assert tool.total_area == 0.0
        assert tool.perimeter == 0.0
        assert not tool.finished


# ------------------------------------------------------------------
# IdentifyTool
# ------------------------------------------------------------------

class TestIdentifyTool:
    """Tests for IdentifyTool."""

    def test_identify_tool_creation(self) -> None:
        """Basic construction and initial state."""
        tool = IdentifyTool()
        assert tool.name == "identify"
        assert tool.last_result is None

    def test_identify_tool_click_no_callback(self) -> None:
        """Click without a callback produces an empty IdentifyResult."""
        tool = IdentifyTool()
        tool.on_press(100, 200, 5.0, 10.0)
        assert tool.last_result is not None
        assert tool.last_result.map_x == 5.0
        assert tool.last_result.map_y == 10.0
        assert tool.last_result.total_features == 0

    def test_identify_tool_with_callback(self) -> None:
        """Click with a callback stores the returned features."""
        def mock_query(mx, my, layers):
            return {"layer_1": [{"id": 1, "name": "Building"}]}

        tool = IdentifyTool(query_callback=mock_query, layers=[])
        tool.on_press(100, 200, 5.0, 10.0)

        result = tool.last_result
        assert result is not None
        assert result.total_features == 1
        assert "layer_1" in result.results
        assert result.results["layer_1"][0]["name"] == "Building"

    def test_identify_tool_reset(self) -> None:
        """Reset clears the last result."""
        tool = IdentifyTool()
        tool.on_press(0, 0, 1.0, 1.0)
        assert tool.last_result is not None
        tool.reset()
        assert tool.last_result is None


# ------------------------------------------------------------------
# SelectTool
# ------------------------------------------------------------------

class TestSelectTool:
    """Tests for SelectTool."""

    def test_select_tool_point_click(self) -> None:
        """Click (no drag) invokes point selection."""
        def mock_point_query(mx, my, layers):
            return [("layer_a", 42)]

        tool = SelectTool(query_callback=mock_point_query, layers=[])
        # Simulate press then immediate release (no drag)
        tool.on_press(100, 200, 5.0, 10.0)
        tool.on_release(100, 200, 5.0, 10.0)

        assert ("layer_a", 42) in tool.selected_features
        assert tool.selection_count == 1

    def test_select_tool_rectangle(self) -> None:
        """Drag beyond threshold invokes rectangle selection."""
        def mock_rect_query(bbox, layers):
            # Verify we got a BoundingBox
            assert hasattr(bbox, "xmin")
            return [("layer_b", 1), ("layer_b", 2), ("layer_b", 3)]

        tool = SelectTool(query_callback=mock_rect_query, layers=[])

        # Press at one corner
        tool.on_press(10, 10, 0.0, 0.0)
        # Drag beyond threshold (>4px)
        tool.on_drag(50, 50, 5.0, 5.0)
        # Release at opposite corner
        tool.on_release(50, 50, 5.0, 5.0)

        assert tool.selection_count == 3
        assert ("layer_b", 1) in tool.selected_features
        assert ("layer_b", 2) in tool.selected_features
        assert ("layer_b", 3) in tool.selected_features

    def test_select_tool_clear_selection(self) -> None:
        """Clearing the selection empties the set."""
        tool = SelectTool()
        tool.add_to_selection("layer_x", 99)
        assert tool.selection_count == 1
        tool.clear_selection()
        assert tool.selection_count == 0

    def test_select_tool_add_remove(self) -> None:
        """Manual add/remove of features."""
        tool = SelectTool()
        tool.add_to_selection("L1", "F1")
        tool.add_to_selection("L1", "F2")
        assert tool.selection_count == 2

        tool.remove_from_selection("L1", "F1")
        assert tool.selection_count == 1
        assert ("L1", "F2") in tool.selected_features


# ------------------------------------------------------------------
# ToolManager integration
# ------------------------------------------------------------------

class TestToolManagerIntegration:
    """Test registration and activation with ToolManager."""

    def test_tool_registration_with_manager(
        self, event_bus: EventBus, crs_engine: CRSEngine,
    ) -> None:
        """All new tools can be registered and activated via ToolManager."""
        manager = ToolManager(event_bus=event_bus)

        dist_tool = DistanceTool(crs_engine=crs_engine)
        area_tool = AreaTool(crs_engine=crs_engine)
        identify_tool = IdentifyTool()
        select_tool = SelectTool()

        manager.register_tool(dist_tool)
        manager.register_tool(area_tool)
        manager.register_tool(identify_tool)
        manager.register_tool(select_tool)

        # Activate each in turn
        manager.set_active("measure_distance")
        assert manager.get_active() is dist_tool

        manager.set_active("measure_area")
        assert manager.get_active() is area_tool

        manager.set_active("identify")
        assert manager.get_active() is identify_tool

        manager.set_active("select")
        assert manager.get_active() is select_tool

    def test_unknown_tool_raises(self, event_bus: EventBus) -> None:
        manager = ToolManager(event_bus=event_bus)
        with pytest.raises(KeyError):
            manager.set_active("nonexistent")
