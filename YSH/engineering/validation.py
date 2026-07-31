"""Reusable validation functions for engineering inputs."""

from __future__ import annotations

import math
from collections.abc import Collection
from numbers import Real

from engineering.exceptions import EngineeringValidationError


def validate_required_text(value: object, parameter_name: str) -> str:
    """Return normalized required text or raise a clear validation error."""
    if not isinstance(value, str):
        raise EngineeringValidationError(f"{parameter_name} must be text.")
    normalized_value = value.strip()
    if not normalized_value:
        raise EngineeringValidationError(f"{parameter_name} is required.")
    return normalized_value


def validate_finite_number(value: object, parameter_name: str) -> float:
    """Return a finite numeric value while rejecting booleans and non-numerics."""
    if isinstance(value, bool) or not isinstance(value, Real):
        raise EngineeringValidationError(f"{parameter_name} must be a finite number.")
    normalized_value = float(value)
    if not math.isfinite(normalized_value):
        raise EngineeringValidationError(f"{parameter_name} must be finite.")
    return normalized_value


def validate_positive_number(value: object, parameter_name: str) -> float:
    """Return a finite number greater than zero."""
    normalized_value = validate_finite_number(value, parameter_name)
    if normalized_value <= 0:
        raise EngineeringValidationError(f"{parameter_name} must be greater than zero.")
    return normalized_value


def validate_non_negative_number(value: object, parameter_name: str) -> float:
    """Return a finite number greater than or equal to zero."""
    normalized_value = validate_finite_number(value, parameter_name)
    if normalized_value < 0:
        raise EngineeringValidationError(
            f"{parameter_name} must be greater than or equal to zero."
        )
    return normalized_value


def validate_inclusive_range(
    value: object,
    minimum: object,
    maximum: object,
    parameter_name: str,
) -> float:
    """Return a finite value constrained to inclusive finite bounds."""
    normalized_minimum = validate_finite_number(minimum, "minimum")
    normalized_maximum = validate_finite_number(maximum, "maximum")
    if normalized_minimum > normalized_maximum:
        raise EngineeringValidationError("minimum must not be greater than maximum.")
    normalized_value = validate_finite_number(value, parameter_name)
    if not normalized_minimum <= normalized_value <= normalized_maximum:
        raise EngineeringValidationError(
            f"{parameter_name} must be between {normalized_minimum} and "
            f"{normalized_maximum}, inclusive."
        )
    return normalized_value


def validate_percentage_range(
    value: object,
    minimum: object,
    maximum: object,
    parameter_name: str,
) -> float:
    """Validate a percentage against explicitly supplied inclusive bounds."""
    return validate_inclusive_range(value, minimum, maximum, parameter_name)


def validate_factor_range(
    value: object,
    minimum: object,
    maximum: object,
    parameter_name: str,
) -> float:
    """Validate a factor against explicitly supplied inclusive bounds."""
    return validate_inclusive_range(value, minimum, maximum, parameter_name)


def validate_allowed_choice(
    value: object,
    allowed_choices: Collection[object],
    parameter_name: str,
) -> object:
    """Return an allowed value or raise a clear validation error."""
    if value not in allowed_choices:
        raise EngineeringValidationError(
            f"{parameter_name} must be one of: "
            f"{', '.join(str(choice) for choice in allowed_choices)}."
        )
    return value
