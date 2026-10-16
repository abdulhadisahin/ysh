"""Typed V2 data access; no seeding, UI, or engineering calculations."""
from __future__ import annotations

from uuid import UUID

from repositories._v2_base import _Repository, _validate
from repositories.v2_models import MaterialProperty


class MaterialPropertyRepository(_Repository[MaterialProperty]):
    _table = "material_properties"
    _model = MaterialProperty

    def get_by_material(
        self, material_id: UUID, *, property_name: str | None = None,
    ) -> tuple[MaterialProperty, ...]:
        """Return recorded values only; no interpolation or unit conversion."""
        _validate("material_id", material_id, UUID)
        where = "material_id=?"
        values: tuple[object, ...] = (str(material_id),)
        if property_name is not None:
            _validate("property_name", property_name, str)
            where += " AND property_name=?"
            values += (property_name,)
        return self._list(where, values)
