"""Bind existing EngineeringValue evidence to Fire fields, without a second value model."""
from dataclasses import dataclass

from engineering.provenance import EngineeringValue
from engineering.fire.enums import FireSourceStatus
from engineering.validation import ValidationError, ValidationIssue


@dataclass(frozen=True, slots=True, kw_only=True)
class ParameterProvenance:
    field_name: str
    engineering_value: EngineeringValue
    source_status: FireSourceStatus

    def __post_init__(self) -> None:
        if not isinstance(self.field_name, str) or not self.field_name.strip():
            raise TypeError("field_name requires text")
        if not isinstance(self.engineering_value, EngineeringValue):
            raise TypeError("engineering_value requires EngineeringValue")
        if not isinstance(self.source_status, FireSourceStatus):
            raise TypeError("source_status requires FireSourceStatus")


def validate_provenance(model: object, evidence: tuple[ParameterProvenance, ...],
                        units: dict[str, str]) -> None:
    """Reject contradictory/duplicate evidence; never infer verification from arithmetic."""
    if not isinstance(evidence, tuple) or not all(isinstance(e, ParameterProvenance) for e in evidence):
        raise TypeError("provenance requires an immutable tuple of ParameterProvenance")
    seen = set()
    for item in evidence:
        name = item.field_name
        if name not in units or name in seen:
            raise ValidationError(ValidationIssue("fire.provenance_field", name))
        seen.add(name)
        value = item.engineering_value
        if value.used_value != getattr(model, name) or value.unit != units[name]:
            raise ValidationError(ValidationIssue("fire.provenance_mismatch", name))
