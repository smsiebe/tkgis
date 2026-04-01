"""Menu builder for the main application."""
from __future__ import annotations

import tkinter as tk
from typing import Any


class MenuBuilder:
    """Constructs the main menu bar for TkGISApp."""

    @staticmethod
    def build(app: Any) -> None:
        """Build and attach the menu bar to *app*."""
        menubar = tk.Menu(app, tearoff=False)
        app.configure(menu=menubar)

        # File
        file_menu = tk.Menu(menubar, tearoff=False)
        file_menu.add_command(label="New Project", command=lambda: app._menu_action("File > New Project"), accelerator="Ctrl+N")
        file_menu.add_command(label="Open Project\u2026", command=lambda: app._menu_action("File > Open Project"), accelerator="Ctrl+O")
        file_menu.add_separator()
        file_menu.add_command(label="Save Project", command=lambda: app._menu_action("File > Save Project"), accelerator="Ctrl+S")
        file_menu.add_command(label="Save Project As\u2026", command=lambda: app._menu_action("File > Save Project As"))
        file_menu.add_separator()
        file_menu.add_command(label="Add Layer\u2026", command=lambda: app._menu_action("File > Add Layer"), accelerator="Ctrl+L")
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=app._on_close)
        menubar.add_cascade(label="File", menu=file_menu)

        # Edit
        edit_menu = tk.Menu(menubar, tearoff=False)
        edit_menu.add_command(label="Undo", command=lambda: app._menu_action("Edit > Undo"))
        edit_menu.add_command(label="Redo", command=lambda: app._menu_action("Edit > Redo"))
        edit_menu.add_separator()
        edit_menu.add_command(label="Copy", command=lambda: app._menu_action("Edit > Copy"))
        edit_menu.add_command(label="Paste", command=lambda: app._menu_action("Edit > Paste"))
        edit_menu.add_separator()
        edit_menu.add_command(label="Preferences\u2026", command=lambda: app._menu_action("Edit > Preferences"))
        menubar.add_cascade(label="Edit", menu=edit_menu)

        # View
        view_menu = tk.Menu(menubar, tearoff=False)
        view_menu.add_command(label="Zoom In", command=lambda: app._menu_action("View > Zoom In"))
        view_menu.add_command(label="Zoom Out", command=lambda: app._menu_action("View > Zoom Out"))
        view_menu.add_command(label="Zoom to Fit", command=lambda: app._menu_action("View > Zoom to Fit"))
        view_menu.add_separator()

        # Theme submenu
        theme_menu = tk.Menu(view_menu, tearoff=False)
        theme_menu.add_command(label="Dark", command=lambda: app._set_theme("dark"))
        theme_menu.add_command(label="Light", command=lambda: app._set_theme("light"))
        theme_menu.add_command(label="System", command=lambda: app._set_theme("system"))
        view_menu.add_cascade(label="Theme", menu=theme_menu)

        view_menu.add_separator()
        view_menu.add_command(label="Toggle Log Console", command=lambda: app._toggle_panel("log_console"))
        menubar.add_cascade(label="View", menu=view_menu)
        app._view_menu = view_menu

        # Layer
        layer_menu = tk.Menu(menubar, tearoff=False)
        layer_menu.add_command(label="Add Raster Layer\u2026", command=lambda: app._menu_action("Layer > Add Raster Layer"))
        layer_menu.add_command(label="Add Vector Layer\u2026", command=lambda: app._menu_action("Layer > Add Vector Layer"))
        layer_menu.add_separator()
        layer_menu.add_command(label="Remove Layer", command=lambda: app._menu_action("Layer > Remove Layer"))
        layer_menu.add_command(label="Layer Properties\u2026", command=lambda: app._menu_action("Layer > Layer Properties"))
        menubar.add_cascade(label="Layer", menu=layer_menu)

        # Processing
        proc_menu = tk.Menu(menubar, tearoff=False)
        proc_menu.add_command(label="Toolbox\u2026", command=lambda: app._menu_action("Processing > Toolbox"))
        proc_menu.add_command(label="Workflow Builder\u2026", command=lambda: app._menu_action("Processing > Workflow Builder"))
        proc_menu.add_separator()
        proc_menu.add_command(label="Run Workflow\u2026", command=lambda: app._menu_action("Processing > Run Workflow"))
        menubar.add_cascade(label="Processing", menu=proc_menu)

        # Plugins
        plugin_menu = tk.Menu(menubar, tearoff=False)
        plugin_menu.add_command(label="Plugin Manager\u2026", command=lambda: app._menu_action("Plugins > Plugin Manager"))
        menubar.add_cascade(label="Plugins", menu=plugin_menu)

        # Help
        help_menu = tk.Menu(menubar, tearoff=False)
        help_menu.add_command(label="Documentation", command=lambda: app._menu_action("Help > Documentation"))
        help_menu.add_command(label="About tkgis", command=lambda: app._menu_action("Help > About"))
        menubar.add_cascade(label="Help", menu=help_menu)

        app._menubar = menubar
