"""Reusable application status bar widget."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import ttk

from i18n.translator import Translator
from ui.theme.spacing import MD, SM


class StatusBar(ttk.Frame):
    """Displays concise application status messages in a ttk frame."""

    def __init__(
        self,
        parent: tk.Misc,
        translate: Callable[[str], str] | None = None,
    ) -> None:
        """Create a status bar with the default Ready message."""
        super().__init__(parent, style="Status.TFrame", padding=(MD, SM // 2))
        self._translate = translate or Translator().translate
        self._message = tk.StringVar(value=self._translate("message.ready"))
        ttk.Label(self, textvariable=self._message, anchor="w", style="Status.TLabel").pack(
            fill="x",
            expand=True,
        )

    def set_message(self, message: str) -> None:
        """Display the supplied status message."""
        self._message.set(message)

    def clear_message(self) -> None:
        """Restore the default Ready status message."""
        self._message.set(self._translate("message.ready"))

    def refresh_texts(self) -> None:
        """Refresh the default status text without replacing a real status."""
        if self._message.get() in {"Ready", "Hazır"}:
            self.clear_message()
