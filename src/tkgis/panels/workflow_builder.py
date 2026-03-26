"""Workflow builder panel — assemble and run processing chains."""
from __future__ import annotations

import logging
import tkinter as tk
from pathlib import Path
from tkinter import filedialog
from typing import Any

import customtkinter as ctk

from tkgis.models.events import EventBus, EventType
from tkgis.panels.base import BasePanel
from tkgis.processing.executor import ProcessingExecutor
from tkgis.processing.workflow_io import (
    load_workflow as io_load_workflow,
    save_workflow as io_save_workflow,
)

try:
    import grdl_rt
except ImportError:  # pragma: no cover
    grdl_rt = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


class WorkflowBuilderPanel(BasePanel):
    """Visual workflow builder with step list, parameter editors, and
    run/preview/save/load controls.
    """

    name = "workflow_builder"
    title = "Workflow"
    dock_position = "right"
    default_visible = False

    def __init__(
        self,
        event_bus: EventBus | None = None,
        executor: ProcessingExecutor | None = None,
    ) -> None:
        super().__init__()
        self._event_bus = event_bus
        self._executor = executor
        self._steps: list[dict[str, Any]] = []
        self._step_listbox: tk.Listbox | None = None
        self._param_frame: ctk.CTkFrame | None = None
        self._param_widgets: dict[str, tk.Variable] = {}

    # ------------------------------------------------------------------
    # BasePanel interface
    # ------------------------------------------------------------------

    def create_widget(self, parent: Any) -> ctk.CTkFrame:
        """Build and return the panel's root frame."""
        frame = ctk.CTkFrame(parent)
        self._widget = frame

        # --- Step list ---
        list_label = ctk.CTkLabel(frame, text="Steps", anchor="w")
        list_label.pack(fill="x", padx=6, pady=(4, 0))

        list_frame = ctk.CTkFrame(frame)
        list_frame.pack(fill="both", expand=True, padx=4, pady=2)

        self._step_listbox = tk.Listbox(list_frame, selectmode="single", height=8)
        self._step_listbox.pack(side="left", fill="both", expand=True)
        self._step_listbox.bind("<<ListboxSelect>>", self._on_step_selected)

        scrollbar = ctk.CTkScrollbar(list_frame, command=self._step_listbox.yview)
        self._step_listbox.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

        # --- Step manipulation buttons ---
        btn_frame = ctk.CTkFrame(frame)
        btn_frame.pack(fill="x", padx=4, pady=2)

        ctk.CTkButton(btn_frame, text="\u25b2", width=30, command=self._move_step_up).pack(
            side="left", padx=1
        )
        ctk.CTkButton(btn_frame, text="\u25bc", width=30, command=self._move_step_down).pack(
            side="left", padx=1
        )
        ctk.CTkButton(btn_frame, text="Add", width=50, command=self._add_step).pack(
            side="left", padx=1
        )
        ctk.CTkButton(btn_frame, text="Remove", width=60, command=self._remove_step).pack(
            side="left", padx=1
        )

        # --- Parameter editor ---
        param_label = ctk.CTkLabel(frame, text="Parameters", anchor="w")
        param_label.pack(fill="x", padx=6, pady=(6, 0))

        self._param_frame = ctk.CTkFrame(frame)
        self._param_frame.pack(fill="both", expand=True, padx=4, pady=2)

        # --- Action buttons ---
        action_frame = ctk.CTkFrame(frame)
        action_frame.pack(fill="x", padx=4, pady=(4, 4))

        ctk.CTkButton(action_frame, text="Run", width=60, command=self._run_workflow).pack(
            side="left", padx=2
        )
        ctk.CTkButton(
            action_frame, text="Preview", width=70, command=self._preview_workflow
        ).pack(side="left", padx=2)
        ctk.CTkButton(action_frame, text="Save", width=60, command=self._save_workflow).pack(
            side="left", padx=2
        )
        ctk.CTkButton(action_frame, text="Load", width=60, command=self._load_workflow).pack(
            side="left", padx=2
        )

        return frame

    # ------------------------------------------------------------------
    # Step list management
    # ------------------------------------------------------------------

    @property
    def steps(self) -> list[dict[str, Any]]:
        """Return current workflow steps (read-only copy)."""
        return list(self._steps)

    def add_step(self, processor_name: str, params: dict[str, Any] | None = None) -> None:
        """Programmatically add a processing step."""
        step: dict[str, Any] = {
            "processor_name": processor_name,
            "params": params or {},
        }
        self._steps.append(step)
        self._refresh_listbox()

    def _refresh_listbox(self) -> None:
        if self._step_listbox is None:
            return
        self._step_listbox.delete(0, "end")
        for i, s in enumerate(self._steps):
            self._step_listbox.insert("end", f"{i + 1}. {s['processor_name']}")

    def _selected_index(self) -> int | None:
        if self._step_listbox is None:
            return None
        sel = self._step_listbox.curselection()
        return sel[0] if sel else None

    def _move_step_up(self) -> None:
        idx = self._selected_index()
        if idx is None or idx == 0:
            return
        self._steps[idx - 1], self._steps[idx] = self._steps[idx], self._steps[idx - 1]
        self._refresh_listbox()
        self._step_listbox.selection_set(idx - 1)  # type: ignore[union-attr]

    def _move_step_down(self) -> None:
        idx = self._selected_index()
        if idx is None or idx >= len(self._steps) - 1:
            return
        self._steps[idx], self._steps[idx + 1] = self._steps[idx + 1], self._steps[idx]
        self._refresh_listbox()
        self._step_listbox.selection_set(idx + 1)  # type: ignore[union-attr]

    def _add_step(self) -> None:
        """Open a simple dialog to add a step by processor name."""
        dialog = ctk.CTkInputDialog(
            text="Processor name:", title="Add Processing Step"
        )
        name = dialog.get_input()
        if name:
            self.add_step(name.strip())

    def _remove_step(self) -> None:
        idx = self._selected_index()
        if idx is not None:
            self._steps.pop(idx)
            self._refresh_listbox()
            self._clear_param_editor()

    # ------------------------------------------------------------------
    # Parameter editor
    # ------------------------------------------------------------------

    def _on_step_selected(self, _event: Any = None) -> None:
        idx = self._selected_index()
        if idx is not None and idx < len(self._steps):
            self._build_param_editor(self._steps[idx])

    def _clear_param_editor(self) -> None:
        if self._param_frame is None:
            return
        for child in self._param_frame.winfo_children():
            child.destroy()
        self._param_widgets.clear()

    def _build_param_editor(self, step: dict[str, Any]) -> None:
        """Auto-generate parameter entries from the step's param dict."""
        self._clear_param_editor()
        if self._param_frame is None:
            return

        params = step.get("params", {})

        # If we have a param_schema from the catalog, use it to build editors.
        # Otherwise fall back to showing existing params as string entries.
        schema = self._get_param_schema(step["processor_name"])

        if schema:
            for pname, pspec in schema.items():
                self._add_param_row(pname, pspec, params.get(pname))
        else:
            for pname, pval in params.items():
                self._add_param_row(pname, {"type": "string"}, pval)

        # "No parameters" placeholder
        if not schema and not params:
            ctk.CTkLabel(self._param_frame, text="(no parameters)").pack(
                padx=4, pady=4
            )

    def _add_param_row(
        self, name: str, spec: dict[str, Any], current_value: Any
    ) -> None:
        """Add one parameter row to the editor."""
        if self._param_frame is None:
            return

        row = ctk.CTkFrame(self._param_frame)
        row.pack(fill="x", padx=2, pady=1)

        ctk.CTkLabel(row, text=name, width=100, anchor="w").pack(side="left", padx=2)

        var = tk.StringVar(value=str(current_value) if current_value is not None else "")
        entry = ctk.CTkEntry(row, textvariable=var)
        entry.pack(side="left", fill="x", expand=True, padx=2)

        self._param_widgets[name] = var

    def _get_param_schema(self, processor_name: str) -> dict[str, Any] | None:
        """Look up parameter schema from the grdl-runtime catalog."""
        if grdl_rt is None:
            return None
        try:
            catalog = grdl_rt.discover_processors()
            artifact = catalog.get(processor_name)
            if artifact and hasattr(artifact, "param_schema"):
                return artifact.param_schema
        except Exception:
            logger.debug("Could not retrieve param schema for %s", processor_name)
        return None

    def _collect_params(self) -> dict[str, Any]:
        """Collect current values from the parameter editor widgets."""
        result: dict[str, Any] = {}
        for name, var in self._param_widgets.items():
            val = var.get()
            # Attempt numeric coercion
            try:
                val = int(val)
            except ValueError:
                try:
                    val = float(val)
                except ValueError:
                    pass
            result[name] = val
        return result

    def _apply_params_to_selected(self) -> None:
        """Write edited params back to the selected step."""
        idx = self._selected_index()
        if idx is not None and idx < len(self._steps):
            self._steps[idx]["params"] = self._collect_params()

    # ------------------------------------------------------------------
    # Workflow actions
    # ------------------------------------------------------------------

    def _build_workflow(self) -> Any:
        """Build a grdl_rt.Workflow from the current steps."""
        self._apply_params_to_selected()

        if grdl_rt is None:
            logger.error("grdl-runtime not available — cannot build workflow.")
            return None

        wf = grdl_rt.Workflow(name="tkgis-workflow")
        for step in self._steps:
            wf = wf.step(step["processor_name"], **(step.get("params") or {}))
        return wf

    def _run_workflow(self) -> None:
        """Execute the assembled workflow."""
        wf = self._build_workflow()
        if wf is None:
            return
        if self._executor is not None:
            self._executor.execute(wf, input_layer=None, output_name="Processed")
        else:
            logger.warning("No executor configured — cannot run workflow.")

    def _preview_workflow(self) -> None:
        """Execute a preview on the visible extent."""
        wf = self._build_workflow()
        if wf is None:
            return
        if self._executor is not None:
            self._executor.execute_preview(wf, input_layer=None, visible_extent=None)
        else:
            logger.warning("No executor configured — cannot preview workflow.")

    def _save_workflow(self) -> None:
        """Save the current workflow to a YAML file."""
        self._apply_params_to_selected()
        path = filedialog.asksaveasfilename(
            defaultextension=".yaml",
            filetypes=[("YAML files", "*.yaml *.yml"), ("All files", "*.*")],
            title="Save Workflow",
        )
        if path:
            io_save_workflow(self._steps, path)

    def _load_workflow(self) -> None:
        """Load a workflow from a YAML file."""
        path = filedialog.askopenfilename(
            filetypes=[("YAML files", "*.yaml *.yml"), ("All files", "*.*")],
            title="Load Workflow",
        )
        if path:
            self._steps = io_load_workflow(path)
            self._refresh_listbox()
            self._clear_param_editor()
