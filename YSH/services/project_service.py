"""Service layer for project workflows."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from core.constants import PROJECT_NAME_MAXIMUM_LENGTH, PROJECT_TEXT_MAXIMUM_LENGTH
from core.project import Project
from repositories.project_repository import (
    ProjectRepository,
    ProjectRepositoryConflictError,
)


class ProjectValidationError(ValueError):
    """Raised when project data does not meet application requirements."""


class ProjectConflictError(ValueError):
    """Raised when a project conflicts with an existing project."""

    def __init__(self, code: str = "project_duplicate_name") -> None:
        """Create a language-neutral duplicate-project error."""
        self.code = code
        super().__init__(code)


class ProjectNotFoundError(LookupError):
    """Raised when a requested project does not exist."""

    def __init__(self, code: str = "project_not_found") -> None:
        """Create a language-neutral missing-project error."""
        self.code = code
        super().__init__(code)


class ProjectService:
    """Validates and coordinates project CRUD operations."""

    def __init__(self, repository: ProjectRepository) -> None:
        """Create the service with its project repository dependency."""
        self._repository = repository

    def create_project(
        self,
        name: str,
        description: str = "",
        notes: str = "",
    ) -> Project:
        """Validate project details, then create and persist a project."""
        project = Project(
            name=name.strip(),
            description=description.strip(),
            notes=notes.strip(),
        )
        self._validate_project(project)
        self._ensure_name_is_available(project)
        try:
            return self._repository.create(project)
        except ProjectRepositoryConflictError as error:
            raise ProjectConflictError() from error

    def get_project(self, project_id: UUID) -> Project:
        """Return a project by identifier after validating the request."""
        self._validate_identifier(project_id)
        project = self._repository.get(project_id)
        if project is None:
            raise ProjectNotFoundError()
        return project

    def list_projects(self) -> Sequence[Project]:
        """Return all persisted projects."""
        return self.get_all_projects()

    def get_all_projects(self) -> Sequence[Project]:
        """Return all persisted projects."""
        return self._repository.get_all()

    def project_name_exists(
        self,
        name: str,
        excluded_project_id: UUID | None = None,
    ) -> bool:
        """Return whether a different project has the supplied name."""
        normalized_name = name.strip().casefold()
        if not normalized_name:
            return False
        return any(
            project.id != excluded_project_id
            and project.name.casefold() == normalized_name
            for project in self._repository.get_all()
        )

    def update_project(self, project: Project) -> Project:
        """Validate, timestamp, and persist updates to an existing project."""
        project.name = project.name.strip()
        project.description = project.description.strip()
        project.notes = project.notes.strip()
        self._validate_project(project)
        self._ensure_name_is_available(project)
        project.touch()
        try:
            return self._repository.update(project)
        except KeyError as error:
            raise ProjectNotFoundError() from error
        except ProjectRepositoryConflictError as error:
            raise ProjectConflictError() from error

    def delete_project(self, project_id: UUID) -> None:
        """Validate and delete a project by identifier."""
        self._validate_identifier(project_id)
        try:
            self._repository.delete(project_id)
        except KeyError as error:
            raise ProjectNotFoundError() from error

    @staticmethod
    def _validate_project(project: Project) -> None:
        if not project.name:
            raise ProjectValidationError("Project name is required.")
        if len(project.name) > PROJECT_NAME_MAXIMUM_LENGTH:
            raise ProjectValidationError(
                f"Project name cannot exceed {PROJECT_NAME_MAXIMUM_LENGTH} characters."
            )
        if len(project.description) > PROJECT_TEXT_MAXIMUM_LENGTH:
            raise ProjectValidationError("Project description is too long.")
        if len(project.notes) > PROJECT_TEXT_MAXIMUM_LENGTH:
            raise ProjectValidationError("Project notes are too long.")

    @staticmethod
    def _validate_identifier(project_id: UUID) -> None:
        if not isinstance(project_id, UUID):
            raise ProjectValidationError("Project identifier must be a UUID.")

    def _ensure_name_is_available(self, candidate: Project) -> None:
        if self.project_name_exists(candidate.name, candidate.id):
            raise ProjectConflictError()
