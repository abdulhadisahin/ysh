"""Modal dialog that collects metadata for a copied project workspace."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import messagebox, ttk

from i18n.translator import Translator
from ui.theme.spacing import LG, MD, SM


class SaveProjectAsDialog:
    """Collect metadata for saving the current workspace as a new project."""

    def __init__(
        self,
        parent: tk.Misc,
        translate: Callable[[str], str] | None = None,
        localization_owner: object | None = None,
    ) -> None:
        """Create the modal dialog without persistence dependencies."""
        self.result: tuple[str, str, str] | None = None
        self._translate = translate or Translator().translate
        self._localization_owner = localization_owner
        self._dialog = tk.Toplevel(parent)
        self._dialog.title(self._translate("dialog.save_project_as"))
        self._dialog.transient(parent)
        self._dialog.protocol("WM_DELETE_WINDOW", self._cancel)
        frame = ttk.Frame(self._dialog, style="Dialog.TFrame", padding=LG)
        frame.grid(sticky="nsew")
        self._name_label = ttk.Label(frame)
        self._name_label.grid(row=0, column=0, sticky="w")
        self._name = ttk.Entry(frame, width=52)
        self._name.grid(row=0, column=1, sticky="ew", padx=(SM, 0))
        self._description_label = ttk.Label(frame)
        self._description_label.grid(row=1, column=0, sticky="nw", pady=(SM, 0))
        self._description = tk.Text(frame, width=52, height=4, wrap="word")
        self._description.grid(row=1, column=1, pady=(SM, 0))
        self._notes_label = ttk.Label(frame)
        self._notes_label.grid(row=2, column=0, sticky="nw", pady=(SM, 0))
        self._notes = tk.Text(frame, width=52, height=5, wrap="word")
        self._notes.grid(row=2, column=1, pady=(SM, 0))
        actions = ttk.Frame(frame)
        actions.grid(row=3, column=1, sticky="e", pady=(MD, 0))
        self._cancel_button = ttk.Button(actions, command=self._cancel, style="Neutral.TButton")
        self._cancel_button.pack(side="left")
        self._submit_button = ttk.Button(actions, command=self._submit, style="Success.TButton")
        self._submit_button.pack(side="left", padx=(SM, 0))
        self._dialog.grab_set()
        self._name.focus_set()
        self._dialog.bind("<Return>", self._submit)
        self._dialog.bind("<Escape>", self._cancel)
        self.refresh_texts()
        if localization_owner is not None:
            register = getattr(localization_owner, "register_localizable", None)
            if callable(register):
                register(self)

    def show(self) -> tuple[str, str, str] | None:
        """Wait for completion and return normalized metadata, if supplied."""
        self._dialog.wait_window()
        return self.result

    def refresh_texts(self) -> None:
        """Refresh text without changing entered save-as metadata."""
        self._dialog.title(self._translate("dialog.save_project_as"))
        self._name_label.configure(text=f"{self._translate('project.name')}:")
        self._description_label.configure(text=f"{self._translate('project.description')}:")
        self._notes_label.configure(text=f"{self._translate('project.notes')}:")
        self._cancel_button.configure(text=self._translate("common.cancel"))
        self._submit_button.configure(text=self._translate("menu.file.save_project_as"))

    def _submit(self, _event: object | None = None) -> str:
        name = self._name.get().strip()
        if not name:
            messagebox.showerror(
                self._translate("dialog.error"),
                self._translate(
                    "validation.required",
                    field_name=self._translate("field.project_name"),
                ),
                parent=self._dialog,
            )
            self._name.focus_set()
            return "break"
        self.result = (name, self._description.get("1.0", "end-1c").strip(), self._notes.get("1.0", "end-1c").strip())
        self._dialog.grab_release()
        self._destroy()
        return "break"

    def _cancel(self, _event: object | None = None) -> str:
        self._dialog.grab_release()
        self._destroy()
        return "break"

    def _destroy(self) -> None:
        """Unregister and destroy this completed dialog."""
        if self._localization_owner is not None:
            unregister = getattr(self._localization_owner, "unregister_localizable", None)
            if callable(unregister):
                unregister(self)
        self._dialog.destroy()
