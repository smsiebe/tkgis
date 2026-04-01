"""Main application window."""
from __future__ import annotations

import logging
import tkinter as tk
from pathlib import Path
from tkinter import filedialog
from typing import Any

import customtkinter as ctk

from tkgis.config import Config
from tkgis.constants import (
    APP_NAME,
    BOTTOM_PANEL_HEIGHT,
    DEFAULT_HEIGHT,
    DEFAULT_WIDTH,
    LEFT_PANEL_WIDTH,
    RIGHT_PANEL_WIDTH,
    STATUS_BAR_HEIGHT,
)
from tkgis.models.events import EventBus, EventType
from tkgis.models.project import Project
from tkgis.models.tools import ToolManager
from tkgis.panels.log_console import LogConsolePanel
from tkgis.panels.registry import PanelRegistry
from tkgis.plugins.base import PluginContext
from tkgis.plugins.manager import PluginManager
from tkgis.plugins.providers import DataProviderRegistry

from tkgis.app_ui.menu_builder import MenuBuilder
from tkgis.app_ui.toolbar_builder import ToolbarBuilder
from tkgis.widgets.status_bar import StatusBarWidget

logger = logging.getLogger(__name__)


class TkGISApp(ctk.CTk):
    """Top-level tkgis application window."""

    def __init__(self, config: Config | None = None) -> None:
        super().__init__()

        # -- configuration ----------------------------------------------------
        self.config = config or Config()
        ctk.set_appearance_mode(self.config.theme)

        # -- core domain objects ----------------------------------------------
        self.event_bus = EventBus()
        # Wire up invoke_later for thread-safe events to hit the main thread
        self.event_bus.set_invoke_later(self._invoke_later)
        
        self.project = Project()
        self.tool_manager = ToolManager(event_bus=self.event_bus)
        self.data_provider_registry = DataProviderRegistry()

        # -- window setup -----------------------------------------------------
        self.title(f"{APP_NAME} \u2014 {self.project.name}")
        self.geometry(self.config.window_geometry)
        self.minsize(800, 600)

        # -- panel registry ---------------------------------------------------
        self.panel_registry = PanelRegistry()

        # -- logging setup ----------------------------------------------------
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%H:%M:%S",
        )

        # -- build UI ---------------------------------------------------------
        self._build_menu_bar()
        self._build_toolbar()
        self._build_main_layout()
        self._build_status_bar()
        self._register_default_panels()

        # -- wiring -----------------------------------------------------------
        self._register_all_panels()
        self._register_all_tools()
        self._setup_plugins()
        self._wire_menu_actions()
        self._bind_keyboard_shortcuts()

        # -- default state: dark theme, pan tool active -----------------------
        ctk.set_appearance_mode("dark")
        try:
            self.tool_manager.set_active("pan")
        except KeyError:
            pass

        self.event_bus.subscribe(EventType.PROGRESS_UPDATED, self._on_progress_updated)

        # -- save geometry on close -------------------------------------------
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        logger.info("tkgis application started.")
        self.on_startup()

    # ── App Lifecycle Hooks ─────────────────────────────────────────────────

    def on_startup(self) -> None:
        """Called when the application is fully built and ready."""
        logger.debug("on_startup hook fired")

    def on_shutdown(self) -> None:
        """Called right before window destruction."""
        logger.debug("on_shutdown hook fired")
        # Deactivate all plugins cleanly
        for p in self.plugin_manager.list_plugins():
            if self.plugin_manager.is_enabled(p.name):
                self.plugin_manager.deactivate(p.name)

    def on_project_change(self) -> None:
        """Called when a new project is loaded."""
        logger.debug("on_project_change hook fired")
        for panel in self.panel_registry.list_panels():
            if hasattr(panel, "on_project_changed"):
                panel.on_project_changed(self.project)

    def _invoke_later(self, func: Any) -> None:
        """Execute a function on the main thread safely."""
        self.after(0, func)

    # ── Component wiring ────────────────────────────────────────────────────

    def _register_all_panels(self) -> None:
        """Register all panels from all TGs."""
        from tkgis.panels.chart_panel import ChartPanel
        from tkgis.panels.toolbox import ProcessingToolboxPanel
        from tkgis.panels.workflow_builder import WorkflowBuilderPanel

        panels = [
            ChartPanel(),
            ProcessingToolboxPanel(event_bus=self.event_bus),
            WorkflowBuilderPanel(event_bus=self.event_bus),
        ]

        # Panels that require project and event_bus
        try:
            from tkgis.panels.layer_tree import LayerTreePanel
            panels.append(LayerTreePanel(project=self.project, event_bus=self.event_bus))
        except Exception:
            logger.debug("LayerTreePanel could not be instantiated", exc_info=True)

        try:
            from tkgis.panels.attribute_table import AttributeTablePanel
            panels.append(AttributeTablePanel(project=self.project, event_bus=self.event_bus))
        except Exception:
            logger.debug("AttributeTablePanel could not be instantiated", exc_info=True)

        # TimeSliderPanel requires a TemporalLayerManager
        try:
            from tkgis.panels.time_slider import TimeSliderPanel
            from tkgis.temporal.manager import TemporalLayerManager
            temporal_mgr = TemporalLayerManager(event_bus=self.event_bus)
            panels.append(TimeSliderPanel(event_bus=self.event_bus, manager=temporal_mgr))
        except Exception:
            logger.debug("TimeSliderPanel could not be instantiated", exc_info=True)

        for panel in panels:
            self.panel_registry.register(panel)

    def _register_all_tools(self) -> None:
        """Register navigation, measurement, selection tools."""
        from tkgis.crs.engine import CRSEngine
        from tkgis.tools.identify import IdentifyTool
        from tkgis.tools.measure import AreaTool, DistanceTool
        from tkgis.tools.navigation import PanTool, ZoomInTool, ZoomOutTool
        from tkgis.tools.select import SelectTool

        crs_engine = CRSEngine()

        tools = [
            PanTool(),
            ZoomInTool(),
            ZoomOutTool(),
            DistanceTool(crs_engine=crs_engine),
            AreaTool(crs_engine=crs_engine),
            IdentifyTool(),
            SelectTool(),
        ]

        for tool in tools:
            self.tool_manager.register_tool(tool)

    def _setup_plugins(self) -> None:
        """Load and activate builtin plugins."""
        context = PluginContext()
        context.set_data_provider_registry(self.data_provider_registry)
        self.plugin_manager = PluginManager(context=context)
        self.plugin_manager.load_all()

    def _wire_menu_actions(self) -> None:
        """Connect menu items to real actions."""
        # Build a mapping of action strings to callables
        self._action_map: dict[str, Any] = {
            "File > New Project": self._action_new_project,
            "File > Open Project": self._action_open_project,
            "File > Save Project": self._action_save_project,
            "File > Save Project As": self._action_save_project_as,
            "File > Add Layer": self._action_add_layer,
            "Processing > Toolbox": lambda: self._toggle_panel("processing_toolbox"),
            "Processing > Workflow Builder": self._action_open_workflow_builder,
        }

    def _bind_keyboard_shortcuts(self) -> None:
        """Set up global keyboard shortcuts."""
        self.bind("<Control-n>", lambda e: self._action_new_project())
        self.bind("<Control-o>", lambda e: self._action_open_project())
        self.bind("<Control-s>", lambda e: self._action_save_project())
        self.bind("<Control-l>", lambda e: self._action_add_layer())

    # ── UI Construction ─────────────────────────────────────────────────────

    def _build_menu_bar(self) -> None:
        MenuBuilder.build(self)

    def _build_toolbar(self) -> None:
        self._toolbar = ToolbarBuilder.build(self)

    def _build_main_layout(self) -> None:
        # Outer vertical paned window (main area / bottom panel)
        self._vpaned = tk.PanedWindow(self, orient=tk.VERTICAL, sashwidth=4)
        self._vpaned.pack(fill="both", expand=True)

        # Inner horizontal paned window (left / center / right)
        self._hpaned = tk.PanedWindow(self._vpaned, orient=tk.HORIZONTAL, sashwidth=4)
        self._vpaned.add(self._hpaned, stretch="always")

        # Left panel container
        self._left_panel_frame = ctk.CTkFrame(self._hpaned, width=LEFT_PANEL_WIDTH)
        self._left_panel_frame.pack_propagate(False)
        ctk.CTkLabel(self._left_panel_frame, text="Layers", font=("", 13, "bold")).pack(pady=6)
        ctk.CTkLabel(self._left_panel_frame, text="(Layer tree placeholder)").pack(expand=True)
        self._hpaned.add(self._left_panel_frame, width=LEFT_PANEL_WIDTH, stretch="never")

        # Center (map placeholder)
        self._center_frame = ctk.CTkFrame(self._hpaned)
        ctk.CTkLabel(
            self._center_frame,
            text="Map Canvas",
            font=("", 18, "bold"),
            text_color="gray60",
        ).pack(expand=True)
        self._hpaned.add(self._center_frame, stretch="always")

        # Right panel container
        self._right_panel_frame = ctk.CTkFrame(self._hpaned, width=RIGHT_PANEL_WIDTH)
        self._right_panel_frame.pack_propagate(False)
        ctk.CTkLabel(self._right_panel_frame, text="Properties", font=("", 13, "bold")).pack(pady=6)
        ctk.CTkLabel(self._right_panel_frame, text="(Properties placeholder)").pack(expand=True)
        self._hpaned.add(self._right_panel_frame, width=RIGHT_PANEL_WIDTH, stretch="never")

        # Bottom panel container
        self._bottom_panel_frame = ctk.CTkFrame(self._vpaned, height=BOTTOM_PANEL_HEIGHT)
        self._bottom_panel_frame.pack_propagate(False)
        self._vpaned.add(self._bottom_panel_frame, height=BOTTOM_PANEL_HEIGHT, stretch="never")

    def _build_status_bar(self) -> None:
        self._status_bar = StatusBarWidget(self)
        self._status_bar.pack(fill="x", side="bottom")

    # ── Status bar public methods ───────────────────────────────────────────

    def update_coordinates(self, x: float, y: float) -> None:
        """Update the coordinate readout in the status bar."""
        self._status_bar.update_coordinates(x, y)

    def update_crs(self, name: str) -> None:
        """Update the CRS indicator in the status bar."""
        self._status_bar.update_crs(name)

    def update_scale(self, scale: float) -> None:
        """Update the scale display in the status bar."""
        self._status_bar.update_scale(scale)

    def show_progress(self, value: float, maximum: float = 100.0) -> None:
        """Set the progress bar.  Pass value == maximum to complete."""
        self._status_bar.show_progress(value, maximum)

    def _on_progress_updated(self, *, value: float, maximum: float, **_kwargs: Any) -> None:
        """Handle global progress event."""
        self.show_progress(value, maximum)

    # ── Panel management ────────────────────────────────────────────────────

    def _register_default_panels(self) -> None:
        log_panel = LogConsolePanel()
        self.panel_registry.register(log_panel)
        widget = log_panel.create_widget(self._bottom_panel_frame)
        widget.pack(fill="both", expand=True)

    def _toggle_panel(self, name: str) -> None:
        self.panel_registry.toggle(name)
        panel = self.panel_registry.get(name)
        if panel and panel.widget:
            if panel.visible:
                panel.widget.pack(fill="both", expand=True)
            else:
                panel.widget.pack_forget()

    # ── Theme switching ─────────────────────────────────────────────────────

    def _set_theme(self, theme: str) -> None:
        ctk.set_appearance_mode(theme)
        self.config.theme = theme
        self.config.save()
        logger.info("Theme changed to: %s", theme)

    # ── Action implementations ──────────────────────────────────────────────

    def _action_new_project(self) -> None:
        """Create a new empty project."""
        self.project = Project()
        self.title(f"{APP_NAME} \u2014 {self.project.name}")
        self.event_bus.emit(EventType.PROJECT_LOADED)
        self.on_project_change()
        logger.info("New project created.")

    def _action_open_project(self) -> None:
        """Open an existing project file."""
        path = filedialog.askopenfilename(
            filetypes=[("tkgis Project", "*.tkgis *.json"), ("All files", "*.*")],
            title="Open Project",
        )
        if path:
            try:
                self.project = Project.load(path)
                self.title(f"{APP_NAME} \u2014 {self.project.name}")
                self.event_bus.emit(EventType.PROJECT_LOADED)
                self.on_project_change()
                self.config.add_recent_file(path)
                self.config.save()
                logger.info("Project opened: %s", path)
            except Exception:
                logger.exception("Failed to open project: %s", path)

    def _action_save_project(self) -> None:
        """Save the current project."""
        if self.project.path:
            self.project.save()
            self.event_bus.emit(EventType.PROJECT_SAVED)
            logger.info("Project saved: %s", self.project.path)
        else:
            self._action_save_project_as()

    def _action_save_project_as(self) -> None:
        """Save the current project to a new file."""
        path = filedialog.asksaveasfilename(
            defaultextension=".tkgis",
            filetypes=[("tkgis Project", "*.tkgis *.json"), ("All files", "*.*")],
            title="Save Project As",
        )
        if path:
            self.project.save(path)
            self.title(f"{APP_NAME} \u2014 {self.project.name}")
            self.event_bus.emit(EventType.PROJECT_SAVED)
            self.config.add_recent_file(path)
            self.config.save()
            logger.info("Project saved as: %s", path)

    def _action_add_layer(self) -> None:
        """Open a file dialog and add a layer via DataProviderRegistry."""
        filters = self.data_provider_registry.get_all_filters()
        filetypes = [("All supported", "*.*")]
        if filters:
            for f in filters.split(";;"):
                filetypes.insert(0, (f, "*.*"))

        path = filedialog.askopenfilename(
            filetypes=filetypes,
            title="Add Layer",
        )
        if path:
            try:
                layer = self.data_provider_registry.open_file(Path(path))
                self.project.add_layer(layer)
                self.event_bus.emit(
                    EventType.LAYER_ADDED, layer_id=layer.id, name=layer.name
                )
                logger.info("Layer added: %s", layer.name)
            except Exception:
                logger.exception("Failed to add layer from: %s", path)

    def _action_open_workflow_builder(self) -> None:
        """Open the WorkflowBuilderWindow as a toplevel window."""
        try:
            from tkgis.workflow.builder_window import WorkflowBuilderWindow
            WorkflowBuilderWindow(self, event_bus=self.event_bus)
        except Exception:
            logger.exception("Failed to open Workflow Builder")

    # ── Placeholder callbacks ───────────────────────────────────────────────

    def _menu_action(self, action: str) -> None:
        """Dispatch menu action to registered handler or log it."""
        handler = getattr(self, "_action_map", {}).get(action)
        if handler is not None:
            handler()
        else:
            logger.info("Menu action: %s", action)

    # ── Lifecycle ───────────────────────────────────────────────────────────

    def _on_close(self) -> None:
        self.on_shutdown()
        self.config.window_geometry = self.geometry()
        self.config.save()
        logger.info("tkgis shutting down.")
        self.destroy()
