"""Project domain model for YSH."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from collections.abc import Mapping
from uuid import UUID, uuid4


def _current_timestamp() -> datetime:
    """Return the current UTC timestamp for project lifecycle fields."""
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class Project:
    """Represents an engineering project and its lifecycle metadata."""

    name: str
    description: str = ""
    notes: str = ""
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=_current_timestamp)
    modified_at: datetime = field(default_factory=_current_timestamp)

    def touch(self) -> None:
        """Update the project's modification timestamp to the current UTC time."""
        self.modified_at = _current_timestamp()

    def to_dict(self) -> dict[str, str]:
        """Serialize the project into a dictionary of portable primitive values."""
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "notes": self.notes,
            "created_at": self.created_at.isoformat(),
            "modified_at": self.modified_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> Project:
        """Create a project from a dictionary produced by :meth:`to_dict`."""
        return cls(
            id=UUID(cls._required_value(data, "id")),
            name=cls._required_value(data, "name"),
            description=cls._required_value(data, "description"),
            notes=cls._required_value(data, "notes"),
            created_at=datetime.fromisoformat(
                cls._required_value(data, "created_at")
            ),
            modified_at=datetime.fromisoformat(
                cls._required_value(data, "modified_at")
            ),
        )

    @property
    def display_name(self) -> str:
        """Return the name used to identify the project in user-facing contexts."""
        return self.name

    @staticmethod
    def _required_value(data: Mapping[str, object], key: str) -> str:
        value = data.get(key)
        if not isinstance(value, str):
            raise ValueError(f"Project field '{key}' must be a string.")
        return value
