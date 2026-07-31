"""Display precision utilities for engineering values."""

from __future__ import annotations

from engineering.exceptions import EngineeringValidationError
from engineering.validation import validate_finite_number

DEFAULT_DECIMAL_PLACES: int = 6


def round_for_display(
    value: object,
    decimal_places: int = DEFAULT_DECIMAL_PLACES,
) -> float:
    """Round a finite engineering value only for user-facing display."""
    _validate_decimal_places(decimal_places)
    return round(validate_finite_number(value, "value"), decimal_places)


def format_engineering_value(
    value: object,
    decimal_places: int = DEFAULT_DECIMAL_PLACES,
) -> str:
    """Format a finite engineering value with a fixed number of decimals."""
    _validate_decimal_places(decimal_places)
    rounded_value = round_for_display(value, decimal_places)
    return f"{rounded_value:.{decimal_places}f}"


def _validate_decimal_places(decimal_places: object) -> None:
    if isinstance(decimal_places, bool) or not isinstance(decimal_places, int):
        raise EngineeringValidationError("decimal_places must be a non-negative integer.")
    if decimal_places < 0:
        raise EngineeringValidationError("decimal_places must not be negative.")
