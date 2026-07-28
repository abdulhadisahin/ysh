"""TTK dialog for creating a new project."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import messagebox, ttk


class NewProjectDialog:
    """Collects validated project details and submits them to a caller callback."""

    def __init__(
        self,
        parent: tk.Misc,
        on_submit: Callable[[str, str, str], bool],
    ) -> None:
        """Create and display a modal dialog for a new project."""
        self._on_submit = on_submit
        self._dialog = tk.Toplevel(parent)
        self._dialog.title("New Project")
        self._dialog.transient(parent)
        self._dialog.resizable(False, False)
        self._dialog.protocol("WM_DELETE_WINDOW", self._dialog.destroy)
        self._create_widgets()
        self._dialog.grab_set()
        self._name_entry.focus_set()
        self._dialog.bind("<Return>", self._submit)
        self._dialog.bind("<Control-Return>", self._submit)
        self._dialog.bind("<Escape>", self._cancel)

    def _create_widgets(self) -> None:
        content = ttk.Frame(self._dialog, padding=18)
        content.grid(row=0, column=0, sticky="nsew")
        content.columnconfigure(1, weight=1)

        ttk.Label(content, text="Project Name:").grid(
            row=0,
            column=0,
            sticky="w",
        )
        self._name_entry = ttk.Entry(content, width=54)
        self._name_entry.grid(row=0, column=1, sticky="ew", padx=(10, 0))

        ttk.Label(content, text="Description:").grid(
            row=1,
            column=0,
            sticky="nw",
            pady=(12, 0),
        )
        self._description_text = tk.Text(content, width=54, height=4, wrap="word")
        self._description_text.grid(
            row=1,
            column=1,
            sticky="ew",
            padx=(10, 0),
            pady=(12, 0),
        )

        ttk.Label(content, text="Notes:").grid(
            row=2,
            column=0,
            sticky="nw",
            pady=(12, 0),
        )
        self._notes_text = tk.Text(content, width=54, height=5, wrap="word")
        self._notes_text.grid(
            row=2,
            column=1,
            sticky="ew",
            padx=(10, 0),
            pady=(12, 0),
        )

        actions = ttk.Frame(content)
        actions.grid(row=3, column=1, sticky="e", pady=(18, 0))
        ttk.Button(actions, text="Cancel", command=self._cancel).pack(
            side="left"
        )
        ttk.Button(actions, text="OK", command=self._submit).pack(
            side="left",
            padx=(8, 0),
        )

    def _submit(self, event: tk.Event[tk.Misc] | None = None) -> str:
        """Validate and submit the entered project details."""
        name = self._name_entry.get().strip()
        if not name:
            messagebox.showerror(
                "Project Name Required",
                "Enter a project name before continuing.",
                parent=self._dialog,
            )
            self._name_entry.focus_set()
            return "break"
        description = self._description_text.get("1.0", "end-1c").strip()
        notes = self._notes_text.get("1.0", "end-1c").strip()
        if self._on_submit(name, description, notes):
            self._dialog.destroy()
        return "break"

    def _cancel(self, event: tk.Event[tk.Misc] | None = None) -> str:
        """Close the dialog without submitting project details."""
        self._dialog.destroy()
        return "break"
