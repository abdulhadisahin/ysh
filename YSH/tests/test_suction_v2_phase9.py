"""Phase 9 discovery, suction/ENPY numerical freeze and display-free page workflows."""
from dataclasses import fields, replace
import json
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

from core.local_loss_item import LocalLossItem
from engineering.head_loss.models import DischargeHeadLossResult
from engineering.head_loss.v2_models import DischargeLocalLoss
from engineering.pipe_design.transfer import PipeInputMode, PipeLinkStatus, PipeInputState, PipeTransferProjectState, PipeValues
from engineering.pipe_design.transfer import revise_selection
from engineering.pipe_design.transfer_serialization import transfer_to_dict, transfer_from_dict
from engineering.suction_npsh.models import SuctionNPSHResult
from engineering.suction_npsh.v2_models import ENPYV2Input, SuctionV2Input, SuctionV2Result
from engineering.validation import ValidationError
from i18n.translator import Translator
from services.discharge_workflow import DischargeWorkflow
from services.pipe_source_discovery import PipeSourceDiscovery
from services.suction_workflow import SuctionWorkflow
from services.suction_npsh_service import SuctionNPSHService
from services.pipe_design_service import PipeDesignService
from ui.pages.suction_npsh_page import SuctionNPSHPage
from ui.pages.pipe_design_page import PipeDesignPage
from ui.main_window import MainWindow
from .test_discharge_v2_phase8 import source, revised, page_stub, panel_stub, Var, Widget


def suction_input(pipe: PipeInputState | None = None, **changes: object) -> SuctionV2Input:
    """Synthetic representative hydraulics with independent local inputs."""
    return SuctionV2Input(**(dict(pipe_input=pipe or PipeInputState(manual_values=PipeValues(
        actual_internal_diameter_mm=101,flow_rate_m3_h=20)),viscosity=2,viscosity_unit='cSt',
        pipe_length_m=20,roughness_mm=.015,local_losses=(DischargeLocalLoss('test',2,.5),)) | changes))


def enpy_input(**changes: object) -> ENPYV2Input:
    """Absolute PE/Pb, signed HEgeo and optional external manufacturer NPSHr."""
    return ENPYV2Input(**(dict(suction_pressure=1.2,suction_pressure_unit='bar',
        vapour_pressure=.03,vapour_pressure_unit='bar',density_kg_m3=850,
        static_suction_height_m=2,npsh_required_m=3) | changes))


def flow() -> SuctionWorkflow:
    """Create a linked suction state through an explicit source choice."""
    result=SuctionWorkflow();result.publish(source());result.link(source().selection_id)
    return result


def numeric(value: object, target: type) -> dict[str, object]:
    """Compare all existing numeric results/warnings independently of extra source metadata."""
    return {f.name:getattr(value,f.name) for f in fields(target) if f.name!='metadata'}


@pytest.mark.parametrize('count',[0,1,3])
def test_discovery_is_automatic_pure_and_does_not_link(count: int) -> None:
    """Read current project results repeatedly without mutation, revision changes or linkage."""
    selections=tuple(source(selection_id=uuid4()) for _ in range(count))
    discovery=PipeSourceDiscovery(PipeTransferProjectState(selections=selections))
    before=transfer_to_dict(discovery.state)
    for _ in range(5):
        assert discovery.available()==selections
        assert transfer_to_dict(discovery.state)==before
    assert discovery.state.discharge.mode is discovery.state.suction.mode is PipeInputMode.MANUAL
    assert all(s.revision==1 for s in selections)


@pytest.mark.parametrize('bad',[
    source(selected_pipe=None),source(flow_rate_m3_h=0),source(flow_rate_m3_h=float('nan')),
    source(flow_rate_m3_h=True),source(flow_rate_m3_h=-1),
])
def test_incomplete_invalid_sources_are_not_selectable(bad: object) -> None:
    """Provisional real geometry is usable, but invalid hydraulic values are never fabricated."""
    discovery=PipeSourceDiscovery(PipeTransferProjectState(selections=(bad,)))
    assert discovery.available()==()
    owner=SuctionWorkflow(discovery=discovery)
    with pytest.raises(ValueError): owner.link(bad.selection_id)


def test_shared_discovery_updates_status_only_for_both_owners() -> None:
    """No duplicate registry and no silent Q/Di propagation into Basma or Emme."""
    discovery=PipeSourceDiscovery()
    discharge=DischargeWorkflow(discovery=discovery);suction=SuctionWorkflow(discovery=discovery)
    events=[];discovery.subscribe(lambda:events.append('observe'))
    discovery.publish(source())
    discharge.link(source().selection_id);suction.link(source().selection_id)
    d,s=discharge.pipe_input.snapshot,suction.pipe_input.snapshot
    discovery.publish(revised(source()))
    assert discharge.pipe_input.status is suction.pipe_input.status is PipeLinkStatus.LINKED_STALE
    assert discharge.pipe_input.snapshot is d and suction.pipe_input.snapshot is s
    assert events==['observe','observe']
    suction.keep_current()
    assert suction.pipe_input.kept_current and not discharge.pipe_input.kept_current
    suction.update()
    assert suction.pipe_input.used_values.hydraulic_values()==(99,30)
    assert discharge.pipe_input.used_values.hydraulic_values()==(101,20)
    assert suction.state is discharge.state is discovery.state


@pytest.mark.parametrize('mode',['manual','linked','stale','kept','missing','detached'])
@pytest.mark.parametrize('height',[-2,0,2,30])
@pytest.mark.parametrize('required',[None,15])
def test_manual_linked_hydraulics_enpy_match_existing_results(mode: str,height: float,required: float | None) -> None:
    """Preserve every legacy hydraulic/ENPY output with all applied-source states."""
    owner=flow()
    if mode in ('stale','kept'): owner.publish(revised(source()))
    if mode=='kept': owner.keep_current()
    if mode=='missing': owner.remove(source().selection_id)
    if mode in ('manual','detached'): owner.manual()
    service=SuctionNPSHService(object())
    request=suction_input(owner.pipe_input)
    enpy=enpy_input(static_suction_height_m=height,npsh_required_m=required)
    loss=service.calculate_suction_loss_v2(request)
    result=service.calculate_enpy_v2(loss,enpy)
    legacy_loss=service.calculate_suction_loss(101,20,2,'cSt',20,.015,[LocalLossItem('test',2,.5)])
    legacy=service.calculate_enpy(legacy_loss.total_hydraulic_loss_m,1.2,'bar',.03,'bar',850,height,required)
    assert numeric(loss,DischargeHeadLossResult)==numeric(legacy_loss,DischargeHeadLossResult)
    assert numeric(result,SuctionNPSHResult)==numeric(legacy,SuctionNPSHResult)
    assert result.hydraulic is loss
    assert (result.flow_rate_m3_h,result.actual_internal_diameter_mm)==(20,101)
    assert result.actual_internal_diameter_mm!=source().theoretical_internal_diameter_mm
    assert result.input==enpy
    assert result.hydraulic.input.pipe_input==owner.pipe_input
    assert result.metadata['pipe_transfer']['mode']==owner.pipe_input.mode.value
    assert result.suction_loss_m==result.suction_line_loss_m==loss.total_hydraulic_loss_m
    combined=service.calculate_v2(request,enpy)
    old_combined=service.calculate(101,20,2,'cSt',20,.015,[LocalLossItem('test',2,.5)],1.2,'bar',.03,'bar',850,height,required)
    assert numeric(combined,SuctionNPSHResult)==numeric(old_combined,SuctionNPSHResult)


@pytest.mark.parametrize('unit,pe,pb',[('Pa',120000,3000),('kPa',120,3),('bar',1.2,.03)])
@pytest.mark.parametrize('density',[850,1000])
def test_pressure_units_density_and_hegeo_semantics_unchanged(unit: str,pe: float,pb: float,density: float) -> None:
    """Absolute pressure conversion and signed subtraction stay in the existing service/core."""
    service=SuctionNPSHService(object())
    request=enpy_input(suction_pressure=pe,suction_pressure_unit=unit,
        vapour_pressure=pb,vapour_pressure_unit=unit,density_kg_m3=density)
    result=service.calculate_v2(suction_input(),request)
    legacy=service.calculate(101,20,2,'cSt',20,.015,[LocalLossItem('test',2,.5)],pe,unit,pb,unit,density,2,3)
    assert numeric(result,SuctionNPSHResult)==numeric(legacy,SuctionNPSHResult)
    assert result.metadata['suction_pressure_pa']==120000
    assert result.metadata['vapour_pressure_pa']==3000


def test_no_automatic_one_metre_margin_and_enpy_has_one_arithmetic_source(monkeypatch) -> None:
    """An available margin of 0.5 m remains positive without invented extra requirements."""
    from engineering.suction_npsh.calculator import SuctionNPSHCalculator
    original=SuctionNPSHCalculator.calculate_enpy
    calls=[]
    def counted(self,value):
        calls.append(value)
        return original(self,value)
    monkeypatch.setattr(SuctionNPSHCalculator,'calculate_enpy',counted)
    service=SuctionNPSHService(object())
    loss=service.calculate_suction_loss_v2(suction_input())
    available=service.calculate_enpy_v2(loss,enpy_input(npsh_required_m=None))
    result=service.calculate_enpy_v2(loss,enpy_input(npsh_required_m=available.enpym_available_m-.5))
    assert len(calls)==2
    assert result.npsh_margin_m==pytest.approx(.5)
    assert not any(w.code=='npsh_below_required' for w in result.warnings)


@pytest.mark.parametrize('q,regime',[(.1,'Laminar'),(.85,'Transitional'),(20,'Turbulent')])
def test_flow_regimes_and_colebrook_preserved(q: float,regime: str) -> None:
    """V/Re/f match the core for laminar, transitional and turbulent flow."""
    pipe=PipeInputState(manual_values=PipeValues(actual_internal_diameter_mm=100,flow_rate_m3_h=q))
    service=SuctionNPSHService(object())
    result=service.calculate_suction_loss_v2(suction_input(pipe,viscosity=1))
    old=service.calculate_suction_loss(100,q,1,'cSt',20,.015,[LocalLossItem('test',2,.5)])
    assert numeric(result,DischargeHeadLossResult)==numeric(old,DischargeHeadLossResult)
    assert result.flow_regime==regime
    if regime=='Laminar': assert result.friction_factor==64/result.reynolds_number


def test_suction_d5_d4_exponents_preserved() -> None:
    """Isolate D^5 by normalizing pipe loss by the computed f; local loss remains D^4."""
    service=SuctionNPSHService(object())
    results=[service.calculate_suction_loss_v2(suction_input(PipeInputState(manual_values=PipeValues(
        actual_internal_diameter_mm=d,flow_rate_m3_h=20)))) for d in (100,200)]
    a,b=results
    assert (a.pipe_friction_loss_m/a.friction_factor)/(b.pipe_friction_loss_m/b.friction_factor)==pytest.approx(32)
    assert a.local_loss_m/b.local_loss_m==pytest.approx(16)


@pytest.mark.parametrize('field,bad',[
    ('flow_rate_m3_h',0),('flow_rate_m3_h',float('nan')),
    ('actual_internal_diameter_mm',0),('actual_internal_diameter_mm',float('inf')),
])
def test_linked_values_still_require_numeric_core_validation(field: str,bad: float) -> None:
    """A stored applied link never bypasses downstream numeric domain checks."""
    linked=flow().pipe_input
    linked=replace(linked,snapshot=replace(linked.snapshot,values=replace(linked.used_values,**{field:bad})))
    with pytest.raises(ValidationError): SuctionNPSHService(object()).calculate_suction_loss_v2(suction_input(linked))


@pytest.mark.parametrize('field,bad',[
    ('suction_pressure',-1),('vapour_pressure',-1),('density_kg_m3',0),
    ('static_suction_height_m',float('nan')),('npsh_required_m',float('inf')),
])
def test_enpy_validation_stays_semantic(field: str,bad: float) -> None:
    """Existing external ENPY inputs retain their domain validation."""
    service=SuctionNPSHService(object());loss=service.calculate_suction_loss_v2(suction_input())
    with pytest.raises(ValidationError): service.calculate_enpy_v2(loss,enpy_input(**{field:bad}))


def suction_page() -> SuctionNPSHPage:
    """Run real page callbacks with real domain/service objects and lightweight widget doubles."""
    page=SuctionNPSHPage.__new__(SuctionNPSHPage)
    page._workflow=SuctionWorkflow();page._translate=Translator('tr').translate
    page._fields={key:Var(value) for key,value in dict(diameter='101',flow='20',viscosity='2',
        length='20',roughness='0.015',pressure='1.2',vapour='0.03',density='850',height='2',required='3').items()}
    page._pipe_entries={key:Widget() for key in ('diameter','flow')}
    page._viscosity_unit=Var('cSt');page._pressure_unit=Var('bar');page._vapour_unit=Var('bar')
    page._roughness_source_mode='manual';page._roughness_source=Var();page._material=Var();page._material_ids={}
    page._material_box=Widget();page._roughness_entry=Widget()
    page._warning_fluid=Var();page._warning_fluid_codes={}
    page._suppress_dirty=False;page._events=[];page._dirty_callback=lambda:page._events.append('dirty')
    page._service=SuctionNPSHService(object());page._items={'test':LocalLossItem('test',2,.5)}
    page._result=Var();page._formula=Var();page._message=Var()
    page._suction_loss_summary=Var();page._enpy_summary=Var();page._k_total_summary=Var()
    page._detail_values={key:Var() for key in ('flow_velocity','reynolds_number','flow_regime','relative_roughness','friction_factor','pipe_loss','local_loss','k_total','suction_pressure_head','vapour_pressure_head','npsh_margin')}
    page._loss_status_messages=[];page._enpy_status_messages=[]
    page._refresh_losses=lambda:None
    page._sync_detail_presentation=lambda:None
    page._evaluate_engineering_warnings=lambda:None
    page._refresh_formula_panel=lambda:None
    page._warning_panel=SimpleNamespace(set_findings=lambda _:None)
    panel_stub(page)
    return page


def test_suction_page_two_stages_use_applied_values_and_keep_formula_view_compatible() -> None:
    """Read-only fields, staged result source and substitutions use the exact applied snapshot."""
    page=suction_page();page.set_transfer_state(flow().state)
    assert page._pipe_entries['diameter'].options['state']=='readonly'
    page._fields['diameter'].set('777');page._fields['flow'].set('999')
    page._calculate_suction_loss();page._calculate_enpy()
    assert (page._last_loss.actual_internal_diameter_mm,page._last_loss.flow_rate_m3_h)==(101,20)
    assert page._last_enpy.hydraulic is page._last_loss
    assert 'ENPYm' in '\n'.join(s.text for s in page._formula_sections())
    assert page._fields['diameter'].get()=='101'
    assert page._last_enpy.input.static_suction_height_m==2


def test_suction_update_keep_missing_and_manual_actions_never_calculate_implicitly() -> None:
    """Discovery/Keep retain prior results; explicit apply invalidates stages and keeps all locals."""
    page=suction_page();discovery=PipeSourceDiscovery();page.attach_pipe_sources(discovery)
    discovery.publish(source());panel=page._pipe_source_panel
    assert page._workflow.pipe_input.mode is PipeInputMode.MANUAL
    panel._mode_box.current(1);panel._choose_mode()
    assert page._workflow.pipe_input.mode is PipeInputMode.LINKED
    page._calculate_suction_loss();page._calculate_enpy()
    loss,enpy=page._last_loss,page._last_enpy
    local={key:var.get() for key,var in page._fields.items() if key not in ('diameter','flow')}
    discovery.publish(revised(source()))
    assert page._last_loss is loss and page._last_enpy is enpy
    assert 'sonucu değişti' in panel._status.get()
    panel._keep()
    assert page._workflow.pipe_input.kept_current
    assert page._last_enpy is enpy and 'korundu' in panel._status.get()
    page._calculate_suction_loss();page._calculate_enpy()
    assert page._last_enpy.flow_rate_m3_h==20
    panel._update()
    assert not hasattr(page,'_last_loss') and not hasattr(page,'_last_enpy')
    assert (page._fields['diameter'].get(),page._fields['flow'].get())==('99','30')
    assert {key:page._fields[key].get() for key in local}==local
    page._calculate_suction_loss();page._calculate_enpy();result=page._last_enpy
    discovery.remove(source().selection_id)
    assert page._last_enpy is result
    assert page._workflow.pipe_input.status is PipeLinkStatus.LINKED_SOURCE_MISSING
    page._calculate_suction_loss();page._calculate_enpy()
    assert page._last_enpy.flow_rate_m3_h==30
    panel._mode_box.current(0);panel._choose_mode()
    assert page._workflow.pipe_input.snapshot is None
    assert page._pipe_entries['flow'].options['state']=='normal'
    discovery.publish(source(flow_rate_m3_h=40))
    assert page._fields['flow'].get()=='30'
    assert page._workflow.pipe_input.status is PipeLinkStatus.MANUAL


@pytest.mark.parametrize('module',['suction','discharge'])
def test_zero_one_multiple_source_mode_choice_is_explicit_without_bind_step(module: str) -> None:
    """Normal mode/source controls automatically discover candidates without registry actions."""
    page=suction_page() if module=='suction' else page_stub()
    panel=page._pipe_source_panel if module=='suction' else panel_stub(page)
    discovery=PipeSourceDiscovery();page.attach_pipe_sources(discovery)
    panel._mode_box.current(1);panel._choose_mode()
    assert page._workflow.pipe_input.mode is PipeInputMode.MANUAL
    assert 'kullanılabilir' in panel._error.get()
    discovery.publish(source());assert page._workflow.pipe_input.mode is PipeInputMode.MANUAL
    panel._mode_box.current(1);panel._choose_mode()
    assert page._workflow.pipe_input.snapshot.source_selection_id==source().selection_id
    panel._mode_box.current(0);panel._choose_mode()
    second=source(selection_id=uuid4(),flow_rate_m3_h=50)
    discovery.publish(second)
    panel._selected_id=None;panel._mode_box.current(1);panel._choose_mode()
    assert page._workflow.pipe_input.mode is PipeInputMode.MANUAL
    assert panel._pending_link
    panel._source_box.current(1);panel._choose_source()
    assert page._workflow.pipe_input.snapshot.source_selection_id==second.selection_id
    assert page._workflow.pipe_input.used_values.flow_rate_m3_h==50


@pytest.mark.parametrize('mode',['manual','linked','stale','kept','missing'])
def test_suction_basma_project_json_roundtrip_preserves_independent_owners(
    mode: str,project_database,project_service,
) -> None:
    """Use one existing namespace and existing DB schema for both applied input owners."""
    from repositories.project_state_repository import ProjectStateRepository
    from services.project_persistence_service import ProjectPersistenceService
    discovery=PipeSourceDiscovery();suction=suction_page();discharge=page_stub()
    suction.attach_pipe_sources(discovery);discharge.attach_pipe_sources(discovery)
    discovery.publish(source())
    discharge._workflow.link(source().selection_id)
    if mode!='manual': suction._workflow.link(source().selection_id)
    if mode in ('stale','kept'): discovery.publish(revised(source()))
    if mode=='kept': suction._workflow.keep_current()
    if mode=='missing': discovery.remove(source().selection_id)
    window=MainWindow.__new__(MainWindow);window._pipe_sources=discovery
    window._pages={'discharge_head_loss':discharge,'suction_npsh':suction}
    persistence=ProjectPersistenceService(project_service,ProjectStateRepository(project_database))
    project=persistence.create_project('Phase 9 synthetic test')
    payload=window._export_all_page_states();persistence.save(payload)
    _,saved=persistence.open(project.id)
    expected=discovery.state
    restored=PipeSourceDiscovery();d2=page_stub();s2=suction_page()
    d2.attach_pipe_sources(restored);s2.attach_pipe_sources(restored)
    window._pipe_sources=restored;window._pages={'discharge_head_loss':d2,'suction_npsh':s2}
    window._load_all_page_states(saved)
    assert restored.state==expected
    assert s2._fields['roughness'].get()=='0.015'
    assert s2._fields['height'].get()=='2' and s2._fields['required'].get()=='3'
    assert saved['schema_version']==saved['pipe_transfer']['version']==1
    assert 'registry' not in json.dumps(saved).lower()
    with project_database.connection() as connection:
        assert connection.execute('SELECT version FROM schema_version').fetchone()[0]==1
    window._clear_all_pages()
    assert not restored.available()
    assert restored.state.suction.mode is restored.state.discharge.mode is PipeInputMode.MANUAL


def test_legacy_suction_payload_stays_manual_with_original_inputs_and_text_fallback() -> None:
    """Old Q/Di matching current source values cannot create provenance."""
    page=suction_page()
    legacy=page.export_state();legacy['result']='historical saved display'
    page._workflow.publish(source());page._workflow.link(source().selection_id)
    page.load_state(legacy)
    assert page._workflow.pipe_input.mode is PipeInputMode.MANUAL
    assert page._fields['roughness'].get()=='0.015'
    assert page._result.get()=='historical saved display'
    assert not hasattr(page,'_last_loss')
    assert page._pipe_entries['flow'].options['state']=='normal'


def test_pipe_design_normal_calculation_event_publishes_and_revises_automatically(
    material_service,pipe_size_service,engineering_constant_service,
) -> None:
    """A normal Pipe Design result event supplies both modules without a create/refresh command."""
    service=PipeDesignService(material_service,pipe_size_service,engineering_constant_service)
    standard=pipe_size_service.create_standard(code='PHASE9_TEST',display_name='Synthetic fixture')
    pipe_size_service.create_pipe_size(standard_id=standard.id,nominal_diameter='TEST',outside_diameter_mm=110,wall_thickness_mm=4,inside_diameter_mm=102)
    window=MainWindow.__new__(MainWindow);window._pipe_sources=PipeSourceDiscovery()
    window._pipe_design_service=service;window._mark_workspace_dirty=lambda:None
    pipe=PipeDesignPage.__new__(PipeDesignPage)
    pipe._service=service
    state=dict(pipe_standard_code=standard.code,fields=dict(q='20',v='2',pc='16',wf='.85',c='1',rp='195',sf='1.8'))
    pipe.export_state=lambda:state;pipe._using_library_source=lambda:False
    pipe._selected_pipe_standard_code=lambda:standard.code
    pipe._number=lambda key:float(state['fields'][key])
    pipe._update_diameter_summary=lambda:None
    pipe._warning_codes_from_result=lambda:[]
    pipe._refresh_diameter_warning_message=lambda:None
    pipe._evaluate_velocity_warning=lambda:None
    pipe._refresh_formula_panel=lambda:None
    pipe._sync_pipe_result_empty_state=lambda:None
    pipe._message=Var();pipe._translate=Translator('tr').translate
    pipe._material_ids={};pipe._material=Var();pipe._bend=Var(False)
    pipe._update_wall_summary=lambda:None
    state['fields']['da']='110'
    pipe.set_pipe_selection_listener(window._publish_pipe_selection,window._pipe_sources.remove)
    pipe._calculate_diameter()
    first=window._pipe_sources.available()[0]
    assert pipe._source_selection_id==first.selection_id
    assert first.actual_internal_diameter_mm==102
    owner=SuctionWorkflow(discovery=window._pipe_sources);owner.link(first.selection_id)
    state['fields']['q']='25';pipe._calculate_diameter()
    second=window._pipe_sources.available()[0]
    assert second.selection_id==first.selection_id and second.revision==2
    assert owner.pipe_input.status is PipeLinkStatus.LINKED_STALE
    assert owner.pipe_input.used_values.flow_rate_m3_h==20
    pipe._calculate_wall();assert window._pipe_sources.available()[0].revision==2
    state['fields']['q']='invalid';pipe._notify_pipe_selection()
    assert window._pipe_sources.available()[0].revision==2


def test_real_pipe_design_handlers_publish_only_after_successful_result() -> None:
    """The actual legacy handlers contain notification hooks; no hydraulic formulas are added."""
    import inspect
    for method in (PipeDesignPage._calculate_diameter,PipeDesignPage._calculate_wall):
        text=inspect.getsource(method)
        assert 'self._notify_pipe_selection()' in text
        assert text.index('self._notify_pipe_selection()')>text.index('self._service.calculate')
    import ast
    text=inspect.getsource(__import__('ui.pages.discharge_pipe_source',fromlist=['DischargePipeSourcePanel']))
    # The constructor creates only decision buttons; legacy private helpers remain internal.
    init=inspect.getsource(__import__('ui.pages.discharge_pipe_source',fromlist=['DischargePipeSourcePanel']).DischargePipeSourcePanel.__init__)
    assert '("link", self._link)' not in init and '("publish", self._publish)' not in init
    assert 'after(' not in inspect.getsource(PipeSourceDiscovery)


def test_pending_multiple_source_intent_does_not_leak_between_projects() -> None:
    """Loading/clearing a project restores the actual manual/linked mode, never a pending old choice."""
    page=suction_page();panel=page._pipe_source_panel
    page._workflow.publish(source());page._workflow.publish(source(selection_id=uuid4()))
    panel._mode_box.current(1);panel._choose_mode()
    assert panel._pending_link and page._workflow.pipe_input.mode is PipeInputMode.MANUAL
    legacy=page.export_state();page.load_state(legacy)
    assert not panel._pending_link
    assert panel._mode_box.current()==0
    panel._mode_box.current(1);panel._choose_mode();assert panel._pending_link
    page.clear_state()
    assert not panel._pending_link and panel._mode_box.current()==0


def test_suction_material_context_does_not_infer_library_roughness() -> None:
    """Library k is fetched once only when explicitly requested by Emme."""
    reads=[]
    class Materials:
        def get_material(self,identifier: UUID) -> object:
            reads.append(identifier)
            return SimpleNamespace(roughness_mm=.123)
    service=SuctionNPSHService(Materials())
    linked=flow().pipe_input
    result=service.calculate_suction_loss_v2(suction_input(linked))
    assert not reads and result.input.roughness_mm==.015
    identifier=uuid4()
    result=service.calculate_suction_loss_v2(suction_input(linked,material_id=identifier,roughness_mm=None))
    assert reads==[identifier]
    assert result.input.roughness_mm==.123
    assert result.metadata['roughness_source']=='material'


def test_suction_enpy_stage_reuses_loss_without_fetching_live_upstream_or_material() -> None:
    """Pressure/density changes calculate ENPY once and never recalculate hydraulics."""
    service=SuctionNPSHService(object())
    loss=service.calculate_suction_loss_v2(suction_input(flow().pipe_input))
    service.calculate_suction_loss_v2=lambda _:pytest.fail('Unexpected hydraulic recalculation')
    service.calculate_suction_loss=lambda *args:pytest.fail('Unexpected legacy recalculation')
    result=service.calculate_enpy_v2(loss,enpy_input())
    assert result.hydraulic is loss
    assert result.metadata['pipe_transfer']['source_revision']==1


def test_discovery_publication_does_not_invalidate_real_traced_page_results() -> None:
    """Simulate StringVar traces so status-only redraw cannot invalidate either Emme stage."""
    class TracedVar(Var):
        def set(self,value: str) -> None:
            self.value=value
            page._invalidate_hydraulics()
            page._mark_dirty()
    page=suction_page()
    discovery=PipeSourceDiscovery();page.attach_pipe_sources(discovery)
    discovery.publish(source());panel=page._pipe_source_panel
    panel._mode_box.current(1);panel._choose_mode()
    page._calculate_suction_loss();page._calculate_enpy()
    loss,enpy=page._last_loss,page._last_enpy
    for key in ('diameter','flow'):
        page._fields[key]=TracedVar(page._fields[key].get())
    page._events.clear()
    discovery.publish(revised(source()))
    assert page._last_loss is loss and page._last_enpy is enpy
    assert not page._events
    assert page._fields['flow'].get()=='20'


def test_unavailable_numeric_source_cannot_replace_historical_snapshot() -> None:
    """Discovery and Update both reject a known-invalid published source without overwriting Q/Di."""
    owner=flow();before=owner.pipe_input.snapshot
    bad=revise_selection(source(),source(flow_rate_m3_h=0))
    owner.publish(bad)
    assert owner.available_sources()==()
    with pytest.raises(ValueError): owner.update()
    assert owner.pipe_input.snapshot is before


def test_explicit_suction_library_roughness_renders_existing_warning_path() -> None:
    """The existing material selector uses the actual suction warning renderer without an undefined callback."""
    page=suction_page();identifier=uuid4()
    page._material_ids={'TEST':identifier};page._material.set('TEST')
    page._materials=SimpleNamespace(get_material=lambda _:SimpleNamespace(roughness_mm=.123))
    page._roughness_source_mode='material'
    page._load_selected_roughness()
    assert page._fields['roughness'].get()=='0.123'
    assert not hasattr(page,'_last_loss')
