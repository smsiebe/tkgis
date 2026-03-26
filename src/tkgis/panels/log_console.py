"""Log console panel — captures Python logging output."""
from __future__ import annotations

import logging
from typing import Any

import customtkinter as ctk

from tkgis.panels.base import BasePanel


class _TextboxHandler(logging.Handler):
    """Logging handler that writes records into a CTkTextbox."""

    def __init__(self, textbox: ctk.CTkTextbox) -> None:
        super().__init__()
        self._textbox = textbox

    def emit(self, record: logging.LogRecord) -> None:
        msg = self.format(record)
        try:
            self._textbox.configure(state="normal")
            self._textbox.insert("end", msg + "\n")
            self._textbox.see("end")
            self._textbox.configure(state="disabled")
        except Exception:
            # Widget may have been destroyed
            pass


class LogConsolePanel(BasePanel):
    """Scrolling log console that sits in the bottom dock."""

    name = "log_console"
    title = "Log Console"
    dock_position = "bottom"
    default_visible = True

    def __init__(self) -> None:
        super().__init__()
        self._handler: _TextboxHandler | None = None

    def create_widget(self, parent: Any) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(parent)

        # Header
        header = ctk.CTkFrame(frame, height=24)
        header.pack(fill="x")
        ctk.CTkLabel(header, text=self.title, font=("", 12, "bold")).pack(
            side="left", padx=6
        )
        ctk.CTkButton(
            header, text="Clear", width=50, height=20, command=self._clear
        ).pack(side="right", padx=4)

        # Text area
        self._textbox = ctk.CTkTextbox(frame, wrap="word", state="disabled")
        self._textbox.pack(fill="both", expand=True, padx=2, pady=2)

        # Attach logging handler
        self._handler = _TextboxHandler(self._textbox)
        self._handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                              datefmt="%H:%M:%S")
        )
        logging.getLogger().addHandler(self._handler)

        self._widget = frame
        return frame

    def _clear(self) -> None:
        self._textbox.configure(state="normal")
        self._textbox.delete("1.0", "end")
        self._textbox.configure(state="disabled")

    def on_hide(self) -> None:
        if self._handler is not None:
            logging.getLogger().removeHandler(self._handler)

    def on_show(self) -> None:
        if self._handler is not None and self._handler not in logging.getLogger().handlers:
            logging.getLogger().addHandler(self._handler)
