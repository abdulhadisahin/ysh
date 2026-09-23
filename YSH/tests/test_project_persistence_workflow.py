"""Regression tests for optional-project workspace persistence workflows."""

from __future__ import annotations

from pathlib import Path

import pytest

from database.project_database import ProjectDatabase
from repositories.project_repository import ProjectRepository
from repositories.project_state_repository import ProjectStateRepository
from services.project_persistence_service import ProjectPersistenceService
from services.project_service import ProjectConflictError, ProjectService


def _service(tmp_path: Path) -> ProjectPersistenceService:
    """Build an isolated optional-project persistence service."""
    database = ProjectDatabase(tmp_path / "projects.db")
    database.initialize()
    return ProjectPersistenceService(
        ProjectService(ProjectRepository(database)),
        ProjectStateRepository(database),
    )


def _state(marker: str) -> dict[str, object]:
    """Return a deterministic four-page state with distinct data."""
    return {
        "schema_version": 1,
        "pipe_design": {"fields": {"q": marker}, "diameter_result": {"diameter_mm": marker}},
        "transfer_pump": {"capacity": marker},
        "discharge_head_loss": {"fields": {"d": marker}, "items": [{"name": marker}]},
        "suction_npsh": {"fields": {"flow": marker}, "items": [{"id": marker}]},
    }


def test_project_a_b_c_states_are_isolated_and_save_as_copies_state(tmp_path: Path) -> None:
    """Opening projects restores exact per-project state without cross leakage."""
    service = _service(tmp_path)
    project_a = service.create_project("Project A", "A", "notes A")
    state_a = _state("A")
    service.save(state_a)
    project_b = service.create_project("Project B", "B", "notes B")
    state_b = _state("B")
    service.save(state_b)

    _, restored_a = service.open(project_a.id)
    assert restored_a == state_a
    project_c = service.create_project("Project C", "C", "notes C")
    service.save(restored_a)
    assert project_c.id != project_a.id
    assert service.is_dirty is False

    copied_c = service.open(project_c.id)[1]
    assert copied_c == state_a
    copied_c["pipe_design"] = {"fields": {"q": "C"}}
    service.save(copied_c)
    assert service.open(project_a.id)[1] == state_a
    assert service.open(project_b.id)[1] == state_b
    assert service.open(project_c.id)[1]["pipe_design"] == {"fields": {"q": "C"}}


def test_project_persistence_dirty_close_delete_and_duplicate_name(tmp_path: Path) -> None:
    """Cover clean saves, optional close, delete, and duplicate-name safety."""
    service = _service(tmp_path)
    project = service.create_project("Project A")
    service.mark_dirty()
    assert service.is_dirty is True
    service.save(_state("A"))
    assert service.is_dirty is False
    service.close()
    assert service.active_project is None
    service.open(project.id)
    with pytest.raises(ProjectConflictError):
        service.create_project("  project a  ")
    service.delete(project.id)
    assert service.active_project is None
    with pytest.raises(Exception):
        service.open(project.id)


def test_project_persistence_restores_first_suitable_dn_recommendation(
    tmp_path: Path,
) -> None:
    """The existing diameter-result payload retains its recommended DN unchanged."""
    service = _service(tmp_path)
    project = service.create_project("Pipe Recommendation")
    state = _state("680")
    state["pipe_design"] = {
        "fields": {"q": "680", "v": "5"},
        "diameter_result": {
            "diameter_mm": 219.3,
            "minimum_matching_dn": "DN250",
            "recommended_dn": "DN250",
        },
    }

    service.save(state)

    assert service.open(project.id)[1]["pipe_design"] == state["pipe_design"]
