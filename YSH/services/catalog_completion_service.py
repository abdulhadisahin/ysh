"""Exact-condition read-only catalog queries. No calculator or historical lookup."""
from dataclasses import asdict
import math
import json
from repositories.catalog_completion_repository import (
    FluidCatalogProfileRepository, OperatingFluidPropertyRepository,
    MechanicalGradeRepository, MechanicalGradePropertyRepository,
)
from repositories.fluid_repository import FluidRepository
from engineering.source_verification import BY_KEY


def scoped_payload(row):
    result=asdict(row)
    result['source_evidence']=BY_KEY[row.source_key].payload()
    return json.loads(json.dumps(result,default=str,ensure_ascii=False,allow_nan=False))


class CatalogCompletionService:
    def __init__(self,database):
        self.database=database
        self.profiles=FluidCatalogProfileRepository(database)
        self.operating=OperatingFluidPropertyRepository(database)
        self.grades=MechanicalGradeRepository(database)
        self.mechanics=MechanicalGradePropertyRepository(database)

    def aliases(self,fluid_id):
        with self.database.connection() as db:
            return tuple(r[0] for r in db.execute('SELECT alias FROM fluid_aliases WHERE fluid_id=? ORDER BY alias',(str(fluid_id),)))

    def resolve_fluid(self,name):
        """Exact code takes precedence, preserving legacy user identities."""
        with self.database.connection() as db:
            row=db.execute('SELECT id FROM fluids WHERE code=? COLLATE NOCASE',(name,)).fetchone()
            if row is None:row=db.execute('SELECT fluid_id FROM fluid_aliases WHERE alias=? COLLATE NOCASE',(name,)).fetchone()
        if row is None:return None
        from uuid import UUID
        return FluidRepository(self.database).get(UUID(row[0]))

    def operating_references(self,fluid_id,*,temperature_c,salinity_g_kg,pressure_mpa):
        """Only a unique published point; never interpolate or use spec limits."""
        conditions=(temperature_c,salinity_g_kg,pressure_mpa)
        if any(type(v) not in (int,float) or not math.isfinite(v) for v in conditions):return {}
        if salinity_g_kg<0 or pressure_mpa<=0:return {}
        matches=[row for row in self.operating.get_all() if row.fluid_id==fluid_id and row.verification=='VERIFIED' and row.is_active
            and (row.reference_temperature_c,row.reference_salinity_g_kg,row.reference_pressure_mpa)==conditions]
        result={}
        for name in ('density','kinematic_viscosity'):
            candidates=[row for row in matches if row.property_name==name]
            if len(candidates)==1:result[name]=scoped_payload(candidates[0])
        return result

    def mechanical_properties(self,grade_id,*,thickness_mm):
        if type(thickness_mm) not in (int,float) or not math.isfinite(thickness_mm) or thickness_mm<=0:return ()
        return tuple(scoped_payload(row) for row in self.mechanics.get_all() if row.grade_id==grade_id and row.is_active
            and row.thickness_above_mm<thickness_mm<=row.thickness_up_to_mm and row.verification=='VERIFIED')
