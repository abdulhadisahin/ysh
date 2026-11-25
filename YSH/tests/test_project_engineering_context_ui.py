"""Native project-context inheritance and frozen engineering-basis integration."""
from uuid import uuid4
import json
import pytest
from dataclasses import replace
from .test_fire_phase5cd_navigation import application, shell
from .test_project_engineering_context import chosen
from ._tk_geometry import settle_geometry
from engineering.catalog_seeds import identity
from i18n.messages_tr import MESSAGES as TR
from i18n.messages_en import MESSAGES as EN


def project(w):
    assert w._create_project('Engineering '+str(uuid4()), '', '', 'fuel')
    return w._engineering_context_controller


def test_context_applies_only_empty_fields_and_explicit_updates(shell):
    w=shell;c=project(w);page=w._pages['discharge_head_loss']
    page._fields['nu'].set('');page._fields['k'].set('')
    context=chosen(c.catalog)
    c.apply(context)
    assert c.read('discharge_head_loss','kinematic_viscosity') is None
    assert c.links['discharge_head_loss']['kinematic_viscosity'].status=='SOURCE_REQUIRED'
    assert c.read('discharge_head_loss','absolute_roughness')==.045
    page._fields['k'].set('.1')
    assert c.links['discharge_head_loss']['absolute_roughness'].status=='OVERRIDE'
    assert json.loads(w._system_context.engineering_defaults_json)=={}
    c.apply(context.changed(surface_profile_id=identity('surface:STAINLESS_NEW')))
    assert c.read('discharge_head_loss','absolute_roughness')==.1
    assert c.links['discharge_head_loss']['absolute_roughness'].status=='STALE'
    c.action('discharge_head_loss','absolute_roughness','keep')
    assert c.read('discharge_head_loss','absolute_roughness')==.1
    c.action('discharge_head_loss','absolute_roughness','update')
    assert c.read('discharge_head_loss','absolute_roughness')==.1
    assert c.links['discharge_head_loss']['absolute_roughness'].status=='OVERRIDE'
    c.action('discharge_head_loss','absolute_roughness','reference')
    assert c.read('discharge_head_loss','absolute_roughness')==.015
    assert c.links['discharge_head_loss']['absolute_roughness'].status=='LINKED'


def test_project_defaults_roundtrip_and_calculation_overrides_are_local(shell):
    w=shell;c=project(w);c.apply(chosen(c.catalog))
    page=w._pages['discharge_head_loss'];page._fields['k'].set('.1')
    assert c.catalog.references(w._system_context)['absolute_roughness']['default_value']==.045
    c.action('discharge_head_loss','absolute_roughness','project')
    assert c.catalog.references(w._system_context)['absolute_roughness']['default_value']==.1
    state=w._export_all_page_states();service=w._project_persistence_service
    service.save(state);identifier=w._active_project.id
    reopened,_=service.open(identifier)
    w._activate_project(reopened);w._root.update()
    assert w._locked_project_family()=='fuel'
    assert w._system_context.fluid.code=='F76'
    assert w._engineering_context_controller.read('discharge_head_loss','absolute_roughness')==.1
    assert w._export_all_page_states()['engineering_links']==state['engineering_links']


@pytest.mark.parametrize('size',[(1100,700),(1440,900)])
@pytest.mark.parametrize('language',['tr','en'])
def test_context_dialog_geometry_and_localized_contract(shell,size,language):
    from ui.dialogs.project_engineering_context import ProjectEngineeringContextDialog
    from i18n.translator import Translator
    w=shell;c=project(w);c.apply(chosen(c.catalog));old=w._translate
    w._translate=Translator(language).translate
    dialog=None
    try:
        root=w._root;root.deiconify();root.geometry(f'{size[0]}x{size[1]}')
        dialog=ProjectEngineeringContextDialog(w);settle_geometry(root,dialog.window,dialog.tree)
        for widget in dialog.window.winfo_children():
            assert widget.winfo_x()>=0
            assert widget.winfo_x()+widget.winfo_width()<=dialog.window.winfo_width()
        assert dialog.window.winfo_width()<=size[0] and dialog.window.winfo_height()<=size[1]
        assert 'system_family' not in dialog.variables
        assert len(dialog.tree.get_children())==6
    finally:
        if dialog:dialog.window.destroy()
        w._translate=old


def test_engineering_localization_keys_are_paired():
    keys={key for key in TR if key.startswith('engineering.')}
    assert keys=={key for key in EN if key.startswith('engineering.')}
    for key in keys:assert TR[key] and EN[key] and TR[key]!=key and EN[key]!=key

def test_calculation_freezes_actual_values_and_old_reports_ignore_library(shell,monkeypatch,tmp_path):
    from reporting.models import adapt_snapshot
    from reporting.renderer import render_pdf
    from ui.widgets.formula_steps import step_sections
    from io import BytesIO
    from pypdf import PdfReader
    w=shell;c=project(w);page=w._pages['discharge_head_loss']
    # Capture must fail this test immediately instead of opening a modal error.
    def fail(*args,**kwargs):pytest.fail('Snapshot capture failed')
    monkeypatch.setattr('ui.main_window.messagebox.showerror',fail)
    page._fields['nu'].set('');page._fields['k'].set('')
    c.apply(chosen(c.catalog))
    # Reconstruct a pre-v8 saved source link. Loading must retain it, while a
    # new calculation must flag its specification midpoint as stale operating data.
    from services.engineering_value_links import bind
    legacy={'version':1,'links':{'discharge_head_loss':{
        'kinematic_viscosity':bind(c.catalog.references(w._system_context)['kinematic_viscosity'],4).payload(),
        'absolute_roughness':c.links['discharge_head_loss']['absolute_roughness'].payload()}}}
    c.load(legacy)
    for key,value in {'d':'100','q':'25','l':'10','h':'5','nu':'4'}.items():page._fields[key].set(value)
    page._calculate();w._root.update()
    assert page._last_result
    snapshot=page._pdf_snapshot
    assert snapshot and w._pdf_is_current(page)
    basis=json.loads(snapshot.formula_steps[0].engineering_basis_json)
    value=next(v for v in basis['values'] if v['reference']['property_name']=='kinematic_viscosity')
    assert value['reference']['source_min']==1.7 and value['reference']['source_max']==4.3
    assert value['reference']['default_value']==3 and value['used_value']==4
    assert value['reference']['default_method']=='DERIVED_MIDPOINT' and value['status']=='STALE'
    assert value['is_override'] and value['pending']['verification']=='SOURCE_REQUIRED'
    assert value['reference']['source_document']=='MIL-DTL-16884R'
    assert any(s.key=='engineering_basis' for s in step_sections(snapshot.formula_steps[0],w._translate))
    report=adapt_snapshot(snapshot,language='en')
    assert report.engineering_basis_json==snapshot.formula_steps[0].engineering_basis_json
    roughness=next(row for row in report.inputs if row.symbol=='k')
    assert roughness.source==EN['source.state.library']
    pdf=render_pdf(report)
    (tmp_path/"engineering-basis.pdf").write_bytes(pdf)
    text='\n'.join(p.extract_text() for p in PdfReader(BytesIO(pdf)).pages)
    assert 'MIL-DTL-16884R' in text and '1.7' in text and '4.3' in text
    assert EN['engineering.method.DERIVED_MIDPOINT'] in text
    assert EN['engineering.status.STALE'] in text
    assert any(v.source.source_type.value=='USER_INPUT' and not v.is_overridden for step in snapshot.formula_steps for v in step.used_values if v.symbol=='ν')
    frozen=snapshot.evidence_json
    c.catalog.property_records=tuple(replace(r,default_value=900,default_method='USER_DEFINED') if r.property_name=='density' else r for r in c.catalog.property_records)
    assert adapt_snapshot(snapshot,language='en')==report and snapshot.evidence_json==frozen
    c.apply(w._system_context.changed(surface_profile_id=identity('surface:STAINLESS_NEW')))
    assert not w._pdf_is_current(page)

def test_fire_rule_is_scope_specific_and_frozen_in_center(shell):
    from .test_fire_phase5_live_ui import fill_view
    from services.engineering_warning_center import WarningStatus
    from engineering.fire.hazen_williams_workflow import HWService
    w=shell;assert w._create_project('Fire basis '+str(uuid4()),'','','fire')
    c=w._engineering_context_controller
    context=chosen(c.catalog,fuel='WATER',profile='TL_FFS',line='DELIVERY')
    c.apply(context)
    assert w._fire_workspace.model.service is HWService.WATER
    view=w._fire_workspace.views['hw']
    # Q/Di yields just over 4 m/s; this is not a universal TL requirement.
    fill_view(view,('2000','100','150','120'));view.calculate()
    snapshot=w._fire_workspace.model.snapshots['hw']
    assert snapshot and not json.loads(snapshot.formula_steps[0].engineering_basis_json)['rules']
    c.apply(context.changed(applicability_scope='TL_FFS'))
    assert w._fire_workspace.model.results['hw'] is None
    view.calculate()
    snapshot=w._fire_workspace.model.snapshots['hw']
    assert snapshot
    basis=json.loads(snapshot.formula_steps[0].engineering_basis_json)
    rule=next(r for r in basis['rules'] if r['code']=='TL_FFS_DELIVERY')
    assert rule['status']=='OUT_OF_RANGE' and rule['applicability']=='TL_FFS'
    matches=[i for i in w._refresh_warning_center().items if i.code=='engineering.rule.TL_FFS_DELIVERY']
    assert len(matches)==1 and matches[0].severity is WarningStatus.OUT_OF_RANGE
    frozen=snapshot.evidence_json
    c.catalog.rule_records=tuple(replace(r,hard_max=5) if r.code=='TL_FFS_DELIVERY' else r for r in c.catalog.rule_records)
    c.observe()
    assert w._fire_workspace.model.results['hw'] is None
    assert not view.formula._post_pdf_available()
    assert snapshot.evidence_json==frozen
    c.catalog.reload()
