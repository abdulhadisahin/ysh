"""Authoritative ENPY arithmetic composed with the shared head-loss engine."""
from __future__ import annotations

from engineering.head_loss.calculator import DischargeHeadLossCalculator
from engineering.head_loss.models import DischargeHeadLossInput
from engineering.suction_npsh.models import ENPYInput, SuctionNPSHInput, SuctionNPSHResult
from engineering.validation import ValidationError, ValidationIssue


class SuctionNPSHCalculator:
    """Reuse shared hydraulics and evaluate ENPY with one implementation."""

    def calculate(self, value: SuctionNPSHInput) -> SuctionNPSHResult:
        """Keep the combined API and its ENPY-before-hydraulics validation order."""
        self._validate_input(value)
        loss = DischargeHeadLossCalculator().calculate(DischargeHeadLossInput(
            value.inside_diameter_mm, value.flow_rate_m3h,
            value.kinematic_viscosity_m2s, value.pipe_length_m,
            value.roughness_mm, 0, value.local_loss_items,
        ))
        result = self.calculate_enpy(ENPYInput(
            loss.total_hydraulic_loss_m, value.suction_pressure_pa,
            value.vapour_pressure_pa, value.density_kg_m3,
            value.static_suction_height_m, value.npsh_required_m,
        ))
        result.warnings[:0] = loss.warnings
        result.metadata["head_loss"] = loss
        return result

    def calculate_enpy(self, value: ENPYInput) -> SuctionNPSHResult:
        """Calculate available ENPY from existing loss, without recomputing it.

        PE/Pb are absolute pressures in Pa; positive HEgeo subtracts head.
        NPSHr is an optional external input. No automatic safety margin is added.
        Existing entry points validate inputs before calling this arithmetic-only
        method: combined calculate() validates Pa values; the staged service
        validates raw pressure values before conversion, preserving its contract.
        """
        g = 9.80665
        pe = value.suction_pressure_pa / (value.density_kg_m3 * g)
        pb = value.vapour_pressure_pa / (value.density_kg_m3 * g)
        enpy = pe - pb - value.static_suction_height_m - value.suction_line_loss_m
        margin = None if value.npsh_required_m is None else enpy - value.npsh_required_m
        warnings = []
        if enpy < 0:
            warnings.append(ValidationIssue("negative_available_npsh"))
        if margin is not None and margin < 0:
            warnings.append(ValidationIssue("npsh_below_required"))
        return SuctionNPSHResult(
            value.suction_line_loss_m, pe, pb, enpy, margin, [], warnings,
            {"formula": "ENPYm = PE/(rho*g) - Pb/(rho*g) - HEgeo - he"},
        )

    @staticmethod
    def _validate_input(value: SuctionNPSHInput) -> None:
        """Preserve ENPY validation fields, bounds and optional required input."""
        import math
        checks = (
            (value.suction_pressure_pa, "field.suction_pressure", False),
            (value.vapour_pressure_pa, "field.vapour_pressure", False),
            (value.density_kg_m3, "field.fluid_density", True),
            (value.static_suction_height_m, "field.static_suction_height", None),
        )
        for number, field_key, positive in checks:
            if isinstance(number, bool) or not isinstance(number, (int, float)) or not math.isfinite(number):
                raise ValidationError(ValidationIssue("valid_number", field_key))
            if positive and number <= 0:
                raise ValidationError(ValidationIssue("greater_than_zero", field_key))
            if positive is False and number < 0:
                raise ValidationError(ValidationIssue("zero_or_greater", field_key))
        required = value.npsh_required_m
        if required is not None and (isinstance(required, bool) or not isinstance(required, (int, float)) or not math.isfinite(required)):
            raise ValidationError(ValidationIssue("valid_number", "field.npsh_required"))
