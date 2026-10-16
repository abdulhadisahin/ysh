"""Typed V2 data access; no seeding, UI, or engineering calculations."""
from __future__ import annotations

from uuid import UUID

from repositories._v2_base import _Repository, _active_clause, _validate
from repositories.v2_models import Circuit


class CircuitRepository(_Repository[Circuit]):
    _table = "circuits"
    _model = Circuit

    def get_by_code(self, system_id: UUID, code: str) -> Circuit | None:
        _validate("system_id", system_id, UUID)
        _validate("code", code, str)
        rows = self._list("system_id=? AND code=? COLLATE NOCASE", (str(system_id), code))
        return rows[0] if rows else None

    def get_by_system(self, system_id: UUID, *, active_only: bool = False) -> tuple[Circuit, ...]:
        _validate("system_id", system_id, UUID)
        return self._list("system_id=? AND " + _active_clause(active_only), (str(system_id),))
