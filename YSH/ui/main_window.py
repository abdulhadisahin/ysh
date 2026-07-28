"""Main Tkinter window for YSH."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import messagebox, ttk

from core.constants import (
    WINDOW_HEIGHT,
    WINDOW_MINIMUM_HEIGHT,
    WINDOW_MINIMUM_WIDTH,
    WINDOW_WIDTH,
)
from core.project import Project
from services.project_service import (
    ProjectConflictError,
    ProjectService,
    ProjectValidationError,
)
from ui.dialogs.new_project_dialog import NewProjectDialog
from ui.dialogs.open_project_dialog import OpenProjectDialog
from ui.widgets.project_summary import ProjectSummary
from ui.widgets.status_bar import StatusBar


class MainWindow:
    """Creates and runs the primary YSH desktop window."""

    def __init__(
        self,
        project_service: ProjectService,
        on_close: Callable[[], None],
    ) -> None:
        """Create the window and configure its layout and close lifecycle."""
        self._on_close = on_close
        self._project_service = project_service
        self._active_project: Project | None = None
        self._root = tk.Tk()
        self._root.title("YSH")
        self._root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self._root.minsize(WINDOW_MINIMUM_WIDTH, WINDOW_MINIMUM_HEIGHT)
        self._root.protocol("WM_DELETE_WINDOW", self._close)
        self._root.iconname("YSH")
        self._create_layout()
        self._refresh_projects()

    def run(self) -> None:
        """Start the Tkinter event loop."""
        self._root.mainloop()

    def _create_layout(self) -> None:
        self._root.columnconfigure(0, weight=1)
        self._root.rowconfigure(3, weight=1)
        self._create_menu_bar()

        toolbar = ttk.Frame(self._root, padding=(12, 8))
        toolbar.grid(row=1, column=0, sticky="ew")
        ttk.Button(toolbar, text="New Project", command=self._open_new_project).pack(
            side="left"
        )
        ttk.Button(toolbar, text="Open Project", command=self._open_project).pack(
            side="left",
            padx=(8, 0),
        )
        ttk.Button(toolbar, text="Refresh", command=self._refresh_projects).pack(
            side="left", padx=(8, 0)
        )

        header = ttk.Frame(self._root, padding=(24, 18))
        header.grid(row=2, column=0, sticky="ew")
        ttk.Label(header, text="YSH", font=("Segoe UI", 20, "bold")).pack(
            side="left"
        )
        ttk.Label(header, text="Engineering Calculation System").pack(
            side="left", padx=(12, 0)
        )

        workspace = ttk.Frame(self._root, padding=(24, 0, 24, 24))
        workspace.grid(row=3, column=0, sticky="nsew")
        workspace.columnconfigure(1, weight=1)
        workspace.rowconfigure(0, weight=1)

        self._root.rowconfigure(3, weight=1)
        navigation = ttk.LabelFrame(workspace, text="Workspace", padding=16)
        navigation.grid(row=0, column=0, sticky="nsw")
        ttk.Label(navigation, text="Projects").pack(anchor="w")
        ttk.Label(
            navigation,
            text="Use New Project to create a local calculation project.",
            wraplength=180,
        ).pack(anchor="w", pady=(10, 0))

        content = ttk.Frame(workspace)
        content.grid(row=0, column=1, sticky="nsew", padx=(18, 0))
        content.columnconfigure(0, weight=1)
        content.rowconfigure(1, weight=1)
        self._project_summary = ProjectSummary(content)
        self._project_summary.grid(row=0, column=0, sticky="ew", pady=(0, 16))

        projects_frame = ttk.LabelFrame(content, text="Projects", padding=16)
        projects_frame.grid(row=1, column=0, sticky="nsew")
        projects_frame.columnconfigure(0, weight=1)
        projects_frame.rowconfigure(0, weight=1)
        self._projects_tree = ttk.Treeview(
            projects_frame,
            columns=("name", "description", "modified"),
            show="headings",
        )
        self._projects_tree.heading("name", text="Project")
        self._projects_tree.heading("description", text="Description")
        self._projects_tree.heading("modified", text="Last Modified")
        self._projects_tree.column("name", width=260, anchor="w")
        self._projects_tree.column("description", width=520, anchor="w")
        self._projects_tree.column("modified", width=180, anchor="w")
        self._projects_tree.grid(row=0, column=0, sticky="nsew")

        self._status_bar = StatusBar(self._root)
        self._status_bar.grid(row=4, column=0, sticky="ew")

    def _create_menu_bar(self) -> None:
        menu_bar = tk.Menu(self._root)
        self._file_menu = tk.Menu(menu_bar, tearoff=False)
        self._file_menu.add_command(
            label="New Project",
            command=self._open_new_project,
        )
        self._file_menu.add_command(label="Open Project", command=self._open_project)
        self._file_menu.add_command(label="Save Project", state="disabled")
        self._file_menu.add_command(
            label="Close Project",
            command=self._close_project,
            state="disabled",
        )
        self._file_menu.add_separator()
        self._file_menu.add_command(label="Exit", command=self._close)
        menu_bar.add_cascade(label="File", menu=self._file_menu)

        project_menu = tk.Menu(menu_bar, tearoff=False)
        project_menu.add_command(label="Refresh", command=self._refresh_projects)
        menu_bar.add_cascade(label="Projects", menu=project_menu)

        help_menu = tk.Menu(menu_bar, tearoff=False)
        help_menu.add_command(label="About", command=self._show_about)
        menu_bar.add_cascade(label="Help", menu=help_menu)
        self._root.configure(menu=menu_bar)

    def _open_new_project(self) -> None:
        NewProjectDialog(self._root, self._create_project)

    def _open_project(self) -> None:
        OpenProjectDialog(
            self._root,
            self._project_service,
            self._activate_project,
        )

    def _create_project(
        self,
        name: str,
        description: str,
        notes: str,
    ) -> bool:
        try:
            project = self._project_service.create_project(name, description, notes)
        except ProjectValidationError as error:
            messagebox.showerror("Invalid Project", str(error), parent=self._root)
            return False
        except ProjectConflictError as error:
            messagebox.showerror(
                "Duplicate Project Name",
                str(error),
                parent=self._root,
            )
            return False
        except ValueError as error:
            messagebox.showerror(
                "Cannot Create Project",
                str(error),
                parent=self._root,
            )
            return False
        self._refresh_projects()
        self._activate_project(project, "Project created successfully")
        return True

    def _activate_project(
        self,
        project: Project,
        message: str = "Project opened successfully",
    ) -> None:
        self._active_project = project
        self._root.title(f"YSH - {project.display_name}")
        self._project_summary.set_project(project)
        self._file_menu.entryconfigure("Close Project", state="normal")
        self._status_bar.set_message(message)

    def _close_project(self) -> None:
        self._active_project = None
        self._root.title("YSH")
        self._project_summary.clear()
        self._file_menu.entryconfigure("Close Project", state="disabled")
        self._status_bar.set_message("Project closed")

    def _refresh_projects(self) -> None:
        for item_id in self._projects_tree.get_children():
            self._projects_tree.delete(item_id)
        for project in self._project_service.list_projects():
            self._add_project(project)

    def _add_project(self, project: Project) -> None:
        self._projects_tree.insert(
            "",
            "end",
            iid=str(project.id),
            values=(
                project.display_name,
                project.description,
                project.modified_at.astimezone().strftime("%Y-%m-%d %H:%M"),
            ),
        )

    def _show_about(self) -> None:
        messagebox.showinfo(
            "About YSH",
            "YSH - Engineering Calculation System\nOffline Windows desktop application.",
            parent=self._root,
        )

    def _close(self) -> None:
        self._on_close()
        self._root.destroy()
