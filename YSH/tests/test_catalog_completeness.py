"""Additive catalogs cannot turn reference limits or scoped points into defaults."""
from dataclasses import replace
from pathlib import Path
import json
import sqlite3
import hashlib
from uuid import uuid4
import pytest

from database.library_database import LibraryDatabase
from database.library_v8 import create_v8_schema
from engineering.catalog_completion import FluidCatalogProfile, MechanicalGrade
from engineering.catalog_completion import OperatingFluidProperty, MechanicalGradeProperty
from engineering.catalog_completion_seeds import FLUID_IDENTITIES
from engineering.source_verification import BY_KEY
from engineering.system_context import SystemContext
from services.catalog_completion_service import CatalogCompletionService
from services.engineering_catalog_service import EngineeringCatalogService
from services.engineering_library_service import EngineeringLibraryService
from services.system_context_service import reference
from ui.dialogs.engineering_library_workspace import record_label, localized_library_value
from i18n.translator import Translator


@pytest.fixture
def db(tmp_path):
    result=LibraryDatabase(tmp_path/'library.db');result.initialize();return result


def test_v7_additive_migration_preserves_all_old_rows_and_aliases(tmp_path):
    class V7(LibraryDatabase):SCHEMA_VERSION=7
    old=V7(tmp_path/'v7.db');old.initialize()
    custom=str(uuid4())
    with old.connection() as connection:
        connection.execute('INSERT INTO fluids VALUES(?,?,?,?,0,1)',(custom,'MY_WASTE','Atık Yağ','Dirty Oil'))
        tables=[r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name!='schema_version'")]
        before={table:tuple(tuple(r) for r in connection.execute('SELECT * FROM '+table)) for table in tables}
    upgraded=LibraryDatabase(old.database_path);upgraded.initialize()
    service=CatalogCompletionService(upgraded)
    assert str(service.resolve_fluid('WASTE_OIL').id)==custom
    assert len(service.profiles.get_all())==11
    assert len(service.operating.get_all())==24
    assert len(service.grades.get_all())==1 and len(service.mechanics.get_all())==4
    with upgraded.connection() as connection:
        for table,rows in before.items():
            actual=tuple(tuple(r) for r in connection.execute('SELECT * FROM '+table))
            assert all(row in actual for row in rows)
            if table!='fluids':assert actual==rows
        dump=tuple(connection.iterdump())
    upgraded.initialize()
    with upgraded.connection() as connection:
        create_v8_schema(connection)
        assert tuple(connection.iterdump())==dump
        assert not connection.execute('PRAGMA foreign_key_check').fetchall()


def test_audit_does_not_upgrade_its_input(tmp_path):
    from YSH.tools.catalog_completeness_audit import audit
    class V7(LibraryDatabase):SCHEMA_VERSION=7
    old=V7(tmp_path/'source.db');old.initialize()
    before=hashlib.sha256(old.database_path.read_bytes()).hexdigest()
    report=audit(old.database_path)
    assert report['source_schema']==7 and report['target_schema']==8
    assert report['old_rows_preserved_in_copy'] and report['idempotent']
    assert sum(r['identity_action']!='REUSED' for r in report['fluid_inventory'])==6
    assert hashlib.sha256(old.database_path.read_bytes()).hexdigest()==before


def test_duplicate_legacy_code_is_not_reassigned(tmp_path):
    class V7(LibraryDatabase):SCHEMA_VERSION=7
    old=V7(tmp_path/'v7.db');old.initialize();legacy=str(uuid4())
    with old.connection() as c:c.execute('INSERT INTO fluids VALUES(?,?,?,?,0,1)',(legacy,'Sea water','DenizSuyu','Sea water'))
    current=LibraryDatabase(old.database_path);current.initialize();s=CatalogCompletionService(current)
    assert str(s.resolve_fluid('Sea water').id)==legacy
    assert s.resolve_fluid('SEAWATER').id!=s.resolve_fluid('Sea water').id


@pytest.mark.parametrize('code', [r[0] for r in FLUID_IDENTITIES])
def test_canonical_identity_and_aliases(db,code):
    service=CatalogCompletionService(db)
    fluid=service.resolve_fluid(code)
    assert fluid is not None
    profile=service.profiles.get(fluid.id)
    assert profile.canonical_code==code
    for alias in service.aliases(fluid.id):assert service.resolve_fluid(alias).id==fluid.id
    if code=='FOAM_SOLUTION':
        assert profile.concentration_percent is None and profile.concentration_basis=='volume_percent'
        assert replace(profile,concentration_percent=3).concentration_percent==3
        service.profiles.update(replace(profile,concentration_percent=3))
        assert CatalogCompletionService(db).profiles.get(fluid.id).concentration_percent==3
        with pytest.raises(ValueError):replace(profile,concentration_percent=101)
        assert not [r for r in service.operating.get_all() if r.fluid_id==fluid.id]


def test_unverified_new_records_do_not_default_to_verified(db):
    service=CatalogCompletionService(db)
    point=service.operating.get_all()[0]
    raw={key:value for key,value in point.__dict__.items() if key!='verification'}
    assert OperatingFluidProperty(**raw).verification=='SOURCE_REQUIRED'
    prop=service.mechanics.get_all()[0]
    raw={key:value for key,value in prop.__dict__.items() if key!='verification'}
    assert MechanicalGradeProperty(**raw).verification=='SOURCE_REQUIRED'


def test_ambiguous_identity_rolls_back_instead_of_duplicating(tmp_path):
    from database.migrations import MigrationError
    class V7(LibraryDatabase):SCHEMA_VERSION=7
    old=V7(tmp_path/'ambiguous.db');old.initialize()
    with old.connection() as c:
        for code,name in (('CUSTOM_A','Waste Oil'),('CUSTOM_B','Dirty Oil')):
            c.execute('INSERT INTO fluids VALUES(?,?,?,?,0,1)',(str(uuid4()),code,name,name))
    with pytest.raises(MigrationError,match='Ambiguous existing fluid identity'):
        LibraryDatabase(old.database_path).initialize()
    with old.connection() as c:
        assert c.execute('SELECT version FROM schema_version').fetchone()[0]==7
        assert not c.execute("SELECT name FROM sqlite_master WHERE name='fluid_catalog_profiles'").fetchone()


@pytest.mark.parametrize('code,temp,salinity,rho,nu',[
    ('WATER',10,0,999.5,1.307),('WATER',20,0,998.0,1.004),('WATER',40,0,992.2,.658),
    ('SEAWATER',10,35,1027.0,1.360),('SEAWATER',20,35,1024.9,1.050),('SEAWATER',40,35,1018.3,.695),
    ('SEAWATER',20,30,1021.1,1.043),('SEAWATER',20,40,1028.8,1.058),
])
def test_published_points_units_and_frozen_provenance(db,code,temp,salinity,rho,nu):
    service=CatalogCompletionService(db);fluid=service.resolve_fluid(code)
    rows=service.operating_references(fluid.id,temperature_c=temp,salinity_g_kg=salinity,pressure_mpa=.101325)
    assert rows['density']['value']==rho and rows['density']['unit']=='kg/m³'
    assert rows['kinematic_viscosity']['value']==nu and rows['kinematic_viscosity']['unit']=='cSt'
    proof=rows['density']['source_evidence']
    assert proof['publication_date'] is None
    assert proof['revision_date']=='2023-12-09' and proof['verification_date']=='2026-11-24'
    assert 'Tables 3 and 21' in proof['clause']
    assert service.operating_references(fluid.id,temperature_c=temp,salinity_g_kg=salinity,pressure_mpa=8)=={}
    assert service.operating_references(fluid.id,temperature_c=21,salinity_g_kg=salinity,pressure_mpa=.101325)=={}
    assert service.operating_references(fluid.id,temperature_c=None,salinity_g_kg=salinity,pressure_mpa=.101325)=={}


def test_ambiguous_point_is_not_last_record_wins(db):
    service=CatalogCompletionService(db);fluid=service.resolve_fluid('SEAWATER')
    row=next(r for r in service.operating.get_all() if r.fluid_id==fluid.id and r.reference_temperature_c==20 and r.reference_salinity_g_kg==35 and r.property_name=='density')
    service.operating.create(replace(row,id=uuid4(),code='USER_OTHER',value=1026))
    refs=service.operating_references(fluid.id,temperature_c=20,salinity_g_kg=35,pressure_mpa=.101325)
    assert 'density' not in refs and 'kinematic_viscosity' in refs


def test_fuel_limits_and_existing_calculator_defaults_do_not_change(db):
    catalog=EngineeringCatalogService(db)
    f76=next(f for f in catalog.fluid_records if f.code=='F76')
    ref=catalog.references(SystemContext(fluid=reference(f76)))['density']
    assert (ref['source_min'],ref['source_max'],ref['default_value'])==(800,876,838)
    assert ref['default_method']=='DERIVED_MIDPOINT'
    assert not catalog.completion.operating_references(f76.id,temperature_c=15,salinity_g_kg=0,pressure_mpa=.101325)
    water=catalog.completion.resolve_fluid('WATER')
    assert catalog.references(SystemContext(fluid=reference(water)))['density']['default_value'] is None
    assert {f.code for f in catalog.project_fluids('fire')}=={'WATER'}
    assert {f.code for f in catalog.project_fluids('seawater')}=={'SEAWATER'}
    assert not {'HVAC_AIR','COMPRESSED_AIR','FOAM_SOLUTION','WASTE_OIL'} & {f.code for f in catalog.project_fluids('fuel')}


@pytest.mark.parametrize('thickness,yield_min',[(.1,235),(16,235),(16.01,225),(40,225),(40.01,215),(60,215)])
def test_mechanical_grade_thickness_boundaries_and_separation(db,thickness,yield_min):
    service=CatalogCompletionService(db);grade=service.grades.get_all()[0]
    assert grade.designation=='P235TR2' and grade.material_number=='1.0255'
    assert grade.standard=='EN 10216-1:2013' and grade.national_adoption_status=='SOURCE_REQUIRED'
    rows={r['property_name']:r for r in service.mechanical_properties(grade.id,thickness_mm=thickness)}
    assert rows['ReH']['minimum_value']==yield_min and rows['ReH']['maximum_value'] is None
    assert (rows['Rm']['minimum_value'],rows['Rm']['maximum_value'],rows['Rm']['unit'])==(360,500,'MPa')
    assert rows['Rm']['source_evidence']['publication_date']=='2013-12'
    assert not {'roughness','allowable_stress'} & rows.keys()
    assert service.mechanical_properties(grade.id,thickness_mm=60.01)==()
    assert service.mechanical_properties(grade.id,thickness_mm=None)==()


@pytest.mark.parametrize('language',['tr','en'])
def test_library_browse_scoped_records_read_only_and_localized(db,language):
    service=EngineeringLibraryService(db);tr=Translator(language).translate
    with db.connection() as c:before=tuple(c.iterdump())
    grade=next(r for r in service.list_display_records('materials') if isinstance(r,MechanicalGrade))
    assert not service.can_edit('materials',grade)
    points=service.list_display_records('fluid_properties')
    assert len([r for r in points if hasattr(r,'reference_pressure_mpa')])==24
    mechanics=service.list_display_records('material_properties',grade.id)
    assert len(mechanics)==4
    for category,rows in (('fluid_properties',points),('material_properties',mechanics),('materials',(grade,))):
        for row in rows:
            assert record_label(row,tr)
            details=service.details(category,row)
            assert 'source_key' not in dict(details.values)
            for key,value in details.values:
                shown=localized_library_value(key,value,tr)
                assert not str(shown).startswith('catalog.')
    assert any(r.publication_date=='2013-12' for r in service.list_display_records('sources'))
    with db.connection() as c:assert tuple(c.iterdump())==before
