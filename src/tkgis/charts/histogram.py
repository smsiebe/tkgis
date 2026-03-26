"""HistogramChart — value distribution for a raster band or vector attribute."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

import numpy as np
from matplotlib.figure import Figure

from tkgis.charts.base import BaseChart


@dataclass
class HistogramData:
    """Data container for a histogram.

    Attributes
    ----------
    values:
        1-D array of numeric values to bin.
    label:
        Descriptive label for the data (band name, attribute name, …).
    bins:
        Number of bins.  Defaults to 64.
    """

    values: Sequence[float]
    label: str = ""
    bins: int = 64


class HistogramChart(BaseChart):
    """Value-distribution histogram."""

    name: str = "histogram"
    title: str = "Histogram"

    def __init__(self) -> None:
        self._fig: Figure | None = None
        self._ax: Any = None

    def create_figure(self) -> Figure:
        fig = Figure(figsize=(5, 3), tight_layout=True)
        ax = fig.add_subplot(111)
        ax.set_xlabel("Value")
        ax.set_ylabel("Frequency")
        ax.set_title(self.title)
        self._fig = fig
        self._ax = ax
        return fig

    def update(self, data: HistogramData) -> None:  # type: ignore[override]
        """Recompute and draw the histogram from *data*."""
        ax = self._ax
        ax.clear()

        arr = np.asarray(data.values, dtype=float)
        # Drop NaN / inf
        arr = arr[np.isfinite(arr)]

        ax.hist(arr, bins=data.bins, edgecolor="black", linewidth=0.4)
        ax.set_xlabel("Value")
        ax.set_ylabel("Frequency")
        title = self.title
        if data.label:
            title += f" — {data.label}"
        ax.set_title(title, fontsize=9)

        self._fig.canvas.draw_idle()  # type: ignore[union-attr]
