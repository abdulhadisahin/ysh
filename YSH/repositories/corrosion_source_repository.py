"""Typed V2 data access; no seeding, UI, or engineering calculations."""
from __future__ import annotations

from uuid import UUID

from repositories._v2_base import _Repository, _validate
from repositories.v2_errors import RepositoryNotFoundError
from repositories.v2_models import CorrosionSourceLink


class CorrosionSourceRepository(_Repository[CorrosionSourceLink]):
    _table = "corrosion_allowance_sources"
    _model = CorrosionSourceLink
    _key = "corrosion_circuit_id"

    def remove(self, corrosion_circuit_id: UUID) -> None:
        """Remove only the linkage; never delete the corrosion/source records."""
        _validate("corrosion_circuit_id", corrosion_circuit_id, UUID)
        with self._connection() as c:
            cursor = c.execute("DELETE FROM corrosion_allowance_sources WHERE corrosion_circuit_id=?", (str(corrosion_circuit_id),))
            if cursor.rowcount == 0:
                raise RepositoryNotFoundError("corrosion source linkage not found")
