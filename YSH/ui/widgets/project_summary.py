"""Reusable ttk widget for displaying an active project summary."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from core.project import Project


class ProjectSummary(ttk.LabelFrame):
    """Displays the currently active project's descriptive metadata."""

    def __init__(self, parent: tk.Misc) -> None:
        """Create an empty project summary widget."""
        super().__init__(parent, text="Active Project", padding=16)
        self._values = {
            "name": tk.StringVar(),
            "description": tk.StringVar(),
            "notes": tk.StringVar(),
            "created_at": tk.StringVar(),
            "modified_at": tk.StringVar(),
        }
        self._create_fields()
        self.clear()

    def set_project(self, project: Project) -> None:
        """Display all summary fields for the supplied project."""
        self._values["name"].set(project.display_name)
        self._values["description"].set(project.description)
        self._values["notes"].set(project.notes)
        self._values["created_at"].set(
            project.created_at.astimezone().strftime("%Y-%m-%d %H:%M")
        )
        self._values["modified_at"].set(
            project.modified_at.astimezone().strftime("%Y-%m-%d %H:%M")
        )

    def clear(self) -> None:
        """Clear all displayed project summary fields."""
        for value in self._values.values():
            value.set("")

    def _create_fields(self) -> None:
        labels = (
            ("Project Name", "name"),
            ("Description", "description"),
            ("Notes", "notes"),
            ("Created At", "created_at"),
            ("Modified At", "modified_at"),
        )
        self.columnconfigure(1, weight=1)
        for row, (label, value_name) in enumerate(labels):
            ttk.Label(self, text=f"{label}:").grid(
                row=row,
                column=0,
                sticky="nw",
                padx=(0, 10),
                pady=(0, 8),
            )
            ttk.Label(
                self,
                textvariable=self._values[value_name],
                wraplength=540,
            ).grid(row=row, column=1, sticky="ew", pady=(0, 8))
