"""V6 catalog, explicit context inheritance, rule policy and frozen evidence."""
from dataclasses import replace,asdict
from pathlib import Path
from uuid import uuid4
import json,sqlite3
import pytest
from database.library_database import LibraryDatabase
from services.engineering_catalog_service import EngineeringCatalogService
from services.engineering_value_links import bind,EngineeringValueLink
from engineering.catalog_seeds import identity,fluid_seeds,surface_seeds,rule_seeds,d243_rule
from engineering.rule_evaluation import rule_status,applicable_rules,evaluate_rule
from engineering.system_context import SystemContext,ContextReference
from .test_project_persistence_workflow import _service

@pytest.fixture
def catalog(tmp_path):
    database=LibraryDatabase(tmp_path/'library.db');database.initialize()
    return EngineeringCatalogService(database)

def chosen(catalog,*,fuel='F76',surface='CARBON_NEW',profile='EVERLLENCE',line='DELIVERY',scope=''):
    fluid=next(f for f in catalog.fluid_records if f.code==fuel)
    return SystemContext(fluid=ContextReference(id=fluid.id,code=fluid.code,name_tr=fluid.name_tr,name_en=fluid.name_en),
        surface_profile_id=identity('surface:'+surface),rule_set_id=identity('profile:'+profile),line_type=line,applicability_scope=scope)

def test_verified_fluids_and_one_sided_limit(catalog):
    refs=catalog.references(chosen(catalog))
    density=refs['density'];viscosity=refs['kinematic_viscosity']
    assert (density['source_min'],density['source_max'],density['default_value'],density['reference_temperature_c'])==(800,876,838,15)
    assert (viscosity['source_min'],viscosity['source_max'],viscosity['default_value'],viscosity['reference_temperature_c'])==(1.7,4.3,3,40)
    assert density['default_method']==viscosity['default_method']=='DERIVED_MIDPOINT'
    assert density['verification']=='VERIFIED' and density['source_nominal'] is None
    f44=catalog.references(chosen(catalog,fuel='F44'))
    assert f44['density']['default_value']==816.5
    assert f44['kinematic_viscosity']['source_min'] is None
    assert f44['kinematic_viscosity']['source_max']==7
    assert f44['kinematic_viscosity']['reference_temperature_c']==-20
    assert f44['kinematic_viscosity']['default_value'] is None
    spec=next(r for r in catalog.property_records if r.code=='F44_KINEMATIC_VISCOSITY')
    with pytest.raises(ValueError,match='Midpoint'):replace(spec,default_method='DERIVED_MIDPOINT',default_value=3.5)


def test_unresolved_marine_grades_and_surface_conditions(catalog):
    for code in ('DMA','DMZ','DMB','RMA_20','RME_180','RMG_380','RMK_500'):
        context=chosen(catalog,fuel=code)
        refs=catalog.references(context)
        assert refs['density']['default_value'] is None and refs['density']['source_document']=='ISO 8217:2024'
        distillate=code in ('DMA','DMZ','DMB')
        assert (refs['kinematic_viscosity']['default_method']=='DERIVED_MIDPOINT')==distillate
    low,high={'DMA':(2.,6.),'DMZ':(2.,6.),'DMB':(2.,11.)}['DMB']
    dmb=catalog.references(chosen(catalog,fuel='DMB'))
    assert (dmb['kinematic_viscosity']['source_min'],dmb['kinematic_viscosity']['source_max'])==(low,high)
    assert dmb['kinematic_viscosity']['default_value']==6.5 and dmb['density']['source_max']==900.
    surfaces={r.code:r for r in catalog.surface_records}
    assert surfaces['CARBON_NEW'].roughness_mm==.045 and surfaces['STAINLESS_NEW'].roughness_mm==.015
    assert surfaces['HDPE_NEW'].roughness_mm==.00152
    assert surfaces['CARBON_CORRODED'].roughness_mm is None
    assert surfaces['CARBON_CORRODED'].material_name==surfaces['CARBON_NEW'].material_name
    assert surfaces['CARBON_CORRODED'].surface_condition!=surfaces['CARBON_NEW'].surface_condition
    assert surfaces['GRE_NEW'].verification=='SOURCE_REQUIRED'
    assert surfaces['PVC_NEW'].roughness_mm==.00152 and surfaces['CAST_IRON_NEW'].roughness_mm==.122
    assert surfaces['CAST_IRON_UNCOATED'].roughness_mm==.26 and 'Table 3.A.1' in surfaces['CAST_IRON_UNCOATED'].source_document


@pytest.mark.parametrize('value,status',[(1.8,'OK'),(2.1,'WARNING'),(3,'OUT_OF_RANGE'),(15,'CRITICAL'),(99,'CRITICAL')])
def test_parameterized_manufacturer_velocity_policy(value,status):
    rule=next(r for r in rule_seeds() if r.code=='EVERLLENCE_DIESEL_FUEL_DELIVERY')
    assert rule_status(rule,value)==status
    assert rule.rule_nature=='RECOMMENDED_RANGE' and rule.source_authority=='Everllence'


@pytest.mark.parametrize('value,status',[(7,'OK'),(7.01,'WARNING'),(8,'OUT_OF_RANGE'),(99,'CRITICAL')])
def test_d243_is_its_own_authoritative_record(value,status):
    rule=d243_rule()
    assert rule.source_authority==rule.source_document=='D243'
    assert rule.rule_nature=='D243_CRITERION' and rule.recommended_max==7
    assert not any(word in rule.source_document for word in ('Türk','ISO','Everllence'))
    assert rule_status(rule,value)==status
    findings=evaluate_rule(rule,value)
    assert bool(findings)==(value>7)
    if findings:assert not findings[0].blocks_calculation


def test_hard_limit_has_no_yellow_grace_and_scope_is_explicit(catalog):
    rule=next(r for r in catalog.rule_records if r.code=='TL_FFS_DELIVERY')
    assert rule_status(rule,4)=='OK' and rule_status(rule,4.01)=='OUT_OF_RANGE'
    kwargs=dict(family='fire',profile_id=rule.profile_id,fluid_group='FRESH_WATER',line_type='DELIVERY')
    assert rule not in applicable_rules(catalog.rule_records,**kwargs)
    assert rule in applicable_rules(catalog.rule_records,scope='TL_FFS',**kwargs)
    assert rule not in applicable_rules(catalog.rule_records,scope='TL_FFS',**{**kwargs,'family':'fuel'})
    assert next(r for r in catalog.rule_records if r.code=='TL_FFS_NPSH').hard_min==1
    codes={r.code:r for r in catalog.rule_records}
    assert 'BALLAST' not in codes and 'BILGE' not in codes and 'WARTSILA' not in codes  # unfillable placeholders removed
    assert (codes['CUNI_9010'].recommended_max,codes['CUNI_7030'].recommended_max)==(3.5,4.0)
    assert (codes['WARTSILA_CUNI9010'].recommended_max,codes['WARTSILA_CUNI7030'].recommended_max,codes['WARTSILA_GALVANIZED'].recommended_max)==(3.0,4.5,2.5)
    assert all(codes[c].source_document and codes[c].source_clause and codes[c].verification=='RECOMMENDATION' for c in codes if c.startswith(('CUNI_','WARTSILA_')))


def test_factory_d243_and_manufacturer_rules_coexist(catalog):
    rules=catalog.matching_rules(chosen(catalog),'fuel','pipe_design')
    assert {r.code for r in rules}=={'D243_FUEL_MAX','EVERLLENCE_DIESEL_FUEL_DELIVERY'}
    assert {r.source_authority for r in rules}=={'D243','Everllence'}


def test_link_updates_and_manual_without_recommendation(catalog):
    refs=catalog.references(chosen(catalog));steel=refs['absolute_roughness']
    stainless=catalog.references(chosen(catalog,surface='STAINLESS_NEW'))['absolute_roughness']
    linked=bind(steel)
    assert linked.used_value==.045 and linked.status=='LINKED'
    pending=linked.observe(stainless);assert pending.stale and pending.used_value==.045
    assert pending.keep().stale and pending.keep().used_value==.045
    assert pending.update().used_value==.015
    override=linked.edit(.1).observe(stainless)
    assert override.overridden and override.update().used_value==.1
    assert override.use_reference().used_value==.015
    unresolved=catalog.references(chosen(catalog,fuel='F44'))['kinematic_viscosity']
    manual=bind(unresolved,3.)
    assert not manual.overridden and manual.status=='SOURCE_REQUIRED'
    assert EngineeringValueLink.from_payload(override.payload())==override
    assert refs['absolute_roughness']['default_value']==.045


def test_project_context_and_links_roundtrip_without_mutating_family(tmp_path,catalog):
    service=_service(tmp_path);project=service.create_project('Context',system_family='fuel')
    context=chosen(catalog);link=bind(catalog.references(context)['density'],850)
    state={'schema_version':1,'system_context':context.to_payload(),
           'engineering_links':{'version':1,'links':{'suction_npsh':{'density':link.payload()}}}}
    service.save(state);service.close();_,restored=service.open(project.id)
    assert SystemContext.from_workspace(restored)==context
    assert EngineeringValueLink.from_payload(restored['engineering_links']['links']['suction_npsh']['density']).overridden
    service.save({'schema_version':1,'pipe_design':{}})
    _,again=service.open(project.id)
    assert again['engineering_links']==restored['engineering_links']
    assert again['navigation']['active_system_family']=='fuel'


def test_v5_migration_preserves_existing_rows_and_is_atomic(tmp_path,monkeypatch):
    path=tmp_path/'v5.db'
    with monkeypatch.context() as patch:
        patch.setattr(LibraryDatabase,'SCHEMA_VERSION',5)
        LibraryDatabase(path).initialize()
    with sqlite3.connect(path) as c:
        fluid_id=str(uuid4());c.execute('INSERT INTO fluids(id,code,name_tr,is_factory,is_active) VALUES(?,?,?,0,1)',(fluid_id,'CUSTOM','User fluid'))
        before={name:c.execute('SELECT * FROM '+name).fetchall() for name in ('materials','engineering_constants','fluid_properties','pump_references')}
    globals_=LibraryDatabase.create_schema.__globals__;original=globals_['create_v6_schema']
    def fail(connection):
        original(connection);connection.execute("UPDATE materials SET name='broken'");raise RuntimeError('rollback')
    from database.migrations import MigrationError
    with monkeypatch.context() as patch:
        patch.setitem(globals_,'create_v6_schema',fail)
        with pytest.raises(MigrationError):LibraryDatabase(path).initialize()
    with sqlite3.connect(path) as c:
        assert c.execute('SELECT version FROM schema_version').fetchone()[0]==5
        assert not c.execute("SELECT name FROM sqlite_master WHERE name='engineering_rules'").fetchall()
        for name,rows in before.items():assert c.execute('SELECT * FROM '+name).fetchall()==rows
    database=LibraryDatabase(path);database.initialize();database.initialize()
    with database.connection() as c:
        assert c.execute('SELECT version FROM schema_version').fetchone()[0]==11
        for name,rows in before.items():assert [tuple(row) for row in c.execute('SELECT * FROM '+name)]==rows
        assert c.execute('SELECT name_tr FROM fluids WHERE id=?',(fluid_id,)).fetchone()[0]=='User fluid'
        assert not c.execute('PRAGMA foreign_key_check').fetchall()
        assert c.execute('SELECT count(*) FROM engineering_rules').fetchone()[0]==len(rule_seeds())

def test_v6_profile_and_fluid_code_collisions_preserve_user_identity(tmp_path,monkeypatch):
    path=tmp_path/'collision.db'
    with monkeypatch.context() as patch:
        patch.setattr(LibraryDatabase,'SCHEMA_VERSION',5)
        LibraryDatabase(path).initialize()
    fluid_id=str(uuid4());profile_id=str(uuid4())
    with sqlite3.connect(path) as c:
        c.execute('INSERT INTO fluids(id,code,name_tr,is_factory,is_active) VALUES(?,?,?,0,1)',(fluid_id,'F76','User F76'))
        c.execute('INSERT INTO rule_sets(id,code,name,is_active,created_at,modified_at) VALUES(?,?,?,1,?,?)',(profile_id,'ENG_D243','User profile','2026-11-17T00:00:00+00:00','2026-11-17T00:00:00+00:00'))
    database=LibraryDatabase(path);database.initialize()
    service=EngineeringCatalogService(database)
    assert str(next(r for r in service.fluid_records if r.code=='F76').id)==fluid_id
    assert next(r for r in service.fluid_records if r.code=='F76').name_tr=='User F76'
    rule=next(r for r in service.rule_records if r.code=='D243_FUEL_MAX')
    assert str(rule.profile_id)==profile_id
    assert rule in service.matching_rules(SystemContext(),'fuel','pipe_design')
    with database.connection() as c:assert not c.execute('PRAGMA foreign_key_check').fetchall()


def test_new_library_categories_support_user_records_without_editing_factory(catalog):
    from services.engineering_library_service import EngineeringLibraryService
    service=EngineeringLibraryService(catalog.rules._database)
    seed=next(iter(catalog.surface_records))
    repository=catalog.surfaces
    assert not service.can_edit('material_surfaces',seed)
    user=repository.create(replace(seed,id=uuid4(),code='USER_SURFACE',name='User surface',roughness_mm=.06,is_factory=False,verification='RECOMMENDATION'))
    assert repository.get(user.id)==user
    updated=repository.update(replace(user,roughness_mm=.07))
    assert repository.get(user.id).roughness_mm==.07
    assert repository.get(seed.id)==seed

def test_inactive_parent_sources_are_not_silently_recommended(catalog):
    context=chosen(catalog)
    fluid=next(r for r in catalog.fluid_records if r.id==context.fluid_id)
    catalog.fluid_repository.update(replace(fluid,is_active=False))
    catalog.reload()
    assert 'density' not in catalog.references(context)
    linked=bind({'default_value':838},850).observe(None)
    assert linked.status=='STALE' and linked.used_value==850
    with pytest.raises(ValueError,match='no longer available'):linked.use_reference()
    profile=next(r for r in catalog.profile_records if r.id==context.rule_set_id)
    catalog.profile_repository.update(replace(profile,is_active=False))
    catalog.reload()
    assert [r.code for r in catalog.matching_rules(context,'fuel','pipe_design')]==['D243_FUEL_MAX']
