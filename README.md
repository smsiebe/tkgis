# tkgis - Python Tkinter GIS Workbench

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-270%20across%2020%20files-brightgreen.svg)]()

A desktop GIS workbench built on Python and tkinter, designed to handle
arbitrarily large remotely sensed imagery with the analytical depth of
QGIS/ArcGIS Pro and the simplicity of Google Earth.

## What is tkgis?

Geospatial desktop applications fall into two camps: heavyweight
professional tools (QGIS, ArcGIS Pro) that require significant
expertise, and lightweight viewers (Google Earth) that sacrifice
analytical capability for ease of use. tkgis bridges the gap -- a
Python-native GIS workbench that loads SAR, electro-optical,
multispectral, and vector data through a modern, clean interface.
Tile-based rendering means imagery of any size loads smoothly without
exhausting memory.

tkgis is built on GRDL for raster I/O and grdl-runtime for image
processing. This means every format GRDL supports (SICD, CPHD,
Sentinel-1, Sentinel-2, GeoTIFF, NITF, HDF5, JPEG2000) works out of
the box, and every processor in grdl-runtime's catalog (50+) is
available through the processing toolbox. Vector data flows through
geopandas, supporting nine formats including Shapefile, GeoJSON,
GeoPackage, and KML.

The flagship feature is the **Visual DAG Workflow Builder** -- a
drag-and-drop node graph editor following the QGIS Model Builder and
Orange Data Mining paradigm. Users compose raster processors, vector
operators, and I/O nodes into directed acyclic graphs. Workflows save
as grdl-runtime YAML v3.0, making them portable: run them headless via
the grdl-runtime CLI, or publish them to AuraGrid for distributed
compute across a federated node fabric.

## Key Features

- **Tile-based map canvas** for arbitrarily large remotely sensed imagery (256px tiles, LRU cache, background loading)
- **Multi-format raster support** via GRDL: SAR (SICD, CPHD, Sentinel-1), EO (Sentinel-2, NITF), multispectral, GeoTIFF, HDF5, JPEG2000
- **Vector data**: 9 formats via geopandas + pyogrio (Shapefile, GeoJSON, GeoPackage, KML, GML, GPKG, FlatGeobuf, Parquet, CSV)
- **Visual DAG workflow builder** -- drag-and-drop node graph with YAML export and AuraGrid integration
- **Processing toolbox** with 50+ processors from the grdl-runtime catalog, with auto-generated parameter UI
- **Attribute table** with virtual scrolling, expression-based filtering, and bidirectional map synchronization
- **Time slider** for temporal raster and vector animation
- **Charts**: spectral profile, histogram, scatter plot, time series (matplotlib via FigureCanvasTkAgg)
- **Spatiotemporal analysis**: change detection, zonal statistics, IDW interpolation, time series extraction
- **Plugin architecture** with 3 discovery vectors (built-in, directory scan, entry points)
- **CRS engine** with on-the-fly reprojection, coordinate formatting, and interactive CRS selector
- **Modern dark/light theme** via customtkinter + ttkbootstrap

## Screenshots

<!-- TODO: Add screenshots of main window with loaded imagery -->
<!-- TODO: Add screenshot of visual workflow builder with connected nodes -->
<!-- TODO: Add screenshot of attribute table with expression filter -->
<!-- TODO: Add screenshot of time slider animating temporal stack -->
<!-- TODO: Add screenshot of chart panel (spectral profile) -->

## Quick Start

### Install

```bash
pip install tkgis
```

### Launch

#### Using Startup Scripts (Recommended)
The easiest way to launch tkgis is using the provided startup scripts which auto-detect your environment:

- **Linux**: `./tkgis.sh`
- **Windows**: `.\tkgis.ps1` (PowerShell)

These scripts will attempt to find a `.venv` or a `tkgis` conda environment. If not found, they will prompt you for the location and save your preference in `~/.tkgis/config.yml`.

#### Manual Launch
```bash
tkgis
# or
python -m tkgis
```

### Open a file

1. Launch tkgis
2. File > Open or drag a file onto the map canvas
3. Supported formats: GeoTIFF, NITF, SICD, Shapefile, GeoJSON, GeoPackage, and more

```python
# Or use tkgis programmatically
from tkgis.app import TkGISApp

app = TkGISApp()
app.mainloop()
```

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│              tkgis GUI (customtkinter/ttkbootstrap)       │
│  Map Canvas | Layer Tree | Toolbox | Charts               │
│  Attribute Table | Time Slider | Plugin Manager           │
│  ┌──────────────────────────────────────────────────┐    │
│  │  Visual DAG Workflow Builder (drag-and-drop)      │    │
│  │  Node Palette | Canvas | Inspector | Execution    │    │
│  └──────────────────────────┬───────────────────────┘    │
└─────────────────────────────┼────────────────────────────┘
                              │
          ┌───────────────────┼──────────────┐
          v                   v              v
    ┌────────────┐  ┌───────────────┐  ┌───────────┐
    │   GRDL     │  │ grdl-runtime  │  │ geopandas │
    │ (raster    │  │ (workflow     │  │ (vector   │
    │  I/O,      │  │  engine,      │  │  I/O)     │
    │  geoloc)   │  │  processors)  │  │           │
    └────────────┘  └──────┬────────┘  └───────────┘
                           │
                    ┌──────┴──────┐
                    v             v
              ┌──────────┐  ┌─────────┐
              │ AuraGrid │  │ CLI     │
              │ (remote  │  │ (local  │
              │  exec)   │  │  exec)  │
              └──────────┘  └─────────┘
```

**Data flow:** Files open through the `DataProviderRegistry`, which routes to the correct backend (GRDL for rasters, geopandas for vectors). Raster data renders via `TileProvider` into 256px tiles cached in an LRU cache. Vector data renders by projecting geometries through the `ViewTransform`. All state changes propagate through the `EventBus`, keeping GUI components decoupled from domain models.

## Module Overview

| Module | Description |
|--------|-------------|
| `models/` | Domain models with no GUI dependencies: Layer, Project, EventBus, CRS, Tools |
| `canvas/` | Tile-based map renderer: ViewTransform, TileProvider, MapCanvas, minimap, overlays |
| `crs/` | CRS engine: pyproj transforms, coordinate formatting, CRS selector dialog |
| `io/` | Data backends: VectorLayerData (geopandas), RasterTileProvider (GRDL), geolocation bridge |
| `panels/` | Dockable panels: LayerTree, AttributeTable, Toolbox, Charts, TimeSlider, WorkflowBuilder |
| `plugins/` | Plugin system: TkGISPlugin ABC, manifest, discovery, lifecycle, DataProvider registry |
| `tools/` | Map interaction tools: Pan, Zoom, Distance, Area, Identify, Select |
| `processing/` | grdl-runtime integration: background executor, workflow YAML I/O, run dialog |
| `query/` | Spatial and attribute queries: query engine, safe expression parser, query dialog |
| `analysis/` | Spatiotemporal analysis: change detection, zonal statistics, IDW, time series |
| `temporal/` | Temporal data management: TemporalLayerManager, raster stacks, time slider integration |
| `charts/` | Matplotlib chart types: spectral profile, histogram, scatter, time series |
| `workflow/` | Visual DAG builder: node graph canvas, palette, inspector, edges, DnD, undo/redo, preview |
| `widgets/` | Reusable widgets: DataTableWidget with virtual scrolling |
| `resources/` | Icons and assets |

## Installation

### From PyPI

```bash
pip install tkgis
```

### From source

```bash
git clone https://github.com/geoint-org/tkgis.git
cd tkgis
pip install -e .
```

### Development install

```bash
git clone https://github.com/geoint-org/tkgis.git
cd tkgis
pip install -e ".[dev]"
```

### Conda environment

```bash
conda create -n tkgis python=3.11
conda activate tkgis
pip install -e ".[dev]"
```

### Dependencies

**Core (always required):**

| Package | Version | Purpose |
|---------|---------|---------|
| customtkinter | >= 5.2.0 | Modern tkinter widgets, dark/light themes |
| ttkbootstrap | >= 1.10.0 | Themed Treeview, Notebook, and other ttk widgets |
| Pillow | >= 10.0.0 | Image rendering for tkinter Canvas |
| grdl | >= 0.1.0 | Raster I/O (SAR, EO, multispectral, GeoTIFF, NITF, HDF5, JP2) |
| grdl-runtime | >= 0.1.0 | Workflow engine, processor catalog, GPU dispatch |
| geopandas | >= 0.14.0 | Vector data I/O and spatial operations |
| pyogrio | >= 0.7.0 | Fast vector format driver (9 formats) |
| pyproj | >= 3.6.0 | CRS definitions and coordinate transforms |
| matplotlib | >= 3.7.0 | Charts and plotting (FigureCanvasTkAgg backend) |
| numpy | >= 1.20.0 | Array operations |
| scipy | >= 1.7.0 | Spatial analysis, interpolation |
| pandas | >= 2.0.0 | DataFrame operations for attribute tables |
| pydantic | >= 2.0.0 | Model validation (workflows, config) |
| PyYAML | >= 6.0 | Workflow YAML serialization |
| rasterio | >= 1.3.0 | GeoTIFF I/O support |
| shapely | >= 2.0.0 | Geometric operations |

**Development:**

| Package | Version | Purpose |
|---------|---------|---------|
| pytest | >= 7.0 | Test framework |
| pytest-cov | | Coverage reporting |

## Plugin Development

tkgis supports plugins through the `TkGISPlugin` abstract base class.
Plugins can add new data providers, panels, tools, and processing
nodes. Three discovery vectors are supported:

1. **Built-in plugins** -- shipped with tkgis under `plugins/builtin/`
2. **Directory scan** -- drop a plugin into `~/.tkgis/plugins/`
3. **Entry points** -- register via `[project.entry-points."tkgis.plugins"]` in `pyproject.toml`

```python
from tkgis.plugins.base import TkGISPlugin

class MyPlugin(TkGISPlugin):
    name = "my-plugin"
    version = "1.0.0"

    def activate(self, app):
        # Register data providers, panels, tools, etc.
        ...

    def deactivate(self):
        ...
```

<!-- See docs/plugins.md for the full plugin development guide. -->

## Workflow Builder

The Visual DAG Workflow Builder is tkgis's flagship feature. It provides
a drag-and-drop node graph editor for composing image processing
workflows without writing code.

### How it works

1. **Drag nodes** from the palette onto the canvas. Nodes are
   discovered from grdl-runtime's processor catalog and organized by
   category (filters, detectors, I/O, vector operations).
2. **Connect ports** by dragging from an output port to an input port.
   Connections validate type compatibility at design time (green =
   valid, red = invalid).
3. **Configure parameters** in the inspector panel. Parameter controls
   (sliders, dropdowns, text fields) are auto-generated from
   processor `__param_specs__`.
4. **Execute** the workflow locally through grdl-runtime's DAG
   executor, or export for remote execution.

### Node color coding

| Color | Data type |
|-------|-----------|
| Blue | Raster |
| Green | Vector |
| Orange | Detection |
| Gray | I/O |
| Purple | Conversion |

### YAML export

Workflows save as grdl-runtime YAML v3.0 with no tkgis-specific
fields. This means workflows are portable:

```bash
# Run headless via grdl-runtime CLI
grdl-rt run workflow.yaml

# Publish to AuraGrid for distributed compute
auragrid submit workflow.yaml
```

### Undo/redo

The workflow builder maintains a full undo/redo history stack for all
graph mutations (add/remove nodes, connect/disconnect edges, parameter
changes).

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Write tests for new functionality
4. Run the test suite: `pytest tests/ -x -q`
5. Submit a pull request

### Code style

- Type hints on all public methods
- NumPy-style docstrings
- `from __future__ import annotations` in all files
- Models in `models/` must never import GUI libraries

### Running tests

```bash
pytest tests/ -x -q                    # Full suite, stop on first failure
pytest tests/test_canvas.py -v         # Single module
pytest tests/ -x -q --cov=tkgis       # With coverage
```

## Publishing to PyPI

1. Bump `version` in `pyproject.toml` and `src/tkgis/__init__.py`
2. Commit and push:
   ```bash
   git add pyproject.toml src/tkgis/__init__.py
   git commit -m "Bump version to X.Y.Z"
   git push origin main
   ```
3. Create a git tag:
   ```bash
   git tag vX.Y.Z
   git push origin vX.Y.Z
   ```
4. Create a GitHub Release from the tag:
   ```bash
   gh release create vX.Y.Z --title "vX.Y.Z" --notes "Release notes"
   ```
5. The publish workflow builds wheels via `python -m build` and uploads to PyPI.

## License

MIT License. See [LICENSE](LICENSE) for full text.

---

**Author:** Steven Siebert

**Repository:** [github.com/geoint-org/tkgis](https://github.com/geoint-org/tkgis) (planned)
