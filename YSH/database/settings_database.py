"""SQLite database definition for local YSH application settings."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from database.base_database import BaseDatabase


class SettingsDatabase(BaseDatabase):
    """Initializes the local SQLite database used for application settings."""

    def __init__(self) -> None:
        """Configure the local settings database file."""
        database_directory = Path(__file__).resolve().parent
        super().__init__(database_directory / "settings.db")

    def create_schema(self, connection: sqlite3.Connection) -> None:
        """Create the table used to store local application setting values."""
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )
