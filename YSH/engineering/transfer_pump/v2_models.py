"""Distinct transfer-pump design and empirical contracts with Phase 2 provenance."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
import math
from uuid import UUID

from engineering.provenance import EngineeringValue, SourceReference, SourceType
from engineering.transfer_pump.capacity_basis import CAPACITY_MODE_VOLUME, FuelCapacityResolution
from engineering.transfer_pump.models import TransferPumpResult
from engineering.validation import ValidationError, ValidationIssue


class TransferPumpMode(StrEnum):
    """Stable persisted calculation methods, independent of localized labels."""
    DESIGN = "DESIGN"
    EMPIRICAL = "EMPIRICAL"


class CapacityStatus(StrEnum):
    """Capacity suitability only; these outcomes are not classification approval."""
    NO_SELECTED_PUMP = "NO_SELECTED_PUMP"
    ADEQUATE = "ADEQUATE"
    PUMP_CAPACITY_BELOW_REQUIRED = "PUMP_CAPACITY_BELOW_REQUIRED"


def positive(value: float, field_key: str) -> None:
    """Reject invalid inputs without clamping or engineering maximum assumptions."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValidationError(ValidationIssue("valid_number", field_key))
    if value <= 0:
        raise ValidationError(ValidationIssue("greater_than_zero", field_key))


def user_source() -> SourceReference:
    """No document, project criterion or verification is inferred from manual entry."""
    return SourceReference(source_type=SourceType.USER_INPUT)


@dataclass(frozen=True, slots=True, kw_only=True)
class PumpIntegrationContext:
    """Preparation only: external values/references are retained, never calculated here."""
    system_id: UUID | None = None
    circuit_id: UUID | None = None
    fluid_id: UUID | None = None
    selected_pump_reference_id: UUID | None = None
    required_head_m: float | None = None
    available_npsh_m: float | None = None
    required_npsh_m: float | None = None
    npsh_margin_m: float | None = None

    def __post_init__(self) -> None:
        for name in ('system_id', 'circuit_id', 'fluid_id', 'selected_pump_reference_id'):
            value = getattr(self, name)
            if value is not None and not isinstance(value, UUID):
                raise TypeError(f"{name} must be a UUID or None")
        for name in ('required_head_m', 'available_npsh_m', 'required_npsh_m', 'npsh_margin_m'):
            value = getattr(self, name)
            if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)):
                raise ValueError(f"{name} must be finite or None")


@dataclass(frozen=True, slots=True, kw_only=True)
class TransferPumpDesignInput:
    """Required capacity comes only from explicit transferable volume and target time."""
    transfer_volume_m3: float
    target_transfer_time_h: float
    selected_pump_capacity_m3_h: float | None = None
    volume_source: SourceReference = field(default_factory=user_source)
    target_time_source: SourceReference = field(default_factory=user_source)
    context: PumpIntegrationContext = field(default_factory=PumpIntegrationContext)
    mode: TransferPumpMode = field(default=TransferPumpMode.DESIGN, init=False)

    def __post_init__(self) -> None:
        positive(self.transfer_volume_m3, 'transfer.design.volume')
        positive(self.target_transfer_time_h, 'transfer.design.target_time')
        if self.selected_pump_capacity_m3_h is not None:
            positive(self.selected_pump_capacity_m3_h, 'transfer.design.pump_capacity')
        for source, allowed in (
            (self.volume_source, (SourceType.USER_INPUT, SourceType.PROJECT_CRITERION)),
            (self.target_time_source, (SourceType.USER_INPUT, SourceType.PROJECT_CRITERION, SourceType.D243_CRITERION)),
        ):
            if not isinstance(source, SourceReference) or source.source_type not in allowed:
                raise ValueError('Design source must be explicit user/project/configured criterion')
        if not isinstance(self.context, PumpIntegrationContext):
            raise TypeError('context must be PumpIntegrationContext')


@dataclass(frozen=True, slots=True, kw_only=True)
class TransferPumpDesignResult:
    """Full-precision design output; no margin or future hydraulic values are invented."""
    input: TransferPumpDesignInput
    required_capacity: EngineeringValue
    transfer_time_h: float | None
    status: CapacityStatus
    mode: TransferPumpMode = field(default=TransferPumpMode.DESIGN, init=False)
    margin_percent: float | None = None
    margin_adjusted_flow_m3_h: float | None = None

    @property
    def required_flow_m3_h(self) -> float:
        """Expose a future explicit PipeSelection-compatible design flow."""
        return self.required_capacity.used_value


@dataclass(frozen=True, slots=True, kw_only=True)
class TransferPumpEmpiricalInput:
    """A vessel-capacity estimate request never doubles as required design flow."""
    source_capacity: float
    capacity_input_mode: str = CAPACITY_MODE_VOLUME
    context: PumpIntegrationContext = field(default_factory=PumpIntegrationContext)
    mode: TransferPumpMode = field(default=TransferPumpMode.EMPIRICAL, init=False)


@dataclass(frozen=True, slots=True, kw_only=True)
class ReferenceVesselSample:
    """Immutable data actually used in the fit, with honest reference-vessel origin."""
    reference_id: UUID
    ship_name: str
    fuel_capacity_m3: float
    pump_capacity_m3_h: float
    description: str
    source: SourceReference


@dataclass(frozen=True, slots=True, kw_only=True)
class TransferPumpEmpiricalResult:
    """Legacy fit plus its reference provenance; required design flow stays absent."""
    input: TransferPumpEmpiricalInput
    resolution: FuelCapacityResolution
    estimate: TransferPumpResult
    references: tuple[ReferenceVesselSample, ...]
    calculated_capacity: EngineeringValue | None
    mode: TransferPumpMode = field(default=TransferPumpMode.EMPIRICAL, init=False)
    required_flow_m3_h: None = field(default=None, init=False)
