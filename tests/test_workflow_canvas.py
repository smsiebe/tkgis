"""Tests for the visual workflow builder components."""
from __future__ import annotations

import tkinter as tk

import customtkinter as ctk
import pytest

from tkgis.workflow.history import WorkflowHistory
from tkgis.workflow.edges import ConnectionValidator, EdgeRenderer
from tkgis.workflow.layer_nodes import LayerInputNode, LayerOutputNode
from tkgis.workflow.canvas import WorkflowCanvas, create_graph, create_fallback_graph


# -----------------------------------------------------------------------
# WorkflowHistory
# -----------------------------------------------------------------------


class TestWorkflowHistory:
    def test_workflow_history_undo_redo(self):
        h = WorkflowHistory()
        h.push({"state": 1})
        h.push({"state": 2})
        h.push({"state": 3})

        assert h.can_undo()
        s = h.undo()
        assert s == {"state": 3}

        s = h.undo()
        assert s == {"state": 2}

        assert h.can_redo()
        s = h.redo()
        assert s == {"state": 2}

        # After redo the state is back on the undo stack
        assert h.can_undo()

    def test_workflow_history_max_limit(self):
        h = WorkflowHistory(max_history=5)
        for i in range(10):
            h.push({"state": i})

        # Only the last 5 should remain
        count = 0
        while h.can_undo():
            h.undo()
            count += 1
        assert count == 5

    def test_redo_cleared_after_new_push(self):
        h = WorkflowHistory()
        h.push({"state": 1})
        h.push({"state": 2})
        h.undo()
        assert h.can_redo()
        h.push({"state": 3})
        assert not h.can_redo()

    def test_undo_empty_returns_none(self):
        h = WorkflowHistory()
        assert h.undo() is None
        assert h.redo() is None


# -----------------------------------------------------------------------
# ConnectionValidator
# -----------------------------------------------------------------------


class TestConnectionValidator:
    def _make_graph(self):
        g = create_fallback_graph()
        return g

    def test_connection_validator_self_loop(self):
        g = self._make_graph()
        sid = g.add_node("A", output_type="raster")
        ok, reason = ConnectionValidator.can_connect(g, sid, sid)
        assert not ok
        assert "itself" in reason.lower()

    def test_connection_validator_compatible_types(self):
        g = self._make_graph()
        s1 = g.add_node("A", output_type="raster")
        s2 = g.add_node("B", input_type="raster", output_type="raster")
        ok, reason = ConnectionValidator.can_connect(g, s1, s2)
        assert ok
        assert reason == ""

    def test_connection_validator_incompatible_types(self):
        g = self._make_graph()
        s1 = g.add_node("A", output_type="raster")
        s2 = g.add_node("B", input_type="feature_set", output_type="feature_set")
        ok, reason = ConnectionValidator.can_connect(g, s1, s2)
        assert not ok
        assert "mismatch" in reason.lower()

    def test_connection_validator_none_types_compatible(self):
        """None input_type or output_type accepts anything."""
        g = self._make_graph()
        s1 = g.add_node("A", output_type="raster")
        s2 = g.add_node("B")  # input_type=None
        ok, _ = ConnectionValidator.can_connect(g, s1, s2)
        assert ok

    def test_connection_validator_duplicate_edge(self):
        g = self._make_graph()
        s1 = g.add_node("A", output_type="raster")
        s2 = g.add_node("B", input_type="raster")
        g.connect(s1, s2)
        ok, reason = ConnectionValidator.can_connect(g, s1, s2)
        assert not ok
        assert "already exists" in reason.lower()


# -----------------------------------------------------------------------
# LayerInputNode / LayerOutputNode
# -----------------------------------------------------------------------


class TestLayerNodes:
    def test_layer_input_node_raster(self):
        node = LayerInputNode(layer_name="test.tif", layer_id="abc", layer_type="raster")
        assert node.processor_name == "tkgis.input.raster"
        assert node.output_type == "raster"
        assert node.input_type is None
        assert node.params["layer_id"] == "abc"

    def test_layer_input_node_vector(self):
        node = LayerInputNode(layer_name="test.shp", layer_id="xyz", layer_type="vector")
        assert node.processor_name == "tkgis.input.vector"
        assert node.output_type == "feature_set"
        assert node.input_type is None

    def test_layer_input_node_feature_set(self):
        node = LayerInputNode(layer_type="feature_set")
        assert node.processor_name == "tkgis.input.vector"
        assert node.output_type == "feature_set"

    def test_layer_output_node(self):
        node = LayerOutputNode()
        assert node.processor_name == "tkgis.output.layer"
        assert node.input_type is None
        assert node.output_type is None
        assert "output_name" in node.params


# -----------------------------------------------------------------------
# EdgeRenderer (requires Tk)
# -----------------------------------------------------------------------


class TestEdgeRenderer:
    def test_edge_renderer_creates_line(self, tk_root):
        canvas = tk.Canvas(tk_root, width=400, height=300)
        item_id = EdgeRenderer.draw_edge(canvas, 50, 50, 300, 200, data_type="raster")
        assert isinstance(item_id, int)
        assert item_id > 0
        # Verify it is a line item
        assert canvas.type(item_id) == "line"
        canvas.destroy()

    def test_rubber_band_creates_line(self, tk_root):
        canvas = tk.Canvas(tk_root, width=400, height=300)
        item_id = EdgeRenderer.draw_rubber_band(canvas, 10, 10, 200, 150)
        assert isinstance(item_id, int)
        assert canvas.type(item_id) == "line"
        canvas.destroy()


# -----------------------------------------------------------------------
# WorkflowCanvas (requires Tk)
# -----------------------------------------------------------------------


class TestWorkflowCanvas:
    def test_workflow_canvas_add_node(self, tk_root):
        canvas = WorkflowCanvas(tk_root, width=600, height=400)
        step_id = canvas.add_node_at("Median", 100, 100, output_type="raster")
        assert step_id is not None
        assert canvas.graph.get_node(step_id) is not None
        node = canvas.graph.get_node(step_id)
        assert node.processor_name == "Median"
        canvas.destroy()

    def test_workflow_canvas_remove_selected(self, tk_root):
        canvas = WorkflowCanvas(tk_root, width=600, height=400)
        step_id = canvas.add_node_at("Median", 100, 100)
        canvas.state.selected_node = step_id
        canvas.remove_selected_node()
        assert canvas.graph.get_node(step_id) is None
        assert canvas.get_selected_node() is None
        canvas.destroy()

    def test_workflow_canvas_refresh(self, tk_root):
        canvas = WorkflowCanvas(tk_root, width=600, height=400)
        canvas.add_node_at("A", 50, 50, output_type="raster")
        canvas.add_node_at("B", 300, 50, input_type="raster", output_type="raster")
        # Should not raise
        canvas.refresh()
        canvas.destroy()

    def test_workflow_canvas_grid_snap(self, tk_root):
        canvas = WorkflowCanvas(tk_root, width=600, height=400)
        step_id = canvas.add_node_at("Snap", 107, 213)
        node = canvas.graph.get_node(step_id)
        x, y = node.position
        assert x % canvas.GRID_SIZE == 0
        assert y % canvas.GRID_SIZE == 0
        canvas.destroy()


# -----------------------------------------------------------------------
# Auto layout
# -----------------------------------------------------------------------


class TestAutoLayout:
    def test_auto_layout_topological(self, tk_root):
        canvas = WorkflowCanvas(tk_root, width=800, height=600)
        s1 = canvas.add_node_at("A", 500, 500, output_type="raster")
        s2 = canvas.add_node_at("B", 500, 500, input_type="raster", output_type="raster")
        s3 = canvas.add_node_at("C", 500, 500, input_type="raster")

        canvas.graph.connect(s1, s2)
        canvas.graph.connect(s2, s3)
        canvas.auto_layout()

        n1 = canvas.graph.get_node(s1)
        n2 = canvas.graph.get_node(s2)
        n3 = canvas.graph.get_node(s3)

        # After auto-layout, nodes should be arranged left-to-right
        assert n1.position[0] < n2.position[0]
        assert n2.position[0] < n3.position[0]
        canvas.destroy()

    def test_auto_layout_parallel_nodes(self, tk_root):
        canvas = WorkflowCanvas(tk_root, width=800, height=600)
        s1 = canvas.add_node_at("Source", 0, 0, output_type="raster")
        s2a = canvas.add_node_at("Branch_A", 0, 0, input_type="raster", output_type="raster")
        s2b = canvas.add_node_at("Branch_B", 0, 0, input_type="raster", output_type="raster")

        canvas.graph.connect(s1, s2a)
        canvas.graph.connect(s1, s2b)
        canvas.auto_layout()

        na = canvas.graph.get_node(s2a)
        nb = canvas.graph.get_node(s2b)
        # Both branches should be at the same x level (further right than source)
        n1 = canvas.graph.get_node(s1)
        assert na.position[0] > n1.position[0]
        assert na.position[0] == nb.position[0]
        canvas.destroy()


# -----------------------------------------------------------------------
# NodePalettePanel (requires Tk)
# -----------------------------------------------------------------------


class TestNodePalettePanel:
    def test_node_palette_panel_creates(self, tk_root):
        from tkgis.workflow.palette import NodePalettePanel

        panel = NodePalettePanel()
        frame = ctk.CTkFrame(tk_root)
        widget = panel.create_widget(frame)
        assert widget is not None
        assert panel.get_selected_processor() is None
        widget.destroy()
        frame.destroy()


# -----------------------------------------------------------------------
# Fallback graph
# -----------------------------------------------------------------------


class TestFallbackGraph:
    def test_add_remove_nodes(self):
        g = create_fallback_graph()
        s1 = g.add_node("A")
        s2 = g.add_node("B")
        assert len(g.get_nodes()) == 2
        g.remove_node(s1)
        assert len(g.get_nodes()) == 1

    def test_connect_disconnect(self):
        g = create_fallback_graph()
        s1 = g.add_node("A", output_type="raster")
        s2 = g.add_node("B", input_type="raster")
        g.connect(s1, s2)
        assert len(g.get_edges()) == 1
        g.disconnect(s1, s2)
        assert len(g.get_edges()) == 0

    def test_topological_levels(self):
        g = create_fallback_graph()
        s1 = g.add_node("A", output_type="raster")
        s2 = g.add_node("B", input_type="raster", output_type="raster")
        s3 = g.add_node("C", input_type="raster")
        g.connect(s1, s2)
        g.connect(s2, s3)
        levels = g.topological_levels()
        assert len(levels) == 3
        assert s1 in levels[0]
        assert s2 in levels[1]
        assert s3 in levels[2]

    def test_validate_type_mismatch(self):
        g = create_fallback_graph()
        s1 = g.add_node("A", output_type="raster")
        s2 = g.add_node("B", input_type="feature_set")
        g.connect(s1, s2)
        errors = g.validate()
        assert len(errors) > 0
        assert "mismatch" in errors[0].lower()

    def test_update_params(self):
        g = create_fallback_graph()
        s1 = g.add_node("A", params={"kernel": 3})
        g.update_node_params(s1, {"kernel": 5, "sigma": 1.0})
        node = g.get_node(s1)
        assert node.params["kernel"] == 5
        assert node.params["sigma"] == 1.0

    def test_update_position(self):
        g = create_fallback_graph()
        s1 = g.add_node("A", position=(10, 20))
        g.update_node_position(s1, (100, 200))
        node = g.get_node(s1)
        assert node.position == (100, 200)
