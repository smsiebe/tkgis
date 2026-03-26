"""ChartPanel — tabbed chart container docked at the bottom."""
from __future__ import annotations

from typing import Any

import customtkinter as ctk

from tkgis.charts.base import BaseChart
from tkgis.charts.container import ChartContainer
from tkgis.panels.base import BasePanel


class ChartPanel(BasePanel):
    """Bottom-docked panel that hosts multiple charts in tabs.

    Each chart is wrapped in a :class:`ChartContainer` and added to a
    ``CTkTabview``.  Charts can be added dynamically via :meth:`add_chart`.
    """

    name: str = "charts"
    title: str = "Charts"
    dock_position: str = "bottom"
    default_visible: bool = False

    def __init__(self) -> None:
        super().__init__()
        self._tabview: ctk.CTkTabview | None = None
        self._containers: dict[str, ChartContainer] = {}

    def create_widget(self, parent: Any) -> ctk.CTkFrame:
        """Build the tabbed chart frame."""
        frame = ctk.CTkFrame(parent)
        self._tabview = ctk.CTkTabview(frame)
        self._tabview.pack(fill="both", expand=True, padx=4, pady=4)
        self._widget = frame
        return frame

    def add_chart(self, chart: BaseChart) -> ChartContainer:
        """Add a chart tab and return its :class:`ChartContainer`.

        If a chart with the same *name* already exists the existing
        container is returned without creating a duplicate tab.
        """
        if chart.name in self._containers:
            return self._containers[chart.name]

        assert self._tabview is not None, "create_widget() must be called first"
        self._tabview.add(chart.title)
        tab_frame = self._tabview.tab(chart.title)

        container = ChartContainer(tab_frame, chart)
        container.pack(fill="both", expand=True)
        self._containers[chart.name] = container
        return container

    def get_container(self, chart_name: str) -> ChartContainer | None:
        """Return the container for *chart_name*, or ``None``."""
        return self._containers.get(chart_name)
