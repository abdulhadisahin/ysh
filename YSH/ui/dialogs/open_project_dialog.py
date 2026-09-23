"""TTK dialog for selecting and opening an existing project."""

from __future__ import annotations

import logging
import tkinter as tk
from collections.abc import Callable
from datetime import datetime
from tkinter import messagebox, ttk
from uuid import UUID

from core.project import Project
from services.project_service import ProjectNotFoundError, ProjectService
from i18n.translator import Translator
from ui.theme.spacing import LG, MD, SM

LOGGER = logging.getLogger(__name__)


class OpenProjectDialog:
    """Lists persisted projects and returns a user-selected project result."""

    def __init__(
        self,
        parent: tk.Misc,
        project_service: ProjectService,
        translate: Callable[[str], str] | None = None,
        localization_owner: object | None = None,
    ) -> None:
        """Create a visible modal dialog for selecting an existing project."""
        self._translate = translate or Translator().translate
        self._localization_owner = localization_owner
        self._project_service = project_service
        self.result: Project | None = None
        self._dialog = tk.Toplevel(parent)
        self._dialog.title(self._translate("menu.file.open_project"))
        self._dialog.geometry("900x440")
        self._dialog.minsize(760, 360)
        self._dialog.transient(parent)
        self._dialog.protocol("WM_DELETE_WINDOW", self._cancel)
        self._create_widgets()
        self._load_projects()
        self._dialog.grab_set()
        self._dialog.wait_visibility()
        self._dialog.lift()
        self._projects_tree.focus_set()
        self._dialog.bind("<Return>", self._open_selected)
        self._dialog.bind("<Escape>", self._cancel)
        if localization_owner is not None:
            register = getattr(localization_owner, "register_localizable", None)
            if callable(register):
                register(self)

    def show(self) -> Project | None:
        """Wait for dialog completion and return the selected project, if any."""
        self._dialog.focus_set()
        self._dialog.wait_window()
        return self.result

    def _create_widgets(self) -> None:
        content = ttk.Frame(self._dialog, style="Dialog.TFrame", padding=LG)
        content.grid(row=0, column=0, sticky="nsew")
        content.columnconfigure(0, weight=1)
        content.rowconfigure(1, weight=1)
        self._dialog.columnconfigure(0, weight=1)
        self._dialog.rowconfigure(0, weight=1)

        self._empty_message = ttk.Label(content, text="")
        self._empty_message.grid(row=0, column=0, sticky="w", pady=(0, SM))

        self._projects_tree = ttk.Treeview(
            content,
            columns=("name", "description", "created_at", "modified_at"),
            show="headings",
            selectmode="browse",
        )
        for column, label, width in (
            ("name", self._translate("field.project_name"), 200),
            ("description", self._translate("project.description"), 280),
            ("created_at", self._translate("project.created"), 140),
            ("modified_at", self._translate("project.modified"), 140),
        ):
            self._projects_tree.heading(column, text=label)
            self._projects_tree.column(column, width=width, anchor="w")
        self._projects_tree.grid(row=1, column=0, sticky="nsew")
        self._projects_tree.bind("<<TreeviewSelect>>", self._update_open_button)
        self._projects_tree.bind("<Double-1>", self._open_selected)

        actions = ttk.Frame(content)
        actions.grid(row=2, column=0, sticky="e", pady=(MD, 0))
        self._cancel_button = ttk.Button(
            actions, command=self._cancel, style="Neutral.TButton"
        )
        self._cancel_button.pack(side="left")
        self._open_button = ttk.Button(
            actions,
            text="Open",
            command=self._open_selected,
            state="disabled",
            style="Warning.TButton",
        )
        self._open_button.pack(side="left", padx=(SM, 0))
        self.refresh_texts()

    def refresh_texts(self) -> None:
        """Refresh labels in place while preserving the selected project row."""
        self._dialog.title(self._translate("menu.file.open_project"))
        headings = {
            "name": self._translate("field.project_name"),
            "description": self._translate("project.description"),
            "created_at": self._translate("project.created"),
            "modified_at": self._translate("project.modified"),
        }
        for column, label in headings.items():
            self._projects_tree.heading(column, text=label)
        self._cancel_button.configure(text=self._translate("common.cancel"))
        self._open_button.configure(text=self._translate("action.open"))
        if not self._projects_tree.get_children():
            self._empty_message.configure(
                text=self._translate("message.no_projects_available")
            )
        elif not self._projects_tree.selection():
            self._empty_message.configure(
                text=self._translate("message.select_project_to_open")
            )

    def _load_projects(self) -> None:
        for item_id in self._projects_tree.get_children():
            self._projects_tree.delete(item_id)
        self._open_button.configure(state="disabled")
        try:
            projects = sorted(
                self._project_service.get_all_projects(),
                key=lambda project: project.modified_at,
                reverse=True,
            )
        except Exception:
            LOGGER.exception("Unable to load projects for the Open Project dialog.")
            self._empty_message.configure(text=self._translate("validation.unexpected_error"))
            messagebox.showerror(self._translate("dialog.error"), self._translate("validation.unexpected_error"), parent=self._dialog)
            return
        if not projects:
            self._empty_message.configure(text=self._translate("message.no_projects_available"))
            return
        self._empty_message.configure(text=self._translate("message.select_project_to_open"))
        for project in projects:
            self._projects_tree.insert(
                "",
                "end",
                iid=str(project.id),
                values=(
                    project.display_name,
                    project.description,
                    self._format_datetime(project.created_at),
                    self._format_datetime(project.modified_at),
                ),
            )

    def _update_open_button(self, event: tk.Event[tk.Misc] | None = None) -> None:
        """Enable Open only when a Treeview row is selected."""
        del event
        state = "normal" if self._projects_tree.selection() else "disabled"
        self._open_button.configure(state=state)

    def _open_selected(self, event: tk.Event[tk.Misc] | None = None) -> str:
        """Set the selected project result and close the dialog."""
        if event is not None:
            clicked_item = self._projects_tree.identify_row(event.y)
            if clicked_item:
                self._projects_tree.selection_set(clicked_item)
        selected_items = self._projects_tree.selection()
        if not selected_items:
            return "break"
        try:
            project = self._project_service.get_project(UUID(selected_items[0]))
        except (ProjectNotFoundError, ValueError):
            messagebox.showerror(
                self._translate("dialog.error"),
                self._translate("validation.project_not_found"),
                parent=self._dialog,
            )
            self._load_projects()
            return "break"
        except Exception:
            LOGGER.exception("Unable to open the selected project.")
            messagebox.showerror(
                self._translate("dialog.error"),
                self._translate("validation.unexpected_error"),
                parent=self._dialog,
            )
            return "break"
        self.result = project
        self._dialog.grab_release()
        self._destroy()
        return "break"

    def _cancel(self, event: tk.Event[tk.Misc] | None = None) -> str:
        """Close the dialog without selecting a project."""
        del event
        self._dialog.grab_release()
        self._destroy()
        return "break"

    def _destroy(self) -> None:
        """Unregister and destroy the dialog once it has completed."""
        localization_owner = getattr(self, "_localization_owner", None)
        if localization_owner is not None:
            unregister = getattr(localization_owner, "unregister_localizable", None)
            if callable(unregister):
                unregister(self)
        self._dialog.destroy()

    @staticmethod
    def _format_datetime(value: datetime) -> str:
        """Format a project timestamp for the project-selection table."""
        return value.astimezone().strftime("%Y-%m-%d %H:%M")
