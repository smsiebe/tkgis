"""Attribute table panel — tabular view of layer feature attributes."""
from __future__ import annotations

import io
import tkinter as tk
from typing import Any

import customtkinter as ctk
import pandas as pd

from tkgis.models.events import EventBus, EventType
from tkgis.models.project import Project
from tkgis.panels.base import BasePanel
from tkgis.query.expression import ExpressionError, ExpressionParser
from tkgis.widgets.data_table import DataTableWidget


class AttributeTablePanel(BasePanel):
    """Bottom-docked panel showing feature attributes for the selected layer."""

    name = "attribute_table"
    title = "Attribute Table"
    dock_position = "bottom"
    default_visible = False

    def __init__(self, project: Project, event_bus: EventBus) -> None:
        super().__init__()
        self.project = project
        self.event_bus = event_bus
        self._parser = ExpressionParser()

        # Widget references (assigned in create_widget).
        self._layer_var: tk.StringVar | None = None
        self._layer_menu: ctk.CTkOptionMenu | None = None
        self._filter_var: tk.StringVar | None = None
        self._filter_entry: ctk.CTkEntry | None = None
        self._table: DataTableWidget | None = None
        self._status_label: ctk.CTkLabel | None = None
        self._current_layer_id: str | None = None
        self._current_df: pd.DataFrame = pd.DataFrame()

        # React to layer changes.
        self.event_bus.subscribe(EventType.LAYER_ADDED, self._on_layers_changed)
        self.event_bus.subscribe(EventType.LAYER_REMOVED, self._on_layers_changed)
        self.event_bus.subscribe(EventType.LAYER_SELECTED, self._on_layer_selected)
        self.event_bus.subscribe(EventType.PROJECT_LOADED, self._on_layers_changed)

    # ------------------------------------------------------------------
    # BasePanel interface
    # ------------------------------------------------------------------

    def create_widget(self, parent: Any) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(parent)
        self._widget = frame

        # ---- top bar: layer selector + filter ----
        top_bar = ctk.CTkFrame(frame)
        top_bar.pack(fill="x", padx=2, pady=(2, 0))

        ctk.CTkLabel(top_bar, text="Layer:").pack(side="left", padx=(4, 2))
        self._layer_var = tk.StringVar(value="")
        self._layer_menu = ctk.CTkOptionMenu(
            top_bar,
            values=self._layer_names(),
            variable=self._layer_var,
            command=self._on_layer_dropdown_changed,
            width=180,
        )
        self._layer_menu.pack(side="left", padx=2)

        ctk.CTkLabel(top_bar, text="Filter:").pack(side="left", padx=(12, 2))
        self._filter_var = tk.StringVar(value="")
        self._filter_entry = ctk.CTkEntry(
            top_bar,
            textvariable=self._filter_var,
            placeholder_text="e.g. population > 1000 AND name LIKE '%City%'",
            width=350,
        )
        self._filter_entry.pack(side="left", padx=2, fill="x", expand=True)
        self._filter_entry.bind("<Return>", self._on_filter_apply)

        btn_apply = ctk.CTkButton(top_bar, text="Apply", width=60, command=self._apply_filter)
        btn_apply.pack(side="left", padx=2)
        btn_clear = ctk.CTkButton(top_bar, text="Clear", width=60, command=self._clear_filter)
        btn_clear.pack(side="left", padx=2)

        # ---- data table ----
        self._table = DataTableWidget(frame)
        self._table.pack(fill="both", expand=True, padx=2, pady=2)

        # ---- bottom bar: status + toolbar ----
        bottom_bar = ctk.CTkFrame(frame)
        bottom_bar.pack(fill="x", padx=2, pady=(0, 2))

        self._status_label = ctk.CTkLabel(bottom_bar, text="No layer selected")
        self._status_label.pack(side="left", padx=4)

        # Toolbar buttons (right-aligned).
        btn_export = ctk.CTkButton(
            bottom_bar, text="Export CSV", width=80, command=self._on_export
        )
        btn_export.pack(side="right", padx=2)
        btn_invert = ctk.CTkButton(
            bottom_bar, text="Invert", width=60, command=self._on_invert_selection
        )
        btn_invert.pack(side="right", padx=2)
        btn_deselect = ctk.CTkButton(
            bottom_bar, text="Deselect", width=70, command=self._on_deselect_all
        )
        btn_deselect.pack(side="right", padx=2)
        btn_select_all = ctk.CTkButton(
            bottom_bar, text="Select All", width=70, command=self._on_select_all
        )
        btn_select_all.pack(side="right", padx=2)

        # Bind treeview selection change to update status bar.
        if self._table._tree is not None:
            self._table._tree.bind("<<TreeviewSelect>>", self._on_table_selection, add="+")

        self._refresh_layer_menu()
        return frame

    def on_project_changed(self, project: Any) -> None:
        self.project = project
        self._refresh_layer_menu()
        self._load_layer_data(None)

    # ------------------------------------------------------------------
    # Layer helpers
    # ------------------------------------------------------------------

    def _layer_names(self) -> list[str]:
        """Return display names for all layers in the project."""
        return [layer.name for layer in self.project.layers]

    def _refresh_layer_menu(self) -> None:
        """Update the layer dropdown with current project layers."""
        if self._layer_menu is None:
            return
        names = self._layer_names()
        self._layer_menu.configure(values=names if names else [""])

    def _find_layer_by_name(self, name: str) -> Any:
        """Locate a layer by its display name."""
        for layer in self.project.layers:
            if layer.name == name:
                return layer
        return None

    def _load_layer_data(self, layer_id: str | None) -> None:
        """Load attribute data for the given layer."""
        self._current_layer_id = layer_id
        self._current_df = pd.DataFrame()

        if layer_id is not None:
            layer = self.project.get_layer(layer_id)
            if layer is not None and hasattr(layer, "attributes") and layer.attributes is not None:
                self._current_df = layer.attributes

        if self._table is not None:
            self._table.set_data(self._current_df)
        if self._filter_var is not None:
            self._filter_var.set("")
        self._update_status()

    # ------------------------------------------------------------------
    # Filter
    # ------------------------------------------------------------------

    def _apply_filter(self) -> None:
        """Parse the filter expression and apply it to the table."""
        if self._table is None or self._filter_var is None:
            return
        expr = self._filter_var.get().strip()
        if not expr:
            self._clear_filter()
            return

        try:
            mask = self._parser.parse(expr, self._current_df)
            self._table.filter_rows(mask)
        except ExpressionError as exc:
            self._show_filter_error(str(exc))
            return

        self._update_status()

    def _clear_filter(self) -> None:
        """Remove any active filter."""
        if self._filter_var is not None:
            self._filter_var.set("")
        if self._table is not None:
            self._table.filter_rows(None)
        self._update_status()

    def _on_filter_apply(self, _event: tk.Event) -> None:  # type: ignore[type-arg]
        """Handle <Return> key in the filter entry."""
        self._apply_filter()

    def _show_filter_error(self, message: str) -> None:
        """Display a filter error in the status bar."""
        if self._status_label is not None:
            self._status_label.configure(text=f"Filter error: {message}")

    # ------------------------------------------------------------------
    # Selection toolbar
    # ------------------------------------------------------------------

    def _on_select_all(self) -> None:
        if self._table is not None:
            self._table.select_all()
            self._update_status()

    def _on_deselect_all(self) -> None:
        if self._table is not None:
            self._table.deselect_all()
            self._update_status()

    def _on_invert_selection(self) -> None:
        if self._table is not None:
            self._table.invert_selection()
            self._update_status()

    def _on_export(self) -> None:
        """Export the currently displayed data to CSV via file dialog."""
        if self._table is None or self._current_df.empty:
            return
        from tkinter import filedialog

        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Export Attribute Table",
        )
        if path:
            self._table._display_df.to_csv(path, index=False)

    # ------------------------------------------------------------------
    # Status bar
    # ------------------------------------------------------------------

    def _update_status(self) -> None:
        """Refresh the status label with current counts."""
        if self._status_label is None or self._table is None:
            return

        if self._current_df.empty:
            self._status_label.configure(text="No layer selected")
            return

        showing = self._table.row_count
        total = self._table.total_count
        selected = self._table.selected_count
        self._status_label.configure(
            text=f"Showing {showing} of {total} features ({selected} selected)"
        )

    def _on_table_selection(self, _event: tk.Event) -> None:  # type: ignore[type-arg]
        self._update_status()

    # ------------------------------------------------------------------
    # Event bus handlers
    # ------------------------------------------------------------------

    def _on_layers_changed(self, **_kwargs: Any) -> None:
        self._refresh_layer_menu()

    def _on_layer_selected(self, *, layer_id: str, **_kwargs: Any) -> None:
        """When a layer is selected in the layer tree, show its attributes."""
        layer = self.project.get_layer(layer_id)
        if layer is None:
            return
        if self._layer_var is not None:
            self._layer_var.set(layer.name)
        self._load_layer_data(layer_id)

    def _on_layer_dropdown_changed(self, name: str) -> None:
        """User picked a different layer from the dropdown."""
        layer = self._find_layer_by_name(name)
        if layer is not None:
            self._load_layer_data(layer.id)
