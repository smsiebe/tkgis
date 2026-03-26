"""Base class for dockable panels."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import customtkinter as ctk


class BasePanel(ABC):
    """Abstract base for all dockable panels.

    Subclasses must set *name*, *title*, and *dock_position* and implement
    :meth:`create_widget`.
    """

    name: str
    title: str
    dock_position: str  # "left", "right", "bottom"
    default_visible: bool = True

    def __init__(self) -> None:
        self._widget: ctk.CTkFrame | None = None
        self._visible: bool = self.default_visible

    @abstractmethod
    def create_widget(self, parent: Any) -> ctk.CTkFrame:
        """Build and return the panel's root frame."""
        ...

    @property
    def widget(self) -> ctk.CTkFrame | None:
        return self._widget

    @property
    def visible(self) -> bool:
        return self._visible

    @visible.setter
    def visible(self, value: bool) -> None:
        self._visible = value
        if value:
            self.on_show()
        else:
            self.on_hide()

    def on_show(self) -> None:
        """Called when the panel becomes visible."""

    def on_hide(self) -> None:
        """Called when the panel is hidden."""

    def on_project_changed(self, project: Any) -> None:
        """Called when the active project changes."""
