"""Project and MapView models for tkgis."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from tkgis.models.crs import CRSDefinition
from tkgis.models.geometry import BoundingBox
from tkgis.models.layers import Layer


@dataclass
class MapView:
    """Persisted viewport state."""

    center_x: float = 0.0
    center_y: float = 0.0
    zoom_level: float = 1.0
    rotation: float = 0.0
    crs: str = "EPSG:4326"

    def to_dict(self) -> dict[str, Any]:
        return {
            "center_x": self.center_x,
            "center_y": self.center_y,
            "zoom_level": self.zoom_level,
            "rotation": self.rotation,
            "crs": self.crs,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> MapView:
        return cls(
            center_x=d.get("center_x", 0.0),
            center_y=d.get("center_y", 0.0),
            zoom_level=d.get("zoom_level", 1.0),
            rotation=d.get("rotation", 0.0),
            crs=d.get("crs", "EPSG:4326"),
        )


@dataclass
class Project:
    """Top-level project container.

    Owns the layer stack, CRS, viewport state, and plugin state.
    Serializes to / deserializes from JSON for project save/load.
    """

    name: str = "Untitled Project"
    path: str | None = None
    crs: CRSDefinition = field(
        default_factory=lambda: CRSDefinition.from_epsg(4326)
    )
    layers: list[Layer] = field(default_factory=list)
    map_view: MapView = field(default_factory=MapView)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    modified_at: str = field(default_factory=lambda: datetime.now().isoformat())
    plugin_state: dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Layer operations
    # ------------------------------------------------------------------

    def add_layer(self, layer: Layer) -> None:
        """Append a layer to the stack."""
        self.layers.append(layer)
        self._touch()

    def remove_layer(self, layer_id: str) -> None:
        """Remove the layer with the given *layer_id*."""
        self.layers = [lyr for lyr in self.layers if lyr.id != layer_id]
        self._touch()

    def get_layer(self, layer_id: str) -> Layer | None:
        """Return the layer with *layer_id*, or ``None``."""
        for lyr in self.layers:
            if lyr.id == layer_id:
                return lyr
        return None

    def move_layer(self, layer_id: str, new_index: int) -> None:
        """Move the layer identified by *layer_id* to *new_index*."""
        layer = self.get_layer(layer_id)
        if layer is None:
            raise KeyError(f"Unknown layer: {layer_id!r}")
        self.layers.remove(layer)
        new_index = max(0, min(new_index, len(self.layers)))
        self.layers.insert(new_index, layer)
        self._touch()

    def get_full_extent(self) -> BoundingBox | None:
        """Return the union of all layer bounding boxes, or ``None``."""
        result: BoundingBox | None = None
        for lyr in self.layers:
            if lyr.bounds is not None:
                result = lyr.bounds if result is None else result.union(lyr.bounds)
        return result

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, path: str | None = None) -> None:
        """Write the project to a JSON file.

        If *path* is provided it becomes the new ``self.path``.
        """
        if path is not None:
            self.path = path
        if self.path is None:
            raise ValueError("No save path specified")
        self._touch()
        with open(self.path, "w", encoding="utf-8") as fh:
            json.dump(self.to_dict(), fh, indent=2)

    @classmethod
    def load(cls, path: str) -> Project:
        """Load a project from a JSON file."""
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        proj = cls.from_dict(data)
        proj.path = path
        return proj

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "crs": self.crs.to_dict(),
            "layers": [lyr.to_dict() for lyr in self.layers],
            "map_view": self.map_view.to_dict(),
            "created_at": self.created_at,
            "modified_at": self.modified_at,
            "plugin_state": self.plugin_state,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Project:
        crs_data = d.get("crs")
        map_view_data = d.get("map_view")
        return cls(
            name=d.get("name", "Untitled Project"),
            crs=CRSDefinition.from_dict(crs_data) if crs_data else CRSDefinition.from_epsg(4326),
            layers=[Layer.from_dict(lyr) for lyr in d.get("layers", [])],
            map_view=MapView.from_dict(map_view_data) if map_view_data else MapView(),
            created_at=d.get("created_at", datetime.now().isoformat()),
            modified_at=d.get("modified_at", datetime.now().isoformat()),
            plugin_state=d.get("plugin_state", {}),
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _touch(self) -> None:
        """Update the modification timestamp."""
        self.modified_at = datetime.now().isoformat()
