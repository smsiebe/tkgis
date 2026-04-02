"""Application configuration — reads/writes ``~/.tkgis/config.json``."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

from tkgis.constants import (
    CONFIG_DIR_NAME,
    CONFIG_FILE_NAME,
    DEFAULT_CRS,
    DEFAULT_HEIGHT,
    DEFAULT_THEME,
    DEFAULT_WIDTH,
)

logger = logging.getLogger(__name__)

_DEFAULTS: dict[str, Any] = {
    "theme": DEFAULT_THEME,
    "recent_files": [],
    "window_geometry": f"{DEFAULT_WIDTH}x{DEFAULT_HEIGHT}",
    "default_crs": DEFAULT_CRS,
}


class Config:
    """Manages persistent application settings stored as YAML."""

    def __init__(self, config_dir: Path | None = None) -> None:
        if config_dir is None:
            config_dir = Path.home() / CONFIG_DIR_NAME
        self._config_dir = config_dir
        self._config_path = config_dir / CONFIG_FILE_NAME
        self._data: dict[str, Any] = dict(_DEFAULTS)
        self.load()

    # -- persistence ----------------------------------------------------------

    def load(self) -> None:
        """Load settings from disk, falling back to defaults."""
        if self._config_path.exists():
            try:
                with open(self._config_path, "r", encoding="utf-8") as fh:
                    stored = yaml.safe_load(fh)
                if isinstance(stored, dict):
                    self._data.update(stored)
                logger.debug("Config loaded from %s", self._config_path)
            except (yaml.YAMLError, OSError) as exc:
                logger.warning("Failed to load config: %s", exc)
        else:
            logger.debug("No config file found; using defaults.")

    def save(self) -> None:
        """Persist current settings to disk."""
        try:
            self._config_dir.mkdir(parents=True, exist_ok=True)
            with open(self._config_path, "w", encoding="utf-8") as fh:
                yaml.safe_dump(self._data, fh, default_flow_style=False, sort_keys=False)
            logger.debug("Config saved to %s", self._config_path)
        except OSError as exc:
            logger.warning("Failed to save config: %s", exc)

    # -- accessors ------------------------------------------------------------

    @property
    def theme(self) -> str:
        return self._data.get("theme", DEFAULT_THEME)

    @theme.setter
    def theme(self, value: str) -> None:
        self._data["theme"] = value

    @property
    def recent_files(self) -> list[str]:
        return list(self._data.get("recent_files", []))

    def add_recent_file(self, path: str, max_recent: int = 10) -> None:
        files = self.recent_files
        if path in files:
            files.remove(path)
        files.insert(0, path)
        self._data["recent_files"] = files[:max_recent]

    @property
    def window_geometry(self) -> str:
        return self._data.get("window_geometry", f"{DEFAULT_WIDTH}x{DEFAULT_HEIGHT}")

    @window_geometry.setter
    def window_geometry(self, value: str) -> None:
        self._data["window_geometry"] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value
