"""Phase 10 real sizing, unchanged empirical regression and project/UI separation."""
from dataclasses import FrozenInstanceError, asdict, replace
from datetime import date
import json
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

from core.pump_reference import PumpReference
from engineering.provenance import SourceReference, SourceType, VerificationStatus
from engineering.transfer_pump.v2_models import (
    CapacityStatus, TransferPumpMode, TransferPumpDesignInput, TransferPumpDesignResult,
    TransferPumpEmpiricalInput, TransferPumpEmpiricalResult, PumpIntegrationContext,
)
from engineering.transfer_pump.v2_state import TransferPumpPageState
from engineering.validation import ValidationError
from services.transfer_pump_service import TransferPumpService
from ui.pages.transfer_pump_design import TransferPumpDesignPanel
from ui.pages.transfer_pump_page import TransferPumpPage
from i18n.translator import Translator
from .test_discharge_v2_phase8 import Var, Widget


def references() -> list[PumpReference]:
    """Synthetic vessel data; no manufacturer or production standard is implied."""
    return [PumpReference(name,volume,capacity,source='Synthetic historical fixture',id=UUID(int=index))
            for index,(name,volume,capacity) in enumerate((('A',100,20),('B',200,30),('C',300,40)),1)]


def service() -> TransferPumpService:
    """Use explicit synthetic references for the empirical path only."""
    return TransferPumpService(SimpleNamespace(get_all_references=references))


@pytest.mark.parametrize('volume,time,expected',[(120,3,40),(1,2,.5),(1000,.5,2000),(1.234567,.33333,1.234567/.33333)])
def test_design_capacity_uses_only_volume_divided_by_explicit_target(volume: float,time: float,expected: float) -> None:
    """No reference reads, mass conversion, default target, margin or rounding enters design."""
    result=TransferPumpService(object()).calculate_v2(TransferPumpDesignInput(
        transfer_volume_m3=volume,target_transfer_time_h=time))
    assert isinstance(result,TransferPumpDesignResult)
    assert result.required_flow_m3_h==expected
    assert result.required_capacity.unit=='m³/h'
    assert result.required_capacity.source.source_type is SourceType.CALCULATED
    assert result.input.volume_source.source_type is SourceType.USER_INPUT
    assert result.input.target_time_source.source_type is SourceType.USER_INPUT
    assert result.mode is TransferPumpMode.DESIGN
    assert result.margin_percent is result.margin_adjusted_flow_m3_h is None
    assert result.transfer_time_h is None
    assert result.status is CapacityStatus.NO_SELECTED_PUMP


@pytest.mark.parametrize('field',['transfer_volume_m3','target_transfer_time_h','selected_pump_capacity_m3_h'])
@pytest.mark.parametrize('bad',[0,-1,True,float('nan'),float('inf'),float('-inf'),'invalid'])
def test_invalid_design_inputs_are_rejected(field: str,bad: object) -> None:
    """Reject invalid source numbers without infinity, clamping or invented maximum limits."""
    values=dict(transfer_volume_m3=120,target_transfer_time_h=3,selected_pump_capacity_m3_h=40)
    values[field]=bad
    with pytest.raises(ValidationError): TransferPumpDesignInput(**values)


@pytest.mark.parametrize('selected,time,status',[
    (60,2,CapacityStatus.ADEQUATE),(40,3,CapacityStatus.ADEQUATE),
    (30,4,CapacityStatus.PUMP_CAPACITY_BELOW_REQUIRED),
])
def test_selected_capacity_time_and_exact_adequacy(selected: float,time: float,status: CapacityStatus) -> None:
    """Required capacity and actual transfer time answer separate questions with no tolerance."""
    result=service().calculate_v2(TransferPumpDesignInput(transfer_volume_m3=120,
        target_transfer_time_h=3,selected_pump_capacity_m3_h=selected))
    assert result.required_flow_m3_h==40
    assert result.transfer_time_h==time and result.status is status
    assert (result.transfer_time_h<=3)==(selected>=40)


def test_capacity_comparison_has_no_epsilon_band() -> None:
    """A capacity even slightly below Qgerekli is insufficient without an arbitrary tolerance."""
    result=service().calculate_v2(TransferPumpDesignInput(transfer_volume_m3=120,
        target_transfer_time_h=3,selected_pump_capacity_m3_h=39.99999999999999))
    assert result.status is CapacityStatus.PUMP_CAPACITY_BELOW_REQUIRED


@pytest.mark.parametrize('source_type',[SourceType.PROJECT_CRITERION,SourceType.D243_CRITERION])
def test_explicit_configured_time_source_is_preserved(source_type: SourceType) -> None:
    """Existing Phase 2 source facts are retained, never promoted to verified or TL."""
    target=SourceReference(source_type=source_type,document='Synthetic configured project criterion',
        verification_status=VerificationStatus.USER_SUPPLIED,effective_date=date(2026,1,1))
    volume=SourceReference(source_type=SourceType.PROJECT_CRITERION,document='Synthetic project volume')
    result=service().calculate_v2(TransferPumpDesignInput(transfer_volume_m3=120,
        target_transfer_time_h=3,volume_source=volume,target_time_source=target))
    assert result.input.target_time_source is target
    assert result.input.volume_source is volume
    assert result.required_capacity.source.source_type is SourceType.CALCULATED
    assert target.verification_status is VerificationStatus.USER_SUPPLIED


def test_tl_and_reference_data_cannot_silently_become_design_inputs() -> None:
    """The new design path has no classification or regression-derived target defaults."""
    for kind in (SourceType.TL_RULE,SourceType.REFERENCE_VESSEL_DATA,SourceType.MANUFACTURER_DATA):
        with pytest.raises(ValueError):
            TransferPumpDesignInput(transfer_volume_m3=120,target_transfer_time_h=3,
                target_time_source=SourceReference(source_type=kind))


@pytest.mark.parametrize('capacity',[50,100,250,300,450])
@pytest.mark.parametrize('mode',['VOLUME','MASS'])
def test_empirical_fit_is_exactly_the_legacy_fit(capacity: float,mode: str) -> None:
    """Preserve coefficient order, estimated capacity, R², extrapolation and both time units."""
    instance=service();records=references()
    value=capacity if mode=='VOLUME' else capacity*.83
    resolution,legacy=instance.calculate_from_capacity_input(mode,value,records)
    typed=instance.calculate_v2(TransferPumpEmpiricalInput(source_capacity=value,
        capacity_input_mode=mode),references=records)
    assert isinstance(typed,TransferPumpEmpiricalResult)
    assert asdict(typed.estimate)==asdict(legacy)
    assert typed.resolution==resolution
    assert typed.mode is TransferPumpMode.EMPIRICAL
    assert typed.required_flow_m3_h is None
    assert typed.calculated_capacity.source.source_type is SourceType.CALCULATED
    for sample,original in zip(typed.references,records):
        assert sample.reference_id==original.id
        assert sample.source.source_type is SourceType.REFERENCE_VESSEL_DATA
        assert sample.source.verification_status is VerificationStatus.UNVERIFIED
        assert sample.source.notes==original.source
        assert sample.source.document is None


def test_explicit_legacy_regression_goldens_and_times_unchanged() -> None:
    """A known reference fit remains m=.1, b=10, R²=1 and Q=35 at V=250."""
    result=service().calculate_v2(TransferPumpEmpiricalInput(source_capacity=250))
    model=result.estimate.regression_model
    assert (model.slope,model.intercept,model.r_squared)==(.1,10,1)
    assert result.estimate.predicted_pump_capacity_m3h==35
    assert result.estimate.estimated_emptying_time_hours==250/35
    assert result.estimate.estimated_emptying_time_minutes==(250/35)*60
    assert result.resolution.required_capacity_12h_m3h==250/12


def test_invalid_empirical_data_and_reference_snapshot_safety() -> None:
    """Legacy error results remain error results, while valid used reference values are immutable copies."""
    instance=service()
    invalid=instance.calculate_v2(TransferPumpEmpiricalInput(source_capacity=250),references=[])
    assert not invalid.estimate.is_successful and invalid.calculated_capacity is None
    assert invalid.required_flow_m3_h is None
    records=references();result=instance.calculate_v2(TransferPumpEmpiricalInput(source_capacity=250),references=records)
    records[0].fuel_capacity_m3=999
    assert result.references[0].fuel_capacity_m3==100
    with pytest.raises(FrozenInstanceError): result.references[0].fuel_capacity_m3=999


def test_future_context_is_preserved_but_nothing_hydraulic_is_calculated() -> None:
    """Hs/ENPY/NPSHr are optional externally supplied facts; no curves, power or live links exist."""
    empty=PumpIntegrationContext()
    assert all(value is None for value in asdict(empty).values())
    context=PumpIntegrationContext(system_id=uuid4(),circuit_id=uuid4(),fluid_id=uuid4(),
        selected_pump_reference_id=uuid4(),required_head_m=20,available_npsh_m=4,
        required_npsh_m=3,npsh_margin_m=None)
    result=TransferPumpService(object()).calculate_v2(TransferPumpDesignInput(
        transfer_volume_m3=120,target_transfer_time_h=3,context=context))
    assert result.input.context is context
    assert result.input.context.npsh_margin_m is None
    empirical=service().calculate_v2(TransferPumpEmpiricalInput(source_capacity=250,context=context))
    assert empirical.input.context is context and empirical.required_flow_m3_h is None


@pytest.mark.parametrize('mode',[TransferPumpMode.DESIGN,TransferPumpMode.EMPIRICAL])
def test_additive_state_roundtrip_includes_context_sources_and_unfinished_fields(mode: TransferPumpMode) -> None:
    """Use primitive, language-neutral state while keeping incomplete raw input editable."""
    context=PumpIntegrationContext(system_id=uuid4(),circuit_id=uuid4(),fluid_id=uuid4(),required_head_m=20)
    state=TransferPumpPageState(mode=mode,volume_text='120,123456',target_time_text='3',
        pump_capacity_text='unfinished',context=context,
        target_time_source=SourceReference(source_type=SourceType.PROJECT_CRITERION,
            document='Synthetic project requirement',effective_date=date(2026,1,1)))
    payload=state.to_payload();encoded=json.dumps(payload,allow_nan=False,sort_keys=True)
    assert payload['mode']==mode.value and payload['context']['system_id']==str(context.system_id)
    restored=TransferPumpPageState.from_page_payload({'transfer_v2':json.loads(encoded),'future':'ignored'})
    assert restored==state
    assert json.dumps(restored.to_payload(),allow_nan=False,sort_keys=True)==encoded


def test_legacy_state_is_empirical_and_unknown_state_version_is_not_reinterpreted() -> None:
    """An old regression result is never used as a required design capacity."""
    legacy={'capacity':'250','capacity_input_mode':'VOLUME','result':'old regression estimate'}
    restored=TransferPumpPageState.from_page_payload(legacy)
    assert restored.mode is TransferPumpMode.EMPIRICAL
    assert restored.volume_text==restored.target_time_text==''
    with pytest.raises(ValueError): TransferPumpPageState.from_page_payload({'transfer_v2':{'version':2,'mode':'DESIGN'}})


class Group(Widget):
    """Capture which calculation mode's input/result groups are visible."""
    def grid(self,**kwargs: object) -> None: self.visible=True
    def grid_remove(self) -> None: self.visible=False


def design_panel() -> TransferPumpDesignPanel:
    """Use actual panel callbacks with no Tk interpreter or reference dependency."""
    panel=TransferPumpDesignPanel.__new__(TransferPumpDesignPanel)
    panel._service=TransferPumpService(object());panel._translate=Translator('tr').translate
    panel._state=TransferPumpPageState();panel._suppress=False
    panel._fields={key:Var(value) for key,value in dict(volume='120',target_time='3',pump_capacity='60').items()}
    panel._flow=Var();panel._time=Var();panel._status=Var();panel._error=Var()
    # The production renderer now manages empty/calculated visual surfaces.
    panel._results=Group();panel._results.master=None
    panel._results.winfo_children=lambda:()
    panel._empty_result=Group();panel._flow_metric=Group();panel._time_metric=Group()
    panel._events=[];panel._changed=lambda:panel._events.append('changed')
    panel.visible=True
    panel.grid=lambda: setattr(panel,'visible',True)
    panel.grid_remove=lambda:setattr(panel,'visible',False)
    return panel


def transfer_page() -> TransferPumpPage:
    """Real parent handlers keep both modes' independent variables and result caches."""
    page=TransferPumpPage.__new__(TransferPumpPage)
    page._service=service();page._translate=Translator('tr').translate
    page._calculation_mode=TransferPumpMode.DESIGN
    page._design_panel=design_panel();page._method_box=Group();page._method_explanation=Var()
    page._upper=Group();page._analysis=Group()
    page._capacity=Var('250');page._capacity_mode=Var('VOLUME')
    page._capacity_mode_labels={'VOLUME':'VOLUME','MASS':'MASS'}
    page._capacity_mode_codes={'VOLUME':'VOLUME','MASS':'MASS'}
    page._message=Var();page._status_messages=[];page._suppress_dirty=False
    page._events=[];page._dirty_callback=lambda:page._events.append('dirty')
    page._clear_estimate_summary=lambda:None
    page._update_capacity_input_presentation=lambda:None
    page._sync_result_empty_state=lambda:None
    page._refresh_chart=lambda:None
    page._refresh_formula_panel=lambda:None
    page._render_estimate=lambda:None
    page.refresh=lambda:None
    return page


def test_design_page_calculation_and_formula_view_use_stored_full_precision_results() -> None:
    """The page renders capacity/time/adequacy without performing formulas itself."""
    panel=design_panel();panel.calculate()
    assert panel._last_result.required_flow_m3_h==40
    assert panel._flow.get()=='40,00' and panel._time.get()=='2,00'
    assert 'karşılıyor' in panel._status.get()
    result=panel._last_result
    panel._service.calculate_v2=lambda _:pytest.fail('Formula View must not recalculate')
    assert 'Qgerekli' in '\n'.join(x.text for x in panel.formula_sections())
    assert panel._last_result is result
    panel._fields['volume'].set('240');panel._invalidate()
    assert not hasattr(panel,'_last_result') and panel._flow.get()=='—'


def test_mode_switch_keeps_independent_inputs_and_results() -> None:
    """Active mode controls visibility/primary result; switching never calculates or overwrites."""
    page=transfer_page();page._design_panel.calculate();design=page._design_panel._last_result
    page._calculate();empirical=page._estimate_result
    assert empirical.predicted_pump_capacity_m3h==35
    page._method_box.current(1);page._choose_calculation_mode()
    assert page._upper.visible and not page._design_panel.visible
    assert page._has_active_result()
    assert page._design_panel._last_result is design
    page._capacity.set('450');page._invalidate_estimate()
    assert page._design_panel._last_result is design
    page._calculate();empirical=page._estimate_result
    page._method_box.current(0);page._choose_calculation_mode()
    assert page._design_panel.visible and not page._upper.visible
    assert page._estimate_result is empirical
    assert page._capacity.get()=='450' and page._design_panel._fields['volume'].get()=='120'
    assert 'Qgerekli' in '\n'.join(s.text for s in page._formula_sections())


@pytest.mark.parametrize('mode',[TransferPumpMode.DESIGN,TransferPumpMode.EMPIRICAL])
def test_page_and_project_state_roundtrip_without_schema_change(mode: TransferPumpMode,project_database,project_service) -> None:
    """Use the existing project-state JSON row and preserve mode, both inputs and optional pump capacity."""
    from repositories.project_state_repository import ProjectStateRepository
    from services.project_persistence_service import ProjectPersistenceService
    page=transfer_page();page._calculation_mode=mode
    persistence=ProjectPersistenceService(project_service,ProjectStateRepository(project_database))
    project=persistence.create_project('Phase 10 synthetic test')
    with project_database.connection() as connection:
        before=connection.execute("SELECT name,sql FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
    payload=page.export_state();persistence.save({'schema_version':1,'transfer_pump':payload})
    _,workspace=persistence.open(project.id)
    restored=transfer_page();restored.load_state(workspace['transfer_pump'])
    assert restored._calculation_mode is mode
    assert restored._capacity.get()=='250'
    assert restored._design_panel._fields['pump_capacity'].get()=='60'
    assert restored._design_panel._fields['target_time'].get()=='3'
    assert not hasattr(restored._design_panel,'_last_result')
    assert restored.export_state()==payload
    with project_database.connection() as connection:
        assert connection.execute('SELECT version FROM schema_version').fetchone()[0]==1
        assert connection.execute("SELECT name,sql FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()==before


def test_real_page_legacy_load_selects_empirical_and_clear_starts_clean_design() -> None:
    """No saved estimate becomes required design flow, and project clear resets both forms."""
    page=transfer_page();page.load_state({'capacity':'250','capacity_input_mode':'VOLUME'})
    assert page._calculation_mode is TransferPumpMode.EMPIRICAL
    assert not page._design_panel.visible and page._upper.visible
    assert page._design_panel._fields['volume'].get()==''
    page.clear_state()
    assert page._calculation_mode is TransferPumpMode.DESIGN
    assert page._capacity.get()==''
    assert all(not value.get() for value in page._design_panel._fields.values())


def test_empirical_classification_is_explicit_and_not_a_tl_rule() -> None:
    """Both language catalogues distinguish estimation from actual required design flow."""
    for language in ('tr','en'):
        translate=Translator(language).translate
        assert translate('transfer.mode.DESIGN')!=translate('transfer.mode.EMPIRICAL')
        assert 'emp' in translate('transfer.mode.EMPIRICAL').lower() or 'ampirik' in translate('transfer.mode.EMPIRICAL').lower()
        assert '12' not in translate('transfer.mode.help.DESIGN')
    assert 'Türk Loydu formülü' in Translator('tr').translate('formula.regression_model_note')
    assert 'değildir' in Translator('tr').translate('formula.regression_model_note')
    assert service().calculate_v2(TransferPumpEmpiricalInput(source_capacity=250)).references[0].source.source_type is not SourceType.TL_RULE
