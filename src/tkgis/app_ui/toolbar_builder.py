"""Toolbar builder for the main application."""
from __future__ import annotations

from typing import Any
import customtkinter as ctk


class ToolbarBuilder:
    """Constructs the main toolbar for TkGISApp."""

    @staticmethod
    def build(app: Any) -> ctk.CTkFrame:
        """Build and return the toolbar frame."""
        toolbar = ctk.CTkFrame(app, height=36, corner_radius=0)
        toolbar.pack(fill="x", side="top")

        groups: dict[str, list[tuple[str, str]]] = {
            "File": [("New", "File > New Project"), ("Open", "File > Open Project"), ("Save", "File > Save Project")],
            "Navigation": [("Zoom+", "View > Zoom In"), ("Zoom-", "View > Zoom Out"), ("Fit", "View > Zoom to Fit")],
            "Selection": [("Select", "Selection > Select"), ("Identify", "Selection > Identify")],
            "Measurement": [("Distance", "Measure > Distance"), ("Area", "Measure > Area")],
            "Processing": [("Toolbox", "Processing > Toolbox"), ("Workflow", "Processing > Workflow Builder")],
        }

        for group_name, buttons in groups.items():
            sep = ctk.CTkFrame(toolbar, width=1, height=24, fg_color="gray50")
            sep.pack(side="left", padx=4, pady=4)
            for label, action in buttons:
                btn = ctk.CTkButton(
                    toolbar,
                    text=label,
                    width=60,
                    height=26,
                    font=("", 11),
                    command=lambda a=action: app._menu_action(a),
                )
                btn.pack(side="left", padx=1, pady=4)

        return toolbar
