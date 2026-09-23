"""Reusable independently scrollable ttk Treeview container."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ui.widgets.scrollable_frame import ScrollableFrame


class ScrollableTreeview(ttk.Frame):
    """Host one Treeview with coordinated vertical and horizontal scrollbars."""

    def __init__(self, parent: tk.Misc, **tree_options: object) -> None:
        """Create an expanding Treeview and its two local scrollbars."""
        super().__init__(parent)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        tree_options.setdefault("style", "Data.Treeview")
        self.tree = ttk.Treeview(self, **tree_options)
        self.vertical_scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.horizontal_scrollbar = ttk.Scrollbar(self, orient="horizontal", command=self.tree.xview)
        self.tree.configure(
            yscrollcommand=self.vertical_scrollbar.set,
            xscrollcommand=self.horizontal_scrollbar.set,
        )
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.tree.bind("<MouseWheel>", self._on_mousewheel)
        self.vertical_scrollbar.grid(row=0, column=1, sticky="ns")
        self.horizontal_scrollbar.grid(row=1, column=0, sticky="ew")

    def _on_mousewheel(self, event: tk.Event[tk.Misc]) -> str:
        """Scroll this table first, then continue the page at a boundary."""
        return ScrollableFrame.route_nested_mousewheel(event, self.tree) or "break"
