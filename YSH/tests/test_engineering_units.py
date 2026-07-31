"""Tests for explicit YSH engineering unit conversions."""

from __future__ import annotations

import math

import pytest

from engineering.exceptions import UnitConversionError, UnsupportedUnitError
from engineering.units import (
    convert_flow_rate,
    convert_kinematic_viscosity,
    convert_length,
    convert_pressure,
    validate_density,
)


@pytest.mark.parametrize(
    ("value", "source", "target", "expected"),
    [
        (1_000.0, "mm", "m", 1.0),
        (1.0, "m", "mm", 1_000.0),
    ],
)
def test_length_conversions(
    value: float,
    source: str,
    target: str,
    expected: float,
) -> None:
    """Length conversions support both required directions."""
    assert convert_length(value, source, target) == pytest.approx(expected)


@pytest.mark.parametrize(
    ("value", "source", "target", "expected"),
    [
        (1_000.0, "Pa", "kPa", 1.0),
        (1.0, "kPa", "Pa", 1_000.0),
        (1_000_000.0, "Pa", "MPa", 1.0),
        (1.0, "MPa", "Pa", 1_000_000.0),
        (100_000.0, "Pa", "bar", 1.0),
        (1.0, "bar", "Pa", 100_000.0),
        (1.0, "MPa", "N/mm²", 1.0),
        (1.0, "N/mm²", "MPa", 1.0),
    ],
)
def test_pressure_conversions(
    value: float,
    source: str,
    target: str,
    expected: float,
) -> None:
    """Pressure conversions support every required forward and reverse pair."""
    assert convert_pressure(value, source, target) == pytest.approx(expected)


@pytest.mark.parametrize(
    ("value", "source", "target", "expected"),
    [
        (3_600.0, "m³/h", "m³/s", 1.0),
        (1.0, "m³/s", "m³/h", 3_600.0),
        (1.0, "cSt", "m²/s", 0.000001),
        (0.000001, "m²/s", "cSt", 1.0),
    ],
)
def test_flow_and_viscosity_conversions(
    value: float,
    source: str,
    target: str,
    expected: float,
) -> None:
    """Flow-rate and viscosity conversions support both required directions."""
    converter = (
        convert_flow_rate if "³" in source or "³" in target else convert_kinematic_viscosity
    )
    assert converter(value, source, target) == pytest.approx(expected)


@pytest.mark.parametrize(
    ("converter", "value", "source", "target"),
    [
        (convert_length, 123.456, "mm", "m"),
        (convert_pressure, 123_456.0, "Pa", "bar"),
        (convert_flow_rate, 123.456, "m³/h", "m³/s"),
        (convert_kinematic_viscosity, 12.3456, "cSt", "m²/s"),
    ],
)
def test_conversions_round_trip(
    converter: object,
    value: float,
    source: str,
    target: str,
) -> None:
    """Required conversions remain reversible within floating-point tolerance."""
    converted_value = converter(value, source, target)
    assert converter(converted_value, target, source) == pytest.approx(value)


def test_unsupported_unit_is_rejected() -> None:
    """An unsupported conversion unit raises a clear unit exception."""
    with pytest.raises(UnsupportedUnitError, match="Unsupported unit"):
        convert_length(1.0, "ft", "m")


def test_cross_quantity_unit_is_rejected() -> None:
    """A known but incompatible unit raises a conversion exception."""
    with pytest.raises(UnitConversionError, match="Cannot convert"):
        convert_length(1.0, "Pa", "m")


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_non_finite_conversion_value_is_rejected(value: float) -> None:
    """Conversion functions reject every non-finite input value."""
    with pytest.raises(Exception, match="finite"):
        convert_pressure(value, "Pa", "kPa")


def test_density_validation_preserves_internal_unit_value() -> None:
    """Density is validated without adding unsupported conversions."""
    assert validate_density(998.2) == pytest.approx(998.2)
