"""Material domain model for the local engineering data library."""
from __future__ import annotations
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4

def _now() -> datetime:
    return datetime.now(timezone.utc)

@dataclass(slots=True)
class Material:
    """Represents a traceable engineering material record."""
    name: str
    designation: str
    standard: str = ""
    yield_strength_mpa: float | None = None
    roughness_mm: float = 0.0
    description: str = ""
    source: str = "User"
    is_system: bool = False
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=_now)
    modified_at: datetime = field(default_factory=_now)

    def touch(self) -> None:
        """Update the modification timestamp."""
        self.modified_at = _now()

    def to_dict(self) -> dict[str, object]:
        """Serialize this material to portable primitive values."""
        return {"id": str(self.id), "name": self.name, "designation": self.designation,
                "standard": self.standard, "yield_strength_mpa": self.yield_strength_mpa,
                "roughness_mm": self.roughness_mm, "description": self.description,
                "source": self.source, "is_system": self.is_system,
                "created_at": self.created_at.isoformat(), "modified_at": self.modified_at.isoformat()}

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "Material":
        """Deserialize a material from :meth:`to_dict` output."""
        value = data.get("yield_strength_mpa")
        return cls(id=UUID(str(data["id"])), name=str(data["name"]), designation=str(data["designation"]),
                   standard=str(data.get("standard", "")), yield_strength_mpa=None if value is None else float(value),
                   roughness_mm=float(data.get("roughness_mm", 0)), description=str(data.get("description", "")),
                   source=str(data.get("source", "User")), is_system=bool(data.get("is_system", False)),
                   created_at=datetime.fromisoformat(str(data["created_at"])), modified_at=datetime.fromisoformat(str(data["modified_at"])))
