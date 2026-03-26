"""ScatterPlotChart — two-variable comparison."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

import numpy as np
from matplotlib.figure import Figure

from tkgis.charts.base import BaseChart


@dataclass
class ScatterData:
    """Data container for a scatter plot.

    Attributes
    ----------
    x:
        Values for the horizontal axis.
    y:
        Values for the vertical axis.
    x_label:
        Axis label for *x*.
    y_label:
        Axis label for *y*.
    """

    x: Sequence[float]
    y: Sequence[float]
    x_label: str = "X"
    y_label: str = "Y"


class ScatterPlotChart(BaseChart):
    """Two-variable scatter plot."""

    name: str = "scatter"
    title: str = "Scatter Plot"

    def __init__(self) -> None:
        self._fig: Figure | None = None
        self._ax: Any = None

    def create_figure(self) -> Figure:
        fig = Figure(figsize=(5, 4), tight_layout=True)
        ax = fig.add_subplot(111)
        ax.set_xlabel("X")
        ax.set_ylabel("Y")
        ax.set_title(self.title)
        self._fig = fig
        self._ax = ax
        return fig

    def update(self, data: ScatterData) -> None:  # type: ignore[override]
        """Redraw the scatter plot with *data*."""
        ax = self._ax
        ax.clear()

        ax.scatter(np.asarray(data.x), np.asarray(data.y), s=12, alpha=0.7)
        ax.set_xlabel(data.x_label)
        ax.set_ylabel(data.y_label)
        ax.set_title(self.title, fontsize=9)

        self._fig.canvas.draw_idle()  # type: ignore[union-attr]
