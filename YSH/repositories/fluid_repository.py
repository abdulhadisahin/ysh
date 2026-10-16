"""Typed V2 data access; no seeding, UI, or engineering calculations."""
from __future__ import annotations

from repositories._v2_base import _Repository, _active_clause, _validate
from repositories.v2_models import Fluid


class FluidRepository(_Repository[Fluid]):
    _table = "fluids"
    _model = Fluid

    def get_by_code(self, code: str) -> Fluid | None:
        _validate("code", code, str)
        rows = self._list("code=? COLLATE NOCASE", (code,))
        return rows[0] if rows else None

    def get_all(self, *, active_only: bool = False) -> tuple[Fluid, ...]:
        return self._list(_active_clause(active_only))

    def find_by_name(self, name: str) -> tuple[Fluid, ...]:
        """Exact bilingual name lookup; no physical-property assumptions."""
        _validate("name", name, str)
        return self._list("name_tr=? COLLATE NOCASE OR name_en=? COLLATE NOCASE", (name, name))
