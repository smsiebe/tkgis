"""Singleton registry for dockable panels."""
from __future__ import annotations

import logging
from typing import Iterator

from tkgis.panels.base import BasePanel

logger = logging.getLogger(__name__)


class PanelRegistry:
    """Central catalogue of available panels.

    Acts as a singleton-style dict of ``name -> BasePanel``.
    """

    def __init__(self) -> None:
        self._panels: dict[str, BasePanel] = {}

    # -- mutation -------------------------------------------------------------

    def register(self, panel: BasePanel) -> None:
        """Register a panel instance.  Overwrites if name already exists."""
        self._panels[panel.name] = panel
        logger.debug("Panel registered: %s (%s)", panel.name, panel.dock_position)

    def unregister(self, name: str) -> None:
        """Remove a panel by name."""
        self._panels.pop(name, None)

    # -- queries --------------------------------------------------------------

    def get(self, name: str) -> BasePanel | None:
        """Return the panel with *name*, or ``None``."""
        return self._panels.get(name)

    def list_panels(self, dock_position: str | None = None) -> list[BasePanel]:
        """Return panels, optionally filtered by dock position."""
        if dock_position is None:
            return list(self._panels.values())
        return [p for p in self._panels.values() if p.dock_position == dock_position]

    def toggle(self, name: str) -> bool:
        """Toggle visibility of panel *name*.  Returns new visibility state."""
        panel = self._panels.get(name)
        if panel is None:
            logger.warning("Cannot toggle unknown panel: %s", name)
            return False
        panel.visible = not panel.visible
        logger.debug("Panel %s toggled to %s", name, panel.visible)
        return panel.visible

    # -- dunder helpers -------------------------------------------------------

    def __contains__(self, name: str) -> bool:
        return name in self._panels

    def __len__(self) -> int:
        return len(self._panels)

    def __iter__(self) -> Iterator[str]:
        return iter(self._panels)
