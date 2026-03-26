"""Top-level window for the visual workflow builder."""
from __future__ import annotations

import logging
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Any

import customtkinter as ctk

from tkgis.models.events import EventBus
from tkgis.workflow.canvas import WorkflowCanvas, create_graph, _HAS_GRDL_RT
from tkgis.workflow.dnd import PaletteToCanvasDnD
from tkgis.workflow.history import WorkflowHistory
from tkgis.workflow.inspector import NodeInspectorPanel
from tkgis.workflow.palette import NodePalettePanel

logger = logging.getLogger(__name__)

if _HAS_GRDL_RT:
    from grdl_rt.execution.graph import WorkflowGraph
    from grdl_rt.execution.workflow import WorkflowDefinition


class WorkflowBuilderWindow(ctk.CTkToplevel):
    """Three-pane workflow builder: Palette | Canvas | Inspector.

    Provides menu bar, toolbar, undo/redo, save/load, validation,
    and execution through the ProcessingExecutor.
    """

    def __init__(
        self,
        parent: Any,
        event_bus: EventBus | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(parent, **kwargs)

        self.title("Workflow Builder")
        self.geometry("1200x700")
        self.minsize(800, 500)

        self._event_bus = event_bus or EventBus()
        self._history = WorkflowHistory()
        self._file_path: Path | None = None

        # Create the graph backend
        self._graph = create_graph()

        # ------------------------------------------------------------------
        # Menu bar
        # ------------------------------------------------------------------
        self._menu_bar = tk.Menu(self)
        self.configure(menu=self._menu_bar)  # type: ignore[arg-type]

        file_menu = tk.Menu(self._menu_bar, tearoff=0)
        file_menu.add_command(label="New", command=self.new_workflow, accelerator="Ctrl+N")
        file_menu.add_command(label="Open...", command=self.open_workflow, accelerator="Ctrl+O")
        file_menu.add_separator()
        file_menu.add_command(label="Save", command=self.save_workflow, accelerator="Ctrl+S")
        file_menu.add_command(label="Save As...", command=lambda: self.save_workflow(save_as=True))
        file_menu.add_separator()
        file_menu.add_command(label="Close", command=self.destroy)
        self._menu_bar.add_cascade(label="File", menu=file_menu)

        edit_menu = tk.Menu(self._menu_bar, tearoff=0)
        edit_menu.add_command(label="Undo", command=self._undo, accelerator="Ctrl+Z")
        edit_menu.add_command(label="Redo", command=self._redo, accelerator="Ctrl+Y")
        edit_menu.add_separator()
        edit_menu.add_command(label="Delete Node", command=self._delete_selected)
        self._menu_bar.add_cascade(label="Edit", menu=edit_menu)

        run_menu = tk.Menu(self._menu_bar, tearoff=0)
        run_menu.add_command(label="Validate", command=self.validate_workflow, accelerator="F5")
        run_menu.add_command(label="Execute", command=self.execute_workflow, accelerator="F6")
        self._menu_bar.add_cascade(label="Run", menu=run_menu)

        # ------------------------------------------------------------------
        # Toolbar
        # ------------------------------------------------------------------
        toolbar = ctk.CTkFrame(self, height=36, fg_color="#181825")
        toolbar.pack(fill="x", side="top")

        btn_cfg: dict[str, Any] = {"height": 28, "width": 80, "font": ctk.CTkFont(size=11)}

        ctk.CTkButton(toolbar, text="New", command=self.new_workflow, **btn_cfg).pack(side="left", padx=2, pady=4)
        ctk.CTkButton(toolbar, text="Open", command=self.open_workflow, **btn_cfg).pack(side="left", padx=2, pady=4)
        ctk.CTkButton(toolbar, text="Save", command=self.save_workflow, **btn_cfg).pack(side="left", padx=2, pady=4)

        sep = ctk.CTkFrame(toolbar, width=2, height=20, fg_color="#45475a")
        sep.pack(side="left", padx=6, pady=8)

        ctk.CTkButton(toolbar, text="Validate", command=self.validate_workflow, **btn_cfg).pack(side="left", padx=2, pady=4)
        ctk.CTkButton(toolbar, text="Run", command=self.execute_workflow, fg_color="#a6e3a1", text_color="#1e1e2e", hover_color="#94e2d5", **btn_cfg).pack(side="left", padx=2, pady=4)

        sep2 = ctk.CTkFrame(toolbar, width=2, height=20, fg_color="#45475a")
        sep2.pack(side="left", padx=6, pady=8)

        ctk.CTkButton(toolbar, text="Auto Layout", command=self._auto_layout, **btn_cfg).pack(side="left", padx=2, pady=4)

        # Zoom controls
        ctk.CTkButton(toolbar, text="Zoom +", command=self._zoom_in, width=60, height=28).pack(side="right", padx=2, pady=4)
        ctk.CTkButton(toolbar, text="Zoom -", command=self._zoom_out, width=60, height=28).pack(side="right", padx=2, pady=4)

        # ------------------------------------------------------------------
        # Three-pane layout
        # ------------------------------------------------------------------
        pane_container = ctk.CTkFrame(self)
        pane_container.pack(fill="both", expand=True)

        # Left: Palette
        self._palette = NodePalettePanel()
        palette_widget = self._palette.create_widget(pane_container)
        palette_widget.pack(side="left", fill="y", padx=(0, 2))

        # Center: Canvas
        canvas_frame = ctk.CTkFrame(pane_container)
        canvas_frame.pack(side="left", fill="both", expand=True)

        self._canvas = WorkflowCanvas(
            canvas_frame,
            graph=self._graph,
            event_bus=self._event_bus,
            width=800,
            height=600,
        )
        self._canvas.pack(fill="both", expand=True)

        # Right: Inspector
        self._inspector = NodeInspectorPanel()
        inspector_widget = self._inspector.create_widget(pane_container)
        inspector_widget.pack(side="right", fill="y", padx=(2, 0))
        self._inspector.set_graph(self._graph)

        # ------------------------------------------------------------------
        # Wire up interactions
        # ------------------------------------------------------------------
        self._dnd = PaletteToCanvasDnD(self._palette, self._canvas)

        self._canvas.on_node_select(self._on_node_selected)
        self._canvas.on_node_double_click(self._on_node_double_clicked)

        self._inspector.on_param_changed(self._on_param_changed)

        # Keyboard shortcuts
        self.bind("<Control-n>", lambda e: self.new_workflow())
        self.bind("<Control-o>", lambda e: self.open_workflow())
        self.bind("<Control-s>", lambda e: self.save_workflow())
        self.bind("<Control-z>", lambda e: self._undo())
        self.bind("<Control-y>", lambda e: self._redo())
        self.bind("<Delete>", lambda e: self._delete_selected())
        self.bind("<F5>", lambda e: self.validate_workflow())
        self.bind("<F6>", lambda e: self.execute_workflow())

        # Status bar
        self._status_var = ctk.StringVar(value="Ready")
        status_bar = ctk.CTkLabel(
            self,
            textvariable=self._status_var,
            height=24,
            font=ctk.CTkFont(size=10),
            text_color="#9399b2",
            anchor="w",
        )
        status_bar.pack(fill="x", side="bottom", padx=6)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def new_workflow(self) -> None:
        """Create a new empty workflow."""
        self._push_history()
        self._graph = create_graph()
        self._canvas.graph = self._graph
        self._inspector.set_graph(self._graph)
        self._inspector.set_node(None)
        self._file_path = None
        self.title("Workflow Builder - Untitled")
        self._status_var.set("New workflow created")

    def open_workflow(self) -> None:
        """Load a workflow YAML file."""
        path = filedialog.askopenfilename(
            title="Open Workflow",
            filetypes=[("YAML files", "*.yaml *.yml"), ("All files", "*.*")],
            parent=self,
        )
        if not path:
            return

        try:
            from tkgis.processing.workflow_io import load_workflow

            steps = load_workflow(path)

            self._push_history()
            self._graph = create_graph()

            # Add nodes from loaded steps
            prev_id: str | None = None
            for i, step in enumerate(steps):
                step_id = self._graph.add_node(
                    step["processor_name"],
                    params=step.get("params", {}),
                    position=(100 + i * 240, 200),
                    input_type=step.get("input_type"),
                    output_type=step.get("output_type"),
                )
                if prev_id is not None:
                    try:
                        self._graph.connect(prev_id, step_id)
                    except (KeyError, ValueError):
                        pass
                prev_id = step_id

            self._canvas.graph = self._graph
            self._inspector.set_graph(self._graph)
            self._canvas.auto_layout()
            self._file_path = Path(path)
            self.title(f"Workflow Builder - {self._file_path.name}")
            self._status_var.set(f"Opened: {path}")

        except Exception as exc:
            logger.exception("Failed to open workflow")
            messagebox.showerror("Open Error", str(exc), parent=self)

    def save_workflow(self, path: Path | str | None = None, *, save_as: bool = False) -> None:
        """Save the workflow to YAML.

        If *save_as* is True or no path is set, prompts for a file location.
        """
        if path is None and (save_as or self._file_path is None):
            path = filedialog.asksaveasfilename(
                title="Save Workflow",
                defaultextension=".yaml",
                filetypes=[("YAML files", "*.yaml *.yml"), ("All files", "*.*")],
                parent=self,
            )
            if not path:
                return

        if path is not None:
            self._file_path = Path(path)

        if self._file_path is None:
            return

        try:
            # Convert graph to step list for workflow_io
            steps = []
            for node in self._graph.get_nodes():
                steps.append({
                    "processor_name": node.processor_name,
                    "params": node.params,
                })

            from tkgis.processing.workflow_io import save_workflow

            save_workflow(steps, self._file_path)
            self.title(f"Workflow Builder - {self._file_path.name}")
            self._status_var.set(f"Saved: {self._file_path}")

        except Exception as exc:
            logger.exception("Failed to save workflow")
            messagebox.showerror("Save Error", str(exc), parent=self)

    def validate_workflow(self) -> list[str]:
        """Validate the workflow and highlight errors on the canvas.

        Returns the list of error messages.
        """
        errors = self._graph.validate()
        self._canvas.show_validation_errors(errors)

        if errors:
            self._status_var.set(f"Validation: {len(errors)} error(s)")
            messagebox.showwarning(
                "Validation Errors",
                "\n".join(errors),
                parent=self,
            )
        else:
            self._status_var.set("Validation: OK")

        return errors

    def execute_workflow(self) -> None:
        """Execute the workflow via ProcessingExecutor."""
        errors = self._graph.validate()
        if errors:
            messagebox.showwarning(
                "Cannot Execute",
                "Fix validation errors first:\n" + "\n".join(errors),
                parent=self,
            )
            return

        try:
            from tkgis.processing.executor import ProcessingExecutor

            executor = ProcessingExecutor(self._event_bus)

            # Build a WorkflowDefinition if using grdl-runtime
            if _HAS_GRDL_RT and hasattr(self._graph, "to_workflow_definition"):
                wd = self._graph.to_workflow_definition()
                executor.execute(wd, None, output_name="Workflow Output")
                self._status_var.set("Workflow execution started...")
            else:
                self._status_var.set("Execution requires grdl-runtime")
                messagebox.showinfo(
                    "Execute",
                    "Workflow execution requires grdl-runtime to be installed.",
                    parent=self,
                )
        except Exception as exc:
            logger.exception("Failed to execute workflow")
            messagebox.showerror("Execution Error", str(exc), parent=self)

    def auto_layout(self) -> None:
        """Apply automatic topological layout."""
        self._auto_layout()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _push_history(self) -> None:
        """Snapshot the current graph state for undo."""
        snapshot = self._snapshot_graph()
        self._history.push(snapshot)

    def _snapshot_graph(self) -> dict:
        """Serialize the graph to a dict for history."""
        nodes = []
        for n in self._graph.get_nodes():
            nodes.append({
                "step_id": n.step_id,
                "processor_name": n.processor_name,
                "params": dict(n.params),
                "position": n.position,
                "input_type": n.input_type,
                "output_type": n.output_type,
                "depends_on": list(n.depends_on),
            })
        edges = []
        for e in self._graph.get_edges():
            edges.append({
                "source_id": e.source_id,
                "target_id": e.target_id,
            })
        return {"nodes": nodes, "edges": edges}

    def _restore_snapshot(self, snapshot: dict) -> None:
        """Rebuild the graph from a history snapshot."""
        self._graph = create_graph()

        for nd in snapshot.get("nodes", []):
            self._graph.add_node(
                nd["processor_name"],
                params=nd.get("params", {}),
                position=nd.get("position"),
                input_type=nd.get("input_type"),
                output_type=nd.get("output_type"),
            )

        for ed in snapshot.get("edges", []):
            try:
                self._graph.connect(ed["source_id"], ed["target_id"])
            except (KeyError, ValueError):
                pass

        self._canvas.graph = self._graph
        self._inspector.set_graph(self._graph)
        self._inspector.set_node(None)

    def _undo(self) -> None:
        """Undo the last action."""
        state = self._history.undo()
        if state is not None:
            self._restore_snapshot(state)
            self._status_var.set("Undo")

    def _redo(self) -> None:
        """Redo the last undone action."""
        state = self._history.redo()
        if state is not None:
            self._restore_snapshot(state)
            self._status_var.set("Redo")

    def _delete_selected(self) -> None:
        """Delete the currently selected node."""
        self._push_history()
        self._canvas.remove_selected_node()
        self._inspector.set_node(None)

    def _auto_layout(self) -> None:
        """Auto-layout the graph nodes."""
        self._push_history()
        self._canvas.auto_layout()
        self._status_var.set("Auto layout applied")

    def _zoom_in(self) -> None:
        self._canvas.scale("all", 0, 0, 1.1, 1.1)

    def _zoom_out(self) -> None:
        self._canvas.scale("all", 0, 0, 0.9, 0.9)

    def _on_node_selected(self, step_id: str) -> None:
        """Handle node selection on the canvas."""
        self._inspector.set_node(step_id)

    def _on_node_double_clicked(self, step_id: str) -> None:
        """Handle node double-click — focus the inspector."""
        self._inspector.set_node(step_id)

    def _on_param_changed(self, step_id: str, name: str, value: Any) -> None:
        """Handle parameter change from the inspector."""
        self._canvas.refresh()
