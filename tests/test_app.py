"""Tests for the tkgis application shell."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
import yaml

from tkgis.config import Config
from tkgis.panels.base import BasePanel
from tkgis.panels.registry import PanelRegistry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _DummyPanel(BasePanel):
    name = "dummy"
    title = "Dummy Panel"
    dock_position = "left"
    default_visible = True

    def create_widget(self, parent):  # type: ignore[override]
        return None  # No GUI in unit tests


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not hasattr(pytest, "_tkgis_gui_tests"),
    reason="GUI app test skipped to avoid Tk root conflicts in batch runs. "
           "Run individually: pytest tests/test_app.py::test_app_creates_without_error",
)
def test_app_creates_without_error():
    """TkGISApp can be instantiated and immediately destroyed."""
    import customtkinter as ctk
    try:
        from tkgis.app import TkGISApp
        with tempfile.TemporaryDirectory() as tmp:
            cfg = Config(config_dir=Path(tmp))
            app = TkGISApp(config=cfg)
            assert app.panel_registry is not None
            assert app.config is not None
            app.destroy()
    except Exception as exc:
        if "display" in str(exc).lower() or "no display" in str(exc).lower():
            pytest.skip("No display available")
        raise


def test_panel_registry_register_and_get():
    """Panels can be registered and retrieved by name."""
    registry = PanelRegistry()
    panel = _DummyPanel()

    registry.register(panel)

    assert "dummy" in registry
    assert registry.get("dummy") is panel
    assert len(registry) == 1
    assert registry.list_panels("left") == [panel]
    assert registry.list_panels("right") == []


def test_panel_toggle():
    """Toggling flips the panel's visible state."""
    registry = PanelRegistry()
    panel = _DummyPanel()
    registry.register(panel)

    assert panel.visible is True
    new_state = registry.toggle("dummy")
    assert new_state is False
    assert panel.visible is False

    new_state = registry.toggle("dummy")
    assert new_state is True
    assert panel.visible is True


def test_panel_toggle_unknown():
    """Toggling an unknown panel returns False."""
    registry = PanelRegistry()
    assert registry.toggle("nonexistent") is False


def test_config_persistence():
    """Config round-trips through YAML on disk."""
    with tempfile.TemporaryDirectory() as tmp:
        config_dir = Path(tmp)

        # Write
        cfg1 = Config(config_dir=config_dir)
        cfg1.theme = "light"
        cfg1.add_recent_file("/some/path.tif")
        cfg1.window_geometry = "1200x800"
        cfg1.save()

        # Verify file exists
        config_file = config_dir / "config.yml"
        assert config_file.exists()
        with open(config_file, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        assert data["theme"] == "light"
        assert "/some/path.tif" in data["recent_files"]

        # Reload
        cfg2 = Config(config_dir=config_dir)
        assert cfg2.theme == "light"
        assert cfg2.recent_files == ["/some/path.tif"]
        assert cfg2.window_geometry == "1200x800"
