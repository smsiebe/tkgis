# tkgis — Python Tkinter GIS Workbench

tkgis is a Python tkinter-based desktop GIS application designed to rival QGIS and ArcPro in features while matching Google Earth's simplicity. It combines very large image handling (remotely sensed imagery via GRDL), vector data (via geopandas), and spatiotemporal analysis in a modern, extensible interface. Its flagship feature is a **visual drag-and-drop workflow builder** (like QGIS Model Builder / Orange Data Mining) that composes GRDL raster processors, vector operators, and I/O nodes into DAG workflows — saved as grdl-runtime YAML for headless or AuraGrid execution.

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│              tkgis GUI (customtkinter/ttkbootstrap)       │
│  Map Canvas │ Layer Tree │ Toolbox │ Charts               │
│  Attribute Table │ Time Slider │ Plugin Manager           │
│  ┌──────────────────────────────────────────────────┐    │
│  │  Visual DAG Workflow Builder (drag-and-drop)      │    │
│  │  Node Palette │ Canvas │ Inspector │ Execution    │    │
│  └──────────────────────────┬───────────────────────┘    │
└─────────────────────────────┼────────────────────────────┘
                              │
          ┌───────────────────┼──────────────┐
          ▼                   ▼              ▼
    ┌────────────┐  ┌───────────────┐  ┌───────────┐
    │   GRDL     │  │ grdl-runtime  │  │ geopandas │
    │ (I/O +     │  │ (workflow     │  │ (vector   │
    │  FeatureSet│  │  engine +     │  │  I/O)     │
    │  + Vector  │  │  WorkflowGraph│  │           │
    │  Operators)│  │  + DAG exec)  │  │           │
    └────────────┘  └──────┬────────┘  └───────────┘
                           │
                    ┌──────┴──────┐
                    ▼             ▼
              ┌──────────┐  ┌─────────┐
              │ AuraGrid │  │ CLI     │
              │ (remote  │  │ (local  │
              │  exec)   │  │  exec)  │
              └──────────┘  └─────────┘
```

## Project Structure

```
tkgis/
├── CLAUDE.md                  ← This file
├── TKGIS_TASKGROUP.md         ← Build plan (agentic task groups)
├── pyproject.toml
├── requirements.txt
├── src/
│   └── tkgis/
│       ├── __init__.py
│       ├── __main__.py        ← Entry: python -m tkgis
│       ├── app.py             ← TkGISApp main window
│       ├── config.py          ← Application config (~/.tkgis/config.json)
│       ├── constants.py       ← Version, app name, defaults
│       ├── models/            ← Domain models (no GUI imports)
│       │   ├── geometry.py    ← BoundingBox
│       │   ├── crs.py         ← CRSDefinition
│       │   ├── layers.py      ← Layer, LayerType, LayerStyle
│       │   ├── project.py     ← Project, MapView
│       │   ├── events.py      ← EventBus, EventType
│       │   └── tools.py       ← BaseTool, ToolManager, ToolMode
│       ├── canvas/            ← Map rendering engine
│       │   ├── map_canvas.py  ← MapCanvas (tile-based renderer)
│       │   ├── transform.py   ← ViewTransform (screen↔map coords)
│       │   ├── tiles.py       ← TileProvider ABC, TileCache
│       │   ├── minimap.py     ← Overview widget
│       │   └── overlays.py    ← Grid, scale bar
│       ├── crs/               ← CRS engine
│       │   ├── engine.py      ← CRSEngine (pyproj wrapper)
│       │   ├── formatting.py  ← Coordinate formatters
│       │   └── selector.py    ← CRS selector dialog
│       ├── io/                ← Data backends
│       │   ├── vector.py      ← VectorLayerData (geopandas)
│       │   ├── vector_tiles.py← Vector tile renderer
│       │   ├── raster_tiles.py← RasterTileProvider (GRDL)
│       │   ├── raster_geoloc.py← Geolocation bridge
│       │   ├── raster_metadata.py
│       │   └── raster_display.py
│       ├── panels/            ← Dockable panels
│       │   ├── base.py        ← BasePanel ABC
│       │   ├── registry.py    ← PanelRegistry
│       │   ├── layer_tree.py  ← Layer management
│       │   ├── time_slider.py ← Temporal controls
│       │   ├── toolbox.py     ← Processing catalog
│       │   ├── workflow_builder.py
│       │   ├── chart_panel.py ← Matplotlib charts
│       │   └── attribute_table.py
│       ├── plugins/           ← Plugin system
│       │   ├── base.py        ← TkGISPlugin ABC
│       │   ├── manifest.py    ← PluginManifest
│       │   ├── discovery.py   ← Plugin discovery
│       │   ├── manager.py     ← Plugin lifecycle
│       │   ├── providers.py   ← DataProvider ABC
│       │   └── builtin/       ← Built-in plugins
│       │       ├── vector_provider.py
│       │       └── raster_provider.py
│       ├── tools/             ← Map interaction tools
│       │   ├── measure.py     ← Distance, Area
│       │   ├── identify.py    ← Feature identification
│       │   └── select.py      ← Feature selection
│       ├── processing/        ← grdl-runtime integration
│       │   ├── executor.py    ← Background workflow execution
│       │   ├── run_dialog.py
│       │   └── workflow_io.py ← YAML save/load
│       ├── query/             ← Spatial/attribute queries
│       │   ├── engine.py      ← SpatialQueryEngine
│       │   ├── expression.py  ← Safe expression parser
│       │   └── dialog.py
│       ├── analysis/          ← Spatiotemporal analysis
│       │   ├── time_series.py
│       │   ├── change_detection.py
│       │   ├── zonal.py
│       │   ├── interpolation.py
│       │   └── dialog.py
│       ├── temporal/          ← Temporal data management
│       │   ├── manager.py
│       │   └── raster_stack.py
│       ├── charts/            ← Matplotlib chart types
│       │   ├── base.py
│       │   ├── container.py
│       │   ├── spectral.py
│       │   ├── histogram.py
│       │   ├── scatter.py
│       │   └── time_series.py
│       ├── workflow/          ← Visual DAG workflow builder
│       │   ├── canvas.py      ← Node graph canvas (tkinter Canvas)
│       │   ├── palette.py     ← Node palette panel (catalog browser)
│       │   ├── inspector.py   ← Node property inspector
│       │   ├── edges.py       ← Edge rendering and connection logic
│       │   ├── builder_window.py ← Top-level workflow builder window
│       │   ├── dnd.py         ← Drag-and-drop palette → canvas
│       │   ├── history.py     ← Undo/redo stack
│       │   ├── preview.py     ← Live workflow preview on map
│       │   └── layer_nodes.py ← Layer input/output pseudo-nodes
│       ├── widgets/           ← Reusable custom widgets
│       │   └── data_table.py
│       └── resources/         ← Icons, assets
└── tests/
```

## Tech Stack

- **Language**: Python 3.11+
- **GUI**: customtkinter (primary), ttkbootstrap (supplementary Treeview/Notebook)
- **Raster I/O**: GRDL (SAR, EO, multispectral, GeoTIFF, NITF, HDF5, JP2)
- **Image Processing**: grdl-runtime (workflow execution, processor catalog, GPU dispatch)
- **Vector I/O**: geopandas + pyogrio
- **CRS/Projections**: pyproj
- **Plotting**: matplotlib (FigureCanvasTkAgg backend)
- **Serialization**: JSON (project files), YAML (workflows), Pydantic (validation)
- **Testing**: pytest

## Conventions

### Code Style
- Type hints on all public methods
- `dataclass` for simple models, Pydantic `BaseModel` for validated models
- Models in `models/` must NEVER import GUI libraries
- Use `from __future__ import annotations` in all files for forward references

### Patterns
- **EventBus**: All state changes emit events. GUI subscribes reactively. Never call GUI methods from models.
- **Panel Registration**: Panels register via `PanelRegistry.register()`. Never hardcode panels in `app.py`.
- **Plugin Architecture**: Plugins extend via `TkGISPlugin.activate()`. Built-in functionality uses the same plugin API.
- **Data Provider**: File open requests route through `DataProviderRegistry`. Each format has a registered `DataProvider`.
- **Tile Rendering**: Large rasters render via `TileProvider` → `TileCache` → `MapCanvas`. Never load full images.
- **Background Processing**: Heavy operations (I/O, processing, analysis) run in `threading.Thread`. Use `widget.after()` for UI updates.

### GRDL Integration
- All raster I/O through `grdl.IO` readers (never rasterio/GDAL directly)
- All image processing through `grdl_rt.Workflow` builder (never processor `.apply()` directly)
- All vector operations through `grdl.vector` operators (FeatureSet-based)
- Processors discovered via `grdl_rt.discover_processors()`
- Parameter specs from processor `__param_specs__` drive auto-generated UI in both toolbox and workflow builder

### Visual Workflow Builder
- The workflow builder is a **view** over grdl-runtime's `WorkflowGraph` API — all state lives in the graph
- Saved workflows are grdl-runtime YAML v3.0 — no tkgis-specific fields
- Nodes are color-coded by data type: blue=raster, green=vector, orange=detection, gray=I/O, purple=conversion
- Connections validate type compatibility at design time (green=valid, red=invalid)
- Execution goes through grdl-runtime's DAG executor — the builder never executes processors directly
- Workflows are portable: runnable via grdl-runtime CLI, publishable to AuraGrid

### Testing
- `pytest tests/ -x -q`
- Tkinter tests: create `tk.Tk()` in fixtures, destroy after
- Use small test fixtures (100x100 GeoTIFF, 10-feature GeoJSON)
- No network access in tests

## Key Design Decisions

- **customtkinter over Qt**: MIT license, modern appearance, simpler API. Trade-off: fewer widgets.
- **GRDL for raster I/O**: Unified API for SAR/EO/MSI with lazy chip reading for large images.
- **grdl-runtime for processing**: Provides metadata injection, GPU dispatch, catalog, and workflow serialization.
- **Tile-based rendering**: 256px tiles with LRU cache enables smooth viewing of arbitrarily large imagery.
- **EventBus decoupling**: Enables plugin architecture without component coupling.
- **geopandas for vector**: De facto Python standard. DataFrame API feeds attribute table directly.
- **Visual DAG builder over code-only**: Users compose workflows by dragging nodes and connecting ports (QGIS/Orange paradigm). Saves as grdl-runtime YAML for portability to CLI and AuraGrid.
- **FeatureSet in GRDL (upstream)**: Generic vector container alongside DetectionSet. Enables vector operations as first-class workflow nodes.
- **WorkflowGraph API in grdl-runtime (upstream)**: Introspection/mutation API that the visual builder projects onto. Separates construction from execution.

## Environment

- **Platform**: Windows 11 primary, cross-platform secondary
- **Python**: 3.11+ (match GRDL minimum)
- **Entry point**: `python -m tkgis` or `tkgis` (console script)
- **Config directory**: `~/.tkgis/` (config.json, plugins.json, plugins/)
