"""Coordinate Reference System definition model for tkgis."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    import pyproj

# Well-known EPSG definitions so basic lookups work without pyproj.
_WELL_KNOWN: dict[int, dict[str, Any]] = {
    4326: {
        "name": "WGS 84",
        "is_geographic": True,
        "units": "degrees",
    },
    3857: {
        "name": "WGS 84 / Pseudo-Mercator",
        "is_geographic": False,
        "units": "meters",
    },
    32601: {
        "name": "WGS 84 / UTM zone 1N",
        "is_geographic": False,
        "units": "meters",
    },
}


@dataclass
class CRSDefinition:
    """Lightweight CRS descriptor that works with or without *pyproj*."""

    epsg_code: int | None = None
    proj_string: str | None = None
    wkt: str | None = None
    name: str = ""
    is_geographic: bool = True
    units: str = "degrees"

    # ------------------------------------------------------------------
    # Factories
    # ------------------------------------------------------------------

    @classmethod
    def from_epsg(cls, code: int) -> CRSDefinition:
        """Build a CRSDefinition from an EPSG code.

        Attempts to use *pyproj* for full metadata; falls back to a small
        built-in table for common codes (4326, 3857).
        """
        try:
            import pyproj  # type: ignore[import-untyped]

            crs = pyproj.CRS.from_epsg(code)
            return cls(
                epsg_code=code,
                proj_string=crs.to_proj4(),
                wkt=crs.to_wkt(),
                name=crs.name,
                is_geographic=crs.is_geographic,
                units="degrees" if crs.is_geographic else "meters",
            )
        except Exception:
            info = _WELL_KNOWN.get(code, {})
            return cls(
                epsg_code=code,
                proj_string=None,
                wkt=None,
                name=info.get("name", f"EPSG:{code}"),
                is_geographic=info.get("is_geographic", True),
                units=info.get("units", "degrees"),
            )

    # ------------------------------------------------------------------
    # Interop
    # ------------------------------------------------------------------

    def to_pyproj(self) -> pyproj.CRS:
        """Return a *pyproj.CRS* instance (lazy import)."""
        import pyproj  # type: ignore[import-untyped]

        if self.epsg_code is not None:
            return pyproj.CRS.from_epsg(self.epsg_code)
        if self.wkt:
            return pyproj.CRS.from_wkt(self.wkt)
        if self.proj_string:
            return pyproj.CRS.from_proj4(self.proj_string)
        raise ValueError("CRSDefinition has no usable representation for pyproj")

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dictionary."""
        return {
            "epsg_code": self.epsg_code,
            "proj_string": self.proj_string,
            "wkt": self.wkt,
            "name": self.name,
            "is_geographic": self.is_geographic,
            "units": self.units,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> CRSDefinition:
        """Deserialize from a plain dictionary."""
        return cls(
            epsg_code=d.get("epsg_code"),
            proj_string=d.get("proj_string"),
            wkt=d.get("wkt"),
            name=d.get("name", ""),
            is_geographic=d.get("is_geographic", True),
            units=d.get("units", "degrees"),
        )
