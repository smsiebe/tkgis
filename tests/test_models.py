"""Tests for tkgis domain models."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from tkgis.models.geometry import BoundingBox
from tkgis.models.crs import CRSDefinition
from tkgis.models.layers import Layer, LayerStyle, LayerType
from tkgis.models.project import MapView, Project
from tkgis.models.events import EventBus, EventType
from tkgis.models.tools import BaseTool, ToolManager, ToolMode


# ── helpers ──────────────────────────────────────────────────────────


class _DummyTool(BaseTool):
    """Minimal concrete tool for testing."""

    def __init__(self, name: str, mode: ToolMode) -> None:
        self.name = name
        self.mode = mode
        self.cursor = "arrow"
        self.activated = False
        self.deactivated = False

    def on_press(self, x, y, map_x, map_y):
        pass

    def on_drag(self, x, y, map_x, map_y):
        pass

    def on_release(self, x, y, map_x, map_y):
        pass

    def activate(self):
        self.activated = True

    def deactivate(self):
        self.deactivated = True


# ── BoundingBox ──────────────────────────────────────────────────────


class TestBoundingBox:
    def test_properties(self):
        bb = BoundingBox(0, 0, 10, 5)
        assert bb.width == 10.0
        assert bb.height == 5.0
        assert bb.center == (5.0, 2.5)

    def test_contains(self):
        bb = BoundingBox(0, 0, 10, 10)
        assert bb.contains(5, 5)
        assert bb.contains(0, 0)  # on boundary
        assert bb.contains(10, 10)  # on boundary
        assert not bb.contains(-1, 5)
        assert not bb.contains(5, 11)

    def test_intersects(self):
        a = BoundingBox(0, 0, 10, 10)
        b = BoundingBox(5, 5, 15, 15)
        c = BoundingBox(20, 20, 30, 30)
        assert a.intersects(b)
        assert b.intersects(a)
        assert not a.intersects(c)

    def test_intersects_crs_mismatch(self):
        a = BoundingBox(0, 0, 10, 10, crs="EPSG:4326")
        b = BoundingBox(5, 5, 15, 15, crs="EPSG:3857")
        with pytest.raises(ValueError, match="CRS mismatch"):
            a.intersects(b)

    def test_union(self):
        a = BoundingBox(0, 0, 10, 10)
        b = BoundingBox(5, 5, 15, 15)
        u = a.union(b)
        assert u.xmin == 0
        assert u.ymin == 0
        assert u.xmax == 15
        assert u.ymax == 15

    def test_to_dict_from_dict(self):
        bb = BoundingBox(1.5, 2.5, 3.5, 4.5, crs="EPSG:3857")
        d = bb.to_dict()
        restored = BoundingBox.from_dict(d)
        assert restored == bb


# ── CRSDefinition ────────────────────────────────────────────────────


class TestCRSDefinition:
    def test_from_epsg_4326(self):
        """from_epsg(4326) should work with or without pyproj."""
        crs = CRSDefinition.from_epsg(4326)
        assert crs.epsg_code == 4326
        assert crs.is_geographic is True
        assert crs.units == "degrees"
        assert "WGS" in crs.name or "4326" in crs.name

    def test_from_epsg_3857(self):
        crs = CRSDefinition.from_epsg(3857)
        assert crs.epsg_code == 3857
        assert crs.is_geographic is False
        assert crs.units == "meters"

    def test_to_dict_from_dict(self):
        crs = CRSDefinition.from_epsg(4326)
        d = crs.to_dict()
        restored = CRSDefinition.from_dict(d)
        assert restored.epsg_code == crs.epsg_code
        assert restored.name == crs.name
        assert restored.is_geographic == crs.is_geographic
        assert restored.units == crs.units


# ── Layer serialization ──────────────────────────────────────────────


class TestLayerSerialization:
    def test_roundtrip(self):
        layer = Layer(
            id="test-layer-1",
            name="My Raster",
            layer_type=LayerType.RASTER,
            source_path="/data/test.tif",
            crs=CRSDefinition.from_epsg(4326),
            bounds=BoundingBox(-180, -90, 180, 90),
            style=LayerStyle(opacity=0.8, colormap="viridis"),
            metadata={"sensor": "SAR", "resolution": 1.0},
            time_start="2025-01-01T00:00:00",
            time_end="2025-12-31T23:59:59",
            time_steps=["2025-01-01", "2025-06-01", "2025-12-01"],
        )
        d = layer.to_dict()
        # Ensure it is JSON-serializable
        json_str = json.dumps(d)
        d2 = json.loads(json_str)
        restored = Layer.from_dict(d2)

        assert restored.id == layer.id
        assert restored.name == layer.name
        assert restored.layer_type == layer.layer_type
        assert restored.source_path == layer.source_path
        assert restored.bounds == layer.bounds
        assert restored.style.opacity == layer.style.opacity
        assert restored.style.colormap == layer.style.colormap
        assert restored.metadata == layer.metadata
        assert restored.time_start == layer.time_start
        assert restored.time_end == layer.time_end
        assert restored.time_steps == layer.time_steps


# ── Project save/load ────────────────────────────────────────────────


class TestProjectSaveLoad:
    def test_roundtrip(self, tmp_path: Path):
        proj = Project(name="Test Project")
        proj.add_layer(
            Layer(
                id="lyr-1",
                name="Layer 1",
                layer_type=LayerType.VECTOR,
                bounds=BoundingBox(0, 0, 10, 10),
                crs=CRSDefinition.from_epsg(4326),
            )
        )
        proj.add_layer(
            Layer(
                id="lyr-2",
                name="Layer 2",
                layer_type=LayerType.RASTER,
                bounds=BoundingBox(5, 5, 15, 15),
                crs=CRSDefinition.from_epsg(4326),
            )
        )
        proj.map_view = MapView(center_x=5.0, center_y=5.0, zoom_level=3.0)
        proj.plugin_state = {"my_plugin": {"key": "value"}}

        save_path = str(tmp_path / "test_project.json")
        proj.save(save_path)

        loaded = Project.load(save_path)
        assert loaded.name == "Test Project"
        assert len(loaded.layers) == 2
        assert loaded.layers[0].id == "lyr-1"
        assert loaded.layers[1].id == "lyr-2"
        assert loaded.map_view.center_x == 5.0
        assert loaded.map_view.zoom_level == 3.0
        assert loaded.plugin_state == {"my_plugin": {"key": "value"}}
        assert loaded.crs.epsg_code == 4326


# ── Project layer operations ─────────────────────────────────────────


class TestProjectLayerOperations:
    def test_add_get_remove(self):
        proj = Project()
        lyr = Layer(id="a", name="A")
        proj.add_layer(lyr)
        assert proj.get_layer("a") is lyr
        assert proj.get_layer("nonexistent") is None

        proj.remove_layer("a")
        assert proj.get_layer("a") is None
        assert len(proj.layers) == 0

    def test_move_layer(self):
        proj = Project()
        proj.add_layer(Layer(id="a", name="A"))
        proj.add_layer(Layer(id="b", name="B"))
        proj.add_layer(Layer(id="c", name="C"))

        proj.move_layer("c", 0)
        assert [lyr.id for lyr in proj.layers] == ["c", "a", "b"]

        proj.move_layer("a", 2)
        assert [lyr.id for lyr in proj.layers] == ["c", "b", "a"]

    def test_move_layer_unknown(self):
        proj = Project()
        with pytest.raises(KeyError):
            proj.move_layer("nonexistent", 0)

    def test_get_full_extent(self):
        proj = Project()
        proj.add_layer(Layer(id="a", bounds=BoundingBox(0, 0, 10, 10)))
        proj.add_layer(Layer(id="b", bounds=BoundingBox(5, 5, 20, 20)))
        extent = proj.get_full_extent()
        assert extent is not None
        assert extent.xmin == 0
        assert extent.ymin == 0
        assert extent.xmax == 20
        assert extent.ymax == 20

    def test_get_full_extent_no_bounds(self):
        proj = Project()
        proj.add_layer(Layer(id="a"))
        assert proj.get_full_extent() is None


# ── EventBus ─────────────────────────────────────────────────────────


class TestEventBus:
    def test_pub_sub(self):
        bus = EventBus()
        received: list[dict] = []

        def handler(**kwargs):
            received.append(kwargs)

        bus.subscribe(EventType.LAYER_ADDED, handler)
        bus.emit(EventType.LAYER_ADDED, layer_id="abc", name="Test")

        assert len(received) == 1
        assert received[0]["layer_id"] == "abc"
        assert received[0]["name"] == "Test"

    def test_unsubscribe(self):
        bus = EventBus()
        call_count = 0

        def handler(**kwargs):
            nonlocal call_count
            call_count += 1

        bus.subscribe(EventType.VIEW_CHANGED, handler)
        bus.emit(EventType.VIEW_CHANGED)
        assert call_count == 1

        bus.unsubscribe(EventType.VIEW_CHANGED, handler)
        bus.emit(EventType.VIEW_CHANGED)
        assert call_count == 1  # should not increment

    def test_unsubscribe_not_subscribed(self):
        """Unsubscribing a callback that was never subscribed should not raise."""
        bus = EventBus()
        bus.unsubscribe(EventType.VIEW_CHANGED, lambda **kw: None)

    def test_no_duplicate_subscribe(self):
        bus = EventBus()
        call_count = 0

        def handler(**kwargs):
            nonlocal call_count
            call_count += 1

        bus.subscribe(EventType.LAYER_ADDED, handler)
        bus.subscribe(EventType.LAYER_ADDED, handler)  # duplicate
        bus.emit(EventType.LAYER_ADDED)
        assert call_count == 1

    def test_handler_exception_does_not_stop_others(self):
        bus = EventBus()
        results: list[str] = []

        def bad_handler(**kwargs):
            raise RuntimeError("boom")

        def good_handler(**kwargs):
            results.append("ok")

        bus.subscribe(EventType.LAYER_ADDED, bad_handler)
        bus.subscribe(EventType.LAYER_ADDED, good_handler)
        bus.emit(EventType.LAYER_ADDED)
        assert results == ["ok"]


# ── ToolManager ──────────────────────────────────────────────────────


class TestToolManager:
    def test_register_and_activate(self):
        bus = EventBus()
        mgr = ToolManager(event_bus=bus)

        pan = _DummyTool("pan", ToolMode.PAN)
        zoom = _DummyTool("zoom", ToolMode.ZOOM_IN)
        mgr.register_tool(pan)
        mgr.register_tool(zoom)

        assert mgr.get_active() is None

        events: list[str] = []
        bus.subscribe(EventType.TOOL_CHANGED, lambda **kw: events.append(kw["tool_name"]))

        mgr.set_active("pan")
        assert mgr.get_active() is pan
        assert pan.activated is True

        mgr.set_active("zoom")
        assert mgr.get_active() is zoom
        assert pan.deactivated is True
        assert zoom.activated is True
        assert events == ["pan", "zoom"]

    def test_set_active_unknown(self):
        mgr = ToolManager()
        with pytest.raises(KeyError, match="Unknown tool"):
            mgr.set_active("nonexistent")
