"""Plugin discovery — builtin, entry-point, and directory scanning."""
from __future__ import annotations

import importlib
import logging
import pkgutil
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tkgis.plugins.base import TkGISPlugin

logger = logging.getLogger(__name__)


def discover_builtin() -> list[TkGISPlugin]:
    """Scan ``tkgis.plugins.builtin`` for plugin classes.

    Each sub-module in the builtin package must expose a ``get_plugin()``
    factory that returns a :class:`TkGISPlugin` instance.
    """
    plugins: list[TkGISPlugin] = []
    try:
        import tkgis.plugins.builtin as builtin_pkg

        for importer, modname, _ispkg in pkgutil.iter_modules(builtin_pkg.__path__):
            try:
                mod = importlib.import_module(f"tkgis.plugins.builtin.{modname}")
                factory = getattr(mod, "get_plugin", None)
                if factory is not None:
                    plugin = factory()
                    plugins.append(plugin)
                    logger.info("Discovered builtin plugin: %s", modname)
                else:
                    logger.debug(
                        "Builtin module '%s' has no get_plugin(); skipped", modname
                    )
            except Exception:
                logger.exception("Failed to load builtin plugin module '%s'", modname)
    except Exception:
        logger.exception("Failed to scan builtin plugins package")
    return plugins


def discover_entrypoints() -> list[TkGISPlugin]:
    """Scan the ``tkgis.plugins`` entry-point group via importlib.metadata."""
    plugins: list[TkGISPlugin] = []
    try:
        from importlib.metadata import entry_points

        eps = entry_points()
        # Python 3.12+ returns SelectableGroups; 3.9-3.11 returns dict
        if isinstance(eps, dict):
            group = eps.get("tkgis.plugins", [])
        else:
            group = eps.select(group="tkgis.plugins")

        for ep in group:
            try:
                factory = ep.load()
                plugin = factory()
                plugins.append(plugin)
                logger.info("Discovered entry-point plugin: %s", ep.name)
            except Exception:
                logger.exception(
                    "Failed to load entry-point plugin '%s'", ep.name
                )
    except Exception:
        logger.exception("Failed to scan entry-point plugins")
    return plugins


def discover_directory(path: Path | None = None) -> list[TkGISPlugin]:
    """Scan a directory for plugin packages containing ``__plugin__.py``.

    Each ``__plugin__.py`` must expose ``get_plugin() -> TkGISPlugin``.
    Defaults to ``~/.tkgis/plugins/``.
    """
    if path is None:
        path = Path.home() / ".tkgis" / "plugins"

    plugins: list[TkGISPlugin] = []
    if not path.is_dir():
        logger.debug("Plugin directory does not exist: %s", path)
        return plugins

    try:
        for child in sorted(path.iterdir()):
            if not child.is_dir():
                continue
            plugin_file = child / "__plugin__.py"
            if not plugin_file.exists():
                continue
            try:
                import importlib.util

                spec = importlib.util.spec_from_file_location(
                    f"tkgis_ext_{child.name}", str(plugin_file)
                )
                if spec is None or spec.loader is None:
                    logger.warning("Cannot create module spec for %s", plugin_file)
                    continue
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                factory = getattr(mod, "get_plugin", None)
                if factory is not None:
                    plugin = factory()
                    plugins.append(plugin)
                    logger.info("Discovered directory plugin: %s", child.name)
                else:
                    logger.debug(
                        "Plugin dir '%s' __plugin__.py has no get_plugin()", child.name
                    )
            except Exception:
                logger.exception(
                    "Failed to load directory plugin '%s'", child.name
                )
    except Exception:
        logger.exception("Failed to scan plugin directory %s", path)
    return plugins


def discover_all() -> list[TkGISPlugin]:
    """Run all discovery vectors; merge results and deduplicate by name.

    The first plugin discovered for a given name wins.  Failures in any
    individual discovery vector are logged but never crash the application.
    """
    seen_names: set[str] = set()
    merged: list[TkGISPlugin] = []

    for label, func in [
        ("builtin", discover_builtin),
        ("entrypoints", discover_entrypoints),
        ("directory", discover_directory),
    ]:
        try:
            found = func()  # type: ignore[call-arg]
            for plugin in found:
                name = plugin.manifest.name
                if name in seen_names:
                    logger.info(
                        "Duplicate plugin '%s' from %s; skipped", name, label
                    )
                    continue
                seen_names.add(name)
                merged.append(plugin)
        except Exception:
            logger.exception("Discovery vector '%s' failed", label)

    logger.info("Plugin discovery complete: %d plugin(s) found", len(merged))
    return merged
