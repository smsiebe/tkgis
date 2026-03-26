"""Raster test fixtures — creates a small GeoTIFF for testing."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest


FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def test_raster_tif() -> Path:
    """Create a 100x100, 3-band uint8 GeoTIFF with EPSG:4326."""
    import rasterio
    from rasterio.transform import from_bounds

    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    tif_path = FIXTURES_DIR / "test_raster.tif"

    if tif_path.exists():
        return tif_path

    rng = np.random.default_rng(42)
    data = rng.integers(0, 256, size=(3, 100, 100), dtype=np.uint8)

    transform = from_bounds(-77.5, 38.5, -77.0, 39.0, 100, 100)

    with rasterio.open(
        str(tif_path),
        "w",
        driver="GTiff",
        height=100,
        width=100,
        count=3,
        dtype="uint8",
        crs="EPSG:4326",
        transform=transform,
    ) as dst:
        dst.write(data)

    return tif_path
