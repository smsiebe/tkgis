"""Shared test fixtures."""
from __future__ import annotations

import tkinter as tk

import pytest


# Use a session-scoped Tk root to avoid Tcl re-init errors when multiple
# test files each try to create and destroy Tk() instances.
@pytest.fixture(scope="session")
def tk_root():
    """Create a single Tk root for the entire test session."""
    root = tk.Tk()
    root.withdraw()
    yield root
    root.destroy()


@pytest.fixture()
def tk_frame(tk_root):
    """Provide a fresh frame parented to the session root, destroyed after test."""
    frame = tk.Frame(tk_root)
    yield frame
    frame.destroy()
