"""Application service for explicit project calculation workspaces."""
from __future__ import annotations
from dataclasses import dataclass, field
from uuid import UUID
from core.calculation import Calculation
from core.project import Project
from services.calculation_service import CalculationService
from services.project_service import ProjectService
@dataclass(slots=True)
class ProjectWorkspaceState:
    """Serializable active project and its independent calculations."""
    project: Project
    calculations_by_type: dict[str, Calculation] = field(default_factory=dict)
    active_calculation_type: str = "pipe_design"
    is_dirty: bool = False
class ProjectWorkspaceService:
    """Owns active workspace state without UI or SQL dependencies."""
    def __init__(self,projects:ProjectService,calculations:CalculationService)->None:
        """Configure project and calculation services."""
        self._projects=projects;self._calculations=calculations;self._state:ProjectWorkspaceState|None=None
    @property
    def active_workspace(self)->ProjectWorkspaceState|None:
        """Return the current workspace, if a project is active."""
        return self._state
    @property
    def has_unsaved_changes(self)->bool:
        """Return whether the active workspace has unsaved changes."""
        return self._state is not None and self._state.is_dirty
    def create_new_workspace(self,name:str,description:str="",notes:str="")->ProjectWorkspaceState:
        """Create a project with an intentionally empty calculation workspace."""
        project=self._projects.create_project(name,description,notes);self._state=ProjectWorkspaceState(project);return self._state
    def open_workspace(self,project_id:UUID)->ProjectWorkspaceState:
        """Load all child calculations owned by the selected project."""
        project=self._projects.get_project(project_id);records=self._calculations.get_all(project_id);self._state=ProjectWorkspaceState(project,{record.calculation_type:record for record in records});return self._state
    def save_workspace(self,calculation_type:str,input_data:dict[str,object],result_data:dict[str,object],trace_data:dict[str,object])->Calculation:
        """Save current state and mark the workspace clean."""
        if self._state is None:raise ValueError("Create or open a project to begin.")
        record=self._calculations.save(self._state.project.id,calculation_type,input_data,result_data,trace_data);self._state.calculations_by_type[calculation_type]=record;self._state.is_dirty=False;return record
    def close_workspace(self)->None:
        """Clear all active state without assigning it to another project."""
        self._state=None
    def mark_dirty(self)->None:
        """Mark the active workspace as containing unsaved edits."""
        if self._state is not None:self._state.is_dirty=True
    def mark_clean(self)->None:
        """Mark the active workspace clean after an explicit save."""
        if self._state is not None:self._state.is_dirty=False
