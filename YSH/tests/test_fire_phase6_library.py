"""Synthetic TEST_ONLY records; never production regulatory recommendations."""
from dataclasses import replace
from io import BytesIO
import json
from uuid import uuid4

import pytest
from pypdf import PdfReader

from engineering.fire.library import FireParameter, FireEngineeringDataRecord, UNITS, FIRE_CATEGORIES, FIELD_PARAMETERS
from engineering.fire.enums import FireSourceStatus
from engineering.provenance import SourceReference, SourceType, VerificationStatus
from engineering.snapshots.models import CalculationSnapshot
from engineering.system_context import SystemContext, ContextReference
from engineering.validation import ValidationError
from repositories.source_repository import SourceRepository
from repositories.v2_models import SourceRecord
from services.engineering_library_service import EngineeringLibraryService, LibraryError
from services.fire_workspace import FireWorkspace
from services.fire_hazen_williams_service import HWApplicabilityBlocked
from services.library_catalog import CATEGORY_BY_CODE
from ui.library_controller import LibraryController
from ui.history_presentation import fire_details
from reporting.models import adapt_snapshot
from reporting.renderer import render_pdf
from .test_fire_phase5_live_ui import foam, hw


@pytest.fixture
def library(library_database):
    source=SourceRepository(library_database).create(SourceRecord(reference=SourceReference(
        source_type=SourceType.ENGINEERING_REFERENCE,source_organization='TEST_ONLY organization',
        document='TEST_ONLY Fire reference',section='Synthetic fixture',revision='TEST A',
        verification_status=VerificationStatus.VERIFIED)))
    return EngineeringLibraryService(library_database),source


def record(library,parameter=FireParameter.APPLICATION_RATE,value=5,**extra):
    service,source=library
    category=next(code for code,param in FIRE_CATEGORIES.items() if param==parameter)
    values=dict(value=value,unit=UNITS[parameter],context='TEST_ONLY',service='water' if parameter is FireParameter.HW_COEFFICIENT else 'foam',
                applicability='TEST_ONLY protected-space/product/material context',source_id=source.id,
                source_status=FireSourceStatus.SOURCE_VERIFIED_CONTEXT_DEPENDENT,notes='TEST_ONLY example, not a universal value',is_active=True)
    values.update(extra)
    return service.save(category,values)


@pytest.mark.parametrize('parameter,value',[(FireParameter.APPLICATION_RATE,5),(FireParameter.DURATION,30),
    (FireParameter.CONCENTRATION,.03),(FireParameter.HW_COEFFICIENT,120)])
def test_record_roundtrip_existing_storage_no_editable_family(library,parameter,value):
    service,_=library;r=record(library,parameter,value)
    assert service.get_fire_record(r.id)==r and r.system_family=='fire'
    assert FireEngineeringDataRecord.from_payload(r.to_payload())==r
    category=next(k for k,v in FIRE_CATEGORIES.items() if v==parameter)
    assert r in service.list_records(category) and service.can_edit(category,r)
    assert not {'system_family','system_type','family'}.intersection(f.name for f in CATEGORY_BY_CODE[category].fields)
    assert next(f for f in CATEGORY_BY_CODE[category].fields if f.name=='context').optional
    assert r.source in service.details(category,r).sources
    assert all(not row.key.startswith('FIRE.LIBRARY.') for row in service.list_records('constants'))
    assert service.get_record('constants',r.id) is None


def test_construction_browse_and_empty_lookup_do_not_seed_or_change_schema(library_database):
    with library_database.connection() as connection:
        before=tuple(connection.execute('SELECT name,sql FROM sqlite_master ORDER BY name').fetchall())
    service=EngineeringLibraryService(library_database)
    for category in FIRE_CATEGORIES:assert service.list_records(category)==()
    assert service.fire_recommendations(FireParameter.APPLICATION_RATE,'','foam')==()
    with library_database.connection() as connection:
        assert tuple(connection.execute('SELECT name,sql FROM sqlite_master ORDER BY name').fetchall())==before
        assert connection.execute("SELECT count(*) FROM engineering_constants WHERE key LIKE 'FIRE.LIBRARY.%'").fetchone()[0]==0


def test_fire_namespace_does_not_affect_legacy_fuel_constants(library,library_database):
    from repositories.engineering_constant_repository import EngineeringConstantRepository
    from services.engineering_constant_service import EngineeringConstantService, EngineeringConstantNotFoundError
    r=record(library)
    legacy=EngineeringConstantService(EngineeringConstantRepository(library_database))
    assert len(legacy.get_all_constants())==5
    assert legacy.get_constant('safety_factor').value==1.8
    raw=EngineeringConstantRepository(library_database).get(r.id)
    with pytest.raises(EngineeringConstantNotFoundError):legacy.get_constant(raw.key)
    with pytest.raises(EngineeringConstantNotFoundError):legacy.delete_constant(r.id)
    raw.key='renamed'
    with pytest.raises(EngineeringConstantNotFoundError):legacy.update_constant(raw)
    assert library[0].get_fire_record(r.id)==r


@pytest.mark.parametrize('change',[{'source_id':None},{'source_status':'SOURCE_VERIFIED','context':''},
    {'unit':'mm'},{'value':0},{'value':float('inf')},{'value':True}])
def test_invalid_or_source_less_verified_record_rejected(library,change):
    with pytest.raises(LibraryError):record(library,**change)


def test_unverified_source_and_approved_workbook_cannot_be_promoted(library,library_database):
    service,source=library;repo=SourceRepository(library_database)
    repo.update(replace(source,reference=replace(source.reference,verification_status=VerificationStatus.USER_SUPPLIED)))
    with pytest.raises(LibraryError):record(library)
    workbook=repo.create(SourceRecord(reference=replace(source.reference,document='Yangın Söndürme.xlsx')))
    with pytest.raises(LibraryError):record(library,source_id=workbook.id,source_status='SOURCE_VERIFIED')
    reference=record(library,source_id=workbook.id,source_status='WORKBOOK_REFERENCE_ONLY')
    assert reference.recommendable and reference.source_status is FireSourceStatus.WORKBOOK_REFERENCE_ONLY


def test_context_active_status_parameter_and_service_filtering(library):
    service,_=library;r=record(library)
    record(library,context='OTHER_TEST');record(library,is_active=False)
    record(library,source_status='SOURCE_REQUIRED');record(library,FireParameter.DURATION,30)
    assert service.fire_recommendations(FireParameter.APPLICATION_RATE,'TEST_ONLY','foam')==(r,)
    assert service.fire_recommendations(FireParameter.APPLICATION_RATE,'WRONG','foam')==()
    assert service.fire_recommendations(FireParameter.APPLICATION_RATE,'TEST_ONLY','water')==()


@pytest.mark.parametrize('name,parameter,recommended,used,kind',[
    ('application_density_lpm_m2',FireParameter.APPLICATION_RATE,5,'6','foam'),
    ('application_duration_min',FireParameter.DURATION,30,'40','foam'),
    ('foam_fraction',FireParameter.CONCENTRATION,.03,'6','foam'),
    ('hazen_williams_c',FireParameter.HW_COEFFICIENT,120,'140','hw')])
def test_manual_link_override_uses_actual_value_and_reason(library,name,parameter,recommended,used,kind):
    draft=FireWorkspace();(foam if kind=='foam' else hw)(draft)
    assert draft.library_inputs.links=={}
    manual=draft.calculate(kind)
    draft.set_library_context(kind,'TEST_ONLY')
    r=record(library,parameter,recommended);draft.link_library(kind,name,r)
    baseline=draft.calculate(kind)
    assert tuple((row.key,row.value,row.unit) for row in baseline.summary)==tuple((row.key,row.value,row.unit) for row in manual.summary)
    draft.set_field(kind,name,used)
    with pytest.raises(ValidationError):draft.calculate(kind)
    draft.metadata[kind][name]['reason']='TEST_ONLY approved override'
    result=draft.calculate(kind)
    evidence=next(p for p in result.input_provenance if p.field_name==name)
    expected=.06 if name=='foam_fraction' else float(used)
    assert evidence.engineering_value.used_value==expected
    assert evidence.engineering_value.recommended_value==recommended
    assert evidence.engineering_value.override_reason=='TEST_ONLY approved override'
    assert evidence.engineering_value.source==r.source
    assert str(r.id) in evidence.engineering_value.selection_reason and 'r1' in evidence.engineering_value.selection_reason
    if name=='application_density_lpm_m2':assert result.domain_result.solution_flow_lpm==1260
    if name=='hazen_williams_c':assert result.domain_result.total_pressure_loss_bar==pytest.approx(1.7832957445009588)
    draft.manual_library(kind,name)
    assert name not in draft.library_inputs.links and draft.fields[kind][name]==used


def test_revision_observation_keep_current_and_explicit_update_do_not_replace_used(library):
    service,_=library;r=record(library)
    draft=FireWorkspace();foam(draft);draft.set_library_context('foam','TEST_ONLY')
    draft.link_library('foam','application_density_lpm_m2',r);draft.calculate('foam')
    old=draft.results['foam'];snapshot=draft.snapshots['foam'].to_json()
    category='fire_foam_rate';values=service.form_values(category,r);values['value']=6
    updated=service.save(category,values,r.id)
    assert updated.revision==2
    draft.observe_library(service.get_fire_record)
    assert draft.library_inputs.stale['application_density_lpm_m2']
    assert draft.results['foam'] is old and draft.snapshots['foam'].to_json()==snapshot
    draft.keep_library('application_density_lpm_m2')
    assert draft.library_inputs.links['application_density_lpm_m2'].revision==1
    assert draft.fields['foam']['application_density_lpm_m2']=='5.0'
    assert draft.results['foam'] is old
    draft.link_library('foam','application_density_lpm_m2',updated,update=True)
    assert draft.fields['foam']['application_density_lpm_m2']=='5.0'
    assert draft.library_inputs.links['application_density_lpm_m2'].revision==2
    with pytest.raises(ValidationError):draft.calculate('foam')


def test_old_project_remains_manual_even_when_matching_record_exists(library):
    record(library)
    draft=FireWorkspace();foam(draft);state=draft.export_state();state.pop('library_inputs')
    restored=FireWorkspace.from_state(state)
    assert restored.library_inputs.links=={} and restored.fields['foam']['application_density_lpm_m2']=='5'
    assert restored.calculate('foam').domain_result.foam_concentrate_volume_l==945


def test_manual_status_claim_cannot_create_verified_provenance():
    draft=FireWorkspace();foam(draft)
    draft.metadata['foam']['application_density_lpm_m2']['status']='SOURCE_VERIFIED'
    result=draft.calculate('foam')
    evidence=next(value for value in result.input_provenance if value.field_name=='application_density_lpm_m2')
    assert evidence.source_status is FireSourceStatus.SOURCE_REQUIRED
    assert result.domain_result.foam_concentrate_volume_l==945


def test_frozen_project_links_need_no_current_library_and_keep_reason(library):
    r=record(library);draft=FireWorkspace();foam(draft)
    draft.set_library_context('foam','TEST_ONLY');draft.link_library('foam','application_density_lpm_m2',r)
    draft.set_field('foam','application_density_lpm_m2','6');draft.metadata['foam']['application_density_lpm_m2']['reason']='TEST_ONLY reason'
    restored=FireWorkspace.from_state(json.loads(json.dumps(draft.export_state())))
    assert restored.library_inputs.links['application_density_lpm_m2']==r
    assert restored.calculate('foam').domain_result.solution_flow_lpm==1260


def test_history_formula_and_pdf_are_frozen_after_library_edit(library,monkeypatch):
    service,_=library;r=record(library);draft=FireWorkspace();foam(draft)
    draft.set_library_context('foam','TEST_ONLY');draft.link_library('foam','application_density_lpm_m2',r)
    draft.set_field('foam','application_density_lpm_m2','6');draft.metadata['foam']['application_density_lpm_m2']['reason']='TEST_ONLY override'
    draft.calculate('foam');snapshot=CalculationSnapshot.from_payload(draft.snapshots['foam'].to_payload());before=snapshot.to_json()
    frozen=snapshot.evidence['facts']['fire']['library_inputs']['application_density_lpm_m2']
    assert frozen['record']['id']==str(r.id) and frozen['record']['revision']==1
    assert frozen['used_value']==6 and frozen['recommended_value']==5
    values=service.form_values('fire_foam_rate',r);values['value']=9;service.save('fire_foam_rate',values,r.id)
    monkeypatch.setattr(service,'get_fire_record',lambda *_:pytest.fail('History queried current Library'))
    from i18n.translator import Translator
    assert any('6' in row for row in fire_details(snapshot.evidence,Translator('en').translate))
    used=next(v for step in snapshot.formula_steps for v in step.used_values if v.symbol=='q')
    assert used.used_value==6 and used.recommended_value==5 and used.override_reason=='TEST_ONLY override'
    assert 'r1' in used.selection_reason
    report=adapt_snapshot(snapshot)
    text='\n'.join(page.extract_text() for page in PdfReader(BytesIO(render_pdf(report))).pages)
    assert 'TEST_ONLY Fire reference' in text and 'TEST_ONLY override' in text
    assert snapshot.to_json()==before


@pytest.mark.parametrize('c,expected',[(120,2.3717829024660286),(140,1.7832957445009588)])
def test_hw_water_regression_and_blocked_services(library,c,expected):
    draft=FireWorkspace();hw(draft);draft.set_library_context('hw','TEST_ONLY')
    r=record(library,FireParameter.HW_COEFFICIENT,c)
    draft.link_library('hw','hazen_williams_c',r)
    assert draft.calculate('hw').domain_result.total_pressure_loss_bar==pytest.approx(expected)
    for code in ('SEAWATER','FUEL','UNKNOWN'):
        draft.set_context(SystemContext(fluid=ContextReference(id=uuid4(),code=code,name_tr=code)))
        with pytest.raises(HWApplicabilityBlocked):draft.calculate('hw')


def test_chw_library_link_keeps_pipe_selection_independent(library):
    from .test_fire_phase3_hazen_williams_workflow import selection
    draft=FireWorkspace();hw(draft);draft.use_pipe(selection())
    pipe=draft.pipe;diameter=draft.fields['hw']['inside_diameter_mm'];flow=draft.fields['hw']['flow_lpm']
    draft.set_library_context('hw','TEST_ONLY')
    draft.link_library('hw','hazen_williams_c',record(library,FireParameter.HW_COEFFICIENT,120))
    assert draft.pipe is pipe and draft.fields['hw']['inside_diameter_mm']==diameter and draft.fields['hw']['flow_lpm']==flow
    assert draft.calculate('hw').domain_result.input.hazen_williams_c==120


def test_canonical_library_fraction_is_not_rounded_by_display_roundtrip(library):
    r=record(library,FireParameter.CONCENTRATION,.12345678912345678)
    draft=FireWorkspace();foam(draft);draft.set_library_context('foam','TEST_ONLY')
    draft.link_library('foam','foam_fraction',r)
    evidence=draft._parameter('foam','foam_fraction').engineering_value
    assert evidence.used_value==r.value and not evidence.is_overridden
    draft.set_field('foam','foam_fraction','0,03')
    draft.metadata['foam']['foam_fraction']['reason']='TEST_ONLY explicit low percent'
    assert draft._parameter('foam','foam_fraction').engineering_value.used_value==.0003


@pytest.mark.parametrize('area,flow,volume',[('210',31.5,945),('1660',249,7470)])
def test_foam_reference_regression(library,area,flow,volume):
    draft=FireWorkspace();foam(draft,area);draft.set_library_context('foam','TEST_ONLY')
    for name,param,value in (('application_density_lpm_m2',FireParameter.APPLICATION_RATE,5),
                            ('application_duration_min',FireParameter.DURATION,30),('foam_fraction',FireParameter.CONCENTRATION,.03)):
        draft.link_library('foam',name,record(library,param,value))
    result=draft.calculate('foam')
    assert result.domain_result.foam_concentrate_flow_lpm==flow
    assert result.domain_result.foam_concentrate_volume_l==volume
    if area=='1660':assert result.snapshot_payload['converted_results']['foam_concentrate_flow_m3h']['value']==14.94
