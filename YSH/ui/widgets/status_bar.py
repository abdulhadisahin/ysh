"""Reusable application status bar widget."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class StatusBar(ttk.Frame):
    """Displays concise application status messages in a ttk frame."""

    def __init__(self, parent: tk.Misc) -> None:
        """Create a status bar with the default Ready message."""
        super().__init__(parent, padding=(12, 6))
        self._message = tk.StringVar(value="Ready")
        ttk.Label(self, textvariable=self._message, anchor="w").pack(
            fill="x",
            expand=True,
        )

    def set_message(self, message: str) -> None:
        """Display the supplied status message."""
        self._message.set(message)

    def clear_message(self) -> None:
        """Restore the default Ready status message."""
        self._message.set("Ready")
