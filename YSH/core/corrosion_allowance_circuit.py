"""Editable circuit-specific corrosion-allowance library record."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class CorrosionAllowanceCircuit:
    """Defines a D243 default corrosion allowance for one circuit/system."""

    code: str
    display_name: str
    default_corrosion_allowance_mm: float
    description: str = ""
    is_active: bool = True
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=_now)
    modified_at: datetime = field(default_factory=_now)

    def touch(self) -> None:
        self.modified_at = _now()
