"""Reusable parameter domain model for YSH."""

from __future__ import annotations

from dataclasses import dataclass, field
from collections.abc import Mapping
from uuid import UUID, uuid4


@dataclass(slots=True)
class Parameter:
    """Represents one engineering input parameter belonging to a project."""

    project_id: UUID
    category: str
    name: str
    symbol: str
    value: float
    unit: str = ""
    description: str = ""
    id: UUID = field(default_factory=uuid4)

    def to_dict(self) -> dict[str, str | float]:
        """Serialize the parameter into primitive values for data transfer."""
        return {
            "id": str(self.id),
            "project_id": str(self.project_id),
            "category": self.category,
            "name": self.name,
            "symbol": self.symbol,
            "value": self.value,
            "unit": self.unit,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> Parameter:
        """Create a parameter from a dictionary produced by :meth:`to_dict`."""
        value = data.get("value")
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise ValueError("Parameter field 'value' must be numeric.")
        return cls(
            id=UUID(cls._required_value(data, "id")),
            project_id=UUID(cls._required_value(data, "project_id")),
            category=cls._required_value(data, "category"),
            name=cls._required_value(data, "name"),
            symbol=cls._required_value(data, "symbol"),
            value=float(value),
            unit=cls._required_value(data, "unit"),
            description=cls._required_value(data, "description"),
        )

    @staticmethod
    def _required_value(data: Mapping[str, object], key: str) -> str:
        value = data.get(key)
        if not isinstance(value, str):
            raise ValueError(f"Parameter field '{key}' must be a string.")
        return value
