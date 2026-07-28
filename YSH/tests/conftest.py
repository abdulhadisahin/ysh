"""Shared pytest fixtures for YSH persistence and service tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from database.project_database import ProjectDatabase
from repositories.project_repository import ProjectRepository
from services.project_service import ProjectService


@pytest.fixture
def project_database(tmp_path: Path) -> ProjectDatabase:
    """Provide an initialized project database stored in a test-only path."""
    database = ProjectDatabase(tmp_path / "projects.db")
    database.initialize()
    return database


@pytest.fixture
def project_repository(project_database: ProjectDatabase) -> ProjectRepository:
    """Provide a repository backed by the test-only project database."""
    return ProjectRepository(project_database)


@pytest.fixture
def project_service(project_repository: ProjectRepository) -> ProjectService:
    """Provide a project service backed by the test-only repository."""
    return ProjectService(project_repository)
