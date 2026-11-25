"""Native fluid overrides, linked updates, snapshots and project isolation."""
import json
from uuid import uuid4
import pytest
from engineering.snapshots.models import CalculationSnapshot
from .test_fire_phase5cd_navigation import application, shell
from ._tk_geometry import settle_geometry


def sea(w):
    assert w._create_project('Fluid '+str(uuid4()),'','','seawater')
    c=w._engineering_context_controller
    from .test_seawater_system import sea_context
    c.apply(sea_context(c.catalog))
    fluid=c.catalog.completion.resolve_fluid('SEAWATER')
    return c,fluid


def test_manual_values_update_keep_and_project_defaults(shell):
    w=shell;c,f=sea(w);project=w._system_context
    module='suction_npsh';page=w._pages[module]
    page._fields['viscosity'].set('4');page._fields['density'].set('1030')
    c.select_fluid(module,f.id,20,35,.101325)
    assert w._system_context==project
    assert c.read(module,'kinematic_viscosity')==4
    link=c.links[module]['kinematic_viscosity']
    if link.stale:
        c.action(module,'kinematic_viscosity','keep');assert c.read(module,'kinematic_viscosity')==4
        c.action(module,'kinematic_viscosity','update');assert c.read(module,'kinematic_viscosity')==4
    assert c.links[module]['kinematic_viscosity'].overridden
    c.action(module,'kinematic_viscosity','reference')
    assert c.read(module,'kinematic_viscosity')==1.05
    c.select_fluid(module,f.id,40,35,.101325)
    assert c.read(module,'kinematic_viscosity')==1.05
    assert c.links[module]['kinematic_viscosity'].stale
    c.action(module,'kinematic_viscosity','update')
    assert c.read(module,'kinematic_viscosity')==.695
    assert w._system_context==project
    state=w._export_all_page_states();w._project_persistence_service.save(state)
    project_record,_=w._project_persistence_service.open(w._active_project.id)
    w._activate_project(project_record);w._root.update()
    c=w._engineering_context_controller
    assert c.context_for(module).fluid_reference_pressure_mpa==.101325
    assert c.context_for(module).fluid_temperature_c==40
    assert c.read(module,'kinematic_viscosity')==.695


@pytest.mark.parametrize('size',['1100x700','1440x900'])
def test_selector_geometry_filter_and_draft_preservation(shell,size):
    w=shell;c,f=sea(w);w._root.deiconify();w._root.geometry(size)
    for module in ('discharge_head_loss','suction_npsh'):
        panel=w._pages[module]._engineering_panel
        w._page_host.select(w._page_host._page_keys[module])
        settle_geometry(w._root,panel,panel.fluid_box)
        assert set(panel.fluid_choices.values())=={f.id}
        assert panel.fluid_box.get().endswith('SEAWATER')
        panel.conditions['temperature'].set('20')
        panel.conditions['salinity'].set('35');panel.conditions['pressure'].set('.101325')
        c.refresh_labels()
        assert panel.conditions['temperature'].get()=='20'
        assert panel._apply_fluid()
        assert c.context_for(module).fluid_temperature_c==20
        assert 'line_type' not in panel.conditions
        assert panel.fluid_box.winfo_reqwidth()>0
        assert panel.operating.winfo_rootx()+panel.operating.winfo_width()<=w._root.winfo_rootx()+w._root.winfo_width()


def test_discharge_snapshot_captures_frozen_fluid_and_reference_density(shell,monkeypatch):
    from reporting.models import adapt_snapshot
    w=shell;c,f=sea(w);page=w._pages['discharge_head_loss']
    c.select_fluid('discharge_head_loss',f.id,20,35,.101325)
    for name in ('density','kinematic_viscosity'):
        link=c.links['discharge_head_loss'][name]
        if link.stale:c.action('discharge_head_loss',name,'reference')
    for key,value in {'d':'100','q':'20','nu':'1.05','l':'10','k':'.015','h':'2'}.items():page._fields[key].set(value)
    page._calculate()
    snapshot=page._pdf_snapshot
    assert snapshot is not None
    basis=json.loads(snapshot.formula_steps[0].engineering_basis_json)
    assert basis['fluid_id']==str(f.id)
    assert basis['fluid_conditions']=={'temperature_c':20,'salinity_g_kg':35,'pressure_mpa':.101325}
    density=next(v for v in basis['values'] if v['reference']['property_name']=='density')
    assert density['used_value']==1024.9 and density['use_role']=='REFERENCE_ONLY'
    assert density['reference']['source_evidence']['revision_date']=='2023-12-09'
    before=snapshot.to_json()
    report=adapt_snapshot(snapshot)
    restored=CalculationSnapshot.from_payload(json.loads(before))
    c.catalog.reload();c.select_fluid('discharge_head_loss',f.id,40,35,.101325)
    assert restored.to_json()==before and adapt_snapshot(restored)==report


def test_family_filter_rejects_cross_family_override(shell):
    w=shell;assert w._create_project('Fuel '+str(uuid4()),'','','fuel')
    c=w._engineering_context_controller
    water=c.catalog.completion.resolve_fluid('WATER')
    with pytest.raises(ValueError):c.select_fluid('discharge_head_loss',water.id,20,None,.101325)
    assert not any(c.catalog.completion.resolve_fluid(code).id in w._pages['discharge_head_loss']._engineering_panel.fluid_choices.values() for code in ('WATER','SEAWATER','COMPRESSED_AIR'))


def test_manual_units_roughness_and_kept_source_survive_reopen(shell):
    w=shell;c,f=sea(w);module='suction_npsh';page=w._pages[module]
    page._viscosity_unit.set('m²/s');page._fields['viscosity'].set('0.000004')
    page._fields['density'].set('1030');page._fields['roughness'].set('0.012345')
    c.select_fluid(module,f.id,20,35,.101325)
    assert page._viscosity_unit.get()=='m²/s' and page._fields['viscosity'].get()=='0.000004'
    assert page._fields['density'].get()=='1030' and page._fields['roughness'].get()=='0.012345'
    c.action(module,'kinematic_viscosity','keep')
    assert c.links[module]['kinematic_viscosity'].kept_current
    w._project_persistence_service.save(w._export_all_page_states())
    record,_=w._project_persistence_service.open(w._active_project.id);w._activate_project(record)
    c=w._engineering_context_controller;page=w._pages[module]
    assert c.links[module]['kinematic_viscosity'].kept_current
    assert page._viscosity_unit.get()=='m²/s' and page._fields['viscosity'].get()=='0.000004'
    assert page._fields['roughness'].get()=='0.012345'
    c.action(module,'kinematic_viscosity','update')
    assert c.read(module,'kinematic_viscosity')==4
    assert page._viscosity_unit.get()=='m²/s'


def test_enpy_snapshot_word_history_and_warning_provenance(shell):
    from io import BytesIO
    from docx import Document
    from reporting.models import adapt_snapshot
    from reporting.word_renderer import render_word
    w=shell;c,f=sea(w);module='suction_npsh';page=w._pages[module]
    c.select_fluid(module,f.id,20,35,.101325)
    for name in ('density','kinematic_viscosity'):
        if c.links[module][name].stale:c.action(module,name,'reference')
    for key,value in dict(diameter='100',flow='20',length='10',roughness='.015',pressure='1.2',vapour='.03',height='2',required='3').items():
        page._fields[key].set(value)
    page._fields['density'].set('1030')
    page._calculate_suction_loss();page._calculate_enpy()
    assert page._last_loss and page._last_enpy
    snapshot=page._pdf_snapshot
    basis=json.loads(snapshot.formula_steps[0].engineering_basis_json)
    density=next(v for v in basis['values'] if v['reference']['property_name']=='density')
    assert density['used_value']==1030 and density['is_override']
    assert density['reference']['default_value']==1024.9
    assert any(v.is_overridden for s in snapshot.formula_steps for v in s.used_values if v.symbol=='ρ')
    viscosity=next(v for v in basis['values'] if v['reference']['property_name']=='kinematic_viscosity')
    assert viscosity['used_value']==pytest.approx(1.05)
    assert viscosity['status']=='LINKED' and not viscosity['is_override']
    assert any(v.value==pytest.approx(1.05e-6) for s in snapshot.formula_steps for v in s.variables if v.symbol=='ν')
    frozen=snapshot.to_json();report=adapt_snapshot(snapshot)
    doc=Document(BytesIO(render_word(report)))
    text='\n'.join(p.text for p in doc.paragraphs)+'\n'+'\n'.join(cell.text for table in doc.tables for row in table.rows for cell in row.cells)
    assert '0,101325' in text and '2023-12-09' in text and '1030' in text.replace(' ','')
    c.select_fluid(module,f.id,21,35,.101325)
    assert c.links[module]['density'].stale
    summary=w._refresh_warning_center()
    assert any(item.module_id==module and item.severity.value=='STALE' for item in summary.items)
    assert CalculationSnapshot.from_payload(json.loads(frozen)).to_json()==frozen
    assert adapt_snapshot(snapshot)==report


def test_legacy_manual_project_without_fluid_still_calculates(shell):
    w=shell;assert w._create_project('Legacy '+str(uuid4()),'','','fuel')
    page=w._pages['discharge_head_loss']
    assert w._system_context.fluid is None
    for key,value in dict(d='100',q='20',nu='4',l='10',k='.015',h='2').items():page._fields[key].set(value)
    page._calculate()
    assert page._last_result


def test_fluid_reset_does_not_accept_pending_roughness_or_reset_material_context(shell):
    from dataclasses import replace
    from engineering.catalog_seeds import identity
    w=shell;c,f=sea(w);module='discharge_head_loss';page=w._pages[module]
    surface_id=identity('surface:CARBON_NEW')
    c.set_module_context(module,c.context_for(module).changed(surface_profile_id=surface_id))
    page._fields['k'].set('.12345')
    original=c.links[module]['absolute_roughness'].reference
    c.catalog.surface_records=tuple(replace(r,roughness_mm=.1) if r.id==surface_id else r for r in c.catalog.surface_records)
    c.observe()
    assert c.links[module]['absolute_roughness'].stale
    c.select_fluid(module,f.id,20,35,.101325)
    c.use_project_fluid(module)
    assert c.context_for(module).surface_profile_id==surface_id
    assert c.links[module]['absolute_roughness'].reference==original
    assert c.links[module]['absolute_roughness'].stale
    assert page._fields['k'].get()=='.12345'
    c.catalog.reload()


@pytest.mark.parametrize('code',['F76','F44'])
def test_project_fuel_selection_does_not_seed_operating_midpoints(shell,code):
    from .test_project_engineering_context import chosen
    w=shell;assert w._create_project('Fuel conditions '+str(uuid4()),'','','fuel')
    c=w._engineering_context_controller;c.apply(chosen(c.catalog,fuel=code))
    project=w._system_context
    for module in ('discharge_head_loss','suction_npsh'):
        for name in ('density','kinematic_viscosity'):
            assert c.read(module,name) is None
            assert c.links[module][name].reference['default_value'] is None
            assert c.links[module][name].status=='SOURCE_REQUIRED'
    other=c.catalog.completion.resolve_fluid('F44' if code=='F76' else 'F76')
    page=w._pages['discharge_head_loss'];page._fields['nu'].set('4')
    c.select_fluid('discharge_head_loss',other.id,20,None,.101325)
    assert c.context_for('discharge_head_loss').fluid_id==other.id
    assert c.read('discharge_head_loss','kinematic_viscosity')==4
    assert not c.links['discharge_head_loss']['kinematic_viscosity'].overridden
    assert w._system_context==project


def test_fire_fluid_filter_uses_only_supported_water(shell):
    w=shell;assert w._create_project('Fire fluids '+str(uuid4()),'','','fire')
    c=w._engineering_context_controller;water=c.catalog.completion.resolve_fluid('WATER')
    fuel=c.catalog.completion.resolve_fluid('F76')
    for module in ('discharge_head_loss','suction_npsh'):
        assert set(w._pages[module]._engineering_panel.fluid_choices.values())=={water.id}
        with pytest.raises(ValueError):c.select_fluid(module,fuel.id,20,None,.101325)
