"""Engineering-constant domain model for the local data library."""
from __future__ import annotations
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4

def _now() -> datetime:
    return datetime.now(timezone.utc)

@dataclass(slots=True)
class EngineeringConstant:
    """Represents an editable, traceable engineering configuration value."""
    key: str
    display_name: str
    value: float
    unit: str = ""
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
        """Serialize this constant to primitive values."""
        return {"id": str(self.id), "key": self.key, "display_name": self.display_name,
                "value": self.value, "unit": self.unit, "description": self.description,
                "source": self.source, "is_system": self.is_system,
                "created_at": self.created_at.isoformat(), "modified_at": self.modified_at.isoformat()}

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "EngineeringConstant":
        """Deserialize a constant from :meth:`to_dict` output."""
        return cls(id=UUID(str(data["id"])), key=str(data["key"]), display_name=str(data["display_name"]),
                   value=float(data["value"]), unit=str(data.get("unit", "")),
                   description=str(data.get("description", "")), source=str(data.get("source", "User")),
                   is_system=bool(data.get("is_system", False)), created_at=datetime.fromisoformat(str(data["created_at"])),
                   modified_at=datetime.fromisoformat(str(data["modified_at"])))
