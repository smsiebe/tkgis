# tkgis User Guide

## Getting Started

### Installation

Install tkgis using pip:

```
pip install tkgis
```

For raster imagery support (GeoTIFF, NITF, HDF5, JPEG2000), also install GRDL:

```
pip install grdl
```

For workflow execution, install grdl-runtime:

```
pip install grdl-runtime
```

### First Launch

Start tkgis from the command line:

```
python -m tkgis
```

Or, if the console script is on your PATH:

```
tkgis
```

### UI Overview

The tkgis window is organized into several regions:

- **Menu Bar** (top) -- File, Edit, View, Tools, Analysis, Plugins, Help.
- **Toolbar** (below menu) -- Quick access to navigation, measurement, and selection tools.
- **Map Canvas** (center) -- The main map display. Supports pan, zoom, and tool interactions.
- **Layer Tree** (left panel) -- Lists all loaded layers. Toggle visibility, reorder, and access layer properties.
- **Toolbox** (left or right panel) -- Processing catalog for running analysis operations.
- **Attribute Table** (bottom panel) -- Tabular view of the selected vector layer's features.
- **Time Slider** (bottom) -- Scrub through temporal datasets frame by frame.
- **Status Bar** (bottom edge) -- Displays cursor coordinates, current CRS, and progress messages.

---

## Opening Data

### Raster Files

tkgis opens raster imagery through the GRDL library, which provides a unified reader for multiple sensor formats:

| Format | Extensions | Notes |
|--------|-----------|-------|
| GeoTIFF | `.tif`, `.tiff` | Standard geospatial raster format |
| NITF | `.nitf`, `.ntf` | National Imagery Transmission Format (SAR, EO) |
| HDF5 | `.h5`, `.hdf5` | Hierarchical Data Format |
| JPEG2000 | `.jp2` | Wavelet-compressed imagery |

To open a raster file:

1. Go to **File > Open** or press **Ctrl+O**.
2. In the file dialog, select the raster file.
3. The image will appear on the map canvas. Large images are displayed using a tile-based renderer with a 256-pixel tile cache, so arbitrarily large files can be viewed smoothly without loading the entire image into memory.

### Vector Files

Vector data is handled through geopandas. Supported formats:

| Format | Extensions | Notes |
|--------|-----------|-------|
| Shapefile | `.shp` | Esri Shapefile (also reads .dbf, .shx, .prj) |
| GeoJSON | `.geojson`, `.json` | Open standard, web-friendly |
| GeoPackage | `.gpkg` | OGC standard, SQLite-based |
| KML | `.kml` | Keyhole Markup Language (Google Earth) |
| GML | `.gml` | Geography Markup Language |
| FlatGeobuf | `.fgb` | Optimized binary format |
| CSV | `.csv` | Comma-separated values (requires lat/lon columns) |
| Parquet | `.parquet` | Columnar storage format |

To open a vector file, use **File > Open** or **Ctrl+O** and select the file.

### Temporal Data

For time-series analysis, tkgis can load a directory of images as a temporal stack:

1. Go to **File > Open Temporal Directory** (or equivalent menu option).
2. Select a directory containing images. Each image represents one time step.
3. Use the **Time Slider** panel at the bottom to scrub through the frames.

Temporal layers display `time_start`, `time_end`, and `time_steps` metadata so you can see the temporal extent of your data in the layer properties.

---

## Map Navigation

### Pan

- **Click and drag** with the Pan tool active (the default tool).
- **Middle-click and drag** works regardless of the active tool.

### Zoom

- **Scroll wheel** -- scroll up to zoom in, scroll down to zoom out.
- **Zoom In tool** -- click on the map to zoom in, or drag a rectangle to zoom to a region.
- **Zoom Out tool** -- click on the map to zoom out.

### Keyboard Shortcuts for Navigation

| Shortcut | Action |
|----------|--------|
| Arrow keys | Pan the map |
| `+` or `=` | Zoom in |
| `-` | Zoom out |
| `Home` | Zoom to full extent |

---

## Layer Management

The Layer Tree panel on the left side of the application shows all loaded layers.

### Add/Remove Layers

- **Add**: Open a file using **File > Open** (Ctrl+O). The layer appears at the top of the layer tree.
- **Remove**: Right-click a layer in the tree and select **Remove Layer**, or select the layer and press **Delete**.

### Visibility

Click the visibility checkbox next to a layer name to show or hide it on the map. Hidden layers are not rendered but remain in the project.

### Reorder

Drag layers up and down in the layer tree to change their draw order. Layers at the top of the list are drawn on top of layers below them.

### Styling

Right-click a layer and select **Properties** or **Style** to adjust visual appearance:

- **Opacity** -- Set from 0.0 (fully transparent) to 1.0 (fully opaque).
- **Colormap** -- For raster layers, choose from standard colormaps (viridis, gray, jet, etc.) or set a custom colormap.
- **Band Mapping** -- For multi-band rasters, assign which bands map to the red, green, and blue display channels.
- **Contrast Stretch** -- Controls how pixel values are mapped to display brightness. Options include `percentile` (default), `min-max`, and `standard-deviation`.
- **Fill Color** -- For vector polygon layers, set the interior fill color (supports alpha transparency, e.g., `#4682B480`).
- **Stroke Color** -- For vector layers, set the outline color.
- **Stroke Width** -- Set the outline width in pixels.

---

## Measurement Tools

### Distance

1. Select the **Measure Distance** tool from the toolbar.
2. Click on the map to place vertices along a polyline.
3. Each segment length and the running total are displayed as you add points.
4. Double-click to finish the measurement.

Distances are computed geodesically (accounting for Earth's curvature) using the CRS engine.

### Area

1. Select the **Measure Area** tool from the toolbar.
2. Click on the map to place vertices of a polygon.
3. Double-click to close the polygon and compute its geodesic area.

Results are displayed in appropriate units (meters, kilometers, square meters, square kilometers) based on the measurement size.

---

## Identify and Select

### Identify

1. Select the **Identify** tool from the toolbar.
2. Click on a feature or pixel on the map.
3. An information popup displays the attributes (for vector features) or pixel values (for raster layers) at the clicked location.

### Rectangle Selection

1. Select the **Select** tool from the toolbar.
2. Click and drag to draw a selection rectangle.
3. All vector features intersecting the rectangle are selected and highlighted on the map.
4. Selected features appear highlighted in the attribute table.

---

## Attribute Table

The attribute table displays the tabular data associated with the active vector layer.

### Opening the Table

Select a vector layer in the layer tree. The attribute table appears in the bottom panel, or go to **View > Attribute Table** to open it explicitly.

### Sorting

Click a column header to sort by that column. Click again to reverse the sort order.

### Filtering with Expressions

Use the filter bar at the top of the attribute table to enter an expression that filters the displayed rows. The expression syntax is a safe subset of SQL WHERE clauses (see "Expression Syntax" below).

### Exporting

Right-click the attribute table and select **Export** to save the table contents (or current filter results) to CSV or other formats.

---

## Expression Syntax

tkgis uses a safe expression parser for attribute queries. No `eval()` is ever called -- expressions are tokenized and converted to pandas boolean operations. The following operators and constructs are supported:

### Comparison Operators

| Operator | Meaning |
|----------|---------|
| `=` | Equal to |
| `!=` or `<>` | Not equal to |
| `<` | Less than |
| `>` | Greater than |
| `<=` | Less than or equal to |
| `>=` | Greater than or equal to |

### Logical Operators

| Operator | Meaning |
|----------|---------|
| `AND` | Both conditions must be true |
| `OR` | Either condition must be true |
| `NOT` | Negates a condition |

Parentheses can be used to group sub-expressions and control evaluation order.

### Pattern Matching

- `LIKE` -- SQL-style pattern matching. `%` matches any sequence of characters; `_` matches a single character. The match is anchored to the full string.

### Set Membership

- `IN` -- Tests whether a value is in a list of values.

### Null Checks

- `IS NULL` -- Tests whether a value is null/missing.
- `IS NOT NULL` -- Tests whether a value is not null.

### Column-to-Column Comparison

You can compare two columns directly:

```
elevation > base_height
```

### Examples

```
value > 100
```

```
name LIKE 'New%'
```

```
population > 10000 AND state = 'CA'
```

```
category IN ('urban', 'suburban')
```

```
notes IS NULL
```

```
NOT (status = 'inactive')
```

```
(temperature > 30 OR humidity > 80) AND region = 'southeast'
```

### Safety

The expression parser rejects any input containing potentially dangerous content such as `import`, `exec`, `eval`, `os.`, `sys.`, `subprocess`, `lambda`, `__`, and similar patterns. Only column names, literal values (strings, numbers, NULL), and the operators listed above are permitted.

---

## Processing

### Toolbox

The Toolbox panel provides a catalog of all available processing operations, discovered from grdl-runtime's processor registry. Processors are organized by category.

To run a processor:

1. Open the **Toolbox** panel.
2. Browse or search for a processor.
3. Double-click the processor to open its parameter dialog.
4. Configure the input parameters. Parameter types, ranges, and defaults are auto-generated from the processor's parameter specifications.
5. Click **Run**. The processor executes in a background thread, and progress is displayed in the status bar.

### Parameter Editing

Each processor defines a set of typed parameters with defaults, ranges, and descriptions. The parameter dialog automatically generates appropriate input widgets:

- Numeric parameters show spinboxes with min/max constraints.
- String parameters show text fields.
- Enum parameters show dropdown selectors.
- Boolean parameters show checkboxes.
- File path parameters show file browser buttons.

---

## Visual Workflow Builder

The workflow builder lets you compose multi-step processing pipelines by dragging nodes onto a canvas and connecting them with edges. Workflows are saved as YAML files compatible with grdl-runtime for headless or distributed execution.

### Opening the Builder

Go to **View > Workflow Builder** or click the workflow icon in the toolbar. The builder opens in a separate window with three panes:

- **Palette** (left) -- A catalog of available processing nodes, organized by category.
- **Canvas** (center) -- The visual graph editor where you build the workflow.
- **Inspector** (right) -- Parameter editor for the currently selected node.

### Adding Nodes

Drag a node type from the palette onto the canvas. The node snaps to a 20-pixel grid. Each node represents a processing step (a grdl-runtime processor) with typed input and output ports.

### Node Types and Colors

Nodes are color-coded by their output data type:

| Color | Data Type | Description |
|-------|-----------|-------------|
| Blue (`#89b4fa`) | Raster | Raster image data |
| Green (`#a6e3a1`) | Feature Set (Vector) | Vector feature data |
| Orange (`#fab387`) | Detection Set | Detection/classification results |
| Gray (`#9399b2`) | Any / I/O | Generic or I/O nodes |

### Connecting Nodes

1. Click on a node's **output port** (circle on the right edge).
2. Drag to another node's **input port** (circle on the left edge).
3. Release to create the connection. A smooth bezier curve is drawn between the ports.

Connections validate type compatibility at design time:

- Compatible types (e.g., raster-to-raster) create a solid colored edge.
- Incompatible types (e.g., raster-to-vector) are rejected, and the connection is not created.
- Self-loops and duplicate edges are also rejected.

To disconnect nodes, right-click the target node and select **Disconnect from [source name]**.

### Editing Parameters

1. Click a node on the canvas to select it (the border highlights in purple).
2. The Inspector panel on the right shows the node's parameters.
3. Edit parameter values directly. Changes are reflected on the node immediately.
4. Double-click a node to focus the inspector on it.

### Validation

Press **F5** or click **Validate** in the toolbar to check the workflow for errors. Validation checks:

- Missing or broken connections.
- Type mismatches between connected ports (e.g., a raster output connected to a node expecting vector input).

Nodes with errors are highlighted with a dashed red border on the canvas.

### Saving and Loading

- **Save**: Press **Ctrl+S** or click **Save** in the toolbar. Workflows are saved as YAML files compatible with grdl-runtime. The first save prompts for a file location; subsequent saves overwrite the same file.
- **Save As**: Use **File > Save As** to save to a new location.
- **Open**: Press **Ctrl+O** or click **Open** to load a previously saved YAML workflow.
- **New**: Press **Ctrl+N** or click **New** to start a fresh empty workflow.

### Executing Workflows

1. Press **F6** or click **Run** (the green button) in the toolbar.
2. The workflow is validated first. If there are errors, you are prompted to fix them.
3. If valid, the workflow is submitted to grdl-runtime's DAG executor for processing.
4. Progress is reported in the status bar.

Workflow execution requires grdl-runtime to be installed. Saved YAML workflows can also be executed outside tkgis using the grdl-runtime CLI or published to AuraGrid for distributed execution.

### Auto Layout

Click **Auto Layout** in the toolbar to arrange all nodes in a topological layout. Nodes are organized in columns by dependency level, centered vertically.

### Undo/Redo

The workflow builder maintains a full undo/redo history:

| Shortcut | Action |
|----------|--------|
| Ctrl+Z | Undo |
| Ctrl+Y | Redo |
| Delete | Delete selected node |

### Context Menu

Right-click on the canvas background for options like **Auto Layout**. Right-click on a node for options including **Delete Node** and **Disconnect** from upstream nodes.

---

## Charts

tkgis includes several chart types for data analysis, rendered using matplotlib:

### Spectral Profile

View the spectral response of a pixel across multiple bands in a multi-band raster. Click a pixel on the map with the spectral tool active to generate the chart.

### Histogram

Display the value distribution of a raster band or a vector attribute column. Useful for understanding data ranges and choosing classification thresholds.

### Scatter Plot

Plot two attributes or bands against each other. Useful for identifying correlations and clusters in your data.

### Time Series

Plot the value of a pixel or region over time using a temporal raster stack. Requires a temporal dataset to be loaded.

---

## Analysis Tools

### Change Detection

Compare two raster images (e.g., before and after images) to identify areas of change. The change detection module produces a difference layer highlighting significant changes.

### Zonal Statistics

Compute statistics (mean, min, max, sum, count, standard deviation) for raster values within vector polygon zones. For example, compute the average elevation within each county boundary.

### Interpolation

Generate a continuous raster surface from scattered point observations. Useful for creating surfaces from sample data (e.g., temperature, elevation, or concentration readings).

---

## Projects

### Saving a Project

Go to **File > Save Project** to save the current state of the application:

- All loaded layers and their styling
- The current map view (center, zoom level, CRS)
- Layer order and visibility settings

Projects are saved as JSON files.

### Loading a Project

Go to **File > Open Project** to restore a previously saved project. All layers, styles, and view settings are restored.

### Recent Files

The most recent files (up to 10) are listed under **File > Recent Files** for quick access. The recent files list persists across application sessions.

---

## Themes

tkgis supports three appearance modes:

- **Dark** (default) -- A dark color scheme that reduces eye strain during extended use.
- **Light** -- A standard light color scheme.
- **System** -- Follows the operating system's theme preference.

To change the theme, go to **Settings > Theme** or set it in the configuration file.

---

## Keyboard Shortcuts

### General

| Shortcut | Action |
|----------|--------|
| Ctrl+O | Open file |
| Ctrl+S | Save project |
| Ctrl+Z | Undo |
| Ctrl+Y | Redo |
| Delete | Delete selected item |
| F1 | Help |

### Map Navigation

| Shortcut | Action |
|----------|--------|
| Arrow keys | Pan map |
| `+` / `=` | Zoom in |
| `-` | Zoom out |
| Home | Zoom to full extent |
| Scroll wheel | Zoom in/out |

### Workflow Builder

| Shortcut | Action |
|----------|--------|
| Ctrl+N | New workflow |
| Ctrl+O | Open workflow |
| Ctrl+S | Save workflow |
| Ctrl+Z | Undo |
| Ctrl+Y | Redo |
| Delete | Delete selected node |
| F5 | Validate workflow |
| F6 | Execute workflow |

### Tools

| Shortcut | Action |
|----------|--------|
| P | Pan tool |
| Z | Zoom in tool |
| I | Identify tool |
| S | Select tool |
| M | Measure distance tool |

---

## Configuration

### Configuration Directory

tkgis stores its configuration and state files in `~/.tkgis/`:

```
~/.tkgis/
├── config.json         # Application settings
├── plugins.json        # Plugin enabled/disabled state
└── plugins/            # Directory-based plugins
    └── ...
```

### config.json Options

The configuration file is JSON with the following keys:

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `theme` | string | `"dark"` | Appearance mode: `"dark"`, `"light"`, or `"system"`. |
| `recent_files` | array of strings | `[]` | List of recently opened file paths (most recent first, max 10). |
| `window_geometry` | string | `"1600x900"` | Window size on launch (`WIDTHxHEIGHT`). |
| `default_crs` | string | `"EPSG:4326"` | Default coordinate reference system for new projects. |

You can edit `config.json` in any text editor while tkgis is not running. Changes take effect on the next launch.

### Plugin State

The `plugins.json` file tracks which plugins are enabled or disabled:

```json
{
  "vector-provider": true,
  "grdl-raster": true,
  "csv-points": false
}
```

Plugins default to enabled unless explicitly disabled. To disable a plugin, set its entry to `false` or use the plugin manager in the application.

### Adding Plugins

To install a directory-based plugin, create a subfolder under `~/.tkgis/plugins/` containing a `__plugin__.py` file. See the [Plugin Development Guide](plugin_development.md) for details.

To install a packaged plugin, use pip:

```
pip install tkgis-some-plugin
```

Packaged plugins register through the `tkgis.plugins` entry-point group and are discovered automatically.
