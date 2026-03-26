"""TimeSeriesChart — values plotted over time with datetime x-axis."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Sequence

import matplotlib.dates as mdates
import numpy as np
from matplotlib.figure import Figure

from tkgis.charts.base import BaseChart


@dataclass
class TimeSeriesData:
    """Data container for a time-series chart.

    Attributes
    ----------
    timestamps:
        Sequence of datetime objects for the x-axis.
    values:
        Corresponding numeric values.
    label:
        Series label shown in the legend.
    """

    timestamps: Sequence[datetime]
    values: Sequence[float]
    label: str = ""


class TimeSeriesChart(BaseChart):
    """Line chart with a datetime x-axis."""

    name: str = "time_series"
    title: str = "Time Series"

    def __init__(self) -> None:
        self._fig: Figure | None = None
        self._ax: Any = None

    def create_figure(self) -> Figure:
        fig = Figure(figsize=(6, 3), tight_layout=True)
        ax = fig.add_subplot(111)
        ax.set_xlabel("Time")
        ax.set_ylabel("Value")
        ax.set_title(self.title)
        self._fig = fig
        self._ax = ax
        return fig

    def update(self, data: TimeSeriesData) -> None:  # type: ignore[override]
        """Plot the time series from *data*."""
        ax = self._ax
        ax.clear()

        ax.plot(data.timestamps, np.asarray(data.values), marker=".", linewidth=1.2,
                label=data.label or None)
        ax.set_xlabel("Time")
        ax.set_ylabel("Value")
        ax.set_title(self.title, fontsize=9)

        # Auto-format datetime ticks
        ax.xaxis.set_major_formatter(mdates.AutoDateFormatter(mdates.AutoDateLocator()))
        fig = self._fig
        assert fig is not None
        fig.autofmt_xdate()

        if data.label:
            ax.legend(fontsize=7)

        fig.canvas.draw_idle()
