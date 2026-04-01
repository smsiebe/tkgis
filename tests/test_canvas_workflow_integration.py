"""Integration tests for MapCanvas and WorkflowBuilder interaction."""
from __future__ import annotations

import tkinter as tk
import pytest
from unittest.mock import MagicMock, patch

from tkgis.models.events import EventBus, EventType
from tkgis.workflow.canvas import WorkflowCanvas
from tkgis.panels.workflow_builder import WorkflowBuilderPanel
from tkgis.canvas.map_canvas import MapCanvas
from tkgis.models.tools import ToolManager
from tkgis.processing.executor import ProcessingExecutor

@pytest.fixture
def tk_root():
    root = tk.Tk()
    root.withdraw()
    yield root
    root.destroy()

def test_workflow_preview_interacts_with_canvas(tk_root):
    """Verify WorkflowBuilder preview triggers execution bound to MapCanvas."""
    event_bus = EventBus()
    tool_manager = ToolManager(event_bus=event_bus)
    
    map_canvas = MapCanvas(tk_root, event_bus=event_bus, tool_manager=tool_manager)
    map_canvas.pack()
    
    executor = ProcessingExecutor(event_bus)
    builder_panel = WorkflowBuilderPanel(event_bus=event_bus, executor=executor)
    builder_widget = builder_panel.create_widget(tk_root)
    builder_widget.pack()
    
    # Add a simple workflow step
    builder_panel.add_step("tkgis.input.raster", {"layer_id": "test_layer"})
    
    # Capture progress events to ensure the preview executes
    events_captured = []
    def on_progress(**kwargs):
        events_captured.append(kwargs)
        
    event_bus.subscribe(EventType.PROGRESS_UPDATED, on_progress)
    
    # Mock grdl_rt to avoid actual processing and registration issues
    with patch('tkgis.panels.workflow_builder.grdl_rt') as mock_gr_rt, \
         patch('tkgis.processing.executor.grdl_rt') as mock_exec_gr_rt:
        
        # Setup mock workflow
        mock_wf = MagicMock()
        mock_gr_rt.Workflow.return_value = mock_wf
        mock_wf.step.return_value = mock_wf
        mock_wf.source.return_value = mock_wf
        mock_wf.chip.return_value = mock_wf
        
        # Make builder_panel use our mock
        # (It's already patched because it imports grdl_rt at module level or inside methods)
        
        # Get the visible extent from MapCanvas for the preview
        extent = map_canvas.view.get_visible_extent()
        
        # Execute preview
        executor.execute_preview(builder_panel._build_workflow(), None, extent)
        
        # Let threads process
        import time
        for _ in range(10):
            if any("Starting preview" in e.get("message", "") for e in events_captured):
                break
            time.sleep(0.05)
        
        # Assert execution was triggered
        assert any("Starting preview" in e.get("message", "") for e in events_captured)
