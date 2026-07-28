"""Reusable calculation domain model for YSH."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from collections.abc import Mapping
from uuid import UUID, uuid4


def _current_timestamp() -> datetime:
    """Return the current timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class Calculation:
    """Represents calculation metadata without implementing engineering formulas."""

    project_id: UUID
    calculation_type: str
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=_current_timestamp)
    inputs: dict[str, object] = field(default_factory=dict)
    outputs: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        """Serialize calculation metadata and input/output collections."""
        return {
            "id": str(self.id),
            "project_id": str(self.project_id),
            "calculation_type": self.calculation_type,
            "created_at": self.created_at.isoformat(),
            "inputs": dict(self.inputs),
            "outputs": dict(self.outputs),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> Calculation:
        """Create a calculation from a dictionary produced by :meth:`to_dict`."""
        return cls(
            id=UUID(cls._required_string(data, "id")),
            project_id=UUID(cls._required_string(data, "project_id")),
            calculation_type=cls._required_string(data, "calculation_type"),
            created_at=datetime.fromisoformat(
                cls._required_string(data, "created_at")
            ),
            inputs=cls._mapping_value(data, "inputs"),
            outputs=cls._mapping_value(data, "outputs"),
        )

    @staticmethod
    def _required_string(data: Mapping[str, object], key: str) -> str:
        value = data.get(key)
        if not isinstance(value, str):
            raise ValueError(f"Calculation field '{key}' must be a string.")
        return value

    @staticmethod
    def _mapping_value(data: Mapping[str, object], key: str) -> dict[str, object]:
        value = data.get(key)
        if not isinstance(value, Mapping):
            raise ValueError(f"Calculation field '{key}' must be a mapping.")
        if not all(isinstance(item_key, str) for item_key in value):
            raise ValueError(f"Calculation field '{key}' has an invalid key.")
        return dict(value)
