"""TemporalRasterStack — ordered collection of time-indexed raster layers."""
from __future__ import annotations

import glob
import logging
import os
import re
from datetime import datetime
from typing import TYPE_CHECKING

import numpy as np

from tkgis.models.layers import Layer, LayerType

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Common filename date patterns, tried in order.
_DATE_PATTERNS: list[tuple[str, str]] = [
    # 20210315T120000
    (r"(\d{4}\d{2}\d{2}T\d{6})", "%Y%m%dT%H%M%S"),
    # 2021-03-15T12:00:00
    (r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})", "%Y-%m-%dT%H:%M:%S"),
    # 2021-03-15
    (r"(\d{4}-\d{2}-\d{2})", "%Y-%m-%d"),
    # 20210315
    (r"(\d{8})", "%Y%m%d"),
]


def _extract_datetime_from_filename(path: str) -> datetime | None:
    """Try to extract a datetime from the file's basename."""
    basename = os.path.basename(path)
    for regex, fmt in _DATE_PATTERNS:
        m = re.search(regex, basename)
        if m:
            try:
                return datetime.strptime(m.group(1), fmt)
            except ValueError:
                continue
    return None


class TemporalRasterStack:
    """An ordered stack of raster :class:`Layer` objects indexed by time.

    Layers are sorted by ``time_start`` on construction.  Layers without
    temporal metadata are rejected.

    Parameters
    ----------
    layers:
        Sequence of :class:`Layer` objects that each have ``time_start`` set.
    """

    def __init__(self, layers: list[Layer]) -> None:
        # Validate: every layer must have a time_start.
        for lyr in layers:
            if lyr.time_start is None:
                raise ValueError(
                    f"Layer '{lyr.name}' has no time_start; "
                    "cannot include in TemporalRasterStack"
                )

        self._layers: list[Layer] = sorted(
            layers, key=lambda lyr: datetime.fromisoformat(lyr.time_start)  # type: ignore[arg-type]
        )
        self._times: list[datetime] = [
            datetime.fromisoformat(lyr.time_start) for lyr in self._layers  # type: ignore[arg-type]
        ]

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def layers(self) -> list[Layer]:
        """The time-sorted list of layers."""
        return list(self._layers)

    @property
    def times(self) -> list[datetime]:
        """Sorted datetime list, one per layer."""
        return list(self._times)

    def __len__(self) -> int:
        return len(self._layers)

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def from_directory(
        cls,
        directory: str,
        pattern: str = "*.tif",
    ) -> TemporalRasterStack:
        """Build a stack by scanning *directory* for files matching *pattern*.

        Datetime is extracted from each filename.  Files whose names do
        not contain a recognisable date are skipped with a warning.
        """
        search = os.path.join(directory, pattern)
        paths = sorted(glob.glob(search))
        if not paths:
            raise FileNotFoundError(
                f"No files matching '{pattern}' in {directory}"
            )

        layers: list[Layer] = []
        for path in paths:
            dt = _extract_datetime_from_filename(path)
            if dt is None:
                logger.warning("Skipping %s — no date in filename", path)
                continue
            lyr = Layer(
                name=os.path.basename(path),
                layer_type=LayerType.TEMPORAL_RASTER,
                source_path=path,
                time_start=dt.isoformat(),
                time_end=dt.isoformat(),
            )
            layers.append(lyr)

        if not layers:
            raise ValueError(
                f"No files in {directory} had a recognisable date in their name"
            )
        return cls(layers)

    # ------------------------------------------------------------------
    # Access
    # ------------------------------------------------------------------

    def get_frame_at_time(self, t: datetime) -> Layer:
        """Return the layer whose time is closest to *t*.

        Parameters
        ----------
        t:
            Target datetime.

        Returns
        -------
        Layer
            The closest layer by absolute time difference.
        """
        if not self._layers:
            raise ValueError("Stack is empty")

        best_idx = 0
        best_delta = abs(self._times[0] - t)
        for i in range(1, len(self._times)):
            delta = abs(self._times[i] - t)
            if delta < best_delta:
                best_delta = delta
                best_idx = i
        return self._layers[best_idx]

    def get_time_series_at_pixel(self, row: int, col: int) -> np.ndarray:
        """Extract the value at ``(row, col)`` across all frames.

        This reads band 1 from each layer's source file using rasterio
        if available, otherwise returns an array of NaN.

        Returns
        -------
        numpy.ndarray
            1-D float64 array of length ``len(self)``.
        """
        values = np.full(len(self._layers), np.nan, dtype=np.float64)
        try:
            import rasterio  # type: ignore[import-untyped]
        except ImportError:
            logger.warning(
                "rasterio not installed — returning NaN for pixel time series"
            )
            return values

        for i, lyr in enumerate(self._layers):
            if lyr.source_path is None:
                continue
            try:
                with rasterio.open(lyr.source_path) as ds:
                    win = rasterio.windows.Window(col, row, 1, 1)
                    data = ds.read(1, window=win)
                    values[i] = float(data[0, 0])
            except Exception:
                logger.debug(
                    "Could not read pixel (%d,%d) from %s",
                    row,
                    col,
                    lyr.source_path,
                    exc_info=True,
                )
        return values
