"""Validation helpers for approved pipe-design inputs."""
from __future__ import annotations
import math
from engineering.validation import ValidationError, ValidationIssue
from engineering.pipe_design.models import PipeDiameterInput, WallThicknessInput
def validate_diameter_input(value:PipeDiameterInput)->None:
    """Validate required diameter input values."""
    _positive(value.flow_rate_m3h,"field.flow_rate");_positive(value.design_velocity_mps,"field.design_velocity")
def validate_wall_input(value:WallThicknessInput)->None:
    """Validate all wall-thickness inputs before calculation."""
    _positive(value.outside_diameter_mm,"field.pipe_outside_diameter");_positive(value.design_pressure_bar,"field.design_pressure")
    if value.yield_strength_mpa is None:raise ValidationError(ValidationIssue("required","field.yield_strength"))
    _positive(value.yield_strength_mpa,"field.yield_strength");_positive(value.safety_factor,"field.safety_factor");_positive(value.weld_factor,"field.weld_factor");_non_negative(value.corrosion_allowance_mm,"field.corrosion_allowance")
    if value.bend_allowance_enabled: _positive(value.bend_radius_mm,"field.bend_radius")

def _positive(value: object, field_key: str) -> None:
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):raise ValidationError(ValidationIssue("valid_number",field_key))
    if value<=0:raise ValidationError(ValidationIssue("greater_than_zero",field_key))

def _non_negative(value: object, field_key: str) -> None:
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):raise ValidationError(ValidationIssue("valid_number",field_key))
    if value<0:raise ValidationError(ValidationIssue("zero_or_greater",field_key))
