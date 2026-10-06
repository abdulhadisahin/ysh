"""Service validation for circuit-based corrosion allowance defaults."""

from __future__ import annotations

import math
from collections.abc import Sequence
from uuid import UUID

from core.corrosion_allowance_circuit import CorrosionAllowanceCircuit
from engineering.validation import ValidationError, ValidationIssue
from repositories.corrosion_allowance_circuit_repository import (
    CorrosionAllowanceCircuitRepository,
    CorrosionAllowanceCircuitRepositoryConflictError,
)


class CorrosionAllowanceCircuitValidationError(ValidationError): pass
class CorrosionAllowanceCircuitConflictError(ValidationError): pass
class CorrosionAllowanceCircuitNotFoundError(ValidationError, LookupError): pass


class CorrosionAllowanceCircuitService:
    """Owns editable D243 defaults; they are not an external standard claim."""

    DEFAULT_CODE = "FUEL"

    def __init__(self, repository: CorrosionAllowanceCircuitRepository) -> None:
        self._repository = repository

    def get_active_circuits(self) -> Sequence[CorrosionAllowanceCircuit]:
        return self._repository.list(active_only=True)

    def get_all_circuits(self) -> Sequence[CorrosionAllowanceCircuit]:
        return self._repository.list()

    def get_circuit_by_code(self, code: str) -> CorrosionAllowanceCircuit:
        item = self._repository.get_by_code(code)
        if item is None:
            raise CorrosionAllowanceCircuitNotFoundError(ValidationIssue("circuit_not_found"))
        return item

    def create_circuit(self, **values: object) -> CorrosionAllowanceCircuit:
        item = CorrosionAllowanceCircuit(**values)  # type: ignore[arg-type]
        self._normalise(item); self._validate(item)
        try: return self._repository.create(item)
        except CorrosionAllowanceCircuitRepositoryConflictError as error:
            raise CorrosionAllowanceCircuitConflictError(ValidationIssue("circuit_duplicate")) from error

    def update_circuit(self, item: CorrosionAllowanceCircuit) -> CorrosionAllowanceCircuit:
        self._normalise(item); self._validate(item); item.touch()
        try: return self._repository.update(item)
        except KeyError as error: raise CorrosionAllowanceCircuitNotFoundError(ValidationIssue("circuit_not_found")) from error
        except CorrosionAllowanceCircuitRepositoryConflictError as error:
            raise CorrosionAllowanceCircuitConflictError(ValidationIssue("circuit_duplicate")) from error

    def delete_circuit(self, item_id: UUID) -> None:
        try: self._repository.delete(item_id)
        except KeyError as error: raise CorrosionAllowanceCircuitNotFoundError(ValidationIssue("circuit_not_found")) from error

    @staticmethod
    def _normalise(item: CorrosionAllowanceCircuit) -> None:
        item.code = item.code.strip(); item.display_name = item.display_name.strip(); item.description = item.description.strip()

    @staticmethod
    def _validate(item: CorrosionAllowanceCircuit) -> None:
        if not item.code: raise CorrosionAllowanceCircuitValidationError(ValidationIssue("required", "field.circuit_code"))
        if not item.display_name: raise CorrosionAllowanceCircuitValidationError(ValidationIssue("required", "field.circuit"))
        if isinstance(item.default_corrosion_allowance_mm, bool) or not math.isfinite(item.default_corrosion_allowance_mm) or item.default_corrosion_allowance_mm < 0:
            raise CorrosionAllowanceCircuitValidationError(ValidationIssue("zero_or_greater", "field.default_corrosion_allowance"))
