"""Bridge between GRDL geolocation and tkgis models.

Extracts geolocation objects, bounding boxes, and CRS definitions from
GRDL ImageReader instances.
"""
from __future__ import annotations

import logging
from typing import Any

import numpy as np

from tkgis.models.crs import CRSDefinition
from tkgis.models.geometry import BoundingBox

logger = logging.getLogger(__name__)

# Guard GRDL imports for graceful degradation
try:
    from grdl.geolocation.base import Geolocation
    from grdl.geolocation.eo.affine import AffineGeolocation

    _HAS_GRDL_GEOLOC = True
except ImportError:
    _HAS_GRDL_GEOLOC = False
    Geolocation = None  # type: ignore[assignment,misc]
    AffineGeolocation = None  # type: ignore[assignment,misc]


class RasterGeolocationBridge:
    """Static utilities bridging GRDL geolocation to tkgis models."""

    @staticmethod
    def extract_geolocation(reader: Any) -> Any | None:
        """Attempt to build a GRDL Geolocation from a reader.

        For GeoTIFF readers the ``metadata`` dict should contain
        ``transform`` and ``crs`` keys (inside ``extras``).  If those are
        present an :class:`AffineGeolocation` is returned.

        Parameters
        ----------
        reader : grdl.IO.base.ImageReader
            An open GRDL reader instance.

        Returns
        -------
        Geolocation or None
        """
        if not _HAS_GRDL_GEOLOC:
            logger.debug("GRDL geolocation not available; skipping")
            return None

        try:
            md = reader.metadata
            # ImageMetadata.get() may not expose 'extras'; use getattr
            extras = getattr(md, "extras", None)
            if extras is None or not isinstance(extras, dict):
                extras = md.get("extras", {}) if hasattr(md, "get") else {}
            transform = extras.get("transform") if isinstance(extras, dict) else None
            crs_str = getattr(md, "crs", None)
            if crs_str is None and hasattr(md, "get"):
                crs_str = md.get("crs", None)

            if transform is not None and crs_str is not None:
                rows = md.get("rows", None) if hasattr(md, "get") else getattr(md, "rows", None)
                cols = md.get("cols", None) if hasattr(md, "get") else getattr(md, "cols", None)
                if rows is not None and cols is not None:
                    geoloc = AffineGeolocation(
                        transform=transform,
                        shape=(rows, cols),
                        crs=crs_str,
                    )
                    return geoloc
        except Exception:
            logger.debug("Failed to build geolocation from reader", exc_info=True)

        return None

    @staticmethod
    def compute_bounds(reader: Any, geolocation: Any | None) -> BoundingBox:
        """Compute geographic bounds for a raster.

        Uses the GRDL geolocation ``get_bounds()`` when available.  Falls
        back to the four image corners via ``image_to_latlon()``.  If no
        geolocation is available, returns a dummy unit box.

        Parameters
        ----------
        reader : grdl.IO.base.ImageReader
        geolocation : Geolocation or None

        Returns
        -------
        BoundingBox
        """
        if geolocation is not None:
            try:
                # get_bounds() returns (lon_min, lat_min, lon_max, lat_max)
                bounds = geolocation.get_bounds()
                return BoundingBox(
                    xmin=bounds[0],
                    ymin=bounds[1],
                    xmax=bounds[2],
                    ymax=bounds[3],
                    crs="EPSG:4326",
                )
            except Exception:
                logger.debug("get_bounds() failed; falling back to corners", exc_info=True)

            try:
                md = reader.metadata
                rows = md.get("rows", None) if hasattr(md, "get") else getattr(md, "rows", None)
                cols = md.get("cols", None) if hasattr(md, "get") else getattr(md, "cols", None)
                if rows is not None and cols is not None:
                    corners_rc = np.array([
                        [0, 0],
                        [0, cols - 1],
                        [rows - 1, 0],
                        [rows - 1, cols - 1],
                    ], dtype=np.float64)
                    latlons = geolocation.image_to_latlon(corners_rc)
                    lats = latlons[:, 0]
                    lons = latlons[:, 1]
                    return BoundingBox(
                        xmin=float(np.min(lons)),
                        ymin=float(np.min(lats)),
                        xmax=float(np.max(lons)),
                        ymax=float(np.max(lats)),
                        crs="EPSG:4326",
                    )
            except Exception:
                logger.debug("Corner-based bounds failed", exc_info=True)

        # Fallback: use rasterio bounds from metadata extras if present
        try:
            md = reader.metadata
            extras = getattr(md, "extras", None)
            if extras is None or not isinstance(extras, dict):
                extras = md.get("extras", {}) if hasattr(md, "get") else {}
            if isinstance(extras, dict) and "bounds" in extras:
                b = extras["bounds"]
                return BoundingBox(
                    xmin=b.left,
                    ymin=b.bottom,
                    xmax=b.right,
                    ymax=b.top,
                    crs="EPSG:4326",
                )
        except Exception:
            logger.debug("Rasterio bounds fallback failed", exc_info=True)

        # Last resort dummy box
        return BoundingBox(xmin=0, ymin=0, xmax=1, ymax=1, crs="EPSG:4326")

    @staticmethod
    def extract_crs(reader: Any, geolocation: Any | None) -> CRSDefinition:
        """Extract a CRSDefinition from the reader or geolocation.

        Parameters
        ----------
        reader : grdl.IO.base.ImageReader
        geolocation : Geolocation or None

        Returns
        -------
        CRSDefinition
        """
        crs_str: str | None = None

        # Try metadata first
        try:
            md = reader.metadata
            crs_str = getattr(md, "crs", None)
            if crs_str is None and hasattr(md, "get"):
                crs_str = md.get("crs", None)
        except Exception:
            pass

        if crs_str:
            # Parse EPSG code if possible
            epsg = _parse_epsg(crs_str)
            if epsg is not None:
                return CRSDefinition.from_epsg(epsg)
            return CRSDefinition(
                proj_string=crs_str,
                name=crs_str,
            )

        return CRSDefinition.from_epsg(4326)  # default WGS84


def _parse_epsg(crs_str: str) -> int | None:
    """Try to extract an EPSG code from a CRS string."""
    if not crs_str:
        return None
    s = crs_str.strip().upper()
    if s.startswith("EPSG:"):
        try:
            return int(s.split(":")[1])
        except (ValueError, IndexError):
            return None
    # Try pyproj
    try:
        import pyproj  # type: ignore[import-untyped]
        crs = pyproj.CRS(crs_str)
        code = crs.to_epsg()
        return code
    except Exception:
        return None
