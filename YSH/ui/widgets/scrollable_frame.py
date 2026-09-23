"""Reusable scoped vertical scrolling container for ttk page content."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class ScrollableFrame(ttk.Frame):
    """Canvas-backed page viewport with active-tab-aware wheel routing."""

    def __init__(self, parent: tk.Misc, **kwargs: object) -> None:
        """Create the canvas viewport, scrollbar, and content frame."""
        super().__init__(parent, **kwargs)
        self._wheel_active = False
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.canvas = tk.Canvas(self, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.scrollbar.grid(row=0, column=1, sticky="ns")
        self.content = ttk.Frame(self.canvas)
        self._window = self.canvas.create_window((0, 0), window=self.content, anchor="nw")
        self.content.bind("<Configure>", self._update_scrollregion)
        self.canvas.bind("<Configure>", self._sync_width)
        self.canvas.bind("<MouseWheel>", self.scroll_mousewheel)
        self.canvas.bind("<Prior>", lambda _event: self._scroll_pages(-1))
        self.canvas.bind("<Next>", lambda _event: self._scroll_pages(1))
        self.canvas.bind("<Home>", lambda _event: self._move_to(0.0))
        self.canvas.bind("<End>", lambda _event: self._move_to(1.0))

    def set_wheel_active(self, active: bool) -> None:
        """Enable wheel routing only while this page is the selected tab."""
        self._wheel_active = active

    def scroll_mousewheel(self, event: tk.Event[tk.Misc]) -> str | None:
        """Scroll this active page for a normalized Windows wheel event."""
        if not self._wheel_active:
            return None
        amount = self._wheel_amount(event)
        if amount:
            self.canvas.yview_scroll(amount, "units")
        return "break"

    @staticmethod
    def _wheel_amount(event: tk.Event[tk.Misc]) -> int:
        """Normalize one Windows wheel message into vertical scroll units."""
        delta = int(getattr(event, "delta", 0) / 120)
        return -delta

    @staticmethod
    def _can_scroll(widget: tk.Misc, amount: int) -> bool:
        """Return whether a nested widget can move in the requested direction."""
        yview = getattr(widget, "yview", None)
        if not callable(yview) or amount == 0:
            return False
        view = yview()
        if not isinstance(view, tuple) or len(view) != 2:
            return False
        start, end = view
        return start > 0.0 if amount < 0 else end < 1.0

    @classmethod
    def nearest_page_host(cls, widget: tk.Misc) -> "ScrollableFrame | None":
        """Find the nearest page viewport without relying on widget names."""
        current: tk.Misc | None = widget
        while current is not None:
            if isinstance(current, cls):
                return current
            parent_name = current.winfo_parent()
            if not parent_name:
                return None
            try:
                current = current.nametowidget(parent_name)
            except KeyError:
                return None
        return None

    @classmethod
    def route_nested_mousewheel(
        cls,
        event: tk.Event[tk.Misc],
        nested_widget: tk.Misc,
    ) -> str | None:
        """Scroll nested content first, delegating at its vertical boundaries."""
        amount = cls._wheel_amount(event)
        if amount == 0:
            return "break"
        if cls._can_scroll(nested_widget, amount):
            yview_scroll = getattr(nested_widget, "yview_scroll", None)
            if callable(yview_scroll):
                yview_scroll(amount, "units")
                return "break"
        host = cls.nearest_page_host(nested_widget)
        return host.scroll_mousewheel(event) if host is not None else None

    def _update_scrollregion(self, _event: tk.Event[tk.Misc]) -> None:
        """Update bounds and bind ordinary or nested-scrollable descendants."""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self._bind_descendant_wheels(self.content)

    def _bind_descendant_wheels(self, widget: tk.Misc) -> None:
        """Route ordinary descendants and delegate nested scroll boundaries."""
        ordinary_classes = {
            "Entry", "TEntry", "Combobox", "TCombobox", "Button", "TButton",
            "Label", "TLabel", "Frame", "TFrame", "Labelframe", "TLabelframe",
        }
        for child in widget.winfo_children():
            widget_class = child.winfo_class()
            if (
                widget_class in ordinary_classes
                and not getattr(child, "_ysh_page_wheel_bound", False)
            ):
                child.bind("<MouseWheel>", self.scroll_mousewheel, add="+")
                child._ysh_page_wheel_bound = True
            if (
                widget_class == "Canvas"
                and not getattr(child, "_ysh_nested_wheel_bound", False)
            ):
                child.bind(
                    "<MouseWheel>",
                    lambda event, nested=child: self.route_nested_mousewheel(
                        event, nested
                    ),
                    add="+",
                )
                child._ysh_nested_wheel_bound = True
            if widget_class != "Treeview":
                self._bind_descendant_wheels(child)

    def _sync_width(self, event: tk.Event[tk.Misc]) -> None:
        """Keep the content width synchronized with the viewport."""
        self.canvas.itemconfigure(self._window, width=event.width)

    def _scroll_pages(self, amount: int) -> str:
        self.canvas.yview_scroll(amount, "pages")
        return "break"

    def _move_to(self, position: float) -> str:
        self.canvas.yview_moveto(position)
        return "break"
