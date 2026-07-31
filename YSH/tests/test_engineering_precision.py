"""Tests for engineering display precision utilities."""

from __future__ import annotations

import pytest

from engineering.exceptions import EngineeringValidationError
from engineering.precision import (
    DEFAULT_DECIMAL_PLACES,
    format_engineering_value,
    round_for_display,
)


def test_default_display_rounding_uses_six_decimal_places() -> None:
    """Default display rounding uses the required six decimal places."""
    assert DEFAULT_DECIMAL_PLACES == 6
    assert round_for_display(1.23456789) == pytest.approx(1.234568)


def test_custom_display_rounding_uses_requested_places() -> None:
    """Custom display rounding honors the requested decimal count."""
    assert round_for_display(1.23456789, 3) == pytest.approx(1.235)


def test_display_rounding_does_not_mutate_source_value() -> None:
    """Display rounding returns a separate value and leaves the source unchanged."""
    value = 1.23456789
    round_for_display(value)

    assert value == 1.23456789


def test_negative_decimal_places_are_rejected() -> None:
    """Negative display precision is rejected clearly."""
    with pytest.raises(EngineeringValidationError, match="must not be negative"):
        round_for_display(1.0, -1)


def test_engineering_format_uses_stable_fixed_decimals() -> None:
    """Formatting uses exactly the requested fixed decimal places."""
    assert format_engineering_value(12.5) == "12.500000"
    assert format_engineering_value(12.5, 2) == "12.50"
