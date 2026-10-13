"""Small, shared non-interactive tooltips for compact icon commands."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class Tooltip:
    """Show a short delayed description without taking keyboard focus."""

    def __init__(self, widget: tk.Misc, text: str, delay_ms: int = 550) -> None:
        self._widget = widget
        self._text = text
        self._delay_ms = delay_ms
        self._after_id: str | None = None
        self._window: tk.Toplevel | None = None
        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<ButtonPress>", self._hide, add="+")

    def set_text(self, text: str) -> None:
        """Keep a tooltip synchronized with localized native button text."""
        self._text = text

    def _schedule(self, _event: tk.Event[tk.Misc]) -> None:
        self._hide()
        self._after_id = self._widget.after(self._delay_ms, self._show)

    def _show(self) -> None:
        self._after_id = None
        if not self._text or not self._widget.winfo_exists():
            return
        try:
            window = tk.Toplevel(self._widget)
            window.wm_overrideredirect(True)
            window.attributes("-topmost", True)
            x = self._widget.winfo_rootx() + 8
            y = self._widget.winfo_rooty() + self._widget.winfo_height() + 6
            window.wm_geometry(f"+{x}+{y}")
            ttk.Label(window, text=self._text, padding=(7, 3), style="Tooltip.TLabel").pack()
            self._window = window
        except tk.TclError:
            self._window = None

    def _hide(self, _event: tk.Event[tk.Misc] | None = None) -> None:
        if self._after_id is not None:
            self._widget.after_cancel(self._after_id)
            self._after_id = None
        if self._window is not None:
            self._window.destroy()
            self._window = None
