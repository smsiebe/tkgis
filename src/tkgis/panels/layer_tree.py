"""Layer tree panel — tree view for organizing, styling, and controlling layers."""
from __future__ import annotations

import tkinter as tk
from typing import Any

import customtkinter as ctk

from tkgis.models.events import EventBus, EventType
from tkgis.models.layers import Layer, LayerType
from tkgis.models.project import Project
from tkgis.panels.base import BasePanel

# Attempt ttkbootstrap; fall back to plain ttk.
try:
    from ttkbootstrap import Treeview  # type: ignore[import-untyped]
except ImportError:  # pragma: no cover
    from tkinter.ttk import Treeview  # type: ignore[assignment]

# Simple text symbols for layer types.
_LAYER_ICONS: dict[LayerType, str] = {
    LayerType.RASTER: "\u25a3",          # square with fill
    LayerType.VECTOR: "\u25b3",          # triangle
    LayerType.TEMPORAL_RASTER: "\u29d6", # hourglass-like
    LayerType.TEMPORAL_VECTOR: "\u29d7",
    LayerType.ANNOTATION: "\u270e",      # pencil
}

# Colormaps offered in the quick-style dropdown.
_COLORMAPS = ["", "gray", "viridis", "plasma", "inferno", "magma", "cividis", "jet"]


class LayerTreePanel(BasePanel):
    """Tree-based layer manager panel."""

    name = "layer_tree"
    title = "Layers"
    dock_position = "left"
    default_visible = True

    def __init__(self, project: Project, event_bus: EventBus) -> None:
        super().__init__()
        self.project = project
        self.event_bus = event_bus
        self._tree: Treeview | None = None
        self._opacity_var: tk.DoubleVar | None = None
        self._colormap_var: tk.StringVar | None = None

        # React to external layer changes.
        self.event_bus.subscribe(EventType.LAYER_ADDED, self._on_external_change)
        self.event_bus.subscribe(EventType.LAYER_REMOVED, self._on_external_change)
        self.event_bus.subscribe(EventType.LAYER_ORDER_CHANGED, self._on_external_change)
        self.event_bus.subscribe(EventType.PROJECT_LOADED, self._on_external_change)

    # ------------------------------------------------------------------
    # BasePanel interface
    # ------------------------------------------------------------------

    def create_widget(self, parent: Any) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(parent)
        self._widget = frame

        # ---- toolbar ----
        toolbar = ctk.CTkFrame(frame)
        toolbar.pack(fill="x", padx=2, pady=(2, 0))

        self._btn_add = ctk.CTkButton(toolbar, text="+", width=30, command=self._on_add_layer)
        self._btn_add.pack(side="left", padx=1)
        self._btn_remove = ctk.CTkButton(toolbar, text="\u2212", width=30, command=self._on_remove_layer)
        self._btn_remove.pack(side="left", padx=1)
        self._btn_up = ctk.CTkButton(toolbar, text="\u25b2", width=30, command=self._on_move_up)
        self._btn_up.pack(side="left", padx=1)
        self._btn_down = ctk.CTkButton(toolbar, text="\u25bc", width=30, command=self._on_move_down)
        self._btn_down.pack(side="left", padx=1)

        # ---- treeview ----
        tree_frame = ctk.CTkFrame(frame)
        tree_frame.pack(fill="both", expand=True, padx=2, pady=2)

        columns = ("visible", "name")
        self._tree = Treeview(
            tree_frame,
            columns=columns,
            show="tree headings",
            selectmode="browse",
        )
        self._tree.heading("#0", text="")
        self._tree.column("#0", width=30, stretch=False)
        self._tree.heading("visible", text="\u2713")
        self._tree.column("visible", width=30, stretch=False, anchor="center")
        self._tree.heading("name", text="Layer")
        self._tree.column("name", width=150, stretch=True)

        self._tree.pack(fill="both", expand=True)
        self._tree.bind("<Button-1>", self._on_click)
        self._tree.bind("<Double-1>", self._on_double_click)
        self._tree.bind("<Button-3>", self._on_context_menu)
        self._tree.bind("<<TreeviewSelect>>", self._on_selection_changed)

        # ---- quick style controls ----
        style_frame = ctk.CTkFrame(frame)
        style_frame.pack(fill="x", padx=2, pady=(0, 2))

        ctk.CTkLabel(style_frame, text="Opacity:").pack(side="left", padx=(4, 2))
        self._opacity_var = tk.DoubleVar(value=1.0)
        self._opacity_slider = ctk.CTkSlider(
            style_frame,
            from_=0.0,
            to=1.0,
            variable=self._opacity_var,
            command=self._on_opacity_changed,
            width=100,
        )
        self._opacity_slider.pack(side="left", padx=2)

        ctk.CTkLabel(style_frame, text="Cmap:").pack(side="left", padx=(8, 2))
        self._colormap_var = tk.StringVar(value="")
        self._colormap_menu = ctk.CTkOptionMenu(
            style_frame,
            values=_COLORMAPS,
            variable=self._colormap_var,
            command=self._on_colormap_changed,
            width=90,
        )
        self._colormap_menu.pack(side="left", padx=2)

        self._refresh_tree()
        return frame

    def on_project_changed(self, project: Any) -> None:
        self.project = project
        self._refresh_tree()

    # ------------------------------------------------------------------
    # Tree population
    # ------------------------------------------------------------------

    def _refresh_tree(self) -> None:
        """Rebuild tree items from the current project layer stack."""
        if self._tree is None:
            return
        self._tree.delete(*self._tree.get_children())
        for layer in self.project.layers:
            icon = _LAYER_ICONS.get(layer.layer_type, "\u25cf")
            vis_text = "\u2713" if layer.style.visible else ""
            self._tree.insert(
                "",
                "end",
                iid=layer.id,
                text=icon,
                values=(vis_text, layer.name),
            )

    # ------------------------------------------------------------------
    # Toolbar actions
    # ------------------------------------------------------------------

    def _on_add_layer(self) -> None:
        """Placeholder: create a blank layer and add it to the project."""
        layer = Layer(name=f"Layer {len(self.project.layers) + 1}")
        self.project.add_layer(layer)
        self.event_bus.emit(EventType.LAYER_ADDED, layer_id=layer.id, name=layer.name)
        self._refresh_tree()

    def _on_remove_layer(self) -> None:
        sel = self._selected_layer_id()
        if sel is None:
            return
        self.project.remove_layer(sel)
        self.event_bus.emit(EventType.LAYER_REMOVED, layer_id=sel)
        self._refresh_tree()

    def _on_move_up(self) -> None:
        sel = self._selected_layer_id()
        if sel is None:
            return
        idx = self._layer_index(sel)
        if idx is None or idx == 0:
            return
        self.project.move_layer(sel, idx - 1)
        self.event_bus.emit(EventType.LAYER_ORDER_CHANGED, layer_id=sel, new_index=idx - 1)
        self._refresh_tree()
        self._tree.selection_set(sel)  # type: ignore[union-attr]

    def _on_move_down(self) -> None:
        sel = self._selected_layer_id()
        if sel is None:
            return
        idx = self._layer_index(sel)
        if idx is None or idx >= len(self.project.layers) - 1:
            return
        self.project.move_layer(sel, idx + 1)
        self.event_bus.emit(EventType.LAYER_ORDER_CHANGED, layer_id=sel, new_index=idx + 1)
        self._refresh_tree()
        self._tree.selection_set(sel)  # type: ignore[union-attr]

    # ------------------------------------------------------------------
    # Click handlers
    # ------------------------------------------------------------------

    def _on_click(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        """Handle single-click — toggle visibility when the 'visible' column is clicked."""
        region = self._tree.identify_region(event.x, event.y)  # type: ignore[union-attr]
        if region != "cell":
            return
        col = self._tree.identify_column(event.x)  # type: ignore[union-attr]
        # Column #1 is the "visible" column.
        if col != "#1":
            return
        row_id = self._tree.identify_row(event.y)  # type: ignore[union-attr]
        if not row_id:
            return
        self._on_visibility_toggled_by_id(row_id)

    def _on_visibility_toggled(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        """Alias kept for interface parity — delegates to click-based toggle."""
        self._on_click(event)

    def _on_visibility_toggled_by_id(self, layer_id: str) -> None:
        layer = self.project.get_layer(layer_id)
        if layer is None:
            return
        layer.style.visible = not layer.style.visible
        vis_text = "\u2713" if layer.style.visible else ""
        self._tree.item(layer_id, values=(vis_text, layer.name))  # type: ignore[union-attr]
        self.event_bus.emit(
            EventType.LAYER_VISIBILITY_CHANGED,
            layer_id=layer_id,
            visible=layer.style.visible,
        )

    def _on_double_click(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        """Open properties dialog on double-click."""
        sel = self._selected_layer_id()
        if sel is None:
            return
        layer = self.project.get_layer(sel)
        if layer is None:
            return
        from tkgis.panels.properties_dialog import LayerPropertiesDialog

        parent_window = self._widget.winfo_toplevel()  # type: ignore[union-attr]
        LayerPropertiesDialog(parent_window, layer)

    def _on_context_menu(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        """Show right-click context menu."""
        row_id = self._tree.identify_row(event.y)  # type: ignore[union-attr]
        if not row_id:
            return
        self._tree.selection_set(row_id)  # type: ignore[union-attr]
        layer = self.project.get_layer(row_id)
        if layer is None:
            return

        menu = tk.Menu(self._tree, tearoff=0)  # type: ignore[arg-type]
        menu.add_command(label="Zoom to Layer", command=lambda: self._zoom_to(row_id))
        menu.add_command(label="Rename", command=lambda: self._rename_layer(row_id))
        menu.add_separator()
        menu.add_command(label="Properties\u2026", command=lambda: self._show_properties(row_id))
        menu.add_separator()
        menu.add_command(label="Remove", command=lambda: self._remove_by_id(row_id))
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _on_selection_changed(self, _event: tk.Event) -> None:  # type: ignore[type-arg]
        """Update quick-style controls to reflect the selected layer."""
        sel = self._selected_layer_id()
        if sel is None:
            return
        layer = self.project.get_layer(sel)
        if layer is None:
            return
        if self._opacity_var is not None:
            self._opacity_var.set(layer.style.opacity)
        if self._colormap_var is not None:
            self._colormap_var.set(layer.style.colormap or "")
        self.event_bus.emit(EventType.LAYER_SELECTED, layer_id=sel)

    # ------------------------------------------------------------------
    # Quick style callbacks
    # ------------------------------------------------------------------

    def _on_opacity_changed(self, value: float | str) -> None:
        sel = self._selected_layer_id()
        if sel is None:
            return
        layer = self.project.get_layer(sel)
        if layer is None:
            return
        layer.style.opacity = float(value)
        self.event_bus.emit(EventType.LAYER_STYLE_CHANGED, layer_id=sel)

    def _on_colormap_changed(self, value: str) -> None:
        sel = self._selected_layer_id()
        if sel is None:
            return
        layer = self.project.get_layer(sel)
        if layer is None:
            return
        layer.style.colormap = value if value else None
        self.event_bus.emit(EventType.LAYER_STYLE_CHANGED, layer_id=sel)

    # ------------------------------------------------------------------
    # Context-menu helpers
    # ------------------------------------------------------------------

    def _zoom_to(self, layer_id: str) -> None:
        layer = self.project.get_layer(layer_id)
        if layer and layer.bounds:
            self.event_bus.emit(EventType.VIEW_CHANGED, bounds=layer.bounds)

    def _rename_layer(self, layer_id: str) -> None:
        layer = self.project.get_layer(layer_id)
        if layer is None:
            return
        dialog = ctk.CTkInputDialog(text="New layer name:", title="Rename Layer")
        new_name = dialog.get_input()
        if new_name:
            layer.name = new_name
            self._refresh_tree()
            self.event_bus.emit(EventType.PROJECT_MODIFIED)

    def _show_properties(self, layer_id: str) -> None:
        layer = self.project.get_layer(layer_id)
        if layer is None:
            return
        from tkgis.panels.properties_dialog import LayerPropertiesDialog

        parent_window = self._widget.winfo_toplevel()  # type: ignore[union-attr]
        LayerPropertiesDialog(parent_window, layer)

    def _remove_by_id(self, layer_id: str) -> None:
        self.project.remove_layer(layer_id)
        self.event_bus.emit(EventType.LAYER_REMOVED, layer_id=layer_id)
        self._refresh_tree()

    # ------------------------------------------------------------------
    # External event handler
    # ------------------------------------------------------------------

    def _on_external_change(self, **_kwargs: Any) -> None:
        self._refresh_tree()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _selected_layer_id(self) -> str | None:
        if self._tree is None:
            return None
        selection = self._tree.selection()
        if not selection:
            return None
        return str(selection[0])

    def _layer_index(self, layer_id: str) -> int | None:
        for i, lyr in enumerate(self.project.layers):
            if lyr.id == layer_id:
                return i
        return None

    def toggle_visibility(self, layer_id: str) -> None:
        """Programmatic visibility toggle (useful for tests)."""
        self._on_visibility_toggled_by_id(layer_id)
