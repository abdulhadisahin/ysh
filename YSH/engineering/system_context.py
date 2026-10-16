"""Optional project context; identity is independent of engineering properties."""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from uuid import UUID

from engineering.validation import ValidationError, ValidationIssue


@dataclass(frozen=True, slots=True, kw_only=True)
class ContextReference:
    """Retain saved identity and labels even if master data later disappears."""
    id: UUID
    code: str
    name_tr: str
    name_en: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.id, UUID):
            raise ValueError("Context reference requires a UUID")
        if not isinstance(self.code, str) or not isinstance(self.name_tr, str):
            raise ValueError("Context reference requires text labels")
        if self.name_en is not None and not isinstance(self.name_en, str):
            raise ValueError("Invalid context name")


@dataclass(frozen=True, slots=True, kw_only=True)
class SystemContext:
    """Owned by one workspace, never a global application preference."""
    system: ContextReference | None = None
    circuit: ContextReference | None = None
    fluid: ContextReference | None = None
    material_id: UUID | None = None
    pipe_standard_id: UUID | None = None
    rule_set_id: UUID | None = None
    revision: int = 1
    is_active: bool = True

    def __post_init__(self) -> None:
        for name in ("system", "circuit", "fluid"):
            if getattr(self, name) is not None and not isinstance(getattr(self, name), ContextReference):
                raise ValueError("Invalid context reference")
        for name in ("material_id", "pipe_standard_id", "rule_set_id"):
            if getattr(self, name) is not None and not isinstance(getattr(self, name), UUID):
                raise ValueError("Invalid context UUID")
        if self.circuit is not None and self.system is None:
            raise ValueError("A circuit requires a system")
        if type(self.revision) is not int or self.revision < 1 or type(self.is_active) is not bool:
            raise ValueError("Invalid context revision/active state")

    @property
    def system_id(self) -> UUID | None:
        """Expose the selected system identity without resolving master data."""
        return self.system.id if self.system else None

    @property
    def circuit_id(self) -> UUID | None:
        """Expose the optional circuit identity."""
        return self.circuit.id if self.circuit else None

    @property
    def fluid_id(self) -> UUID | None:
        """Expose fluid identity without reading or injecting physical properties."""
        return self.fluid.id if self.fluid else None

    def changed(self, **values: object) -> SystemContext:
        """Advance only on an explicit metadata edit; never recalculate results."""
        updated = replace(self, **values)
        return self if updated == self else replace(updated, revision=self.revision + 1)

    def to_payload(self) -> dict[str, object]:
        """Serialize a versioned additive project-state namespace."""
        data = asdict(self)
        for name in ("system", "circuit", "fluid"):
            if data[name] is not None:
                data[name]["id"] = str(data[name]["id"])
        for name in ("material_id", "pipe_standard_id", "rule_set_id"):
            data[name] = str(data[name]) if data[name] is not None else None
        return {"version": 1, **data}

    @classmethod
    def from_workspace(cls, workspace: dict[str, object]) -> SystemContext:
        """Legacy workspaces remain undefined; invalid payloads fail before UI mutation."""
        if "system_context" not in workspace:
            return cls()
        try:
            raw = workspace["system_context"]
            if not isinstance(raw, dict) or type(raw.get("version")) is not int or raw["version"] != 1:
                raise ValueError("Unsupported context version")
            values = {key: raw[key] for key in cls.__dataclass_fields__ if key in raw}
            for name in ("system", "circuit", "fluid"):
                ref = values.get(name)
                if ref is not None:
                    values[name] = ContextReference(**{**ref, "id": UUID(ref["id"])})
            for name in ("material_id", "pipe_standard_id", "rule_set_id"):
                if values.get(name) is not None:
                    values[name] = UUID(values[name])
            return cls(**values)
        except (ValueError, TypeError, KeyError, AttributeError) as error:
            raise ValidationError(ValidationIssue("project_state_unsupported")) from error
