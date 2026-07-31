"""Reusable engineering result and message data structures."""

from __future__ import annotations

from dataclasses import dataclass, field
from collections.abc import Mapping

from engineering.exceptions import EngineeringValidationError
from engineering.validation import validate_finite_number

_ALLOWED_MESSAGE_LEVELS: frozenset[str] = frozenset({"INFO", "WARNING", "ERROR"})


@dataclass(slots=True)
class EngineeringMessage:
    """Represents a traceable informational, warning, or error message."""

    level: str
    code: str
    text: str

    def __post_init__(self) -> None:
        """Normalize and validate message fields after construction."""
        if not isinstance(self.level, str):
            raise EngineeringValidationError("Message level must be text.")
        if not isinstance(self.code, str):
            raise EngineeringValidationError("Message code must be text.")
        if not isinstance(self.text, str):
            raise EngineeringValidationError("Message text must be text.")
        self.level = self.level.strip().upper()
        if self.level not in _ALLOWED_MESSAGE_LEVELS:
            raise EngineeringValidationError(
                "Message level must be INFO, WARNING, or ERROR."
            )
        if not self.code.strip():
            raise EngineeringValidationError("Message code is required.")
        if not self.text.strip():
            raise EngineeringValidationError("Message text is required.")
        self.code = self.code.strip()
        self.text = self.text.strip()

    def to_dict(self) -> dict[str, str]:
        """Serialize the message into primitive data."""
        return {"level": self.level, "code": self.code, "text": self.text}

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> EngineeringMessage:
        """Create a message from data produced by :meth:`to_dict`."""
        return cls(
            level=_required_text(data, "level", "message"),
            code=_required_text(data, "code", "message"),
            text=_required_text(data, "text", "message"),
        )


@dataclass(slots=True)
class EngineeringResult:
    """Contains a numeric engineering result and traceability messages."""

    value: float | int | None = None
    unit: str = ""
    messages: list[EngineeringMessage] = field(default_factory=list)
    metadata: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate result fields while preserving internal numeric precision."""
        if self.value is not None:
            self.value = validate_finite_number(self.value, "result value")
        if not isinstance(self.unit, str):
            raise EngineeringValidationError("Result unit must be text.")
        if not isinstance(self.metadata, dict):
            raise EngineeringValidationError("Result metadata must be a dictionary.")
        if not all(isinstance(message, EngineeringMessage) for message in self.messages):
            raise EngineeringValidationError(
                "Result messages must contain EngineeringMessage values."
            )

    @property
    def has_warnings(self) -> bool:
        """Return whether the result contains one or more warning messages."""
        return any(message.level == "WARNING" for message in self.messages)

    @property
    def has_errors(self) -> bool:
        """Return whether the result contains one or more error messages."""
        return any(message.level == "ERROR" for message in self.messages)

    @property
    def is_successful(self) -> bool:
        """Return whether the result contains no error messages."""
        return not self.has_errors

    def add_info(self, code: str, text: str) -> None:
        """Add an informational traceability message."""
        self.messages.append(EngineeringMessage("INFO", code, text))

    def add_warning(self, code: str, text: str) -> None:
        """Add a warning traceability message."""
        self.messages.append(EngineeringMessage("WARNING", code, text))

    def add_error(self, code: str, text: str) -> None:
        """Add an error traceability message."""
        self.messages.append(EngineeringMessage("ERROR", code, text))

    def to_dict(self) -> dict[str, object]:
        """Serialize result data, messages, and metadata without rounding values."""
        return {
            "value": self.value,
            "unit": self.unit,
            "messages": [message.to_dict() for message in self.messages],
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> EngineeringResult:
        """Create a result from data produced by :meth:`to_dict`."""
        messages_data = data.get("messages", [])
        metadata_data = data.get("metadata", {})
        if not isinstance(messages_data, list):
            raise EngineeringValidationError("Result messages must be a list.")
        if not isinstance(metadata_data, dict):
            raise EngineeringValidationError("Result metadata must be a dictionary.")
        unit = data.get("unit")
        if not isinstance(unit, str):
            raise EngineeringValidationError("Result unit must be text.")
        return cls(
            value=data.get("value"),
            unit=unit,
            messages=[EngineeringMessage.from_dict(item) for item in messages_data],
            metadata=dict(metadata_data),
        )


def _required_text(data: Mapping[str, object], key: str, subject: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise EngineeringValidationError(f"{subject.capitalize()} {key} is required.")
    return value
