"""tkgis domain models — pure Python, no GUI dependencies."""
from __future__ import annotations

from tkgis.models.crs import CRSDefinition
from tkgis.models.events import EventBus, EventType
from tkgis.models.geometry import BoundingBox
from tkgis.models.layers import Layer, LayerStyle, LayerType
from tkgis.models.project import MapView, Project
from tkgis.models.tools import BaseTool, ToolManager, ToolMode

__all__ = [
    "BoundingBox",
    "CRSDefinition",
    "EventBus",
    "EventType",
    "Layer",
    "LayerStyle",
    "LayerType",
    "MapView",
    "Project",
    "BaseTool",
    "ToolManager",
    "ToolMode",
]
