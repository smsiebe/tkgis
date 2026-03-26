"""Application-wide constants."""
from __future__ import annotations

APP_NAME: str = "tkgis"
VERSION: str = "0.1.0"

# Default window geometry
DEFAULT_WIDTH: int = 1600
DEFAULT_HEIGHT: int = 900

# Panel default sizes
LEFT_PANEL_WIDTH: int = 280
RIGHT_PANEL_WIDTH: int = 300
BOTTOM_PANEL_HEIGHT: int = 200
STATUS_BAR_HEIGHT: int = 28

# Default theme
DEFAULT_THEME: str = "dark"

# Config directory name (under user home)
CONFIG_DIR_NAME: str = ".tkgis"
CONFIG_FILE_NAME: str = "config.json"

# Default CRS
DEFAULT_CRS: str = "EPSG:4326"
