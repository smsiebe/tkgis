"""Raster metadata extraction from GRDL readers."""
from __future__ import annotations

import logging
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


class RasterMetadataExtractor:
    """Extract standardised metadata dictionaries from GRDL ImageReaders."""

    @staticmethod
    def extract(reader: Any) -> dict[str, Any]:
        """Build a metadata dictionary from an open GRDL reader.

        Parameters
        ----------
        reader : grdl.IO.base.ImageReader
            An open reader with ``metadata``, ``get_shape()``, and
            ``get_dtype()`` available.

        Returns
        -------
        dict
            Keys: ``rows``, ``cols``, ``bands``, ``dtype``, ``modality``,
            ``format``, ``crs``, ``nodata``, ``is_complex``.
        """
        md = reader.metadata
        shape = reader.get_shape()
        dtype = reader.get_dtype()

        # Determine rows, cols, bands from metadata or shape
        rows = _get_field(md, "rows", shape[0] if len(shape) >= 2 else 0)
        cols = _get_field(md, "cols", shape[1] if len(shape) >= 2 else 0)
        bands_val = _get_field(md, "bands", None)
        if bands_val is None:
            bands_val = shape[2] if len(shape) >= 3 else 1

        fmt = _get_field(md, "format", "unknown")
        crs = _get_field(md, "crs", None)
        nodata = _get_field(md, "nodata", None)

        is_complex = np.issubdtype(dtype, np.complexfloating)
        modality = _infer_modality(fmt, is_complex, dtype)

        return {
            "rows": int(rows),
            "cols": int(cols),
            "bands": int(bands_val),
            "dtype": str(dtype),
            "modality": modality,
            "format": fmt,
            "crs": crs,
            "nodata": nodata,
            "is_complex": is_complex,
        }


def _get_field(md: Any, key: str, default: Any = None) -> Any:
    """Get a field from metadata that may be a dict or an object."""
    if hasattr(md, "get"):
        return md.get(key, default)
    return getattr(md, key, default)


def _infer_modality(fmt: str, is_complex: bool, dtype: np.dtype) -> str:
    """Best-effort modality inference."""
    if is_complex:
        return "SAR"

    fmt_lower = fmt.lower() if isinstance(fmt, str) else ""
    if "nitf" in fmt_lower or "sicd" in fmt_lower:
        return "SAR"
    if "geotiff" in fmt_lower or "tif" in fmt_lower:
        return "EO"
    if "hdf" in fmt_lower:
        return "MSI"
    if "jp2" in fmt_lower or "jpeg" in fmt_lower:
        return "EO"
    return "unknown"
