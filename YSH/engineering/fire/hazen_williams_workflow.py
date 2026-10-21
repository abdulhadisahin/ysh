"""Immutable Fire straight-water workflow contracts; no persistence registration."""
from dataclasses import dataclass, field
from enum import StrEnum
import json
from typing import ClassVar
from uuid import UUID

from engineering.fire.enums import FireCalculationType, HWApplicability
from engineering.fire.foam_workflow import SourceReadiness, FoamSourceMessage, FoamRawInput, FoamSummaryValue
from engineering.fire.models import HazenWilliamsResult
from engineering.fire.provenance import ParameterProvenance
from engineering.formula.models import FormulaStep
from engineering.pipe_design.transfer import PipeInputState, PipeInputMode
from engineering.system_context import SystemContext


class HWService(StrEnum):
    WATER = "WATER"
    SEAWATER = "SEAWATER"
    FUEL = "FUEL"
    UNKNOWN = "UNKNOWN"


class HWWorkflowStatus(StrEnum):
    CALCULATED = "CALCULATED"
    CALCULATED_WITH_SOURCE_WARNING = "CALCULATED_WITH_SOURCE_WARNING"


@dataclass(frozen=True, slots=True, kw_only=True)
class HazenWilliamsWorkflowInput:
    flow_lpm: ParameterProvenance | None = None
    inside_diameter_mm: ParameterProvenance | None = None
    pipe_length_m: ParameterProvenance | None = None
    hazen_williams_c: ParameterProvenance | None = None
    service: HWService = HWService.UNKNOWN
    applicability: HWApplicability = HWApplicability.NOT_CONFIGURED
    pipe_input: PipeInputState | None = None
    raw_inputs: tuple[FoamRawInput, ...] = ()
    context: SystemContext = field(default_factory=SystemContext)
    assumptions: tuple[str, ...] = ()
    case_id: UUID | None = None
    revision: int = 1

    def __post_init__(self):
        if not isinstance(self.service, HWService) or not isinstance(self.applicability, HWApplicability):
            raise TypeError("typed service/applicability required")
        if self.pipe_input is not None and not isinstance(self.pipe_input, PipeInputState):
            raise TypeError("pipe_input requires PipeInputState")
        if not isinstance(self.raw_inputs, tuple) or not all(isinstance(v, FoamRawInput) for v in self.raw_inputs):
            raise TypeError("raw_inputs requires immutable numeric observations")
        if not isinstance(self.assumptions, tuple) or not all(isinstance(v, str) for v in self.assumptions):
            raise TypeError("assumptions requires immutable text tuple")
        if not isinstance(self.context, SystemContext):
            raise TypeError("context requires SystemContext")
        if self.case_id is not None and not isinstance(self.case_id, UUID):
            raise TypeError("case_id requires UUID")
        if type(self.revision) is not int or self.revision < 1:
            raise ValueError("revision must be positive")


@dataclass(frozen=True, slots=True, kw_only=True)
class HazenWilliamsWorkflowResult:
    calculation_type: ClassVar[FireCalculationType] = FireCalculationType.FIRE_HAZEN_WILLIAMS
    workflow_version: ClassVar[str] = "fire.hazen_williams.workflow.v1"
    domain_result: HazenWilliamsResult
    formula_steps: tuple[FormulaStep, ...]
    warnings: tuple[FoamSourceMessage, ...]
    status: HWWorkflowStatus
    source_readiness: SourceReadiness
    applicability: HWApplicability
    service: HWService
    input_provenance: tuple[ParameterProvenance, ...]
    pipe_mode: PipeInputMode
    pipe_input: PipeInputState | None
    summary: tuple[FoamSummaryValue, ...]
    primary_result_key: str
    payload_json: str

    @property
    def snapshot_payload(self) -> dict[str, object]:
        return json.loads(self.payload_json)

    def to_json(self) -> str:
        return self.payload_json
