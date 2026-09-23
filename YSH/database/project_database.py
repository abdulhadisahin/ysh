"""SQLite database definition for YSH projects."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from uuid import uuid4

from core.constants import PROJECT_DATABASE_FILENAME
from database.base_database import BaseDatabase
from paths import ApplicationPaths


class ProjectDatabase(BaseDatabase):
    """Initializes the SQLite database that stores project records."""

    def __init__(self, database_path: Path | None = None) -> None:
        """Configure the local projects database file."""
        if database_path is None:
            database_path = ApplicationPaths().projects_database_path
        super().__init__(database_path)

    def create_schema(self, connection: sqlite3.Connection) -> None:
        """Create the project table required by the application infrastructure."""
        if self._projects_table_exists(connection):
            self._migrate_schema_if_required(connection)
        else:
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
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS calculations (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                calculation_type TEXT NOT NULL,
                module_version TEXT NOT NULL,
                created_at TEXT NOT NULL,
                modified_at TEXT NOT NULL,
                input_data_json TEXT NOT NULL,
                result_data_json TEXT NOT NULL,
                trace_data_json TEXT NOT NULL,
                UNIQUE(project_id, calculation_type),
                FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS project_states (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL UNIQUE,
                state_json TEXT NOT NULL,
                schema_version INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                modified_at TEXT NOT NULL,
                FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
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
