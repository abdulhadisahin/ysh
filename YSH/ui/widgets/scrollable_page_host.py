"""Notebook host for independently scrollable calculation pages."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import ttk

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

    def set_page_enabled(self, page_key: str, enabled: bool) -> None:
        """Keep inapplicable modules visible and preserve their cached page values."""
        host = self._page_keys.get(page_key)
        if host is None:
            return
        if not enabled and self.select() == str(host):
            for candidate in self.tabs():
                if candidate != str(host) and self.tab(candidate, "state") == "normal":
                    self.select(candidate)
                    break
        self.tab(host, state="normal" if enabled else "disabled")

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
        from ui.theme.module_visuals import MODULES
        selected_foreground = colors.GOLD
        selected_background = colors.DEEP_NAVY
        if page_key == "pipe_design":
            from ui.theme.pipe_pilot import PIPE_DARK
            selected_background = PIPE_DARK
            selected_foreground = colors.WHITE
        elif page_key in MODULES:
            selected_background = MODULES[page_key][2]
            selected_foreground = colors.WHITE
        style = ttk.Style(self)
        style.configure(
            "YSH.TNotebook.Tab",
            background=colors.NAVY,
            foreground=colors.ON_ACCENT,
        )
        style.map(
            "YSH.TNotebook.Tab",
            background=[("selected", selected_background), ("active", colors.DEEP_NAVY)],
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
