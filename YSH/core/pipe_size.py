"""Pipe-size domain model for the local engineering data library."""
from __future__ import annotations
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4

def _now() -> datetime:
    return datetime.now(timezone.utc)

@dataclass(slots=True)
class PipeSize:
    """Represents a nominal pipe size and its measured dimensions."""
    nominal_diameter: str
    outside_diameter_mm: float
    wall_thickness_mm: float
    inside_diameter_mm: float
    standard: str = ""
    description: str = ""
    is_system: bool = False
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=_now)
    modified_at: datetime = field(default_factory=_now)

    def touch(self) -> None:
        """Update the modification timestamp."""
        self.modified_at = _now()

    def to_dict(self) -> dict[str, object]:
        """Serialize this pipe size to primitive values."""
        return {"id": str(self.id), "nominal_diameter": self.nominal_diameter,
                "outside_diameter_mm": self.outside_diameter_mm, "wall_thickness_mm": self.wall_thickness_mm,
                "inside_diameter_mm": self.inside_diameter_mm, "standard": self.standard,
                "description": self.description, "is_system": self.is_system,
                "created_at": self.created_at.isoformat(), "modified_at": self.modified_at.isoformat()}

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "PipeSize":
        """Deserialize a pipe size from :meth:`to_dict` output."""
        return cls(id=UUID(str(data["id"])), nominal_diameter=str(data["nominal_diameter"]),
                   outside_diameter_mm=float(data["outside_diameter_mm"]), wall_thickness_mm=float(data["wall_thickness_mm"]),
                   inside_diameter_mm=float(data["inside_diameter_mm"]), standard=str(data.get("standard", "")),
                   description=str(data.get("description", "")), is_system=bool(data.get("is_system", False)),
                   created_at=datetime.fromisoformat(str(data["created_at"])), modified_at=datetime.fromisoformat(str(data["modified_at"])))
