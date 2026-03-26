"""PluginManager — lifecycle management for tkgis plugins."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from tkgis.plugins.base import PluginContext, TkGISPlugin
from tkgis.plugins.discovery import discover_all
from tkgis.plugins.manifest import PluginManifest

logger = logging.getLogger(__name__)

_STATE_FILE = Path.home() / ".tkgis" / "plugins.json"


class PluginManager:
    """Discovers, loads, activates, and deactivates plugins.

    Enabled/disabled state is persisted in ``~/.tkgis/plugins.json``.
    """

    def __init__(self, context: PluginContext | None = None) -> None:
        self._context = context or PluginContext()
        self._plugins: dict[str, TkGISPlugin] = {}
        self._active: set[str] = set()
        self._state: dict[str, bool] = self._load_state()

    # -- public API -----------------------------------------------------------

    def load_all(self) -> None:
        """Discover and register all available plugins."""
        for plugin in discover_all():
            name = plugin.manifest.name
            self._plugins[name] = plugin
            # Auto-activate if state says enabled (default: enabled)
            if self._state.get(name, True):
                self.activate(name)

    def activate(self, name: str) -> None:
        """Activate a plugin by name.  Activates dependencies first."""
        if name in self._active:
            return
        plugin = self._plugins.get(name)
        if plugin is None:
            logger.warning("Cannot activate unknown plugin '%s'", name)
            return

        # Dependency resolution: activate dependencies first
        for dep in plugin.manifest.dependencies:
            if dep not in self._active:
                if dep in self._plugins:
                    self.activate(dep)
                else:
                    logger.error(
                        "Plugin '%s' depends on '%s' which is not available", name, dep
                    )
                    return

        try:
            plugin.activate(self._context)
            self._active.add(name)
            self._state[name] = True
            self._persist_state()
            logger.info("Activated plugin '%s'", name)
        except Exception:
            logger.exception("Failed to activate plugin '%s'", name)

    def deactivate(self, name: str) -> None:
        """Deactivate a plugin by name."""
        if name not in self._active:
            return
        plugin = self._plugins.get(name)
        if plugin is None:
            return
        try:
            plugin.deactivate()
        except Exception:
            logger.exception("Error during deactivation of plugin '%s'", name)
        finally:
            self._active.discard(name)
            self._state[name] = False
            self._persist_state()
            logger.info("Deactivated plugin '%s'", name)

    def is_enabled(self, name: str) -> bool:
        """Return True if the plugin is currently active."""
        return name in self._active

    def list_plugins(self) -> list[PluginManifest]:
        """Return manifests for all discovered plugins."""
        return [p.manifest for p in self._plugins.values()]

    def get_context(self) -> PluginContext:
        """Return the shared PluginContext."""
        return self._context

    # -- persistence ----------------------------------------------------------

    @staticmethod
    def _load_state() -> dict[str, bool]:
        """Load enabled/disabled map from disk."""
        try:
            if _STATE_FILE.exists():
                with _STATE_FILE.open("r", encoding="utf-8") as fh:
                    data: Any = json.load(fh)
                if isinstance(data, dict):
                    return {k: bool(v) for k, v in data.items()}
        except Exception:
            logger.exception("Failed to read plugin state from %s", _STATE_FILE)
        return {}

    def _persist_state(self) -> None:
        """Write enabled/disabled map to disk."""
        try:
            _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            with _STATE_FILE.open("w", encoding="utf-8") as fh:
                json.dump(self._state, fh, indent=2)
        except Exception:
            logger.exception("Failed to persist plugin state to %s", _STATE_FILE)
