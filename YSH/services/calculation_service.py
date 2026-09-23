"""Service layer for project-owned calculation persistence."""
from __future__ import annotations
from uuid import UUID
from core.calculation import Calculation
from repositories.calculation_repository import CalculationRepository
class CalculationService:
    """Coordinates calculation persistence through its repository."""
    def __init__(self,repository:CalculationRepository)->None: self._repository=repository
    def save(self,project_id:UUID,calculation_type:str,input_data:dict[str,object],result_data:dict[str,object],trace_data:dict[str,object])->Calculation:
        """Persist one project calculation state."""
        return self._repository.upsert_for_project_and_type(project_id,calculation_type,input_data,result_data,trace_data)
    def get(self,project_id:UUID,calculation_type:str)->Calculation|None:
        """Return a saved calculation state."""
        return self._repository.get_by_project_and_type(project_id,calculation_type)
    def get_all(self,project_id:UUID)->tuple[Calculation,...]:
        """Return every calculation saved for a project."""
        return self._repository.get_all_by_project(project_id)
