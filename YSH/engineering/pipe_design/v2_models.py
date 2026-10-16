"""Opt-in V2 pipe selection inputs/results; legacy serializable models are intact."""
from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID, uuid4

from engineering.pipe_design.validation import _positive
from engineering.pipe_design.rules import (
    AllowableStressRule, DesignStatus, ManufacturingToleranceRule, MinimumWallRule, RuleValue,
)
from engineering.provenance import EngineeringValue, SourceReference
from engineering.validation import ValidationError, ValidationIssue


@dataclass(frozen=True, slots=True)
class PipeCandidate:
    """One real library row; stored ID takes precedence over nominal geometry."""

    id: UUID
    standard_id: UUID
    outside_diameter_mm: float
    wall_thickness_mm: float
    inside_diameter_mm: float | None = None
    standard_code: str | None = None
    nominal_diameter: str | None = None
    nps: str | None = None
    schedule: str | None = None
    dimension_source: SourceReference | None = None

    def __post_init__(self) -> None:
        _positive(self.outside_diameter_mm, "field.pipe_outside_diameter")
        _positive(self.wall_thickness_mm, "field.wall_thickness")
        _positive(self.outside_diameter_mm - 2 * self.wall_thickness_mm, "field.pipe_inside_diameter")
        if self.inside_diameter_mm is not None:
            _positive(self.inside_diameter_mm, "field.pipe_inside_diameter")
            if self.inside_diameter_mm > self.outside_diameter_mm:
                raise ValidationError(ValidationIssue("pipe_size_invalid_geometry"))
        if not isinstance(self.id, UUID) or not isinstance(self.standard_id, UUID):
            raise ValidationError(ValidationIssue("selection_required", "field.pipe_standard"))

    @property
    def actual_internal_diameter_mm(self) -> float:
        """Use authoritative stored ID, or derive nominal geometric ID if absent."""
        return self.inside_diameter_mm if self.inside_diameter_mm is not None else self.outside_diameter_mm - 2 * self.wall_thickness_mm


@dataclass(frozen=True, slots=True)
class PipeProvenance:
    """Optional selected-value wrappers; recommended and used values stay distinct."""

    design_velocity: EngineeringValue | None = None
    allowable_stress: EngineeringValue | None = None
    source_factor: EngineeringValue | None = None
    corrosion_allowance: EngineeringValue | None = None
    manufacturing_tolerance: EngineeringValue | None = None
    minimum_wall: EngineeringValue | None = None
    material_standard: SourceReference | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class PipeDesignV2Input:
    """Explicit V2 request; missing temperatures/rules have no invented defaults."""

    flow_rate_m3_h: float
    design_velocity_m_s: float
    standard_id: UUID
    design_pressure_bar: float
    weld_factor: float
    corrosion_allowance_mm: float
    standard_code: str | None = None
    yield_strength_mpa: float | None = None
    safety_factor: float | None = None
    bend_allowance_enabled: bool = False
    bend_radius_mm: float | None = None
    design_temperature_c: float | None = None
    material_id: UUID | None = None
    fluid_id: UUID | None = None
    system_id: UUID | None = None
    circuit_id: UUID | None = None
    stress_rule: AllowableStressRule = field(default_factory=AllowableStressRule)
    tolerance_rule: ManufacturingToleranceRule = field(default_factory=ManufacturingToleranceRule)
    minimum_wall_rule: MinimumWallRule = field(default_factory=MinimumWallRule)
    provenance: PipeProvenance = field(default_factory=PipeProvenance)


@dataclass(frozen=True, slots=True)
class WallBreakdown:
    """Provisional legacy wall remains available when optional rules are missing."""

    base_wall_mm: float
    bend_allowance_mm: float
    corrosion_allowance_mm: float
    manufacturing_allowance_mm: float | None
    calculated_required_wall_mm: float
    minimum_required_wall_mm: float | None
    final_required_wall_mm: float


@dataclass(frozen=True, slots=True, kw_only=True)
class PipeSelection:
    """A selected pipe is not a rule-compliance claim when status is incomplete."""

    status: DesignStatus
    theoretical_internal_diameter_mm: float
    design_velocity_m_s: float
    flow_rate_m3_h: float
    selected_standard_id: UUID
    selected_standard_code: str | None = None
    candidate: PipeCandidate | None = None
    selected_pipe: PipeCandidate | None = None
    actual_velocity_m_s: float | None = None
    wall: WallBreakdown | None = None
    allowable_stress: RuleValue | None = None
    manufacturing_tolerance: RuleValue | None = None
    minimum_wall: RuleValue | None = None
    provenance: PipeProvenance = field(default_factory=PipeProvenance)
    design_temperature_c: float | None = None
    material_id: UUID | None = None
    fluid_id: UUID | None = None
    system_id: UUID | None = None
    circuit_id: UUID | None = None

    selection_id: UUID = field(default_factory=uuid4)
    revision: int = 1

    def __post_init__(self) -> None:
        if not isinstance(self.selection_id, UUID):
            raise TypeError("selection_id must be a UUID")
        if type(self.revision) is not int or self.revision < 1:
            raise ValueError("revision must be a positive integer")

    @property
    def nominal_diameter(self) -> str | None:
        """Return selected DN, if a final standard wall exists."""
        return self.selected_pipe.nominal_diameter if self.selected_pipe else None

    @property
    def nps(self) -> str | None:
        """Return only stored NPS metadata."""
        return self.selected_pipe.nps if self.selected_pipe else None

    @property
    def schedule(self) -> str | None:
        """Return only stored Schedule metadata."""
        return self.selected_pipe.schedule if self.selected_pipe else None

    @property
    def outside_diameter_mm(self) -> float | None:
        """Return final selected outside diameter."""
        return self.selected_pipe.outside_diameter_mm if self.selected_pipe else None

    @property
    def selected_wall_thickness_mm(self) -> float | None:
        """Return a real available wall; never an arbitrary rounded requirement."""
        return self.selected_pipe.wall_thickness_mm if self.selected_pipe else None

    @property
    def actual_internal_diameter_mm(self) -> float | None:
        """Return final actual ID, distinct from theoretical D."""
        return self.selected_pipe.actual_internal_diameter_mm if self.selected_pipe else None

    @property
    def calculated_required_wall_mm(self) -> float | None:
        """Return calculated pressure/allowance wall, possibly provisional."""
        return self.wall.calculated_required_wall_mm if self.wall else None

    @property
    def minimum_required_wall_mm(self) -> float | None:
        """Missing rule content remains None."""
        return self.wall.minimum_required_wall_mm if self.wall else None

    @property
    def final_required_wall_mm(self) -> float | None:
        """Return calculated/minimum maximum where available."""
        return self.wall.final_required_wall_mm if self.wall else None

    @property
    def velocity_within_design(self) -> bool | None:
        """Expose actual-velocity checking without changing existing warnings."""
        return None if self.actual_velocity_m_s is None else self.actual_velocity_m_s <= self.design_velocity_m_s
