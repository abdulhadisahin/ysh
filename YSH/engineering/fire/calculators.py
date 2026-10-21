"""Pure source-decided mathematics; no UI, storage, margins or regulatory defaults."""
from engineering.fire.enums import FireSourceStatus, HWApplicability
from engineering.fire.models import FoamSystemInput, FoamSystemResult, HazenWilliamsInput, HazenWilliamsResult, NozzleRequest
from engineering.fire.validation import positive
from engineering.validation import ValidationError, ValidationIssue

# docs/fire_fighting_source_decisions.md S03, JCI/SKUM FDS-2017084-04 p.2.
# This coefficient belongs ONLY to L/min, mm, bar/m; not to a head-loss equation.
HW_COEFFICIENT = 605000.0
HW_FLOW_EXPONENT = 1.85
HW_DIAMETER_EXPONENT = 4.87


class FireCalculationBlocked(ValidationError):
    """A source/applicability gate, never a numeric result."""
    def __init__(self, status: FireSourceStatus, issue_id: str) -> None:
        self.status = status
        self.issue_id = issue_id
        super().__init__(ValidationIssue(status.value, issue_id))


def calculate_foam_system(value: FoamSystemInput) -> FoamSystemResult:
    if not isinstance(value, FoamSystemInput):
        raise TypeError("value requires FoamSystemInput")
    try:
        solution = value.protected_area_m2 * value.application_density_lpm_m2
        concentrate = value.foam_fraction * solution
        water = (1 - value.foam_fraction) * solution
        volume = concentrate * value.application_duration_min
    except OverflowError as error:
        raise ValidationError(ValidationIssue("fire.numeric_range", "FIRE.FOAM.SOLUTION_FLOW")) from error
    for number, name in ((solution, "solution_flow_lpm"), (concentrate, "foam_concentrate_flow_lpm"),
                         (water, "water_flow_lpm"), (volume, "foam_concentrate_volume_l")):
        positive(number, name)
    return FoamSystemResult(input=value, solution_flow_lpm=solution,
                            foam_concentrate_flow_lpm=concentrate,
                            water_flow_lpm=water, foam_concentrate_volume_l=volume)


def calculate_hazen_williams(value: HazenWilliamsInput) -> HazenWilliamsResult:
    if not isinstance(value, HazenWilliamsInput):
        raise TypeError("value requires HazenWilliamsInput")
    if value.applicability is not HWApplicability.WATER_ONLY:
        status = (FireSourceStatus.NOT_CONFIGURED if value.applicability is HWApplicability.NOT_CONFIGURED
                  else FireSourceStatus.SOURCE_REQUIRED)
        raise FireCalculationBlocked(status, "FIRE-HW-UNITS-001")
    try:
        per_m = (HW_COEFFICIENT * value.flow_lpm**HW_FLOW_EXPONENT /
                 (value.hazen_williams_c**HW_FLOW_EXPONENT *
                  value.inside_diameter_mm**HW_DIAMETER_EXPONENT))
        total = per_m * value.pipe_length_m
    except (OverflowError, ZeroDivisionError) as error:
        raise ValidationError(ValidationIssue("fire.numeric_range", "FIRE.HW.EQUATION")) from error
    positive(per_m, "pressure_loss_per_m_bar")
    positive(total, "total_pressure_loss_bar", zero_allowed=value.pipe_length_m == 0)
    return HazenWilliamsResult(input=value, pressure_loss_per_m_bar=per_m,
                              total_pressure_loss_bar=total)


def calculate_nozzle(value: NozzleRequest) -> None:
    """Deliberately no nozzle equation; supplied device/K cannot bypass Phase 0 gate."""
    if not isinstance(value, NozzleRequest):
        raise TypeError("value requires NozzleRequest")
    raise FireCalculationBlocked(FireSourceStatus.SOURCE_REQUIRED, value.issue_id)
