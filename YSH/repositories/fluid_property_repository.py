"""Typed V2 data access; no seeding, UI, or engineering calculations."""
from __future__ import annotations

from uuid import UUID

from repositories._v2_base import _Repository, _validate
from repositories.v2_models import FluidProperty


class FluidPropertyRepository(_Repository[FluidProperty]):
    _table = "fluid_properties"
    _model = FluidProperty

    def get_by_fluid(
        self, fluid_id: UUID, *, property_name: str | None = None,
    ) -> tuple[FluidProperty, ...]:
        """Return recorded values only; no interpolation or unit conversion."""
        _validate("fluid_id", fluid_id, UUID)
        where = "fluid_id=?"
        values: tuple[object, ...] = (str(fluid_id),)
        if property_name is not None:
            _validate("property_name", property_name, str)
            where += " AND property_name=?"
            values += (property_name,)
        return self._list(where, values)
