"""MapCanvas — tile-based map display widget for tkgis."""
from __future__ import annotations

import logging
import math
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import tkinter as tk

import numpy as np

try:
    from PIL import Image, ImageTk
except ImportError:  # allow import without Pillow for headless testing
    Image = None  # type: ignore[assignment,misc]
    ImageTk = None  # type: ignore[assignment,misc]

from tkgis.canvas.tiles import TileCache, TileKey, TileProvider
from tkgis.canvas.transform import ViewTransform
from tkgis.models.events import EventBus, EventType
from tkgis.models.layers import Layer
from tkgis.models.tools import ToolManager

logger = logging.getLogger(__name__)

_ZOOM_FACTOR = 1.2
_TILE_SIZE = 256


class MapCanvas(tk.Canvas):
    """Central map rendering widget.

    Renders tiles supplied by registered :class:`TileProvider` instances and
    delegates mouse interaction to the active tool in a :class:`ToolManager`.
    """

    def __init__(
        self,
        parent: tk.Widget,
        event_bus: EventBus,
        tool_manager: ToolManager,
        *,
        tile_cache_size: int = 256,
        **kwargs: Any,
    ) -> None:
        kwargs.setdefault("bg", "#1a1a2e")
        kwargs.setdefault("highlightthickness", 0)
        super().__init__(parent, **kwargs)

        self._event_bus = event_bus
        self._tool_manager = tool_manager

        self._layers: list[Layer] = []
        self._providers: dict[str, TileProvider] = {}
        self._tile_cache = TileCache(max_tiles=tile_cache_size)
        self._view = ViewTransform()

        # Keep references to PhotoImages so they are not garbage-collected
        self._photo_refs: dict[str, Any] = {}

        # Background tile loading
        self._executor = ThreadPoolExecutor(max_workers=2)
        self._pending_tiles: set[TileKey] = set()
        self._pending_lock = threading.Lock()

        # Drag state
        self._drag_start_x: int | None = None
        self._drag_start_y: int | None = None

        self._event_bus.subscribe(EventType.TIME_STEP_CHANGED, self._on_time_changed)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def _on_time_changed(self, **kwargs: Any) -> None:
        """Trigger refresh when the global time step changes."""
        self.refresh()

    def set_layers(self, layers: list[Layer]) -> None:
        """Replace the current layer stack and refresh."""
        self._layers = list(layers)
        self.refresh()

    def register_tile_provider(self, layer_id: str, provider: TileProvider) -> None:
        """Associate a :class:`TileProvider` with a layer id."""
        self._providers[layer_id] = provider

    def refresh(self) -> None:
        """Clear and redraw all visible tiles."""
        self._photo_refs.clear()
        self.delete("all")
        self._render_tiles()
        self._emit_view_changed()

    @property
    def view(self) -> ViewTransform:
        """Access the current view transform."""
        return self._view

    # ------------------------------------------------------------------
    # Tile rendering
    # ------------------------------------------------------------------

    def _render_tiles(self) -> None:
        """Determine visible tiles for each layer and draw them."""
        extent = self._view.get_visible_extent()

        for layer in self._layers:
            if not layer.style.visible:
                continue
            provider = self._providers.get(layer.id)
            if provider is None:
                continue

            num_zoom = provider.get_num_zoom_levels(layer)
            if num_zoom <= 0:
                continue

            # Pick best zoom level based on scale
            zoom_level = self._pick_zoom_level(provider, layer, num_zoom)
            num_rows, num_cols = provider.get_tile_grid(layer, zoom_level)
            if num_rows <= 0 or num_cols <= 0:
                continue

            # Layer-space extent
            if layer.bounds is None:
                continue
            lbounds = layer.bounds

            tile_w_map = lbounds.width / num_cols
            tile_h_map = lbounds.height / num_rows

            if tile_w_map <= 0 or tile_h_map <= 0:
                continue

            # Determine tile range that intersects the visible extent
            col_min = max(0, int((extent.xmin - lbounds.xmin) / tile_w_map))
            col_max = min(num_cols - 1, int((extent.xmax - lbounds.xmin) / tile_w_map))
            row_min = max(0, int((lbounds.ymax - extent.ymax) / tile_h_map))
            row_max = min(num_rows - 1, int((lbounds.ymax - extent.ymin) / tile_h_map))

            for row in range(row_min, row_max + 1):
                for col in range(col_min, col_max + 1):
                    key = TileKey(layer.id, zoom_level, row, col)
                    cached = self._tile_cache.get(key)
                    if cached is not None:
                        self._place_tile(cached, layer, lbounds, row, col, tile_w_map, tile_h_map)
                    else:
                        self._load_tile_async(key, layer, lbounds, row, col, tile_w_map, tile_h_map)

    def _pick_zoom_level(self, provider: TileProvider, layer: Layer, num_zoom: int) -> int:
        """Select zoom level closest to the current view scale."""
        if layer.bounds is None or num_zoom <= 1:
            return 0
        # At zoom 0 the whole layer fits; each subsequent level doubles resolution.
        native_scale = layer.bounds.width / self._view.canvas_width
        if native_scale <= 0:
            return 0
        ideal = math.log2(native_scale / self._view.scale) if self._view.scale > 0 else 0
        return max(0, min(num_zoom - 1, int(round(ideal))))

    def _place_tile(
        self,
        key: TileKey,
        photo: Any,
        layer: Layer,
        lbounds: Any,
        row: int,
        col: int,
        tile_w_map: float,
        tile_h_map: float,
    ) -> None:
        """Draw a PhotoImage tile at the correct screen position."""
        # Top-left corner of this tile in map space
        mx = lbounds.xmin + col * tile_w_map
        my = lbounds.ymax - row * tile_h_map  # top edge
        sx, sy = self._view.map_to_screen(mx, my)

        tag = f"tk_tile_{key.layer_id}_{key.zoom_level}_{key.tile_row}_{key.tile_col}"
        existing = self.find_withtag(tag)
        if existing:
            self.coords(existing[0], sx, sy)
        else:
            self.create_image(sx, sy, anchor="nw", image=photo, tags=("tile", tag))
        
        self._photo_refs[tag] = photo

    def _load_tile_async(
        self,
        key: TileKey,
        layer: Layer,
        lbounds: Any,
        row: int,
        col: int,
        tile_w_map: float,
        tile_h_map: float,
    ) -> None:
        """Submit a background tile load and schedule UI placement via after()."""
        with self._pending_lock:
            if key in self._pending_tiles:
                return
            self._pending_tiles.add(key)

        provider = self._providers.get(layer.id)
        if provider is None:
            return

        def _load() -> np.ndarray | None:
            try:
                return provider.get_tile(layer, key.zoom_level, row, col, _TILE_SIZE)
            except Exception:
                logger.exception("Tile load error for %s", key)
                return None

        def _on_done(fut: Any) -> None:
            arr = fut.result()
            with self._pending_lock:
                self._pending_tiles.discard(key)
            if arr is not None:
                # Schedule UI update on the main thread
                self.after(0, lambda: self._insert_loaded_tile(key, arr, layer, lbounds, row, col, tile_w_map, tile_h_map))

        future = self._executor.submit(_load)
        future.add_done_callback(_on_done)

    def _insert_loaded_tile(
        self,
        key: TileKey,
        arr: np.ndarray,
        layer: Layer,
        lbounds: Any,
        row: int,
        col: int,
        tile_w_map: float,
        tile_h_map: float,
    ) -> None:
        """Convert array to PhotoImage, cache it, and place on canvas."""
        if Image is None or ImageTk is None:
            return
        try:
            if arr.ndim == 2:
                pil_img = Image.fromarray(arr, mode="L")
            elif arr.shape[2] == 4:
                pil_img = Image.fromarray(arr, mode="RGBA")
            else:
                pil_img = Image.fromarray(arr, mode="RGB")
            photo = ImageTk.PhotoImage(pil_img)
        except Exception:
            logger.exception("Failed to create PhotoImage for %s", key)
            return

        self._tile_cache.put(key, photo)
        self._place_tile(key, photo, layer, lbounds, row, col, tile_w_map, tile_h_map)

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_resize(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        self._view.resize(event.width, event.height)
        self.refresh()

    def _on_press(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        self._drag_start_x = event.x
        self._drag_start_y = event.y
        tool = self._tool_manager.get_active()
        if tool is not None:
            mx, my = self._view.screen_to_map(event.x, event.y)
            tool.on_press(event.x, event.y, mx, my)

    def _on_drag(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        tool = self._tool_manager.get_active()
        if tool is not None:
            mx, my = self._view.screen_to_map(event.x, event.y)
            tool.on_drag(event.x, event.y, mx, my)

    def _on_release(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        self._drag_start_x = None
        self._drag_start_y = None
        tool = self._tool_manager.get_active()
        if tool is not None:
            mx, my = self._view.screen_to_map(event.x, event.y)
            tool.on_release(event.x, event.y, mx, my)

    def _on_move(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        mx, my = self._view.screen_to_map(event.x, event.y)
        self._event_bus.emit(EventType.VIEW_CHANGED, map_x=mx, map_y=my)
        tool = self._tool_manager.get_active()
        if tool is not None:
            tool.on_move(event.x, event.y, mx, my)

    def _on_scroll(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        # Windows / macOS: event.delta is +/-120 per notch
        if event.delta > 0:
            factor = 1.0 / _ZOOM_FACTOR
        else:
            factor = _ZOOM_FACTOR
        self._apply_zoom(factor, event.x, event.y)

        tool = self._tool_manager.get_active()
        if tool is not None:
            tool.on_scroll(event.x, event.y, event.delta)

    def _on_scroll_linux(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        if event.num == 4:
            factor = 1.0 / _ZOOM_FACTOR
        else:
            factor = _ZOOM_FACTOR
        self._apply_zoom(factor, event.x, event.y)

    def _apply_zoom(self, factor: float, sx: int, sy: int) -> None:
        self._view.zoom(factor, sx, sy)
        self.refresh()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _emit_view_changed(self) -> None:
        extent = self._view.get_visible_extent()
        self._event_bus.emit(
            EventType.VIEW_CHANGED,
            extent=extent,
            scale=self._view.scale,
        )
