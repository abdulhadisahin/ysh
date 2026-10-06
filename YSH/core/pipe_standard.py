"""Domain model for one authoritative pipe-dimension standard."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class PipeStandard:
    """Identifies one standard that owns nominal designations and geometry."""

    code: str
    display_name: str
    description: str = ""
    source: str = ""
    is_active: bool = True
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=_now)
    modified_at: datetime = field(default_factory=_now)

    def touch(self) -> None:
        """Update the record modification timestamp."""
        self.modified_at = _now()
