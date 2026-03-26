"""Abstract base class for all chart types."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from matplotlib.figure import Figure


class BaseChart(ABC):
    """Abstract base for embeddable matplotlib charts.

    Subclasses must set *name* and *title* and implement
    :meth:`create_figure` and :meth:`update`.
    """

    name: str
    title: str

    @abstractmethod
    def create_figure(self) -> Figure:
        """Build and return the initial matplotlib Figure."""
        ...

    @abstractmethod
    def update(self, data: Any) -> None:
        """Refresh the chart with new *data*."""
        ...

    def set_theme(self, dark: bool) -> None:
        """Apply a light or dark colour scheme to the figure.

        Subclasses may override for custom theming; the default
        implementation sets background and text colours on the
        existing figure.
        """
        fig = getattr(self, "_fig", None)
        if fig is None:
            return

        bg = "#2b2b2b" if dark else "#ffffff"
        fg = "#e0e0e0" if dark else "#000000"

        fig.patch.set_facecolor(bg)
        for ax in fig.axes:
            ax.set_facecolor(bg)
            ax.tick_params(colors=fg)
            ax.xaxis.label.set_color(fg)
            ax.yaxis.label.set_color(fg)
            ax.title.set_color(fg)
            for spine in ax.spines.values():
                spine.set_edgecolor(fg)

        fig.canvas.draw_idle()
