"""Semantic live UI tests; no pixel coordinates and no alternative engineering formulas."""
from dataclasses import replace
from io import BytesIO
from types import SimpleNamespace
from uuid import UUID
import json
from pathlib import Path

import pytest
from pypdf import PdfReader

from engineering.fire.hazen_williams_workflow import HWService
from engineering.fire.enums import FireSourceStatus
from engineering.pipe_design.transfer import PipeInputMode, revise_selection
from engineering.snapshots.models import CalculationSnapshot
from engineering.system_context import SystemContext, ContextReference
from engineering.validation import ValidationError
from i18n.translator import Translator
from services.fire_workspace import FireWorkspace, FOAM_FIELDS, HW_FIELDS
from services.fire_hazen_williams_service import HWApplicabilityBlocked
from services.pipe_source_discovery import PipeSourceDiscovery
from ui.pages.fire_workspace_page import FireWorkspacePage
from .test_fire_phase3_hazen_williams_workflow import selection


def foam(draft,area='210',percent='3'):
    for key,value in zip(FOAM_FIELDS,(area,'5','30',percent)):draft.set_field('foam',key,value)


def hw(draft,c='120'):
    for key,value in zip(HW_FIELDS,('2000','105','150',c)):draft.set_field('hw',key,value)
    draft.service=HWService.WATER


def test_initial_drafts_have_no_engineering_defaults_or_results():
    draft=FireWorkspace()
    assert all(not value for fields in draft.fields.values() for value in fields.values())
    assert draft.results=={'foam':None,'hw':None}
    assert draft.service is HWService.UNKNOWN and draft.mode is PipeInputMode.MANUAL


@pytest.mark.parametrize('area,expected',[('210',(1050,31.5,1018.5,945)),('1660',(8300,249,8051,7470))])
def test_foam_live_normalization_and_frozen_snapshots(area,expected):
    draft=FireWorkspace();foam(draft,area)
    result=draft.calculate('foam')
    d=result.domain_result
    assert (d.solution_flow_lpm,d.foam_concentrate_flow_lpm,d.water_flow_lpm,d.foam_concentrate_volume_l)==expected
    assert d.input.foam_fraction==.03
    assert result.snapshot_payload['raw_inputs']['foam_fraction']['value']==3
    snapshot=draft.snapshots['foam'];before=snapshot.to_json()
    draft.set_field('foam','protected_area_m2','300')
    assert draft.results['foam'] is None and draft.snapshots['foam'] is None
    assert snapshot.to_json()==before


def test_foam_percent_override_and_reason_requirement():
    draft=FireWorkspace();foam(draft,percent='6,00')
    meta=draft.metadata['foam']['foam_fraction'];meta.update(recommended='3',reason='Project-selected approved concentrate')
    result=draft.calculate('foam')
    assert result.domain_result.foam_concentrate_volume_l==1890
    item=result.input_provenance[-1].engineering_value
    assert (item.used_value,item.recommended_value,item.override_reason)==(.06,.03,'Project-selected approved concentrate')
    meta['reason']=''
    with pytest.raises(ValidationError):draft.calculate('foam')


@pytest.mark.parametrize('field,value',[('protected_area_m2','0'),('application_density_lpm_m2','-1'),
    ('application_duration_min','0'),('foam_fraction','0'),('foam_fraction','100'),('foam_fraction','101'),
    ('protected_area_m2',''),('foam_fraction','NaN')])
def test_invalid_foam_input_is_rejected(field,value):
    draft=FireWorkspace();foam(draft);draft.set_field('foam',field,value)
    with pytest.raises(ValidationError):draft.calculate('foam')
    assert draft.snapshots['foam'] is None


@pytest.mark.parametrize('c,expected',[('120',2.3717829024660286),('140',1.7832957445009588)])
def test_hw_live_reference_source_required(c,expected):
    draft=FireWorkspace();hw(draft,c)
    result=draft.calculate('hw')
    assert result.domain_result.total_pressure_loss_bar==pytest.approx(expected,rel=1e-13)
    assert result.input_provenance[-1].source_status is FireSourceStatus.SOURCE_REQUIRED
    assert any(w.source_status is FireSourceStatus.SOURCE_REQUIRED for w in result.warnings)


@pytest.mark.parametrize('service',[HWService.SEAWATER,HWService.FUEL,HWService.UNKNOWN])
def test_service_blocked_before_workflow(service,monkeypatch):
    draft=FireWorkspace();hw(draft);draft.service=service
    monkeypatch.setattr('services.fire_workspace.HazenWilliamsCalculationService.calculate',lambda *a:pytest.fail('blocked'))
    with pytest.raises(HWApplicabilityBlocked):draft.calculate('hw')
    assert draft.results['hw'] is None


@pytest.mark.parametrize('code',['SEAWATER','FUEL','OIL','UNKNOWN'])
def test_context_cannot_silently_use_water(code):
    draft=FireWorkspace();hw(draft)
    draft.context=SystemContext(fluid=ContextReference(id=UUID(int=7),code=code,name_tr=code))
    with pytest.raises(HWApplicabilityBlocked):draft.calculate('hw')


def test_linked_missing_manual_linked_equality_stale_update_keep():
    draft=FireWorkspace();hw(draft);draft.mode=PipeInputMode.LINKED
    with pytest.raises(ValidationError):draft.calculate('hw')
    original=selection();draft.use_pipe(original)
    result=draft.calculate('hw');di=result.domain_result.input.inside_diameter_mm
    assert di==105 and draft.pipe.snapshot.source_revision==3
    manual=FireWorkspace();hw(manual)
    manual.fields['hw']['flow_lpm']=draft.fields['hw']['flow_lpm']
    assert manual.calculate('hw').domain_result.total_pressure_loss_bar==result.domain_result.total_pressure_loss_bar
    revised=revise_selection(original,replace(original,flow_rate_m3_h=180))
    draft.observe(revised)
    assert draft.results['hw'] is None
    assert draft.pipe.snapshot.source_revision==3 and draft.pipe.observed_revision==4
    draft.use_pipe(revised,'keep');assert draft.pipe.kept_current
    assert draft.calculate('hw').domain_result.total_pressure_loss_bar==result.domain_result.total_pressure_loss_bar
    draft.use_pipe(revised,'update');assert draft.pipe.snapshot.source_revision==4


def test_project_state_roundtrip_has_no_results_or_widget_objects():
    draft=FireWorkspace();foam(draft);hw(draft);draft.use_pipe(selection());draft.active='hw'
    draft.metadata['foam']['foam_fraction'].update(recommended='3',reason='saved reason')
    payload=draft.export_state();restored=FireWorkspace.from_state(json.loads(json.dumps(payload)))
    assert restored.export_state()==payload
    assert restored.results=={'foam':None,'hw':None}
    assert restored.pipe==draft.pipe
    payload['fields']['foam']['foam_fraction']='99'
    assert draft.fields['foam']['foam_fraction']=='3'
    with pytest.raises(ValueError):FireWorkspace.from_state({'version':2})


@pytest.fixture
def live():
    import tkinter as tk
    root=tk.Tk();root.withdraw();saved=[];sources=PipeSourceDiscovery()
    translator=Translator('tr')
    page=FireWorkspacePage(root,translator.translate,sources=sources,context=lambda:SystemContext(),
        project=lambda:None,on_snapshot=saved.append,on_dirty=lambda:None)
    page.pack(fill='both',expand=True);root.update_idletasks()
    yield root,page,saved,translator
    root.destroy()


def fill_view(view,values):
    for key,value in zip(view.spec,values):view.variables[key].set(value)


def test_real_foam_widgets_empty_calculate_results_actions_stale_reset(live,monkeypatch):
    root,page,saved,tr=live;view=page.views['foam']
    assert all(v.get()=='' for v in view.variables.values())
    assert str(view.pdf_button['state'])=='disabled'
    fill_view(view,('210','5','30','3'));view.calculate()
    assert len(saved)==1 and page.model.results['foam'].domain_result.foam_concentrate_volume_l==945
    assert '945,00' in view.result_labels[0]['text']
    assert len(view.steps())==4
    view.formula.toggle();root.update_idletasks();assert view.formula.expanded
    import ui.dialogs.pdf_report as pdf
    seen=[];monkeypatch.setattr(pdf,'save_snapshot_pdf',lambda parent,snapshot:seen.append(snapshot))
    view.pdf();assert seen==saved
    view.variables['foam_fraction'].set('6')
    assert str(view.pdf_button['state'])=='disabled' and not view.steps()
    assert not view.formula.expanded and 'değişti' in view.status['text']
    view.pdf();assert len(seen)==1
    view.clear();assert all(not v.get() for v in view.variables.values())
    assert saved[0].formula_steps[-1].result_value==945


def test_real_hw_widgets_service_and_linked_state(live):
    root,page,saved,tr=live;view=page.views['hw']
    fill_view(view,('2000','105','150','120'))
    view.calculate();assert not saved and 'kapsam' in view.status['text']
    view.service_var.set(tr.translate('fire.value.WATER'));view._service();view.calculate()
    assert len(view.steps())==2 and saved[-1].formula_steps[-1].result_value==pytest.approx(2.3717829024660286)
    page.sources.publish(selection());view.pipe_action('link')
    assert str(view.entries['inside_diameter_mm']['state'])=='readonly'
    assert '3' in view.pipe_status['text']
    view.calculate();assert page.model.results['hw'] is not None
    view.service_var.set(tr.translate('fire.value.SEAWATER'));view._service();view.calculate()
    assert page.model.results['hw'] is None and str(view.pdf_button['state'])=='disabled'


@pytest.mark.parametrize('kind',['foam','hw'])
def test_live_to_pdf_history_frozen_values(kind,live):
    from reporting.models import adapt_snapshot
    from reporting.renderer import render_pdf
    from ui.history_presentation import primary_result
    root,page,saved,tr=live
    view=page.views[kind]
    if kind=='foam':fill_view(view,('210','5','30','3'))
    else:
        fill_view(view,('2000','105','150','120'));page.model.service=HWService.WATER
    view.calculate();snapshot=CalculationSnapshot.from_payload(saved[-1].to_payload())
    expected=snapshot.to_json()
    next(iter(view.variables.values())).set('999')
    assert snapshot.to_json()==expected
    report=adapt_snapshot(snapshot);text='\n'.join(p.extract_text() for p in PdfReader(BytesIO(render_pdf(report))).pages)
    assert 'Yangın Söndürme' in text and ('945,00' if kind=='foam' else '2,37') in text
    assert primary_result(snapshot.module_code,snapshot.evidence).startswith('Vfoam' if kind=='foam' else 'ΔpHW')


def test_localization_subview_and_project_load(live):
    root,page,saved,tr=live
    original=id(page.views['foam'])
    page.host.select(page.host._page_keys['hw']);root.update()
    assert page.model.active=='hw'
    fill_view(page.views['foam'],('210','5','30','3'))
    state=page.export_state();page.clear_state();page.load_state(state)
    assert page.model.active=='hw' and page.views['foam'].variables['protected_area_m2'].get()=='210'
    assert id(page.views['foam'])==original
    from i18n.messages_en import MESSAGES as EN
    from i18n.messages_tr import MESSAGES as TR
    assert all(key in EN for key in TR if key.startswith('fire.ui.'))
    en=Translator('en').translate;page.tr=en
    for view in page.views.values():view.tr=en
    page.refresh_texts()
    assert page.title['text']=='Fire Fighting'
    assert page.views['foam'].calculate_button['text']=='Calculate'


def test_no_engineering_equations_assets_or_workbook_access_in_new_ui():
    source=(Path(__file__).parents[1]/'ui/pages/fire_workspace_page.py').read_text(encoding='utf-8')
    assert not any(text in source for text in ('605000','1.85','4.87','openpyxl','.xlsx','watermark'))


@pytest.mark.parametrize('size',[(1100,700),(1280,800),(1440,900),(1700,1000)])
def test_window_sizes_keep_fields_and_actions_inside_scroll_viewport(live,size):
    root,page,saved,tr=live
    root.deiconify();root.geometry(f'{size[0]}x{size[1]}')
    # Reserve the existing shell sidebar width to exercise the narrow content case.
    page.pack_forget();page.place(x=320,y=110,width=size[0]-320,height=size[1]-140)
    root.update()
    for kind,view in page.views.items():
        page.host.select(page.host._page_keys[kind]);root.update()
        canvas=page.host._page_keys[kind].canvas
        edge=canvas.winfo_rootx()+canvas.winfo_width()
        for widget in list(view.entries.values())+[view.calculate_button,view.pdf_button]:
            assert widget.winfo_rootx()+widget.winfo_width()<=edge+2
        assert view.winfo_reqheight()>0 and canvas.cget('scrollregion')


def test_cached_family_navigation_and_shell_state_namespace(live):
    from ui.main_window import MainWindow
    root,page,saved,tr=live
    # Use the real shell method with existing host/page objects and optional services.
    shell=SimpleNamespace(_fire_workspace=page,_page_host=page.host,_family='existing',
        _context_panel=object(),_pages={},_fire_pending_state={},_system_context=SystemContext())
    for _ in range(3):
        MainWindow._show_family(shell,'fire');MainWindow._show_family(shell,'existing')
    assert shell._fire_workspace is page
    state=MainWindow._export_all_page_states(shell)
    assert state['fire_workspace']['version']==1 and state['schema_version']==1
    assert len(page.views)==2


def test_project_save_preserves_fire_namespace_without_second_store(project_database):
    from repositories.project_repository import ProjectRepository
    from repositories.project_state_repository import ProjectStateRepository
    from services.project_service import ProjectService
    from services.project_persistence_service import ProjectPersistenceService
    service=ProjectPersistenceService(ProjectService(ProjectRepository(project_database)),ProjectStateRepository(project_database))
    project=service.create_project('Fire namespace')
    draft=FireWorkspace();foam(draft)
    service.save({'schema_version':1,'fire_workspace':draft.export_state()})
    service.save({'schema_version':1,'pipe_design':{}})
    _,state=service.open(project.id)
    assert FireWorkspace.from_state(state['fire_workspace']).fields['foam']['protected_area_m2']=='210'
