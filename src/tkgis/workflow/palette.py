"""Node palette panel — catalog browser for available processors."""
from __future__ import annotations

import logging
from typing import Any

import customtkinter as ctk

from tkgis.panels.base import BasePanel

logger = logging.getLogger(__name__)

# Try to import processor discovery from grdl-runtime
try:
    from grdl_rt import discover_processors as _discover
except ImportError:
    _discover = None

# Default processor categories and entries when the catalog is empty
_DEFAULT_PROCESSORS: dict[str, list[dict[str, Any]]] = {
    "I/O": [
        {"name": "tkgis.input.raster", "display": "Raster Input", "output_type": "raster"},
        {"name": "tkgis.input.vector", "display": "Vector Input", "output_type": "feature_set"},
        {"name": "tkgis.output.layer", "display": "Layer Output", "input_type": None},
    ],
    "Raster": [
        {"name": "Median", "display": "Median Filter", "input_type": "raster", "output_type": "raster"},
        {"name": "Gaussian", "display": "Gaussian Blur", "input_type": "raster", "output_type": "raster"},
        {"name": "Sharpen", "display": "Sharpen", "input_type": "raster", "output_type": "raster"},
        {"name": "Threshold", "display": "Threshold", "input_type": "raster", "output_type": "raster"},
        {"name": "Normalize", "display": "Normalize", "input_type": "raster", "output_type": "raster"},
    ],
    "Vector": [
        {"name": "Buffer", "display": "Buffer", "input_type": "feature_set", "output_type": "feature_set"},
        {"name": "Clip", "display": "Clip", "input_type": "feature_set", "output_type": "feature_set"},
        {"name": "Dissolve", "display": "Dissolve", "input_type": "feature_set", "output_type": "feature_set"},
    ],
    "Detection": [
        {"name": "CFAR", "display": "CFAR Detector", "input_type": "raster", "output_type": "detection_set"},
        {"name": "BlobDetector", "display": "Blob Detector", "input_type": "raster", "output_type": "detection_set"},
    ],
    "Conversion": [
        {"name": "RasterToVector", "display": "Raster to Vector", "input_type": "raster", "output_type": "feature_set"},
        {"name": "VectorToRaster", "display": "Vector to Raster", "input_type": "feature_set", "output_type": "raster"},
    ],
    "Analysis": [
        {"name": "ZonalStats", "display": "Zonal Statistics", "input_type": "raster", "output_type": "raster"},
        {"name": "Histogram", "display": "Histogram", "input_type": "raster", "output_type": "raster"},
    ],
}

# Type color badges
_TYPE_BADGE_COLORS = {
    "raster": "#89b4fa",
    "feature_set": "#a6e3a1",
    "detection_set": "#fab387",
    None: "#9399b2",
}


class NodePalettePanel(BasePanel):
    """Sidebar panel listing available processors grouped by category.

    Supports search filtering and displays type badges (colored dots).
    """

    name = "node_palette"
    title = "Node Palette"
    dock_position = "left"
    default_visible = False

    def __init__(self) -> None:
        super().__init__()
        self._processors: dict[str, list[dict[str, Any]]] = {}
        self._tree: Any = None
        self._search_var: ctk.StringVar | None = None
        self._selected_processor: str | None = None
        self._selected_meta: dict[str, Any] | None = None
        self._item_map: dict[str, dict[str, Any]] = {}  # tree item id -> proc meta

        # Drag-start callback: (event, processor_name) -> None
        self.on_drag_start: Any = None

    def create_widget(self, parent: Any) -> ctk.CTkFrame:
        """Build and return the palette widget."""
        frame = ctk.CTkFrame(parent, width=220)
        self._widget = frame

        # Search entry
        self._search_var = ctk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._filter_tree())

        search_entry = ctk.CTkEntry(
            frame,
            placeholder_text="Search processors...",
            textvariable=self._search_var,
            height=30,
        )
        search_entry.pack(fill="x", padx=6, pady=(6, 3))

        # Use a tkinter Treeview for the category tree (customtkinter
        # doesn't have a tree widget)
        import tkinter.ttk as ttk

        style = ttk.Style()
        try:
            style.configure(
                "Palette.Treeview",
                background="#1e1e2e",
                foreground="#cdd6f4",
                fieldbackground="#1e1e2e",
                rowheight=26,
            )
            style.map(
                "Palette.Treeview",
                background=[("selected", "#45475a")],
                foreground=[("selected", "#cdd6f4")],
            )
        except Exception:
            pass

        tree_frame = ctk.CTkFrame(frame)
        tree_frame.pack(fill="both", expand=True, padx=6, pady=3)

        self._tree = ttk.Treeview(
            tree_frame,
            style="Palette.Treeview",
            show="tree",
            selectmode="browse",
        )
        scrollbar = ttk.Scrollbar(
            tree_frame, orient="vertical", command=self._tree.yview
        )
        self._tree.configure(yscrollcommand=scrollbar.set)
        self._tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self._tree.bind("<<TreeviewSelect>>", self._on_select)
        self._tree.bind("<ButtonPress-1>", self._on_tree_press)

        # Load processors
        self._load_processors()
        self._populate_tree()

        return frame

    def get_selected_processor(self) -> str | None:
        """Return the currently selected processor name, or None."""
        return self._selected_processor

    def get_selected_meta(self) -> dict[str, Any] | None:
        """Return full metadata for the selected processor."""
        return self._selected_meta

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _load_processors(self) -> None:
        """Discover available processors from grdl-runtime or defaults."""
        self._processors = {}

        if _discover is not None:
            try:
                catalog = _discover()
                if catalog:
                    # Group by category
                    for name, proc_cls in catalog.items():
                        cat = getattr(proc_cls, "category", "Uncategorized") or "Uncategorized"
                        entry = {
                            "name": name,
                            "display": name.rsplit(".", 1)[-1],
                            "input_type": getattr(proc_cls, "input_type", None),
                            "output_type": getattr(proc_cls, "output_type", None),
                        }
                        self._processors.setdefault(cat, []).append(entry)
            except Exception:
                logger.exception("Failed to discover processors")

        # Fall back to defaults if catalog was empty
        if not self._processors:
            self._processors = dict(_DEFAULT_PROCESSORS)

    def _populate_tree(self, filter_text: str = "") -> None:
        """Populate the treeview with categories and processors."""
        if self._tree is None:
            return

        self._tree.delete(*self._tree.get_children())
        self._item_map.clear()
        filter_lower = filter_text.lower()

        for category, procs in sorted(self._processors.items()):
            matching = [
                p
                for p in procs
                if not filter_lower or filter_lower in p["display"].lower()
                or filter_lower in p["name"].lower()
            ]
            if not matching:
                continue

            cat_id = self._tree.insert("", "end", text=f"  {category}", open=True)

            for proc in matching:
                out_type = proc.get("output_type")
                badge = _type_badge_char(out_type)
                display = f"  {badge} {proc['display']}"
                item_id = self._tree.insert(cat_id, "end", text=display)
                self._item_map[item_id] = proc

    def _filter_tree(self) -> None:
        """Rebuild tree with current search filter."""
        if self._search_var is None:
            return
        self._populate_tree(self._search_var.get())

    def _on_select(self, _event: Any) -> None:
        """Handle treeview selection."""
        if self._tree is None:
            return
        selection = self._tree.selection()
        if not selection:
            self._selected_processor = None
            self._selected_meta = None
            return
        item_id = selection[0]
        meta = self._item_map.get(item_id)
        if meta:
            self._selected_processor = meta["name"]
            self._selected_meta = meta
        else:
            self._selected_processor = None
            self._selected_meta = None

    def _on_tree_press(self, event: Any) -> None:
        """Detect drag start on a processor item."""
        if self._tree is None:
            return
        item = self._tree.identify_row(event.y)
        if item and item in self._item_map and self.on_drag_start:
            meta = self._item_map[item]
            self.on_drag_start(event, meta["name"])


def _type_badge_char(output_type: str | None) -> str:
    """Return a unicode circle character colored conceptually by type."""
    # In a Treeview we can't actually color individual characters easily,
    # so we use descriptive emoji-like markers
    mapping = {
        "raster": "\u25cf",       # filled circle
        "feature_set": "\u25a0",  # filled square
        "detection_set": "\u25b2",  # filled triangle
    }
    return mapping.get(output_type, "\u25cb")  # open circle for unknown
