"""Typed V2 data access; no seeding, UI, or engineering calculations."""
from __future__ import annotations

from repositories._v2_base import _Repository, _active_clause, _validate
from repositories.v2_models import System


class SystemRepository(_Repository[System]):
    _table = "systems"
    _model = System

    def get_by_code(self, code: str) -> System | None:
        _validate("code", code, str)
        rows = self._list("code=? COLLATE NOCASE", (code,))
        return rows[0] if rows else None

    def get_all(self, *, active_only: bool = False) -> tuple[System, ...]:
        return self._list(_active_clause(active_only))
