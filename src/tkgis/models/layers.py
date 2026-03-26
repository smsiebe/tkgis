"""Layer, LayerType, and LayerStyle models for tkgis."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from tkgis.models.crs import CRSDefinition
from tkgis.models.geometry import BoundingBox


class LayerType(Enum):
    """Supported layer types."""

    VECTOR = "vector"
    RASTER = "raster"
    TEMPORAL_RASTER = "temporal_raster"
    TEMPORAL_VECTOR = "temporal_vector"
    ANNOTATION = "annotation"


@dataclass
class LayerStyle:
    """Visual styling parameters for a layer."""

    opacity: float = 1.0
    visible: bool = True
    fill_color: str | None = None
    stroke_color: str | None = None
    stroke_width: float = 1.0
    colormap: str | None = None
    band_mapping: list[int] | None = None
    contrast_stretch: str = "percentile"
    stretch_params: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "opacity": self.opacity,
            "visible": self.visible,
            "fill_color": self.fill_color,
            "stroke_color": self.stroke_color,
            "stroke_width": self.stroke_width,
            "colormap": self.colormap,
            "band_mapping": self.band_mapping,
            "contrast_stretch": self.contrast_stretch,
            "stretch_params": self.stretch_params,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> LayerStyle:
        return cls(
            opacity=d.get("opacity", 1.0),
            visible=d.get("visible", True),
            fill_color=d.get("fill_color"),
            stroke_color=d.get("stroke_color"),
            stroke_width=d.get("stroke_width", 1.0),
            colormap=d.get("colormap"),
            band_mapping=d.get("band_mapping"),
            contrast_stretch=d.get("contrast_stretch", "percentile"),
            stretch_params=d.get("stretch_params"),
        )


@dataclass
class Layer:
    """A single map layer (raster, vector, or annotation)."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    layer_type: LayerType = LayerType.RASTER
    source_path: str | None = None
    crs: CRSDefinition | None = None
    bounds: BoundingBox | None = None
    style: LayerStyle = field(default_factory=LayerStyle)
    metadata: dict[str, Any] = field(default_factory=dict)
    time_start: str | None = None
    time_end: str | None = None
    time_steps: list[str] | None = None

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "layer_type": self.layer_type.value,
            "source_path": self.source_path,
            "crs": self.crs.to_dict() if self.crs else None,
            "bounds": self.bounds.to_dict() if self.bounds else None,
            "style": self.style.to_dict(),
            "metadata": self.metadata,
            "time_start": self.time_start,
            "time_end": self.time_end,
            "time_steps": self.time_steps,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Layer:
        """Deserialize from a plain dictionary."""
        crs_data = d.get("crs")
        bounds_data = d.get("bounds")
        style_data = d.get("style")
        return cls(
            id=d.get("id", str(uuid.uuid4())),
            name=d.get("name", ""),
            layer_type=LayerType(d.get("layer_type", "raster")),
            source_path=d.get("source_path"),
            crs=CRSDefinition.from_dict(crs_data) if crs_data else None,
            bounds=BoundingBox.from_dict(bounds_data) if bounds_data else None,
            style=LayerStyle.from_dict(style_data) if style_data else LayerStyle(),
            metadata=d.get("metadata", {}),
            time_start=d.get("time_start"),
            time_end=d.get("time_end"),
            time_steps=d.get("time_steps"),
        )
