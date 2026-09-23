"""Tests for centralized engineering numeric input normalization."""

from __future__ import annotations

import pytest

from engineering.exceptions import EngineeringValidationError
from engineering.input_parsing import parse_engineering_float, parse_engineering_integer


@pytest.mark.parametrize(("text", "expected"), [("12.5", 12.5), ("12,5", 12.5), ("-12.5", -12.5), ("-12,5", -12.5), ("2.92e-6", 2.92e-6), ("2,92e-6", 2.92e-6), (" 12,5 ", 12.5)])
def test_float_accepts_supported_engineering_forms(text: str, expected: float) -> None:
    """Accept point/comma decimals and scientific notation."""
    assert parse_engineering_float(text, field_name="Value") == expected


@pytest.mark.parametrize("text", ("", "NaN", "infinity", "1,234.5", "1.234,5", "invalid"))
def test_float_rejects_invalid_or_ambiguous_values(text: str) -> None:
    """Reject missing, non-finite, text, and thousands-style values."""
    with pytest.raises(EngineeringValidationError):
        parse_engineering_float(text, field_name="Value")


def test_optional_empty_and_integer_parsing() -> None:
    """Allow optional blanks and retain strict integer validation."""
    assert parse_engineering_float(" ", field_name="Value", allow_empty=True) is None
    assert parse_engineering_integer("-12", field_name="Quantity") == -12
    with pytest.raises(EngineeringValidationError):
        parse_engineering_integer("12,5", field_name="Quantity")


@pytest.mark.parametrize("text", ("", "   ", "abc", "1,2.3"))
def test_invalid_float_messages_are_user_friendly(text: str) -> None:
    """Parser failures name the field without exposing Python conversion details."""
    with pytest.raises(EngineeringValidationError) as error:
        parse_engineering_float(text, field_name="Flow Rate")
    message = str(error.value)
    assert "Flow Rate" in message
    assert not any(token in message for token in ("could not convert", "ValueError", "invalid literal", "Traceback"))


def test_optional_empty_value_remains_available_for_optional_inputs() -> None:
    """Optional engineering fields retain an empty ``None`` representation."""
    assert parse_engineering_float("", field_name="NPSH Required", allow_empty=True) is None
