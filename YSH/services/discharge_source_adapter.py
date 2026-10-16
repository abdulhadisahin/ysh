"""Explicit compatibility adapter from existing Pipe Design inputs to V2 results."""
from __future__ import annotations

from uuid import UUID

from engineering.input_parsing import parse_engineering_float
from engineering.pipe_design.v2_models import PipeDesignV2Input, PipeSelection
from engineering.validation import ValidationError, ValidationIssue
from services.pipe_design_service import PipeDesignService


def prepare_discharge_source(
    service: PipeDesignService, state: dict[str, object],
    previous: PipeSelection | None = None, *, manual_material: bool,
) -> PipeSelection:
    """Calculate/publish only on explicit source action; never use legacy D as Di.

    Both diameter and wall inputs are required. Rule configuration stays exactly
    as supplied by the existing V2 service, including provisional rule statuses.
    """
    standard = next((s for s in service.get_available_pipe_standards()
                     if s.code == state.get("pipe_standard_code")), None)
    if standard is None:
        raise ValidationError(ValidationIssue("pipe_standard_required"))
    fields = state.get("fields", {})
    labels = {"q": "field.flow_rate", "v": "field.design_velocity",
              "pc": "field.design_pressure", "wf": "field.weld_factor",
              "c": "field.corrosion_allowance", "rp": "field.yield_strength",
              "sf": "field.safety_factor", "r": "field.bend_radius"}

    def number(key: str) -> float:
        return parse_engineering_float(fields.get(key, ""), field_name=key,
                                       field_key=labels[key])

    material_id = state.get("material_id")
    manual = manual_material
    if not manual and not material_id:
        raise ValidationError(ValidationIssue("selection_required", "field.material"))
    circuit = next((c for c in service.get_active_corrosion_allowance_circuits()
                    if c.code == state.get("circuit_code")), None)
    value = PipeDesignV2Input(
        flow_rate_m3_h=number("q"), design_velocity_m_s=number("v"),
        standard_id=standard.id, standard_code=standard.code,
        design_pressure_bar=number("pc"), weld_factor=number("wf"),
        corrosion_allowance_mm=number("c"),
        yield_strength_mpa=number("rp") if manual else None,
        safety_factor=number("sf"),
        bend_allowance_enabled=bool(state.get("bend_enabled", False)),
        bend_radius_mm=number("r") if state.get("bend_enabled") else None,
        material_id=UUID(str(material_id)) if not manual else None,
        circuit_id=circuit.id if circuit else None,
    )
    return service.calculate_v2(value, previous_selection=previous)
