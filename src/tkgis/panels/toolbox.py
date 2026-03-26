"""Processing toolbox panel — searchable catalog of available processors."""
from __future__ import annotations

import logging
import tkinter as tk
from typing import Any

import customtkinter as ctk

from tkgis.panels.base import BasePanel

try:
    import grdl_rt
except ImportError:  # pragma: no cover
    grdl_rt = None  # type: ignore[assignment]

# Attempt ttkbootstrap; fall back to plain ttk.
try:
    from ttkbootstrap import Treeview  # type: ignore[import-untyped]
except ImportError:  # pragma: no cover
    from tkinter.ttk import Treeview  # type: ignore[assignment]

logger = logging.getLogger(__name__)


class ProcessingToolboxPanel(BasePanel):
    """Searchable tree of available grdl-runtime processors.

    The panel discovers processors via :func:`grdl_rt.discover_processors`
    and groups them by category.  A search entry filters the list in
    real-time.
    """

    name = "processing_toolbox"
    title = "Processing"
    dock_position = "right"
    default_visible = False

    def __init__(self, event_bus: Any | None = None) -> None:
        super().__init__()
        self._event_bus = event_bus
        self._catalog: dict[str, Any] = {}
        self._search_var: tk.StringVar | None = None
        self._tree: Treeview | None = None

    # ------------------------------------------------------------------
    # BasePanel interface
    # ------------------------------------------------------------------

    def create_widget(self, parent: Any) -> ctk.CTkFrame:
        """Build and return the panel's root frame."""
        frame = ctk.CTkFrame(parent)
        self._widget = frame

        # --- Search entry ---
        search_frame = ctk.CTkFrame(frame)
        search_frame.pack(fill="x", padx=4, pady=(4, 0))

        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", self._on_search_changed)

        search_entry = ctk.CTkEntry(
            search_frame,
            textvariable=self._search_var,
            placeholder_text="Search processors…",
        )
        search_entry.pack(fill="x", padx=2, pady=2)

        # --- Processor tree ---
        tree_frame = ctk.CTkFrame(frame)
        tree_frame.pack(fill="both", expand=True, padx=4, pady=4)

        self._tree = Treeview(
            tree_frame,
            columns=("description",),
            show="tree headings",
            selectmode="browse",
        )
        self._tree.heading("#0", text="Processor")
        self._tree.heading("description", text="Description")
        self._tree.column("#0", width=180, stretch=False)
        self._tree.column("description", width=220)

        scrollbar = ctk.CTkScrollbar(tree_frame, command=self._tree.yview)
        self._tree.configure(yscrollcommand=scrollbar.set)

        self._tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Populate catalog
        self._refresh_catalog()

        return frame

    # ------------------------------------------------------------------
    # Catalog
    # ------------------------------------------------------------------

    def _refresh_catalog(self) -> None:
        """Discover processors and populate the tree."""
        if grdl_rt is None:
            logger.warning("grdl-runtime not available — toolbox will be empty.")
            return

        try:
            self._catalog = grdl_rt.discover_processors()
        except Exception:
            logger.exception("Failed to discover processors.")
            self._catalog = {}

        self._populate_tree()

    def _populate_tree(self, filter_text: str = "") -> None:
        """Fill the tree view, optionally filtered by *filter_text*."""
        if self._tree is None:
            return

        # Clear existing items
        for item in self._tree.get_children():
            self._tree.delete(item)

        # Group by category using Artifact tags or processor_type
        categories: dict[str, list[tuple[str, str]]] = {}
        ft = filter_text.lower()

        for name, artifact_or_cls in self._catalog.items():
            # Artifact objects have description; classes may not
            desc = ""
            category = "Uncategorized"

            if hasattr(artifact_or_cls, "description"):
                desc = artifact_or_cls.description or ""
            if hasattr(artifact_or_cls, "processor_type") and artifact_or_cls.processor_type:
                category = artifact_or_cls.processor_type
            elif hasattr(artifact_or_cls, "tags") and artifact_or_cls.tags:
                cats = artifact_or_cls.tags.get("category", [])
                if cats:
                    category = cats[0]

            if ft and ft not in name.lower() and ft not in desc.lower():
                continue

            categories.setdefault(category, []).append((name, desc))

        # Insert into tree
        for category in sorted(categories):
            cat_id = self._tree.insert("", "end", text=category, open=True)
            for proc_name, proc_desc in sorted(categories[category]):
                self._tree.insert(
                    cat_id, "end", text=proc_name, values=(proc_desc,)
                )

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def _on_search_changed(self, *_args: Any) -> None:
        """Re-filter tree when search text changes."""
        if self._search_var is not None:
            self._populate_tree(self._search_var.get())

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def get_selected_processor(self) -> str | None:
        """Return the name of the currently selected processor, or *None*."""
        if self._tree is None:
            return None
        selection = self._tree.selection()
        if not selection:
            return None
        item = selection[0]
        # Only leaf items (not categories) represent processors
        if self._tree.get_children(item):
            return None
        return self._tree.item(item, "text")
