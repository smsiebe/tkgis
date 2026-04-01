"""Visual node graph editor canvas for the workflow builder."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import math
import tkinter as tk
import logging

from tkgis.workflow.edges import ConnectionValidator, EdgeRenderer, TYPE_COLORS
from tkgis.workflow.models_fallback import FallbackGraph

logger = logging.getLogger(__name__)

try:
    from grdl_rt.execution.graph import WorkflowGraph, NodeInfo, EdgeInfo
    from grdl_rt.execution.workflow import WorkflowDefinition, ProcessingStep

    _HAS_GRDL_RT = True
except ImportError:
    WorkflowGraph = None
    _HAS_GRDL_RT = False

def create_graph() -> Any:
    """Create a graph, preferring grdl-runtime if available."""
    if _HAS_GRDL_RT:
        wd = WorkflowDefinition(name="untitled")
        return WorkflowGraph(wd)
    return FallbackGraph()

def create_fallback_graph() -> FallbackGraph:
    """Create a fallback graph instance."""
    return FallbackGraph()

@dataclass
class VisualState:
    selected_node: str | None = None
    dragging_node: str | None = None
    drag_offset: tuple[float, float] = (0.0, 0.0)
    connecting: bool = False
    connect_source: str | None = None
    connect_start: tuple[float, float] = (0.0, 0.0)
    rubber_band_id: int | None = None

class NodeRenderer:
    NODE_WIDTH = 180
    NODE_HEIGHT = 80
    PORT_RADIUS = 6
    NODE_BG = "#313244"
    NODE_BORDER = "#45475a"
    NODE_SELECTED_BORDER = "#cba6f7"
    TEXT_COLOR = "#cdd6f4"
    TEXT_DIM = "#9399b2"

    @classmethod
    def render(cls, canvas: tk.Canvas, node: Any, is_selected: bool) -> tuple[list[int], dict[str, tuple[float, float]]]:
        step_id = node.step_id
        pos = node.position or (100, 100)
        x, y = pos
        w = cls.NODE_WIDTH
        h = cls.NODE_HEIGHT
        header_h = 24

        border_color = cls.NODE_SELECTED_BORDER if is_selected else cls.NODE_BORDER
        header_color = TYPE_COLORS.get(node.output_type, TYPE_COLORS[None])

        items = []

        # Node body
        body = canvas.create_rectangle(
            x, y, x + w, y + h,
            fill=cls.NODE_BG,
            outline=border_color,
            width=2 if is_selected else 1,
            tags=("node", f"node_{step_id}"),
        )
        items.append(body)

        # Header bar
        header = canvas.create_rectangle(
            x + 1, y + 1, x + w - 1, y + header_h,
            fill=header_color,
            outline="",
            tags=("node", f"node_{step_id}"),
        )
        items.append(header)

        # Title text
        title = canvas.create_text(
            x + w // 2,
            y + header_h // 2,
            text=node.display_name,
            fill="#1e1e2e",
            font=("Segoe UI", 10, "bold"),
            anchor="center",
            tags=("node", f"node_{step_id}"),
        )
        items.append(title)

        # Parameter summary
        param_text = ", ".join(f"{k}={v}" for k, v in list(node.params.items())[:3])
        if len(param_text) > 28:
            param_text = param_text[:25] + "..."
        if param_text:
            ptext = canvas.create_text(
                x + 10, y + header_h + 12,
                text=param_text, fill=cls.TEXT_DIM,
                font=("Segoe UI", 8), anchor="w",
                tags=("node", f"node_{step_id}"),
            )
            items.append(ptext)

        # Type badge
        badge = canvas.create_text(
            x + w - 10, y + h - 10,
            text=node.output_type or "any", fill=cls.TEXT_DIM,
            font=("Segoe UI", 7, "italic"), anchor="e",
            tags=("node", f"node_{step_id}"),
        )
        items.append(badge)

        # Ports
        port_y = y + h // 2
        input_port = canvas.create_oval(
            x - cls.PORT_RADIUS, port_y - cls.PORT_RADIUS,
            x + cls.PORT_RADIUS, port_y + cls.PORT_RADIUS,
            fill=TYPE_COLORS.get(node.input_type, TYPE_COLORS[None]),
            outline="#1e1e2e", width=2,
            tags=("port", "input_port", f"port_{step_id}_in"),
        )
        items.append(input_port)

        output_port = canvas.create_oval(
            x + w - cls.PORT_RADIUS, port_y - cls.PORT_RADIUS,
            x + w + cls.PORT_RADIUS, port_y + cls.PORT_RADIUS,
            fill=TYPE_COLORS.get(node.output_type, TYPE_COLORS[None]),
            outline="#1e1e2e", width=2,
            tags=("port", "output_port", f"port_{step_id}_out"),
        )
        items.append(output_port)

        ports = {
            "input": (x, port_y),
            "output": (x + w, port_y),
        }
        return items, ports

class WorkflowCanvas(tk.Canvas):
    GRID_SIZE = 20
    BG_COLOR = "#1e1e2e"
    GRID_COLOR = "#313244"

    def __init__(
        self,
        parent: tk.Widget,
        graph: Any | None = None,
        event_bus: Any | None = None,
        **kwargs: Any,
    ) -> None:
        kwargs.setdefault("bg", self.BG_COLOR)
        kwargs.setdefault("highlightthickness", 0)
        super().__init__(parent, **kwargs)

        self._graph = graph if graph is not None else create_graph()
        self._event_bus = event_bus

        self.state = VisualState()

        # Visual cache
        self._node_items: dict[str, list[int]] = {}
        self._edge_items: list[int] = []
        self._port_positions: dict[str, dict[str, tuple[float, float]]] = {}

        # Bind events
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Double-Button-1>", self._on_double_click)
        self.bind("<ButtonPress-3>", self._on_right_click)

        self._on_node_select_callback: Any = None
        self._on_node_double_click_callback: Any = None

    @property
    def graph(self) -> Any:
        return self._graph

    @graph.setter
    def graph(self, value: Any) -> None:
        self._graph = value
        self.refresh()

    def refresh(self) -> None:
        self.delete("all")
        self._node_items.clear()
        self._edge_items.clear()
        self._port_positions.clear()

        self._draw_grid()

        for node in self._graph.get_nodes():
            is_selected = (node.step_id == self.state.selected_node)
            items, ports = NodeRenderer.render(self, node, is_selected)
            self._node_items[node.step_id] = items
            self._port_positions[node.step_id] = ports

        for edge in self._graph.get_edges():
            self._render_edge(edge.source_id, edge.target_id)

    def add_node_at(
        self,
        processor_name: str,
        x: float,
        y: float,
        *,
        input_type: str | None = None,
        output_type: str | None = None,
    ) -> str:
        x = round(x / self.GRID_SIZE) * self.GRID_SIZE
        y = round(y / self.GRID_SIZE) * self.GRID_SIZE

        step_id = self._graph.add_node(
            processor_name,
            position=(x, y),
            input_type=input_type,
            output_type=output_type,
        )
        self.refresh()
        return step_id

    def remove_selected_node(self) -> None:
        if self.state.selected_node is None:
            return
        try:
            self._graph.remove_node(self.state.selected_node)
        except KeyError:
            pass
        self.state.selected_node = None
        self.refresh()

    def get_selected_node(self) -> str | None:
        return self.state.selected_node

    def show_validation_errors(self, errors: list[str]) -> None:
        self.delete("validation_error")

        for error in errors:
            for node in self._graph.get_nodes():
                if node.step_id in error:
                    pos = node.position or (0, 0)
                    x, y = pos
                    self.create_rectangle(
                        x - 4, y - 4,
                        x + NodeRenderer.NODE_WIDTH + 4,
                        y + NodeRenderer.NODE_HEIGHT + 4,
                        outline="#f38ba8", width=3, dash=(4, 4),
                        tags=("validation_error",),
                    )

    def auto_layout(self) -> None:
        try:
            levels = self._graph.topological_levels()
        except (ValueError, AttributeError):
            return

        h_spacing = NodeRenderer.NODE_WIDTH + 60
        v_spacing = NodeRenderer.NODE_HEIGHT + 40
        start_x = 60
        start_y = 60

        for col_idx, level in enumerate(levels):
            x = start_x + col_idx * h_spacing
            total_height = len(level) * v_spacing
            offset_y = start_y + max(0, (400 - total_height) // 2)

            for row_idx, step_id in enumerate(level):
                y = offset_y + row_idx * v_spacing
                snapped_x = round(x / self.GRID_SIZE) * self.GRID_SIZE
                snapped_y = round(y / self.GRID_SIZE) * self.GRID_SIZE
                self._graph.update_node_position(step_id, (snapped_x, snapped_y))

        self.refresh()

    def _draw_grid(self) -> None:
        w = max(int(self.cget("width") or 2000), 2000)
        h = max(int(self.cget("height") or 1500), 1500)
        for gx in range(0, w, self.GRID_SIZE * 5):
            for gy in range(0, h, self.GRID_SIZE * 5):
                self.create_oval(
                    gx - 1, gy - 1, gx + 1, gy + 1,
                    fill=self.GRID_COLOR, outline="", tags=("grid",),
                )

    def _render_edge(self, source_id: str, target_id: str) -> None:
        src_ports = self._port_positions.get(source_id)
        tgt_ports = self._port_positions.get(target_id)

        if src_ports is None:
            src_node = self._graph.get_node(source_id)
            if src_node is None: return
            pos = src_node.position or (100, 100)
            src_ports = {"output": (pos[0] + NodeRenderer.NODE_WIDTH, pos[1] + NodeRenderer.NODE_HEIGHT // 2)}
        if tgt_ports is None:
            tgt_node = self._graph.get_node(target_id)
            if tgt_node is None: return
            pos = tgt_node.position or (100, 100)
            tgt_ports = {"input": (pos[0], pos[1] + NodeRenderer.NODE_HEIGHT // 2)}

        x1, y1 = src_ports["output"]
        x2, y2 = tgt_ports["input"]

        src_node = self._graph.get_node(source_id)
        data_type = src_node.output_type if src_node else None

        item = EdgeRenderer.draw_edge(self, x1, y1, x2, y2, data_type=data_type)
        self._edge_items.append(item)

    def _hit_test_port(self, x: float, y: float) -> tuple[str | None, str | None]:
        for step_id, ports in self._port_positions.items():
            for port_name, (px, py) in ports.items():
                dist = math.hypot(x - px, y - py)
                if dist <= NodeRenderer.PORT_RADIUS + 4:
                    return step_id, port_name
        return None, None

    def _hit_test_node(self, x: float, y: float) -> str | None:
        for node in self._graph.get_nodes():
            pos = node.position or (0, 0)
            nx, ny = pos
            if nx <= x <= nx + NodeRenderer.NODE_WIDTH and ny <= y <= ny + NodeRenderer.NODE_HEIGHT:
                return node.step_id
        return None

    def _on_press(self, event: tk.Event) -> None:
        x, y = self.canvasx(event.x), self.canvasy(event.y)

        step_id, port_name = self._hit_test_port(x, y)
        if step_id is not None and port_name == "output":
            self.state.connecting = True
            self.state.connect_source = step_id
            ports = self._port_positions.get(step_id, {})
            self.state.connect_start = ports.get("output", (x, y))
            return

        hit_node = self._hit_test_node(x, y)
        old_selected = self.state.selected_node
        self.state.selected_node = hit_node

        if hit_node is not None:
            node = self._graph.get_node(hit_node)
            if node and node.position:
                self.state.drag_offset = (x - node.position[0], y - node.position[1])
            else:
                self.state.drag_offset = (0.0, 0.0)
            self.state.dragging_node = hit_node

        if old_selected != self.state.selected_node:
            self.refresh()
            if self._on_node_select_callback and self.state.selected_node:
                self._on_node_select_callback(self.state.selected_node)

    def _on_drag(self, event: tk.Event) -> None:
        x, y = self.canvasx(event.x), self.canvasy(event.y)

        if self.state.connecting and self.state.connect_source is not None:
            self.delete("rubber_band")
            sx, sy = self.state.connect_start
            self.state.rubber_band_id = EdgeRenderer.draw_rubber_band(self, sx, sy, x, y)
            return

        if self.state.dragging_node is not None:
            new_x = round((x - self.state.drag_offset[0]) / self.GRID_SIZE) * self.GRID_SIZE
            new_y = round((y - self.state.drag_offset[1]) / self.GRID_SIZE) * self.GRID_SIZE
            self._graph.update_node_position(self.state.dragging_node, (new_x, new_y))
            self.refresh()

    def _on_release(self, event: tk.Event) -> None:
        x, y = self.canvasx(event.x), self.canvasy(event.y)

        if self.state.connecting and self.state.connect_source is not None:
            self.delete("rubber_band")
            self.state.rubber_band_id = None

            target_id, port_name = self._hit_test_port(x, y)
            if target_id is None:
                target_id = self._hit_test_node(x, y)
                port_name = "input"

            if target_id is not None and port_name == "input":
                ok, reason = ConnectionValidator.can_connect(
                    self._graph, self.state.connect_source, target_id
                )
                if ok:
                    try:
                        self._graph.connect(self.state.connect_source, target_id)
                    except (KeyError, ValueError) as exc:
                        logger.warning("Connection failed: %s", exc)
                else:
                    logger.info("Connection rejected: %s", reason)

            self.state.connecting = False
            self.state.connect_source = None
            self.refresh()
            return

        self.state.dragging_node = None

    def _on_double_click(self, event: tk.Event) -> None:
        x, y = self.canvasx(event.x), self.canvasy(event.y)
        hit_node = self._hit_test_node(x, y)
        if hit_node is not None and self._on_node_double_click_callback:
            self._on_node_double_click_callback(hit_node)

    def _on_right_click(self, event: tk.Event) -> None:
        x, y = self.canvasx(event.x), self.canvasy(event.y)
        hit_node = self._hit_test_node(x, y)

        menu = tk.Menu(self, tearoff=0)
        if hit_node is not None:
            self.state.selected_node = hit_node
            self.refresh()
            menu.add_command(label="Delete Node", command=self.remove_selected_node)
            menu.add_separator()

            node = self._graph.get_node(hit_node)
            if node is not None:
                for dep_id in node.depends_on:
                    dep_node = self._graph.get_node(dep_id)
                    dep_name = dep_node.display_name if dep_node else dep_id
                    menu.add_command(
                        label=f"Disconnect from {dep_name}",
                        command=lambda sid=dep_id, tid=hit_node: self._disconnect_and_refresh(sid, tid),
                    )
        else:
            menu.add_command(label="Auto Layout", command=self.auto_layout)

        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _disconnect_and_refresh(self, source_id: str, target_id: str) -> None:
        try:
            self._graph.disconnect(source_id, target_id)
        except KeyError:
            pass
        self.refresh()

    def on_node_select(self, callback: Any) -> None:
        self._on_node_select_callback = callback

    def on_node_double_click(self, callback: Any) -> None:
        self._on_node_double_click_callback = callback
