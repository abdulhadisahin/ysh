"""Opt-in V2 orchestration of pure pipe sizing, configured rules and selection."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from uuid import UUID

from engineering.pipe_design.calculator import PipeDesignCalculator, wall_from_stress
from engineering.pipe_design.models import PipeDiameterInput
from engineering.pipe_design.rules import DesignStatus, _finite_temperature
from engineering.pipe_design.selection import actual_velocity, select_pipe_candidate, select_standard_wall
from engineering.pipe_design.v2_models import PipeCandidate, PipeDesignV2Input, PipeSelection, WallBreakdown
from engineering.pipe_design.validation import _positive, _non_negative
from engineering.provenance import EngineeringValue, OverridePolicy, SourceReference, SourceType, VerificationStatus
from engineering.validation import ValidationError, ValidationIssue


def _value(
    supplied: EngineeringValue | None, number: float | None,
    unit: str, symbol: str | None, source: SourceReference | None,
    *, calculated: bool = False,
) -> EngineeringValue | None:
    if supplied is not None:
        if (number is None or supplied.used_value != number or supplied.unit != unit
                or symbol is not None and supplied.symbol not in (None, symbol)):
            raise ValidationError(ValidationIssue("valid_number", "engineering_provenance"))
        return supplied
    if number is None:
        return None
    reference = source or SourceReference(source_type=SourceType.USER_INPUT, verification_status=VerificationStatus.USER_SUPPLIED)
    return EngineeringValue(
        used_value=number, unit=unit, source=reference,
        override_policy=OverridePolicy.LOCKED if calculated else OverridePolicy.USER_INPUT,
        recommended_value=number if calculated else None,
        symbol=symbol, terminology_key=f"engineering.{symbol}" if symbol else None,
    )


class PipeDesignV2Calculator:
    """A separate V2 path; it does not modify legacy DN or wall-selection behavior."""

    def calculate(self, value: PipeDesignV2Input, candidates: Sequence[PipeCandidate]) -> PipeSelection:
        """Return normal missing-candidate/source outcomes as structured results."""
        diameter = PipeDesignCalculator().calculate_diameter(PipeDiameterInput(value.flow_rate_m3_h, value.design_velocity_m_s))
        if not isinstance(value.standard_id, UUID):
            raise ValidationError(ValidationIssue("selection_required", "field.pipe_standard"))
        _positive(value.design_pressure_bar, "field.design_pressure")
        _positive(value.weld_factor, "field.weld_factor")
        _non_negative(value.corrosion_allowance_mm, "field.corrosion_allowance")
        if value.bend_allowance_enabled:
            _positive(value.bend_radius_mm, "field.bend_radius")
        if value.design_temperature_c is not None:
            _finite_temperature(value.design_temperature_c)
        supplied = value.provenance
        provenance = replace(
            supplied,
            design_velocity=_value(supplied.design_velocity, value.design_velocity_m_s, "m/s", "V", None),
            source_factor=_value(supplied.source_factor, value.weld_factor, "-", "v", None),
            corrosion_allowance=_value(supplied.corrosion_allowance, value.corrosion_allowance_mm, "mm", "c", None),
        )
        result = PipeSelection(
            status=DesignStatus.NO_PIPE_CANDIDATE,
            theoretical_internal_diameter_mm=diameter.diameter_mm,
            flow_rate_m3_h=value.flow_rate_m3_h, design_velocity_m_s=value.design_velocity_m_s,
            selected_standard_id=value.standard_id, selected_standard_code=value.standard_code,
            design_temperature_c=value.design_temperature_c,
            material_id=value.material_id, fluid_id=value.fluid_id,
            system_id=value.system_id, circuit_id=value.circuit_id, provenance=provenance,
        )
        candidate = select_pipe_candidate(diameter.diameter_mm, candidates, value.standard_id, standard_code=value.standard_code)
        if candidate is None:
            return result
        result = replace(result, candidate=candidate, selected_standard_code=candidate.standard_code)
        stress = value.stress_rule.evaluate(
            yield_strength_mpa=value.yield_strength_mpa, safety_factor=value.safety_factor,
            design_temperature_c=value.design_temperature_c,
        )
        if stress.value is None:
            return replace(result, status=stress.status, allowable_stress=stress)
        _positive(stress.value, "result.allowable_stress")
        legacy_wall = wall_from_stress(
            candidate.outside_diameter_mm, value.design_pressure_bar, stress.value,
            value.weld_factor, value.corrosion_allowance_mm,
            value.bend_allowance_enabled, value.bend_radius_mm,
        )
        tolerance = value.tolerance_rule.evaluate(legacy_wall.base_wall_thickness_mm)
        minimum = value.minimum_wall_rule.evaluate()
        calculated = legacy_wall.final_wall_thickness_mm
        if tolerance.value is not None:
            calculated += tolerance.value
        final = calculated if minimum.value is None else max(calculated, minimum.value)
        wall = WallBreakdown(
            legacy_wall.base_wall_thickness_mm, legacy_wall.bend_allowance_mm,
            legacy_wall.corrosion_allowance_mm, tolerance.value,
            calculated, minimum.value, final,
        )
        selected = select_standard_wall(final, candidate, candidates, required_internal_diameter_mm=diameter.diameter_mm)
        if selected is None:
            status = DesignStatus.NO_STANDARD_WALL_MATCH
        elif DesignStatus.SOURCE_REQUIRED in (tolerance.status, minimum.status):
            status = DesignStatus.SOURCE_REQUIRED
        elif DesignStatus.RULE_NOT_CONFIGURED in (tolerance.status, minimum.status):
            status = DesignStatus.RULE_NOT_CONFIGURED
        else:
            status = DesignStatus.SUCCESS
        provenance = replace(
            provenance,
            allowable_stress=_value(supplied.allowable_stress, stress.value, "MPa", "σallow", stress.source, calculated=True),
            manufacturing_tolerance=_value(supplied.manufacturing_tolerance, tolerance.value, "mm", None, tolerance.source, calculated=True),
            minimum_wall=_value(supplied.minimum_wall, minimum.value, "mm", "s", minimum.source, calculated=True),
        )
        return replace(
            result, status=status, selected_pipe=selected,
            actual_velocity_m_s=actual_velocity(value.flow_rate_m3_h, selected.actual_internal_diameter_mm) if selected else None,
            wall=wall, allowable_stress=stress, manufacturing_tolerance=tolerance,
            minimum_wall=minimum, provenance=provenance,
        )
