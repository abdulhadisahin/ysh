"""Hydraulic explanation adapter: every result is read, never recalculated."""
from dataclasses import replace

from engineering.formula.common import step, used, variable
from engineering.formula.models import FormulaStep, SelectionReason
from engineering.head_loss.v2_models import DischargeV2Result
from engineering.pipe_design.transfer import PipeInputMode
from engineering.provenance import SourceReference, SourceType
from engineering.suction_npsh.v2_models import SuctionV2LossResult


def hydraulic_steps(result: DischargeV2Result | SuctionV2LossResult) -> tuple[FormulaStep, ...]:
    """Explain exact applied Q/Di and the authoritative hydraulic intermediates."""
    inp = result.input
    state = inp.pipe_input
    linked = state.mode is PipeInputMode.LINKED
    origin = SourceReference(source_type=SourceType.CALCULATED if linked else SourceType.USER_INPUT)
    reason = SelectionReason.LINKED_PIPE_SELECTION if linked else SelectionReason.USER_INPUT
    q = variable("Q", result.flow_rate_m3_h, "m³/h", source=origin, reason=reason)
    di = variable("Di", result.actual_internal_diameter_mm, "mm", source=origin, reason=reason)
    if linked:
        snapshot = state.snapshot
        assert snapshot is not None
        q, di = (replace(v, source_selection_id=snapshot.source_selection_id,
                         source_revision=snapshot.source_revision) for v in (q, di))
    v = variable("V", result.flow_velocity_m_s, "m/s")
    re = variable("Re", result.reynolds_number)
    f = variable("f", result.friction_factor)
    manual = SourceReference(source_type=SourceType.USER_INPUT)
    length = variable("L", inp.pipe_length_m, "m", source=manual)
    nu = variable("ν", result.metadata["viscosity_m2s"] if isinstance(result, SuctionV2LossResult)
                  else inp.kinematic_viscosity_m2s, "m²/s", source=manual)
    k_source = SourceReference(source_type=SourceType.MATERIAL_STANDARD if inp.material_id else SourceType.USER_INPUT)
    k = variable("k", inp.roughness_mm, "mm", source=k_source,
                 reason=SelectionReason.MATERIAL_LIBRARY if inp.material_id else SelectionReason.USER_INPUT)
    kt = variable("Ktotal", result.local_loss_coefficient_total)
    hf = variable("hf", result.pipe_friction_loss_m, "m")
    hl = variable("hL", result.local_loss_m, "m")
    suction = isinstance(result, SuctionV2LossResult)
    total_symbol = "he" if suction else "hhat"
    prefix = "suction" if suction else "discharge"
    friction_formula = {
        "Laminar": "f = 64 / Re",
        "Transitional": "f = 64/Re + (fColebrook − 64/Re) × ((Re − 2300)/1700)",
        "Turbulent": "1/√f = −2 log10(k/(3.7Di) + 2.51/(Re√f))",
    }.get(result.flow_regime, "formula2.f_equation")
    steps = [
        step(f"{prefix}.V", "V", result.flow_velocity_m_s, "m/s", "V = 4Q / (πDi²)", (q, di), 0),
        step(f"{prefix}.Re", "Re", result.reynolds_number, "", "Re = VDi / ν", (v, di, nu), 1),
        step(f"{prefix}.f", "f", result.friction_factor, "", friction_formula, (re, k, di), 2,
             used_values=(used("k", inp.roughness_mm, "mm", source=k_source),)),
        step(f"{prefix}.hf", "hf", result.pipe_friction_loss_m, "m", "hf = 6.4 × 10⁶ × f × L × Q² / Di⁵", (f, length, q, di), 3),
        step(f"{prefix}.hL", "hL", result.local_loss_m, "m", "hL = 6400 × Ktotal × Q² / Di⁴", (kt, q, di), 4,
             used_values=(used("Ktotal", result.local_loss_coefficient_total,
                               source=SourceReference(source_type=SourceType.CALCULATED)),)),
        step(f"{prefix}.{total_symbol}", total_symbol, result.total_hydraulic_loss_m, "m",
             f"{total_symbol} = hf + hL", (hf, hl), 5),
    ]
    if not suction:
        steps.append(step("discharge.Hs", "Hs", result.system_head_m, "m", "Hs = Hgeo + hhat",
                          (variable("Hgeo", result.geodetic_head_m, "m", source=manual),
                           variable("hhat", result.total_hydraulic_loss_m, "m")), 6))
    return tuple(steps)
