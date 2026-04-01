# ADR 002: Monolithic Workflow Refactoring

## Status
Accepted

## Context
The visual workflow builder's main canvas (`WorkflowCanvas` in `src/tkgis/workflow/canvas.py`) had grown into a monolithic 25KB file. It tightly coupled visual state, complex rendering logic (node bodies, headers, bezier edges), and business logic for graph interactions, creating a severe maintenance risk. Furthermore, it relied on embedded fallback classes when `grdl-runtime` was unavailable.

## Decision
We decoupled the `WorkflowCanvas` by splitting its responsibilities:
1. **NodeRenderer**: Extracted to handle drawing node bodies, titles, parameters, and ports.
2. **VisualState**: A pure data class introduced to track interactive state (selection, dragging, connection start).
3. **models_fallback.py**: A new module that houses all `grdl-runtime` fallback classes (`FallbackGraph`, `_FallbackNodeInfo`, `_FallbackEdgeInfo`).

## Consequences
- **Positive:** Improved maintainability by reducing `canvas.py` file size and separating visual logic from state.
- **Positive:** Extensibility is enhanced. The isolated `NodeRenderer` can be easily swapped for an OpenGL/Vulkan accelerated version or SVG exporter in the future.
- **Negative:** Slightly increased module complexity due to the new files, requiring developers to navigate multiple files to understand the full rendering pipeline.