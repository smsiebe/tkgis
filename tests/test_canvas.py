"""Tests for the tkgis canvas and tools packages."""
from __future__ import annotations

import math

import pytest

from tkgis.canvas.transform import ViewTransform
from tkgis.canvas.tiles import TileCache, TileKey
from tkgis.models.geometry import BoundingBox
from tkgis.models.tools import ToolManager
from tkgis.models.events import EventBus
from tkgis.tools.navigation import PanTool, ZoomInTool, ZoomOutTool


# ======================================================================
# ViewTransform
# ======================================================================


class TestViewTransform:
    def test_screen_to_map_roundtrip(self):
        """screen_to_map and map_to_screen are inverses."""
        vt = ViewTransform(
            center_x=500.0, center_y=300.0,
            scale=2.0, canvas_width=800, canvas_height=600,
        )
        # Pick an arbitrary screen point
        sx, sy = 123.0, 456.0
        mx, my = vt.screen_to_map(sx, sy)
        sx2, sy2 = vt.map_to_screen(mx, my)
        assert abs(sx - sx2) < 1e-9
        assert abs(sy - sy2) < 1e-9

    def test_screen_center_maps_to_view_center(self):
        """The screen center should map to (center_x, center_y)."""
        vt = ViewTransform(
            center_x=10.0, center_y=20.0,
            scale=0.5, canvas_width=640, canvas_height=480,
        )
        mx, my = vt.screen_to_map(320, 240)
        assert abs(mx - 10.0) < 1e-9
        assert abs(my - 20.0) < 1e-9

    def test_y_axis_inversion(self):
        """Screen Y down → map Y up: moving screen-down decreases map Y."""
        vt = ViewTransform(center_x=0, center_y=0, scale=1.0,
                           canvas_width=100, canvas_height=100)
        _, my_top = vt.screen_to_map(50, 0)
        _, my_bot = vt.screen_to_map(50, 99)
        assert my_top > my_bot

    def test_zoom_anchor(self):
        """Zoom preserves the map point under the anchor screen pixel."""
        vt = ViewTransform(
            center_x=0, center_y=0, scale=1.0,
            canvas_width=800, canvas_height=600,
        )
        anchor_sx, anchor_sy = 200.0, 150.0
        mx_before, my_before = vt.screen_to_map(anchor_sx, anchor_sy)

        vt.zoom(0.5, anchor_sx, anchor_sy)  # zoom in

        mx_after, my_after = vt.screen_to_map(anchor_sx, anchor_sy)
        assert abs(mx_before - mx_after) < 1e-9
        assert abs(my_before - my_after) < 1e-9

    def test_zoom_changes_scale(self):
        vt = ViewTransform(scale=1.0, canvas_width=800, canvas_height=600)
        vt.zoom(2.0, 400, 300)
        assert abs(vt.scale - 2.0) < 1e-9

    def test_pan(self):
        vt = ViewTransform(center_x=0, center_y=0, scale=1.0,
                           canvas_width=800, canvas_height=600)
        vt.pan(10, 20)
        # pan(+dx) shifts map left → center_x decreases
        assert abs(vt.center_x - (-10.0)) < 1e-9
        # pan(+dy screen down) shifts map up → center_y increases
        assert abs(vt.center_y - 20.0) < 1e-9

    def test_fit_extent(self):
        vt = ViewTransform(canvas_width=800, canvas_height=400)
        bbox = BoundingBox(xmin=0, ymin=0, xmax=1600, ymax=400)
        vt.fit_extent(bbox)
        assert abs(vt.center_x - 800.0) < 1e-9
        assert abs(vt.center_y - 200.0) < 1e-9
        # Scale should be max(1600/800, 400/400) = 2.0
        assert abs(vt.scale - 2.0) < 1e-9

    def test_visible_extent(self):
        vt = ViewTransform(center_x=100, center_y=200, scale=1.0,
                           canvas_width=400, canvas_height=300)
        ext = vt.get_visible_extent()
        assert abs(ext.xmin - (-100.0)) < 1e-9
        assert abs(ext.xmax - 300.0) < 1e-9
        assert abs(ext.ymin - 50.0) < 1e-9
        assert abs(ext.ymax - 350.0) < 1e-9


# ======================================================================
# TileCache
# ======================================================================


class TestTileCache:
    def test_lru_eviction(self):
        """When cache exceeds max_tiles, oldest entries are evicted."""
        cache = TileCache(max_tiles=3)
        keys = [TileKey("layer", 0, 0, i) for i in range(5)]
        for i, k in enumerate(keys):
            cache.put(k, f"img_{i}")

        # First two should have been evicted
        assert cache.get(keys[0]) is None
        assert cache.get(keys[1]) is None
        # Last three remain
        assert cache.get(keys[2]) == "img_2"
        assert cache.get(keys[3]) == "img_3"
        assert cache.get(keys[4]) == "img_4"

    def test_lru_access_refreshes(self):
        """Accessing an entry moves it to most-recently-used."""
        cache = TileCache(max_tiles=3)
        k0 = TileKey("l", 0, 0, 0)
        k1 = TileKey("l", 0, 0, 1)
        k2 = TileKey("l", 0, 0, 2)
        k3 = TileKey("l", 0, 0, 3)

        cache.put(k0, "a")
        cache.put(k1, "b")
        cache.put(k2, "c")

        # Touch k0 so it becomes most-recent
        cache.get(k0)

        # Insert k3 → should evict k1 (the least-recently-used)
        cache.put(k3, "d")

        assert cache.get(k0) == "a"
        assert cache.get(k1) is None  # evicted
        assert cache.get(k2) == "c"
        assert cache.get(k3) == "d"

    def test_invalidate_layer(self):
        cache = TileCache(max_tiles=10)
        cache.put(TileKey("A", 0, 0, 0), "a1")
        cache.put(TileKey("A", 0, 0, 1), "a2")
        cache.put(TileKey("B", 0, 0, 0), "b1")

        cache.invalidate_layer("A")
        assert cache.get(TileKey("A", 0, 0, 0)) is None
        assert cache.get(TileKey("A", 0, 0, 1)) is None
        assert cache.get(TileKey("B", 0, 0, 0)) == "b1"

    def test_clear(self):
        cache = TileCache(max_tiles=10)
        cache.put(TileKey("x", 0, 0, 0), "v")
        cache.clear()
        assert len(cache) == 0

    def test_put_update_existing(self):
        """Putting a key that already exists updates the value."""
        cache = TileCache(max_tiles=5)
        k = TileKey("l", 0, 0, 0)
        cache.put(k, "old")
        cache.put(k, "new")
        assert cache.get(k) == "new"
        assert len(cache) == 1


# ======================================================================
# TileKey
# ======================================================================


class TestTileKey:
    def test_hashable(self):
        """TileKeys can be used in sets and as dict keys."""
        k1 = TileKey("layer1", 3, 5, 7)
        k2 = TileKey("layer1", 3, 5, 7)
        k3 = TileKey("layer1", 3, 5, 8)

        assert k1 == k2
        assert k1 != k3
        assert hash(k1) == hash(k2)

        s = {k1, k2, k3}
        assert len(s) == 2

    def test_frozen(self):
        k = TileKey("l", 0, 0, 0)
        with pytest.raises(AttributeError):
            k.layer_id = "other"  # type: ignore[misc]


# ======================================================================
# Tools
# ======================================================================


class TestPanTool:
    def test_creation(self):
        tool = PanTool()
        assert tool.name == "pan"
        assert tool.mode.value == "pan"
        assert tool.cursor == "fleur"

    def test_register_with_tool_manager(self):
        bus = EventBus()
        tm = ToolManager(event_bus=bus)
        tool = PanTool()
        tm.register_tool(tool)
        tm.set_active("pan")
        assert tm.get_active() is tool


class TestZoomTools:
    def test_zoom_in_creation(self):
        tool = ZoomInTool()
        assert tool.name == "zoom_in"
        assert tool.mode.value == "zoom_in"

    def test_zoom_out_creation(self):
        tool = ZoomOutTool()
        assert tool.name == "zoom_out"
        assert tool.mode.value == "zoom_out"

    def test_register_zoom_tools(self):
        bus = EventBus()
        tm = ToolManager(event_bus=bus)
        tm.register_tool(ZoomInTool())
        tm.register_tool(ZoomOutTool())
        tm.set_active("zoom_in")
        assert tm.get_active().name == "zoom_in"
        tm.set_active("zoom_out")
        assert tm.get_active().name == "zoom_out"
