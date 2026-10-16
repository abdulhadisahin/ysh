"""Small master-data catalogs and explicit project-context edits; no SQL or math."""
from __future__ import annotations

from dataclasses import dataclass, replace
from uuid import UUID, NAMESPACE_URL, uuid5

from engineering.system_context import ContextReference, SystemContext
from engineering.module_registry import ModuleAvailability, module_availability
from repositories.system_repository import SystemRepository
from repositories.circuit_repository import CircuitRepository
from repositories.fluid_repository import FluidRepository
from repositories.v2_models import System, Circuit, Fluid


DEFAULT_SYSTEMS = tuple(System(
    id=uuid5(NAMESPACE_URL, f"d243:application-system:{code}"),
    code=code, name_tr=tr, name_en=en,
) for code, tr, en in (("FUEL", "Yakıt", "Fuel"),
                      ("FRESH_WATER", "Tatlı Su", "Fresh Water"),
                      ("OIL", "Yağ", "Oil")))


@dataclass(frozen=True, slots=True)
class ContextIssue:
    """Unresolved IDs remain historical facts instead of being replaced."""
    field: str
    reason_key: str


def reference(record: System | Circuit | Fluid) -> ContextReference:
    """Capture available identity/labels, without properties or rule lookups."""
    return ContextReference(id=record.id, code=record.code,
                            name_tr=record.name_tr, name_en=record.name_en)


class SystemContextService:
    """Cache small catalogs between explicit reloads; no polling or startup writes."""

    def __init__(self, systems: SystemRepository | None = None,
                 circuits: CircuitRepository | None = None,
                 fluids: FluidRepository | None = None) -> None:
        """Accept Phase 4 repositories; application defaults require no database rows."""
        self._system_repository = systems
        self._circuit_repository = circuits
        self._fluid_repository = fluids
        self._systems: tuple[System, ...] = ()
        self._fluids: tuple[Fluid, ...] = ()
        self._circuits: dict[UUID, tuple[Circuit, ...]] = {}
        self.reload()

    def reload(self) -> None:
        """Read each small catalog once; inactive user codes suppress fallback defaults."""
        stored = self._system_repository.get_all() if self._system_repository else ()
        codes = {row.code.upper() for row in stored}
        ids = {row.id for row in stored}
        self._systems = tuple(stored) + tuple(row for row in DEFAULT_SYSTEMS
                            if row.code not in codes and row.id not in ids)
        self._fluids = self._fluid_repository.get_all() if self._fluid_repository else ()
        self._circuits.clear()
        self._issue_cache: dict[SystemContext, tuple[ContextIssue, ...]] = {}

    def systems(self) -> tuple[System, ...]:
        """List active master rows and nonpersistent defaults deterministically."""
        return tuple(sorted((r for r in self._systems if r.is_active), key=lambda r: (r.code.upper(),str(r.id))))

    def fluids(self) -> tuple[Fluid, ...]:
        """Expose fluid identities; never query fluid properties."""
        return tuple(sorted((r for r in self._fluids if r.is_active), key=lambda r: (r.code.upper(),str(r.id))))

    def circuits(self, system_id: UUID | None) -> tuple[Circuit, ...]:
        """Only query the selected system, once until an explicit catalog reload."""
        if system_id is None:
            return ()
        if system_id not in self._circuits:
            self._circuits[system_id] = self._circuit_repository.get_by_system(system_id) if self._circuit_repository else ()
        return tuple(sorted((r for r in self._circuits[system_id] if r.is_active), key=lambda r: (r.code,str(r.id))))

    def issues(self, context: SystemContext) -> tuple[ContextIssue, ...]:
        """Resolve missing, inactive and invalid relationship status without erasing IDs."""
        if context in self._issue_cache:
            return self._issue_cache[context]
        issues = []
        for field, rows in (("system", self._systems), ("fluid", self._fluids)):
            saved = getattr(context, field)
            if saved is not None:
                row = next((r for r in rows if r.id == saved.id), None)
                if row is None or not row.is_active:
                    issues.append(ContextIssue(field, "context.source_missing" if row is None else "context.inactive"))
        if context.circuit is not None:
            self.circuits(context.system_id)
            row = next((r for r in self._circuits[context.system_id] if r.id == context.circuit_id), None)
            if row is None:
                row = self._circuit_repository.get(context.circuit_id) if self._circuit_repository else None
            if row is None:
                issues.append(ContextIssue("circuit", "context.source_missing"))
            elif row.system_id != context.system_id:
                issues.append(ContextIssue("circuit", "context.invalid_circuit"))
            elif not row.is_active:
                issues.append(ContextIssue("circuit", "context.inactive"))
        self._issue_cache[context] = tuple(issues)
        return tuple(issues)

    def select(self, current: SystemContext, *, system_id: UUID | None,
               circuit_id: UUID | None, fluid_id: UUID | None) -> SystemContext:
        """Validate an explicit selection; changing system clears an old circuit."""
        system = next((r for r in self.systems() if r.id == system_id), None)
        fluid = next((r for r in self.fluids() if r.id == fluid_id), None)
        if system_id is not None and system is None or fluid_id is not None and fluid is None:
            raise ValueError("Unavailable context selection")
        if system_id != current.system_id and circuit_id == current.circuit_id:
            circuit_id = None
        circuit = next((r for r in self.circuits(system_id) if r.id == circuit_id), None)
        if circuit_id is not None and circuit is None:
            raise ValueError("Circuit does not belong to selected system")
        return current.changed(system=reference(system) if system else None,
                               circuit=reference(circuit) if circuit else None,
                               fluid=reference(fluid) if fluid else None)

    def availability(self, context: SystemContext) -> tuple[ModuleAvailability, ...]:
        """Use current resolved system scope while retaining historical saved labels."""
        system = next((row for row in self._systems if row.id == context.system_id), None)
        effective = context
        if system is not None:
            effective = replace(context, system=reference(system))
        unavailable = any(issue.field == "system" for issue in self.issues(context))
        return module_availability(effective, unavailable=unavailable)
