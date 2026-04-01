"""TkGISPlugin ABC and PluginContext facade."""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Callable

from tkgis.plugins.manifest import PluginManifest

logger = logging.getLogger(__name__)


class PluginContext:
    """Facade providing controlled access to tkgis internals.

    Passed to every plugin during activation.  Methods are safe to call even
    when the corresponding subsystem is not yet initialised — they will log a
    warning and silently succeed so that plugins loaded early in the boot
    sequence do not crash.
    """

    def __init__(self) -> None:
        self._panels: list[Any] = []
        self._tools: list[Any] = []
        self._menu_items: list[tuple[str, str, Callable[..., Any]]] = []
        # Lazy import to avoid circular dependency with providers module
        self._data_provider_registry: Any | None = None
        self._project: Any | None = None

    # -- properties ----------------------------------------------------------

    @property
    def project(self) -> Any:
        """Access the active tkgis Project."""
        return self._project

    @property
    def menu_items(self) -> list[tuple[str, str, Callable[..., Any]]]:
        """Return all registered plugin menu items."""
        return self._menu_items

    # -- registration helpers ------------------------------------------------

    def register_panel(self, panel: Any) -> None:
        """Register a dockable panel with the application."""
        self._panels.append(panel)
        logger.debug("Panel registered via PluginContext: %s", panel)

    def register_tool(self, tool: Any) -> None:
        """Register a map-interaction tool."""
        self._tools.append(tool)
        logger.debug("Tool registered via PluginContext: %s", tool)

    def add_menu_item(
        self, menu_path: str, label: str, callback: Callable[..., Any]
    ) -> None:
        """Add a menu entry (e.g. menu_path='File', label='Export KML')."""
        self._menu_items.append((menu_path, label, callback))
        logger.debug("Menu item registered: %s > %s", menu_path, label)

    def register_data_provider(self, provider: Any) -> None:
        """Register a DataProvider with the application-wide registry."""
        if self._data_provider_registry is not None:
            self._data_provider_registry.register(provider)
        else:
            logger.warning(
                "DataProviderRegistry not available; provider %s queued", provider
            )

    # -- wiring (called by PluginManager / App, not by plugins) ---------------

    def set_data_provider_registry(self, registry: Any) -> None:
        """Wire the live DataProviderRegistry (called during app bootstrap)."""
        self._data_provider_registry = registry

    def set_project(self, project: Any) -> None:
        """Wire the active Project (called during app bootstrap)."""
        self._project = project


class TkGISPlugin(ABC):
    """Base class for all tkgis plugins (built-in and third-party)."""

    @property
    @abstractmethod
    def manifest(self) -> PluginManifest:
        """Return the plugin's manifest."""
        ...

    @abstractmethod
    def activate(self, context: PluginContext) -> None:
        """Called when the plugin is enabled.

        Use *context* to register panels, tools, menu items, and data
        providers.
        """
        ...

    @abstractmethod
    def deactivate(self) -> None:
        """Called when the plugin is disabled.

        Clean up any resources acquired during activation.
        """
        ...
