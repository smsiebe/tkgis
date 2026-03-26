"""Layer properties dialog — modal dialog showing layer details and metadata."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any

import customtkinter as ctk

from tkgis.models.layers import Layer


class LayerPropertiesDialog(ctk.CTkToplevel):
    """Modal dialog with General and Metadata tabs for a layer."""

    def __init__(self, parent: Any, layer: Layer) -> None:
        super().__init__(parent)
        self.layer = layer
        self.title(f"Properties \u2014 {layer.name}")
        self.geometry("420x360")
        self.resizable(False, False)

        # Make modal.
        self.transient(parent)
        self.grab_set()

        self._build_ui()

        # Center on parent.
        self.update_idletasks()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        # Tab view
        self._tabview = ctk.CTkTabview(self, width=400, height=300)
        self._tabview.pack(fill="both", expand=True, padx=8, pady=(8, 4))

        self._tabview.add("General")
        self._tabview.add("Metadata")

        self._build_general_tab(self._tabview.tab("General"))
        self._build_metadata_tab(self._tabview.tab("Metadata"))

        # Close button
        close_btn = ctk.CTkButton(self, text="Close", width=80, command=self._on_close)
        close_btn.pack(pady=(0, 8))

    def _build_general_tab(self, tab: Any) -> None:
        fields: list[tuple[str, str]] = [
            ("Name", self.layer.name),
            ("Type", self.layer.layer_type.value),
            ("Source", self.layer.source_path or "(none)"),
            ("CRS", self._format_crs()),
            ("Extent", self._format_extent()),
            ("Features", self._format_feature_count()),
        ]

        for row, (label, value) in enumerate(fields):
            ctk.CTkLabel(tab, text=f"{label}:", anchor="e", width=80).grid(
                row=row, column=0, padx=(8, 4), pady=3, sticky="e"
            )
            entry = ctk.CTkEntry(tab, width=280)
            entry.insert(0, value)
            entry.configure(state="disabled")
            entry.grid(row=row, column=1, padx=(0, 8), pady=3, sticky="w")

    def _build_metadata_tab(self, tab: Any) -> None:
        tree_frame = ctk.CTkFrame(tab)
        tree_frame.pack(fill="both", expand=True, padx=4, pady=4)

        columns = ("key", "value")
        self._meta_tree = ttk.Treeview(
            tree_frame, columns=columns, show="headings", height=10
        )
        self._meta_tree.heading("key", text="Key")
        self._meta_tree.heading("value", text="Value")
        self._meta_tree.column("key", width=120)
        self._meta_tree.column("value", width=250)
        self._meta_tree.pack(fill="both", expand=True)

        for key, val in self.layer.metadata.items():
            self._meta_tree.insert("", "end", values=(str(key), str(val)))

    # ------------------------------------------------------------------
    # Formatting helpers
    # ------------------------------------------------------------------

    def _format_crs(self) -> str:
        if self.layer.crs is None:
            return "(unknown)"
        if self.layer.crs.epsg_code:
            return f"EPSG:{self.layer.crs.epsg_code}"
        return self.layer.crs.name or "(unknown)"

    def _format_extent(self) -> str:
        b = self.layer.bounds
        if b is None:
            return "(unknown)"
        return f"({b.xmin:.4f}, {b.ymin:.4f}) \u2013 ({b.xmax:.4f}, {b.ymax:.4f})"

    def _format_feature_count(self) -> str:
        count = self.layer.metadata.get("feature_count")
        if count is not None:
            return str(count)
        return "(n/a)"

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _on_close(self) -> None:
        self.grab_release()
        self.destroy()
