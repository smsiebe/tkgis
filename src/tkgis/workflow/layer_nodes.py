"""Layer I/O pseudo-nodes for bridging map layers into workflows."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class LayerInputNode:
    """Represents a loaded map layer as a workflow input source.

    When dragged onto the canvas this creates a special source node whose
    output feeds into the first processing step.
    """

    layer_name: str = ""
    layer_id: str = ""
    layer_type: str = "raster"

    @property
    def processor_name(self) -> str:
        if self.layer_type in ("vector", "feature_set"):
            return "tkgis.input.vector"
        return "tkgis.input.raster"

    @property
    def output_type(self) -> str:
        if self.layer_type in ("vector", "feature_set"):
            return "feature_set"
        return "raster"

    @property
    def input_type(self) -> None:
        return None

    @property
    def params(self) -> dict[str, Any]:
        return {"layer_id": self.layer_id, "layer_name": self.layer_name}


@dataclass
class LayerOutputNode:
    """Represents a workflow output that creates a new map layer."""

    processor_name: str = "tkgis.output.layer"
    input_type: None = None  # Accepts any data type
    output_type: None = None
    output_name: str = "Output Layer"

    @property
    def params(self) -> dict[str, Any]:
        return {"output_name": self.output_name}
