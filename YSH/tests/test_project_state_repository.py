"""Tests for one JSON workspace state per optional project."""

from __future__ import annotations

from pathlib import Path

from database.project_database import ProjectDatabase
from repositories.project_repository import ProjectRepository
from repositories.project_state_repository import ProjectStateRepository
from services.project_persistence_service import ProjectPersistenceService
from services.project_service import ProjectService


def test_project_state_round_trip_and_delete(tmp_path: Path) -> None:
    """Persist, load, and delete a complete state without library data."""
    database = ProjectDatabase(tmp_path / "projects.db")
    database.initialize()
    service = ProjectPersistenceService(ProjectService(ProjectRepository(database)), ProjectStateRepository(database))
    project = service.create_project("Project A")
    state = {"pipe_design": {"flow": "12,5"}, "transfer_pump": {}, "discharge_head_loss": {}, "suction_npsh": {}}
    service.save(state)
    loaded_project, loaded = service.open(project.id)
    assert loaded_project.id == project.id
    assert loaded["schema_version"] == 1
    assert loaded["pipe_design"] == {"flow": "12,5"}
    service.delete(project.id)
    assert ProjectStateRepository(database).get(project.id) is None


def test_empty_project_has_no_implicit_state_and_populated_project_is_isolated(
    tmp_path: Path,
) -> None:
    """Opening an empty project never creates or inherits another state."""
    database = ProjectDatabase(tmp_path / "projects.db")
    database.initialize()
    states = ProjectStateRepository(database)
    service = ProjectPersistenceService(ProjectService(ProjectRepository(database)), states)
    project_a = service.create_project("Project A")
    state_a = {
        "pipe_design": {"fields": {"q": "100"}},
        "transfer_pump": {"capacity": "200"},
        "discharge_head_loss": {"fields": {"d": "300"}},
        "suction_npsh": {"fields": {"flow": "400"}},
    }
    service.save(state_a)
    project_b = service.create_project("Project B")

    assert service.has_saved_state(project_a.id) is True
    assert service.has_saved_state(project_b.id) is False
    assert states.get(project_b.id) is None
    assert service.open(project_a.id)[1]["pipe_design"] == state_a["pipe_design"]
    assert service.open(project_b.id)[1] == {"schema_version": 1}
    assert service.has_saved_state(project_b.id) is False
    assert service.open(project_a.id)[1]["suction_npsh"] == state_a["suction_npsh"]
