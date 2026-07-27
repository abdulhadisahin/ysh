class DatabaseManager:
    """Placeholder database manager."""

    def __init__(self, database_path: str = "database") -> None:
        self.database_path = database_path
"""
YSH - Engineering Calculation System

SQLite database manager.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from core.constants import DATABASE_PATH


class DatabaseManager:
    """Manages the SQLite database connection and schema."""

    def __init__(self) -> None:
        self._connection: sqlite3.Connection | None = None

    @property
    def connection(self) -> sqlite3.Connection:
        """Return the active database connection."""

        if self._connection is None:
            raise RuntimeError("Database connection has not been established.")

        return self._connection

    def connect(self) -> None:
        """Open the database connection."""

        Path(DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)

        self._connection = sqlite3.connect(DATABASE_PATH)
        self._connection.row_factory = sqlite3.Row

        self.connection.execute("PRAGMA foreign_keys = ON;")

    def disconnect(self) -> None:
        """Close the database connection."""

        if self._connection is not None:
            self._connection.close()
            self._connection = None

    def create_tables(self) -> None:
        """Create all required database tables."""

        cursor = self.connection.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            notes TEXT NOT NULL,
            created_at TEXT NOT NULL,
            modified_at TEXT NOT NULL
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS calculations (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            name TEXT NOT NULL,
            calculation_type TEXT NOT NULL,
            description TEXT NOT NULL,
            created_at TEXT NOT NULL,
            modified_at TEXT NOT NULL,
            FOREIGN KEY(project_id)
                REFERENCES projects(id)
                ON DELETE CASCADE
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS parameters (
            id TEXT PRIMARY KEY,
            calculation_id TEXT NOT NULL,
            name TEXT NOT NULL,
            value TEXT,
            unit TEXT NOT NULL,
            description TEXT NOT NULL,
            editable INTEGER NOT NULL,
            FOREIGN KEY(calculation_id)
                REFERENCES calculations(id)
                ON DELETE CASCADE
        );
        """)

        self.connection.commit()