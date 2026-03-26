"""Raster display engine — transforms raw raster data to display-ready RGB/RGBA.

Handles single-band, multi-band, and complex (SAR) data with configurable
stretching, colormap application, and band mapping.
"""
from __future__ import annotations

import logging
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


class RasterDisplayEngine:
    """Static utilities for converting raw raster arrays to uint8 RGBA."""

    @staticmethod
    def to_display_rgb(
        data: np.ndarray,
        style: Any | None = None,
    ) -> np.ndarray:
        """Convert raw raster data to an RGBA uint8 array.

        Parameters
        ----------
        data : np.ndarray
            Raw chip data.  Shapes accepted:
            - ``(H, W)`` — single band or complex
            - ``(B, H, W)`` — multi-band (band-first, matching GRDL convention)
        style : LayerStyle or None
            Optional styling parameters (colormap, band_mapping, stretch_params).

        Returns
        -------
        np.ndarray
            uint8 RGBA array with shape ``(H, W, 4)``.
        """
        if np.iscomplexobj(data):
            return RasterDisplayEngine._display_complex(data, style)

        if data.ndim == 2:
            return RasterDisplayEngine._display_single_band(data, style)

        if data.ndim == 3:
            bands = data.shape[0]
            # Apply band mapping if provided
            band_mapping = None
            if style is not None and hasattr(style, "band_mapping") and style.band_mapping:
                band_mapping = style.band_mapping

            if band_mapping is not None and len(band_mapping) == 3:
                rgb = data[band_mapping]  # select 3 bands
                return RasterDisplayEngine._display_rgb(rgb, style)
            elif bands >= 3:
                return RasterDisplayEngine._display_rgb(data[:3], style)
            elif bands == 1:
                return RasterDisplayEngine._display_single_band(data[0], style)
            else:
                # 2 bands — use first band as grayscale
                return RasterDisplayEngine._display_single_band(data[0], style)

        logger.warning("Unsupported data shape %s; returning black tile", data.shape)
        h = data.shape[-2] if data.ndim >= 2 else 1
        w = data.shape[-1] if data.ndim >= 1 else 1
        return np.zeros((h, w, 4), dtype=np.uint8)

    @staticmethod
    def _display_complex(data: np.ndarray, style: Any | None) -> np.ndarray:
        """Complex data -> magnitude -> dB -> stretch -> RGBA."""
        # For 3-D complex (B, H, W), use the first band
        work = data
        if work.ndim == 3:
            work = work[0]

        magnitude = np.abs(work)
        # Avoid log(0)
        magnitude = np.where(magnitude > 0, magnitude, np.finfo(float).tiny)
        db = 20.0 * np.log10(magnitude)
        stretched = RasterDisplayEngine.percentile_stretch(db, plow=2.0, phigh=98.0)
        return RasterDisplayEngine._gray_to_rgba(stretched)

    @staticmethod
    def _display_single_band(data: np.ndarray, style: Any | None) -> np.ndarray:
        """Single-band grayscale or colormap display."""
        colormap_name = None
        if style is not None and hasattr(style, "colormap"):
            colormap_name = style.colormap

        stretched = RasterDisplayEngine.percentile_stretch(data.astype(np.float64))

        if colormap_name:
            return RasterDisplayEngine.apply_colormap(stretched, colormap_name)
        return RasterDisplayEngine._gray_to_rgba(stretched)

    @staticmethod
    def _display_rgb(data: np.ndarray, style: Any | None) -> np.ndarray:
        """Three-band RGB display with percentile stretch per band.

        Parameters
        ----------
        data : np.ndarray
            Shape ``(3, H, W)``.
        """
        h, w = data.shape[1], data.shape[2]
        out = np.empty((h, w, 4), dtype=np.uint8)
        for i in range(3):
            out[:, :, i] = RasterDisplayEngine.percentile_stretch(
                data[i].astype(np.float64)
            )
        out[:, :, 3] = 255
        return out

    @staticmethod
    def _gray_to_rgba(gray_uint8: np.ndarray) -> np.ndarray:
        """Convert a 2-D uint8 grayscale array to (H, W, 4) RGBA."""
        h, w = gray_uint8.shape[:2]
        out = np.empty((h, w, 4), dtype=np.uint8)
        out[:, :, 0] = gray_uint8
        out[:, :, 1] = gray_uint8
        out[:, :, 2] = gray_uint8
        out[:, :, 3] = 255
        return out

    @staticmethod
    def apply_colormap(data_2d: np.ndarray, colormap_name: str) -> np.ndarray:
        """Apply a named colormap to a uint8 grayscale array.

        Parameters
        ----------
        data_2d : np.ndarray
            2-D uint8 array (already stretched to 0-255).
        colormap_name : str
            One of the built-in colormaps: ``'jet'``, ``'viridis'``,
            ``'hot'``, ``'cool'``, ``'gray'``.

        Returns
        -------
        np.ndarray
            RGBA uint8 array with shape ``(H, W, 4)``.
        """
        lut = _build_colormap_lut(colormap_name)  # (256, 4)
        indices = np.clip(data_2d, 0, 255).astype(np.uint8)
        return lut[indices]

    @staticmethod
    def percentile_stretch(
        data: np.ndarray,
        plow: float = 2.0,
        phigh: float = 98.0,
    ) -> np.ndarray:
        """Linear percentile stretch to uint8.

        Parameters
        ----------
        data : np.ndarray
            Input array (any numeric dtype).
        plow, phigh : float
            Lower and upper percentiles for the stretch.

        Returns
        -------
        np.ndarray
            uint8 array scaled to [0, 255].
        """
        finite = data[np.isfinite(data)] if np.issubdtype(data.dtype, np.floating) else data.ravel()
        if finite.size == 0:
            return np.zeros(data.shape, dtype=np.uint8)

        lo = float(np.percentile(finite, plow))
        hi = float(np.percentile(finite, phigh))

        if hi <= lo:
            # Constant image
            return np.full(data.shape, 128, dtype=np.uint8)

        clipped = np.clip(data.astype(np.float64), lo, hi)
        scaled = (clipped - lo) / (hi - lo) * 255.0
        return scaled.astype(np.uint8)


# ---------------------------------------------------------------------------
# Colormap LUT helpers
# ---------------------------------------------------------------------------

def _build_colormap_lut(name: str) -> np.ndarray:
    """Return a (256, 4) uint8 RGBA lookup table for *name*.

    Tries matplotlib first; falls back to simple built-in ramps.
    """
    try:
        import matplotlib.cm as cm  # type: ignore[import-untyped]

        cmap = cm.colormaps.get_cmap(name)
        lut = (cmap(np.linspace(0, 1, 256)) * 255).astype(np.uint8)
        return lut
    except Exception:
        pass

    # Built-in fallback colormaps
    return _BUILTIN_CMAPS.get(name, _gray_lut)()


def _jet_lut() -> np.ndarray:
    """Approximate jet colormap."""
    lut = np.zeros((256, 4), dtype=np.uint8)
    x = np.linspace(0, 1, 256)
    lut[:, 0] = np.clip(1.5 - np.abs(4 * x - 3), 0, 1) * 255
    lut[:, 1] = np.clip(1.5 - np.abs(4 * x - 2), 0, 1) * 255
    lut[:, 2] = np.clip(1.5 - np.abs(4 * x - 1), 0, 1) * 255
    lut[:, 3] = 255
    return lut.astype(np.uint8)


def _gray_lut() -> np.ndarray:
    lut = np.zeros((256, 4), dtype=np.uint8)
    ramp = np.arange(256, dtype=np.uint8)
    lut[:, 0] = ramp
    lut[:, 1] = ramp
    lut[:, 2] = ramp
    lut[:, 3] = 255
    return lut


def _hot_lut() -> np.ndarray:
    lut = np.zeros((256, 4), dtype=np.uint8)
    x = np.linspace(0, 1, 256)
    lut[:, 0] = np.clip(x * 3, 0, 1) * 255
    lut[:, 1] = np.clip(x * 3 - 1, 0, 1) * 255
    lut[:, 2] = np.clip(x * 3 - 2, 0, 1) * 255
    lut[:, 3] = 255
    return lut.astype(np.uint8)


_BUILTIN_CMAPS = {
    "jet": _jet_lut,
    "gray": _gray_lut,
    "hot": _hot_lut,
}
