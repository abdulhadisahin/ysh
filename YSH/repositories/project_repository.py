"""SQLite repository for project persistence."""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from core.project import Project
from database.project_database import ProjectDatabase


class ProjectRepositoryConflictError(RuntimeError):
    """Raised when persisted project data conflicts with an existing record."""


class ProjectRepository:
    """Provides CRUD operations for project records stored in SQLite."""

    def __init__(self, database: ProjectDatabase) -> None:
        """Create the repository with its database dependency."""
        self._database = database

    def create(self, project: Project) -> Project:
        """Store a new project and return the stored domain model."""
        try:
            with self._database.connection() as connection:
                connection.execute(
                    """
                    INSERT INTO projects (
                        id, name, description, notes, created_at, modified_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    self._project_values(project),
                )
        except sqlite3.IntegrityError as error:
            raise ProjectRepositoryConflictError(
                "Project name must be unique."
            ) from error
        return project

    def get(self, project_id: UUID) -> Project | None:
        """Return the project with the given identifier, if it exists."""
        with self._database.connection() as connection:
            row = connection.execute(
                """
                SELECT id, name, description, notes, created_at, modified_at
                FROM projects
                WHERE id = ?
                """,
                (str(project_id),),
            ).fetchone()
        return self._map_row(row) if row is not None else None

    def get_by_id(self, project_id: UUID) -> Project | None:
        """Return the project with the given identifier, if it exists."""
        return self.get(project_id)

    def get_all(self) -> Sequence[Project]:
        """Return every project ordered by most recently modified first."""
        with self._database.connection() as connection:
            rows = connection.execute(
                """
                SELECT id, name, description, notes, created_at, modified_at
                FROM projects
                ORDER BY modified_at DESC, name ASC
                """
            ).fetchall()
        return tuple(self._map_row(row) for row in rows)

    def list_all(self) -> Sequence[Project]:
        """Return every project ordered by most recently modified first."""
        return self.get_all()

    def exists(self, project_id: UUID) -> bool:
        """Return whether a project with the given identifier is persisted."""
        with self._database.connection() as connection:
            row = connection.execute(
                "SELECT 1 FROM projects WHERE id = ?",
                (str(project_id),),
            ).fetchone()
        return row is not None

    def update(self, project: Project) -> Project:
        """Persist changes to an existing project and return the updated project."""
        try:
            with self._database.connection() as connection:
                cursor = connection.execute(
                    """
                    UPDATE projects
                    SET name = ?, description = ?, notes = ?, modified_at = ?
                    WHERE id = ?
                    """,
                    (
                        project.name,
                        project.description,
                        project.notes,
                        project.modified_at.isoformat(),
                        str(project.id),
                    ),
                )
        except sqlite3.IntegrityError as error:
            raise ProjectRepositoryConflictError(
                "Project name must be unique."
            ) from error
        if cursor.rowcount == 0:
            raise KeyError(f"Project '{project.id}' was not found.")
        return project

    def delete(self, project_id: UUID) -> None:
        """Delete the project with the given identifier."""
        with self._database.connection() as connection:
            cursor = connection.execute(
                "DELETE FROM projects WHERE id = ?",
                (str(project_id),),
            )
        if cursor.rowcount == 0:
            raise KeyError(f"Project '{project_id}' was not found.")

    @staticmethod
    def _project_values(project: Project) -> tuple[str, str, str, str, str, str]:
        return (
            str(project.id),
            project.name,
            project.description,
            project.notes,
            project.created_at.isoformat(),
            project.modified_at.isoformat(),
        )

    @staticmethod
    def _map_row(row: sqlite3.Row) -> Project:
        return Project(
            id=UUID(str(row["id"])),
            name=str(row["name"]),
            description=str(row["description"]),
            notes=str(row["notes"]),
            created_at=datetime.fromisoformat(str(row["created_at"])),
            modified_at=datetime.fromisoformat(str(row["modified_at"])),
        )
