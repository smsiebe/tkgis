"""Status bar widget for the main application."""
from __future__ import annotations

import customtkinter as ctk
from typing import Any

from tkgis.constants import STATUS_BAR_HEIGHT


class StatusBarWidget(ctk.CTkFrame):
    """Bottom status bar with coordinates, CRS, scale, and progress."""

    def __init__(self, parent: Any, **kwargs: Any) -> None:
        kwargs.setdefault("height", STATUS_BAR_HEIGHT)
        kwargs.setdefault("corner_radius", 0)
        super().__init__(parent, **kwargs)
        self.pack_propagate(False)

        # Coordinate display
        self._coord_label = ctk.CTkLabel(
            self, text="X: 0.000000  Y: 0.000000", font=("Consolas", 11), width=220
        )
        self._coord_label.pack(side="left", padx=8)

        # Separator
        ctk.CTkFrame(self, width=1, height=18, fg_color="gray50").pack(
            side="left", padx=4, pady=4
        )

        # CRS indicator
        self._crs_label = ctk.CTkLabel(
            self, text="EPSG:4326", font=("", 11), width=100
        )
        self._crs_label.pack(side="left", padx=8)

        # Separator
        ctk.CTkFrame(self, width=1, height=18, fg_color="gray50").pack(
            side="left", padx=4, pady=4
        )

        # Scale display
        self._scale_label = ctk.CTkLabel(
            self, text="1:1", font=("", 11), width=80
        )
        self._scale_label.pack(side="left", padx=8)

        # Progress bar (right-aligned)
        self._progress_bar = ctk.CTkProgressBar(self, width=160, height=12)
        self._progress_bar.pack(side="right", padx=8, pady=8)
        self._progress_bar.set(0)

    def update_coordinates(self, x: float, y: float) -> None:
        """Update the coordinate readout in the status bar."""
        self._coord_label.configure(text=f"X: {x:.6f}  Y: {y:.6f}")

    def update_crs(self, name: str) -> None:
        """Update the CRS indicator in the status bar."""
        self._crs_label.configure(text=name)

    def update_scale(self, scale: float) -> None:
        """Update the scale display in the status bar."""
        self._scale_label.configure(text=f"1:{scale:,.0f}")

    def show_progress(self, value: float, maximum: float = 100.0) -> None:
        """Set the progress bar.  Pass value == maximum to complete."""
        self._progress_bar.set(value / maximum if maximum else 0)
