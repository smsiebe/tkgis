"""Tests for the layer manager panel and properties dialog."""
from __future__ import annotations

import tkinter as tk

import pytest

from tkgis.models.events import EventBus, EventType
from tkgis.models.layers import Layer, LayerStyle, LayerType
from tkgis.models.project import Project
from tkgis.panels.layer_tree import LayerTreePanel
from tkgis.panels.properties_dialog import LayerPropertiesDialog


# ── helpers ──────────────────────────────────────────────────────────


def _make_project_with_layers(n: int = 3) -> Project:
    proj = Project(name="Test")
    for i in range(n):
        proj.add_layer(
            Layer(id=f"lyr-{i}", name=f"Layer {i}", layer_type=LayerType.RASTER)
        )
    return proj


# ── LayerTreePanel ───────────────────────────────────────────────────


class TestLayerTreePanelCreates:
    def test_layer_tree_panel_creates(self, tk_root: tk.Tk) -> None:
        """Panel can be instantiated and its widget built."""
        project = Project()
        bus = EventBus()
        panel = LayerTreePanel(project, bus)
        widget = panel.create_widget(tk_root)

        assert widget is not None
        assert panel.widget is widget
        assert panel.name == "layer_tree"
        assert panel.title == "Layers"
        assert panel.dock_position == "left"


class TestLayerTreeReflectsProject:
    def test_layer_tree_reflects_project(self, tk_root: tk.Tk) -> None:
        """Tree shows one row per project layer."""
        project = _make_project_with_layers(3)
        bus = EventBus()
        panel = LayerTreePanel(project, bus)
        panel.create_widget(tk_root)

        tree = panel._tree
        assert tree is not None
        children = tree.get_children()
        assert len(children) == 3
        # Items should be in project layer order.
        assert list(children) == ["lyr-0", "lyr-1", "lyr-2"]

    def test_refresh_after_add(self, tk_root: tk.Tk) -> None:
        """Adding a layer and refreshing updates the tree."""
        project = Project()
        bus = EventBus()
        panel = LayerTreePanel(project, bus)
        panel.create_widget(tk_root)

        assert len(panel._tree.get_children()) == 0  # type: ignore[union-attr]

        project.add_layer(Layer(id="new-lyr", name="New"))
        panel._refresh_tree()

        assert len(panel._tree.get_children()) == 1  # type: ignore[union-attr]


class TestLayerVisibilityToggleEmitsEvent:
    def test_layer_visibility_toggle_emits_event(self, tk_root: tk.Tk) -> None:
        """Toggling visibility emits LAYER_VISIBILITY_CHANGED."""
        project = _make_project_with_layers(1)
        bus = EventBus()
        panel = LayerTreePanel(project, bus)
        panel.create_widget(tk_root)

        received: list[dict] = []
        bus.subscribe(
            EventType.LAYER_VISIBILITY_CHANGED,
            lambda **kw: received.append(kw),
        )

        # Layer starts visible.
        assert project.layers[0].style.visible is True

        # Toggle off.
        panel.toggle_visibility("lyr-0")

        assert project.layers[0].style.visible is False
        assert len(received) == 1
        assert received[0]["layer_id"] == "lyr-0"
        assert received[0]["visible"] is False

        # Toggle back on.
        panel.toggle_visibility("lyr-0")
        assert project.layers[0].style.visible is True
        assert len(received) == 2
        assert received[1]["visible"] is True


class TestLayerReorderEmitsEvent:
    def test_layer_reorder_emits_event(self, tk_root: tk.Tk) -> None:
        """Moving a layer up/down emits LAYER_ORDER_CHANGED."""
        project = _make_project_with_layers(3)
        bus = EventBus()
        panel = LayerTreePanel(project, bus)
        panel.create_widget(tk_root)

        received: list[dict] = []
        bus.subscribe(
            EventType.LAYER_ORDER_CHANGED,
            lambda **kw: received.append(kw),
        )

        # Select the last layer and move it up.
        panel._tree.selection_set("lyr-2")  # type: ignore[union-attr]
        panel._on_move_up()

        assert len(received) == 1
        assert received[0]["layer_id"] == "lyr-2"
        assert received[0]["new_index"] == 1
        assert [lyr.id for lyr in project.layers] == ["lyr-0", "lyr-2", "lyr-1"]

    def test_move_down(self, tk_root: tk.Tk) -> None:
        """Moving a layer down works correctly."""
        project = _make_project_with_layers(3)
        bus = EventBus()
        panel = LayerTreePanel(project, bus)
        panel.create_widget(tk_root)

        received: list[dict] = []
        bus.subscribe(
            EventType.LAYER_ORDER_CHANGED,
            lambda **kw: received.append(kw),
        )

        panel._tree.selection_set("lyr-0")  # type: ignore[union-attr]
        panel._on_move_down()

        assert len(received) == 1
        assert received[0]["layer_id"] == "lyr-0"
        assert received[0]["new_index"] == 1
        assert [lyr.id for lyr in project.layers] == ["lyr-1", "lyr-0", "lyr-2"]

    def test_move_up_at_top_is_noop(self, tk_root: tk.Tk) -> None:
        """Moving the top layer up does nothing."""
        project = _make_project_with_layers(2)
        bus = EventBus()
        panel = LayerTreePanel(project, bus)
        panel.create_widget(tk_root)

        received: list[dict] = []
        bus.subscribe(
            EventType.LAYER_ORDER_CHANGED,
            lambda **kw: received.append(kw),
        )

        panel._tree.selection_set("lyr-0")  # type: ignore[union-attr]
        panel._on_move_up()

        assert len(received) == 0
        assert [lyr.id for lyr in project.layers] == ["lyr-0", "lyr-1"]


class TestPropertiesDialogCreates:
    def test_properties_dialog_creates(self, tk_root: tk.Tk) -> None:
        """LayerPropertiesDialog can be instantiated."""
        layer = Layer(
            id="test-lyr",
            name="Test Layer",
            layer_type=LayerType.VECTOR,
            metadata={"sensor": "EO", "resolution": 0.5},
        )
        dialog = LayerPropertiesDialog(tk_root, layer)

        assert dialog.layer is layer
        assert dialog.winfo_exists()

        # Verify metadata tree has entries.
        children = dialog._meta_tree.get_children()
        assert len(children) == 2

        dialog.destroy()
