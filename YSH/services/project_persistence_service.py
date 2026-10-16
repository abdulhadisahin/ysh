"""Simple optional project persistence for complete Version 1 workspaces."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from engineering.pipe_design.transfer import PipeTransferProjectState

from core.project import Project
from repositories.project_state_repository import ProjectStateRepository
from services.project_service import ProjectService
from engineering.validation import ValidationError, ValidationIssue


class ProjectPersistenceService:
    """Coordinate optional project records and one JSON workspace state."""

    def __init__(self, projects: ProjectService, states: ProjectStateRepository) -> None:
        """Configure persistence dependencies without UI knowledge."""
        self._projects = projects
        self._states = states
        self._active_project: Project | None = None
        self._is_dirty = False

    @property
    def active_project(self) -> Project | None:
        """Return the active optional project."""
        return self._active_project

    @property
    def is_dirty(self) -> bool:
        """Return active-project dirty state."""
        return self._is_dirty

    def create_project(self, name: str, description: str = "", notes: str = "") -> Project:
        """Create and activate an initially clean project."""
        self._active_project = self._projects.create_project(name, description, notes)
        self._is_dirty = False
        return self._active_project

    def save(self, state: dict[str, object]) -> None:
        """Save a version-1 workspace for the active project."""
        if self._active_project is None:
            raise ValidationError(ValidationIssue("project_selection_required"))
        # Existing pages export only their own keys. Preserve the opt-in namespace
        # when those pages save, including future namespace versions kept opaque.
        if "pipe_transfer" not in state or "system_context" not in state:
            previous = self._states.get(self._active_project.id) or {}
            for namespace in ("pipe_transfer", "system_context"):
                if namespace not in state and namespace in previous:
                    state = {**state, namespace: previous[namespace]}
        state["schema_version"] = 1
        self._states.save(self._active_project.id, state)
        self._is_dirty = False

    def open(self, project_id: UUID) -> tuple[Project, dict[str, object]]:
        """Activate a project and safely return its compatible saved state."""
        project = self._projects.get_project(project_id)
        state = self._states.get(project_id) or {"schema_version": 1}
        if state.get("schema_version") != 1:
            raise ValidationError(ValidationIssue("project_state_unsupported"))
        self._active_project = project
        self._is_dirty = False
        return project, state

    def get_all_projects(self) -> Sequence[Project]:
        """Return project metadata for a project-selection dialog."""
        return self._projects.get_all_projects()

    def get_project(self, project_id: UUID) -> Project:
        """Return one project metadata record by its identifier."""
        return self._projects.get_project(project_id)

    def has_saved_state(self, project_id: UUID) -> bool:
        """Return whether a project has an explicitly saved workspace state."""
        return self._states.get(project_id) is not None

    def mark_dirty(self) -> None:
        """Mark the active project dirty after a user workspace edit."""
        if self._active_project is not None:
            self._is_dirty = True

    def close(self) -> None:
        """Clear active-project state without affecting calculations."""
        self._active_project = None
        self._is_dirty = False

    def delete(self, project_id: UUID) -> None:
        """Delete a project and its cascaded state, clearing it if active."""
        self._projects.delete_project(project_id)
        if self._active_project is not None and self._active_project.id == project_id:
            self.close()

    def save_with_pipe_transfer(self, state: dict[str, object], transfer: PipeTransferProjectState) -> None:
        """Persist explicit transfer state through the existing project JSON row."""
        from engineering.pipe_design.transfer_serialization import NAMESPACE, transfer_to_dict
        self.save({**state, NAMESPACE: transfer_to_dict(transfer)})

    def open_with_pipe_transfer(self, project_id: UUID) -> tuple[Project, dict[str, object], PipeTransferProjectState]:
        """Restore typed state; legacy projects default to independent manual input."""
        from engineering.pipe_design.transfer_serialization import transfer_from_workspace
        project, state = self.open(project_id)
        return project, state, transfer_from_workspace(state)
