"""Seawater is an isolated project family, never a waiver of source applicability."""
from dataclasses import replace
from datetime import date
from io import BytesIO
from uuid import uuid4
import json

import pytest
from docx import Document

from core.project_family import project_family
from core.material import Material
from engineering.catalog_seeds import identity
from engineering.fire.enums import HWApplicability
from engineering.fire.hazen_williams_workflow import HWService
from engineering.provenance import SourceReference, SourceType, VerificationStatus
from engineering.snapshots.models import CalculationSnapshot
from engineering.system_context import SystemContext
from engineering.validation import ValidationError
from repositories.v2_models import SourceRecord, MaterialProperty
from reporting.context import freeze_report_context, snapshot_family
from reporting.models import adapt_snapshot
from reporting.word_renderer import render_word
from services.engineering_catalog_service import EngineeringCatalogService
from services.engineering_value_links import bind
from services.fire_hazen_williams_service import HWApplicabilityBlocked
from services.system_context_service import DEFAULT_SYSTEMS, reference
from ui.warning_center_state import collect_warning_summary
from .test_fire_phase5cd_navigation import application, shell
from .test_project_persistence_workflow import _service
from .test_pdf_reports_phase18 import representative_snapshots
from .test_fire_phase3_hazen_williams_workflow import request, calculate
from ._tk_geometry import settle_geometry


def sea_context(catalog, **values):
    fluid=next(r for r in catalog.project_fluids('seawater') if r.code=='SEAWATER')
    system=next(r for r in DEFAULT_SYSTEMS if r.code=='SEA_WATER')
    return SystemContext(system=reference(system),fluid=reference(fluid),**values)


@pytest.fixture
def catalog(library_database):
    return EngineeringCatalogService(library_database)


def test_seawater_creation_restart_lock_and_legacy_families(tmp_path,catalog):
    for family in ('fuel','fire','seawater'):
        service=_service(tmp_path/family)
        project=service.create_project(family,system_family=family)
        state=service.open(project.id)[1]
        assert project_family(state)==family
        if family=='seawater':
            context=sea_context(catalog,fluid_temperature_c=15,fluid_salinity_g_kg=35)
            state['system_context']=context.to_payload()
            service.save(state)
        service.close()
        restarted=_service(tmp_path/family)
        _,saved=restarted.open(project.id)
        assert project_family(saved)==family
        if family=='seawater':assert SystemContext.from_workspace(saved)==context
        changed=json.loads(json.dumps(saved));changed['navigation']['active_system_family']='fire' if family!='fire' else 'fuel'
        with pytest.raises(ValidationError,match='project_family_locked'):restarted.save(changed)
    assert project_family({})=='fuel'


def test_classification_and_absent_seawater_data_are_not_guessed(catalog):
    assert {r.code for r in catalog.project_fluids('seawater')}=={'SEAWATER'}
    assert not {r.id for r in catalog.project_fluids('seawater')} & {
        r.id for family in ('fuel','fire') for r in catalog.project_fluids(family)}
    refs=catalog.references(sea_context(catalog))
    assert all(refs[name]['default_value'] is None for name in ('density','kinematic_viscosity'))
    assert not catalog.seawater_basis(sea_context(catalog),'pipe_design')['fluid_ready']
    assert catalog.seawater_basis(sea_context(catalog),'pipe_design')['material_properties']==[]
    assert catalog.seawater_basis(sea_context(catalog),'pipe_design')['corrosion_criteria']==[]
    assert catalog.matching_rules(sea_context(catalog),'seawater','pipe_design')==()
    scoped=sea_context(catalog,rule_set_id=identity('profile:TL_FFS'),applicability_scope='TL_FFS')
    assert catalog.matching_rules(scoped,'seawater','discharge_head_loss')==()


def test_v6_upgrade_is_additive_and_idempotent(library_database):
    with library_database.connection() as connection:
        connection.execute('ALTER TABLE fluid_specifications DROP COLUMN reference_salinity_g_kg')
        connection.execute('UPDATE schema_version SET version=6')
        before={table:tuple(tuple(row) for row in connection.execute('SELECT * FROM '+table))
                for table in ('fluid_specifications','material_surfaces','engineering_rules','materials','sources')}
    library_database.initialize()
    library_database.initialize()
    with library_database.connection() as connection:
        assert connection.execute('SELECT version FROM schema_version').fetchone()[0]==8
        for table,rows in before.items():
            actual=tuple(tuple(row) for row in connection.execute('SELECT * FROM '+table))
            if table=='fluid_specifications':
                assert tuple(row[:-1] for row in actual)==rows
                assert all(row[-1] is None for row in actual)
            else:assert actual==rows


def test_exact_temperature_salinity_and_ambiguity_gate(catalog):
    context=sea_context(catalog,fluid_temperature_c=15,fluid_salinity_g_kg=35)
    # Synthetic records exercise matching, never seed physical seawater values.
    rows=[]
    for original in tuple(catalog.property_records):
        if original.fluid_id!=context.fluid_id:continue
        row=replace(original,id=uuid4(),code='TEST_ONLY_'+original.code,
            default_value=123,source_nominal=123,default_method='SOURCE_NOMINAL',
            reference_temperature_c=15,reference_salinity_g_kg=35,
            source_authority='TEST ONLY',source_document='Synthetic matching fixture',verification='VERIFIED')
        catalog.properties.create(row);rows.append(row)
    catalog.reload()
    assert catalog.seawater_basis(context,'suction_npsh')['fluid_ready']
    assert catalog.references(context)['density']['default_value']==123
    for changed in (context.changed(fluid_temperature_c=20),context.changed(fluid_salinity_g_kg=30),
                    context.changed(fluid_salinity_g_kg=None)):
        assert catalog.references(changed)['density']['default_method']=='SOURCE_REQUIRED'
    catalog.properties.create(replace(rows[0],id=uuid4(),code='TEST_ONLY_AMBIGUOUS'))
    catalog.reload()
    assert catalog.references(context)[rows[0].property_name]['default_value'] is None


def test_manual_values_stay_manual_without_a_recommendation(catalog):
    ref=catalog.references(sea_context(catalog))['density']
    link=bind(ref,123).edit(456)
    assert link.used_value==456 and not link.overridden and link.status=='SOURCE_REQUIRED'
    recommended={**ref,'default_value':123,'default_method':'USER_DEFINED'}
    assert bind(recommended,456).overridden


def test_material_and_corrosion_require_exact_verified_source_scope(catalog):
    material=catalog.material_repository.create(Material(name='TEST ONLY',designation='TEST_GRADE'))
    source=catalog.sources.create(SourceRecord(reference=SourceReference(
        source_type=SourceType.USER_INPUT,source_organization='TEST ONLY',document='Synthetic source',
        revision='test',effective_date=date(2020,1,1),verification_date=date(2021,1,1),
        verification_status=VerificationStatus.VERIFIED)))
    profile=identity('profile:EVERLLENCE')
    catalog.material_properties.create(MaterialProperty(material_id=material.id,property_name='allowable_stress',
        value=123,unit='MPa',source_id=source.id,rule_set_id=profile,verification_status=VerificationStatus.VERIFIED))
    rule=replace(catalog.rule_records[0],id=uuid4(),code='TEST_CORROSION',name='TEST ONLY',
        system_family='seawater',profile_id=profile,material='TEST_GRADE',service='SEA_WATER_COOLING',
        fluid_group='SEA_WATER',line_type='',applicability='',hard_min=None,hard_max=None,
        parameter='corrosion_allowance',unit='mm',rule_nature='RECOMMENDED_RANGE',
        recommended_min=.25,recommended_max=.25,source_authority='TEST ONLY',source_document='Synthetic source',
        source_clause='TEST TABLE',verification='VERIFIED')
    catalog.rules.create(rule);catalog.reload()
    context=sea_context(catalog,material_id=material.id,rule_set_id=profile,service='SEA_WATER_COOLING')
    basis=catalog.seawater_basis(context,'pipe_design')
    assert basis['material_properties'][0]['record']['value']==123
    assert basis['material_properties'][0]['source']['effective_date']=='2020-01-01'
    assert basis['corrosion_criteria'][0]['recommended_max']==.25
    assert catalog.seawater_basis(context.changed(service=''),'pipe_design')['corrosion_criteria']==[]
    assert catalog.seawater_basis(context.changed(rule_set_id=None),'pipe_design')['material_properties']==[]


def test_hazen_williams_seawater_blocker_cannot_be_bypassed():
    for applicability in (HWApplicability.WATER_ONLY,HWApplicability.SEAWATER_SOURCE_REQUIRED):
        with pytest.raises(HWApplicabilityBlocked):
            calculate(request(service=HWService.SEAWATER,applicability=applicability))


@pytest.mark.parametrize('index',[0,3,4])
def test_seawater_report_and_history_identity_are_frozen(index):
    original=representative_snapshots()[index]
    before=original.to_json()
    sea=freeze_report_context(original,system_family='seawater')
    assert snapshot_family(original)=='fuel' and original.to_json()==before
    restored=CalculationSnapshot.from_payload(json.loads(sea.to_json()))
    assert snapshot_family(restored)=='seawater' and restored.formula_steps==original.formula_steps
    report=adapt_snapshot(restored)
    assert report.system_family=='seawater'
    data=render_word(report)
    doc=Document(BytesIO(data))
    text='\n'.join(p.text for p in doc.paragraphs)+'\n'+'\n'.join(c.text for t in doc.tables for r in t.rows for c in r.cells)
    assert 'Deniz Suyu Sistemi' in text
    with pytest.raises(ValueError):freeze_report_context(representative_snapshots()[1],system_family='seawater')


@pytest.mark.parametrize('size',[(1100,700),(1440,900)])
def test_seawater_dialog_shell_warning_center_and_reopen(shell,monkeypatch,size):
    from ui.dialogs.new_project_dialog import NewProjectDialog
    from ui.dialogs.project_engineering_context import ProjectEngineeringContextDialog
    w=shell;root=w._root;root.deiconify();root.geometry(f'{size[0]}x{size[1]}');root.update()
    errors=[]
    def factory(*args,**kwargs):
        dialog=NewProjectDialog(*args,**kwargs)
        assert not hasattr(dialog,'_notes_text')
        assert dialog._description_text.grid_info()['row']==3
        dialog._name_entry.insert(0,'Seawater '+str(uuid4()))
        dialog._family_choice.choice.current(2);dialog._refresh_fluids()
        assert {r.code for r in dialog._fluid_records.values()}=={'SEAWATER'}
        assert dialog._fluid_records[dialog._fluid_choice.get()].code=='SEAWATER'
        def submit():
            try:dialog._submit()
            except Exception as error:errors.append(error);dialog._cancel()
        root.after_idle(submit)
        return dialog
    monkeypatch.setitem(w._open_new_project.__func__.__globals__,'NewProjectDialog',factory)
    w._open_new_project()
    assert not errors and w._locked_project_family()=='seawater'
    assert w._system_context.fluid.code=='SEAWATER' and w._system_context.system.code=='SEA_WATER'
    assert w._page_host.tab(w._page_host._page_keys['transfer_pump'],'state')=='hidden'
    c=w._engineering_context_controller
    assert c.links['suction_npsh']['density'].status=='SOURCE_REQUIRED'
    assert c.links['discharge_head_loss']['kinematic_viscosity'].status=='SOURCE_REQUIRED'
    with pytest.raises(ValueError):c.set_module_context('pipe_design',w._system_context.changed(fluid=None))
    summary=collect_warning_summary(w)
    assert summary.source_required_count>0 and any(i.code=='seawater.hw' for i in summary.items)
    assert {i.module_id for i in summary.items}<={'pipe_design','discharge_head_loss','suction_npsh'}
    pipe=w._pages['pipe_design']
    pipe._fields['q'].set('200');pipe._fields['v'].set('3');pipe._calculate_diameter()
    assert pipe._diameter_result
    assert pipe._pdf_snapshot is not None and snapshot_family(pipe._pdf_snapshot)=='seawater'
    assert pipe._formula_steps() and any(step.engineering_basis_json for step in pipe._formula_steps())
    frozen=pipe._pdf_snapshot
    basis=json.loads(frozen.formula_steps[0].engineering_basis_json)
    assert basis['seawater_basis']['hw_applicability']=='SOURCE_REQUIRED'
    assert any(item['code']=='seawater.material_required' for item in frozen.evidence['findings'])
    for module in ('pipe_design','discharge_head_loss','suction_npsh'):
        host=w._page_host._page_keys[module];w._page_host.select(host);host.canvas.yview_moveto(0)
        settle_geometry(root,w._pages[module]._engineering_panel)
    dialog=ProjectEngineeringContextDialog(w)
    try:
        assert 'fluid_temperature_c' in dialog.selection.variables
        assert 'fluid_salinity_g_kg' in dialog.selection.variables
        assert str(dialog.selection.boxes['fluid']['state'])=='disabled'
        dialog.selection.variables['fluid_temperature_c'].set('15')
        dialog.selection.variables['fluid_salinity_g_kg'].set('35')
        dialog.apply()
    finally:dialog.window.destroy()
    saved=w._system_context;w._save_project();project=w._active_project
    w._project_persistence_service.close();w._active_project=None
    w._activate_project(project);root.update()
    assert w._system_context==saved and w._locked_project_family()=='seawater'
    w._show_family('fuel',dirty=False)
    assert w._family=='seawater'
    w._project_persistence_service.close();w._active_project=None
    assert w._create_project('Fuel after sea '+str(uuid4()),'','','fuel')
    assert w._family=='fuel'
    assert w._page_host.tab(w._page_host._page_keys['transfer_pump'],'state')=='normal'


def test_transfer_availability_survives_seawater_navigation(shell):
    w=shell
    w._show_family('seawater',dirty=False)
    freshwater=next(row for row in DEFAULT_SYSTEMS if row.code=='FRESH_WATER')
    w._apply_system_context(SystemContext(system=reference(freshwater)))
    transfer=w._page_host._page_keys['transfer_pump']
    assert w._page_host.tab(transfer,'state')=='hidden'
    w._show_family('fuel',dirty=False)
    assert w._page_host.tab(transfer,'state')=='disabled'
    w._apply_system_context(SystemContext())
