"""TTK dialog for creating a new project."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import messagebox, ttk

from i18n.translator import Translator
from ui.theme.spacing import LG, MD, SM


class NewProjectDialog:
    """Collect project metadata and return it to the caller synchronously."""

    def __init__(
        self,
        parent: tk.Misc,
        translate: Callable[[str], str] | None = None,
        localization_owner: object | None = None,
    ) -> None:
        """Create and display a modal dialog for a new project."""
        self._translate = translate or Translator().translate
        self._localization_owner = localization_owner
        self.result: tuple[str, str, str] | None = None
        self._dialog = tk.Toplevel(parent)
        self._dialog.title(self._translate("menu.file.new_project"))
        self._dialog.transient(parent)
        self._dialog.resizable(False, False)
        self._dialog.protocol("WM_DELETE_WINDOW", self._cancel)
        self._create_widgets()
        self._dialog.grab_set()
        self._dialog.wait_visibility()
        self._dialog.lift()
        self._name_entry.focus_set()
        self._dialog.bind("<Return>", self._submit)
        self._dialog.bind("<Control-Return>", self._submit)
        self._dialog.bind("<Escape>", self._cancel)
        if localization_owner is not None:
            register = getattr(localization_owner, "register_localizable", None)
            if callable(register):
                register(self)

    def show(self) -> tuple[str, str, str] | None:
        """Wait for completion and return normalized metadata or ``None``."""
        self._dialog.wait_window()
        return self.result

    def _create_widgets(self) -> None:
        content = ttk.Frame(self._dialog, style="Dialog.TFrame", padding=LG)
        content.grid(row=0, column=0, sticky="nsew")
        content.columnconfigure(1, weight=1)

        self._name_label = ttk.Label(content, text="")
        self._name_label.grid(
            row=0,
            column=0,
            sticky="w",
        )
        self._name_entry = ttk.Entry(content, width=54)
        self._name_entry.grid(row=0, column=1, sticky="ew", padx=(MD, 0))

        self._description_label = ttk.Label(content, text="")
        self._description_label.grid(
            row=1,
            column=0,
            sticky="nw",
            pady=(MD, 0),
        )
        self._description_text = tk.Text(content, width=54, height=4, wrap="word")
        self._description_text.grid(
            row=1,
            column=1,
            sticky="ew",
            padx=(MD, 0),
            pady=(MD, 0),
        )

        self._notes_label = ttk.Label(content, text="")
        self._notes_label.grid(
            row=2,
            column=0,
            sticky="nw",
            pady=(MD, 0),
        )
        self._notes_text = tk.Text(content, width=54, height=5, wrap="word")
        self._notes_text.grid(
            row=2,
            column=1,
            sticky="ew",
            padx=(MD, 0),
            pady=(MD, 0),
        )

        actions = ttk.Frame(content)
        actions.grid(row=3, column=1, sticky="e", pady=(LG, 0))
        self._cancel_button = ttk.Button(actions, command=self._cancel, style="Neutral.TButton")
        self._cancel_button.pack(
            side="left"
        )
        self._submit_button = ttk.Button(actions, command=self._submit, style="Success.TButton")
        self._submit_button.pack(
            side="left",
            padx=(SM, 0),
        )
        self.refresh_texts()

    def refresh_texts(self) -> None:
        """Refresh this open dialog without altering entered project metadata."""
        self._dialog.title(self._translate("menu.file.new_project"))
        self._name_label.configure(text=f"{self._translate('project.name')}:")
        self._description_label.configure(text=f"{self._translate('project.description')}:")
        self._notes_label.configure(text=f"{self._translate('project.notes')}:")
        self._cancel_button.configure(text=self._translate("common.cancel"))
        self._submit_button.configure(text=self._translate("common.save"))

    def _submit(self, event: tk.Event[tk.Misc] | None = None) -> str:
        """Validate and submit the entered project details."""
        name = self._name_entry.get().strip()
        if not name:
            messagebox.showerror(
                self._translate("dialog.error"),
                self._translate("validation.required", field_name=self._translate("field.project_name")),
                parent=self._dialog,
            )
            self._name_entry.focus_set()
            return "break"
        description = self._description_text.get("1.0", "end-1c").strip()
        notes = self._notes_text.get("1.0", "end-1c").strip()
        self.result = (name, description, notes)
        self._dialog.grab_release()
        self._destroy()
        return "break"

    def _cancel(self, event: tk.Event[tk.Misc] | None = None) -> str:
        """Close the dialog without submitting project details."""
        self._dialog.grab_release()
        self._destroy()
        return "break"

    def _destroy(self) -> None:
        """Unregister then destroy the dialog exactly once."""
        if self._localization_owner is not None:
            unregister = getattr(self._localization_owner, "unregister_localizable", None)
            if callable(unregister):
                unregister(self)
        self._dialog.destroy()
