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
    result = apply_recommended_wall(service.calculate_v2(value), state)
    if previous is not None:
        from engineering.pipe_design.transfer import revise_selection
        result = revise_selection(previous, result)
    return result


def apply_recommended_wall(selection: PipeSelection, state: dict[str, object]) -> PipeSelection:
    """Hydraulic pages use the Pipe Design page's last recommended nominal wall and its outside diameter.

    Only a completed wall calculation with a MATCH nominal wall overrides the library lookup;
    otherwise the existing library-based selection is kept unchanged.
    """
    import math
    from dataclasses import replace
    from uuid import NAMESPACE_URL, uuid5
    from engineering.pipe_design.v2_models import PipeCandidate
    from engineering.provenance import SourceReference, SourceType, VerificationStatus
    basis = state.get("wall_standard_basis") or {}
    nominal = basis.get("nominal_wall_mm")
    if not state.get("wall_result") or not isinstance(nominal, (int, float)) or isinstance(nominal, bool):
        return selection
    try:
        outside = parse_engineering_float((state.get("fields") or {}).get("da", ""),
                                          field_name="da", field_key="field.pipe_outside_diameter")
    except ValidationError:
        return selection
    inside = outside - 2 * nominal
    if not (math.isfinite(outside) and nominal > 0 and inside > 0):
        return selection
    standard = basis.get("nominal_standard") or "Pipe Design"
    candidate = PipeCandidate(
        id=uuid5(NAMESPACE_URL, f"d243:recommended-wall:{selection.selected_standard_id}:{outside!r}:{nominal!r}"),
        standard_id=selection.selected_standard_id, standard_code=selection.selected_standard_code,
        outside_diameter_mm=outside, wall_thickness_mm=float(nominal), inside_diameter_mm=inside,
        nominal_diameter=f"OD {outside:g}",
        dimension_source=SourceReference(
            source_type=SourceType.CALCULATED, document=str(standard),
            verification_status=VerificationStatus.UNVERIFIED,
            notes="Pipe Design recommended nominal wall and entered outside diameter."))
    velocity = selection.flow_rate_m3_h / 3600.0 / (math.pi / 4.0 * (inside / 1000.0) ** 2)
    return replace(selection, selected_pipe=candidate, actual_velocity_m_s=velocity)
