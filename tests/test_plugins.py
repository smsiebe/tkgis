"""Tests for the tkgis plugin system."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tkgis.plugins.base import PluginContext, TkGISPlugin
from tkgis.plugins.discovery import discover_all, discover_builtin
from tkgis.plugins.manager import PluginManager
from tkgis.plugins.manifest import PluginManifest
from tkgis.plugins.providers import DataProvider, DataProviderRegistry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_manifest(
    name: str = "test-plugin",
    *,
    dependencies: list[str] | None = None,
) -> PluginManifest:
    return PluginManifest(
        name=name,
        display_name=name.replace("-", " ").title(),
        version="1.0.0",
        description="A test plugin",
        author="Test Author",
        license="MIT",
        dependencies=dependencies or [],
    )


class DummyPlugin(TkGISPlugin):
    """Minimal concrete plugin for testing."""

    def __init__(
        self,
        name: str = "dummy",
        *,
        dependencies: list[str] | None = None,
        fail_on_activate: bool = False,
    ) -> None:
        self._manifest = _make_manifest(name, dependencies=dependencies)
        self._activated = False
        self._deactivated = False
        self._fail_on_activate = fail_on_activate

    @property
    def manifest(self) -> PluginManifest:
        return self._manifest

    def activate(self, context: PluginContext) -> None:
        if self._fail_on_activate:
            raise RuntimeError("Intentional failure in activate()")
        self._activated = True

    def deactivate(self) -> None:
        self._deactivated = True


class StubDataProvider(DataProvider):
    """Concrete DataProvider for testing."""

    @property
    def name(self) -> str:
        return "stub"

    @property
    def supported_extensions(self) -> list[str]:
        return ["shp", "geojson"]

    @property
    def supported_modalities(self) -> list[str]:
        return ["vector"]

    def can_open(self, path: Path) -> bool:
        return path.suffix.lstrip(".").lower() in self.supported_extensions

    def open(self, path: Path) -> str:
        return f"opened:{path.name}"

    def get_file_filter(self) -> str:
        return "Vector files (*.shp *.geojson)"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestPluginManifest:
    def test_plugin_manifest_creation(self) -> None:
        m = _make_manifest()
        assert m.name == "test-plugin"
        assert m.display_name == "Test Plugin"
        assert m.version == "1.0.0"
        assert m.license == "MIT"
        assert m.min_tkgis_version == "0.1.0"
        assert m.capabilities == []
        assert m.dependencies == []

    def test_manifest_rejects_empty_name(self) -> None:
        with pytest.raises(ValueError, match="name"):
            PluginManifest(
                name="",
                display_name="X",
                version="1.0.0",
                description="x",
                author="x",
                license="MIT",
            )

    def test_manifest_rejects_empty_version(self) -> None:
        with pytest.raises(ValueError, match="version"):
            PluginManifest(
                name="x",
                display_name="X",
                version="",
                description="x",
                author="x",
                license="MIT",
            )


class TestDiscovery:
    def test_plugin_discovery_builtin(self) -> None:
        """Builtin discovery finds the shipped vector and raster provider plugins."""
        plugins = discover_builtin()
        assert isinstance(plugins, list)
        assert len(plugins) == 2
        names = {p.manifest.name for p in plugins}
        assert "vector-provider" in names
        assert "grdl-raster" in names

    def test_discover_all_does_not_crash(self) -> None:
        """discover_all must never raise, even if a vector fails."""
        plugins = discover_all()
        assert isinstance(plugins, list)


class TestPluginLifecycle:
    def test_plugin_activate_deactivate(self) -> None:
        ctx = PluginContext()
        mgr = PluginManager(context=ctx)

        plugin = DummyPlugin(name="lifecycle-test")
        mgr._plugins["lifecycle-test"] = plugin

        mgr.activate("lifecycle-test")
        assert mgr.is_enabled("lifecycle-test")
        assert plugin._activated

        mgr.deactivate("lifecycle-test")
        assert not mgr.is_enabled("lifecycle-test")
        assert plugin._deactivated

    def test_plugin_failure_isolation(self) -> None:
        """A plugin that raises during activate must not crash the manager."""
        ctx = PluginContext()
        mgr = PluginManager(context=ctx)

        bad = DummyPlugin(name="bad-plugin", fail_on_activate=True)
        good = DummyPlugin(name="good-plugin")
        mgr._plugins["bad-plugin"] = bad
        mgr._plugins["good-plugin"] = good

        # Activating the bad plugin should not raise
        mgr.activate("bad-plugin")
        assert not mgr.is_enabled("bad-plugin")

        # Good plugin should still activate fine
        mgr.activate("good-plugin")
        assert mgr.is_enabled("good-plugin")

    def test_dependency_resolution(self) -> None:
        """Activating a plugin should first activate its dependencies."""
        ctx = PluginContext()
        mgr = PluginManager(context=ctx)

        dep = DummyPlugin(name="dep-plugin")
        child = DummyPlugin(name="child-plugin", dependencies=["dep-plugin"])

        mgr._plugins["dep-plugin"] = dep
        mgr._plugins["child-plugin"] = child

        # Activate child — dep should be activated automatically
        mgr.activate("child-plugin")

        assert mgr.is_enabled("dep-plugin"), "Dependency should be activated first"
        assert mgr.is_enabled("child-plugin")
        assert dep._activated
        assert child._activated

    def test_list_plugins(self) -> None:
        mgr = PluginManager()
        p = DummyPlugin(name="list-test")
        mgr._plugins["list-test"] = p

        manifests = mgr.list_plugins()
        assert len(manifests) == 1
        assert manifests[0].name == "list-test"


class TestDataProviderRegistry:
    def test_data_provider_registry_register_and_find(self) -> None:
        registry = DataProviderRegistry()
        provider = StubDataProvider()
        registry.register(provider)

        shp_path = Path("test.shp")
        found = registry.find_provider(shp_path)
        assert found is not None
        assert found.name == "stub"

        result = registry.open_file(shp_path)
        assert result == "opened:test.shp"

    def test_registry_returns_none_for_unknown(self) -> None:
        registry = DataProviderRegistry()
        provider = StubDataProvider()
        registry.register(provider)

        assert registry.find_provider(Path("photo.png")) is None

    def test_registry_open_file_raises_for_unknown(self) -> None:
        registry = DataProviderRegistry()
        with pytest.raises(ValueError, match="No data provider"):
            registry.open_file(Path("unknown.xyz"))

    def test_registry_get_all_filters(self) -> None:
        registry = DataProviderRegistry()
        registry.register(StubDataProvider())
        filters = registry.get_all_filters()
        assert "*.shp" in filters

    def test_registry_ignores_duplicate(self) -> None:
        registry = DataProviderRegistry()
        registry.register(StubDataProvider())
        registry.register(StubDataProvider())
        assert len(registry.providers) == 1
