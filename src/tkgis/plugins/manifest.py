"""Plugin manifest — metadata describing a tkgis plugin."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PluginManifest:
    """Immutable descriptor for a tkgis plugin.

    Every plugin must declare a manifest so the plugin manager can inspect
    metadata *before* activation (display name, version, capabilities, etc.).
    """

    name: str  # Unique identifier (e.g. "vector-provider")
    display_name: str  # Human-readable label
    version: str  # Semantic version string
    description: str
    author: str
    license: str  # Must be MIT-compatible
    min_tkgis_version: str = "0.1.0"
    capabilities: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("PluginManifest.name must not be empty")
        if not self.version:
            raise ValueError("PluginManifest.version must not be empty")
