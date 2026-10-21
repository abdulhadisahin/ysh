"""Frozen application contracts; no global snapshot or project registration."""
from dataclasses import dataclass, field
from enum import StrEnum
import json
from typing import ClassVar
from uuid import UUID

from engineering.fire.enums import FireCalculationType, FireSourceStatus, FoamMixtureBasis
from engineering.fire.models import FoamSystemResult
from engineering.fire.provenance import ParameterProvenance
from engineering.fire.validation import finite
from engineering.formula.models import FormulaStep
from engineering.system_context import SystemContext


class FoamWorkflowStatus(StrEnum):
    CALCULATED = "CALCULATED"
    CALCULATED_WITH_SOURCE_WARNING = "CALCULATED_WITH_SOURCE_WARNING"


class SourceReadiness(StrEnum):
    READY = "READY"
    CONTEXT_REQUIRED = "CONTEXT_REQUIRED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


class SourceMessageCategory(StrEnum):
    INFO = "INFO"
    WARNING = "WARNING"
    SOURCE_REQUIRED = "SOURCE_REQUIRED"
    SOURCE_CONTEXT_REQUIRED = "SOURCE_CONTEXT_REQUIRED"


@dataclass(frozen=True, slots=True, kw_only=True)
class FoamSourceMessage:
    field_name: str
    source_status: FireSourceStatus
    category: SourceMessageCategory
    message_key: str


@dataclass(frozen=True, slots=True, kw_only=True)
class FoamRawInput:
    """Optional original numeric observation; strings/locale parsing belong to future UI."""
    field_name: str
    value: float
    unit: str

    def __post_init__(self) -> None:
        if not isinstance(self.field_name, str) or not isinstance(self.unit, str):
            raise TypeError("raw input names/units require text")
        finite(self.value, self.field_name)


@dataclass(frozen=True, slots=True, kw_only=True)
class FoamWorkflowInput:
    """Drafts may omit fields; service rejects missing values without fallbacks."""
    protected_area_m2: ParameterProvenance | None = None
    application_density_lpm_m2: ParameterProvenance | None = None
    application_duration_min: ParameterProvenance | None = None
    foam_fraction: ParameterProvenance | None = None
    mixture_basis: FoamMixtureBasis | None = None
    raw_inputs: tuple[FoamRawInput, ...] = ()
    context: SystemContext = field(default_factory=SystemContext)
    assumptions: tuple[str, ...] = ()
    case_id: UUID | None = None
    revision: int = 1

    def __post_init__(self) -> None:
        if not isinstance(self.raw_inputs, tuple) or not all(isinstance(v, FoamRawInput) for v in self.raw_inputs):
            raise TypeError("raw_inputs requires an immutable tuple of FoamRawInput")
        if not isinstance(self.assumptions, tuple) or not all(isinstance(v, str) for v in self.assumptions):
            raise TypeError("assumptions requires an immutable tuple of text")
        if not isinstance(self.context, SystemContext):
            raise TypeError("context requires SystemContext")
        if self.case_id is not None and not isinstance(self.case_id, UUID):
            raise TypeError("case_id requires UUID")
        if type(self.revision) is not int or self.revision < 1:
            raise ValueError("revision must be a positive integer")


@dataclass(frozen=True, slots=True, kw_only=True)
class FoamSummaryValue:
    key: str
    label_key: str
    symbol: str
    value: float
    unit: str


@dataclass(frozen=True, slots=True, kw_only=True)
class FoamWorkflowResult:
    calculation_type: ClassVar[FireCalculationType] = FireCalculationType.FIRE_FOAM_SYSTEM
    workflow_version: ClassVar[str] = "fire.foam.workflow.v1"
    domain_result: FoamSystemResult
    formula_steps: tuple[FormulaStep, ...]
    warnings: tuple[FoamSourceMessage, ...]
    status: FoamWorkflowStatus
    source_readiness: SourceReadiness
    input_provenance: tuple[ParameterProvenance, ...]
    summary: tuple[FoamSummaryValue, ...]
    primary_result_key: str
    payload_json: str

    @property
    def snapshot_payload(self) -> dict[str, object]:
        """Detached primitive copy, never a live mutable payload inside the result."""
        return json.loads(self.payload_json)

    def to_json(self) -> str:
        return self.payload_json
