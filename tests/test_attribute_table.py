"""Tests for the attribute table panel and data table widget."""
from __future__ import annotations

import tkinter as tk

import pandas as pd
import pytest

from tkgis.models.events import EventBus
from tkgis.models.layers import Layer, LayerType
from tkgis.models.project import Project
from tkgis.query.expression import ExpressionParser
from tkgis.widgets.data_table import DataTableWidget


# ---------------------------------------------------------------------------
# Sample data
# ---------------------------------------------------------------------------

def _sample_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "name": ["Alpha", "Bravo", "Charlie", "Delta", "Echo"],
            "value": [10, 30, 20, 50, 40],
            "category": ["A", "B", "A", "B", "A"],
        }
    )


def _make_layer_with_attributes(df: pd.DataFrame) -> Layer:
    """Create a Layer and attach a DataFrame as the ``attributes`` field."""
    layer = Layer(name="TestVector", layer_type=LayerType.VECTOR)
    layer.attributes = df  # type: ignore[attr-defined]
    return layer


# ---------------------------------------------------------------------------
# DataTableWidget tests
# ---------------------------------------------------------------------------


class TestDataTableWidgetCreates:
    def test_data_table_widget_creates(self, tk_root: tk.Tk) -> None:
        widget = DataTableWidget(tk_root)
        assert widget is not None
        assert widget.row_count == 0
        assert widget.total_count == 0
        widget.destroy()


class TestDataTableSetData:
    def test_data_table_set_data(self, tk_root: tk.Tk) -> None:
        widget = DataTableWidget(tk_root)
        df = _sample_df()
        widget.set_data(df)

        assert widget.total_count == 5
        assert widget.row_count == 5

        # Treeview should have 5 children.
        children = widget._tree.get_children()
        assert len(children) == 5

        # Columns should match the DataFrame.
        tree_cols = list(widget._tree["columns"])
        assert tree_cols == ["name", "value", "category"]

        widget.destroy()


class TestColumnSorting:
    def test_column_sorting(self, tk_root: tk.Tk) -> None:
        widget = DataTableWidget(tk_root)
        df = _sample_df()
        widget.set_data(df)

        # Sort ascending by value.
        widget.sort_by_column("value", ascending=True)
        assert widget.row_count == 5

        # First row in the treeview should be the one with value=10.
        first_iid = widget._tree.get_children()[0]
        first_vals = widget._tree.item(first_iid, "values")
        # Treeview values are strings.
        assert first_vals[0] == "Alpha"
        assert first_vals[1] == "10"

        # Sort descending.
        widget.sort_by_column("value", ascending=False)
        first_iid = widget._tree.get_children()[0]
        first_vals = widget._tree.item(first_iid, "values")
        assert first_vals[0] == "Delta"
        assert first_vals[1] == "50"

        widget.destroy()

    def test_sort_nonexistent_column_is_noop(self, tk_root: tk.Tk) -> None:
        widget = DataTableWidget(tk_root)
        widget.set_data(_sample_df())
        widget.sort_by_column("nonexistent")
        assert widget.row_count == 5
        widget.destroy()


class TestExpressionFilter:
    def test_expression_filter(self, tk_root: tk.Tk) -> None:
        widget = DataTableWidget(tk_root)
        df = _sample_df()
        widget.set_data(df)

        parser = ExpressionParser()
        mask = parser.parse("value > 20", df)
        widget.filter_rows(mask)

        # Should show rows with value 30, 50, 40.
        assert widget.row_count == 3
        assert widget.total_count == 5

        # Clear filter.
        widget.filter_rows(None)
        assert widget.row_count == 5

        widget.destroy()

    def test_combined_filter(self, tk_root: tk.Tk) -> None:
        widget = DataTableWidget(tk_root)
        df = _sample_df()
        widget.set_data(df)

        parser = ExpressionParser()
        mask = parser.parse("category = 'A' AND value > 15", df)
        widget.filter_rows(mask)

        # Should match Charlie (20, A) and Echo (40, A).
        assert widget.row_count == 2

        widget.destroy()


class TestRowSelection:
    def test_row_selection(self, tk_root: tk.Tk) -> None:
        widget = DataTableWidget(tk_root)
        df = _sample_df()
        widget.set_data(df)

        # Initially nothing selected.
        assert widget.get_selected_rows() == []
        assert widget.selected_count == 0

        # Select all.
        widget.select_all()
        assert widget.selected_count == 5
        assert len(widget.get_selected_rows()) == 5

        # Deselect all.
        widget.deselect_all()
        assert widget.selected_count == 0
        assert widget.get_selected_rows() == []

        # Invert (from empty = select all).
        widget.invert_selection()
        assert widget.selected_count == 5

        # Invert again (from all = deselect all).
        widget.invert_selection()
        assert widget.selected_count == 0

        widget.destroy()

    def test_scroll_to_row(self, tk_root: tk.Tk) -> None:
        widget = DataTableWidget(tk_root)
        widget.set_data(_sample_df())
        # Should not raise.
        widget.scroll_to_row(0)
        widget.scroll_to_row(4)
        widget.scroll_to_row(999)  # non-existent, no-op
        widget.destroy()


# ---------------------------------------------------------------------------
# AttributeTablePanel tests
# ---------------------------------------------------------------------------


class TestAttributeTablePanelCreates:
    def test_attribute_table_panel_creates(self, tk_root: tk.Tk) -> None:
        from tkgis.panels.attribute_table import AttributeTablePanel

        project = Project(name="Test")
        bus = EventBus()
        panel = AttributeTablePanel(project, bus)

        assert panel.name == "attribute_table"
        assert panel.title == "Attribute Table"
        assert panel.dock_position == "bottom"
        assert panel.default_visible is False

        frame = panel.create_widget(tk_root)
        assert frame is not None
        assert panel.widget is not None

        frame.destroy()

    def test_panel_loads_layer_attributes(self, tk_root: tk.Tk) -> None:
        from tkgis.panels.attribute_table import AttributeTablePanel

        df = _sample_df()
        layer = _make_layer_with_attributes(df)

        project = Project(name="Test")
        project.add_layer(layer)

        bus = EventBus()
        panel = AttributeTablePanel(project, bus)
        panel.create_widget(tk_root)

        # Directly call the event handler to simulate layer selection.
        panel._on_layer_selected(layer_id=layer.id)

        assert panel._table is not None
        assert panel._table.total_count == 5
        assert panel._table.row_count == 5

        panel.widget.destroy()  # type: ignore[union-attr]

    def test_panel_filter_expression(self, tk_root: tk.Tk) -> None:
        from tkgis.panels.attribute_table import AttributeTablePanel

        df = _sample_df()
        layer = _make_layer_with_attributes(df)

        project = Project(name="Test")
        project.add_layer(layer)

        bus = EventBus()
        panel = AttributeTablePanel(project, bus)
        panel.create_widget(tk_root)

        panel._on_layer_selected(layer_id=layer.id)

        # Apply filter via the panel.
        assert panel._filter_var is not None
        panel._filter_var.set("value > 20")
        panel._apply_filter()

        assert panel._table is not None
        assert panel._table.row_count == 3

        # Clear filter.
        panel._clear_filter()
        assert panel._table.row_count == 5

        panel.widget.destroy()  # type: ignore[union-attr]

    def test_panel_status_bar_updates(self, tk_root: tk.Tk) -> None:
        from tkgis.panels.attribute_table import AttributeTablePanel

        df = _sample_df()
        layer = _make_layer_with_attributes(df)

        project = Project(name="Test")
        project.add_layer(layer)

        bus = EventBus()
        panel = AttributeTablePanel(project, bus)
        panel.create_widget(tk_root)

        # Before loading: "No layer selected"
        assert panel._status_label is not None
        assert "No layer" in panel._status_label.cget("text")

        # Load layer
        panel._on_layer_selected(layer_id=layer.id)

        text = panel._status_label.cget("text")
        assert "5 of 5" in text
        assert "0 selected" in text

        panel.widget.destroy()  # type: ignore[union-attr]
