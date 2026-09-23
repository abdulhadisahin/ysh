"""Runtime paths for YSH bundled resources and writable user data."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ApplicationPaths:
    """Resolve YSH paths without relying on the process working directory."""

    local_app_data: Path | None = None

    @property
    def user_root(self) -> Path:
        """Return the per-user YSH data root under ``LOCALAPPDATA``."""
        root = self.local_app_data or Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return root / "YSH"

    @property
    def data_directory(self) -> Path:
        """Return the writable SQLite data directory."""
        return self.user_root / "data"

    @property
    def logs_directory(self) -> Path:
        """Return the writable application log directory."""
        return self.user_root / "logs"

    @property
    def backups_directory(self) -> Path:
        """Return the reserved writable backup directory."""
        return self.user_root / "backups"

    @property
    def projects_database_path(self) -> Path:
        """Return the per-user projects SQLite path."""
        return self.data_directory / "projects.db"

    @property
    def libraries_database_path(self) -> Path:
        """Return the per-user engineering library SQLite path."""
        return self.data_directory / "libraries.db"

    @property
    def log_file_path(self) -> Path:
        """Return the per-user application log path."""
        return self.logs_directory / "ysh.log"

    @property
    def settings_file_path(self) -> Path:
        """Return the per-user non-project UI-preference file path."""
        return self.data_directory / "settings.json"

    @property
    def resource_root(self) -> Path:
        """Return read-only bundled resources in source or frozen execution."""
        if getattr(sys, "frozen", False):
            return Path(getattr(sys, "_MEIPASS"))
        return Path(__file__).resolve().parent

    def ensure_directories(self) -> None:
        """Create all writable YSH directories safely."""
        for directory in (self.data_directory, self.logs_directory, self.backups_directory):
            directory.mkdir(parents=True, exist_ok=True)
