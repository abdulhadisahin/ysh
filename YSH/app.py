"""Application composition and lifecycle management for YSH."""

from __future__ import annotations

from pathlib import Path
import tkinter as tk

from database.project_database import ProjectDatabase
from repositories.project_repository import ProjectRepository
from services.project_service import ProjectService
from ui.main_window import MainWindow


class YSHApplication:
    """Initializes YSH infrastructure and owns its desktop application lifecycle."""

    def __init__(self) -> None:
        """Create the application dependencies without starting the event loop."""
        self._application_root = Path(__file__).resolve().parent
        self._project_database = ProjectDatabase()
        self._project_repository = ProjectRepository(self._project_database)
        self._project_service = ProjectService(self._project_repository)
        self._root: tk.Tk | None = None
        self._main_window: MainWindow | None = None

    def run(self) -> None:
        """Initialize local resources and start the main window."""
        self._initialize_application()
        self._root = tk.Tk()
        print("START: Tk root created")
        self._main_window = MainWindow(
            root=self._root,
            project_service=self._project_service,
            on_close=self.shutdown,
        )
        print("START: entering mainloop")
        self._root.mainloop()

    def shutdown(self) -> None:
        """Release application resources before the main window closes."""
        self._main_window = None
        self._root = None

    def _initialize_application(self) -> None:
        for directory_name in ("libraries", "reports", "tests"):
            (self._application_root / directory_name).mkdir(exist_ok=True)
        self._project_database.initialize()
