"""Application composition and lifecycle management for YSH."""

from __future__ import annotations

import logging
import sys
import tkinter as tk

from YSH.database.project_database import ProjectDatabase
from YSH.database.library_database import LibraryDatabase
from YSH.repositories.engineering_constant_repository import EngineeringConstantRepository
from YSH.repositories.material_repository import MaterialRepository
from YSH.repositories.pipe_size_repository import PipeSizeRepository
from YSH.repositories.project_repository import ProjectRepository
from YSH.repositories.pump_reference_repository import PumpReferenceRepository
from YSH.repositories.calculation_repository import CalculationRepository
from YSH.services.engineering_constant_service import EngineeringConstantService
from YSH.services.material_service import MaterialService
from YSH.services.pipe_size_service import PipeSizeService
from YSH.services.pipe_design_service import PipeDesignService
from YSH.services.project_service import ProjectService
from YSH.services.calculation_service import CalculationService
from YSH.services.project_workspace_service import ProjectWorkspaceService
from YSH.services.pump_reference_service import PumpReferenceService
from YSH.services.transfer_pump_service import TransferPumpService
from YSH.services.discharge_head_loss_service import DischargeHeadLossService
from YSH.services.suction_npsh_service import SuctionNPSHService
from YSH.services.project_persistence_service import ProjectPersistenceService
from YSH.repositories.project_state_repository import ProjectStateRepository
from YSH.ui.main_window import MainWindow
from YSH.i18n.manager import LocalizationManager
from YSH.paths import ApplicationPaths
from YSH.ui.assets import ysh_icon_path


def configure_logging(paths: ApplicationPaths) -> None:
    """Configure local-only startup and uncaught-error logging once."""
    paths.ensure_directories()
    configuration = {
        "level": logging.INFO,
        "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
    }
    try:
        logging.basicConfig(filename=paths.log_file_path, **configuration)
    except OSError:
        logging.basicConfig(stream=sys.stderr, **configuration)
        logging.getLogger(__name__).exception(
            "Unable to open YSH log file '%s'; using standard error.",
            paths.log_file_path,
        )


class YSHApplication:
    """Initializes YSH infrastructure and owns its desktop application lifecycle."""

    def __init__(self) -> None:
        """Create the application dependencies without starting the event loop."""
        self._paths = ApplicationPaths()
        configure_logging(self._paths)
        self._localization = LocalizationManager(self._paths.settings_file_path)
        logging.getLogger(__name__).info(
            "YSH startup: python=%s executable=%s frozen=%s bundle=%s user_data=%s "
            "projects=%s libraries=%s",
            sys.version,
            sys.executable,
            getattr(sys, "frozen", False),
            self._paths.resource_root,
            self._paths.user_root,
            self._paths.projects_database_path,
            self._paths.libraries_database_path,
        )
        self._project_database = ProjectDatabase()
        self._project_repository = ProjectRepository(self._project_database)
        self._project_service = ProjectService(self._project_repository)
        self._project_persistence_service = ProjectPersistenceService(
            self._project_service, ProjectStateRepository(self._project_database)
        )
        self._calculation_service = CalculationService(
            CalculationRepository(self._project_database)
        )
        self._workspace_service = ProjectWorkspaceService(
            self._project_service,
            self._calculation_service,
        )
        self._library_database = LibraryDatabase()
        self._library_database.initialize()
        self._material_service = MaterialService(MaterialRepository(self._library_database))
        self._pipe_size_service = PipeSizeService(PipeSizeRepository(self._library_database))
        self._constant_service = EngineeringConstantService(
            EngineeringConstantRepository(self._library_database)
        )
        self._pump_reference_service = PumpReferenceService(PumpReferenceRepository(self._library_database))
        self._transfer_pump_service = TransferPumpService(self._pump_reference_service)
        self._discharge_head_loss_service = DischargeHeadLossService(self._material_service)
        self._suction_npsh_service = SuctionNPSHService(self._material_service)
        self._pipe_design_service = PipeDesignService(
            self._material_service,
            self._pipe_size_service,
            self._constant_service,
        )
        self._root: tk.Tk | None = None
        self._main_window: MainWindow | None = None

    def run(self) -> None:
        """Initialize local resources and start the main window."""
        self._initialize_application()
        self._root = tk.Tk()
        self._apply_window_icon()
        window_options = {
            "root": self._root,
            "project_service": self._project_service,
            "material_service": getattr(self, "_material_service", None),
            "pipe_size_service": getattr(self, "_pipe_size_service", None),
            "engineering_constant_service": getattr(self, "_constant_service", None),
            "pipe_design_service": getattr(self, "_pipe_design_service", None),
            "transfer_pump_service": getattr(self, "_transfer_pump_service", None),
            "discharge_head_loss_service": getattr(self, "_discharge_head_loss_service", None),
            "suction_npsh_service": getattr(self, "_suction_npsh_service", None),
            "project_persistence_service": getattr(self, "_project_persistence_service", None),
            "on_close": self.shutdown,
        }
        localization = getattr(self, "_localization", None)
        if localization is not None:
            window_options["localization"] = localization
        self._main_window = MainWindow(**window_options)
        self._root.mainloop()

    def _apply_window_icon(self) -> None:
        """Apply the optional approved Windows icon without blocking startup."""
        if self._root is None:
            return
        icon_path = ysh_icon_path(self._paths.resource_root)
        iconbitmap = getattr(self._root, "iconbitmap", None)
        if icon_path is None or not callable(iconbitmap):
            return
        try:
            iconbitmap(default=str(icon_path))
        except tk.TclError:
            logging.getLogger(__name__).warning(
                "Unable to apply optional YSH window icon: %s",
                icon_path,
                exc_info=True,
            )

    def shutdown(self) -> None:
        """Release application resources before the main window closes."""
        self._main_window = None
        self._root = None

    def _initialize_application(self) -> None:
        """Create only per-user runtime data, then initialize local databases."""
        self._paths.ensure_directories()
        self._project_database.initialize()
        self._library_database.initialize()
