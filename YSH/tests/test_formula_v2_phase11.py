"""Formula explainability consumes precomputed engineering truth, without a GUI."""
from dataclasses import asdict, replace
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest

from engineering.formula.common import step, used, variable
from engineering.formula.models import CalculationClassification, CheckStatus, FormulaCheck, FormulaStep, FormulaVariable, SelectionReason, ordered_steps
from engineering.formula.discharge import hydraulic_steps
from engineering.formula.suction import suction_steps
from engineering.formula.pipe import pipe_steps, legacy_pipe_steps
from engineering.formula.transfer import design_steps, empirical_steps
from engineering.pipe_design.calculator import PipeDesignCalculator
from engineering.pipe_design.v2_calculator import PipeDesignV2Calculator
from engineering.pipe_design.models import PipeDesignCalculationResult, PipeDiameterResult, WallThicknessInput
from engineering.pipe_design.transfer import PipeInputState
from engineering.provenance import EngineeringValue, OverridePolicy, SourceReference, SourceType, VerificationStatus
from engineering.transfer_pump.v2_models import TransferPumpDesignInput, TransferPumpEmpiricalInput, TransferPumpMode
from i18n.messages_en import MESSAGES as EN
from i18n.messages_tr import MESSAGES as TR
from services.discharge_head_loss_service import DischargeHeadLossService
from services.suction_npsh_service import SuctionNPSHService
from ui.widgets.formula_steps import number, source_rows, step_sections
from ui.pages.discharge_head_loss_page import DischargeHeadLossPage
from ui.pages.suction_npsh_page import SuctionNPSHPage
from ui.pages.pipe_design_page import PipeDesignPage
from ui.pages.transfer_pump_page import TransferPumpPage
from .test_discharge_v2_phase8 import inputs, source
from .test_suction_v2_phase9 import suction_input, enpy_input
from .test_transfer_pump_v2_phase10 import service
from .test_pipe_design_v2 import candidate, request, configured


def indexed(steps: tuple[FormulaStep, ...]) -> dict[str, FormulaStep]:
    """Index deterministic test observations without recomputing their outputs."""
    return {s.step_id:s for s in steps}


def test_common_model_precision_roundtrip_and_order() -> None:
    raw = 1.2345678901234567
    v = variable("Q", raw, "m³/h")
    assert FormulaVariable(**asdict(v)) == v
    s = step("a", "Q", raw, "m³/h", "Q", (v,), 1)
    assert ordered_steps((replace(s,step_id='b'),s,replace(s,step_id='z',display_order=0)))[0].step_id=='z'
    assert [x.step_id for x in ordered_steps((replace(s,step_id='b'),s))]==['a','b']
    assert number(raw)=='1,23'
    assert step_sections(s,TR.__getitem__)[-1].text=='Q = 1,23 m³/h'
    assert s.result_value==raw and s.variables[0].value==raw
    assert s.check is None


@pytest.mark.parametrize('status', list(CheckStatus))
@pytest.mark.parametrize('classification', list(CalculationClassification))
def test_check_and_classification_are_independent(status, classification) -> None:
    s = step('x','Q',1,'','Q',(),0,classification=classification,check=FormulaCheck(status=status))
    assert step_sections(s,EN.__getitem__)[-1].text==EN[f'formula2.check.{status.value}']
    assert EN[f'formula2.classification.{classification.value}']


@pytest.mark.parametrize('source_type', list(SourceType))
def test_all_sources_are_localized_and_null_metadata_is_omitted(source_type) -> None:
    src=SourceReference(source_type=source_type)
    for messages in (TR,EN):
        rows=source_rows(src,messages.__getitem__)
        assert rows==((messages['formula2.source.source_type'],messages[f'formula2.source_type.{source_type.value}']),)


@pytest.mark.parametrize('status',list(VerificationStatus))
def test_verification_and_existing_source_fields_are_exposed(status) -> None:
    src=SourceReference(source_type=SourceType.PIPE_STANDARD,document='TEST',verification_status=status,
                        verification_date=date(2025,1,2),article='A',table='T')
    for messages in (TR,EN):
        rows=source_rows(src,messages.__getitem__)
        assert messages[f'formula2.verification_status.{status.value}'] in dict(rows).values()
        assert '2025-01-02' in dict(rows).values()
        assert len(rows)==6


def test_optional_sections_and_override_visibility() -> None:
    s=step('x','Q',2,'m³/h','Q',(),0)
    assert [x.key for x in step_sections(s,TR.__getitem__)]==['formula','result']
    value=EngineeringValue(used_value=3,recommended_value=2,unit='mm',symbol='c',
        source=SourceReference(source_type=SourceType.D243_CRITERION),override_policy=OverridePolicy.SUGGESTED,
        override_reason='Explicit project override')
    sections=step_sections(replace(s,used_values=(value,)),TR.__getitem__)
    text='\n'.join(section.text for section in sections)
    assert '2,00' in text and '3,00' in text and value.override_reason in text
    assert TR['formula2.reason.D243_CRITERION'] in text
    assert TR['formula2.source_type.TL_RULE'] not in text


@pytest.mark.parametrize('linked',[False,True])
def test_discharge_values_and_applied_snapshot_identity(linked) -> None:
    state=PipeInputState().link_to(source()) if linked else None
    result=DischargeHeadLossService(object()).calculate_v2(inputs(state))
    steps=hydraulic_steps(result)
    assert [s.result_symbol for s in steps]==['V','Re','f','hf','hL','hhat','Hs']
    expected=[result.flow_velocity_m_s,result.reynolds_number,result.friction_factor,result.pipe_friction_loss_m,
              result.local_loss_m,result.total_hydraulic_loss_m,result.system_head_m]
    assert [s.result_value for s in steps]==expected
    values={v.symbol:v for s in steps for v in s.variables}
    assert {key:values[key].value for key in ('Q','Di','L','k','ν','Ktotal','Hgeo')}=={
        'Q':20,'Di':101,'L':20,'k':.015,'ν':2e-6,'Ktotal':1,'Hgeo':2}
    for symbol in ('Q','Di'):
        assert values[symbol].reason is (SelectionReason.LINKED_PIPE_SELECTION if linked else SelectionReason.USER_INPUT)
        assert values[symbol].source_selection_id==(source().selection_id if linked else None)
        assert values[symbol].source_revision==(1 if linked else None)


def test_hydraulic_adapter_uses_injected_precomputed_values_without_calculator(monkeypatch) -> None:
    result=DischargeHeadLossService(object()).calculate_v2(inputs())
    result.flow_velocity_m_s=123.456789
    result.pipe_friction_loss_m=987.654321
    from engineering.head_loss.calculator import DischargeHeadLossCalculator
    monkeypatch.setattr(DischargeHeadLossCalculator,'calculate',lambda *args:pytest.fail('recalculated'))
    steps=indexed(hydraulic_steps(result))
    assert steps['discharge.V'].result_value==123.456789
    assert steps['discharge.hf'].result_value==987.654321


@pytest.mark.parametrize('offset,status',[(-.5,CheckStatus.PASS),(0,CheckStatus.PASS),(.5,CheckStatus.WARNING)])
def test_enpy_check_preserves_equality_and_existing_warning_semantics(offset,status) -> None:
    svc=SuctionNPSHService(object())
    loss=svc.calculate_suction_loss_v2(suction_input())
    available=svc.calculate_enpy_v2(loss,enpy_input(npsh_required_m=None)).enpym_available_m
    result=svc.calculate_enpy_v2(loss,enpy_input(npsh_required_m=available+offset))
    steps=indexed(suction_steps(result))
    s=steps['suction.ENPYm']
    assert s.result_value==result.enpym_available_m
    assert s.check.status is status and s.check.operator=='>='
    assert s.check.reference_value==result.input.npsh_required_m
    assert any(w.code=='npsh_below_required' for w in result.warnings)==(status is CheckStatus.WARNING)
    values={v.symbol:v.value for v in s.variables}
    assert values==dict(PE=120000,Pb=3000,ρ=850,g=9.80665,HEgeo=2,he=loss.total_hydraulic_loss_m)
    assert steps['suction.margin'].result_value==result.npsh_margin_m


def test_enpy_without_required_has_no_fabricated_check_and_never_recalculates(monkeypatch) -> None:
    result=SuctionNPSHService(object()).calculate_v2(suction_input(),enpy_input(npsh_required_m=None))
    result.enpym_available_m=432.123456
    from engineering.suction_npsh.calculator import SuctionNPSHCalculator
    monkeypatch.setattr(SuctionNPSHCalculator,'calculate_enpy',lambda *a:pytest.fail('recalculated'))
    steps=indexed(suction_steps(result))
    assert steps['suction.ENPYm'].result_value==432.123456
    assert steps['suction.ENPYm'].check is None and 'suction.margin' not in steps


@pytest.mark.parametrize('bend',[False,True])
@pytest.mark.parametrize('rules',[False,True])
def test_pipe_active_and_unconfigured_steps_are_honest(bend,rules) -> None:
    inp=(configured if rules else request)(bend_allowance_enabled=bend,bend_radius_mm=300 if bend else None)
    result=PipeDesignV2Calculator().calculate(inp,[candidate()])
    steps=indexed(pipe_steps(result,inp))
    assert steps['pipe.D'].result_value==result.theoretical_internal_diameter_mm
    assert steps['pipe.stress'].result_value==result.allowable_stress.value
    assert steps['pipe.s0'].result_value==result.wall.base_wall_mm
    assert steps['pipe.b'].result_value==result.wall.bend_allowance_mm
    assert steps['pipe.c'].result_value==result.wall.corrosion_allowance_mm
    assert steps['pipe.wall'].result_value==result.wall.final_required_wall_mm
    assert steps['pipe.Di'].result_value==result.actual_internal_diameter_mm
    assert steps['pipe.actual_velocity'].result_value==result.actual_velocity_m_s
    assert ('pipe.minimum' in steps)==rules and ('pipe.tolerance' in steps)==rules
    if not bend:
        assert steps['pipe.b'].formula_text=='b = 0' and steps['pipe.b'].result_value==0
    assert all(s.classification is CalculationClassification.ENGINEERING_CALCULATION for s in steps.values())


def test_legacy_pipe_capture_never_reads_live_fields_or_evaluates_again(monkeypatch) -> None:
    inp=WallThicknessInput(100,16,195,1.8,.85,1,False,None)
    wall=PipeDesignCalculator().calculate_wall_thickness(inp)
    result=PipeDesignCalculationResult(wall_thickness=wall,trace={'wall_input':asdict(inp)})
    wall.base_wall_thickness_mm=987.654321
    monkeypatch.setattr(PipeDesignCalculator,'calculate_wall_thickness',lambda *a:pytest.fail('recalculated'))
    page=SimpleNamespace(_diameter_result={},_wall_result=wall.to_dict(),_wall_formula_result=result)
    assert indexed(PipeDesignPage._formula_steps(page))['pipe.s0'].result_value==987.654321
    assert indexed(legacy_pipe_steps(result))['pipe.stress'].variables[0].value==195


@pytest.mark.parametrize('capacity,status',[(None,CheckStatus.NOT_CONFIGURED),(39,CheckStatus.WARNING),(40,CheckStatus.PASS),(41,CheckStatus.PASS)])
def test_transfer_design_copies_result_and_adequacy(capacity,status) -> None:
    result=service().calculate_v2(TransferPumpDesignInput(transfer_volume_m3=120,target_transfer_time_h=3,
                                                       selected_pump_capacity_m3_h=capacity))
    steps=design_steps(result)
    assert steps[0].result_value==result.required_flow_m3_h==40
    assert steps[0].check.status is status
    assert len(steps)==(1 if capacity is None else 2)
    if capacity is not None:
        assert steps[1].result_value==result.transfer_time_h
    injected=replace(result,required_capacity=replace(result.required_capacity,used_value=123.123456,
                                                     recommended_value=123.123456))
    assert design_steps(injected)[0].result_value==123.123456


def test_empirical_model_provenance_and_active_mode_only(monkeypatch) -> None:
    result=service().calculate_v2(TransferPumpEmpiricalInput(source_capacity=250))
    result.estimate.predicted_pump_capacity_m3h=543.123456
    from engineering.transfer_pump.calculator import TransferPumpCalculator
    monkeypatch.setattr(TransferPumpCalculator,'calculate',lambda *a:pytest.fail('recalculated'))
    steps=empirical_steps(result)
    assert steps[0].result_value==543.123456
    assert {v.symbol:v.value for v in steps[0].variables}=={'Vfuel':250,'m':.1,'b':10,'R²':1}
    assert all(s.classification is CalculationClassification.EMPIRICAL_REFERENCE_ESTIMATE for s in steps)
    assert all(s.source_type is SourceType.REFERENCE_VESSEL_DATA for s in steps[0].sources)
    design=service().calculate_v2(TransferPumpDesignInput(transfer_volume_m3=120,target_transfer_time_h=3))
    page=SimpleNamespace(_calculation_mode=TransferPumpMode.DESIGN,_design_panel=SimpleNamespace(_last_result=design),_empirical_v2_result=result)
    assert TransferPumpPage._formula_steps(page)==design_steps(design)
    page._calculation_mode=TransferPumpMode.EMPIRICAL
    assert TransferPumpPage._formula_steps(page)==steps


def test_all_module_sections_have_tr_en_keys_and_no_missing_artifacts() -> None:
    discharge=DischargeHeadLossService(object()).calculate_v2(inputs())
    suction=SuctionNPSHService(object()).calculate_v2(suction_input(),enpy_input())
    inp=configured()
    pipe=PipeDesignV2Calculator().calculate(inp,[candidate()])
    design=service().calculate_v2(TransferPumpDesignInput(transfer_volume_m3=120,target_transfer_time_h=3,selected_pump_capacity_m3_h=40))
    empirical=service().calculate_v2(TransferPumpEmpiricalInput(source_capacity=250))
    for messages in (TR,EN):
        for s in (*hydraulic_steps(discharge),*suction_steps(suction),*pipe_steps(pipe,inp),*design_steps(design),*empirical_steps(empirical)):
            assert messages[s.title_key]
            assert messages[f'formula2.classification.{s.classification.value}']
            for section in step_sections(s,messages.__getitem__):
                assert messages[f'formula2.{section.key}']
                assert 'Unknown' not in section.text


def test_page_entrypoints_only_adapt_cached_results() -> None:
    discharge=DischargeHeadLossService(object()).calculate_v2(inputs())
    assert DischargeHeadLossPage._formula_steps(SimpleNamespace(_last_result=discharge))==hydraulic_steps(discharge)
    suction=SuctionNPSHService(object()).calculate_v2(suction_input(),enpy_input())
    assert SuctionNPSHPage._formula_steps(SimpleNamespace(_last_enpy=suction))==suction_steps(suction)
    assert SuctionNPSHPage._formula_steps(SimpleNamespace(_last_loss=suction.hydraulic))==hydraulic_steps(suction.hydraulic)
    assert DischargeHeadLossPage._formula_steps(SimpleNamespace())==()
    for name in ('pipe_design_page','discharge_head_loss_page','suction_npsh_page','transfer_pump_page'):
        text=(Path(__file__).parents[1]/'ui/pages'/f'{name}.py').read_text(encoding='utf-8')
        assert 'step_provider=self._formula_steps' in text
        assert 'def _formula_sections' in text


def test_v2_pipe_adapter_never_evaluates_configured_rules(monkeypatch) -> None:
    inp=configured()
    result=PipeDesignV2Calculator().calculate(inp,[candidate()])
    result=replace(result,wall=replace(result.wall,base_wall_mm=123.123456))
    from engineering.pipe_design.rules import AllowableStressRule, ManufacturingToleranceRule, MinimumWallRule
    for rule in (AllowableStressRule,ManufacturingToleranceRule,MinimumWallRule):
        monkeypatch.setattr(rule,'evaluate',lambda *a,**k:pytest.fail('rule re-evaluated'))
    assert indexed(pipe_steps(result,inp))['pipe.s0'].result_value==123.123456


def test_loaded_legacy_bend_does_not_invent_disabled_state() -> None:
    from engineering.pipe_design.models import WallThicknessResult
    result=PipeDesignCalculationResult(wall_thickness=WallThicknessResult(100,2,.5,1,3.5))
    bend=indexed(legacy_pipe_steps(result))['pipe.b']
    assert bend.result_value==.5 and bend.formula_text=='formula2.precomputed'


def test_reference_vessel_rows_and_compact_source_summary() -> None:
    result=service().calculate_v2(TransferPumpEmpiricalInput(source_capacity=250))
    s=empirical_steps(result)[0]
    assert [(v.context,v.value) for v in s.reference_variables]==[
        ('A',100),('A',20),('B',200),('B',30),('C',300),('C',40)]
    src=SourceReference(source_type=SourceType.PIPE_STANDARD,document='TEST',article='A',
                        verification_status=VerificationStatus.UNVERIFIED)
    regions=step_sections(replace(s,sources=(src,)),TR.__getitem__)
    summary=next(r for r in regions if r.key=='source' and r.details)
    assert 'TEST' in summary.text and TR['formula2.verification_status.UNVERIFIED'] in summary.text
    assert any(r.key=='reference_data' and r.details for r in regions)


def test_small_nonzero_inputs_stay_visible_without_losing_raw_precision() -> None:
    assert number(2e-6)=='2,00e-06'
    assert number(0)=='0,00'


def test_generic_renderer_uses_vertical_sections_and_existing_equation_renderer(monkeypatch) -> None:
    import ui.widgets.formula_steps as view
    calls=[]
    class Widget:
        def __init__(self,*args,**kwargs):
            self.managed=False
            self.command=kwargs.get('command')
            calls.append(kwargs)
        def grid(self,*args,**kwargs): self.managed=True
        def grid_remove(self): self.managed=False
        def winfo_manager(self): return 'grid' if self.managed else ''
        def columnconfigure(self,*args,**kwargs): pass
    for name in ('LabelFrame','Frame','Label','Button'):
        monkeypatch.setattr(view.ttk,name,Widget)
    equations=[]
    panel=SimpleNamespace(_content=object(),_translate=TR.__getitem__,
                          _render_section_content=lambda parent,section,style:equations.append(section.text))
    result=service().calculate_v2(TransferPumpEmpiricalInput(source_capacity=250))
    view.render_step(panel,empirical_steps(result)[0],0)
    assert equations==['Qpump = m × Vfuel + b']
    assert any(c.get('text')==TR['formula2.reference_data'] for c in calls)
    for call in calls:
        if call.get('command'):
            call['command']()
            call['command']()
