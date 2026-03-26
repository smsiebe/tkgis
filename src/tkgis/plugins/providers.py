"""DataProvider ABC and DataProviderRegistry."""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class DataProvider(ABC):
    """Abstract base for file-format data providers.

    Each provider declares the file extensions and modalities it supports and
    knows how to open files into Layer objects.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique provider identifier."""
        ...

    @property
    @abstractmethod
    def supported_extensions(self) -> list[str]:
        """Lowercase file extensions *without* leading dot (e.g. ``['shp', 'geojson']``)."""
        ...

    @property
    @abstractmethod
    def supported_modalities(self) -> list[str]:
        """Data modalities: ``'vector'``, ``'raster'``, or both."""
        ...

    @abstractmethod
    def can_open(self, path: Path) -> bool:
        """Return True if this provider can handle *path*."""
        ...

    @abstractmethod
    def open(self, path: Path) -> Any:
        """Open *path* and return a Layer (defined in TG3)."""
        ...

    @abstractmethod
    def get_file_filter(self) -> str:
        """Return a file-dialog filter string, e.g. ``'Shapefiles (*.shp)'``."""
        ...


class DataProviderRegistry:
    """Central registry that routes file-open requests to the correct provider."""

    def __init__(self) -> None:
        self._providers: list[DataProvider] = []

    def register(self, provider: DataProvider) -> None:
        """Register a DataProvider.  Duplicates (by name) are silently ignored."""
        if any(p.name == provider.name for p in self._providers):
            logger.warning("DataProvider '%s' already registered; skipping", provider.name)
            return
        self._providers.append(provider)
        logger.debug("DataProvider registered: %s", provider.name)

    def find_provider(self, path: Path) -> DataProvider | None:
        """Return the first registered provider that can open *path*, or None."""
        for provider in self._providers:
            try:
                if provider.can_open(path):
                    return provider
            except Exception:
                logger.exception(
                    "Error checking provider '%s' for path %s", provider.name, path
                )
        return None

    def open_file(self, path: Path) -> Any:
        """Open *path* using the first matching provider.

        Raises ``ValueError`` if no provider can handle the file.
        """
        provider = self.find_provider(path)
        if provider is None:
            raise ValueError(f"No data provider found for: {path}")
        return provider.open(path)

    def get_all_filters(self) -> str:
        """Concatenate all provider file-dialog filters, separated by ``;;``."""
        filters = [p.get_file_filter() for p in self._providers]
        return ";;".join(filters)

    @property
    def providers(self) -> list[DataProvider]:
        """Return a snapshot of registered providers."""
        return list(self._providers)
