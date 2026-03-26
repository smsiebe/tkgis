"""Drag-and-drop support from the node palette to the workflow canvas."""
from __future__ import annotations

import tkinter as tk
from typing import Any


class PaletteToCanvasDnD:
    """Manages drag-and-drop of processor nodes from the palette onto the canvas.

    Displays a ghost label under the cursor during the drag and adds a new
    node at the drop position, snapped to the canvas grid.
    """

    def __init__(self, palette: Any, canvas: Any) -> None:
        self._palette = palette
        self._canvas = canvas
        self._drag_label: tk.Label | None = None
        self._processor_name: str | None = None
        self._processor_meta: dict[str, Any] | None = None

        # Wire up the palette's drag-start hook
        palette.on_drag_start = self.start_drag

    def start_drag(self, event: tk.Event, processor_name: str) -> None:
        """Begin dragging a processor from the palette.

        Creates a floating ghost label that follows the cursor.
        """
        self._processor_name = processor_name

        # Try to get full metadata from the palette
        meta = None
        if hasattr(self._palette, "get_selected_meta"):
            meta = self._palette.get_selected_meta()
        self._processor_meta = meta

        # Create ghost label on the top-level window
        root = self._canvas.winfo_toplevel()
        display = processor_name.rsplit(".", 1)[-1]
        self._drag_label = tk.Label(
            root,
            text=f"  {display}  ",
            bg="#585b70",
            fg="#cdd6f4",
            font=("Segoe UI", 10),
            relief="solid",
            borderwidth=1,
        )
        self._drag_label.place(x=event.x_root - root.winfo_rootx(), y=event.y_root - root.winfo_rooty())

        # Bind mouse events on the root for tracking
        root.bind("<B1-Motion>", self.on_drag, add="+")
        root.bind("<ButtonRelease-1>", self.on_drop, add="+")

    def on_drag(self, event: tk.Event) -> None:
        """Update ghost label position during drag."""
        if self._drag_label is None:
            return
        root = self._canvas.winfo_toplevel()
        self._drag_label.place(
            x=event.x_root - root.winfo_rootx() + 10,
            y=event.y_root - root.winfo_rooty() + 10,
        )

    def on_drop(self, event: tk.Event) -> None:
        """Handle drop: add a node at the canvas drop position."""
        root = self._canvas.winfo_toplevel()
        root.unbind("<B1-Motion>")
        root.unbind("<ButtonRelease-1>")

        if self._drag_label is not None:
            self._drag_label.destroy()
            self._drag_label = None

        if self._processor_name is None:
            return

        # Convert screen coords to canvas coords
        canvas_x = event.x_root - self._canvas.winfo_rootx()
        canvas_y = event.y_root - self._canvas.winfo_rooty()

        # Check if the drop is within the canvas area
        if canvas_x < 0 or canvas_y < 0:
            self._processor_name = None
            self._processor_meta = None
            return

        cx = self._canvas.canvasx(canvas_x)
        cy = self._canvas.canvasy(canvas_y)

        # Extract type info from metadata
        input_type = None
        output_type = None
        if self._processor_meta:
            input_type = self._processor_meta.get("input_type")
            output_type = self._processor_meta.get("output_type")

        self._canvas.add_node_at(
            self._processor_name,
            cx,
            cy,
            input_type=input_type,
            output_type=output_type,
        )

        self._processor_name = None
        self._processor_meta = None
