"""Tests for reusable engineering input validation."""

from __future__ import annotations

import math

import pytest

from engineering.exceptions import EngineeringValidationError
from engineering.validation import (
    validate_allowed_choice,
    validate_finite_number,
    validate_inclusive_range,
    validate_non_negative_number,
    validate_positive_number,
    validate_required_text,
)


def test_required_text_normalizes_whitespace() -> None:
    """Required text is stripped before being returned."""
    assert validate_required_text("  Project Name  ", "name") == "Project Name"


@pytest.mark.parametrize("value", ["", "   "])
def test_required_text_rejects_empty_values(value: str) -> None:
    """Empty and whitespace-only text values are rejected."""
    with pytest.raises(EngineeringValidationError, match="required"):
        validate_required_text(value, "name")


def test_positive_and_non_negative_values_are_valid() -> None:
    """Positive and zero-permitted values pass their matching validation rules."""
    assert validate_positive_number(0.1, "pressure") == pytest.approx(0.1)
    assert validate_non_negative_number(0.0, "flow") == pytest.approx(0.0)


def test_positive_value_rejects_zero_and_negative_values() -> None:
    """Positive-value validation rejects zero and negative values."""
    for value in (0.0, -1.0):
        with pytest.raises(EngineeringValidationError, match="greater than zero"):
            validate_positive_number(value, "pressure")


def test_non_negative_value_rejects_negative_value() -> None:
    """Non-negative validation rejects negative values."""
    with pytest.raises(EngineeringValidationError, match="greater than or equal"):
        validate_non_negative_number(-0.1, "flow")


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf, True])
def test_finite_number_rejects_non_finite_and_boolean_values(value: object) -> None:
    """Non-finite values and booleans are not accepted as engineering numbers."""
    with pytest.raises(EngineeringValidationError):
        validate_finite_number(value, "value")


def test_inclusive_range_accepts_boundaries() -> None:
    """Inclusive ranges accept both lower and upper bounds."""
    assert validate_inclusive_range(0.0, 0.0, 1.0, "factor") == 0.0
    assert validate_inclusive_range(1.0, 0.0, 1.0, "factor") == 1.0


def test_inclusive_range_rejects_outside_value() -> None:
    """Inclusive ranges reject values outside the specified bounds."""
    with pytest.raises(EngineeringValidationError, match="between"):
        validate_inclusive_range(1.1, 0.0, 1.0, "factor")


def test_allowed_choice_rejects_invalid_value() -> None:
    """Allowed-choice validation rejects a value outside the supplied choices."""
    with pytest.raises(EngineeringValidationError, match="must be one of"):
        validate_allowed_choice("steam", ("water", "oil"), "fluid")
