"""SpectralProfileChart — band-value line chart for a single pixel."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Sequence

import numpy as np
from matplotlib.figure import Figure

from tkgis.charts.base import BaseChart


@dataclass
class SpectralProfileData:
    """Data container for a spectral profile.

    Attributes
    ----------
    band_names:
        Labels for each band (e.g. ``["B1", "B2", ...]``).
    values:
        Per-band pixel values.  Length must match *band_names*.
    pixel_coords:
        Optional ``(row, col)`` of the source pixel.
    """

    band_names: Sequence[str]
    values: Sequence[float]
    pixel_coords: tuple[int, int] | None = None


class SpectralProfileChart(BaseChart):
    """Click-a-pixel spectral profile rendered as a line chart."""

    name: str = "spectral_profile"
    title: str = "Spectral Profile"

    def __init__(self) -> None:
        self._fig: Figure | None = None
        self._ax: Any = None

    def create_figure(self) -> Figure:
        fig = Figure(figsize=(5, 3), tight_layout=True)
        ax = fig.add_subplot(111)
        ax.set_xlabel("Band")
        ax.set_ylabel("Value")
        ax.set_title(self.title)
        self._fig = fig
        self._ax = ax
        return fig

    def update(self, data: SpectralProfileData) -> None:  # type: ignore[override]
        """Plot band values from *data*."""
        ax = self._ax
        ax.clear()

        x = np.arange(len(data.band_names))
        ax.plot(x, data.values, marker="o", linewidth=1.5)
        ax.set_xticks(x)
        ax.set_xticklabels(data.band_names, rotation=45, ha="right", fontsize=7)
        ax.set_xlabel("Band")
        ax.set_ylabel("Value")

        label = self.title
        if data.pixel_coords is not None:
            label += f"  (row={data.pixel_coords[0]}, col={data.pixel_coords[1]})"
        ax.set_title(label, fontsize=9)

        self._fig.canvas.draw_idle()  # type: ignore[union-attr]
