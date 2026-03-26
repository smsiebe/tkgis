"""CRS selector dialog using CustomTkinter."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Optional

try:
    import customtkinter as ctk  # type: ignore[import-untyped]
except ImportError:
    ctk = None  # Allows import without GUI; dialog cannot be opened.

import pyproj

from tkgis.models.crs import CRSDefinition


# ~20 commonly-used coordinate reference systems.
COMMON_CRS: list[dict] = [
    {"code": 4326, "name": "WGS 84", "type": "Geographic", "units": "degrees"},
    {"code": 3857, "name": "WGS 84 / Pseudo-Mercator", "type": "Projected", "units": "metre"},
    {"code": 4269, "name": "NAD83", "type": "Geographic", "units": "degrees"},
    {"code": 4267, "name": "NAD27", "type": "Geographic", "units": "degrees"},
    {"code": 32610, "name": "WGS 84 / UTM zone 10N", "type": "Projected", "units": "metre"},
    {"code": 32611, "name": "WGS 84 / UTM zone 11N", "type": "Projected", "units": "metre"},
    {"code": 32612, "name": "WGS 84 / UTM zone 12N", "type": "Projected", "units": "metre"},
    {"code": 32613, "name": "WGS 84 / UTM zone 13N", "type": "Projected", "units": "metre"},
    {"code": 32614, "name": "WGS 84 / UTM zone 14N", "type": "Projected", "units": "metre"},
    {"code": 32615, "name": "WGS 84 / UTM zone 15N", "type": "Projected", "units": "metre"},
    {"code": 32616, "name": "WGS 84 / UTM zone 16N", "type": "Projected", "units": "metre"},
    {"code": 32617, "name": "WGS 84 / UTM zone 17N", "type": "Projected", "units": "metre"},
    {"code": 32618, "name": "WGS 84 / UTM zone 18N", "type": "Projected", "units": "metre"},
    {"code": 32619, "name": "WGS 84 / UTM zone 19N", "type": "Projected", "units": "metre"},
    {"code": 32620, "name": "WGS 84 / UTM zone 20N", "type": "Projected", "units": "metre"},
    {"code": 2193, "name": "NZGD2000 / New Zealand Transverse Mercator", "type": "Projected", "units": "metre"},
    {"code": 27700, "name": "OSGB 1936 / British National Grid", "type": "Projected", "units": "metre"},
    {"code": 3035, "name": "ETRS89 / LAEA Europe", "type": "Projected", "units": "metre"},
    {"code": 2154, "name": "RGF93 / Lambert-93", "type": "Projected", "units": "metre"},
    {"code": 5514, "name": "S-JTSK / Krovak East North", "type": "Projected", "units": "metre"},
]


class CRSSelectorDialog:
    """Modal dialog for choosing a CRS.

    Usage::

        dialog = CRSSelectorDialog(parent)
        result = dialog.result  # CRSDefinition or None
    """

    def __init__(self, parent: tk.Misc | None = None) -> None:
        if ctk is None:
            raise RuntimeError(
                "customtkinter is required for CRSSelectorDialog"
            )

        self.result: Optional[CRSDefinition] = None

        # --- window ---
        self._win = ctk.CTkToplevel(parent)
        self._win.title("Select Coordinate Reference System")
        self._win.geometry("700x480")
        self._win.resizable(True, True)
        self._win.grab_set()

        # --- search bar ---
        search_frame = ctk.CTkFrame(self._win)
        search_frame.pack(fill="x", padx=8, pady=(8, 4))

        ctk.CTkLabel(search_frame, text="Search:").pack(side="left", padx=(4, 4))
        self._search_var = tk.StringVar()
        self._search_entry = ctk.CTkEntry(
            search_frame, textvariable=self._search_var, width=300
        )
        self._search_entry.pack(side="left", fill="x", expand=True, padx=4)
        self._search_var.trace_add("write", self._on_search)

        # --- treeview ---
        tree_frame = ctk.CTkFrame(self._win)
        tree_frame.pack(fill="both", expand=True, padx=8, pady=4)

        cols = ("code", "name", "type", "units")
        self._tree = ttk.Treeview(
            tree_frame, columns=cols, show="headings", selectmode="browse"
        )
        self._tree.heading("code", text="EPSG Code")
        self._tree.heading("name", text="Name")
        self._tree.heading("type", text="Type")
        self._tree.heading("units", text="Units")

        self._tree.column("code", width=90, stretch=False)
        self._tree.column("name", width=340)
        self._tree.column("type", width=100, stretch=False)
        self._tree.column("units", width=80, stretch=False)

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=scrollbar.set)
        self._tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self._tree.bind("<Double-1>", lambda _e: self._on_ok())

        # --- buttons ---
        btn_frame = ctk.CTkFrame(self._win)
        btn_frame.pack(fill="x", padx=8, pady=(4, 8))

        ctk.CTkButton(btn_frame, text="OK", width=90, command=self._on_ok).pack(
            side="right", padx=4
        )
        ctk.CTkButton(
            btn_frame, text="Cancel", width=90, command=self._on_cancel
        ).pack(side="right", padx=4)

        # Populate with common CRS.
        self._populate(COMMON_CRS)

        # Block until closed.
        self._win.wait_window()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _populate(self, items: list[dict]) -> None:
        self._tree.delete(*self._tree.get_children())
        for item in items:
            self._tree.insert(
                "",
                "end",
                iid=str(item["code"]),
                values=(item["code"], item["name"], item["type"], item["units"]),
            )

    def _on_search(self, *_args: object) -> None:
        query = self._search_var.get().strip()
        if not query:
            self._populate(COMMON_CRS)
            return

        # First, filter the common list by name/code substring.
        results: list[dict] = []
        q_lower = query.lower()
        for entry in COMMON_CRS:
            if q_lower in str(entry["code"]) or q_lower in entry["name"].lower():
                results.append(entry)

        # If the query looks numeric, try pyproj database lookup.
        if query.isdigit():
            try:
                code = int(query)
                crs = pyproj.CRS.from_epsg(code)
                entry = {
                    "code": code,
                    "name": crs.name,
                    "type": "Geographic" if crs.is_geographic else "Projected",
                    "units": "degrees" if crs.is_geographic else "metre",
                }
                # Avoid duplicates.
                if not any(r["code"] == code for r in results):
                    results.append(entry)
            except Exception:
                pass
        else:
            # Text search via pyproj database.
            try:
                for auth in ("EPSG",):
                    codes = pyproj.database.get_codes(auth, "CRS")
                    for c in codes:
                        if len(results) >= 50:
                            break
                        try:
                            crs_obj = pyproj.CRS.from_authority(auth, c)
                            if q_lower in crs_obj.name.lower():
                                code_int = int(c)
                                if not any(r["code"] == code_int for r in results):
                                    results.append(
                                        {
                                            "code": code_int,
                                            "name": crs_obj.name,
                                            "type": "Geographic"
                                            if crs_obj.is_geographic
                                            else "Projected",
                                            "units": "degrees"
                                            if crs_obj.is_geographic
                                            else "metre",
                                        }
                                    )
                        except Exception:
                            continue
            except Exception:
                pass

        self._populate(results)

    def _on_ok(self) -> None:
        sel = self._tree.selection()
        if sel:
            code = int(sel[0])
            self.result = CRSDefinition.from_epsg(code)
        self._win.destroy()

    def _on_cancel(self) -> None:
        self.result = None
        self._win.destroy()
