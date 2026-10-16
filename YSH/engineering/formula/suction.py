"""ENPY explanations consume the one authoritative result and its used inputs."""
from engineering.formula.common import step, used, variable
from engineering.formula.discharge import hydraulic_steps
from engineering.formula.models import CheckStatus, FormulaCheck, FormulaStep
from engineering.suction_npsh.v2_models import SuctionV2Result
from engineering.provenance import SourceReference, SourceType


def suction_steps(result: SuctionV2Result) -> tuple[FormulaStep, ...]:
    """Preserve production margin semantics: only a negative margin warns."""
    inp = result.input
    check = None
    configured = ()
    if inp.npsh_required_m is not None:
        check = FormulaCheck(status=CheckStatus.WARNING if result.npsh_margin_m < 0 else CheckStatus.PASS,
                             actual_value=result.enpym_available_m,
                             reference_value=inp.npsh_required_m, operator=">=",
                             reason_key="formula2.npsh_check")
        configured = (used("NPSHr", inp.npsh_required_m, "m"),)
    manual = SourceReference(source_type=SourceType.USER_INPUT)
    variables = (
        variable("PE", result.metadata["suction_pressure_pa"], "Pa", source=manual),
        variable("Pb", result.metadata["vapour_pressure_pa"], "Pa", source=manual),
        variable("ρ", inp.density_kg_m3, "kg/m³", source=manual),
        variable("g", result.metadata["gravity_m_s2"], "m/s²"),
        variable("HEgeo", inp.static_suction_height_m, "m", source=manual),
        variable("he", result.suction_line_loss_m, "m"),
    )
    steps = list(hydraulic_steps(result.hydraulic))
    steps.append(step("suction.ENPYm", "ENPYm", result.enpym_available_m, "m",
                      "ENPYm = PE/(ρg) − Pb/(ρg) − HEgeo − he", variables, 6,
                      used_values=configured, check=check))
    if result.npsh_margin_m is not None:
        steps.append(step("suction.margin", "ΔENPY", result.npsh_margin_m, "m", "ΔENPY = ENPYm − NPSHr",
                          (variable("ENPYm", result.enpym_available_m, "m"),
                           variable("NPSHr", inp.npsh_required_m, "m")), 7))
    return tuple(steps)
