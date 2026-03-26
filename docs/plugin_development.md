# tkgis Plugin Development Guide

## Overview

tkgis has a plugin architecture that lets you extend the application without modifying its core code. Plugins can:

- **Add data providers** -- teach tkgis to open new file formats (e.g., custom sensor data, proprietary formats, web services).
- **Add panels** -- create dockable UI panels that appear alongside the layer tree, toolbox, and other built-in panels.
- **Add tools** -- register new map interaction tools (click, drag, draw) that users select from the toolbar.
- **Add menu items** -- inject entries into the application menu bar (File, Edit, or custom top-level menus).

All built-in functionality uses the same plugin API. The vector data provider (geopandas) and raster data provider (GRDL) are both plugins under `tkgis.plugins.builtin`.

---

## Plugin Structure

A minimal plugin is a single Python module that defines a `TkGISPlugin` subclass and a `get_plugin()` factory function. For anything beyond a trivial plugin, use a package layout:

```
my-tkgis-plugin/
├── pyproject.toml          # Package metadata and entry point
├── src/
│   └── my_plugin/
│       ├── __init__.py
│       ├── __plugin__.py   # Factory: get_plugin() -> TkGISPlugin
│       ├── plugin.py       # TkGISPlugin subclass
│       ├── provider.py     # DataProvider subclass (if applicable)
│       ├── panel.py        # BasePanel subclass (if applicable)
│       └── tool.py         # BaseTool subclass (if applicable)
└── tests/
    └── test_plugin.py
```

For directory-based plugins (no pip install), drop the package into `~/.tkgis/plugins/`:

```
~/.tkgis/plugins/
└── my_plugin/
    ├── __plugin__.py       # Must expose get_plugin()
    ├── plugin.py
    └── ...
```

---

## PluginManifest

Every plugin must declare a `PluginManifest` -- an immutable dataclass that describes the plugin to the plugin manager. The manifest is inspected *before* activation, so it must never perform expensive operations or import optional dependencies.

```python
from tkgis.plugins.manifest import PluginManifest

manifest = PluginManifest(
    name="csv-points",                    # Unique identifier (required)
    display_name="CSV Point Reader",      # Human-readable label (required)
    version="1.0.0",                      # Semantic version (required)
    description="Reads CSV files with lat/lon columns as point layers.",
    author="Jane Developer",
    license="MIT",                        # Must be MIT-compatible
    min_tkgis_version="0.1.0",            # Minimum tkgis version (default: "0.1.0")
    capabilities=["data-provider"],       # What this plugin provides (list of strings)
    dependencies=[],                      # Other plugin names this plugin depends on
)
```

### Field Reference

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | `str` | Yes | Unique plugin identifier. Use lowercase-with-dashes. Must not be empty. |
| `display_name` | `str` | Yes | Human-readable name shown in the plugin manager UI. |
| `version` | `str` | Yes | Semantic version string (e.g., `"1.2.3"`). Must not be empty. |
| `description` | `str` | Yes | One-line summary of what the plugin does. |
| `author` | `str` | Yes | Author or organization name. |
| `license` | `str` | Yes | License identifier (e.g., `"MIT"`, `"Apache-2.0"`). |
| `min_tkgis_version` | `str` | No | Minimum tkgis version required. Default: `"0.1.0"`. |
| `capabilities` | `list[str]` | No | Tags describing what the plugin provides: `"data-provider"`, `"panel"`, `"tool"`, `"menu"`. |
| `dependencies` | `list[str]` | No | Names of other plugins that must be activated first. The plugin manager resolves these automatically. |

Validation is performed in `__post_init__` -- `name` and `version` must not be empty or a `ValueError` is raised at construction time.

---

## TkGISPlugin ABC

All plugins subclass `TkGISPlugin` from `tkgis.plugins.base`. The abstract base class defines three requirements:

```python
from tkgis.plugins.base import TkGISPlugin, PluginContext
from tkgis.plugins.manifest import PluginManifest

class MyPlugin(TkGISPlugin):
    @property
    def manifest(self) -> PluginManifest:
        """Return the plugin's manifest (inspected before activation)."""
        return PluginManifest(
            name="my-plugin",
            display_name="My Plugin",
            version="0.1.0",
            description="Does something useful.",
            author="Me",
            license="MIT",
        )

    def activate(self, context: PluginContext) -> None:
        """Called when the plugin is enabled.

        Use context to register panels, tools, data providers, and menu items.
        """
        pass

    def deactivate(self) -> None:
        """Called when the plugin is disabled.

        Clean up any resources acquired during activation.
        """
        pass
```

### Lifecycle

1. **Discovery** -- The plugin manager discovers the plugin through one of three vectors (see "Discovery Vectors" below) by calling `get_plugin()`.
2. **Manifest inspection** -- The `manifest` property is read to display metadata and check dependencies.
3. **Activation** -- `activate(context)` is called with a `PluginContext` facade. The plugin registers its components here.
4. **Runtime** -- The plugin's registered components (providers, panels, tools, menu items) are live in the application.
5. **Deactivation** -- `deactivate()` is called when the user disables the plugin or the application shuts down. Clean up resources here.

Enabled/disabled state is persisted to `~/.tkgis/plugins.json` automatically.

### PluginContext API

The `PluginContext` object passed to `activate()` provides four registration methods:

| Method | Purpose |
|--------|---------|
| `register_data_provider(provider)` | Register a `DataProvider` with the application-wide `DataProviderRegistry`. |
| `register_panel(panel)` | Register a dockable `BasePanel` with the application. |
| `register_tool(tool)` | Register a map-interaction `BaseTool` with the tool manager. |
| `add_menu_item(menu_path, label, callback)` | Add an entry to the menu bar. `menu_path` is the top-level menu name (e.g., `"File"`, `"Tools"`). |

All registration methods are safe to call even if the corresponding subsystem is not yet initialized -- they will log a warning and silently succeed. This means plugins loaded early in the boot sequence will not crash the application.

---

## Creating a Data Provider

A data provider teaches tkgis how to open a specific file format. It subclasses `DataProvider` from `tkgis.plugins.providers`.

### Step 1: Subclass DataProvider

```python
from pathlib import Path
from tkgis.plugins.providers import DataProvider
from tkgis.models.layers import Layer, LayerType, LayerStyle

class CSVPointProvider(DataProvider):
    """Opens CSV files containing latitude/longitude columns as point layers."""

    @property
    def name(self) -> str:
        return "csv-points"

    @property
    def supported_extensions(self) -> list[str]:
        # Lowercase, no leading dot
        return ["csv", "tsv"]

    @property
    def supported_modalities(self) -> list[str]:
        return ["vector"]

    def can_open(self, path: Path) -> bool:
        """Return True if the file has a supported extension."""
        suffix = path.suffix.lower().lstrip(".")
        return suffix in self.supported_extensions

    def open(self, path: Path) -> Layer:
        """Open a CSV file and return a Layer with point geometry."""
        import pandas as pd
        import geopandas as gpd
        from shapely.geometry import Point

        df = pd.read_csv(path)

        # Detect lat/lon columns (case-insensitive)
        lat_col = next(
            (c for c in df.columns if c.lower() in ("lat", "latitude", "y")),
            None,
        )
        lon_col = next(
            (c for c in df.columns if c.lower() in ("lon", "lng", "longitude", "x")),
            None,
        )
        if lat_col is None or lon_col is None:
            raise ValueError(
                f"CSV must contain latitude and longitude columns; "
                f"found: {list(df.columns)}"
            )

        geometry = [Point(xy) for xy in zip(df[lon_col], df[lat_col])]
        gdf = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")

        from tkgis.io.vector import VectorLayerData
        from tkgis.models.crs import CRSDefinition
        from tkgis.models.geometry import BoundingBox

        vdata = VectorLayerData(gdf)

        layer = Layer(
            name=path.stem,
            layer_type=LayerType.VECTOR,
            source_path=str(path),
            crs=vdata.crs,
            bounds=vdata.bounds,
            style=LayerStyle(
                fill_color="#e74c3c80",
                stroke_color="#c0392b",
                stroke_width=1.5,
            ),
            metadata={
                "feature_count": len(gdf),
                "geometry_types": ["Point"],
                "columns": list(df.columns),
                "provider": self.name,
                "_vector_data": vdata,
            },
        )
        return layer

    def get_file_filter(self) -> str:
        return "CSV Point Files (*.csv *.tsv)"
```

### Step 2: Create the Plugin Class

```python
from tkgis.plugins.base import TkGISPlugin, PluginContext
from tkgis.plugins.manifest import PluginManifest

class CSVPointPlugin(TkGISPlugin):
    def __init__(self) -> None:
        self._provider: CSVPointProvider | None = None

    @property
    def manifest(self) -> PluginManifest:
        return PluginManifest(
            name="csv-points",
            display_name="CSV Point Reader",
            version="1.0.0",
            description="Opens CSV/TSV files with lat/lon columns as point layers.",
            author="Jane Developer",
            license="MIT",
            capabilities=["data-provider"],
        )

    def activate(self, context: PluginContext) -> None:
        self._provider = CSVPointProvider()
        context.register_data_provider(self._provider)

    def deactivate(self) -> None:
        self._provider = None
```

### Step 3: Add the Factory Function

Every discoverable plugin module must expose a `get_plugin()` function:

```python
def get_plugin() -> CSVPointPlugin:
    """Factory function for plugin discovery."""
    return CSVPointPlugin()
```

### DataProvider ABC Reference

| Member | Type | Description |
|--------|------|-------------|
| `name` | `property -> str` | Unique provider identifier. |
| `supported_extensions` | `property -> list[str]` | Lowercase file extensions without leading dot (e.g., `["shp", "geojson"]`). |
| `supported_modalities` | `property -> list[str]` | Data modalities: `"vector"`, `"raster"`, or both. |
| `can_open(path)` | `method -> bool` | Return `True` if this provider can handle the given path. |
| `open(path)` | `method -> Layer` | Open the file and return a `Layer` object. |
| `get_file_filter()` | `method -> str` | Return a file-dialog filter string (e.g., `"Shapefiles (*.shp)"`). |

The `DataProviderRegistry` routes file-open requests to the first registered provider whose `can_open()` returns `True`. Duplicates (by `name`) are silently ignored.

---

## Creating a Panel Plugin

Panels are dockable UI components that appear on the left, right, or bottom of the application window.

### Step 1: Subclass BasePanel

```python
import customtkinter as ctk
from tkgis.panels.base import BasePanel

class BookmarkPanel(BasePanel):
    """Panel for managing spatial bookmarks."""

    name = "bookmarks"
    title = "Bookmarks"
    dock_position = "right"         # "left", "right", or "bottom"
    default_visible = True

    def __init__(self) -> None:
        super().__init__()
        self._bookmarks: list[dict] = []

    def create_widget(self, parent) -> ctk.CTkFrame:
        """Build and return the panel's root frame."""
        frame = ctk.CTkFrame(parent, width=280)
        self._widget = frame

        ctk.CTkLabel(frame, text="Spatial Bookmarks", font=("", 14, "bold")).pack(
            pady=(10, 5), padx=10, anchor="w"
        )

        self._listbox = ctk.CTkTextbox(frame, height=200)
        self._listbox.pack(fill="both", expand=True, padx=10, pady=5)

        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkButton(btn_frame, text="Add Bookmark", command=self._add_bookmark).pack(
            side="left", padx=2
        )
        ctk.CTkButton(btn_frame, text="Go To", command=self._go_to).pack(
            side="left", padx=2
        )

        return frame

    def _add_bookmark(self) -> None:
        # Implementation here
        pass

    def _go_to(self) -> None:
        # Implementation here
        pass
```

### Step 2: Register in activate()

```python
class BookmarkPlugin(TkGISPlugin):
    def __init__(self) -> None:
        self._panel: BookmarkPanel | None = None

    @property
    def manifest(self) -> PluginManifest:
        return PluginManifest(
            name="bookmarks",
            display_name="Spatial Bookmarks",
            version="1.0.0",
            description="Save and recall spatial bookmarks on the map.",
            author="Jane Developer",
            license="MIT",
            capabilities=["panel"],
        )

    def activate(self, context: PluginContext) -> None:
        self._panel = BookmarkPanel()
        context.register_panel(self._panel)

    def deactivate(self) -> None:
        self._panel = None
```

### BasePanel ABC Reference

| Member | Type | Description |
|--------|------|-------------|
| `name` | `str` (class attr) | Unique panel identifier. |
| `title` | `str` (class attr) | Display title shown in the panel header. |
| `dock_position` | `str` (class attr) | Where the panel docks: `"left"`, `"right"`, or `"bottom"`. |
| `default_visible` | `bool` (class attr) | Whether the panel is visible by default. Default: `True`. |
| `create_widget(parent)` | `method -> CTkFrame` | Build the panel's widget tree and return the root frame. |
| `on_show()` | `method` | Called when the panel becomes visible. Override to refresh data. |
| `on_hide()` | `method` | Called when the panel is hidden. Override to pause updates. |
| `on_project_changed(project)` | `method` | Called when the active project changes. Override to reload state. |

---

## Creating a Tool Plugin

Tools are map-interaction modes that handle mouse and keyboard events on the map canvas.

### Step 1: Subclass BaseTool

```python
from tkgis.models.tools import BaseTool, ToolMode

class PinDropTool(BaseTool):
    """Click to drop a pin annotation on the map."""

    name = "pin_drop"
    mode = ToolMode.DRAW_POINT
    cursor = "crosshair"

    def __init__(self) -> None:
        self._pins: list[tuple[float, float]] = []

    def on_press(self, x: float, y: float, map_x: float, map_y: float) -> None:
        """Called when the mouse button is pressed.

        (x, y) are screen coordinates; (map_x, map_y) are map coordinates.
        """
        self._pins.append((map_x, map_y))

    def on_drag(self, x: float, y: float, map_x: float, map_y: float) -> None:
        """Called while the mouse is dragged (no-op for a click tool)."""
        pass

    def on_release(self, x: float, y: float, map_x: float, map_y: float) -> None:
        """Called when the mouse button is released."""
        pass

    def activate(self) -> None:
        """Called when this tool becomes the active tool."""
        self._pins.clear()

    def deactivate(self) -> None:
        """Called when this tool is replaced by another tool."""
        pass
```

### Step 2: Register in activate()

```python
class PinDropPlugin(TkGISPlugin):
    def __init__(self) -> None:
        self._tool: PinDropTool | None = None

    @property
    def manifest(self) -> PluginManifest:
        return PluginManifest(
            name="pin-drop",
            display_name="Pin Drop Tool",
            version="1.0.0",
            description="Click to drop pin annotations on the map.",
            author="Jane Developer",
            license="MIT",
            capabilities=["tool"],
        )

    def activate(self, context: PluginContext) -> None:
        self._tool = PinDropTool()
        context.register_tool(self._tool)

    def deactivate(self) -> None:
        self._tool = None
```

### BaseTool ABC Reference

| Member | Type | Description |
|--------|------|-------------|
| `name` | `str` (class attr) | Unique tool identifier, used with `ToolManager.set_active()`. |
| `mode` | `ToolMode` (class attr) | The tool mode enum value. |
| `cursor` | `str` (class attr) | Cursor name while this tool is active (default: `"arrow"`). |
| `on_press(x, y, map_x, map_y)` | `method` | Mouse button pressed. Required. |
| `on_drag(x, y, map_x, map_y)` | `method` | Mouse dragged. Required. |
| `on_release(x, y, map_x, map_y)` | `method` | Mouse button released. Required. |
| `on_move(x, y, map_x, map_y)` | `method` | Mouse moved (no button). Optional. |
| `on_scroll(x, y, delta)` | `method` | Mouse scroll. Optional. |
| `on_key(key)` | `method` | Key pressed. Optional. |
| `activate()` | `method` | Tool becomes active. Optional. |
| `deactivate()` | `method` | Tool replaced by another. Optional. |

All coordinate pairs include both screen coordinates `(x, y)` and map coordinates `(map_x, map_y)`.

---

## Discovery Vectors

tkgis finds plugins through three mechanisms, checked in order. The first plugin discovered for a given name wins; later duplicates are logged and skipped.

### 1. Built-in Plugins

Modules in the `tkgis.plugins.builtin` package are scanned automatically using `pkgutil.iter_modules()`. Each module must expose a `get_plugin()` factory function that returns a `TkGISPlugin` instance.

The built-in plugins included with tkgis are:

- `vector_provider.py` -- geopandas-backed vector I/O (Shapefile, GeoJSON, GeoPackage, KML, etc.)
- `raster_provider.py` -- GRDL-backed raster I/O (GeoTIFF, NITF, HDF5, JPEG2000)

### 2. Entry-Point Plugins (pip install)

Third-party packages can register plugins using Python's standard entry-point mechanism. Add an entry to your `pyproject.toml`:

```toml
[project.entry-points."tkgis.plugins"]
csv-points = "my_plugin:get_plugin"
```

Or the equivalent in `setup.cfg`:

```ini
[options.entry_points]
tkgis.plugins =
    csv-points = my_plugin:get_plugin
```

The entry point must reference a callable that returns a `TkGISPlugin` instance. tkgis scans the `"tkgis.plugins"` entry-point group using `importlib.metadata.entry_points()`.

This is the recommended distribution method for reusable plugins. Users install with `pip install my-tkgis-plugin` and the plugin appears automatically.

### 3. Directory Plugins

For local or experimental plugins, drop a folder into `~/.tkgis/plugins/`. Each folder must contain a `__plugin__.py` file with a `get_plugin()` function:

```
~/.tkgis/plugins/
├── my_local_plugin/
│   ├── __plugin__.py    # Must define get_plugin() -> TkGISPlugin
│   └── ...
└── another_plugin/
    ├── __plugin__.py
    └── ...
```

The plugin manager loads `__plugin__.py` using `importlib.util.spec_from_file_location()` and calls `get_plugin()`. This approach requires no packaging or installation -- just copy the folder.

### Discovery Order and Deduplication

1. Built-in plugins are discovered first.
2. Entry-point plugins are discovered second.
3. Directory plugins are discovered third.

If two plugins share the same `manifest.name`, the first one discovered wins and later duplicates are skipped with a log message. Failures in any individual discovery vector are logged but never crash the application.

---

## Testing Your Plugin

### Unit Testing a DataProvider

```python
import pytest
from pathlib import Path
from my_plugin.provider import CSVPointProvider

@pytest.fixture
def provider():
    return CSVPointProvider()

def test_name(provider):
    assert provider.name == "csv-points"

def test_supported_extensions(provider):
    assert "csv" in provider.supported_extensions
    assert "tsv" in provider.supported_extensions

def test_can_open_csv(provider, tmp_path):
    csv_file = tmp_path / "test.csv"
    csv_file.write_text("lat,lon,name\n40.7,-74.0,NYC\n")
    assert provider.can_open(csv_file) is True

def test_can_open_wrong_ext(provider, tmp_path):
    shp_file = tmp_path / "test.shp"
    shp_file.touch()
    assert provider.can_open(shp_file) is False

def test_open_csv(provider, tmp_path):
    csv_file = tmp_path / "cities.csv"
    csv_file.write_text("lat,lon,name\n40.7,-74.0,NYC\n34.0,-118.2,LA\n")
    layer = provider.open(csv_file)
    assert layer.name == "cities"
    assert layer.layer_type.value == "vector"
    assert layer.metadata["feature_count"] == 2

def test_file_filter(provider):
    f = provider.get_file_filter()
    assert "*.csv" in f
```

### Unit Testing the Plugin Lifecycle

```python
from my_plugin.plugin import CSVPointPlugin
from tkgis.plugins.base import PluginContext

def test_manifest():
    plugin = CSVPointPlugin()
    m = plugin.manifest
    assert m.name == "csv-points"
    assert m.version == "1.0.0"

def test_activate_deactivate():
    plugin = CSVPointPlugin()
    ctx = PluginContext()
    plugin.activate(ctx)
    assert plugin._provider is not None
    plugin.deactivate()
    assert plugin._provider is None
```

### Integration Testing with PluginManager

```python
from tkgis.plugins.manager import PluginManager
from tkgis.plugins.base import PluginContext

def test_plugin_activation():
    ctx = PluginContext()
    manager = PluginManager(context=ctx)
    # Manually register for testing (bypasses discovery)
    from my_plugin.plugin import CSVPointPlugin
    plugin = CSVPointPlugin()
    manager._plugins[plugin.manifest.name] = plugin
    manager.activate("csv-points")
    assert manager.is_enabled("csv-points")
    manager.deactivate("csv-points")
    assert not manager.is_enabled("csv-points")
```

### Running Tests

```
pytest tests/ -x -q
```

---

## Best Practices

### Error Handling

- **Never let exceptions escape `activate()` or `deactivate()`.** The plugin manager catches exceptions, but a noisy plugin degrades the user experience. Wrap risky operations in try/except and log errors.
- **Guard optional imports.** If your plugin depends on a library that may not be installed, use a try/except guard at module level:

  ```python
  try:
      import some_library
      _HAS_LIB = True
  except ImportError:
      _HAS_LIB = False
  ```

  Then check `_HAS_LIB` in `can_open()` or `activate()` and fail gracefully.

- **Validate input in `open()`.** File content can be malformed. Raise `ValueError` with a clear message rather than letting a `KeyError` or `IndexError` propagate.

### Dependency Management

- Declare Python package dependencies in your `pyproject.toml` `[project.dependencies]`, not in the `PluginManifest.dependencies` field.
- Use `PluginManifest.dependencies` only for inter-plugin dependencies (e.g., your plugin depends on another tkgis plugin being active).
- Pin your minimum version of tkgis in `min_tkgis_version` if you rely on APIs introduced after 0.1.0.

### Resource Cleanup

- Release file handles, threads, and network connections in `deactivate()`.
- Set provider/panel/tool references to `None` in `deactivate()` to help garbage collection.
- If your panel creates background threads, use `on_hide()` to pause them and `on_show()` to resume.

### Naming Conventions

- Use lowercase-with-dashes for `manifest.name`: `"csv-points"`, not `"CSVPoints"`.
- Use the `tkgis_` prefix for your Python package name to make it discoverable: `tkgis_csv_points`.
- Match your provider's `name` property to the manifest `name` when it makes sense.

### Licensing

- tkgis is MIT-licensed. Plugins should use MIT or a compatible license.
- Declare your license in both the manifest and `pyproject.toml`.
- If your plugin wraps a GPL library, the plugin itself inherits GPL. Note this in the manifest.

### Performance

- Keep `can_open()` fast. Only check the file extension, not the file content. Content validation belongs in `open()`.
- Use lazy imports in `open()` for heavy libraries (numpy, geopandas, etc.) to keep plugin discovery fast.
- For large files, consider returning a `Layer` with a tile provider attached (see `raster_provider.py` for the pattern) rather than loading everything into memory.
