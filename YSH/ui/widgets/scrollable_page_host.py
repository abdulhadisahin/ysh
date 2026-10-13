"""Notebook host for independently scrollable calculation pages."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import ttk

from ui.assets import d243_watermark_logo_path
from ui.theme import colors
from ui.widgets.scrollable_frame import ScrollableFrame


class ScrollablePageHost(ttk.Notebook):
    """Host calculation pages and activate wheel routing for the selected tab."""

    def __init__(self, parent: tk.Misc, **kwargs: object) -> None:
        """Create the notebook and its registered page viewports."""
        super().__init__(parent, style="YSH.TNotebook", **kwargs)
        self._hosts: dict[str, ScrollableFrame] = {}
        self._page_hosts: dict[str, ScrollableFrame] = {}
        self._page_keys: dict[str, ScrollableFrame] = {}
        self.bind("<<NotebookTabChanged>>", self._on_tab_changed)
        self.bind("<Prior>", self._page_up)
        self.bind("<Next>", self._page_down)
        self.bind("<Home>", self._home)
        self.bind("<End>", self._end)

    def add_scrollable_page(
        self,
        title: str,
        factory: Callable[[tk.Misc], tk.Misc],
        page_key: str | None = None,
    ) -> tk.Misc:
        """Create and register a page within a standard scroll viewport."""
        host = ScrollableFrame(self)
        host.set_background_watermark(d243_watermark_logo_path())
        page = factory(host.content)
        page.pack(fill="x", expand=True)
        self.add(host, text=title)
        self._hosts[str(host)] = host
        self._page_hosts[str(page)] = host
        if page_key is not None:
            self._page_keys[page_key] = host
        self.after_idle(self._activate_current_host)
        self.after_idle(self._apply_active_tab_color)
        return page

    def set_page_title(self, page_key: str, title: str) -> None:
        """Update a stable-key tab label without rebuilding its page or state."""
        host = self._page_keys.get(page_key)
        if host is not None:
            self.tab(host, text=title)

    def _active_host(self) -> ScrollableFrame | None:
        """Return the viewport belonging to the selected calculation tab."""
        return self._hosts.get(self.select())

    def _on_tab_changed(self, _event: tk.Event[tk.Misc]) -> None:
        """Switch wheel ownership to the newly active tab."""
        self._activate_current_host()
        self._apply_active_tab_color()
        self.focus_set()

    def _apply_active_tab_color(self) -> None:
        """Apply the current page identity color without rebuilding a tab."""
        selected = self.select()
        page_key = next(
            (key for key, host in self._page_keys.items() if str(host) == selected),
            None,
        )
        # D243 navigation is product-led rather than page-color-led: Gold
        # identifies the selected engineering module without borrowing purple
        # or other legacy module colors into the shell.
        selected_foreground = colors.GOLD
        style = ttk.Style(self)
        style.configure(
            "YSH.TNotebook.Tab",
            background=colors.NAVY,
            foreground=colors.ON_ACCENT,
        )
        style.map(
            "YSH.TNotebook.Tab",
            background=[("selected", colors.DEEP_NAVY), ("active", colors.DEEP_NAVY)],
            foreground=[("selected", selected_foreground), ("active", colors.GOLD)],
        )

    def _activate_current_host(self) -> None:
        """Disable stale page routers and enable only the selected viewport."""
        active = self._active_host()
        for host in self._hosts.values():
            host.set_wheel_active(host is active)

    def _scroll(self, event: tk.Event[tk.Misc], amount: int) -> str | None:
        """Apply keyboard scrolling to ordinary content in the active tab."""
        if event.widget.winfo_class() in {"Treeview", "Text", "Entry", "TCombobox", "Spinbox"}:
            return None
        host = self._active_host()
        if host is not None:
            host.canvas.yview_scroll(amount, "pages")
        return "break"

    def _page_up(self, event: tk.Event[tk.Misc]) -> str | None:
        return self._scroll(event, -1)

    def _page_down(self, event: tk.Event[tk.Misc]) -> str | None:
        return self._scroll(event, 1)

    def _home(self, event: tk.Event[tk.Misc]) -> str | None:
        return self._move(event, 0.0)

    def _end(self, event: tk.Event[tk.Misc]) -> str | None:
        return self._move(event, 1.0)

    def _move(self, event: tk.Event[tk.Misc], position: float) -> str | None:
        if event.widget.winfo_class() in {"Treeview", "Text", "Entry", "TCombobox", "Spinbox"}:
            return None
        host = self._active_host()
        if host is not None:
            host.canvas.yview_moveto(position)
        return "break"
