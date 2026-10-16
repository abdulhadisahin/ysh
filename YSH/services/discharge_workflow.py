"""Explicit discharge input decisions independent of Tkinter and repositories."""
from __future__ import annotations

from uuid import UUID

from engineering.pipe_design.transfer import (
    PipeInputMode, PipeInputState, PipeTransferProjectState, PipeValues,
)
from engineering.pipe_design.v2_models import PipeSelection
from services.pipe_source_discovery import PipeSourceDiscovery, applicable


class DischargeWorkflow:
    """Own project transfer state without calculating or observing live UI data."""

    def __init__(
        self, state: PipeTransferProjectState | None = None, *, module: str = "discharge",
        discovery: PipeSourceDiscovery | None = None,
    ) -> None:
        """Share discovery when attached to a workspace; standalone callers stay compatible."""
        if module not in ("discharge", "suction"):
            raise ValueError("Unknown downstream module")
        self.module = module
        self.discovery = discovery or PipeSourceDiscovery(state)

    @property
    def state(self) -> PipeTransferProjectState:
        """Expose the single existing project transfer state."""
        return self.discovery.state

    @state.setter
    def state(self, state: PipeTransferProjectState) -> None:
        self.discovery.state = state

    def available_sources(self) -> tuple[PipeSelection, ...]:
        """Discover usable current-project sources without applying any values."""
        return self.discovery.available()

    def _set_input(self, state: PipeInputState) -> None:
        self.discovery.set_input(self.module, state)

    @property
    def pipe_input(self) -> PipeInputState:
        """Return the sole authority for linked Q/Di."""
        return getattr(self.state, self.module)

    @property
    def pipe_fields_readonly(self) -> bool:
        """Expose page field ownership as a testable state contract."""
        return self.pipe_input.mode is PipeInputMode.LINKED

    def source(self, identifier: UUID) -> PipeSelection | None:
        """Find the exact chosen identity; never infer the latest source."""
        return next((s for s in self.state.selections if s.selection_id == identifier), None)

    def publish(self, selection: PipeSelection) -> None:
        """Observe a published revision without changing any applied values."""
        self.discovery.publish(selection)

    def remove(self, identifier: UUID) -> None:
        """Retain historical inputs when a source disappears."""
        self.discovery.remove(identifier)

    def link(self, identifier: UUID) -> None:
        """Require a specific applicable source before replacing Q/Di."""
        selection = self.source(identifier)
        if selection is None or not applicable(selection):
            raise ValueError("An explicit available source is required")
        self._set_input(self.pipe_input.link_to(selection))

    def update(self) -> None:
        """Apply the current revision of the same source, without calculating."""
        snapshot = self.pipe_input.snapshot
        selection = self.source(snapshot.source_selection_id) if snapshot else None
        if selection is None or not applicable(selection):
            raise ValueError("Linked source is missing or unavailable")
        self._set_input(self.pipe_input.update(selection))

    def keep_current(self) -> None:
        """Record the observed revision while retaining the applied snapshot."""
        snapshot = self.pipe_input.snapshot
        selection = self.source(snapshot.source_selection_id) if snapshot else None
        self._set_input(self.pipe_input.keep_current(selection))

    def manual(self, values: PipeValues | None = None) -> None:
        """Detach explicitly, retaining current numerical inputs if requested."""
        self._set_input(self.pipe_input.to_manual(values))

    def edit_manual(self, *, diameter_mm: float, flow_m3_h: float) -> None:
        """Editing while linked is rejected even outside the UI."""
        if self.pipe_fields_readonly:
            raise ValueError("Switch to MANUAL before editing Q/Di")
        self.manual(PipeValues(actual_internal_diameter_mm=diameter_mm,
                               flow_rate_m3_h=flow_m3_h))
