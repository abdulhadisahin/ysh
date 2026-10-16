"""Historical calculation truth survives live edits without calculator/library reconstruction."""
from dataclasses import FrozenInstanceError, replace, asdict
from datetime import date, datetime, timezone, timedelta
import json
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

from engineering.module_registry import ModuleCode
from engineering.system_context import SystemContext
from engineering.snapshots.models import CalculationSnapshot
from engineering.snapshots.builders import build_snapshot, build_pipe_v2_snapshot
from engineering.snapshots.serialization import canonical, primitive
from engineering.formula.models import CheckStatus
from engineering.provenance import EngineeringValue, OverridePolicy, SourceReference, SourceType, VerificationStatus
from engineering.pipe_design.v2_models import PipeProvenance
from engineering.pipe_design.v2_calculator import PipeDesignV2Calculator
from engineering.pipe_design.models import PipeDesignCalculationResult, PipeDiameterInput, WallThicknessInput
from engineering.pipe_design.calculator import PipeDesignCalculator
from engineering.pipe_design.transfer import PipeInputState
from engineering.warning_rules import EngineeringFinding, WarningSeverity, MAN_EVERLLENCE_SOURCE_ID
from engineering.transfer_pump.v2_models import TransferPumpDesignInput, TransferPumpEmpiricalInput
from services.discharge_head_loss_service import DischargeHeadLossService
from services.suction_npsh_service import SuctionNPSHService
from services.snapshot_history_service import SnapshotHistoryService, HistoryError
from services.snapshot_events import notify_success
from services.project_service import ProjectService
from repositories.project_repository import ProjectRepository
from repositories.calculation_repository import CalculationRepository
from services.calculation_service import CalculationService
from ui.main_window import MainWindow
from ui.dialogs.calculation_history import history_summary
from ui.widgets.formula_steps import step_sections
from i18n.translator import Translator
from i18n.messages_tr import MESSAGES as TR
from i18n.messages_en import MESSAGES as EN
from .test_discharge_v2_phase8 import inputs, source, revised, page_stub
from .test_suction_v2_phase9 import suction_input, enpy_input, suction_page
from .test_transfer_pump_v2_phase10 import service as transfer_service, design_panel, transfer_page
from .test_pipe_design_v2 import request, configured, candidate
from .test_system_context_phase12 import context
from .test_engineering_library_phase13 import library


@pytest.fixture
def history(project_database):
    """Use existing calculations/project tables with no schema extension."""
    project=ProjectService(ProjectRepository(project_database)).create_project('Snapshot project')
    repository=CalculationRepository(project_database)
    return SnapshotHistoryService(repository),repository,project


def discharge_snapshot(project_id=None, *, state=None, **changes):
    """Calculate before freezing; builders never evaluate the equations."""
    result=DischargeHeadLossService(object()).calculate_v2(inputs(state))
    return build_snapshot(ModuleCode.DISCHARGE,'hydraulics',result,context=context(),project_id=project_id,**changes),result


def test_snapshot_identity_version_timestamp_precision_units_and_deep_immutability() -> None:
    snapshot,result=discharge_snapshot()
    assert isinstance(snapshot.snapshot_id,UUID) and snapshot.schema_version==1
    assert snapshot.module_code is ModuleCode.DISCHARGE and snapshot.created_at.utcoffset() is not None
    assert CalculationSnapshot.from_payload(json.loads(snapshot.to_json()))==snapshot
    assert snapshot.to_json()==snapshot.to_json()
    with pytest.raises(FrozenInstanceError): snapshot.stage='other'
    copy=snapshot.evidence;copy['facts']['outputs']['flow_velocity_m_s']=0
    result.flow_velocity_m_s=987.654321;result.warnings.clear();result.metadata.clear()
    assert snapshot.evidence['facts']['outputs']['flow_velocity_m_s']!=0
    assert snapshot.evidence['facts']['outputs']['flow_velocity_m_s']!=987.654321
    first=snapshot.formula_steps[0]
    assert first.result_value==snapshot.evidence['facts']['outputs']['flow_velocity_m_s']
    assert first.result_unit=='m/s' and first.variables[0].unit=='m³/h'
    assert snapshot.context==context()


@pytest.mark.parametrize('bad',[object(),lambda:None,float('nan'),float('inf'),{1:'bad'},datetime(2025,1,1)])
def test_codec_rejects_services_callbacks_nonfinite_and_naive_time(bad) -> None:
    with pytest.raises((ValueError,TypeError)): canonical(bad)


@pytest.mark.parametrize('field,value',[('snapshot_schema_version',2),('snapshot_schema_version',True),
    ('module_code','localized module'),('snapshot_id','bad'),('created_at','2025-01-01T00:00:00')])
def test_unsupported_or_corrupt_snapshot_payloads_are_not_reconstructed(field,value) -> None:
    snapshot,_=discharge_snapshot();payload=snapshot.to_payload();payload[field]=value
    with pytest.raises((ValueError,TypeError)): CalculationSnapshot.from_payload(payload)


def test_engineering_value_override_source_and_enum_date_uuid_roundtrip() -> None:
    src=SourceReference(source_type=SourceType.D243_CRITERION,source_organization='Original org',document='Original document',
                        revision='A',effective_date=date(2025,1,2),verification_date=date(2025,2,3),verification_status=VerificationStatus.USER_SUPPLIED)
    value=EngineeringValue(used_value=2,recommended_value=1.23456789012345,unit='m/s',source=src,
        symbol='V',override_policy=OverridePolicy.SUGGESTED,override_reason='Explicit override',selection_reason='Project choice')
    inp=request(provenance=PipeProvenance(design_velocity=value))
    result=PipeDesignV2Calculator().calculate(inp,[candidate(dimension_source=src)])
    snapshot=build_pipe_v2_snapshot(result,inp,context=context())
    restored=CalculationSnapshot.from_payload(json.loads(snapshot.to_json()))
    frozen=next(s for s in restored.formula_steps if s.step_id=='pipe.D').used_values[0]
    assert frozen==value and frozen.is_overridden and frozen.override_policy is OverridePolicy.SUGGESTED
    assert frozen.source.effective_date==date(2025,1,2) and frozen.source.verification_date==date(2025,2,3)
    assert frozen.source.verification_status is VerificationStatus.USER_SUPPLIED
    assert restored.context.system_id==context().system_id
    source_copy=replace(src,document='Changed',revision='B')
    value_copy=value.with_used_value(2.1,override_reason='New override')
    assert frozen.source.document=='Original document' and frozen.source.revision=='A'
    assert frozen.used_value==2 and frozen.recommended_value==1.23456789012345


@pytest.mark.parametrize('configured_rules',[False,True])
@pytest.mark.parametrize('bend',[False,True])
def test_pipe_v2_snapshots_freeze_selection_and_only_applied_optional_rules(configured_rules,bend) -> None:
    inp=(configured if configured_rules else request)(bend_allowance_enabled=bend,bend_radius_mm=300 if bend else None)
    selection=PipeDesignV2Calculator().calculate(inp,[candidate()])
    snapshot=build_pipe_v2_snapshot(selection,inp,context=context())
    data=snapshot.evidence['facts'];frozen=data['selection']
    assert frozen['flow_rate_m3_h']==selection.flow_rate_m3_h
    assert frozen['theoretical_internal_diameter_mm']==selection.theoretical_internal_diameter_mm
    assert frozen['selected_pipe']['outside_diameter_mm']==selection.outside_diameter_mm
    assert frozen['selected_pipe']['wall_thickness_mm']==selection.selected_wall_thickness_mm
    assert frozen['actual_velocity_m_s']==selection.actual_velocity_m_s
    assert frozen['wall']['base_wall_mm']==selection.wall.base_wall_mm
    assert frozen['wall']['bend_allowance_mm']==selection.wall.bend_allowance_mm
    assert frozen['wall']['corrosion_allowance_mm']==selection.wall.corrosion_allowance_mm
    assert frozen['wall']['final_required_wall_mm']==selection.wall.final_required_wall_mm
    assert frozen['provenance']['source_factor']['used_value']==inp.weld_factor
    assert frozen['allowable_stress']['value']==selection.allowable_stress.value
    steps={s.step_id:s for s in snapshot.formula_steps}
    assert ('pipe.tolerance' in steps)==configured_rules and ('pipe.minimum' in steps)==configured_rules
    assert 'allowance_formula' not in snapshot.to_json()


def test_legacy_new_pipe_stage_records_exact_inputs_without_faking_old_state() -> None:
    calc=PipeDesignCalculator();diameter_input=PipeDiameterInput(20,2)
    result=PipeDesignCalculationResult(diameter=calc.calculate_diameter(diameter_input),trace={'diameter_input':asdict(diameter_input)})
    snapshot=build_snapshot(ModuleCode.PIPE_DESIGN,'diameter',result,context=context())
    assert snapshot.evidence['facts']['calculation']['trace']['diameter_input']==asdict(diameter_input)
    old=replace(result,trace={})
    with pytest.raises(ValueError): build_snapshot(ModuleCode.PIPE_DESIGN,'diameter',old,context=context())
    failed=replace(result,errors=['failed'])
    with pytest.raises(ValueError): build_snapshot(ModuleCode.PIPE_DESIGN,'diameter',failed,context=context())
    with pytest.raises(ValueError): build_snapshot(ModuleCode.PIPE_DESIGN,'wall',result,context=context())


@pytest.mark.parametrize('mode',['manual','synced','stale','missing'])
def test_discharge_applied_snapshot_status_revision_and_all_numerical_outputs_freeze(mode) -> None:
    state=PipeInputState()
    if mode!='manual':
        state=state.link_to(source())
        if mode=='stale': state=state.observe(revised(source()))
        if mode=='missing': state=state.observe(None)
    snapshot,result=discharge_snapshot(state=state if mode!='manual' else None)
    evidence=snapshot.evidence['facts'];inp=evidence['input'];outputs=evidence['outputs']
    assert inp['kinematic_viscosity_m2s']==2e-6 and inp['pipe_length_m']==20 and inp['roughness_mm']==.015
    assert inp['geodetic_head_m']==2 and len(inp['local_losses'])==1
    for key in ('flow_rate_m3_h','actual_internal_diameter_mm','flow_velocity_m_s','reynolds_number','friction_factor',
                'pipe_friction_loss_m','local_loss_coefficient_total','local_loss_m','total_hydraulic_loss_m','system_head_m'):
        assert outputs[key]==getattr(result,key)
    if mode!='manual':
        frozen=inp['pipe_input']['snapshot']
        assert frozen['source_selection_id']==str(source().selection_id) and frozen['source_revision']==1
        assert frozen['values']['actual_internal_diameter_mm']==101 and frozen['values']['flow_rate_m3_h']==20
        assert frozen['values']['nps']=='TEST NPS' and frozen['values']['schedule']=='TEST SCH'
        assert inp['pipe_input']['status']==state.status.value
        later=state.observe(revised(source()))
        assert later.used_values==state.used_values
    before=snapshot.to_json();result.metadata.clear();result.flow_rate_m3_h=999
    assert snapshot.to_json()==before


@pytest.mark.parametrize('required',[None,3,99])
def test_suction_enpy_freezes_inputs_hydraulics_margin_and_compliance(required) -> None:
    result=SuctionNPSHService(object()).calculate_v2(suction_input(),enpy_input(npsh_required_m=required))
    snapshot=build_snapshot(ModuleCode.SUCTION_NPSH,'enpy',result,context=context())
    facts=snapshot.evidence['facts'];inp=facts['input'];hyd=facts['hydraulic_input'];out=facts['outputs']
    assert inp['density_kg_m3']==850 and inp['static_suction_height_m']==2 and inp['npsh_required_m']==required
    assert inp['suction_pressure']==1.2 and inp['suction_pressure_unit']=='bar'
    assert inp['vapour_pressure']==.03 and inp['vapour_pressure_unit']=='bar'
    assert hyd['viscosity']==2 and hyd['viscosity_unit']=='cSt'
    assert facts['hydraulic_outputs']['metadata']['viscosity_m2s']==2e-6
    assert out['metadata']['suction_pressure_pa']==120000 and out['metadata']['vapour_pressure_pa']==3000
    assert out['enpym_available_m']==result.enpym_available_m and out['npsh_margin_m']==result.npsh_margin_m
    steps={s.step_id:s for s in snapshot.formula_steps}
    assert ('suction.margin' in steps)==(required is not None)
    if required is not None:
        assert steps['suction.ENPYm'].check.status is (CheckStatus.WARNING if result.npsh_margin_m<0 else CheckStatus.PASS)
    result.enpym_available_m=-999
    assert snapshot.evidence['facts']['outputs']['enpym_available_m']!=-999


def test_hydraulic_only_suction_is_a_distinct_successful_stage() -> None:
    result=SuctionNPSHService(object()).calculate_suction_loss_v2(suction_input())
    snapshot=build_snapshot(ModuleCode.SUCTION_NPSH,'hydraulics',result,context=context())
    assert snapshot.stage=='hydraulics'
    assert all(s.result_symbol!='ENPYm' for s in snapshot.formula_steps)
    with pytest.raises(ValueError): build_snapshot(ModuleCode.SUCTION_NPSH,'enpy',result,context=context())


@pytest.mark.parametrize('capacity',[None,39,40,41])
def test_transfer_design_freezes_active_mode_adequacy_and_time(capacity) -> None:
    result=transfer_service().calculate_v2(TransferPumpDesignInput(transfer_volume_m3=120,target_transfer_time_h=3,selected_pump_capacity_m3_h=capacity))
    snapshot=build_snapshot(ModuleCode.TRANSFER_PUMP,'design',result,context=context())
    frozen=snapshot.evidence['facts']['calculation']
    assert frozen['mode']=='DESIGN' and frozen['input']['transfer_volume_m3']==120
    assert frozen['input']['target_transfer_time_h']==3 and frozen['input']['selected_pump_capacity_m3_h']==capacity
    assert frozen['required_capacity']['used_value']==result.required_flow_m3_h
    assert frozen['status']==result.status.value and frozen['transfer_time_h']==result.transfer_time_h


def test_transfer_empirical_coefficients_reference_inputs_and_model_identity_freeze() -> None:
    result=transfer_service().calculate_v2(TransferPumpEmpiricalInput(source_capacity=250))
    snapshot=build_snapshot(ModuleCode.TRANSFER_PUMP,'empirical',result,context=context())
    data=snapshot.evidence['facts']['calculation']
    assert data['mode']=='EMPIRICAL' and data['required_flow_m3_h'] is None
    assert data['estimate']['regression_model']['slope']==.1 and data['estimate']['regression_model']['intercept']==10
    assert data['estimate']['predicted_pump_capacity_m3h']==35
    assert len(data['references'])==3 and data['references'][0]['source']['source_type']=='REFERENCE_VESSEL_DATA'
    assert snapshot.model_version=='TRANSFER_OLS_VESSEL_REFERENCE_1'
    result.estimate.regression_model.slope=999;result.estimate.predicted_pump_capacity_m3h=999
    assert snapshot.evidence['facts']['calculation']==data


def test_findings_and_warning_source_metadata_freeze_without_reevaluation() -> None:
    finding=EngineeringFinding('test',WarningSeverity.ENGINEERING_WARNING,'warning.velocity.outside_recommended_range',
                               9,1,7,'m/s',MAN_EVERLLENCE_SOURCE_ID,{'system':'FUEL'})
    snapshot,_=discharge_snapshot(findings=(finding,))
    evidence=snapshot.evidence
    assert evidence['findings'][0]['upper_bound']==7
    assert evidence['findings'][0]['severity']=='ENGINEERING_WARNING'
    assert evidence['finding_sources'][0]['identifier']==MAN_EVERLLENCE_SOURCE_ID
    finding.context['system']='CHANGED'
    assert snapshot.evidence['findings'][0]['context']['system']=='FUEL'


def test_append_only_multiple_history_order_isolation_and_legacy_compatibility(history) -> None:
    service,repo,project=history
    first,_=discharge_snapshot(project.id);second,_=discharge_snapshot(project.id)
    tied=replace(second,created_at=first.created_at)
    service.append(first);service.append(tied)
    rows=service.list(project.id)
    assert len(rows)==2 and rows==tuple(sorted((first,tied),key=lambda s:(s.created_at,str(s.snapshot_id)),reverse=True))
    assert service.list(uuid4())==()
    with pytest.raises(HistoryError): service.append(first)
    assert service.list(project.id)==rows
    with pytest.raises(ValueError): repo.upsert_for_project_and_type(project.id,f'snapshot:discharge_head_loss:{first.snapshot_id}',{}, {},{})
    legacy=CalculationService(repo).save(project.id,'legacy_pipe',{'Q':20},{'D':123},{})
    assert service.legacy(project.id)==(legacy,)
    assert len(service.list(project.id))==2
    assert not hasattr(service,'update') and not hasattr(service,'delete')


def test_snapshot_storage_failure_is_atomic_and_projectless_session_is_explicit(history) -> None:
    service,repo,project=history
    snapshot,_=discharge_snapshot(uuid4())
    with pytest.raises(HistoryError): service.append(snapshot)
    assert service.list(project.id)==()
    unassigned,_=discharge_snapshot()
    service.append(unassigned)
    assert service.list(None)==(unassigned,) and service.list(project.id)==()
    assert SnapshotHistoryService(repo).list(None)==()


def test_historical_view_has_no_calculator_or_live_library_lookup(history,monkeypatch) -> None:
    service,repo,project=history;snapshot,_=discharge_snapshot(project.id);service.append(snapshot)
    monkeypatch.setattr(DischargeHeadLossService,'calculate_v2',lambda *a,**k:pytest.fail('historical recalculation'))
    monkeypatch.setattr(PipeDesignV2Calculator,'calculate',lambda *a,**k:pytest.fail('historical pipe lookup'))
    stored=service.list(project.id)[0]
    for messages in (TR,EN):
        for step in stored.formula_steps:
            sections=step_sections(step,messages.__getitem__)
            assert sections
    assert history_summary(stored)==history_summary(snapshot)


def test_live_source_library_context_edit_does_not_change_persisted_history(history,library,monkeypatch) -> None:
    service,repo,project=history;lib,records=library
    src=records['sources'].reference
    value=EngineeringValue(used_value=2,recommended_value=1.5,unit='m/s',source=src,
        symbol='V',override_policy=OverridePolicy.SUGGESTED,override_reason='Original override')
    inp=request(provenance=PipeProvenance(design_velocity=value))
    result=PipeDesignV2Calculator().calculate(inp,[candidate(dimension_source=src)])
    snapshot=build_pipe_v2_snapshot(result,inp,context=context(),project_id=project.id);service.append(snapshot)
    before=snapshot.to_json()
    source_values=lib.form_values('sources',records['sources']);source_values.update(document='Changed source',revision='NEW',source_organization='Changed org')
    lib.save('sources',source_values,records['sources'].id)
    material_values=lib.form_values('materials',records['materials']);material_values['roughness_mm']=999
    lib.save('materials',material_values,records['materials'].id)
    current_context=context('FRESH_WATER')
    monkeypatch.setattr(lib._repos['sources'],'get',lambda *a:pytest.fail('live historical source lookup'))
    stored=service.list(project.id)[0]
    assert stored.to_json()==before and stored.context==context() and stored.context!=current_context
    frozen=next(s for s in stored.formula_steps if s.step_id=='pipe.D').used_values[0]
    assert frozen.source.document==src.document and frozen.source.revision==src.revision
    assert frozen.source.source_organization==src.source_organization
    assert frozen.override_reason=='Original override'


def test_actual_roughness_library_record_is_frozen_at_calculation_time(history,library) -> None:
    service,repo,project=history;lib,rows=library
    provider=SimpleNamespace(get_material=lambda identity:lib.get_record('materials',identity))
    result=DischargeHeadLossService(provider).calculate_v2(inputs(material_id=rows['materials'].id,roughness_mm=None))
    snapshot=build_snapshot(ModuleCode.DISCHARGE,'hydraulics',result,context=context(),project_id=project.id);service.append(snapshot)
    values=lib.form_values('materials',rows['materials']);values.update(roughness_mm=5,source='Changed legacy source note')
    lib.save('materials',values,rows['materials'].id)
    stored=service.list(project.id)[0]
    assert stored.evidence['facts']['input']['roughness_mm']==.123456789
    assert stored.evidence['facts']['outputs']['metadata']['used_material']['source']==rows['materials'].source


def test_page_success_hooks_do_not_fire_on_edit_load_invalid_or_failed_input() -> None:
    panel=design_panel();calls=[];panel._snapshot_listener=lambda *args:calls.append(args)
    panel.calculate();assert len(calls)==1 and calls[0][0]=='design'
    saved=calls[0][1];panel._fields['volume'].set('not a number');panel.calculate()
    assert len(calls)==1
    panel.load(panel.form_state());assert len(calls)==1
    page=transfer_page();page._snapshot_listener=lambda *args:calls.append(args)
    from engineering.transfer_pump.v2_models import TransferPumpMode
    page._calculation_mode=TransferPumpMode.EMPIRICAL;page._calculate()
    assert len(calls)==2 and calls[-1][0]=='empirical'


def test_snapshot_persistence_failure_keeps_current_result_and_shows_error(monkeypatch) -> None:
    import ui.main_window as module
    errors=[]
    monkeypatch.setattr(module.messagebox,'showerror',lambda *args,**kwargs:errors.append(args))
    class Failed:
        def append(self,snapshot): raise HistoryError('failure')
    panel=design_panel()
    window=SimpleNamespace(_snapshot_history=Failed(),_system_context=context(),_active_project=None,
                           _translate=Translator('tr').translate,_root=object())
    panel._snapshot_listener=lambda stage,result,selection,findings:MainWindow._capture_calculation(window,ModuleCode.TRANSFER_PUMP,stage,result,selection,findings)
    panel.calculate()
    assert panel._last_result.required_flow_m3_h==40 and panel._flow.get()=='40,00'
    assert len(errors)==1 and errors[0][1]==TR['history.persistence_failed']


def test_history_service_and_listener_attachment_are_lazy(history,monkeypatch) -> None:
    service,repo,project=history
    monkeypatch.setattr(repo,'get_snapshot_records',lambda *a:pytest.fail('startup history read'))
    page=SimpleNamespace();transfer=SimpleNamespace(_design_panel=SimpleNamespace())
    window=SimpleNamespace(_pages={'discharge_head_loss':page,'transfer_pump':transfer})
    MainWindow.set_snapshot_history_service(window,service)
    assert callable(page._snapshot_listener) and callable(transfer._design_panel._snapshot_listener)


def test_legacy_project_without_history_and_legacy_incomplete_record_are_not_fabricated(history) -> None:
    service,repo,project=history
    assert service.list(project.id)==() and service.legacy(project.id)==()
    repo.upsert_for_project_and_type(project.id,'pipe_design',{'q':'20'},{'diameter_mm':123},{})
    legacy=service.legacy(project.id)[0]
    assert legacy.inputs=={'q':'20'} and 'source' not in legacy.outputs['trace']
    assert service.list(project.id)==()


def test_history_localization_and_readonly_ui_contracts() -> None:
    for messages in (TR,EN):
        for key in (key for key in TR if key.startswith('history.')): assert messages[key]
    root=Path(__file__).parents[1]
    ui=(root/'ui/dialogs/calculation_history.py').read_text(encoding='utf-8')
    assert 'sqlite3' not in ui and '.execute(' not in ui
    assert 'step_provider=lambda:snapshot.formula_steps' in ui
    assert "state='disabled'" in ui and 'calculate_v2' not in ui
    assert not any(word in ui for word in ('restore_snapshot','delete_snapshot','update_snapshot'))


@pytest.mark.parametrize('corruption', ['schema', 'identity', 'ownership', 'timestamp'])
def test_corrupt_history_is_rejected_without_live_reconstruction(history, monkeypatch, corruption) -> None:
    service, repo, project = history
    snapshot, _ = discharge_snapshot(project.id)
    service.append(snapshot)
    record = repo.get_snapshot_records(project.id)[0]
    if corruption == 'schema':
        record.outputs['results']['snapshot']['snapshot_schema_version'] = 999
    elif corruption == 'identity':
        record = replace(record, id=uuid4())
    elif corruption == 'ownership':
        record.outputs['results']['snapshot']['project_id'] = str(uuid4())
    else:
        record = replace(record, created_at=record.created_at + timedelta(seconds=1))
    monkeypatch.setattr(repo, 'get_snapshot_records', lambda identity: (record,))
    with pytest.raises(HistoryError, match='history.invalid_record'):
        service.list(project.id)


def test_real_hydraulic_page_success_events_append_exact_stages_only(history) -> None:
    service, _, project = history
    discharge, suction = page_stub(), suction_page()
    for page, module in ((discharge, ModuleCode.DISCHARGE), (suction, ModuleCode.SUCTION_NPSH)):
        page._engineering_findings = ()
        page._snapshot_listener = lambda stage, result, selection, findings, module=module: service.append(
            build_snapshot(module, stage, result, context=context(), project_id=project.id,
                           selection=selection, findings=findings))
    discharge._calculate()
    suction._calculate_suction_loss()
    suction._calculate_enpy()
    rows = service.list(project.id)
    assert [(row.module_code, row.stage) for row in rows] == [
        (ModuleCode.SUCTION_NPSH, 'enpy'), (ModuleCode.SUCTION_NPSH, 'hydraulics'),
        (ModuleCode.DISCHARGE, 'hydraulics')]
    before = tuple(row.to_json() for row in rows)
    discharge._fields['q'].set('invalid')
    discharge._calculate()
    suction._fields['pressure'].set('invalid')
    suction._calculate_enpy()
    assert tuple(row.to_json() for row in service.list(project.id)) == before
