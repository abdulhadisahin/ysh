"""SQLite database definition for local YSH library records."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from database.base_database import BaseDatabase


class LibraryDatabase(BaseDatabase):
    """Initializes the local SQLite database reserved for library records."""

    def __init__(self) -> None:
        """Configure the local library database file."""
        database_directory = Path(__file__).resolve().parent
        super().__init__(database_directory / "libraries.db")

    def create_schema(self, connection: sqlite3.Connection) -> None:
        """Create the table used to store locally managed library records."""
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS library_entries (
                id TEXT PRIMARY KEY,
                category TEXT NOT NULL,
                name TEXT NOT NULL,
                data TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(category, name)
            )
            """
        )
