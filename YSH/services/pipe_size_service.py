"""Service layer for pipe-size library workflows."""
from __future__ import annotations
from collections.abc import Sequence
from uuid import UUID
from core.pipe_size import PipeSize
from engineering.validation import ValidationError, ValidationIssue
from repositories.pipe_size_repository import PipeSizeRepository, PipeSizeRepositoryConflictError
class PipeSizeValidationError(ValidationError): """Raised when pipe dimensions are invalid."""
class PipeSizeConflictError(ValidationError): """Raised for duplicate pipe-size natural keys."""
class PipeSizeNotFoundError(ValidationError, LookupError): """Raised for an absent pipe-size record."""
class PipeSizeService:
    """Validates and coordinates pipe-size library operations."""
    CONSISTENCY_TOLERANCE_MM=0.001
    def __init__(self,repository:PipeSizeRepository)->None: self._repository=repository
    def create_pipe_size(self,**values:object)->PipeSize:
        """Validate and store a pipe size."""
        item=PipeSize(**values)  # type: ignore[arg-type]
        self._normalise(item);self._validate(item);self._available(item)
        try:return self._repository.create(item)
        except PipeSizeRepositoryConflictError as error:raise PipeSizeConflictError(ValidationIssue("pipe_size_duplicate")) from error
    def update_pipe_size(self,item:PipeSize)->PipeSize:
        """Validate and update a pipe size."""
        self._normalise(item);self._validate(item);self._available(item);item.touch()
        try:return self._repository.update(item)
        except KeyError as error:raise PipeSizeNotFoundError(ValidationIssue("pipe_size_not_found")) from error
        except PipeSizeRepositoryConflictError as error:raise PipeSizeConflictError(ValidationIssue("pipe_size_duplicate")) from error
    def delete_pipe_size(self,item_id:UUID)->None:
        """Delete a pipe size."""
        try:self._repository.delete(item_id)
        except KeyError as error:raise PipeSizeNotFoundError(ValidationIssue("pipe_size_not_found")) from error
    def get_pipe_size(self,item_id:UUID)->PipeSize:
        """Retrieve one pipe size."""
        item=self._repository.get(item_id)
        if item is None:raise PipeSizeNotFoundError(ValidationIssue("pipe_size_not_found"))
        return item
    def get_all_pipe_sizes(self)->Sequence[PipeSize]:
        """List all pipe sizes; an unseeded library is valid and empty."""
        return self._repository.get_all()
    @staticmethod
    def _normalise(item:PipeSize)->None: item.nominal_diameter=item.nominal_diameter.strip();item.standard=item.standard.strip();item.description=item.description.strip()
    def _validate(self,item:PipeSize)->None:
        if not item.nominal_diameter:raise PipeSizeValidationError(ValidationIssue("required", "field.dn"))
        for value, field in ((item.outside_diameter_mm,"field.outside_diameter"),(item.wall_thickness_mm,"field.wall_thickness"),(item.inside_diameter_mm,"field.inside_diameter")):
            if value<=0:raise PipeSizeValidationError(ValidationIssue("greater_than_zero", field))
        if item.inside_diameter_mm>=item.outside_diameter_mm:raise PipeSizeValidationError(ValidationIssue("pipe_size_invalid_geometry"))
        expected=item.outside_diameter_mm-(2*item.wall_thickness_mm)
        if abs(item.inside_diameter_mm-expected)>self.CONSISTENCY_TOLERANCE_MM:raise PipeSizeValidationError(ValidationIssue("pipe_size_invalid_geometry"))
    def _available(self,item:PipeSize)->None:
        if self._repository.exists(item.nominal_diameter,item.outside_diameter_mm,item.wall_thickness_mm,item.standard,item.id):raise PipeSizeConflictError(ValidationIssue("pipe_size_duplicate"))
