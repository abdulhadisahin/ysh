"""Modal project-selection dialog for confirmed project deletion."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import ttk
from uuid import UUID

from services.project_service import ProjectService
from i18n.translator import Translator
from ui.theme.spacing import LG, MD, SM


class DeleteProjectDialog:
    """Return the UUID of a project selected for deletion."""

    def __init__(
        self,
        parent: tk.Misc,
        projects: ProjectService,
        translate: Callable[[str], str] | None = None,
        localization_owner: object | None = None,
    ) -> None:
        """Create the modal project picker through the service layer."""
        self.result: UUID | None = None
        self._translate = translate or Translator().translate
        self._localization_owner = localization_owner
        self._dialog = tk.Toplevel(parent)
        self._dialog.title(self._translate("dialog.delete_project"))
        self._dialog.transient(parent)
        self._dialog.protocol("WM_DELETE_WINDOW", self._cancel)
        frame = ttk.Frame(self._dialog, style="Dialog.TFrame", padding=LG)
        frame.grid(sticky="nsew")
        self._tree = ttk.Treeview(frame, columns=("name", "description"), show="headings", selectmode="browse", height=10)
        self._tree.heading("name", text=self._translate("field.project_name"))
        self._tree.heading("description", text=self._translate("project.description"))
        self._tree.column("name", width=240)
        self._tree.column("description", width=380)
        self._tree.grid(row=0, column=0, columnspan=2, sticky="nsew")
        for project in projects.get_all_projects():
            self._tree.insert("", "end", iid=str(project.id), values=(project.display_name, project.description))
        self._cancel_button = ttk.Button(
            frame, command=self._cancel, style="Neutral.TButton"
        )
        self._cancel_button.grid(row=1, column=0, sticky="e", pady=(MD, 0))
        self._delete_button = ttk.Button(
            frame, command=self._select, style="Danger.TButton"
        )
        self._delete_button.grid(
            row=1, column=1, sticky="w", padx=(SM, 0), pady=(MD, 0)
        )
        self._dialog.grab_set()
        self._dialog.bind("<Return>", self._select)
        self._dialog.bind("<Escape>", self._cancel)
        self.refresh_texts()
        if localization_owner is not None:
            register = getattr(localization_owner, "register_localizable", None)
            if callable(register):
                register(self)

    def show(self) -> UUID | None:
        """Wait for selection and return a project UUID or ``None``."""
        self._dialog.wait_window()
        return self.result

    def refresh_texts(self) -> None:
        """Refresh labels without reloading rows or changing their selection."""
        self._dialog.title(self._translate("dialog.delete_project"))
        self._tree.heading("name", text=self._translate("field.project_name"))
        self._tree.heading(
            "description", text=self._translate("project.description")
        )
        self._cancel_button.configure(text=self._translate("common.cancel"))
        self._delete_button.configure(text=self._translate("common.delete"))

    def _select(self, _event: object | None = None) -> str:
        selected = self._tree.selection()
        if selected:
            self.result = UUID(selected[0])
            self._dialog.grab_release()
            self._destroy()
        return "break"

    def _cancel(self, _event: object | None = None) -> str:
        self._dialog.grab_release()
        self._destroy()
        return "break"

    def _destroy(self) -> None:
        """Unregister and destroy the dialog after cancellation or selection."""
        localization_owner = getattr(self, "_localization_owner", None)
        if localization_owner is not None:
            unregister = getattr(localization_owner, "unregister_localizable", None)
            if callable(unregister):
                unregister(self)
        self._dialog.destroy()
