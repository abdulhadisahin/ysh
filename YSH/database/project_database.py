"""SQLite database definition for YSH projects."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from database.base_database import BaseDatabase
from database.migrations import migrate
from paths import ApplicationPaths


class ProjectDatabase(BaseDatabase):
    """Initializes the SQLite database that stores project records."""

    SCHEMA_VERSION = 1

    def __init__(self, database_path: Path | None = None) -> None:
        """Configure the local projects database file."""
        if database_path is None:
            database_path = ApplicationPaths().projects_database_path
        super().__init__(database_path)

    def create_schema(self, connection: sqlite3.Connection) -> None:
        """Version the database separately from project_states payload versions."""
        migrate(connection, database="projects", latest=self.SCHEMA_VERSION,
                steps={1: self._create_legacy_schema})

    def _create_legacy_schema(self, connection: sqlite3.Connection) -> None:
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
        """Add missing legacy columns without rebuilding user tables or rows."""
        columns = {row["name"] for row in connection.execute("PRAGMA table_info(projects)")}
        if "id" not in columns:
            if "project_id" not in columns:
                raise ValueError("Legacy projects table has no stable project identifier")
            connection.execute("ALTER TABLE projects RENAME COLUMN project_id TO id")
        if "name" not in columns:
            raise ValueError("Legacy projects table has no project name")
        additions = {
            "description": "TEXT NOT NULL DEFAULT ''",
            "notes": "TEXT NOT NULL DEFAULT ''",
            "created_at": "TEXT NOT NULL DEFAULT ''",
            "modified_at": "TEXT NOT NULL DEFAULT ''",
        }
        for column, definition in additions.items():
            if column not in columns:
                connection.execute(f"ALTER TABLE projects ADD COLUMN {column} {definition}")
