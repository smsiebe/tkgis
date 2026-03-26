"""ProcessingExecutor — run grdl-runtime workflows in background threads."""
from __future__ import annotations

import logging
import threading
from typing import Any

from tkgis.models.events import EventBus, EventType

try:
    import grdl_rt
except ImportError:  # pragma: no cover
    grdl_rt = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


class ProcessingExecutor:
    """Execute grdl-runtime workflows off the GUI thread.

    Progress is reported through the *EventBus* via
    :pyattr:`EventType.PROGRESS_UPDATED` events.
    """

    def __init__(self, event_bus: EventBus) -> None:
        self._event_bus = event_bus
        self._thread: threading.Thread | None = None
        self._cancel_event = threading.Event()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def is_running(self) -> bool:
        """Return *True* if a workflow is currently executing."""
        return self._thread is not None and self._thread.is_alive()

    def execute(
        self,
        workflow: Any,
        input_layer: Any,
        output_name: str = "Processed",
    ) -> None:
        """Run *workflow* against *input_layer* in a background thread.

        Parameters
        ----------
        workflow:
            A ``grdl_rt.Workflow`` builder instance **or** a
            ``grdl_rt.WorkflowDefinition``.
        input_layer:
            The source :class:`~tkgis.models.layers.Layer` to process.
        output_name:
            Human-readable name for the resulting layer.
        """
        if self.is_running:
            logger.warning("A workflow is already running — ignoring request.")
            return

        self._cancel_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            args=(workflow, input_layer, output_name),
            daemon=True,
            name="tkgis-processing",
        )
        self._thread.start()

    def cancel(self) -> None:
        """Request cancellation of the running workflow."""
        self._cancel_event.set()
        logger.info("Processing cancellation requested.")

    def execute_preview(
        self,
        workflow: Any,
        input_layer: Any,
        visible_extent: Any,
    ) -> None:
        """Quick preview limited to *visible_extent*.

        Runs the workflow on a small chip covering the current map view so
        the user gets fast visual feedback before committing to a full run.
        """
        if self.is_running:
            logger.warning("A workflow is already running — ignoring preview request.")
            return

        self._cancel_event.clear()
        self._thread = threading.Thread(
            target=self._run_preview,
            args=(workflow, input_layer, visible_extent),
            daemon=True,
            name="tkgis-preview",
        )
        self._thread.start()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _emit_progress(self, percent: float, message: str = "") -> None:
        self._event_bus.emit(
            EventType.PROGRESS_UPDATED,
            percent=percent,
            message=message,
        )

    def _run(self, workflow: Any, input_layer: Any, output_name: str) -> None:
        """Background execution target."""
        if grdl_rt is None:
            logger.error("grdl-runtime is not installed — cannot execute workflow.")
            self._emit_progress(0.0, "Error: grdl-runtime not available")
            return

        try:
            self._emit_progress(0.0, f"Starting: {output_name}")

            # Build a Workflow if we received a WorkflowDefinition
            wf = workflow
            if isinstance(workflow, grdl_rt.WorkflowDefinition):
                wf = grdl_rt.Workflow(name=workflow.name)
                for level in workflow.topological_sort():
                    for step_id in level:
                        step_def = workflow.get_step(step_id)
                        wf = wf.step(step_def.processor_name, **(step_def.params or {}))

            # Attach source from input layer
            source_path = getattr(input_layer, "source_path", None)
            if source_path:
                wf = wf.source(source_path)

            self._emit_progress(10.0, "Executing workflow…")

            if self._cancel_event.is_set():
                self._emit_progress(0.0, "Cancelled")
                return

            result = wf.execute()
            self._emit_progress(100.0, f"Complete: {output_name}")
            logger.info("Workflow '%s' finished successfully.", output_name)
            return result  # noqa: TRY300

        except Exception:
            logger.exception("Workflow execution failed.")
            self._emit_progress(0.0, "Error during processing")

    def _run_preview(
        self, workflow: Any, input_layer: Any, visible_extent: Any
    ) -> None:
        """Background preview execution target."""
        if grdl_rt is None:
            logger.error("grdl-runtime is not installed — cannot run preview.")
            self._emit_progress(0.0, "Error: grdl-runtime not available")
            return

        try:
            self._emit_progress(0.0, "Starting preview…")

            wf = workflow
            if isinstance(workflow, grdl_rt.WorkflowDefinition):
                wf = grdl_rt.Workflow(name=workflow.name)
                for level in workflow.topological_sort():
                    for step_id in level:
                        step_def = workflow.get_step(step_id)
                        wf = wf.step(step_def.processor_name, **(step_def.params or {}))

            source_path = getattr(input_layer, "source_path", None)
            if source_path:
                wf = wf.source(source_path)

            # Chip to visible extent if available
            if visible_extent is not None:
                wf = wf.chip(extent=visible_extent)

            self._emit_progress(10.0, "Executing preview…")

            if self._cancel_event.is_set():
                self._emit_progress(0.0, "Preview cancelled")
                return

            result = wf.execute()
            self._emit_progress(100.0, "Preview complete")
            return result  # noqa: TRY300

        except Exception:
            logger.exception("Preview execution failed.")
            self._emit_progress(0.0, "Preview error")
