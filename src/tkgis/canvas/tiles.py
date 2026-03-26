"""Tile provider abstraction and LRU tile cache for tkgis."""
from __future__ import annotations

import collections
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from PIL.ImageTk import PhotoImage as PILPhotoImage
    from tkgis.models.layers import Layer


@dataclass(frozen=True)
class TileKey:
    """Immutable, hashable key for a single tile."""

    layer_id: str
    zoom_level: int
    tile_row: int
    tile_col: int


class TileProvider(ABC):
    """Abstract base for tile data sources.

    Implementations supply raw pixel data (NumPy arrays) for a given layer
    and tile coordinate.  The canvas converts them to PhotoImages.
    """

    @abstractmethod
    def get_tile(
        self,
        layer: Layer,
        zoom_level: int,
        row: int,
        col: int,
        tile_size: int = 256,
    ) -> np.ndarray | None:
        """Return an RGBA uint8 array of shape (tile_size, tile_size, 4), or None."""

    @abstractmethod
    def get_num_zoom_levels(self, layer: Layer) -> int:
        """Return the number of zoom levels available for *layer*."""

    @abstractmethod
    def get_tile_grid(self, layer: Layer, zoom_level: int) -> tuple[int, int]:
        """Return (num_rows, num_cols) in the tile grid for *zoom_level*."""


class TileCache:
    """Thread-safe LRU cache for rendered PhotoImage tiles.

    Evicts least-recently-used entries when *max_tiles* is exceeded.
    """

    def __init__(self, max_tiles: int = 256) -> None:
        self.max_tiles = max_tiles
        self._lock = threading.Lock()
        # OrderedDict used as LRU: most-recently-used at the end.
        self._cache: collections.OrderedDict[TileKey, Any] = collections.OrderedDict()

    def get(self, key: TileKey) -> Any | None:
        """Retrieve the cached PhotoImage for *key*, or ``None``."""
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                return self._cache[key]
            return None

    def put(self, key: TileKey, image: Any) -> None:
        """Store *image* under *key*, evicting old entries if necessary."""
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                self._cache[key] = image
            else:
                self._cache[key] = image
                while len(self._cache) > self.max_tiles:
                    self._cache.popitem(last=False)

    def invalidate_layer(self, layer_id: str) -> None:
        """Remove all cached tiles belonging to *layer_id*."""
        with self._lock:
            keys_to_remove = [k for k in self._cache if k.layer_id == layer_id]
            for k in keys_to_remove:
                del self._cache[k]

    def clear(self) -> None:
        """Drop every cached tile."""
        with self._lock:
            self._cache.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._cache)
