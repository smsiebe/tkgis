"""VoxelVault data provider plugin for tkgis.

Enables loading raster cubes from a VoxelVault database with a query interface
for selecting cubes, time ranges, and variables.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TYPE_CHECKING

import numpy as np
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox

from voxelvault import Vault
from tkgis.plugins.providers import DataProvider
from tkgis.plugins.base import TkGISPlugin, PluginContext
from tkgis.plugins.manifest import PluginManifest
from tkgis.models.layers import Layer, LayerType, LayerStyle
from tkgis.canvas.tiles import TileProvider, TileKey
from tkgis.io.raster_display import RasterDisplayEngine
from tkgis.models.geometry import BoundingBox
from tkgis.models.crs import CRSDefinition
from tkgis.models.events import EventType

if TYPE_CHECKING:
    from tkgis.models.events import EventBus

logger = logging.getLogger(__name__)


class VoxelVaultTileProvider(TileProvider):
    """Serve tiles from a VoxelVault cube by querying on demand."""

    def __init__(
        self,
        vault: Vault,
        cube_name: str,
        layer: Layer,
        temporal_range: tuple[datetime, datetime] | None = None,
        variables: list[str] | None = None,
        event_bus: EventBus | None = None,
    ) -> None:
        self._vault = vault
        self._cube_name = cube_name
        self._layer = layer
        self._temporal_range = temporal_range
        self._variables = variables
        self._event_bus = event_bus
        self._cube = vault.get_cube(cube_name)
        
        if self._cube is None:
            raise ValueError(f"Cube {cube_name} not found in vault")

        # Map current time from event bus
        self._current_time: datetime | None = None
        if self._event_bus:
            self._event_bus.subscribe(EventType.TIME_STEP_CHANGED, self._on_time_changed)

        # Build pyramid info based on cube grid
        self._pyramid: list[tuple[int, int, int, int]] = []
        self._build_pyramid_info()

    def _build_pyramid_info(self) -> None:
        """Treat the cube grid as a large image pyramid."""
        grid = self._cube.grid
        rows = grid.height
        cols = grid.width
        tile_size = 256
        max_dim = max(rows, cols)
        
        if max_dim <= 0:
            self._pyramid = [(1, 1, rows, cols)]
            return

        num_levels = max(1, int(np.ceil(np.log2(max_dim / tile_size))) + 1)
        self._pyramid = []
        for level in range(num_levels):
            scale = 2 ** (num_levels - 1 - level)
            pixels_per_tile = tile_size * scale
            grid_rows = max(1, int(np.ceil(rows / pixels_per_tile)))
            grid_cols = max(1, int(np.ceil(cols / pixels_per_tile)))
            self._pyramid.append((grid_rows, grid_cols, rows, cols))

    def _on_time_changed(self, time: datetime, **kwargs: Any) -> None:
        """Update current time and trigger refresh if needed."""
        self._current_time = time
        # We don't refresh the canvas here directly; the MapCanvas should 
        # listen to TIME_STEP_CHANGED and refresh all layers.

    def get_tile(
        self,
        layer: Layer,
        zoom_level: int,
        row: int,
        col: int,
        tile_size: int = 256,
    ) -> np.ndarray | None:
        """Query the vault for a specific spatial/temporal window."""
        if zoom_level < 0 or zoom_level >= len(self._pyramid):
            return None

        grid_rows, grid_cols, img_rows, img_cols = self._pyramid[zoom_level]
        if row < 0 or row >= grid_rows or col < 0 or col >= grid_cols:
            return None

        num_levels = len(self._pyramid)
        scale = 2 ** (num_levels - 1 - zoom_level)
        pixels_per_tile = tile_size * scale

        # Pixel indices in cube space
        r_start = row * pixels_per_tile
        r_end = min(r_start + pixels_per_tile, img_rows)
        c_start = col * pixels_per_tile
        c_end = min(c_start + pixels_per_tile, img_cols)

        # Convert to spatial bounds using cube transform
        # transform: (x_res, x_skew, x_origin, y_skew, y_res, y_origin)
        gt = self._cube.grid.transform
        def to_map(r, c):
            mx = gt[2] + c * gt[0] + r * gt[1]
            my = gt[5] + c * gt[3] + r * gt[4]
            return mx, my

        # Cube grid is (rows, cols). 
        # west = min(mx), east = max(mx), south = min(my), north = max(my)
        pts = [to_map(r_start, c_start), to_map(r_start, c_end), 
               to_map(r_end, c_start), to_map(r_end, c_end)]
        west = min(p[0] for p in pts)
        east = max(p[0] for p in pts)
        south = min(p[1] for p in pts)
        north = max(p[1] for p in pts)
        bounds = (west, south, east, north)

        # Determine temporal range for query
        t_range = self._temporal_range
        if self._current_time:
            # If we have a global time, query exactly that or nearest
            # For simplicity, we use a small window around current time
            t_range = (self._current_time, self._current_time)

        try:
            # Note: query_cube might return multiple time slices. 
            # We want one for the tile.
            # If multiple match, we take the first one or the one matching current_time.
            if t_range and t_range[0] == t_range[1]:
                res = self._vault.query_single(
                    self._cube_name,
                    spatial_bounds=bounds,
                    temporal_range=t_range,
                    variables=self._variables
                )
                data = res.data
            else:
                res = self._vault.query(
                    self._cube_name,
                    spatial_bounds=bounds,
                    temporal_range=t_range,
                    variables=self._variables
                )
                # If multiple time slices, take the first one for this tile
                data = res.data[0] if res.data.ndim == 4 else res.data

            # Display transform
            rgba = RasterDisplayEngine.to_display_rgb(data, layer.style)
            
            # Ensure exact tile size
            h, w = rgba.shape[:2]
            if h != tile_size or w != tile_size:
                out = np.zeros((tile_size, tile_size, 4), dtype=np.uint8)
                out[:h, :w, :] = rgba
                rgba = out
                
            return rgba

        except Exception as exc:
            # No data matches is common for tiles at edges or if time doesn't match
            logger.debug("VoxelVault get_tile failed: %s", exc)
            return None

    def get_num_zoom_levels(self, layer: Layer) -> int:
        return len(self._pyramid)

    def get_tile_grid(self, layer: Layer, zoom_level: int) -> tuple[int, int]:
        if 0 <= zoom_level < len(self._pyramid):
            return self._pyramid[zoom_level][0], self._pyramid[zoom_level][1]
        return 0, 0


class VoxelVaultQueryDialog(ctk.CTkToplevel):
    """Dialog to select cube and parameters from a VoxelVault."""

    def __init__(self, parent: Any, vault: Vault) -> None:
        super().__init__(parent)
        self._vault = vault
        self.result: dict[str, Any] | None = None

        self.title("Load from VoxelVault")
        self.geometry("500x600")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self._setup_ui()
        self._on_cube_selected(self._cube_var.get())

    def _setup_ui(self) -> None:
        # Cube selection
        ctk.CTkLabel(self, text="Select Cube:", font=("", 12, "bold")).pack(pady=(10, 0), padx=20, anchor="w")
        cubes = self._vault.list_cubes()
        self._cube_var = tk.StringVar(value=cubes[0] if cubes else "")
        self._cube_menu = ctk.CTkOptionMenu(self, values=cubes, variable=self._cube_var, command=self._on_cube_selected)
        self._cube_menu.pack(fill="x", padx=20, pady=5)

        # Variables selection
        ctk.CTkLabel(self, text="Select Variables:", font=("", 12, "bold")).pack(pady=(10, 0), padx=20, anchor="w")
        self._vars_frame = ctk.CTkScrollableFrame(self, height=150)
        self._vars_frame.pack(fill="x", padx=20, pady=5)
        self._var_checkboxes: dict[str, ctk.CTkCheckBox] = {}

        # Time range selection
        ctk.CTkLabel(self, text="Time Range:", font=("", 12, "bold")).pack(pady=(10, 0), padx=20, anchor="w")
        time_frame = ctk.CTkFrame(self)
        time_frame.pack(fill="x", padx=20, pady=5)
        
        self._all_time_var = tk.BooleanVar(value=True)
        ctk.CTkCheckBox(time_frame, text="All available time steps", variable=self._all_time_var, command=self._toggle_time_manual).pack(pady=5, padx=5, anchor="w")
        
        self._time_manual_frame = ctk.CTkFrame(time_frame, fg_color="transparent")
        self._time_manual_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(self._time_manual_frame, text="Start:").grid(row=0, column=0, padx=5, pady=2)
        self._start_var = tk.StringVar()
        self._start_entry = ctk.CTkEntry(self._time_manual_frame, textvariable=self._start_var)
        self._start_entry.grid(row=0, column=1, padx=5, pady=2, sticky="ew")
        
        ctk.CTkLabel(self._time_manual_frame, text="End:").grid(row=1, column=0, padx=5, pady=2)
        self._end_var = tk.StringVar()
        self._end_entry = ctk.CTkEntry(self._time_manual_frame, textvariable=self._end_var)
        self._end_entry.grid(row=1, column=1, padx=5, pady=2, sticky="ew")
        
        self._time_manual_frame.grid_columnconfigure(1, weight=1)
        self._toggle_time_manual()

        # Band mapping (Color guns)
        ctk.CTkLabel(self, text="RGB Band Mapping (Optional):", font=("", 12, "bold")).pack(pady=(10, 0), padx=20, anchor="w")
        mapping_frame = ctk.CTkFrame(self)
        mapping_frame.pack(fill="x", padx=20, pady=5)
        
        self._r_var = tk.StringVar(value="1")
        self._g_var = tk.StringVar(value="2")
        self._b_var = tk.StringVar(value="3")
        
        ctk.CTkLabel(mapping_frame, text="R:").grid(row=0, column=0, padx=5, pady=2)
        self._r_menu = ctk.CTkOptionMenu(mapping_frame, values=["1"], variable=self._r_var, width=80)
        self._r_menu.grid(row=0, column=1, padx=5, pady=2)
        
        ctk.CTkLabel(mapping_frame, text="G:").grid(row=0, column=2, padx=5, pady=2)
        self._g_menu = ctk.CTkOptionMenu(mapping_frame, values=["1"], variable=self._g_var, width=80)
        self._g_menu.grid(row=0, column=3, padx=5, pady=2)
        
        ctk.CTkLabel(mapping_frame, text="B:").grid(row=0, column=4, padx=5, pady=2)
        self._b_menu = ctk.CTkOptionMenu(mapping_frame, values=["1"], variable=self._b_var, width=80)
        self._b_menu.grid(row=0, column=5, padx=5, pady=2)

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=20, side="bottom")
        
        ctk.CTkButton(btn_frame, text="Cancel", width=100, command=self._on_cancel).pack(side="right", padx=5)
        ctk.CTkButton(btn_frame, text="Load", width=100, command=self._on_ok).pack(side="right", padx=5)

    def _on_cube_selected(self, cube_name: str) -> None:
        if not cube_name:
            return
        cube = self._vault.get_cube(cube_name)
        if not cube:
            return

        # Refresh variables
        for cb in self._var_checkboxes.values():
            cb.destroy()
        self._var_checkboxes.clear()
        
        for var in cube.variables:
            cb = ctk.CTkCheckBox(self._vars_frame, text=f"{var.name} ({var.unit})")
            cb.select()
            cb.pack(pady=2, padx=5, anchor="w")
            self._var_checkboxes[var.name] = cb

        # Update band mapping menus
        indices = [str(b.band_index) for b in cube.bands]
        self._r_menu.configure(values=indices)
        self._g_menu.configure(values=indices)
        self._b_menu.configure(values=indices)
        if len(indices) >= 3:
            self._r_var.set("1")
            self._g_var.set("2")
            self._b_var.set("3")
        else:
            self._r_var.set("1")
            self._g_var.set("1")
            self._b_var.set("1")

        # Set default time range
        records = self._vault._schema.query_files(cube_name=cube_name)
        if records:
            starts = [r.temporal_extent.start for r in records]
            ends = [r.temporal_extent.end for r in records]
            self._start_var.set(min(starts).isoformat())
            self._end_var.set(max(ends).isoformat())

    def _toggle_time_manual(self) -> None:
        state = "disabled" if self._all_time_var.get() else "normal"
        self._start_entry.configure(state=state)
        self._end_entry.configure(state=state)

    def _on_cancel(self) -> None:
        self.destroy()

    def _on_ok(self) -> None:
        cube_name = self._cube_var.get()
        selected_vars = [name for name, cb in self._var_checkboxes.items() if cb.get()]
        
        if not selected_vars:
            messagebox.showwarning("Selection Required", "Please select at least one variable.")
            return

        t_range = None
        if not self._all_time_var.get():
            try:
                start = datetime.fromisoformat(self._start_var.get())
                end = datetime.fromisoformat(self._end_var.get())
                if start.tzinfo is None:
                    start = start.replace(tzinfo=timezone.utc)
                if end.tzinfo is None:
                    end = end.replace(tzinfo=timezone.utc)
                t_range = (start, end)
            except ValueError:
                messagebox.showerror("Invalid Date", "Please enter valid ISO 8601 dates.")
                return

        self.result = {
            "cube_name": cube_name,
            "variables": selected_vars,
            "temporal_range": t_range,
            "band_mapping": [int(self._r_var.get()), int(self._g_var.get()), int(self._b_var.get())]
        }
        self.destroy()


class VoxelVaultDataProvider(DataProvider):
    """DataProvider for VoxelVault directories."""

    @property
    def name(self) -> str:
        return "voxelvault"

    @property
    def supported_extensions(self) -> list[str]:
        return []  # Directory based

    @property
    def supported_modalities(self) -> list[str]:
        return ["raster"]

    def can_open(self, path: Path) -> bool:
        """Check if *path* is a VoxelVault directory."""
        if not path.is_dir():
            # Also allow selecting v2.db directly
            if path.name == "v2.db" and (path.parent / "vault.json").exists():
                return True
            return False
        return (path / "v2.db").exists() and (path / "vault.json").exists()

    def open(self, path: Path) -> Layer | None:
        """Open the vault and show query dialog."""
        vault_path = path if path.is_dir() else path.parent
        vault = Vault.open(vault_path)
        
        # We need access to the root window for the dialog
        # In tkgis, we can find it via the global registry or pass it in.
        # Here we'll try to find any active window.
        root = tk._default_root
        
        dialog = VoxelVaultQueryDialog(root, vault)
        root.wait_window(dialog)
        
        if dialog.result is None:
            vault.close()
            return None

        res = dialog.result
        cube = vault.get_cube(res["cube_name"])
        
        # Build tkgis Layer
        layer = Layer(
            name=f"{res['cube_name']} ({vault_path.name})",
            layer_type=LayerType.TEMPORAL_RASTER,
            source_path=str(vault_path),
            crs=CRSDefinition.from_epsg(cube.grid.epsg),
            bounds=BoundingBox(
                xmin=cube.grid.bounds.west,
                ymin=cube.grid.bounds.south,
                xmax=cube.grid.bounds.east,
                ymax=cube.grid.bounds.north,
                crs=f"EPSG:{cube.grid.epsg}"
            ),
            style=LayerStyle(),
            metadata={
                "cube_name": res["cube_name"],
                "variables": res["variables"],
                "vault_path": str(vault_path),
                "_vault": vault
            }
        )

        # Populate time steps for TimeSliderPanel
        records = vault._schema.query_files(cube_name=res["cube_name"])
        # Filter by temporal range if specified
        if res["temporal_range"]:
            start, end = res["temporal_range"]
            records = [r for r in records if r.temporal_extent.start >= start and r.temporal_extent.end <= end]
        
        time_steps = sorted([r.temporal_extent.start.isoformat() for r in records])
        layer.time_steps = time_steps
        if time_steps:
            layer.time_start = time_steps[0]
            layer.time_end = time_steps[-1]

        # Attach tile provider
        # We need the event_bus from the app. 
        # Since DataProvider doesn't have it, we'll try to find it later or use a proxy.
        # For now, let's assume we can get it from the root if we're lucky, 
        # but better to attach it in the plugin activation.
        
        # The TileProvider will be wired up by the app after it receives the layer.
        # But RasterTileProvider is usually created here.
        
        # We'll use a placeholder for event_bus and let the plugin wire it.
        provider = VoxelVaultTileProvider(
            vault, res["cube_name"], layer, 
            temporal_range=res["temporal_range"],
            variables=res["variables"]
        )
        layer.metadata["_tile_provider"] = provider
        
        return layer

    def get_file_filter(self) -> str:
        return "VoxelVault Database (v2.db)"


class VoxelVaultPlugin(TkGISPlugin):
    """Plugin registering the VoxelVault data provider."""

    def __init__(self) -> None:
        self._provider: VoxelVaultDataProvider | None = None
        self._context: PluginContext | None = None

    @property
    def manifest(self) -> PluginManifest:
        return PluginManifest(
            name="voxelvault",
            display_name="VoxelVault Integration",
            version="0.1.0",
            description="Integration with VoxelVault spatiotemporal raster engine.",
            author="tkgis",
            license="MIT",
            capabilities=["data_provider"],
            dependencies=["voxelvault"],
        )

    def activate(self, context: PluginContext) -> None:
        self._context = context
        self._provider = VoxelVaultDataProvider()
        context.register_data_provider(self._provider)
        
        # Add "Save to VoxelVault" to Layer menu
        context.add_menu_item("Layer", "Export to VoxelVault...", self._on_export_to_vault)
        logger.info("VoxelVault plugin activated")

    def deactivate(self) -> None:
        self._provider = None
        logger.info("VoxelVault plugin deactivated")

    def _on_export_to_vault(self) -> None:
        """Export active layer to a VoxelVault (Ingest)."""
        if not self._context or not self._context.project:
            return
            
        project = self._context.project
        layer_id = project.selected_layer_id
        if not layer_id:
            messagebox.showwarning("Export to VoxelVault", "Please select a layer in the layer tree first.")
            return
            
        layer = project.get_layer(layer_id)
        if not layer:
            return
            
        if layer.layer_type not in (LayerType.RASTER, LayerType.TEMPORAL_RASTER):
            messagebox.showwarning("Export to VoxelVault", "Only raster layers can be exported to VoxelVault.")
            return
            
        # Select target vault directory
        vault_path_str = filedialog.askdirectory(title="Select VoxelVault Directory")
        if not vault_path_str:
            return
        vault_path = Path(vault_path_str)
        
        try:
            if (vault_path / "v2.db").exists():
                vault = Vault.open(vault_path)
            else:
                if messagebox.askyesno("Create Vault", f"No vault found at {vault_path}. Create a new one?"):
                    vault = Vault.create(vault_path)
                else:
                    return
        except Exception as exc:
            messagebox.showerror("Vault Error", f"Failed to open/create vault: {exc}")
            return

        # Dialog to select target cube and temporal extent
        dialog = VoxelVaultIngestDialog(tk._default_root, vault, layer)
        tk._default_root.wait_window(dialog)
        
        if dialog.result:
            res = dialog.result
            try:
                if layer.source_path and Path(layer.source_path).exists():
                    # Ingest using file path if available
                    vault.ingest_file(
                        res["cube_name"],
                        layer.source_path,
                        res["temporal_extent"]
                    )
                else:
                    # Try to get data from reader or tile provider
                    # For now, we only support source_path ingestion
                    messagebox.showerror("Ingest Error", "Only layers with a valid source file path can be ingested currently.")
                    vault.close()
                    return
                
                messagebox.showinfo("Export Successful", f"Layer {layer.name} ingested into cube {res['cube_name']}.")
            except Exception as exc:
                messagebox.showerror("Ingest Error", f"Failed to ingest: {exc}")
            finally:
                vault.close()
        else:
            vault.close()


class VoxelVaultIngestDialog(ctk.CTkToplevel):
    """Dialog to select target cube and metadata for ingestion."""

    def __init__(self, parent: Any, vault: Vault, layer: Layer) -> None:
        super().__init__(parent)
        self._vault = vault
        self._layer = layer
        self.result: dict[str, Any] | None = None

        self.title("Export to VoxelVault")
        self.geometry("450x400")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self._setup_ui()

    def _setup_ui(self) -> None:
        # Cube selection
        ctk.CTkLabel(self, text="Target Cube:", font=("", 12, "bold")).pack(pady=(10, 0), padx=20, anchor="w")
        cubes = self._vault.list_cubes()
        self._cube_var = tk.StringVar(value=cubes[0] if cubes else "")
        self._cube_menu = ctk.CTkOptionMenu(self, values=cubes, variable=self._cube_var)
        self._cube_menu.pack(fill="x", padx=20, pady=5)
        
        # New cube option
        ctk.CTkButton(self, text="Create New Cube...", command=self._on_new_cube, height=24).pack(padx=20, pady=2, anchor="e")

        # Temporal extent
        ctk.CTkLabel(self, text="Temporal Extent:", font=("", 12, "bold")).pack(pady=(10, 0), padx=20, anchor="w")
        time_frame = ctk.CTkFrame(self)
        time_frame.pack(fill="x", padx=20, pady=5)
        
        # Try to guess time from layer metadata
        t_start = self._layer.time_start or datetime.now(timezone.utc).isoformat()
        t_end = self._layer.time_end or t_start
        
        ctk.CTkLabel(time_frame, text="Start (ISO):").grid(row=0, column=0, padx=5, pady=5)
        self._start_var = tk.StringVar(value=t_start)
        ctk.CTkEntry(time_frame, textvariable=self._start_var).grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        
        ctk.CTkLabel(time_frame, text="End (ISO):").grid(row=1, column=0, padx=5, pady=5)
        self._end_var = tk.StringVar(value=t_end)
        ctk.CTkEntry(time_frame, textvariable=self._end_var).grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        time_frame.grid_columnconfigure(1, weight=1)

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=20, side="bottom")
        
        ctk.CTkButton(btn_frame, text="Cancel", width=100, command=self.destroy).pack(side="right", padx=5)
        ctk.CTkButton(btn_frame, text="Ingest", width=100, command=self._on_ok).pack(side="right", padx=5)

    def _on_new_cube(self) -> None:
        messagebox.showinfo("New Cube", "Feature coming soon: Automated cube descriptor generation from layer metadata.")

    def _on_ok(self) -> None:
        from voxelvault.models import TemporalExtent
        try:
            start = datetime.fromisoformat(self._start_var.get())
            end = datetime.fromisoformat(self._end_var.get())
            if start.tzinfo is None:
                start = start.replace(tzinfo=timezone.utc)
            if end.tzinfo is None:
                end = end.replace(tzinfo=timezone.utc)
            
            extent = TemporalExtent(start=start, end=end)
        except ValueError as exc:
            messagebox.showerror("Invalid Date", f"Invalid date format: {exc}")
            return

        self.result = {
            "cube_name": self._cube_var.get(),
            "temporal_extent": extent
        }
        self.destroy()


def get_plugin() -> VoxelVaultPlugin:
    return VoxelVaultPlugin()
