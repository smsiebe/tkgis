"""Tests for the processing integration — executor, workflow I/O, and panels."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from tkgis.models.events import EventBus, EventType
from tkgis.processing.executor import ProcessingExecutor
from tkgis.processing.workflow_io import load_workflow, save_workflow


# ------------------------------------------------------------------
# ProcessingExecutor
# ------------------------------------------------------------------


class TestProcessingExecutor:
    def test_processing_executor_creation(self):
        """ProcessingExecutor can be instantiated with an EventBus."""
        bus = EventBus()
        executor = ProcessingExecutor(bus)
        assert executor is not None
        assert executor.is_running is False

    def test_executor_cancel_without_running(self):
        """Calling cancel when nothing is running does not raise."""
        bus = EventBus()
        executor = ProcessingExecutor(bus)
        executor.cancel()  # should be a no-op

    def test_executor_emits_progress(self):
        """The executor emits PROGRESS_UPDATED events."""
        bus = EventBus()
        executor = ProcessingExecutor(bus)
        received: list[dict] = []
        bus.subscribe(
            EventType.PROGRESS_UPDATED,
            lambda **kw: received.append(kw),
        )
        # Directly call the internal helper
        executor._emit_progress(50.0, "halfway")
        assert len(received) == 1
        assert received[0]["percent"] == 50.0
        assert received[0]["message"] == "halfway"


# ------------------------------------------------------------------
# Workflow I/O
# ------------------------------------------------------------------


class TestWorkflowIO:
    def test_workflow_save_load_roundtrip(self):
        """Steps survive a save-then-load cycle."""
        steps = [
            {"processor_name": "Median", "params": {"kernel": 3}},
            {"processor_name": "Threshold", "params": {"value": 128}},
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test_workflow.yaml"
            save_workflow(steps, path)

            assert path.exists(), "YAML file was not created"

            loaded = load_workflow(path)
            assert len(loaded) == len(steps)

            for original, restored in zip(steps, loaded):
                assert restored["processor_name"] == original["processor_name"]
                # Params may come back with slight type differences; compare keys
                for key in original["params"]:
                    assert key in restored["params"]
                    assert restored["params"][key] == original["params"][key]

    def test_save_creates_parent_dirs(self):
        """save_workflow creates intermediate directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "sub" / "dir" / "wf.yaml"
            save_workflow([{"processor_name": "Noop", "params": {}}], path)
            assert path.exists()

    def test_load_empty_workflow(self):
        """Loading a workflow with no steps returns an empty list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "empty.yaml"
            save_workflow([], path)
            loaded = load_workflow(path)
            assert loaded == []


# ------------------------------------------------------------------
# Panels (require Tk)
# ------------------------------------------------------------------


class TestToolboxPanel:
    def test_toolbox_panel_creates(self, tk_frame):
        """ProcessingToolboxPanel creates its widget without error."""
        from tkgis.panels.toolbox import ProcessingToolboxPanel

        panel = ProcessingToolboxPanel()
        widget = panel.create_widget(tk_frame)
        assert widget is not None
        assert panel.name == "processing_toolbox"
        assert panel.dock_position == "right"
        assert panel.default_visible is False


class TestWorkflowBuilderPanel:
    def test_workflow_builder_panel_creates(self, tk_frame):
        """WorkflowBuilderPanel creates its widget without error."""
        from tkgis.panels.workflow_builder import WorkflowBuilderPanel

        bus = EventBus()
        executor = ProcessingExecutor(bus)
        panel = WorkflowBuilderPanel(event_bus=bus, executor=executor)
        widget = panel.create_widget(tk_frame)
        assert widget is not None
        assert panel.name == "workflow_builder"
        assert panel.dock_position == "right"
        assert panel.default_visible is False

    def test_workflow_builder_add_step(self, tk_frame):
        """Steps can be added programmatically."""
        from tkgis.panels.workflow_builder import WorkflowBuilderPanel

        panel = WorkflowBuilderPanel()
        panel.create_widget(tk_frame)
        panel.add_step("Median", {"kernel": 5})
        panel.add_step("Threshold", {"value": 100})
        assert len(panel.steps) == 2
        assert panel.steps[0]["processor_name"] == "Median"
        assert panel.steps[1]["processor_name"] == "Threshold"


# ------------------------------------------------------------------
# Catalog discovery
# ------------------------------------------------------------------


class TestCatalogDiscovery:
    def test_catalog_discovery(self):
        """discover_processors returns a dict (may be empty without catalog)."""
        try:
            import grdl_rt

            result = grdl_rt.discover_processors()
            assert isinstance(result, dict)
        except ImportError:
            pytest.skip("grdl-runtime not installed")
