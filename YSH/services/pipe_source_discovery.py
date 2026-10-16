"""Lightweight current-project source discovery; no polling, SQL or recalculation."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
import math
from uuid import UUID

from engineering.pipe_design.transfer import PipeInputState, PipeTransferProjectState
from engineering.pipe_design.v2_models import PipeSelection


def applicable(selection: PipeSelection) -> bool:
    """Check hydraulic transfer applicability without changing engineering/rule status."""
    numbers = (selection.flow_rate_m3_h, selection.actual_internal_diameter_mm)
    return selection.selected_pipe is not None and all(
        not isinstance(n, bool) and isinstance(n, (int, float))
        and math.isfinite(n) and n > 0 for n in numbers
    )


class PipeSourceDiscovery:
    """One authoritative Phase 7 project state shared by independent downstream owners."""

    def __init__(self, state: PipeTransferProjectState | None = None) -> None:
        """Keep selections in the existing project namespace, never in a duplicate registry."""
        self.state = (state or PipeTransferProjectState()).refresh()
        self._listeners: list[Callable[[], None]] = []

    def available(self) -> tuple[PipeSelection, ...]:
        """Pure discovery: reads cannot calculate, link or increase a revision."""
        return tuple(s for s in self.state.selections if applicable(s))

    def subscribe(self, listener: Callable[[], None]) -> None:
        """Register a lightweight page status renderer; no timers or global scans."""
        self._listeners.append(listener)

    def load(self, state: PipeTransferProjectState) -> None:
        """Replace a project atomically, refreshing observations but preserving snapshots."""
        self.state = state.refresh()
        self._notify()

    def publish(self, selection: PipeSelection) -> None:
        """Observe an explicitly calculated upstream result without applying it downstream."""
        self.state = self.state.with_selection(selection)
        self._notify()

    def remove(self, selection_id: UUID) -> None:
        """Preserve applied historical values when a source is removed."""
        self.state = self.state.without_selection(selection_id)
        self._notify()

    def set_input(self, module: str, state: PipeInputState) -> None:
        """Change only the selected downstream owner's explicit applied/manual input."""
        if module not in ("discharge", "suction"):
            raise ValueError("Unknown downstream module")
        self.state = replace(self.state, **{module: state})

    def _notify(self) -> None:
        for listener in tuple(self._listeners):
            listener()
