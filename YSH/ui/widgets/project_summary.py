"""Reusable ttk widget for displaying an active project summary."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import ttk

from core.project import Project
from i18n.translator import Translator
from ui.theme.spacing import MD, SM


class ProjectSummary(ttk.Frame):
    """Display the active project as a compact sidebar information card."""

    def __init__(
        self,
        parent: tk.Misc,
        translate: Callable[[str], str] | None = None,
    ) -> None:
        """Create an empty, deliberately quiet project-summary card."""
        self._translate = translate or Translator().translate
        super().__init__(parent, padding=MD, style="ActiveProject.TFrame")
        self.columnconfigure(0, weight=1)
        self._values = {
            "name": tk.StringVar(),
            "description": tk.StringVar(),
            "notes": tk.StringVar(),
            "created_at": tk.StringVar(),
            "modified_at": tk.StringVar(),
        }
        self._field_labels: dict[str, ttk.Label] = {}
        self._value_labels: dict[str, ttk.Label] = {}
        self._title = ttk.Label(
            self,
            text=self._translate("project.active"),
            style="ActiveProjectTitle.TLabel",
        )
        self._title.grid(row=0, column=0, sticky="w", pady=(0, SM))
        self._create_fields()
        self.clear()

    def set_project(self, project: Project) -> None:
        """Display all summary fields for the supplied project."""
        self._values["name"].set(project.display_name)
        self._values["description"].set(project.description or "—")
        self._values["notes"].set(project.notes or "—")
        self._values["created_at"].set(project.created_at.astimezone().strftime("%Y-%m-%d %H:%M"))
        self._values["modified_at"].set(project.modified_at.astimezone().strftime("%Y-%m-%d %H:%M"))
        self._set_detail_visibility(True)

    def clear(self) -> None:
        """Clear all displayed project summary fields."""
        for value in self._values.values():
            value.set("")
        self._values["name"].set(self._translate("project.none_active"))
        self._set_detail_visibility(False)

    def refresh_texts(self) -> None:
        """Refresh translated shell labels without changing active project metadata."""
        self._title.configure(text=self._translate("project.active"))
        labels = {
            "name": "project.name",
            "description": "project.description",
            "notes": "project.notes",
            "created_at": "project.created",
            "modified_at": "project.modified",
        }
        for value_name, key in labels.items():
            self._field_labels[value_name].configure(text=f"{self._translate(key)}:")
        if not any(
            self._values[name].get()
            for name in ("description", "notes", "created_at", "modified_at")
        ):
            self._values["name"].set(self._translate("project.none_active"))
            self._set_detail_visibility(False)

    def _create_fields(self) -> None:
        labels = (
            ("project.name", "name"),
            ("project.description", "description"),
            ("project.notes", "notes"),
            ("project.created", "created_at"),
            ("project.modified", "modified_at"),
        )
        for row, (label_key, value_name) in enumerate(labels):
            label = ttk.Label(self, text=f"{self._translate(label_key)}:", style="ActiveProjectLabel.TLabel")
            label.grid(
                row=row + 1,
                column=0,
                sticky="nw",
                pady=(0, SM // 2),
            )
            self._field_labels[value_name] = label
            value_label = ttk.Label(
                self,
                textvariable=self._values[value_name],
                style=(
                    "ActiveProjectName.TLabel"
                    if value_name == "name"
                    else "ActiveProjectValue.TLabel"
                ),
                wraplength=250,
                justify="left",
            )
            value_label.grid(
                row=row + 1,
                column=0,
                sticky="ew",
                pady=(0, SM if value_name == "name" else SM // 2),
            )
            self._value_labels[value_name] = value_label

    def _set_detail_visibility(self, visible: bool) -> None:
        """Show metadata only when an active project provides meaningful detail."""
        for value_name in (
            "name",
            "description",
            "notes",
            "created_at",
            "modified_at",
        ):
            label = self._field_labels[value_name]
            value = self._value_labels[value_name]
            if visible:
                label.grid()
                value.grid()
            else:
                label.grid_remove()
                value.grid_remove()
