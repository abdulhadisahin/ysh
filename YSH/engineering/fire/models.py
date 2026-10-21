"""Immutable Fire calculation facts. Numerical success is never a compliance claim."""
from dataclasses import dataclass, field
from typing import ClassVar

from engineering.fire.enums import FireCalculationType, FireRuleId, FireSourceStatus, FoamMixtureBasis, HWApplicability
from engineering.fire.provenance import ParameterProvenance, validate_provenance
from engineering.fire.validation import positive, fraction
from engineering.pipe_design.transfer import PipeInputState
from engineering.system_context import SystemContext


@dataclass(frozen=True, slots=True, kw_only=True)
class FoamSystemInput:
    protected_area_m2: float
    application_density_lpm_m2: float
    application_duration_min: float
    foam_fraction: float
    mixture_basis: FoamMixtureBasis
    provenance: tuple[ParameterProvenance, ...] = ()
    context: SystemContext = field(default_factory=SystemContext)

    def __post_init__(self) -> None:
        for name in ("protected_area_m2", "application_density_lpm_m2", "application_duration_min"):
            positive(getattr(self, name), name)
        fraction(self.foam_fraction, "foam_fraction")
        if not isinstance(self.mixture_basis, FoamMixtureBasis):
            raise TypeError("mixture_basis requires FoamMixtureBasis")
        if not isinstance(self.context, SystemContext):
            raise TypeError("context requires SystemContext")
        validate_provenance(self, self.provenance, {
            "protected_area_m2": "m²", "application_density_lpm_m2": "L/(min·m²)",
            "application_duration_min": "min", "foam_fraction": "1",
        })


@dataclass(frozen=True, slots=True, kw_only=True)
class FoamSystemResult:
    calculation_type: ClassVar[FireCalculationType] = FireCalculationType.FIRE_FOAM_SYSTEM
    formula_version: ClassVar[str] = "FIRE_FOAM_VOLUMETRIC_1"
    rule_ids: ClassVar[tuple[FireRuleId, ...]] = (
        FireRuleId.SOLUTION_FLOW, FireRuleId.CONCENTRATE_FLOW,
        FireRuleId.WATER_FLOW, FireRuleId.CONCENTRATE_VOLUME,
    )
    input: FoamSystemInput
    solution_flow_lpm: float
    foam_concentrate_flow_lpm: float
    water_flow_lpm: float
    foam_concentrate_volume_l: float


@dataclass(frozen=True, slots=True, kw_only=True)
class HazenWilliamsInput:
    flow_lpm: float
    inside_diameter_mm: float
    pipe_length_m: float
    hazen_williams_c: float
    applicability: HWApplicability
    provenance: tuple[ParameterProvenance, ...] = ()
    context: SystemContext = field(default_factory=SystemContext)
    pipe_input: PipeInputState | None = None

    def __post_init__(self) -> None:
        for name in ("flow_lpm", "inside_diameter_mm", "hazen_williams_c"):
            positive(getattr(self, name), name)
        positive(self.pipe_length_m, "pipe_length_m", zero_allowed=True)
        if not isinstance(self.applicability, HWApplicability):
            raise TypeError("applicability requires HWApplicability")
        if not isinstance(self.context, SystemContext):
            raise TypeError("context requires SystemContext")
        if self.pipe_input is not None:
            if not isinstance(self.pipe_input, PipeInputState):
                raise TypeError("pipe_input requires PipeInputState")
            from engineering.fire.units import m3h_to_lpm
            diameter, flow = self.pipe_input.used_values.hydraulic_values()
            if diameter != self.inside_diameter_mm or m3h_to_lpm(flow) != self.flow_lpm:
                raise ValueError("Pipe evidence must match the applied Q and Di")
        validate_provenance(self, self.provenance, {
            "flow_lpm": "L/min", "inside_diameter_mm": "mm",
            "pipe_length_m": "m", "hazen_williams_c": "1",
        })


@dataclass(frozen=True, slots=True, kw_only=True)
class HazenWilliamsResult:
    calculation_type: ClassVar[FireCalculationType] = FireCalculationType.FIRE_HAZEN_WILLIAMS
    formula_version: ClassVar[str] = "FIRE_HW_SKUM_605000_1_85_4_87_1"
    rule_ids: ClassVar[tuple[FireRuleId, ...]] = (FireRuleId.HW_EQUATION,)
    input: HazenWilliamsInput
    pressure_loss_per_m_bar: float
    total_pressure_loss_bar: float


@dataclass(frozen=True, slots=True, kw_only=True)
class NozzleRequest:
    """Optional draft facts only: even a fully populated request cannot execute."""
    calculation_type: ClassVar[FireCalculationType] = FireCalculationType.FIRE_NOZZLE
    status: ClassVar[FireSourceStatus] = FireSourceStatus.SOURCE_REQUIRED
    issue_id: ClassVar[str] = "FIRE-NOZZLE-FORMULA-001"
    rule_id: ClassVar[FireRuleId] = FireRuleId.NOZZLE_RELATION
    device_id: str | None = None
    nozzle_k: ParameterProvenance | None = None
    pressure_bar: float | None = None

    def __post_init__(self) -> None:
        if self.device_id is not None and not isinstance(self.device_id, str):
            raise TypeError("device_id requires text")
        if self.nozzle_k is not None and not isinstance(self.nozzle_k, ParameterProvenance):
            raise TypeError("nozzle_k requires ParameterProvenance")
        if self.pressure_bar is not None:
            positive(self.pressure_bar, "pressure_bar")
