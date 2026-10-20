"""Small native disclosure used for optional provenance and technical details."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class DetailDisclosure(ttk.Frame):
    """Keep a summary visible while the complete original detail remains available."""

    def __init__(self, parent: tk.Misc, title: str, summary: str = "", *,
                 wraplength: int = 620, style: str = "", summary_style: str = "",
                 body_style: str = "") -> None:
        """Create a collapsed detail body without discarding any of its data."""
        super().__init__(parent, style=style)
        self.columnconfigure(0, weight=1)
        self._title = title
        self.expanded = False
        self._toggle = ttk.Button(self, text=f"▸ {title}", command=self.toggle,
                                  style="Secondary.TButton")
        self._toggle.grid(row=0, column=0, sticky="w")
        if summary:
            ttk.Label(self, text=summary if len(summary) <= 180 else summary[:177] + "…", wraplength=wraplength, justify="left", style=summary_style).grid(
                row=1, column=0, sticky="ew", pady=(3, 0))
        self.body = ttk.Frame(self, style=body_style)
        self.body.grid(row=2, column=0, sticky="ew", pady=(6, 0))
        self.body.grid_remove()

    def toggle(self) -> None:
        """Reveal or hide details without querying or modifying their source."""
        self.expanded = not self.expanded
        (self.body.grid if self.expanded else self.body.grid_remove)()
        self._toggle.configure(text=f"{'▾' if self.expanded else '▸'} {self._title}")
