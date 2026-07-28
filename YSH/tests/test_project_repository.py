"""Tests for the SQLite ProjectRepository implementation."""

from __future__ import annotations

from datetime import datetime, timezone

from core.project import Project
from repositories.project_repository import ProjectRepository


def test_repository_creates_and_retrieves_project(
    project_repository: ProjectRepository,
) -> None:
    """A stored project can be retrieved by its UUID."""
    project = Project(name="Repository Project", description="Description")

    project_repository.create(project)

    assert project_repository.get(project.id) == project


def test_repository_updates_project(project_repository: ProjectRepository) -> None:
    """A stored project persists updated descriptive data."""
    project = Project(name="Repository Project", description="Before")
    project_repository.create(project)
    project.description = "After"
    project.touch()

    updated_project = project_repository.update(project)

    assert updated_project.description == "After"
    assert project_repository.get(project.id).description == "After"


def test_repository_deletes_project(project_repository: ProjectRepository) -> None:
    """Deleting a project removes it from persistent storage."""
    project = Project(name="Repository Project")
    project_repository.create(project)

    project_repository.delete(project.id)

    assert project_repository.get(project.id) is None
    assert not project_repository.exists(project.id)


def test_repository_get_all_returns_stored_projects(
    project_repository: ProjectRepository,
) -> None:
    """Retrieving all projects returns every stored project."""
    first_project = Project(name="First Project")
    second_project = Project(name="Second Project")
    project_repository.create(first_project)
    project_repository.create(second_project)

    project_ids = {project.id for project in project_repository.get_all()}

    assert project_ids == {first_project.id, second_project.id}


def test_repository_get_all_orders_projects_by_modified_date(
    project_repository: ProjectRepository,
) -> None:
    """Projects are returned with the most recently modified project first."""
    older_project = Project(name="Older Project")
    newer_project = Project(name="Newer Project")
    older_project.modified_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    newer_project.modified_at = datetime(2024, 1, 2, tzinfo=timezone.utc)
    project_repository.create(older_project)
    project_repository.create(newer_project)

    projects = project_repository.get_all()

    assert [project.id for project in projects] == [newer_project.id, older_project.id]


def test_repository_maps_database_values_to_project(
    project_repository: ProjectRepository,
) -> None:
    """Retrieved records are reconstructed as Project domain objects."""
    project = Project(
        name="Mapped Project",
        description="Description",
        notes="Notes",
    )
    project_repository.create(project)

    retrieved_project = project_repository.get(project.id)

    assert isinstance(retrieved_project, Project)
    assert retrieved_project.to_dict() == project.to_dict()
