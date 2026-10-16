"""Typed V2 data access; no seeding, UI, or engineering calculations."""
from __future__ import annotations

from uuid import UUID

from repositories._v2_base import _Repository, _active_clause, _validate
from repositories.v2_models import RuleSet


class RuleSetRepository(_Repository[RuleSet]):
    _table = "rule_sets"
    _model = RuleSet

    def get_by_code(self, code: str, *, active_only: bool = False) -> tuple[RuleSet, ...]:
        """A code can have several revisions, including unknown revisions."""
        _validate("code", code, str)
        return self._list("code=? COLLATE NOCASE AND " + _active_clause(active_only), (code,))

    def get_all(self, *, active_only: bool = False) -> tuple[RuleSet, ...]:
        return self._list(_active_clause(active_only))
