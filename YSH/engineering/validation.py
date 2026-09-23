"""Semantic validation primitives shared by YSH engineering boundaries."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Mapping


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    """Describe a validation failure without embedding display-language text."""

    code: str
    field_key: str | None = None
    params: Mapping[str, object] | None = None


class ValidationError(ValueError):
    """Raise one semantic validation issue across service and UI boundaries."""

    def __init__(self, issue: ValidationIssue) -> None:
        """Store the semantic issue without creating a user-facing sentence."""
        self.issue = issue
        super().__init__(issue.code)


def validate_finite_number(value: object, name: str) -> float:
    """Retain the established Engineering Core finite-number validation API."""
    from engineering.exceptions import EngineeringValidationError
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise EngineeringValidationError(f"{name} must be a finite number.")
    return float(value)


def validate_required_text(value: object, name: str) -> str:
    """Return required normalized text through the established API."""
    from engineering.exceptions import EngineeringValidationError
    if not isinstance(value, str) or not value.strip(): raise EngineeringValidationError(f"{name} is required.")
    return value.strip()


def validate_positive_number(value: object, name: str) -> float:
    """Validate an established positive-number contract."""
    result = validate_finite_number(value, name)
    if result <= 0: raise __import__("engineering.exceptions", fromlist=["EngineeringValidationError"]).EngineeringValidationError(f"{name} must be greater than zero.")
    return result


def validate_non_negative_number(value: object, name: str) -> float:
    """Validate an established non-negative-number contract."""
    result = validate_finite_number(value, name)
    if result < 0: raise __import__("engineering.exceptions", fromlist=["EngineeringValidationError"]).EngineeringValidationError(f"{name} must be greater than or equal to zero.")
    return result


def validate_inclusive_range(value: object, lower: float, upper: float, name: str) -> float:
    """Validate an established inclusive numeric range contract."""
    result = validate_finite_number(value, name)
    if not lower <= result <= upper: raise __import__("engineering.exceptions", fromlist=["EngineeringValidationError"]).EngineeringValidationError(f"{name} must be between {lower} and {upper}.")
    return result


def validate_allowed_choice(value: object, choices: tuple[object, ...], name: str) -> object:
    """Validate an established allowed-choice contract."""
    from engineering.exceptions import EngineeringValidationError
    if value not in choices: raise EngineeringValidationError(f"{name} must be one of {choices}.")
    return value
