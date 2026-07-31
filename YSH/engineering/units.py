"""Explicit unit conversion functions for YSH Version 1."""

from __future__ import annotations

from collections.abc import Mapping

from engineering.exceptions import UnitConversionError, UnsupportedUnitError
from engineering.validation import validate_finite_number, validate_positive_number

DENSITY_INTERNAL_UNIT: str = "kg/m³"

_UNIT_ALIASES: Mapping[str, str] = {
    "mm": "mm",
    "m": "m",
    "pa": "Pa",
    "kpa": "kPa",
    "mpa": "MPa",
    "bar": "bar",
    "n/mm²": "N/mm²",
    "n/mm2": "N/mm²",
    "m³/h": "m³/h",
    "m3/h": "m³/h",
    "m³/s": "m³/s",
    "m3/s": "m³/s",
    "cst": "cSt",
    "m²/s": "m²/s",
    "m2/s": "m²/s",
    "kg/m³": "kg/m³",
    "kg/m3": "kg/m³",
}

_CONVERSION_FACTORS: Mapping[str, Mapping[str, float]] = {
    "length": {"mm": 0.001, "m": 1.0},
    "pressure": {
        "Pa": 1.0,
        "kPa": 1_000.0,
        "MPa": 1_000_000.0,
        "bar": 100_000.0,
        "N/mm²": 1_000_000.0,
    },
    "flow_rate": {"m³/h": 1.0 / 3_600.0, "m³/s": 1.0},
    "kinematic_viscosity": {"cSt": 0.000001, "m²/s": 1.0},
}


def normalize_unit(unit: object) -> str:
    """Return a canonical supported unit name without guessing a conversion."""
    if not isinstance(unit, str):
        raise UnsupportedUnitError("Unit must be a supported text value.")
    normalized_key = unit.strip().casefold().replace(" ", "")
    try:
        return _UNIT_ALIASES[normalized_key]
    except KeyError as error:
        raise UnsupportedUnitError(f"Unsupported unit: {unit!r}.") from error


def convert_length(value: object, source_unit: object, target_unit: object) -> float:
    """Convert a finite length value between mm and m."""
    return _convert(value, source_unit, target_unit, "length")


def convert_pressure(value: object, source_unit: object, target_unit: object) -> float:
    """Convert a finite pressure value among the supported pressure units."""
    return _convert(value, source_unit, target_unit, "pressure")


def convert_flow_rate(
    value: object,
    source_unit: object,
    target_unit: object,
) -> float:
    """Convert a finite flow-rate value between m³/h and m³/s."""
    return _convert(value, source_unit, target_unit, "flow_rate")


def convert_kinematic_viscosity(
    value: object,
    source_unit: object,
    target_unit: object,
) -> float:
    """Convert a finite viscosity value between cSt and m²/s."""
    return _convert(value, source_unit, target_unit, "kinematic_viscosity")


def validate_density(value: object, parameter_name: str = "density") -> float:
    """Validate density in its internal kg/m³ unit without conversion."""
    return validate_positive_number(value, parameter_name)


def _convert(
    value: object,
    source_unit: object,
    target_unit: object,
    quantity: str,
) -> float:
    numeric_value = validate_finite_number(value, "value")
    source = normalize_unit(source_unit)
    target = normalize_unit(target_unit)
    factors = _CONVERSION_FACTORS[quantity]
    if source not in factors or target not in factors:
        raise UnitConversionError(
            f"Cannot convert {quantity.replace('_', ' ')} from {source} to {target}."
        )
    return numeric_value * factors[source] / factors[target]
