"""Small immutable records for V2 tables; no database or UI dependencies."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from uuid import UUID, uuid4

from engineering.provenance import SourceReference, VerificationStatus


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True, kw_only=True)
class SourceRecord:
    reference: SourceReference
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=_now)
    modified_at: datetime = field(default_factory=_now)


@dataclass(frozen=True, slots=True, kw_only=True)
class RuleSet:
    code: str
    name: str
    organization: str | None = None
    revision: str | None = None
    effective_date: date | None = None
    verification_status: VerificationStatus | None = None
    source_id: UUID | None = None
    is_active: bool = True
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=_now)
    modified_at: datetime = field(default_factory=_now)


@dataclass(frozen=True, slots=True, kw_only=True)
class System:
    code: str
    name_tr: str
    name_en: str | None = None
    is_factory: bool = False
    is_active: bool = True
    id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True, slots=True, kw_only=True)
class Circuit:
    system_id: UUID
    code: str
    name_tr: str
    name_en: str | None = None
    is_factory: bool = False
    is_active: bool = True
    id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True, slots=True, kw_only=True)
class Fluid:
    code: str
    name_tr: str
    name_en: str | None = None
    is_factory: bool = False
    is_active: bool = True
    id: UUID = field(default_factory=uuid4)


@dataclass(frozen=True, slots=True, kw_only=True)
class FluidProperty:
    fluid_id: UUID
    property_name: str
    value: float
    unit: str
    reference_temperature_c: float | None = None
    source_id: UUID | None = None
    verification_status: VerificationStatus | None = None
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=_now)
    modified_at: datetime = field(default_factory=_now)


@dataclass(frozen=True, slots=True, kw_only=True)
class MaterialProperty:
    material_id: UUID
    property_name: str
    value: float
    unit: str
    reference_temperature_c: float | None = None
    source_id: UUID | None = None
    rule_set_id: UUID | None = None
    verification_status: VerificationStatus | None = None
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=_now)
    modified_at: datetime = field(default_factory=_now)


@dataclass(frozen=True, slots=True, kw_only=True)
class PipeStandardMetadata:
    standard_id: UUID
    standard_family: str | None = None
    source_id: UUID | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class PipeSizeMetadata:
    pipe_size_id: UUID
    nps: str | None = None
    schedule: str | None = None
    manufacturing_tolerance: float | None = None
    tolerance_unit: str | None = None
    source_id: UUID | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class EngineeringConstantMetadata:
    constant_id: UUID
    source_id: UUID | None = None
    rule_set_id: UUID | None = None
    system_id: UUID | None = None
    circuit_id: UUID | None = None
    selection_reason: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class CorrosionSourceLink:
    corrosion_circuit_id: UUID
    source_id: UUID | None = None
    rule_set_id: UUID | None = None
    circuit_id: UUID | None = None
