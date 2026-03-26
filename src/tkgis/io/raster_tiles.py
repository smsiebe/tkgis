"""Raster tile provider — chip-based tile serving backed by GRDL readers.

Implements the TileProvider ABC by reading image chips on demand, building
a simple power-of-two pyramid, and handing off display transform to
RasterDisplayEngine.
"""
from __future__ import annotations

import logging
import math
from typing import Any, TYPE_CHECKING

import numpy as np

from tkgis.canvas.tiles import TileProvider
from tkgis.io.raster_display import RasterDisplayEngine

if TYPE_CHECKING:
    from tkgis.models.layers import Layer

logger = logging.getLogger(__name__)


class RasterTileProvider(TileProvider):
    """Serve 256x256 RGBA tiles from a GRDL ImageReader.

    Parameters
    ----------
    reader : grdl.IO.base.ImageReader
        An open GRDL reader (must stay open for the lifetime of this
        provider).
    geolocation : object or None
        A GRDL Geolocation instance; currently unused for tile maths but
        retained for future geo-query support.
    layer : Layer
        The tkgis Layer this provider is bound to.
    """

    def __init__(self, reader: Any, geolocation: Any | None, layer: Layer) -> None:
        self._reader = reader
        self._geolocation = geolocation
        self._layer = layer
        self._pyramid: list[tuple[int, int, int, int]] = []  # per-level info
        self._build_pyramid_info()

    # ------------------------------------------------------------------
    # Pyramid computation
    # ------------------------------------------------------------------

    def _build_pyramid_info(self) -> None:
        """Compute tile grids for each zoom level.

        Level 0 is the most zoomed-out (overview); the highest level shows
        pixels 1:1.  Each level doubles the resolution.
        """
        shape = self._reader.get_shape()
        rows = shape[0]
        cols = shape[1] if len(shape) >= 2 else 1

        # Number of zoom levels: ceil(log2(max(rows, cols) / tile_size)) + 1
        tile_size = 256
        max_dim = max(rows, cols)
        if max_dim <= 0:
            self._pyramid = [(1, 1, rows, cols)]
            return

        num_levels = max(1, int(math.ceil(math.log2(max_dim / tile_size))) + 1)

        self._pyramid = []
        for level in range(num_levels):
            # At the highest level, each tile covers tile_size pixels.
            # At level 0, each tile covers (2^(num_levels-1)) * tile_size pixels.
            scale = 2 ** (num_levels - 1 - level)
            pixels_per_tile = tile_size * scale
            grid_rows = max(1, int(math.ceil(rows / pixels_per_tile)))
            grid_cols = max(1, int(math.ceil(cols / pixels_per_tile)))
            self._pyramid.append((grid_rows, grid_cols, rows, cols))

    # ------------------------------------------------------------------
    # TileProvider interface
    # ------------------------------------------------------------------

    def get_tile(
        self,
        layer: Layer,
        zoom_level: int,
        row: int,
        col: int,
        tile_size: int = 256,
    ) -> np.ndarray | None:
        """Return an RGBA uint8 array of shape ``(tile_size, tile_size, 4)``.

        Steps:
        1. Compute the image-space region for this tile at this zoom level.
        2. Read the chip via ``reader.read_chip()``.
        3. Downsample to *tile_size* using strided sampling.
        4. Run display transform (RasterDisplayEngine).
        """
        if zoom_level < 0 or zoom_level >= len(self._pyramid):
            return None

        grid_rows, grid_cols, img_rows, img_cols = self._pyramid[zoom_level]

        if row < 0 or row >= grid_rows or col < 0 or col >= grid_cols:
            return None

        num_levels = len(self._pyramid)
        scale = 2 ** (num_levels - 1 - zoom_level)
        pixels_per_tile = tile_size * scale

        # Image-space extents for this tile
        r_start = row * pixels_per_tile
        r_end = min(r_start + pixels_per_tile, img_rows)
        c_start = col * pixels_per_tile
        c_end = min(c_start + pixels_per_tile, img_cols)

        if r_start >= img_rows or c_start >= img_cols:
            return None

        try:
            chip = self._reader.read_chip(r_start, r_end, c_start, c_end)
        except Exception:
            logger.debug(
                "read_chip failed for tile z=%d r=%d c=%d",
                zoom_level, row, col,
                exc_info=True,
            )
            return None

        # Downsample to tile_size using striding
        chip = self._downsample(chip, tile_size)

        # Display transform
        style = self._layer.style if self._layer else None
        rgba = RasterDisplayEngine.to_display_rgb(chip, style)

        # Ensure exact tile_size output (pad if the tile is at the edge)
        rgba = self._pad_to_tile(rgba, tile_size)

        return rgba

    def get_num_zoom_levels(self, layer: Layer) -> int:
        """Return the number of zoom levels available."""
        return len(self._pyramid)

    def get_tile_grid(self, layer: Layer, zoom_level: int) -> tuple[int, int]:
        """Return ``(num_rows, num_cols)`` for the tile grid at *zoom_level*."""
        if 0 <= zoom_level < len(self._pyramid):
            return (self._pyramid[zoom_level][0], self._pyramid[zoom_level][1])
        return (0, 0)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _downsample(chip: np.ndarray, target: int) -> np.ndarray:
        """Downsample *chip* so the spatial dimensions do not exceed *target*.

        Uses strided subsampling for speed (no interpolation needed for
        overview tiles).
        """
        if chip.ndim == 2:
            h, w = chip.shape
            step_r = max(1, h // target)
            step_c = max(1, w // target)
            return chip[::step_r, ::step_c]
        elif chip.ndim == 3:
            # Band-first: (B, H, W)
            b, h, w = chip.shape
            step_r = max(1, h // target)
            step_c = max(1, w // target)
            return chip[:, ::step_r, ::step_c]
        return chip

    @staticmethod
    def _pad_to_tile(rgba: np.ndarray, tile_size: int) -> np.ndarray:
        """Pad RGBA array to exact ``(tile_size, tile_size, 4)``."""
        h, w = rgba.shape[:2]
        if h >= tile_size and w >= tile_size:
            return rgba[:tile_size, :tile_size, :]
        out = np.zeros((tile_size, tile_size, 4), dtype=np.uint8)
        rh = min(h, tile_size)
        rw = min(w, tile_size)
        out[:rh, :rw, :] = rgba[:rh, :rw, :]
        return out
