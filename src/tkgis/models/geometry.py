"""Bounding box geometry model for tkgis."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class BoundingBox:
    """Axis-aligned bounding box with CRS awareness.

    Coordinates follow the convention (xmin, ymin) = lower-left,
    (xmax, ymax) = upper-right.
    """

    xmin: float
    ymin: float
    xmax: float
    ymax: float
    crs: str = "EPSG:4326"

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def width(self) -> float:
        """Width of the bounding box (xmax - xmin)."""
        return self.xmax - self.xmin

    @property
    def height(self) -> float:
        """Height of the bounding box (ymax - ymin)."""
        return self.ymax - self.ymin

    @property
    def center(self) -> tuple[float, float]:
        """Center point as (x, y)."""
        return (
            (self.xmin + self.xmax) / 2.0,
            (self.ymin + self.ymax) / 2.0,
        )

    # ------------------------------------------------------------------
    # Spatial operations
    # ------------------------------------------------------------------

    def contains(self, x: float, y: float) -> bool:
        """Return True if the point (x, y) lies inside or on the boundary."""
        return self.xmin <= x <= self.xmax and self.ymin <= y <= self.ymax

    def intersects(self, other: BoundingBox) -> bool:
        """Return True if *other* overlaps this bounding box.

        Both boxes must share the same CRS; no reprojection is attempted.
        """
        if self.crs != other.crs:
            raise ValueError(
                f"CRS mismatch: {self.crs} vs {other.crs}. "
                "Reproject before testing intersection."
            )
        return not (
            other.xmin > self.xmax
            or other.xmax < self.xmin
            or other.ymin > self.ymax
            or other.ymax < self.ymin
        )

    def union(self, other: BoundingBox) -> BoundingBox:
        """Return the smallest BoundingBox enclosing both boxes.

        Both boxes must share the same CRS.
        """
        if self.crs != other.crs:
            raise ValueError(
                f"CRS mismatch: {self.crs} vs {other.crs}. "
                "Reproject before computing union."
            )
        return BoundingBox(
            xmin=min(self.xmin, other.xmin),
            ymin=min(self.ymin, other.ymin),
            xmax=max(self.xmax, other.xmax),
            ymax=max(self.ymax, other.ymax),
            crs=self.crs,
        )

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dictionary."""
        return {
            "xmin": self.xmin,
            "ymin": self.ymin,
            "xmax": self.xmax,
            "ymax": self.ymax,
            "crs": self.crs,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> BoundingBox:
        """Deserialize from a plain dictionary."""
        return cls(
            xmin=d["xmin"],
            ymin=d["ymin"],
            xmax=d["xmax"],
            ymax=d["ymax"],
            crs=d.get("crs", "EPSG:4326"),
        )
