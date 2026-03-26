"""Visual node graph editor canvas for the workflow builder."""
from __future__ import annotations

import logging
import math
import tkinter as tk
from dataclasses import dataclass, field
from typing import Any

from tkgis.workflow.edges import ConnectionValidator, EdgeRenderer, TYPE_COLORS

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# grdl-runtime import (optional)
# ---------------------------------------------------------------------------

try:
    from grdl_rt.execution.graph import WorkflowGraph, NodeInfo, EdgeInfo
    from grdl_rt.execution.workflow import WorkflowDefinition, ProcessingStep

    _HAS_GRDL_RT = True
except ImportError:
    WorkflowGraph = None  # type: ignore[assignment,misc]
    _HAS_GRDL_RT = False

# ---------------------------------------------------------------------------
# Fallback data classes — always defined so the fallback graph and tests
# work regardless of whether grdl-runtime is installed.
# ---------------------------------------------------------------------------


@dataclass
class _FallbackNodeInfo:
    """Lightweight stand-in for ``grdl_rt.execution.graph.NodeInfo``."""

    step_id: str = ""
    processor_name: str = ""
    processor_version: str | None = None
    display_name: str = ""
    category: str | None = None
    input_type: str | None = None
    output_type: str | None = None
    output_ports: dict[str, str] | None = None
    params: dict[str, Any] = field(default_factory=dict)
    param_specs: dict[str, dict] = field(default_factory=dict)
    depends_on: list[str] = field(default_factory=list)
    phase: str | None = None
    position: tuple[float, float] | None = None


@dataclass
class _FallbackEdgeInfo:
    """Lightweight stand-in for ``grdl_rt.execution.graph.EdgeInfo``."""

    source_id: str = ""
    source_port: str | None = None
    target_id: str = ""
    target_port: str | None = None
    data_type: str | None = None


class _FallbackGraph:
    """Minimal local graph when grdl-runtime is unavailable.

    Provides the same CRUD API as ``WorkflowGraph`` so the canvas, tests,
    and connection validator can operate without a runtime dependency.
    """

    def __init__(self) -> None:
        self._nodes: dict[str, _FallbackNodeInfo] = {}
        self._edges: list[_FallbackEdgeInfo] = []
        self._counter = 0

    def get_nodes(self) -> list[_FallbackNodeInfo]:
        return list(self._nodes.values())

    def get_edges(self) -> list[_FallbackEdgeInfo]:
        return list(self._edges)

    def get_node(self, step_id: str) -> _FallbackNodeInfo | None:
        return self._nodes.get(step_id)

    def add_node(
        self,
        processor_name: str,
        params: dict[str, Any] | None = None,
        position: tuple[float, float] | None = None,
        *,
        input_type: str | None = None,
        output_type: str | None = None,
    ) -> str:
        step_id = f"step_{self._counter}"
        self._counter += 1
        display = processor_name.rsplit(".", 1)[-1]
        self._nodes[step_id] = _FallbackNodeInfo(
            step_id=step_id,
            processor_name=processor_name,
            display_name=display,
            input_type=input_type,
            output_type=output_type,
            params=params or {},
            position=position,
        )
        return step_id

    def remove_node(self, step_id: str) -> None:
        if step_id not in self._nodes:
            raise KeyError(f"No node with id '{step_id}'")
        del self._nodes[step_id]
        self._edges = [
            e
            for e in self._edges
            if e.source_id != step_id and e.target_id != step_id
        ]
        for node in self._nodes.values():
            node.depends_on = [d for d in node.depends_on if d != step_id]

    def connect(
        self,
        source_id: str,
        target_id: str,
        source_port: str | None = None,
        target_port: str | None = None,
    ) -> None:
        source = self._nodes.get(source_id)
        target = self._nodes.get(target_id)
        if source is None:
            raise KeyError(f"No node with id '{source_id}'")
        if target is None:
            raise KeyError(f"No node with id '{target_id}'")
        if source_id not in target.depends_on:
            target.depends_on.append(source_id)
        self._edges.append(
            _FallbackEdgeInfo(
                source_id=source_id,
                source_port=source_port,
                target_id=target_id,
                target_port=target_port,
                data_type=source.output_type,
            )
        )

    def disconnect(self, source_id: str, target_id: str) -> None:
        target = self._nodes.get(target_id)
        if target is not None:
            target.depends_on = [d for d in target.depends_on if d != source_id]
        self._edges = [
            e
            for e in self._edges
            if not (e.source_id == source_id and e.target_id == target_id)
        ]

    def update_node_params(self, step_id: str, params: dict) -> None:
        node = self._nodes.get(step_id)
        if node is None:
            raise KeyError(f"No node with id '{step_id}'")
        node.params.update(params)

    def update_node_position(
        self, step_id: str, position: tuple[float, float]
    ) -> None:
        node = self._nodes.get(step_id)
        if node is None:
            raise KeyError(f"No node with id '{step_id}'")
        node.position = position

    def validate(self) -> list[str]:
        errors: list[str] = []
        for edge in self._edges:
            src = self._nodes.get(edge.source_id)
            tgt = self._nodes.get(edge.target_id)
            if src is None:
                errors.append(f"Missing source node '{edge.source_id}'")
            if tgt is None:
                errors.append(f"Missing target node '{edge.target_id}'")
            if src and tgt:
                if (
                    src.output_type is not None
                    and tgt.input_type is not None
                    and src.output_type != tgt.input_type
                ):
                    errors.append(
                        f"Type mismatch: {edge.source_id} outputs "
                        f"'{src.output_type}' but {edge.target_id} "
                        f"expects '{tgt.input_type}'"
                    )
        return errors

    def topological_levels(self) -> list[list[str]]:
        in_degree: dict[str, int] = {nid: 0 for nid in self._nodes}
        children: dict[str, list[str]] = {nid: [] for nid in self._nodes}
        for edge in self._edges:
            if edge.target_id in in_degree:
                in_degree[edge.target_id] += 1
            if edge.source_id in children:
                children[edge.source_id].append(edge.target_id)

        levels: list[list[str]] = []
        queue = [nid for nid, deg in in_degree.items() if deg == 0]
        while queue:
            levels.append(sorted(queue))
            next_queue: list[str] = []
            for nid in queue:
                for child in children.get(nid, []):
                    in_degree[child] -= 1
                    if in_degree[child] == 0:
                        next_queue.append(child)
            queue = next_queue
        return levels


# ---------------------------------------------------------------------------
# Factory helpers
# ---------------------------------------------------------------------------


def create_fallback_graph() -> _FallbackGraph:
    """Create a fallback graph instance for use without grdl-runtime."""
    return _FallbackGraph()


def create_graph() -> Any:
    """Create a graph, preferring grdl-runtime if available."""
    if _HAS_GRDL_RT:
        wd = WorkflowDefinition(name="untitled")
        return WorkflowGraph(wd)
    return create_fallback_graph()


# ---------------------------------------------------------------------------
# WorkflowCanvas
# ---------------------------------------------------------------------------


class WorkflowCanvas(tk.Canvas):
    """Visual node graph editor.

    Renders nodes as rounded rectangles with colored headers, ports as
    circles on the left (input) and right (output) edges, and connections
    as smooth bezier curves.
    """

    NODE_WIDTH = 180
    NODE_HEIGHT = 80
    PORT_RADIUS = 6
    GRID_SIZE = 20

    # Background and theme
    BG_COLOR = "#1e1e2e"
    GRID_COLOR = "#313244"
    NODE_BG = "#313244"
    NODE_BORDER = "#45475a"
    NODE_SELECTED_BORDER = "#cba6f7"
    TEXT_COLOR = "#cdd6f4"
    TEXT_DIM = "#9399b2"

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

        # Visual state
        self._selected_node: str | None = None
        self._node_items: dict[str, list[int]] = {}
        self._edge_items: list[int] = []
        self._port_positions: dict[str, dict[str, tuple[float, float]]] = {}

        # Interaction state
        self._dragging_node: str | None = None
        self._drag_offset: tuple[float, float] = (0.0, 0.0)
        self._connecting: bool = False
        self._connect_source: str | None = None
        self._connect_start: tuple[float, float] = (0.0, 0.0)
        self._rubber_band_id: int | None = None

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

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def refresh(self) -> None:
        """Re-render the entire graph from the backend data."""
        self.delete("all")
        self._node_items.clear()
        self._edge_items.clear()
        self._port_positions.clear()

        self._draw_grid()

        # Render nodes first so port_positions are populated for edges
        for node in self._graph.get_nodes():
            self._render_node(node.step_id)

        # Render edges on top
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
        """Add a new node at canvas coordinates ``(x, y)``.

        Snaps to GRID_SIZE.  Returns the new step ID.
        """
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
        """Delete the currently selected node and its edges."""
        if self._selected_node is None:
            return
        try:
            self._graph.remove_node(self._selected_node)
        except KeyError:
            pass
        self._selected_node = None
        self.refresh()

    def get_selected_node(self) -> str | None:
        return self._selected_node

    def show_validation_errors(self, errors: list[str]) -> None:
        """Highlight nodes mentioned in validation *errors*."""
        self.delete("validation_error")

        for error in errors:
            for node in self._graph.get_nodes():
                if node.step_id in error:
                    pos = node.position or (0, 0)
                    x, y = pos
                    self.create_rectangle(
                        x - 4,
                        y - 4,
                        x + self.NODE_WIDTH + 4,
                        y + self.NODE_HEIGHT + 4,
                        outline="#f38ba8",
                        width=3,
                        dash=(4, 4),
                        tags=("validation_error",),
                    )

    def auto_layout(self) -> None:
        """Apply a Sugiyama-style topological layout to all nodes.

        Arranges nodes in columns by topological level, centered vertically.
        """
        try:
            levels = self._graph.topological_levels()
        except (ValueError, AttributeError):
            return

        h_spacing = self.NODE_WIDTH + 60
        v_spacing = self.NODE_HEIGHT + 40
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

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def _draw_grid(self) -> None:
        """Draw a subtle dot grid on the background."""
        w = max(int(self.cget("width") or 2000), 2000)
        h = max(int(self.cget("height") or 1500), 1500)
        for gx in range(0, w, self.GRID_SIZE * 5):
            for gy in range(0, h, self.GRID_SIZE * 5):
                self.create_oval(
                    gx - 1, gy - 1, gx + 1, gy + 1,
                    fill=self.GRID_COLOR,
                    outline="",
                    tags=("grid",),
                )

    def _render_node(self, step_id: str) -> None:
        """Draw a single node on the canvas."""
        node = self._graph.get_node(step_id)
        if node is None:
            return

        pos = node.position or (100, 100)
        x, y = pos
        w = self.NODE_WIDTH
        h = self.NODE_HEIGHT
        header_h = 24

        is_selected = step_id == self._selected_node
        border_color = self.NODE_SELECTED_BORDER if is_selected else self.NODE_BORDER
        header_color = TYPE_COLORS.get(node.output_type, TYPE_COLORS[None])

        items: list[int] = []

        # Node body
        body = self.create_rectangle(
            x, y, x + w, y + h,
            fill=self.NODE_BG,
            outline=border_color,
            width=2 if is_selected else 1,
            tags=("node", f"node_{step_id}"),
        )
        items.append(body)

        # Header bar
        header = self.create_rectangle(
            x + 1, y + 1, x + w - 1, y + header_h,
            fill=header_color,
            outline="",
            tags=("node", f"node_{step_id}"),
        )
        items.append(header)

        # Title text
        title = self.create_text(
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
        param_text = ", ".join(
            f"{k}={v}" for k, v in list(node.params.items())[:3]
        )
        if len(param_text) > 28:
            param_text = param_text[:25] + "..."
        if param_text:
            ptext = self.create_text(
                x + 10,
                y + header_h + 12,
                text=param_text,
                fill=self.TEXT_DIM,
                font=("Segoe UI", 8),
                anchor="w",
                tags=("node", f"node_{step_id}"),
            )
            items.append(ptext)

        # Type badge at bottom
        type_label = node.output_type or "any"
        badge = self.create_text(
            x + w - 10,
            y + h - 10,
            text=type_label,
            fill=self.TEXT_DIM,
            font=("Segoe UI", 7, "italic"),
            anchor="e",
            tags=("node", f"node_{step_id}"),
        )
        items.append(badge)

        # Input port (left side)
        port_y = y + h // 2
        input_port = self.create_oval(
            x - self.PORT_RADIUS,
            port_y - self.PORT_RADIUS,
            x + self.PORT_RADIUS,
            port_y + self.PORT_RADIUS,
            fill=TYPE_COLORS.get(node.input_type, TYPE_COLORS[None]),
            outline="#1e1e2e",
            width=2,
            tags=("port", "input_port", f"port_{step_id}_in"),
        )
        items.append(input_port)

        # Output port (right side)
        output_port = self.create_oval(
            x + w - self.PORT_RADIUS,
            port_y - self.PORT_RADIUS,
            x + w + self.PORT_RADIUS,
            port_y + self.PORT_RADIUS,
            fill=TYPE_COLORS.get(node.output_type, TYPE_COLORS[None]),
            outline="#1e1e2e",
            width=2,
            tags=("port", "output_port", f"port_{step_id}_out"),
        )
        items.append(output_port)

        # Store port positions for edge drawing
        self._port_positions[step_id] = {
            "input": (x, port_y),
            "output": (x + w, port_y),
        }

        self._node_items[step_id] = items

    def _render_edge(self, source_id: str, target_id: str) -> None:
        """Draw a bezier edge between two nodes."""
        src_ports = self._port_positions.get(source_id)
        tgt_ports = self._port_positions.get(target_id)

        if src_ports is None:
            src_node = self._graph.get_node(source_id)
            if src_node is None:
                return
            pos = src_node.position or (100, 100)
            src_ports = {
                "output": (pos[0] + self.NODE_WIDTH, pos[1] + self.NODE_HEIGHT // 2)
            }
        if tgt_ports is None:
            tgt_node = self._graph.get_node(target_id)
            if tgt_node is None:
                return
            pos = tgt_node.position or (100, 100)
            tgt_ports = {
                "input": (pos[0], pos[1] + self.NODE_HEIGHT // 2)
            }

        x1, y1 = src_ports["output"]
        x2, y2 = tgt_ports["input"]

        src_node = self._graph.get_node(source_id)
        data_type = src_node.output_type if src_node else None

        item = EdgeRenderer.draw_edge(self, x1, y1, x2, y2, data_type=data_type)
        self._edge_items.append(item)

    # ------------------------------------------------------------------
    # Interaction handlers
    # ------------------------------------------------------------------

    def _hit_test_port(
        self, x: float, y: float
    ) -> tuple[str | None, str | None]:
        """Return ``(step_id, "input"|"output")`` or ``(None, None)``."""
        for step_id, ports in self._port_positions.items():
            for port_name, (px, py) in ports.items():
                dist = math.hypot(x - px, y - py)
                if dist <= self.PORT_RADIUS + 4:
                    return step_id, port_name
        return None, None

    def _hit_test_node(self, x: float, y: float) -> str | None:
        """Return step_id if *(x, y)* hits a node body, else ``None``."""
        for node in self._graph.get_nodes():
            pos = node.position or (0, 0)
            nx, ny = pos
            if nx <= x <= nx + self.NODE_WIDTH and ny <= y <= ny + self.NODE_HEIGHT:
                return node.step_id
        return None

    def _on_press(self, event: tk.Event) -> None:
        x, y = self.canvasx(event.x), self.canvasy(event.y)

        step_id, port_name = self._hit_test_port(x, y)
        if step_id is not None and port_name == "output":
            self._connecting = True
            self._connect_source = step_id
            ports = self._port_positions.get(step_id, {})
            self._connect_start = ports.get("output", (x, y))
            return

        hit_node = self._hit_test_node(x, y)
        old_selected = self._selected_node
        self._selected_node = hit_node

        if hit_node is not None:
            node = self._graph.get_node(hit_node)
            if node and node.position:
                self._drag_offset = (x - node.position[0], y - node.position[1])
            else:
                self._drag_offset = (0.0, 0.0)
            self._dragging_node = hit_node

        if old_selected != self._selected_node:
            self.refresh()
            if self._on_node_select_callback and self._selected_node:
                self._on_node_select_callback(self._selected_node)

    def _on_drag(self, event: tk.Event) -> None:
        x, y = self.canvasx(event.x), self.canvasy(event.y)

        if self._connecting and self._connect_source is not None:
            self.delete("rubber_band")
            sx, sy = self._connect_start
            self._rubber_band_id = EdgeRenderer.draw_rubber_band(self, sx, sy, x, y)
            return

        if self._dragging_node is not None:
            new_x = round((x - self._drag_offset[0]) / self.GRID_SIZE) * self.GRID_SIZE
            new_y = round((y - self._drag_offset[1]) / self.GRID_SIZE) * self.GRID_SIZE
            self._graph.update_node_position(self._dragging_node, (new_x, new_y))
            self.refresh()

    def _on_release(self, event: tk.Event) -> None:
        x, y = self.canvasx(event.x), self.canvasy(event.y)

        if self._connecting and self._connect_source is not None:
            self.delete("rubber_band")
            self._rubber_band_id = None

            target_id, port_name = self._hit_test_port(x, y)
            if target_id is None:
                target_id = self._hit_test_node(x, y)
                port_name = "input"

            if target_id is not None and port_name == "input":
                ok, reason = ConnectionValidator.can_connect(
                    self._graph, self._connect_source, target_id
                )
                if ok:
                    try:
                        self._graph.connect(self._connect_source, target_id)
                    except (KeyError, ValueError) as exc:
                        logger.warning("Connection failed: %s", exc)
                else:
                    logger.info("Connection rejected: %s", reason)

            self._connecting = False
            self._connect_source = None
            self.refresh()
            return

        self._dragging_node = None

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
            self._selected_node = hit_node
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

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------

    def on_node_select(self, callback: Any) -> None:
        """Register a callback for node selection: ``callback(step_id)``."""
        self._on_node_select_callback = callback

    def on_node_double_click(self, callback: Any) -> None:
        """Register a callback for double-click: ``callback(step_id)``."""
        self._on_node_double_click_callback = callback
