class Project:
    """Represents a project entity."""

    def __init__(self, name: str, description: str = "") -> None:
        self.name = name
        self.description = description
"""
YSH - Engineering Calculation System

Project model.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4


@dataclass(slots=True)
class Project:
    """Represents an engineering project."""

    id: str = field(default_factory=lambda: str(uuid4()))

    name: str = ""
    description: str = ""
    notes: str = ""

    created_at: datetime = field(default_factory=datetime.now)
    modified_at: datetime = field(default_factory=datetime.now)

    @property
    def display_name(self) -> str:
        """Return the name shown in the user interface."""

        return self.name if self.name else "Unnamed Project"

    def touch(self) -> None:
        """Update the modification timestamp."""

        self.modified_at = datetime.now()