"""SQLite database definition for YSH projects."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from uuid import uuid4

from core.constants import PROJECT_DATABASE_FILENAME
from database.base_database import BaseDatabase


class ProjectDatabase(BaseDatabase):
    """Initializes the SQLite database that stores project records."""

    def __init__(self, database_path: Path | None = None) -> None:
        """Configure the local projects database file."""
        if database_path is None:
            database_directory = Path(__file__).resolve().parent
            database_path = database_directory / PROJECT_DATABASE_FILENAME
        super().__init__(database_path)

    def create_schema(self, connection: sqlite3.Connection) -> None:
        """Create the project table required by the application infrastructure."""
        if self._projects_table_exists(connection):
            self._migrate_schema_if_required(connection)
            return
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL COLLATE NOCASE UNIQUE,
                description TEXT NOT NULL DEFAULT '',
                notes TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                modified_at TEXT NOT NULL
            )
            """
        )

    @staticmethod
    def _projects_table_exists(connection: sqlite3.Connection) -> bool:
        row = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'projects'"
        ).fetchone()
        return row is not None

    def _migrate_schema_if_required(self, connection: sqlite3.Connection) -> None:
        expected_columns = (
            "id",
            "name",
            "description",
            "notes",
            "created_at",
            "modified_at",
        )
        current_columns = tuple(
            str(row["name"])
            for row in connection.execute("PRAGMA table_info(projects)")
        )
        if current_columns == expected_columns:
            return

        rows = connection.execute("SELECT * FROM projects").fetchall()
        connection.execute("ALTER TABLE projects RENAME TO projects_legacy")
        self.create_schema(connection)
        legacy_columns = set(current_columns)
        for row in rows:
            project_id = self._legacy_identifier(row, legacy_columns)
            created_at = self._legacy_value(row, legacy_columns, "created_at")
            modified_at = self._legacy_value(
                row,
                legacy_columns,
                "modified_at",
                fallback=created_at,
            )
            connection.execute(
                """
                INSERT INTO projects (
                    id, name, description, notes, created_at, modified_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    project_id,
                    self._legacy_value(row, legacy_columns, "name"),
                    self._legacy_value(row, legacy_columns, "description"),
                    self._legacy_value(row, legacy_columns, "notes"),
                    created_at,
                    modified_at,
                ),
            )
        connection.execute("DROP TABLE projects_legacy")

    @staticmethod
    def _legacy_identifier(row: sqlite3.Row, columns: set[str]) -> str:
        if "project_id" in columns and row["project_id"]:
            return str(row["project_id"])
        return str(uuid4())

    @staticmethod
    def _legacy_value(
        row: sqlite3.Row,
        columns: set[str],
        column: str,
        fallback: str = "",
    ) -> str:
        if column not in columns or row[column] is None:
            return fallback
        return str(row[column])
