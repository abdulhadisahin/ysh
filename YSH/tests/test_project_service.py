"""Tests for ProjectService validation and CRUD workflows."""

from __future__ import annotations

import pytest

from core.project import Project
from services.project_service import (
    ProjectConflictError,
    ProjectNotFoundError,
    ProjectService,
    ProjectValidationError,
)


def test_service_creates_valid_project(project_service: ProjectService) -> None:
    """A valid project is persisted and returned as a domain object."""
    project = project_service.create_project("Valid Project", "Description", "Notes")

    assert project.name == "Valid Project"
    assert project_service.get_project(project.id) == project


def test_service_trims_project_text(project_service: ProjectService) -> None:
    """Leading and trailing whitespace is removed before persistence."""
    project = project_service.create_project("  Project  ", "  Description  ", "  Notes  ")

    assert project.name == "Project"
    assert project.description == "Description"
    assert project.notes == "Notes"


def test_service_rejects_empty_project_name(project_service: ProjectService) -> None:
    """An empty project name raises a validation exception."""
    with pytest.raises(ProjectValidationError, match="required"):
        project_service.create_project("")


def test_service_rejects_whitespace_only_project_name(
    project_service: ProjectService,
) -> None:
    """A whitespace-only project name raises a validation exception."""
    with pytest.raises(ProjectValidationError, match="required"):
        project_service.create_project("   ")


def test_service_rejects_case_insensitive_duplicate_name(
    project_service: ProjectService,
) -> None:
    """Project names must be unique without regard to case."""
    project_service.create_project("Project Alpha")

    with pytest.raises(ProjectConflictError, match="already exists"):
        project_service.create_project("project alpha")


def test_service_update_allows_its_own_name(
    project_service: ProjectService,
) -> None:
    """Updating a project does not conflict with its existing name."""
    project = project_service.create_project("Project Alpha", "Before")
    project.description = "After"

    updated_project = project_service.update_project(project)

    assert updated_project.description == "After"


def test_service_deletes_and_reports_missing_project(
    project_service: ProjectService,
) -> None:
    """Deleted projects cannot be retrieved through the service."""
    project = project_service.create_project("Project Alpha")

    project_service.delete_project(project.id)

    with pytest.raises(ProjectNotFoundError):
        project_service.get_project(project.id)


def test_service_returns_all_projects(project_service: ProjectService) -> None:
    """The full project collection is exposed through the service layer."""
    first_project = project_service.create_project("First Project")
    second_project = project_service.create_project("Second Project")

    project_ids = {project.id for project in project_service.get_all_projects()}

    assert project_ids == {first_project.id, second_project.id}


def test_service_reports_existing_project_name(project_service: ProjectService) -> None:
    """Project name lookup honors case-insensitive matching."""
    project_service.create_project("Project Alpha")

    assert project_service.project_name_exists("  project alpha  ")


def test_service_opens_an_existing_project(project_service: ProjectService) -> None:
    """The service workflow retrieves a project created in the same workflow."""
    created_project = project_service.create_project("Openable Project")

    opened_project = project_service.get_project(created_project.id)

    assert opened_project == created_project


def test_service_returns_empty_project_list(project_service: ProjectService) -> None:
    """An empty project collection is handled without an exception."""
    assert project_service.get_all_projects() == ()
