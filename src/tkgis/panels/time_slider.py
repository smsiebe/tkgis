"""TimeSliderPanel — bottom-docked time slider for temporal navigation."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

import customtkinter as ctk

from tkgis.models.events import EventBus, EventType
from tkgis.panels.base import BasePanel
from tkgis.temporal.manager import TemporalLayerManager

logger = logging.getLogger(__name__)

# Animation speed presets: label → milliseconds between frames.
_SPEED_PRESETS: dict[str, int] = {
    "0.5x": 2000,
    "1x": 1000,
    "2x": 500,
    "4x": 250,
    "8x": 125,
}


class TimeSliderPanel(BasePanel):
    """A dockable panel with a slider for scrubbing through time steps."""

    name = "time_slider"
    title = "Time"
    dock_position = "bottom"
    default_visible = False

    def __init__(
        self,
        event_bus: EventBus,
        manager: TemporalLayerManager,
    ) -> None:
        super().__init__()
        self._event_bus = event_bus
        self._manager = manager

        # Time domain — populated via configure().
        self._steps: list[datetime] = []
        self._current_index: int = 0

        # Animation state.
        self._playing: bool = False
        self._speed_ms: int = 1000
        self._after_id: str | None = None

        # Widgets (created in create_widget).
        self._slider: ctk.CTkSlider | None = None
        self._time_label: ctk.CTkLabel | None = None
        self._play_btn: ctk.CTkButton | None = None
        self._speed_menu: ctk.CTkOptionMenu | None = None

    # ------------------------------------------------------------------
    # BasePanel interface
    # ------------------------------------------------------------------

    def create_widget(self, parent: Any) -> ctk.CTkFrame:
        """Build the time-slider UI inside *parent*."""
        frame = ctk.CTkFrame(parent)
        self._widget = frame

        # --- Current time label ---
        self._time_label = ctk.CTkLabel(frame, text="No temporal data")
        self._time_label.pack(side="top", fill="x", padx=8, pady=(4, 0))

        # --- Controls row ---
        controls = ctk.CTkFrame(frame, fg_color="transparent")
        controls.pack(side="top", fill="x", padx=8, pady=4)

        self._play_btn = ctk.CTkButton(
            controls, text="\u25B6", width=36, command=self._toggle_play
        )
        self._play_btn.pack(side="left", padx=(0, 4))

        self._speed_menu = ctk.CTkOptionMenu(
            controls,
            values=list(_SPEED_PRESETS.keys()),
            width=60,
            command=self._on_speed_changed,
        )
        self._speed_menu.set("1x")
        self._speed_menu.pack(side="left", padx=(0, 8))

        self._slider = ctk.CTkSlider(
            controls,
            from_=0,
            to=1,
            number_of_steps=1,
            command=self._on_slider_moved,
        )
        self._slider.set(0)
        self._slider.pack(side="left", fill="x", expand=True)

        return frame

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def configure(self, steps: list[datetime]) -> None:
        """Load a set of time steps into the slider.

        Parameters
        ----------
        steps:
            Sorted list of datetime objects. Supports 1000+ entries.
        """
        if not steps:
            self._steps = []
            self._current_index = 0
            if self._time_label:
                self._time_label.configure(text="No temporal data")
            return

        self._steps = sorted(steps)
        self._current_index = 0
        n = max(len(self._steps) - 1, 1)

        if self._slider:
            self._slider.configure(from_=0, to=n, number_of_steps=n)
            self._slider.set(0)

        self._update_label()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _update_label(self) -> None:
        if not self._steps or self._time_label is None:
            return
        idx = min(self._current_index, len(self._steps) - 1)
        dt = self._steps[idx]
        text = dt.isoformat(sep=" ", timespec="seconds")
        total = len(self._steps)
        self._time_label.configure(text=f"{text}  [{idx + 1}/{total}]")

    def _on_slider_moved(self, value: float) -> None:
        """Called when the user drags the slider."""
        idx = int(round(value))
        if idx == self._current_index:
            return
        self._current_index = idx
        self._update_label()
        if self._steps:
            self._manager.set_current_time(self._steps[idx])

    def _toggle_play(self) -> None:
        if self._playing:
            self._stop()
        else:
            self._start()

    def _start(self) -> None:
        if not self._steps:
            return
        self._playing = True
        if self._play_btn:
            self._play_btn.configure(text="\u23F8")
        self._tick()

    def _stop(self) -> None:
        self._playing = False
        if self._play_btn:
            self._play_btn.configure(text="\u25B6")
        if self._after_id and self._widget:
            self._widget.after_cancel(self._after_id)
            self._after_id = None

    def _tick(self) -> None:
        """Advance one frame and schedule the next tick."""
        if not self._playing or not self._steps:
            return
        self._current_index = (self._current_index + 1) % len(self._steps)
        if self._slider:
            self._slider.set(self._current_index)
        self._update_label()
        self._manager.set_current_time(self._steps[self._current_index])
        if self._widget:
            self._after_id = self._widget.after(self._speed_ms, self._tick)

    def _on_speed_changed(self, choice: str) -> None:
        self._speed_ms = _SPEED_PRESETS.get(choice, 1000)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def on_hide(self) -> None:
        self._stop()
