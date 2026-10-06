"""Service workflows for standard-scoped pipe-library geometry."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from core.pipe_size import PipeSize
from core.pipe_standard import PipeStandard
from database.en_10220_pipe_size_seed import EN_10220_STANDARD_CODE
from engineering.validation import ValidationError, ValidationIssue
from repositories.pipe_size_repository import (
    PipeSizeRepository,
    PipeSizeRepositoryConflictError,
    PipeStandardRepositoryConflictError,
)


class PipeSizeValidationError(ValidationError):
    """Raised when pipe dimensions or a standard relation are invalid."""


class PipeSizeConflictError(ValidationError):
    """Raised for duplicate standard-scoped pipe geometry."""


class PipeSizeNotFoundError(ValidationError, LookupError):
    """Raised for an absent pipe-size record."""


class PipeStandardNotFoundError(ValidationError, LookupError):
    """Raised when a requested pipe standard is unavailable."""


class PipeSizeService:
    """Validates pipe-library CRUD while preserving the V1 default workflow."""

    CONSISTENCY_TOLERANCE_MM = 0.001
    DEFAULT_STANDARD_CODE = EN_10220_STANDARD_CODE

    def __init__(self, repository: PipeSizeRepository) -> None:
        self._repository = repository

    def get_available_standards(self) -> Sequence[PipeStandard]:
        """List active standards available for selection in the local library."""
        return self._repository.list_standards(active_only=True)

    def get_standard(self, standard_id: UUID) -> PipeStandard:
        standard = self._repository.get_standard(standard_id)
        if standard is None:
            raise PipeStandardNotFoundError(ValidationIssue("pipe_standard_not_found"))
        return standard

    def get_standard_by_code(self, code: str) -> PipeStandard:
        standard = self._repository.get_standard_by_code(code)
        if standard is None:
            raise PipeStandardNotFoundError(ValidationIssue("pipe_standard_not_found"))
        return standard

    def create_standard(self, **values: object) -> PipeStandard:
        """Create metadata only; this phase does not seed speculative geometry."""
        standard = PipeStandard(**values)  # type: ignore[arg-type]
        standard.code = standard.code.strip()
        standard.display_name = standard.display_name.strip()
        standard.description = standard.description.strip()
        standard.source = standard.source.strip()
        if not standard.code or not standard.display_name:
            raise PipeSizeValidationError(ValidationIssue("pipe_standard_required"))
        try:
            return self._repository.create_standard(standard)
        except PipeStandardRepositoryConflictError as error:
            raise PipeSizeConflictError(ValidationIssue("pipe_standard_duplicate")) from error

    def get_pipe_sizes_for_standard(self, standard: UUID | str | None = None) -> Sequence[PipeSize]:
        """List geometry belonging to one standard and never mix standards."""
        resolved = self._resolve_standard(standard)
        return self._repository.list_for_standard(resolved.id)

    def create_pipe_size(self, **values: object) -> PipeSize:
        """Validate and store one standard-scoped pipe geometry record.

        The legacy editor has no standard selector in Phase 2A, so omitted
        standard input deliberately resolves to EN_10220 until Phase 2B.
        """
        item = PipeSize(**values)  # type: ignore[arg-type]
        self._normalise(item)
        self._assign_standard(item, allow_default=True)
        self._validate(item)
        self._available(item)
        try:
            return self._repository.create(item)
        except PipeSizeRepositoryConflictError as error:
            raise PipeSizeConflictError(ValidationIssue("pipe_size_duplicate")) from error

    def update_pipe_size(self, item: PipeSize) -> PipeSize:
        """Validate and update an existing geometry record without losing its standard."""
        self._normalise(item)
        self._assign_standard(item, allow_default=False)
        self._validate(item)
        self._available(item)
        item.touch()
        try:
            return self._repository.update(item)
        except KeyError as error:
            raise PipeSizeNotFoundError(ValidationIssue("pipe_size_not_found")) from error
        except PipeSizeRepositoryConflictError as error:
            raise PipeSizeConflictError(ValidationIssue("pipe_size_duplicate")) from error

    def delete_pipe_size(self, item_id: UUID) -> None:
        try:
            self._repository.delete(item_id)
        except KeyError as error:
            raise PipeSizeNotFoundError(ValidationIssue("pipe_size_not_found")) from error

    def get_pipe_size(self, item_id: UUID) -> PipeSize:
        item = self._repository.get(item_id)
        if item is None:
            raise PipeSizeNotFoundError(ValidationIssue("pipe_size_not_found"))
        return item

    def get_all_pipe_sizes(self) -> Sequence[PipeSize]:
        """Retain the V1 library-editor API; calculation uses a scoped query."""
        return self._repository.get_all()

    @staticmethod
    def _normalise(item: PipeSize) -> None:
        item.nominal_diameter = item.nominal_diameter.strip()
        item.standard = item.standard.strip()
        item.description = item.description.strip()

    def _resolve_standard(self, standard: UUID | str | None) -> PipeStandard:
        if isinstance(standard, UUID):
            return self.get_standard(standard)
        if standard is None or not standard.strip():
            return self.get_standard_by_code(self.DEFAULT_STANDARD_CODE)
        candidate = self._repository.get_standard_by_code(standard.strip())
        candidate = candidate or self._repository.get_standard_by_display_name(standard.strip())
        if candidate is None:
            raise PipeStandardNotFoundError(ValidationIssue("pipe_standard_not_found"))
        return candidate

    def _assign_standard(self, item: PipeSize, *, allow_default: bool) -> None:
        if item.standard_id is not None:
            standard = self.get_standard(item.standard_id)
        elif item.standard:
            standard = self._resolve_standard(item.standard)
        elif allow_default:
            standard = self.get_standard_by_code(self.DEFAULT_STANDARD_CODE)
        else:
            raise PipeSizeValidationError(ValidationIssue("pipe_standard_required"))
        item.standard_id = standard.id
        item.standard = standard.display_name

    def _validate(self, item: PipeSize) -> None:
        if item.standard_id is None:
            raise PipeSizeValidationError(ValidationIssue("pipe_standard_required"))
        if not item.nominal_diameter:
            raise PipeSizeValidationError(ValidationIssue("required", "field.dn"))
        for value, field in (
            (item.outside_diameter_mm, "field.outside_diameter"),
            (item.wall_thickness_mm, "field.wall_thickness"),
            (item.inside_diameter_mm, "field.inside_diameter"),
        ):
            if value <= 0:
                raise PipeSizeValidationError(ValidationIssue("greater_than_zero", field))
        if item.inside_diameter_mm >= item.outside_diameter_mm:
            raise PipeSizeValidationError(ValidationIssue("pipe_size_invalid_geometry"))
        expected = item.outside_diameter_mm - (2 * item.wall_thickness_mm)
        if abs(item.inside_diameter_mm - expected) > self.CONSISTENCY_TOLERANCE_MM:
            raise PipeSizeValidationError(ValidationIssue("pipe_size_invalid_geometry"))

    def _available(self, item: PipeSize) -> None:
        assert item.standard_id is not None
        if self._repository.exists(
            item.nominal_diameter, item.outside_diameter_mm, item.wall_thickness_mm,
            item.standard_id, item.id,
        ):
            raise PipeSizeConflictError(ValidationIssue("pipe_size_duplicate"))
