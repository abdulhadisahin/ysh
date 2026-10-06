"""D243 fuel-capacity input normalization for Transfer Pump estimates."""

from __future__ import annotations

from dataclasses import dataclass
import math

from engineering.validation import ValidationError, ValidationIssue


FUEL_DENSITY_T_PER_M3 = 0.83
EMPTYING_TARGET_HOURS = 12.0
CAPACITY_MODE_VOLUME = "VOLUME"
CAPACITY_MODE_MASS = "MASS"
CAPACITY_INPUT_MODES = (CAPACITY_MODE_VOLUME, CAPACITY_MODE_MASS)


@dataclass(frozen=True, slots=True)
class FuelCapacityResolution:
    """Source input and derived authoritative m³ values for one calculation."""

    mode: str
    source_value: float
    volume_m3: float
    required_capacity_12h_m3h: float


def resolve_fuel_capacity(mode: str, source_value: float) -> FuelCapacityResolution:
    """Resolve direct m³ or D243 tonne input without rounding intermediate data."""
    field_key = "field.fuel_capacity_mass" if mode == CAPACITY_MODE_MASS else "field.fuel_capacity"
    if mode not in CAPACITY_INPUT_MODES:
        raise ValidationError(ValidationIssue("capacity_input_mode_invalid"))
    if isinstance(source_value, bool) or not isinstance(source_value, (int, float)) or not math.isfinite(source_value):
        raise ValidationError(ValidationIssue("valid_number", field_key))
    if source_value <= 0:
        raise ValidationError(ValidationIssue("greater_than_zero", field_key))
    volume = float(source_value) if mode == CAPACITY_MODE_VOLUME else float(source_value) / FUEL_DENSITY_T_PER_M3
    return FuelCapacityResolution(mode, float(source_value), volume, volume / EMPTYING_TARGET_HOURS)
