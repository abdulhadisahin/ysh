"""Typed access to scoped catalog additions, independent of legacy properties."""
from repositories._v2_base import _Repository
from engineering.catalog_completion import FluidCatalogProfile, OperatingFluidProperty, MechanicalGrade, MechanicalGradeProperty

class CompletionRepository(_Repository):
    def get_all(self):return self._list()

class FluidCatalogProfileRepository(CompletionRepository):
    _table='fluid_catalog_profiles'; _model=FluidCatalogProfile; _key='fluid_id'

class OperatingFluidPropertyRepository(CompletionRepository):
    _table='operating_fluid_properties'; _model=OperatingFluidProperty

class MechanicalGradeRepository(CompletionRepository):
    _table='mechanical_grades'; _model=MechanicalGrade

class MechanicalGradePropertyRepository(CompletionRepository):
    _table='mechanical_grade_properties'; _model=MechanicalGradeProperty
