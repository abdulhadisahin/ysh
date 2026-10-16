"""Explicit pipe transfer: immutable applied values, never a live upstream pointer."""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from enum import StrEnum
from uuid import UUID

from engineering.pipe_design.v2_models import PipeSelection
from engineering.pipe_design.rules import DesignStatus
from engineering.provenance import SourceReference


class PipeInputMode(StrEnum):
    """Stable storage values; translations belong to future page integration."""
    MANUAL = "MANUAL"
    LINKED = "LINKED"


class PipeLinkStatus(StrEnum):
    """Source observation does not change applied engineering values."""
    MANUAL = "MANUAL"
    LINKED_SYNCED = "LINKED_SYNCED"
    LINKED_STALE = "LINKED_STALE"
    LINKED_SOURCE_MISSING = "LINKED_SOURCE_MISSING"
    LINKED_SOURCE_DIFFERENT = "LINKED_SOURCE_DIFFERENT"
    LINKED_SOURCE_UNAVAILABLE = "LINKED_SOURCE_UNAVAILABLE"


@dataclass(frozen=True, slots=True, kw_only=True)
class PipeValues:
    """Small transfer contract; Di is actual selected ID, never theoretical D."""
    flow_rate_m3_h: float | None = None
    actual_internal_diameter_mm: float | None = None
    pipe_id: UUID | None = None
    standard_id: UUID | None = None
    standard_code: str | None = None
    nominal_diameter: str | None = None
    nps: str | None = None
    schedule: str | None = None
    outside_diameter_mm: float | None = None
    wall_thickness_mm: float | None = None
    material_id: UUID | None = None
    fluid_id: UUID | None = None
    system_id: UUID | None = None
    circuit_id: UUID | None = None
    dimension_source: SourceReference | None = None
    material_source: SourceReference | None = None

    @classmethod
    def from_selection(cls, source: PipeSelection) -> PipeValues:
        """Copy relevant immutable values; incomplete selection cannot be applied."""
        pipe = source.selected_pipe
        if pipe is None:
            raise ValueError("A selected pipe with actual Di is required")
        return cls(
            flow_rate_m3_h=source.flow_rate_m3_h,
            actual_internal_diameter_mm=source.actual_internal_diameter_mm,
            pipe_id=pipe.id, standard_id=source.selected_standard_id,
            standard_code=source.selected_standard_code,
            nominal_diameter=source.nominal_diameter, nps=source.nps,
            schedule=source.schedule, outside_diameter_mm=source.outside_diameter_mm,
            wall_thickness_mm=source.selected_wall_thickness_mm,
            material_id=source.material_id, fluid_id=source.fluid_id,
            system_id=source.system_id, circuit_id=source.circuit_id,
            dimension_source=pipe.dimension_source,
            material_source=source.provenance.material_standard,
        )

    def hydraulic_values(self) -> tuple[float, float]:
        """Return actual Di and Q; hydraulic services retain numeric validation."""
        if self.actual_internal_diameter_mm is None or self.flow_rate_m3_h is None:
            raise ValueError("Manual Di and Q are required")
        return self.actual_internal_diameter_mm, self.flow_rate_m3_h


def engineering_signature(source: PipeSelection) -> tuple[object, ...]:
    """Revision fields: Q, real selected geometry/row, standard, labels and context.

    Provenance notes, rule status, theoretical D, wall calculations and display
    metadata are deliberately excluded. Read operations never advance revisions.
    """
    pipe = source.selected_pipe
    return (source.flow_rate_m3_h, pipe.id if pipe else None,
            source.actual_internal_diameter_mm, source.outside_diameter_mm,
            source.selected_wall_thickness_mm, source.selected_standard_id,
            source.selected_standard_code, source.nominal_diameter, source.nps,
            source.schedule, source.material_id, source.fluid_id,
            source.system_id, source.circuit_id)


def revise_selection(previous: PipeSelection, result: PipeSelection) -> PipeSelection:
    """Explicitly publish a recalculated result in the same stable lineage."""
    changed = engineering_signature(previous) != engineering_signature(result)
    return replace(result, selection_id=previous.selection_id,
                   revision=previous.revision + int(changed))


@dataclass(frozen=True, slots=True, kw_only=True)
class PipeSelectionSnapshot:
    """Exact applied values and source revision; status is not a compliance claim."""
    source_selection_id: UUID
    source_revision: int
    values: PipeValues
    upstream_status: DesignStatus
    applied_at: datetime | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.source_selection_id, UUID):
            raise TypeError("source_selection_id must be a UUID")
        if type(self.source_revision) is not int or self.source_revision < 1:
            raise ValueError("source_revision must be positive")
        if not isinstance(self.upstream_status, DesignStatus):
            raise TypeError("upstream_status must be DesignStatus")
        if not isinstance(self.values, PipeValues):
            raise TypeError("values must be immutable PipeValues")
        self.values.hydraulic_values()
        if self.applied_at is not None and self.applied_at.utcoffset() is None:
            raise ValueError("applied_at must include a timezone")

    @classmethod
    def apply(cls, source: PipeSelection, applied_at: datetime | None = None) -> PipeSelectionSnapshot:
        """Capture only on explicit user action, never while loading/observing."""
        return cls(source_selection_id=source.selection_id,
                   source_revision=source.revision, values=PipeValues.from_selection(source),
                   upstream_status=source.status,
                   applied_at=applied_at if applied_at is not None else datetime.now(timezone.utc))


def link_status(snapshot: PipeSelectionSnapshot, current: PipeSelection | None) -> PipeLinkStatus:
    """Pure source comparison; different identities are never interchangeable."""
    if current is None:
        return PipeLinkStatus.LINKED_SOURCE_MISSING
    if current.selection_id != snapshot.source_selection_id:
        return PipeLinkStatus.LINKED_SOURCE_DIFFERENT
    if current.selected_pipe is None:
        return PipeLinkStatus.LINKED_SOURCE_UNAVAILABLE
    return (PipeLinkStatus.LINKED_SYNCED if current.revision == snapshot.source_revision
            else PipeLinkStatus.LINKED_STALE)


def is_stale(snapshot: PipeSelectionSnapshot, current: PipeSelection | None) -> bool:
    """Missing/different/unavailable sources also require an explicit decision."""
    return link_status(snapshot, current) is not PipeLinkStatus.LINKED_SYNCED


@dataclass(frozen=True, slots=True, kw_only=True)
class PipeInputState:
    """Downstream ownership; calculations consume used_values exclusively."""
    mode: PipeInputMode = PipeInputMode.MANUAL
    manual_values: PipeValues = field(default_factory=PipeValues)
    snapshot: PipeSelectionSnapshot | None = None
    status: PipeLinkStatus = PipeLinkStatus.MANUAL
    observed_source_id: UUID | None = None
    observed_revision: int | None = None
    kept_current: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.mode, PipeInputMode) or not isinstance(self.status, PipeLinkStatus):
            raise TypeError("Typed mode and status are required")
        if not isinstance(self.manual_values, PipeValues):
            raise TypeError("manual_values must be PipeValues")
        if self.mode is PipeInputMode.MANUAL:
            if (self.snapshot is not None or self.status is not PipeLinkStatus.MANUAL
                    or self.observed_source_id is not None or self.observed_revision is not None
                    or self.kept_current):
                raise ValueError("Manual inputs cannot retain a driving link")
        elif not isinstance(self.snapshot, PipeSelectionSnapshot) or self.status is PipeLinkStatus.MANUAL:
            raise ValueError("Linked mode requires an explicit applied snapshot")

    @property
    def used_values(self) -> PipeValues:
        """No live upstream reads are possible here."""
        return self.snapshot.values if self.snapshot is not None else self.manual_values

    def link_to(self, source: PipeSelection, *, applied_at: datetime | None = None) -> PipeInputState:
        """Explicit Manual→Linked or explicit source replacement."""
        return PipeInputState(mode=PipeInputMode.LINKED,
            snapshot=PipeSelectionSnapshot.apply(source, applied_at),
            status=PipeLinkStatus.LINKED_SYNCED,
            observed_source_id=source.selection_id, observed_revision=source.revision)

    def observe(self, current: PipeSelection | None) -> PipeInputState:
        """Change status only; no inputs, timestamps or calculations are replaced."""
        if self.snapshot is None:
            return self
        status = link_status(self.snapshot, current)
        same_observation = (self.observed_source_id == (current.selection_id if current else None)
                            and self.observed_revision == (current.revision if current else None))
        return replace(self, status=status,
            observed_source_id=current.selection_id if current else None,
            observed_revision=current.revision if current else None,
            kept_current=self.kept_current and same_observation and status is not PipeLinkStatus.LINKED_SYNCED)

    def update(self, current: PipeSelection, *, applied_at: datetime | None = None) -> PipeInputState:
        """Update the same source only; different sources require explicit link_to."""
        if self.snapshot is None or current.selection_id != self.snapshot.source_selection_id:
            raise ValueError("Update requires the same linked source; use link_to explicitly")
        return self.link_to(current, applied_at=applied_at)

    def keep_current(self, current: PipeSelection | None) -> PipeInputState:
        """Retain applied values and record the observed difference without syncing."""
        state = self.observe(current)
        return replace(state, kept_current=True) if state.status not in (
            PipeLinkStatus.MANUAL, PipeLinkStatus.LINKED_SYNCED) else state

    def to_manual(self, values: PipeValues | None = None) -> PipeInputState:
        """Detach completely, optionally keeping applied values as manual starting data."""
        return PipeInputState(manual_values=values if values is not None else self.used_values)

    def trace(self) -> dict[str, object]:
        """Explicit link provenance without labelling transferred data USER_INPUT."""
        snap = self.snapshot
        return dict(mode=self.mode.value, status=self.status.value,
            source_selection_id=str(snap.source_selection_id) if snap else None,
            source_revision=snap.source_revision if snap else None,
            applied_at=snap.applied_at.isoformat() if snap and snap.applied_at else None,
            upstream_status=snap.upstream_status.value if snap else None,
            observed_source_id=str(self.observed_source_id) if self.observed_source_id else None,
            observed_revision=self.observed_revision, kept_current=self.kept_current)


@dataclass(frozen=True, slots=True, kw_only=True)
class PipeTransferProjectState:
    """Project-owned selections and independent discharge/suction applied inputs."""
    selections: tuple[PipeSelection, ...] = ()
    discharge: PipeInputState = field(default_factory=PipeInputState)
    suction: PipeInputState = field(default_factory=PipeInputState)

    def __post_init__(self) -> None:
        if not isinstance(self.selections, tuple):
            raise TypeError("selections must be an immutable tuple")
        if len({s.selection_id for s in self.selections}) != len(self.selections):
            raise ValueError("Duplicate selection identity")

    def refresh(self) -> PipeTransferProjectState:
        """Resolve by exact identity; change observations only, never run hydraulics."""
        sources = {s.selection_id: s for s in self.selections}
        def observed(state: PipeInputState) -> PipeInputState:
            return state.observe(sources.get(state.snapshot.source_selection_id)) if state.snapshot else state
        return replace(self, discharge=observed(self.discharge), suction=observed(self.suction))

    def with_selection(self, selection: PipeSelection) -> PipeTransferProjectState:
        """Publish an explicit revision without applying it to downstream values."""
        previous = next((s for s in self.selections if s.selection_id == selection.selection_id), None)
        if previous:
            expected = previous.revision + int(engineering_signature(previous) != engineering_signature(selection))
            if selection.revision != expected:
                raise ValueError("Use revise_selection to advance engineering revisions")
        selections = tuple(s for s in self.selections if s.selection_id != selection.selection_id) + (selection,)
        return replace(self, selections=selections).refresh()

    def without_selection(self, selection_id: UUID) -> PipeTransferProjectState:
        """Remove a source while retaining all historical applied snapshots."""
        return replace(self, selections=tuple(s for s in self.selections if s.selection_id != selection_id)).refresh()
