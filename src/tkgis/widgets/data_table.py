"""DataTableWidget — displays a pandas DataFrame using ttkbootstrap Treeview."""
from __future__ import annotations

import tkinter as tk
from typing import Any

import customtkinter as ctk
import pandas as pd

# Attempt ttkbootstrap; fall back to plain ttk.
try:
    from ttkbootstrap import Treeview  # type: ignore[import-untyped]
except ImportError:  # pragma: no cover
    from tkinter.ttk import Treeview  # type: ignore[assignment]

# Virtual-scrolling threshold: DataFrames larger than this use windowed
# insertion to avoid locking the UI.
_VIRTUAL_THRESHOLD = 100_000
_BUFFER_ROWS = 200


class DataTableWidget(ctk.CTkFrame):
    """Displays a pandas DataFrame using ttkbootstrap Treeview.

    For large DataFrames (100k+ rows), only visible rows plus a small
    buffer are inserted into the Treeview.  Scrolling triggers lazy
    loading of additional rows.
    """

    def __init__(self, parent: Any, **kwargs: Any) -> None:
        super().__init__(parent, **kwargs)

        self._df: pd.DataFrame = pd.DataFrame()
        self._display_df: pd.DataFrame = pd.DataFrame()
        self._mask: pd.Series | None = None
        self._sort_column: str | None = None
        self._sort_ascending: bool = True

        # Track which original-index rows are selected.
        self._selected_indices: set[int] = set()

        # Virtual-scrolling state.
        self._virtual: bool = False
        self._loaded_start: int = 0
        self._loaded_end: int = 0

        # --- Treeview + scrollbars ---
        container = ctk.CTkFrame(self)
        container.pack(fill="both", expand=True)

        self._tree = Treeview(
            container,
            show="headings",
            selectmode="extended",
        )

        self._vsb = tk.Scrollbar(container, orient="vertical", command=self._on_scroll)
        self._hsb = tk.Scrollbar(container, orient="horizontal", command=self._tree.xview)

        self._tree.configure(yscrollcommand=self._vsb_set, xscrollcommand=self._hsb.set)

        self._tree.grid(row=0, column=0, sticky="nsew")
        self._vsb.grid(row=0, column=1, sticky="ns")
        self._hsb.grid(row=1, column=0, sticky="ew")

        container.rowconfigure(0, weight=1)
        container.columnconfigure(0, weight=1)

        self._tree.bind("<<TreeviewSelect>>", self._on_tree_select)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_data(self, df: pd.DataFrame) -> None:
        """Replace the displayed data with *df*."""
        self._df = df.copy()
        self._mask = None
        self._sort_column = None
        self._sort_ascending = True
        self._selected_indices.clear()
        self._rebuild()

    def get_selected_rows(self) -> list[int]:
        """Return the original DataFrame indices of selected rows."""
        return sorted(self._selected_indices)

    def sort_by_column(self, column: str, ascending: bool = True) -> None:
        """Sort displayed data by *column*."""
        if column not in self._df.columns:
            return
        self._sort_column = column
        self._sort_ascending = ascending
        self._rebuild()

    def filter_rows(self, mask: pd.Series | None) -> None:
        """Apply a boolean *mask* to filter displayed rows.

        Pass ``None`` to clear the filter.
        """
        self._mask = mask
        self._rebuild()

    def scroll_to_row(self, index: int) -> None:
        """Scroll the Treeview so that the row at *index* is visible."""
        iid = str(index)
        children = self._tree.get_children()
        if iid in children:
            self._tree.see(iid)

    @property
    def row_count(self) -> int:
        """Number of rows currently displayed (after filter)."""
        return len(self._display_df)

    @property
    def total_count(self) -> int:
        """Total number of rows in the underlying DataFrame."""
        return len(self._df)

    @property
    def selected_count(self) -> int:
        """Number of currently selected rows."""
        return len(self._selected_indices)

    # ------------------------------------------------------------------
    # Selection helpers
    # ------------------------------------------------------------------

    def select_all(self) -> None:
        """Select every displayed row."""
        self._selected_indices = set(self._display_df.index.tolist())
        self._tree.selection_set(self._tree.get_children())

    def deselect_all(self) -> None:
        """Deselect all rows."""
        self._selected_indices.clear()
        self._tree.selection_remove(*self._tree.get_children())

    def invert_selection(self) -> None:
        """Invert the current selection within the displayed rows."""
        all_displayed = set(self._display_df.index.tolist())
        self._selected_indices = all_displayed - self._selected_indices
        # Update treeview selection.
        self._tree.selection_remove(*self._tree.get_children())
        iids = [str(i) for i in self._selected_indices]
        if iids:
            self._tree.selection_set(iids)

    # ------------------------------------------------------------------
    # Internal build / virtual-scroll machinery
    # ------------------------------------------------------------------

    def _rebuild(self) -> None:
        """Recompute the display DataFrame and repopulate the Treeview."""
        df = self._df

        # Apply filter mask.
        if self._mask is not None:
            # Align mask to current df index.
            aligned = self._mask.reindex(df.index, fill_value=False)
            df = df.loc[aligned]

        # Apply sort.
        if self._sort_column and self._sort_column in df.columns:
            df = df.sort_values(
                self._sort_column, ascending=self._sort_ascending, na_position="last"
            )

        self._display_df = df
        self._virtual = len(df) > _VIRTUAL_THRESHOLD

        # Clear existing contents.
        self._tree.delete(*self._tree.get_children())

        # Configure columns.
        columns = list(df.columns)
        self._tree["columns"] = columns
        for col in columns:
            self._tree.heading(
                col,
                text=col,
                command=lambda c=col: self._on_heading_click(c),  # type: ignore[misc]
            )
            self._tree.column(col, width=100, stretch=True)

        # Insert rows.
        if self._virtual:
            self._loaded_start = 0
            self._loaded_end = min(_BUFFER_ROWS, len(df))
            self._insert_range(0, self._loaded_end)
        else:
            self._insert_range(0, len(df))

    def _insert_range(self, start: int, end: int) -> None:
        """Insert rows from *start* to *end* (exclusive) of ``_display_df``."""
        df = self._display_df
        if df.empty:
            return
        subset = df.iloc[start:end]
        for idx, row in subset.iterrows():
            values = [self._format_cell(v) for v in row.values]
            self._tree.insert("", "end", iid=str(idx), values=values)

    @staticmethod
    def _format_cell(value: Any) -> str:
        """Convert a cell value to a display string."""
        if pd.isna(value):
            return ""
        return str(value)

    # ------------------------------------------------------------------
    # Scrollbar / virtual-scroll callbacks
    # ------------------------------------------------------------------

    def _vsb_set(self, first: str, last: str) -> None:
        """Intercept scrollbar position to trigger lazy loading."""
        self._vsb.set(first, last)
        if self._virtual:
            self._maybe_load_more(float(first), float(last))

    def _on_scroll(self, *args: Any) -> None:
        """Proxy vertical scrollbar commands to the Treeview."""
        self._tree.yview(*args)

    def _maybe_load_more(self, first: float, last: float) -> None:
        """In virtual mode, load additional rows when the user scrolls near the edge."""
        total = len(self._display_df)
        if total == 0:
            return

        visible_end = int(last * total) + _BUFFER_ROWS
        if visible_end > self._loaded_end and self._loaded_end < total:
            new_end = min(self._loaded_end + _BUFFER_ROWS, total)
            self._insert_range(self._loaded_end, new_end)
            self._loaded_end = new_end

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_heading_click(self, column: str) -> None:
        """Toggle sort on column header click."""
        if self._sort_column == column:
            self._sort_ascending = not self._sort_ascending
        else:
            self._sort_column = column
            self._sort_ascending = True
        self._rebuild()

    def _on_tree_select(self, _event: tk.Event) -> None:  # type: ignore[type-arg]
        """Sync internal selection set with the Treeview selection."""
        selection = self._tree.selection()
        self._selected_indices = set()
        for iid in selection:
            try:
                self._selected_indices.add(int(iid))
            except ValueError:
                pass
