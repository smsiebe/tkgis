"""ChartContainer — embeds a matplotlib Figure in a tkinter frame."""
from __future__ import annotations

from typing import Any

import customtkinter as ctk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

from tkgis.charts.base import BaseChart


class ChartContainer(ctk.CTkFrame):
    """Wraps a :class:`BaseChart` with a matplotlib canvas and toolbar.

    Parameters
    ----------
    parent:
        The tkinter parent widget.
    chart:
        A concrete :class:`BaseChart` instance whose figure will be
        embedded inside this frame.
    """

    def __init__(self, parent: Any, chart: BaseChart, **kwargs: Any) -> None:
        super().__init__(parent, **kwargs)
        self._chart = chart
        self._fig = chart.create_figure()

        # Embed the matplotlib canvas
        self._canvas = FigureCanvasTkAgg(self._fig, master=self)
        self._canvas.draw()

        # Navigation toolbar (zoom, pan, save)
        self._toolbar = NavigationToolbar2Tk(self._canvas, self)
        self._toolbar.update()
        self._toolbar.pack(side="top", fill="x")

        self._canvas.get_tk_widget().pack(side="top", fill="both", expand=True)

    @property
    def chart(self) -> BaseChart:
        """The underlying chart instance."""
        return self._chart

    @property
    def figure_canvas(self) -> FigureCanvasTkAgg:
        """The matplotlib ``FigureCanvasTkAgg`` widget."""
        return self._canvas

    def refresh(self) -> None:
        """Redraw the embedded canvas after a chart update."""
        self._canvas.draw_idle()
