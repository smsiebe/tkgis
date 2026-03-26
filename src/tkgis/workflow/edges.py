"""Edge rendering and connection validation for the workflow canvas."""
from __future__ import annotations

import tkinter as tk
from typing import Any

# Type colors shared with canvas
TYPE_COLORS = {
    "raster": "#89b4fa",
    "feature_set": "#a6e3a1",
    "detection_set": "#fab387",
    None: "#9399b2",
}


class EdgeRenderer:
    """Static methods for drawing edges on a tkinter Canvas."""

    @staticmethod
    def draw_edge(
        canvas: tk.Canvas,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        data_type: str | None = None,
        selected: bool = False,
    ) -> int:
        """Draw a smooth bezier-like edge between two points.

        Returns the canvas item ID.
        """
        color = TYPE_COLORS.get(data_type, TYPE_COLORS[None])
        width = 3.0 if selected else 2.0

        # Compute control points for a horizontal bezier
        dx = abs(x2 - x1) * 0.5
        cx1 = x1 + dx
        cy1 = y1
        cx2 = x2 - dx
        cy2 = y2

        item = canvas.create_line(
            x1, y1, cx1, cy1, cx2, cy2, x2, y2,
            smooth=True,
            splinesteps=36,
            fill=color,
            width=width,
            tags=("edge",),
        )
        return item

    @staticmethod
    def draw_rubber_band(
        canvas: tk.Canvas,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
    ) -> int:
        """Draw a temporary dashed rubber-band edge during connection drag.

        Returns the canvas item ID.
        """
        dx = abs(x2 - x1) * 0.5
        cx1 = x1 + dx
        cy1 = y1
        cx2 = x2 - dx
        cy2 = y2

        item = canvas.create_line(
            x1, y1, cx1, cy1, cx2, cy2, x2, y2,
            smooth=True,
            splinesteps=36,
            fill="#f5c2e7",
            width=2.0,
            dash=(6, 4),
            tags=("rubber_band",),
        )
        return item


class ConnectionValidator:
    """Validates whether two nodes can be connected."""

    @staticmethod
    def can_connect(
        graph: Any,
        source_id: str,
        target_id: str,
    ) -> tuple[bool, str]:
        """Check whether *source_id* can connect to *target_id*.

        Parameters
        ----------
        graph
            A WorkflowGraph or fallback graph instance.
        source_id, target_id
            Node step IDs.

        Returns
        -------
        tuple[bool, str]
            ``(True, "")`` if valid, ``(False, reason)`` otherwise.
        """
        # Self-loop check
        if source_id == target_id:
            return False, "Cannot connect a node to itself"

        # Check nodes exist
        source_node = graph.get_node(source_id)
        target_node = graph.get_node(target_id)
        if source_node is None:
            return False, f"Source node '{source_id}' not found"
        if target_node is None:
            return False, f"Target node '{target_id}' not found"

        # Type compatibility — None means accepts/produces anything
        source_out = source_node.output_type
        target_in = target_node.input_type
        if source_out is not None and target_in is not None:
            if source_out != target_in:
                return False, (
                    f"Type mismatch: '{source_out}' -> '{target_in}'"
                )

        # Check for duplicate edge
        for edge in graph.get_edges():
            if edge.source_id == source_id and edge.target_id == target_id:
                return False, "Connection already exists"

        return True, ""
