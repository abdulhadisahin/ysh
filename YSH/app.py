"""Application composition and lifecycle management for YSH."""

from __future__ import annotations

from pathlib import Path
import tkinter as tk

from database.project_database import ProjectDatabase
from database.library_database import LibraryDatabase
from repositories.engineering_constant_repository import EngineeringConstantRepository
from repositories.material_repository import MaterialRepository
from repositories.pipe_size_repository import PipeSizeRepository
from repositories.project_repository import ProjectRepository
from services.engineering_constant_service import EngineeringConstantService
from services.material_service import MaterialService
from services.pipe_size_service import PipeSizeService
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
        self._library_database = LibraryDatabase()
        self._library_database.initialize()
        self._material_service = MaterialService(MaterialRepository(self._library_database))
        self._pipe_size_service = PipeSizeService(PipeSizeRepository(self._library_database))
        self._constant_service = EngineeringConstantService(
            EngineeringConstantRepository(self._library_database)
        )
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
            material_service=getattr(self, "_material_service", None),
            pipe_size_service=getattr(self, "_pipe_size_service", None),
            engineering_constant_service=getattr(self, "_constant_service", None),
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
        self._library_database.initialize()
