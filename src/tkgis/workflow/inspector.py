"""Node property inspector panel for the workflow builder."""
from __future__ import annotations

import logging
from typing import Any, Callable

import customtkinter as ctk

from tkgis.panels.base import BasePanel

logger = logging.getLogger(__name__)


class NodeInspectorPanel(BasePanel):
    """Right-side panel showing editable parameters for a selected node.

    Auto-generates parameter editors based on param_specs from the
    processor metadata:
    - Range with min/max -> CTkSlider
    - Options list -> CTkComboBox
    - Boolean -> CTkSwitch
    - Everything else -> CTkEntry
    """

    name = "node_inspector"
    title = "Node Properties"
    dock_position = "right"
    default_visible = False

    def __init__(self) -> None:
        super().__init__()
        self._current_step_id: str | None = None
        self._graph: Any = None
        self._param_frame: ctk.CTkScrollableFrame | None = None
        self._header_label: ctk.CTkLabel | None = None
        self._type_label: ctk.CTkLabel | None = None
        self._param_widgets: dict[str, Any] = {}
        self._on_param_changed_callback: Callable[[str, str, Any], None] | None = None

    def create_widget(self, parent: Any) -> ctk.CTkFrame:
        """Build and return the inspector widget."""
        frame = ctk.CTkFrame(parent, width=260)
        self._widget = frame

        # Header
        self._header_label = ctk.CTkLabel(
            frame,
            text="No node selected",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w",
        )
        self._header_label.pack(fill="x", padx=10, pady=(10, 2))

        self._type_label = ctk.CTkLabel(
            frame,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="#9399b2",
            anchor="w",
        )
        self._type_label.pack(fill="x", padx=10, pady=(0, 6))

        separator = ctk.CTkFrame(frame, height=1, fg_color="#45475a")
        separator.pack(fill="x", padx=10, pady=2)

        # Scrollable parameter area
        self._param_frame = ctk.CTkScrollableFrame(frame)
        self._param_frame.pack(fill="both", expand=True, padx=6, pady=6)

        return frame

    def set_graph(self, graph: Any) -> None:
        """Set the backing graph for reading node data."""
        self._graph = graph

    def set_node(self, step_id: str | None) -> None:
        """Load the parameters for *step_id* into the inspector."""
        self._current_step_id = step_id

        if step_id is None or self._graph is None:
            self._clear()
            return

        node = self._graph.get_node(step_id)
        if node is None:
            self._clear()
            return

        # Update header
        if self._header_label:
            self._header_label.configure(text=node.display_name)
        if self._type_label:
            in_t = node.input_type or "any"
            out_t = node.output_type or "any"
            self._type_label.configure(text=f"{in_t} -> {out_t}")

        # Build parameter editors
        self._build_param_editors(node.param_specs, node.params)

    def on_param_changed(
        self, callback: Callable[[str, str, Any], None]
    ) -> None:
        """Register a callback: ``callback(step_id, param_name, value)``."""
        self._on_param_changed_callback = callback

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _clear(self) -> None:
        """Clear the inspector display."""
        if self._header_label:
            self._header_label.configure(text="No node selected")
        if self._type_label:
            self._type_label.configure(text="")
        if self._param_frame:
            for child in self._param_frame.winfo_children():
                child.destroy()
        self._param_widgets.clear()

    def _build_param_editors(
        self, specs: dict[str, dict], values: dict[str, Any]
    ) -> None:
        """Generate UI controls for each parameter."""
        if self._param_frame is None:
            return

        # Clear existing editors
        for child in self._param_frame.winfo_children():
            child.destroy()
        self._param_widgets.clear()

        if not specs and not values:
            # Show the raw values as simple entries if no specs
            for name, val in values.items():
                self._add_entry_editor(name, val)
            return

        # Use specs to determine widget type
        all_params = set(specs.keys()) | set(values.keys())
        for name in sorted(all_params):
            spec = specs.get(name, {})
            current_value = values.get(name, spec.get("default"))
            self._add_editor_for_spec(name, spec, current_value)

    def _add_editor_for_spec(
        self, name: str, spec: dict, value: Any
    ) -> None:
        """Add the appropriate editor widget based on the param spec."""
        param_type = spec.get("type", "string")
        options = spec.get("enum") or spec.get("options")
        minimum = spec.get("minimum") or spec.get("min")
        maximum = spec.get("maximum") or spec.get("max")

        if param_type == "boolean" or isinstance(value, bool):
            self._add_switch_editor(name, bool(value) if value else False)
        elif options:
            self._add_combobox_editor(name, options, value)
        elif minimum is not None and maximum is not None:
            self._add_slider_editor(name, float(minimum), float(maximum), value)
        else:
            self._add_entry_editor(name, value)

    def _add_label(self, name: str) -> None:
        """Add a parameter label."""
        label = ctk.CTkLabel(
            self._param_frame,
            text=name.replace("_", " ").title(),
            font=ctk.CTkFont(size=11),
            anchor="w",
        )
        label.pack(fill="x", padx=4, pady=(8, 2))

    def _add_entry_editor(self, name: str, value: Any) -> None:
        """Add a text entry editor."""
        self._add_label(name)
        var = ctk.StringVar(value=str(value) if value is not None else "")
        entry = ctk.CTkEntry(self._param_frame, textvariable=var, height=28)
        entry.pack(fill="x", padx=4, pady=(0, 2))
        var.trace_add(
            "write",
            lambda *_, n=name, v=var: self._fire_param_changed(n, v.get()),
        )
        self._param_widgets[name] = entry

    def _add_slider_editor(
        self, name: str, minimum: float, maximum: float, value: Any
    ) -> None:
        """Add a slider editor for numeric range parameters."""
        self._add_label(name)

        current = float(value) if value is not None else minimum
        current = max(minimum, min(maximum, current))

        value_label = ctk.CTkLabel(
            self._param_frame,
            text=f"{current:.2f}",
            font=ctk.CTkFont(size=10),
            text_color="#9399b2",
        )
        value_label.pack(anchor="e", padx=4)

        def on_slide(val: float) -> None:
            value_label.configure(text=f"{val:.2f}")
            self._fire_param_changed(name, val)

        slider = ctk.CTkSlider(
            self._param_frame,
            from_=minimum,
            to=maximum,
            number_of_steps=max(1, int((maximum - minimum) * 10)),
            command=on_slide,
        )
        slider.set(current)
        slider.pack(fill="x", padx=4, pady=(0, 2))
        self._param_widgets[name] = slider

    def _add_combobox_editor(
        self, name: str, options: list, value: Any
    ) -> None:
        """Add a dropdown combobox editor."""
        self._add_label(name)
        str_options = [str(o) for o in options]
        combo = ctk.CTkComboBox(
            self._param_frame,
            values=str_options,
            command=lambda val, n=name: self._fire_param_changed(n, val),
            height=28,
        )
        if value is not None and str(value) in str_options:
            combo.set(str(value))
        elif str_options:
            combo.set(str_options[0])
        combo.pack(fill="x", padx=4, pady=(0, 2))
        self._param_widgets[name] = combo

    def _add_switch_editor(self, name: str, value: bool) -> None:
        """Add a toggle switch editor."""
        self._add_label(name)
        var = ctk.BooleanVar(value=value)
        switch = ctk.CTkSwitch(
            self._param_frame,
            text="",
            variable=var,
            command=lambda n=name, v=var: self._fire_param_changed(n, v.get()),
        )
        switch.pack(anchor="w", padx=4, pady=(0, 2))
        self._param_widgets[name] = switch

    def _fire_param_changed(self, name: str, value: Any) -> None:
        """Notify the graph and external callback of a parameter change."""
        if self._current_step_id is None or self._graph is None:
            return
        try:
            self._graph.update_node_params(self._current_step_id, {name: value})
        except KeyError:
            pass

        if self._on_param_changed_callback:
            self._on_param_changed_callback(self._current_step_id, name, value)
