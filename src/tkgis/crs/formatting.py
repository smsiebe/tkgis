"""Coordinate formatting utilities."""

from __future__ import annotations

from typing import Union

import pyproj

from tkgis.models.crs import CRSDefinition

CRSLike = Union[CRSDefinition, int]


def _resolve_crs(crs: CRSLike) -> pyproj.CRS:
    if isinstance(crs, int):
        return pyproj.CRS.from_epsg(crs)
    return crs.to_pyproj()


class CoordinateFormatter:
    """Formats coordinates in various notations."""

    # ------------------------------------------------------------------
    # Decimal Degrees
    # ------------------------------------------------------------------

    def format_dd(self, x: float, y: float) -> str:
        """Format geographic coordinates as decimal degrees.

        Returns a string like ``"38.8977° N, 77.0365° W"``.
        *x* is longitude, *y* is latitude.
        """
        lat_dir = "N" if y >= 0 else "S"
        lon_dir = "E" if x >= 0 else "W"
        return f"{abs(y):.4f}\u00b0 {lat_dir}, {abs(x):.4f}\u00b0 {lon_dir}"

    # ------------------------------------------------------------------
    # Degrees / Minutes / Seconds
    # ------------------------------------------------------------------

    @staticmethod
    def _dd_to_dms(dd: float) -> tuple[int, int, float]:
        """Convert decimal degrees to (degrees, minutes, seconds)."""
        dd = abs(dd)
        d = int(dd)
        m_full = (dd - d) * 60
        m = int(m_full)
        s = (m_full - m) * 60
        return d, m, s

    def format_dms(self, x: float, y: float) -> str:
        """Format geographic coordinates as DMS.

        Returns a string like ``38° 53' 51.7" N, 77° 2' 11.4" W``.
        """
        lat_d, lat_m, lat_s = self._dd_to_dms(y)
        lon_d, lon_m, lon_s = self._dd_to_dms(x)
        lat_dir = "N" if y >= 0 else "S"
        lon_dir = "E" if x >= 0 else "W"
        return (
            f'{lat_d}\u00b0 {lat_m}\' {lat_s:.1f}" {lat_dir}, '
            f'{lon_d}\u00b0 {lon_m}\' {lon_s:.1f}" {lon_dir}'
        )

    # ------------------------------------------------------------------
    # Projected (easting / northing)
    # ------------------------------------------------------------------

    def format_projected(self, x: float, y: float, units: str = "m") -> str:
        """Format projected coordinates.

        Returns a string like ``"500000.00 m E, 4649776.22 m N"``.
        """
        return f"{x:.2f} {units} E, {y:.2f} {units} N"

    # ------------------------------------------------------------------
    # Auto
    # ------------------------------------------------------------------

    def auto_format(self, x: float, y: float, crs: CRSLike) -> str:
        """Choose the best format automatically based on *crs*."""
        c = _resolve_crs(crs)
        if c.is_geographic:
            return self.format_dd(x, y)
        units = "m"
        if c.axis_info:
            units = c.axis_info[0].unit_name
        return self.format_projected(x, y, units)
