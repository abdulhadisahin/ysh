"""Phase 8 discharge engineering/state contracts without a display or real user DB."""
from dataclasses import FrozenInstanceError, fields, replace
from types import SimpleNamespace
from uuid import UUID, uuid4
import json
import math

import pytest

from core.local_loss_item import LocalLossItem
from engineering.head_loss.models import DischargeHeadLossResult
from engineering.head_loss.v2_models import DischargeLocalLoss, DischargeV2Input, DischargeV2Result
from engineering.pipe_design.rules import DesignStatus
from engineering.pipe_design.transfer import (
    PipeInputMode, PipeInputState, PipeLinkStatus, PipeTransferProjectState,
    PipeValues, revise_selection,
)
from engineering.pipe_design.v2_models import PipeCandidate, PipeSelection
from engineering.pipe_design.transfer_serialization import transfer_to_dict, transfer_from_dict
from engineering.validation import ValidationError
from i18n.translator import Translator
from services.discharge_head_loss_service import DischargeHeadLossService
from services.discharge_source_adapter import prepare_discharge_source
from services.discharge_workflow import DischargeWorkflow
from services.pipe_design_service import PipeDesignService
from ui.pages.discharge_head_loss_page import DischargeHeadLossPage
from ui.pages.discharge_pipe_source import DischargePipeSourcePanel
from ui.main_window import MainWindow


def source(**changes: object) -> PipeSelection:
    """Use synthetic geometry with stored ID distinct from theoretical D and OD-2t."""
    pipe = PipeCandidate(id=UUID(int=2), standard_id=UUID(int=1),
        outside_diameter_mm=110, wall_thickness_mm=4, inside_diameter_mm=101,
        nominal_diameter="TEST DN", nps="TEST NPS", schedule="TEST SCH")
    return PipeSelection(**(dict(selection_id=UUID(int=100), status=DesignStatus.RULE_NOT_CONFIGURED,
        theoretical_internal_diameter_mm=75, flow_rate_m3_h=20, design_velocity_m_s=2,
        selected_standard_id=pipe.standard_id, selected_standard_code="TEST",
        candidate=pipe, selected_pipe=pipe, material_id=UUID(int=10),
        fluid_id=UUID(int=11), system_id=UUID(int=12), circuit_id=UUID(int=13)) | changes))


def revised(old: PipeSelection) -> PipeSelection:
    """Publish a changed Q/Di using the Phase 7 authoritative revision helper."""
    return revise_selection(old, replace(old, flow_rate_m3_h=30,
        selected_pipe=replace(old.selected_pipe, inside_diameter_mm=99)))


def inputs(pipe: PipeInputState | None = None, **changes: object) -> DischargeV2Input:
    """Representative local inputs belong solely to discharge."""
    return DischargeV2Input(**(dict(pipe_input=pipe or PipeInputState(manual_values=PipeValues(
        actual_internal_diameter_mm=101, flow_rate_m3_h=20)), kinematic_viscosity_m2s=2e-6,
        pipe_length_m=20, roughness_mm=.015, geodetic_head_m=2,
        local_losses=(DischargeLocalLoss('TEST bend',2,.5),)) | changes))


def workflow() -> DischargeWorkflow:
    """Start with an explicitly selected linked source."""
    result=DischargeWorkflow()
    result.publish(source())
    result.link(source().selection_id)
    return result


def numeric(result: DischargeHeadLossResult) -> dict[str, object]:
    """Compare every legacy output/warning without extra V2 source metadata."""
    return {f.name:getattr(result,f.name) for f in fields(DischargeHeadLossResult) if f.name!='metadata'}


@pytest.mark.parametrize('mode',['manual','linked','stale','kept','missing','detached'])
@pytest.mark.parametrize('height',[0,2,-2,30])
def test_v2_matches_all_legacy_hydraulic_outputs(mode: str, height: float) -> None:
    """V/Re/f/hf/hL/hhat/Hs are unchanged for all input ownership modes."""
    flow=workflow()
    if mode=='stale': flow.publish(revised(source()))
    if mode=='kept': flow.publish(revised(source()));flow.keep_current()
    if mode=='missing': flow.remove(source().selection_id)
    if mode in ('manual','detached'): flow.manual()
    request=inputs(flow.pipe_input,geodetic_head_m=height)
    service=DischargeHeadLossService(object())
    result=service.calculate_v2(request)
    legacy=service.calculate(101,20,2e-6,20,.015,height,[LocalLossItem('TEST bend',2,.5)])
    assert isinstance(result,DischargeV2Result)
    assert numeric(result)==numeric(legacy)
    assert (result.flow_rate_m3_h,result.actual_internal_diameter_mm)==(20,101)
    assert result.actual_internal_diameter_mm!=source().theoretical_internal_diameter_mm
    assert result.system_head_m==height+result.total_hydraulic_loss_m
    assert result.geodetic_head_m==height
    assert result.metadata['pipe_transfer']['mode']==flow.pipe_input.mode.value


def test_manual_editing_and_upstream_independence() -> None:
    """Manual mode permits Q/Di edits and never observes source changes."""
    flow=DischargeWorkflow()
    flow.edit_manual(diameter_mm=80,flow_m3_h=5)
    before=flow.pipe_input
    flow.publish(source());flow.publish(revised(source()))
    assert flow.pipe_input==before
    assert not flow.pipe_fields_readonly
    flow.edit_manual(diameter_mm=90,flow_m3_h=6)
    assert flow.pipe_input.used_values.hydraulic_values()==(90,6)
    with pytest.raises(ValueError): flow.link(uuid4())


def test_stale_update_keep_and_missing_preserve_inputs_and_do_not_calculate() -> None:
    """Decisions are pure state changes; even local input identity remains stable."""
    flow=workflow();local=inputs(flow.pipe_input);snapshot=flow.pipe_input.snapshot
    flow.publish(revised(source()))
    assert flow.pipe_input.status is PipeLinkStatus.LINKED_STALE
    assert flow.pipe_input.snapshot is snapshot
    flow.keep_current()
    assert flow.pipe_input.kept_current
    assert flow.pipe_input.status is PipeLinkStatus.LINKED_STALE
    assert flow.pipe_input.observed_revision==2
    before=DischargeHeadLossService(object()).calculate_v2(replace(local,pipe_input=flow.pipe_input))
    assert (before.flow_rate_m3_h,before.actual_internal_diameter_mm)==(20,101)
    flow.update()
    updated=replace(local,pipe_input=flow.pipe_input)
    assert flow.pipe_input.status is PipeLinkStatus.LINKED_SYNCED
    assert flow.pipe_input.snapshot.source_revision==2
    assert updated.local_losses is local.local_losses
    for name in ('kinematic_viscosity_m2s','pipe_length_m','roughness_mm','geodetic_head_m'):
        assert getattr(updated,name)==getattr(local,name)
    assert flow.pipe_input.used_values.hydraulic_values()==(99,30)
    flow.remove(source().selection_id)
    assert flow.pipe_input.status is PipeLinkStatus.LINKED_SOURCE_MISSING
    assert flow.pipe_input.used_values.hydraulic_values()==(99,30)
    with pytest.raises(ValueError): flow.update()


def test_linked_editing_rejected_and_manual_switch_clears_dependency() -> None:
    """The service path rejects edits even if a caller bypasses readonly widgets."""
    flow=workflow()
    with pytest.raises(ValueError): flow.edit_manual(diameter_mm=50,flow_m3_h=10)
    flow.manual()
    assert flow.pipe_input.snapshot is None
    assert flow.pipe_input.used_values.hydraulic_values()==(101,20)
    flow.publish(revised(source()))
    assert flow.pipe_input.status is PipeLinkStatus.MANUAL
    flow.link(source().selection_id)
    assert flow.pipe_input.used_values.hydraulic_values()==(99,30)


@pytest.mark.parametrize('flow_rate,regime',[(.1,'Laminar'),(.85,'Transitional'),(20,'Turbulent')])
def test_regime_and_friction_unchanged(flow_rate: float, regime: str) -> None:
    """Retain existing laminar/interpolated/Colebrook behavior."""
    service=DischargeHeadLossService(object())
    request=inputs(PipeInputState(manual_values=PipeValues(
        actual_internal_diameter_mm=100,flow_rate_m3_h=flow_rate)),kinematic_viscosity_m2s=1e-6)
    result=service.calculate_v2(request)
    assert result.flow_regime==regime
    assert numeric(result)==numeric(service.calculate(100,flow_rate,1e-6,20,.015,2,[LocalLossItem('TEST bend',2,.5)]))


def test_d5_pipe_and_d4_local_loss_behavior_preserved() -> None:
    """Normalize pipe loss by computed f so the explicit diameter exponent is isolated."""
    service=DischargeHeadLossService(object())
    def calculate(diameter: float) -> DischargeV2Result:
        return service.calculate_v2(inputs(PipeInputState(manual_values=PipeValues(
            actual_internal_diameter_mm=diameter,flow_rate_m3_h=20))))
    small,big=calculate(100),calculate(200)
    assert (small.pipe_friction_loss_m/small.friction_factor)/(big.pipe_friction_loss_m/big.friction_factor)==pytest.approx(32)
    assert small.local_loss_m/big.local_loss_m==pytest.approx(16)
    assert small.local_loss_coefficient_total==1


@pytest.mark.parametrize('key,bad,field_key',[
    ('flow_rate_m3_h',0,'field.flow_rate'),('flow_rate_m3_h',float('nan'),'field.flow_rate'),
    ('actual_internal_diameter_mm',0,'field.pipe_inside_diameter'),
    ('actual_internal_diameter_mm',float('inf'),'field.pipe_inside_diameter'),
])
def test_linked_inputs_still_pass_core_validation(key: str,bad: float,field_key: str) -> None:
    """A source reference is not evidence of valid numerical hydraulic input."""
    state=workflow().pipe_input
    state=replace(state,snapshot=replace(state.snapshot,values=replace(state.used_values,**{key:bad})))
    with pytest.raises(ValidationError) as error:
        DischargeHeadLossService(object()).calculate_v2(inputs(state))
    assert error.value.issue.field_key==field_key


@pytest.mark.parametrize('key,bad',[
    ('pipe_length_m',-1),('kinematic_viscosity_m2s',0),('roughness_mm',-.1),
    ('geodetic_head_m',float('nan')),
])
def test_local_numeric_validation_preserved(key: str,bad: float) -> None:
    """Local input validation remains delegated to the core."""
    with pytest.raises(ValidationError): DischargeHeadLossService(object()).calculate_v2(inputs(**{key:bad}))


@pytest.mark.parametrize('quantity,k', [(-1,1),(True,1),(1.5,1),(1,-1),(1,float('nan')),(1,True)])
def test_invalid_local_entries_rejected(quantity: object,k: object) -> None:
    """Apply the existing nonnegative count/K domain at the typed boundary."""
    with pytest.raises(ValidationError): DischargeLocalLoss('test',quantity,k)


def test_zero_quantity_and_k_remain_supported() -> None:
    """Zero entries retain their established dialog meaning."""
    result=DischargeHeadLossService(object()).calculate_v2(inputs(local_losses=(DischargeLocalLoss('test',0,0),)))
    assert result.local_loss_coefficient_total==result.local_loss_m==0


def test_material_roughness_explicit_once_and_context_does_not_infer_it() -> None:
    """Material context never overrides k unless Basma explicitly selects its library source."""
    reads=[]
    class Materials:
        def get_material(self, identifier: UUID) -> object:
            reads.append(identifier)
            return SimpleNamespace(roughness_mm=.123)
    service=DischargeHeadLossService(Materials())
    linked=workflow().pipe_input
    result=service.calculate_v2(inputs(linked))
    assert not reads and result.input.roughness_mm==.015
    selected=uuid4()
    result=service.calculate_v2(inputs(linked,material_id=selected,roughness_mm=None))
    assert reads==[selected]
    assert result.input.roughness_mm==.123
    assert result.input.material_id==selected
    assert result.metadata['roughness_source']=='material'
    assert result.metadata['pipe_transfer']['source_selection_id']==str(source().selection_id)


def test_missing_library_roughness_retains_semantic_validation() -> None:
    """No default k is invented for incomplete material records."""
    service=DischargeHeadLossService(SimpleNamespace(get_material=lambda _:SimpleNamespace(roughness_mm=None)))
    with pytest.raises(ValidationError) as error:
        service.calculate_v2(inputs(material_id=uuid4()))
    assert error.value.issue.code=='material_roughness_missing'


class Var:
    """Tiny display-free StringVar for testing existing callback paths."""
    def __init__(self,value: str='') -> None: self.value=value
    def get(self) -> str: return self.value
    def set(self,value: str) -> None: self.value=value


class Widget:
    """Capture readonly and source-control presentation state."""
    def __init__(self) -> None: self.options={};self.index=-1
    def configure(self,**options: object) -> None: self.options.update(options)
    def current(self,index: int | None=None) -> int:
        if index is not None: self.index=index
        return self.index


def page_stub() -> DischargeHeadLossPage:
    """Exercise page callbacks with real service/domain objects and no Tk interpreter."""
    page=DischargeHeadLossPage.__new__(DischargeHeadLossPage)
    page._workflow=DischargeWorkflow()
    page._translate=Translator('tr').translate
    page._fields={key:Var(value) for key,value in dict(d='101',q='20',nu='2',l='20',k='0.015',h='2').items()}
    page._entries={key:Widget() for key in ('d','q')}
    page._source_mode='manual';page._source=Var();page._material=Var()
    page._material_ids={};page._material_box=Widget();page._roughness_entry=Widget()
    page._viscosity_unit=Var('cSt');page._warning_fluid=Var();page._warning_fluid_codes={}
    page._warning_panel=SimpleNamespace(set_findings=lambda _:None)
    page._items={'test':LocalLossItem('test',2,.5)}
    page._pipe_source_panel=SimpleNamespace(render=lambda:None,_selected_id=None)
    page._service=DischargeHeadLossService(object())
    page._suppress_dirty=False
    page._events=[]
    page._dirty_callback=lambda:page._events.append('dirty')
    page._invalidate_result=lambda:page._events.append('invalidate')
    page._render_result=lambda:page._events.append('render')
    page._refresh_formula_panel=lambda:None
    page._set_semantic_messages=lambda issues:page._events.append(issues)
    page._clear_result_metrics=lambda:None
    page._sync_result_empty_state=lambda:None
    page._refresh=lambda:None
    page._result_summary=Var()
    return page


def panel_stub(page: DischargeHeadLossPage) -> DischargePipeSourcePanel:
    """Use real panel event handlers/rendering, substituting only Tk variables/widgets."""
    panel=DischargePipeSourcePanel.__new__(DischargePipeSourcePanel)
    panel.workflow=page._workflow
    panel._translate=page._translate
    panel._changed=page._pipe_source_changed
    panel.source_factory=None
    panel._selected_id=None;panel._source_ids=[]
    panel._source_box=Widget();panel._mode_box=Widget()
    panel._source=Var();panel._mode=Var();panel._status=Var();panel._details=Var();panel._error=Var()
    panel._buttons={key:Widget() for key in ('update','keep','publish','link')}
    page._pipe_source_panel=panel
    return panel


def test_page_calculate_uses_snapshot_even_if_display_variables_are_changed() -> None:
    """Linked Q/Di cannot be mutated through the page's normal calculation path."""
    page=page_stub()
    page.set_transfer_state(workflow().state)
    assert page._entries['d'].options['state']=='readonly'
    assert page._entries['q'].options['state']=='readonly'
    page._fields['q'].set('999');page._fields['d'].set('777')
    page._calculate()
    assert page._last_result.flow_rate_m3_h==20
    assert page._last_result.actual_internal_diameter_mm==101
    assert page._last_result.input.pipe_length_m==20
    page._workflow.publish(revised(source()))
    page._calculate()
    assert page._last_result.flow_rate_m3_h==20
    assert page._last_result.input.pipe_input.status is PipeLinkStatus.LINKED_STALE


def test_page_mode_update_keep_and_publish_callbacks_without_recalculation() -> None:
    """Wired controls preserve results on observation/Keep and invalidate only on apply."""
    page=page_stub();panel=panel_stub(page)
    page._workflow.publish(source())
    panel._mode_box.current(1);panel._choose_mode()
    assert page._workflow.pipe_input.mode is PipeInputMode.MANUAL
    assert panel._error.get()
    panel._selected_id=source().selection_id;panel._link()
    assert page._fields['q'].get()=='20' and page._entries['q'].options['state']=='readonly'
    page._calculate();old_result=page._last_result
    page._events.clear()
    panel.source_factory=lambda previous:revised(previous)
    panel._publish()
    assert page._events==['dirty']
    assert page._last_result is old_result
    assert 'sonucu değişti' in panel._status.get()
    assert page._fields['q'].get()=='20'
    panel._keep()
    assert page._workflow.pipe_input.kept_current
    assert 'korundu' in panel._status.get() and 'değişti' in panel._status.get()
    assert page._last_result is old_result
    assert 'render' not in page._events
    page._events.clear();panel._update()
    assert page._events==['invalidate','dirty']
    assert page._fields['q'].get()=='30' and page._fields['d'].get()=='99'
    assert page._fields['l'].get()=='20' and page._fields['k'].get()=='0.015'
    panel._mode_box.current(0);panel._choose_mode()
    assert page._workflow.pipe_input.mode is PipeInputMode.MANUAL
    assert page._fields['q'].get()=='30' and page._entries['q'].options['state']=='normal'
    page._workflow.publish(revise_selection(revised(source()),source(flow_rate_m3_h=40)))
    assert page._workflow.pipe_input.status is PipeLinkStatus.MANUAL


@pytest.mark.parametrize('kind',['manual','linked','stale','kept','missing'])
def test_workspace_page_roundtrip(kind: str) -> None:
    """Global Phase 7 namespace carries links while legacy page fields remain compatible."""
    page=page_stub();flow=workflow()
    if kind=='manual': flow.manual()
    if kind in ('stale','kept'): flow.publish(revised(source()))
    if kind=='kept': flow.keep_current()
    if kind=='missing': flow.remove(source().selection_id)
    # Independent suction snapshot must survive a Basma-only save.
    flow.state=replace(flow.state,suction=PipeInputState().link_to(source()))
    page.set_transfer_state(flow.state)
    window=MainWindow.__new__(MainWindow);window._pages={'discharge_head_loss':page}
    payload=json.loads(json.dumps(window._export_all_page_states()))
    restored=page_stub();window._pages={'discharge_head_loss':restored}
    window._load_all_page_states(payload)
    assert restored._workflow.pipe_input.mode is flow.pipe_input.mode
    assert restored._workflow.pipe_input.snapshot==flow.pipe_input.snapshot
    assert restored._workflow.pipe_input.status is flow.pipe_input.status
    assert restored._workflow.pipe_input.kept_current==flow.pipe_input.kept_current
    assert restored._fields['k'].get()=='0.015'
    assert restored._fields['l'].get()=='20'
    assert restored._workflow.state.suction.snapshot==flow.state.suction.snapshot
    assert payload['schema_version']==payload['pipe_transfer']['version']==1


def test_old_page_state_loads_manual_and_keeps_manual_roughness() -> None:
    """No matching legacy values infer a source; manual k survives load."""
    page=page_stub();page.set_transfer_state(workflow().state)
    state=dict(fields=dict(d='101',q='20',nu='2',l='20',k='0.015',h='2'),source='manual',items=[])
    page.load_state(state)
    assert page._workflow.pipe_input.mode is PipeInputMode.MANUAL
    assert page._fields['k'].get()=='0.015'
    assert page._entries['q'].options['state']=='normal'
    assert 'dirty' not in page._events
    assert not hasattr(page,'_last_result')


@pytest.mark.parametrize('status',['LINKED_SYNCED','LINKED_STALE','LINKED_SOURCE_MISSING','LINKED_SOURCE_UNAVAILABLE'])
def test_link_notices_and_source_labels_are_localized_without_uuid(status: str) -> None:
    """Link notices remain outside engineering warnings and expose readable identity."""
    page=page_stub();panel=panel_stub(page);flow=workflow()
    if status=='LINKED_STALE': flow.publish(revised(source()))
    if status=='LINKED_SOURCE_MISSING': flow.remove(source().selection_id)
    if status=='LINKED_SOURCE_UNAVAILABLE': flow.publish(revise_selection(source(),source(selected_pipe=None)))
    page._workflow.state=flow.state;panel.render()
    assert panel._status.get()==Translator('tr').translate(f'discharge.pipe.status.{status}')
    assert 'Di 101,00' in panel._details.get()
    assert str(source().selection_id) not in panel._details.get()
    for label in panel._source_box.options['values']:
        assert str(source().selection_id) not in label
    assert not page._events


def test_multiple_sources_require_explicit_selection() -> None:
    """Selecting a row alone never changes applied Q/Di."""
    page=page_stub();panel=panel_stub(page)
    first=source();second=source(selection_id=uuid4(),flow_rate_m3_h=50)
    page._workflow.publish(first);page._workflow.publish(second)
    panel.render();assert panel._selected_id is None
    panel._source_box.current(1);panel._choose_source()
    assert page._workflow.pipe_input.mode is PipeInputMode.MANUAL
    panel._link()
    assert page._workflow.pipe_input.snapshot.source_selection_id==second.selection_id
    assert page._fields['q'].get()=='50'


def test_explicit_source_adapter_uses_existing_v2_without_legacy_geometry_inference(
    material_service,pipe_size_service,engineering_constant_service,
) -> None:
    """Legacy theoretical diameter/result dictionaries cannot become hydraulic Di."""
    service=PipeDesignService(material_service,pipe_size_service,engineering_constant_service)
    standard=pipe_size_service.create_standard(code='PHASE8_TEST',display_name='Synthetic test')
    pipe_size_service.create_pipe_size(standard_id=standard.id,nominal_diameter='TEST',outside_diameter_mm=110,wall_thickness_mm=4,inside_diameter_mm=102)
    state=dict(pipe_standard_code=standard.code,fields=dict(q='20',v='2',pc='16',wf='0.85',c='1',rp='195',sf='1.8'),diameter_result={'diameter_mm':999})
    first=prepare_discharge_source(service,state,manual_material=True)
    assert first.actual_internal_diameter_mm==102
    assert first.actual_internal_diameter_mm!=first.theoretical_internal_diameter_mm
    assert first.status is DesignStatus.RULE_NOT_CONFIGURED
    same=prepare_discharge_source(service,state,first,manual_material=True)
    assert same.selection_id==first.selection_id and same.revision==1
    state['fields']['q']='25'
    new=prepare_discharge_source(service,state,same,manual_material=True)
    assert new.revision==2 and new.selection_id==first.selection_id
    with pytest.raises(ValidationError): prepare_discharge_source(service,state,manual_material=False)
    state['fields']['q']='invalid'
    with pytest.raises(ValidationError): prepare_discharge_source(service,state,manual_material=True)


@pytest.mark.parametrize('kind',['manual','linked','stale','kept','missing'])
def test_project_json_storage_uses_existing_schema_and_roundtrips_basma(
    kind: str,project_database,project_service,
) -> None:
    """Persist actual page state through existing repository with unchanged table definitions."""
    from repositories.project_state_repository import ProjectStateRepository
    from services.project_persistence_service import ProjectPersistenceService
    persistence=ProjectPersistenceService(project_service,ProjectStateRepository(project_database))
    project=persistence.create_project('Synthetic Phase 8 test')
    with project_database.connection() as connection:
        before=connection.execute("SELECT name,sql FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
    page=page_stub();flow=workflow()
    if kind=='manual': flow.manual()
    if kind in ('stale','kept'): flow.publish(revised(source()))
    if kind=='kept': flow.keep_current()
    if kind=='missing': flow.remove(source().selection_id)
    page.set_transfer_state(flow.state)
    window=MainWindow.__new__(MainWindow);window._pages={'discharge_head_loss':page}
    persistence.save(window._export_all_page_states())
    _,state=persistence.open(project.id)
    restored=page_stub();window._pages={'discharge_head_loss':restored}
    window._load_all_page_states(state)
    assert restored._workflow.pipe_input==flow.pipe_input
    assert restored._fields['k'].get()=='0.015'
    assert state['schema_version']==1
    with project_database.connection() as connection:
        assert connection.execute('SELECT version FROM schema_version').fetchone()[0]==1
        assert connection.execute("SELECT name,sql FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()==before


def test_typed_inputs_are_immutable_and_reject_mutable_local_loss_collections() -> None:
    """A stored result's used-input description cannot change through a list reference."""
    request=inputs()
    with pytest.raises(FrozenInstanceError): request.pipe_length_m=999
    with pytest.raises(FrozenInstanceError): request.local_losses[0].k_coefficient=99
    with pytest.raises(TypeError): inputs(local_losses=[DischargeLocalLoss('test',1,1)])


def test_clear_project_removes_all_links_and_sources_without_dirty_notification() -> None:
    """Closing a project cannot carry its sources into a new/manual workspace."""
    page=page_stub();page.set_transfer_state(workflow().state)
    page._calculate();page._events.clear()
    page.clear_state()
    assert page._workflow.pipe_input.mode is PipeInputMode.MANUAL
    assert not page._workflow.state.selections
    assert all(not var.get() for var in page._fields.values())
    assert not hasattr(page,'_last_result')
    assert 'dirty' not in page._events


def test_source_preparation_failure_is_inline_and_preserves_calculation() -> None:
    """Incomplete Pipe Design fields cannot destroy an existing Basma snapshot/result."""
    from engineering.validation import ValidationIssue
    page=page_stub();panel=panel_stub(page)
    page.set_transfer_state(workflow().state)
    page._calculate();result=page._last_result
    def broken(previous: PipeSelection | None) -> PipeSelection:
        raise ValidationError(ValidationIssue('required','field.flow_rate'))
    panel.source_factory=broken
    panel._publish()
    assert panel._error.get()
    assert page._last_result is result
    assert page._workflow.pipe_input.snapshot.source_revision==1


def test_source_preparation_retains_explicit_material_and_circuit_context(
    material_service,pipe_size_service,engineering_constant_service,
) -> None:
    """Use the material service explicitly; no new strength or classification data are seeded."""
    material=material_service.create_material(name='Synthetic fixture',designation='PHASE8_TEST',yield_strength_mpa=195)
    service=PipeDesignService(material_service,pipe_size_service,engineering_constant_service)
    standard=pipe_size_service.create_standard(code='PHASE8_LIBRARY_TEST',display_name='Synthetic fixture')
    pipe_size_service.create_pipe_size(standard_id=standard.id,nominal_diameter='TEST',outside_diameter_mm=110,wall_thickness_mm=4,inside_diameter_mm=102)
    circuit=SimpleNamespace(code='TEST_CIRCUIT',id=uuid4())
    service._circuits=SimpleNamespace(get_active_circuits=lambda:[circuit])
    state=dict(pipe_standard_code=standard.code,material_id=str(material.id),circuit_code=circuit.code,
        fields=dict(q='20',v='2',pc='16',wf='0.85',c='1',sf='1.8'))
    result=prepare_discharge_source(service,state,manual_material=False)
    assert result.material_id==material.id
    assert result.circuit_id==circuit.id
    assert result.allowable_stress.value==195/1.8
