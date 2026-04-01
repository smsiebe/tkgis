# tkgis -- Application Architecture

*Modified: 2026-03-26*

## Overview

tkgis is a Python tkinter-based desktop GIS workbench for viewing,
analyzing, and processing geospatial imagery and vector data. It
combines tile-based raster rendering (via GRDL), vector data management
(via geopandas), and a visual drag-and-drop workflow builder (backed by
grdl-runtime) in a single extensible application.

**Scale:** ~85 source files across 15 modules in `src/tkgis/`, plus
~270 tests across 20 test files.

---

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        tkgis Application                            │
│                                                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────┐  ┌─────────────┐  │
│  │  MapCanvas   │  │  LayerTree   │  │ Toolbox  │  │  ChartPanel │  │
│  │  (canvas/)   │  │  (panels/)   │  │(panels/) │  │  (panels/)  │  │
│  └──────┬───────┘  └──────┬───────┘  └────┬─────┘  └──────┬──────┘  │
│         │                 │               │               │         │
│  ┌──────┴─────┐  ┌───────┴──────┐  ┌─────┴──────┐  ┌─────┴──────┐ │
│  │ AttrTable  │  │  TimeSlider   │  │ QueryDlg   │  │ Workflow   │ │
│  │ (panels/)  │  │  (panels/)    │  │ (query/)   │  │ Builder    │ │
│  └──────┬─────┘  └───────┬──────┘  └─────┬──────┘  │(workflow/) │ │
│         │                │               │         └─────┬──────┘ │
│         └────────┬───────┴───────┬───────┘               │        │
│                  │               │                       │        │
│           ┌──────▼───────────────▼───────────────────────▼──┐     │
│           │                  EventBus                        │     │
│           │              (models/events.py)                  │     │
│           └──────┬───────────────┬───────────────────────┬──┘     │
│                  │               │                       │        │
│         ┌────────▼──────┐ ┌──────▼──────┐  ┌────────────▼─────┐  │
│         │    Layer      │ │   Project   │  │   ToolManager    │  │
│         │ (models/)     │ │  (models/)  │  │   (models/)      │  │
│         └────────┬──────┘ └──────┬──────┘  └────────────┬─────┘  │
│                  │               │                      │        │
└──────────────────┼───────────────┼──────────────────────┼────────┘
                   │               │                      │
         ┌─────────▼──────┐ ┌─────▼──────┐  ┌────────────▼─────┐
         │  io/            │ │ processing/│  │  plugins/        │
         │                 │ │            │  │                  │
         │ VectorLayerData │ │  Executor  │  │ DataProvider     │
         │ RasterTileProv  │ │  YAML I/O  │  │ Registry         │
         └───────┬─────────┘ └─────┬──────┘  └──────────────────┘
                 │                 │
         ┌───────▼──────┐  ┌──────▼──────┐
         │   geopandas   │  │ grdl-runtime│
         │   pyogrio     │  │             │
         └───────────────┘  │ Workflow    │
                            │ Graph +     │
         ┌───────────────┐  │ DAG exec    │
         │     GRDL      │  └──────┬──────┘
         │  (raster I/O, │         │
         │   geolocation)│  ┌──────▼──────┐
         └───────────────┘  │  AuraGrid   │
                            │  (remote)   │
                            └─────────────┘
```

---

## Module Map

```
src/tkgis/                           ~85 files, 15 modules
│
├── __init__.py                      Package root, __version__
├── __main__.py                      Entry point: python -m tkgis
├── app.py                           TkGISApp main window, panel layout, menu bar
├── config.py                        Application config (~/.tkgis/config.json)
├── constants.py                     Version, app name, geometry defaults, theme
│
├── models/                          Domain models (no GUI dependencies)
│   ├── geometry.py                    BoundingBox
│   ├── crs.py                        CRSDefinition
│   ├── layers.py                     Layer, LayerType, LayerStyle
│   ├── project.py                    Project, MapView
│   ├── events.py                     EventBus, EventType enum
│   └── tools.py                      BaseTool, ToolManager, ToolMode
│
├── canvas/                          Tile-based map rendering engine
│   ├── map_canvas.py                  MapCanvas (tile renderer on tkinter Canvas)
│   ├── transform.py                   ViewTransform (screen ↔ map coordinate mapping)
│   ├── tiles.py                       TileProvider ABC, TileCache (LRU)
│   ├── minimap.py                     Overview/minimap widget
│   └── overlays.py                    Grid lines, scale bar, north arrow
│
├── crs/                             CRS engine
│   ├── engine.py                      CRSEngine (pyproj wrapper, transform caching)
│   ├── formatting.py                  Coordinate formatters (DD, DMS, UTM, MGRS)
│   └── selector.py                    CRS selector dialog
│
├── io/                              Data backends
│   ├── vector.py                      VectorLayerData (geopandas GeoDataFrame wrapper)
│   ├── vector_tiles.py                Vector tile renderer (geometry → canvas items)
│   ├── raster_tiles.py                RasterTileProvider (GRDL reader → 256px tiles)
│   ├── raster_geoloc.py               Geolocation bridge (GRDL geolocation → ViewTransform)
│   ├── raster_metadata.py             Raster metadata extraction and display
│   └── raster_display.py              Raster display transforms (stretch, colormap)
│
├── panels/                          Dockable GUI panels
│   ├── base.py                        BasePanel ABC
│   ├── registry.py                    PanelRegistry (extensible dock system)
│   ├── layer_tree.py                  Layer management panel (visibility, reorder, style)
│   ├── attribute_table.py             Attribute table (virtual scrolling, expression filter)
│   ├── toolbox.py                     Processing toolbox (grdl-runtime catalog browser)
│   ├── workflow_builder.py            Workflow builder panel (embeds workflow/ module)
│   ├── chart_panel.py                 Matplotlib chart panel (embeds charts/ module)
│   └── time_slider.py                 Temporal controls (playback, step, range)
│
├── plugins/                         Plugin system
│   ├── base.py                        TkGISPlugin ABC (activate, deactivate lifecycle)
│   ├── manifest.py                    PluginManifest (name, version, dependencies)
│   ├── discovery.py                   Plugin discovery (3 vectors: builtin, directory, entry points)
│   ├── manager.py                     Plugin lifecycle manager
│   ├── providers.py                   DataProvider ABC, DataProviderRegistry
│   └── builtin/                       Built-in plugins
│       ├── vector_provider.py           VectorDataProvider (geopandas formats)
│       └── raster_provider.py           RasterDataProvider (GRDL formats)
│
├── tools/                           Map interaction tools
│   ├── measure.py                     Distance and area measurement tools
│   ├── identify.py                    Feature identification (click → attributes)
│   └── select.py                      Feature selection (click, box, polygon)
│
├── processing/                      grdl-runtime integration
│   ├── executor.py                    Background workflow execution (threading)
│   ├── workflow_io.py                 Workflow YAML save/load (grdl-runtime v3.0)
│   └── run_dialog.py                  Execution progress dialog
│
├── query/                           Spatial and attribute queries
│   ├── engine.py                      SpatialQueryEngine (within, intersects, buffer)
│   ├── expression.py                  Safe expression parser (attribute filtering)
│   └── dialog.py                      Query builder dialog
│
├── analysis/                        Spatiotemporal analysis
│   ├── change_detection.py            Multi-modal change detection
│   ├── zonal.py                       Zonal statistics (polygon → raster summary)
│   ├── interpolation.py               IDW spatial interpolation
│   ├── time_series.py                 Time series extraction and analysis
│   └── dialog.py                      Analysis configuration dialog
│
├── temporal/                        Temporal data management
│   ├── manager.py                     TemporalLayerManager (time-indexed layer sets)
│   └── raster_stack.py                Temporal raster stack (time-ordered bands/files)
│
├── charts/                          Matplotlib chart types
│   ├── base.py                        BaseChart ABC
│   ├── container.py                   ChartContainer (FigureCanvasTkAgg host)
│   ├── spectral.py                    Spectral profile chart
│   ├── histogram.py                   Histogram chart
│   ├── scatter.py                     Scatter plot chart
│   └── time_series.py                 Time series chart
│
├── workflow/                        Visual DAG workflow builder
│   ├── canvas.py                      Node graph canvas and renderers
│   ├── models_fallback.py             Fallback models when grdl-runtime is unavailable
│   ├── palette.py                     Node palette (catalog browser, search, categories)
│   ├── inspector.py                   Node property inspector (auto-generated from __param_specs__)
│   ├── edges.py                       Edge rendering and connection logic (bezier curves)
│   ├── builder_window.py              Top-level workflow builder window
│   ├── dnd.py                         Drag-and-drop from palette to canvas
│   ├── history.py                     Undo/redo stack (command pattern)
│   ├── preview.py                     Live workflow preview on map canvas
│   └── layer_nodes.py                 Layer input/output pseudo-nodes
│
├── widgets/                         Reusable custom widgets
│   └── data_table.py                  DataTableWidget (virtual scrolling for large DataFrames)
│
└── resources/                       Icons and assets
```

---

## Design Patterns

### 1. EventBus (Pub/Sub Decoupling)

All state changes in tkgis propagate through a central `EventBus`.
Domain models emit events; GUI components subscribe to them. This
enforces a strict separation: models never import GUI code, and GUI
components never call each other directly.

```python
from tkgis.models.events import EventBus, EventType

# Model emits
bus = EventBus()
bus.emit(EventType.LAYER_ADDED, layer=layer)

# GUI subscribes
bus.subscribe(EventType.LAYER_ADDED, self._on_layer_added)
```

`EventType` is an enum covering all state transitions: layer
add/remove/reorder, selection changes, CRS changes, tool activation,
project load/save, and workflow graph mutations.

### 2. Panel Registration

Panels register themselves with `PanelRegistry` rather than being
hardcoded in `app.py`. This makes the dock system extensible -- plugins
can register new panels at activation time.

```python
from tkgis.panels.registry import PanelRegistry

PanelRegistry.register("layer_tree", LayerTreePanel, position="left")
PanelRegistry.register("attributes", AttributeTablePanel, position="bottom")
```

The `TkGISApp` iterates registered panels at startup and creates the
dock layout. Panel visibility is togglable via the View menu.

### 3. Plugin Architecture

Plugins extend tkgis through the `TkGISPlugin` abstract base class.
Each plugin declares a manifest (name, version, dependencies) and
implements `activate(app)` / `deactivate()` lifecycle hooks.

Three discovery vectors:

| Vector | Location | Mechanism |
|--------|----------|-----------|
| Built-in | `plugins/builtin/` | Direct import |
| Directory | `~/.tkgis/plugins/` | Filesystem scan, dynamic import |
| Entry points | `pyproject.toml` | `importlib.metadata.entry_points("tkgis.plugins")` |

Built-in functionality (vector and raster file loading) uses the same
plugin API as third-party extensions, ensuring the API is sufficient
for real use cases.

### 4. Data Provider Registry

File open requests route through `DataProviderRegistry`. Each
registered `DataProvider` declares the file extensions and MIME types
it handles. When the user opens a file, the registry finds the matching
provider and delegates loading.

```python
from tkgis.plugins.providers import DataProviderRegistry

# Registration (typically in plugin.activate)
registry.register(VectorDataProvider())
registry.register(RasterDataProvider())

# Lookup
provider = registry.find_provider("scene.tif")
layer = provider.load("scene.tif")
```

This pattern decouples the application from specific I/O
implementations and allows plugins to register handlers for new
formats.

### 5. Tile-Based Rendering

Large rasters (gigapixels) never load fully into memory. Instead:

1. `RasterTileProvider` wraps a GRDL `ImageReader` and produces 256px
   tiles on demand.
2. `TileCache` stores rendered tiles in an LRU cache keyed by
   (zoom level, tile row, tile column).
3. `MapCanvas` determines which tiles are visible at the current
   `ViewTransform` and requests only those tiles.
4. Tiles load in background threads. `widget.after()` schedules the
   Canvas update on the main thread when a tile is ready.

This architecture ensures smooth panning and zooming regardless of
image size.

### 6. Tool Manager (Active Tool Pattern)

Map interactions (pan, zoom, measure, identify, select) are modeled as
`BaseTool` subclasses managed by `ToolManager`. Only one tool is active
at a time. The active tool receives all mouse and keyboard events from
the `MapCanvas`.

```python
from tkgis.models.tools import ToolManager, ToolMode

manager = ToolManager(canvas)
manager.activate(ToolMode.PAN)       # Pan tool receives events
manager.activate(ToolMode.MEASURE)   # Measure tool takes over
```

New tools are registered by subclassing `BaseTool` and adding them to
the manager. Plugins can register custom tools.

### 7. Background Processing

All heavy operations (raster I/O, image processing, spatial analysis)
run in `threading.Thread` to keep the GUI responsive. Results are
delivered back to the main thread via `widget.after()`:

```python
import threading

def _run_workflow(self, workflow):
    def _execute():
        result = self.executor.run(workflow)
        self.canvas.after(0, self._on_complete, result)

    thread = threading.Thread(target=_execute, daemon=True)
    thread.start()
```

The `processing/executor.py` module wraps grdl-runtime's DAG executor
with progress callbacks that update the `run_dialog.py` progress bar.

### 8. WorkflowGraph as Single Source of Truth

The visual workflow builder is a **view** over grdl-runtime's
`WorkflowGraph` API. All workflow state (nodes, edges, parameters)
lives in the graph object. The visual canvas (`workflow/canvas.py`)
projects this state onto tkinter Canvas items. User interactions
(drag, connect, configure) mutate the graph, which emits events that
the canvas observes and re-renders.

This separation means:

- Saved workflows contain no tkgis-specific fields (pure grdl-runtime
  YAML v3.0)
- Workflows are portable to grdl-runtime CLI and AuraGrid
- The visual builder can be replaced without affecting workflow logic
- Undo/redo operates on graph mutations, not canvas state

---

## Data Model

### Core Types

| Type | Module | Purpose |
|------|--------|---------|
| `Layer` | `models/layers.py` | Represents a data layer (raster or vector) with style, visibility, CRS |
| `LayerType` | `models/layers.py` | Enum: RASTER, VECTOR |
| `LayerStyle` | `models/layers.py` | Rendering style (opacity, colormap, line color, fill) |
| `Project` | `models/project.py` | Collection of layers, map view state, CRS |
| `MapView` | `models/project.py` | Current viewport (center, zoom, rotation) |
| `BoundingBox` | `models/geometry.py` | Geographic extent (min_x, min_y, max_x, max_y) |
| `CRSDefinition` | `models/crs.py` | CRS identifier and metadata (wraps pyproj.CRS) |
| `EventBus` | `models/events.py` | Pub/sub event dispatcher |
| `EventType` | `models/events.py` | Enum of all application events |
| `BaseTool` | `models/tools.py` | ABC for map interaction tools |
| `ToolManager` | `models/tools.py` | Active tool manager |
| `ToolMode` | `models/tools.py` | Enum of tool modes (PAN, ZOOM, MEASURE, IDENTIFY, SELECT) |

### Design constraint

Everything in `models/` is pure Python with no GUI imports. This
allows models to be used in headless contexts (testing, scripting) and
enforces the EventBus decoupling pattern.

---

## I/O Architecture

### Raster Data Flow

```
File on disk
    │
    ▼
GRDL ImageReader (SICDReader, GeoTIFFReader, etc.)
    │
    ├── read_chip(r0, r1, c0, c1)  ← lazy, reads only requested region
    │
    ▼
RasterTileProvider (io/raster_tiles.py)
    │
    ├── Computes tile grid for current zoom level
    ├── Calls reader.read_chip() for each visible tile
    ├── Applies display transform (stretch, colormap)
    │
    ▼
TileCache (canvas/tiles.py)
    │
    ├── LRU cache keyed by (zoom, row, col)
    ├── Background thread fills cache
    │
    ▼
MapCanvas (canvas/map_canvas.py)
    │
    └── Renders cached PIL.Image tiles as tkinter PhotoImage items
```

**Geolocation:** `raster_geoloc.py` bridges GRDL's `Geolocation` ABC
to the `ViewTransform`, enabling pixel-to-geographic coordinate mapping
for cursor readout, overlay placement, and CRS reprojection.

### Vector Data Flow

```
File on disk (.shp, .geojson, .gpkg, .kml, ...)
    │
    ▼
geopandas.read_file() via pyogrio driver
    │
    ▼
VectorLayerData (io/vector.py)
    │
    ├── Wraps GeoDataFrame
    ├── Provides spatial index (STRtree)
    ├── Feeds attribute table (panels/attribute_table.py)
    │
    ▼
VectorTileRenderer (io/vector_tiles.py)
    │
    ├── Projects geometries through ViewTransform
    ├── Creates tkinter Canvas items (lines, polygons, points)
    ├── Culls off-screen features for performance
    │
    ▼
MapCanvas (canvas/map_canvas.py)
```

### Supported Formats

**Raster (via GRDL):**

| Format | Extensions | Notes |
|--------|-----------|-------|
| GeoTIFF | `.tif`, `.tiff` | Via rasterio |
| NITF | `.nitf`, `.ntf` | Including SICD, SIDD |
| SICD | `.nitf` | Complex SAR (sarkit/sarpy) |
| CPHD | `.cphd` | Phase history |
| Sentinel-1 SLC | `.zip`, `.SAFE` | Annotation + measurement |
| Sentinel-2 | `.zip`, `.SAFE` | L1C/L2A multispectral |
| HDF5 | `.h5`, `.hdf5`, `.he5` | Generic + sensor-specific |
| JPEG2000 | `.jp2` | Via glymur |

**Vector (via geopandas + pyogrio):**

| Format | Extensions |
|--------|-----------|
| Shapefile | `.shp` |
| GeoJSON | `.geojson`, `.json` |
| GeoPackage | `.gpkg` |
| KML | `.kml`, `.kmz` |
| GML | `.gml` |
| FlatGeobuf | `.fgb` |
| GeoParquet | `.parquet` |
| CSV (with geometry) | `.csv` |
| FileGDB | `.gdb` |

---

## Workflow Builder Architecture

The visual workflow builder is the flagship feature. It provides a
node-graph editor that composes grdl-runtime processors into DAG
workflows.

### Component Relationships

```
┌─────────────────────────────────────────────────────────┐
│  WorkflowBuilderWindow (workflow/builder_window.py)     │
│                                                         │
│  ┌──────────┐  ┌──────────────────┐  ┌───────────────┐ │
│  │ Palette   │  │ WorkflowCanvas   │  │  Inspector    │ │
│  │ (palette  │  │ (canvas.py)      │  │  (inspector   │ │
│  │  .py)     │──│                  │──│   .py)        │ │
│  │           │  │  Node items      │  │               │ │
│  │ Catalog   │  │  Edge items      │  │  Param UI     │ │
│  │ browser   │  │  DnD target      │  │  (auto-gen)   │ │
│  └──────────┘  └────────┬─────────┘  └───────────────┘ │
│                         │                               │
│                  ┌──────▼──────┐                        │
│                  │   History   │                        │
│                  │ (history.py)│                        │
│                  │ undo/redo   │                        │
│                  └──────┬──────┘                        │
└─────────────────────────┼───────────────────────────────┘
                          │
                   ┌──────▼──────────┐
                   │  WorkflowGraph  │
                   │  (grdl-runtime) │
                   │                 │
                   │  Nodes, edges,  │
                   │  parameters,    │
                   │  type system    │
                   └──────┬──────────┘
                          │
                   ┌──────▼──────────┐
                   │  YAML v3.0     │
                   │  (portable)    │
                   └────────────────┘
```

### Data flow

1. **Palette** discovers processors via `grdl_rt.discover_processors()`
   and displays them grouped by category.
2. **Drag-and-drop** (`dnd.py`) handles palette-to-canvas drops. A drop
   creates a node in the `WorkflowGraph` and a visual node item on the
   canvas.
3. **Edge connections** (`edges.py`) validate type compatibility between
   output and input ports using grdl-runtime's type system. Valid
   connections render as green bezier curves; invalid as red.
4. **Inspector** reads `__param_specs__` from the selected node's
   processor class and generates appropriate controls (sliders for
   `Range`, dropdowns for `Options`, text fields for free-form).
5. **History** (`history.py`) wraps every graph mutation in a command
   object, enabling unlimited undo/redo.
6. **Preview** (`preview.py`) can execute a partial workflow and render
   intermediate results on the map canvas.
7. **Save/Load** (`processing/workflow_io.py`) serializes the
   `WorkflowGraph` to grdl-runtime YAML v3.0 with no tkgis-specific
   extensions.

### Layer nodes

`layer_nodes.py` provides pseudo-nodes that bridge the workflow graph
to tkgis's layer system. A "Layer Input" node reads from an active
layer; a "Layer Output" node writes results back as a new layer. These
nodes have no grdl-runtime equivalent -- they are resolved to file
paths at execution time.

---

## Testing

### Conventions

- Tests live in `tests/` (270 tests across 20 files)
- Framework: `pytest` (no `unittest.TestCase`)
- Tkinter tests: create `tk.Tk()` in fixtures, `destroy()` after
- Test data: small synthetic fixtures (100x100 GeoTIFF, 10-feature
  GeoJSON), no network access
- Each public class/function gets at least one happy-path test and one
  error-condition test

### Running tests

```bash
pytest tests/ -x -q                    # Full suite, stop on first failure
pytest tests/test_canvas.py -v         # Single module
pytest tests/ -x -q --cov=tkgis       # With coverage
```

### Test file organization

Tests follow the naming pattern `test_<module>.py` or
`test_<module>_<submodule>.py`. Major test files cover:

- `test_models.py` -- Layer, Project, EventBus, BoundingBox
- `test_canvas.py` -- MapCanvas, ViewTransform, TileCache
- `test_io.py` -- VectorLayerData, RasterTileProvider
- `test_crs.py` -- CRSEngine, coordinate formatting
- `test_panels.py` -- Panel registration, attribute table
- `test_plugins.py` -- Plugin discovery, lifecycle, DataProvider
- `test_tools.py` -- Tool activation, measurement
- `test_query.py` -- Expression parser, spatial queries
- `test_analysis.py` -- Zonal stats, IDW, change detection
- `test_workflow.py` -- Workflow canvas, palette, history, YAML I/O
- `test_charts.py` -- Chart rendering
- `test_temporal.py` -- Temporal manager, raster stack

---

## Packaging

### Source layout

tkgis uses the `src/` layout with setuptools:

```
tkgis/
├── pyproject.toml          # Build config, dependencies, entry points
├── src/
│   └── tkgis/              # Package root
│       ├── __init__.py     # __version__
│       ├── __main__.py     # python -m tkgis
│       └── ...
└── tests/
```

### Entry points

```toml
[project.scripts]
tkgis = "tkgis.__main__:main"
```

This registers the `tkgis` console script, so `pip install tkgis`
makes the `tkgis` command available system-wide.

### Build and install

```bash
# Development install (editable)
pip install -e ".[dev]"

# Build distribution
python -m build

# Install from wheel
pip install dist/tkgis-0.1.0-py3-none-any.whl
```

### Version management

Version is defined in two places that must be kept in sync:

| File | Location |
|------|----------|
| `pyproject.toml` | `[project] version = "0.1.0"` |
| `src/tkgis/__init__.py` | `__version__ = "0.1.0"` |
