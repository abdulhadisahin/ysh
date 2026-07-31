"""Shared pytest fixtures for YSH persistence and service tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from database.project_database import ProjectDatabase
from database.library_database import LibraryDatabase
from repositories.engineering_constant_repository import EngineeringConstantRepository
from repositories.material_repository import MaterialRepository
from repositories.pipe_size_repository import PipeSizeRepository
from repositories.project_repository import ProjectRepository
from services.project_service import ProjectService
from services.engineering_constant_service import EngineeringConstantService
from services.material_service import MaterialService
from services.pipe_size_service import PipeSizeService


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

@pytest.fixture
def library_database(tmp_path: Path) -> LibraryDatabase:
    """Provide a test-only initialized engineering library database."""
    database = LibraryDatabase(tmp_path / "libraries.db")
    database.initialize()
    return database

@pytest.fixture
def material_service(library_database: LibraryDatabase) -> MaterialService:
    """Provide a seeded material service using a temporary database."""
    return MaterialService(MaterialRepository(library_database))

@pytest.fixture
def pipe_size_service(library_database: LibraryDatabase) -> PipeSizeService:
    """Provide an empty pipe-size service using a temporary database."""
    return PipeSizeService(PipeSizeRepository(library_database))

@pytest.fixture
def engineering_constant_service(
    library_database: LibraryDatabase,
) -> EngineeringConstantService:
    """Provide a seeded constants service using a temporary database."""
    return EngineeringConstantService(EngineeringConstantRepository(library_database))
