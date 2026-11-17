"""Typed adapters for additive engineering catalogs; existing CRUD codec is reused."""
from repositories._v2_base import _Repository
from engineering.catalog import FluidSpecification,MaterialSurface,EngineeringRule

class CatalogRepository(_Repository):
    def get_all(self,*,active_only=False): return self._list('is_active=1' if active_only else '1=1')

class FluidSpecificationRepository(CatalogRepository):
    _table='fluid_specifications';_model=FluidSpecification
    def get_by_fluid(self,fluid_id):return self._list('fluid_id=?',(str(fluid_id),))

class MaterialSurfaceRepository(CatalogRepository):
    _table='material_surfaces';_model=MaterialSurface

class EngineeringRuleRepository(CatalogRepository):
    _table='engineering_rules';_model=EngineeringRule
