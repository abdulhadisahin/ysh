"""Fire HW evidence contracts; explicit example values are never defaults."""
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
from uuid import UUID

import pytest

from engineering.fire.calculators import calculate_hazen_williams, calculate_nozzle, FireCalculationBlocked
from engineering.fire.enums import FireSourceStatus, HWApplicability
from engineering.fire.foam_workflow import FoamRawInput, SourceReadiness
from engineering.fire.hazen_williams_workflow import HazenWilliamsWorkflowInput, HWService, HWWorkflowStatus
from engineering.fire.models import NozzleRequest
from engineering.fire.units import m3h_to_lpm
from engineering.fire.provenance import ParameterProvenance
from engineering.formula.models import FormulaStep, CalculationClassification
from engineering.pipe_design.transfer import PipeInputState, PipeInputMode, revise_selection
from engineering.pipe_design.v2_models import PipeCandidate, PipeSelection
from engineering.pipe_design.rules import DesignStatus
from engineering.provenance import EngineeringValue, SourceReference, SourceType, OverridePolicy, VerificationStatus
from engineering.snapshots.serialization import canonical, decode
from engineering.validation import ValidationError
from services.fire_hazen_williams_service import HazenWilliamsCalculationService, HWApplicabilityBlocked


UNITS = {"flow_lpm":"L/min","inside_diameter_mm":"mm","pipe_length_m":"m","hazen_williams_c":"1"}


def parameter(name, value, unit=None, status=FireSourceStatus.USER_PROJECT_ASSUMPTION):
    return ParameterProvenance(field_name=name,source_status=status,
        engineering_value=EngineeringValue(used_value=value,unit=unit or UNITS[name],
            source=SourceReference(source_type=SourceType.USER_INPUT,document="Explicit "+name,
                revision="test-v1",verification_status=VerificationStatus.USER_SUPPLIED),
            override_policy=OverridePolicy.USER_INPUT))


def request(q=2000,di=105,length=150,c=120,**changes):
    fields=dict(flow_lpm=parameter("flow_lpm",q),inside_diameter_mm=parameter("inside_diameter_mm",di),
        pipe_length_m=parameter("pipe_length_m",length),hazen_williams_c=parameter("hazen_williams_c",c),
        service=HWService.WATER,applicability=HWApplicability.WATER_ONLY)
    return HazenWilliamsWorkflowInput(**(fields | changes))


def calculate(inp=None):
    return HazenWilliamsCalculationService().calculate(inp if inp is not None else request())


def selection():
    source=SourceReference(source_type=SourceType.PIPE_STANDARD,document="Dimension source",revision="D3")
    pipe=PipeCandidate(id=UUID(int=2),standard_id=UUID(int=1),outside_diameter_mm=114,
        wall_thickness_mm=4,inside_diameter_mm=105,nominal_diameter="TEST",dimension_source=source)
    return PipeSelection(selection_id=UUID(int=3),revision=3,status=DesignStatus.RULE_NOT_CONFIGURED,
        theoretical_internal_diameter_mm=75,design_velocity_m_s=2,flow_rate_m3_h=120,
        selected_standard_id=pipe.standard_id,selected_standard_code="TEST",candidate=pipe,selected_pipe=pipe)


def linked():
    return PipeInputState().link_to(selection(),applied_at=datetime(2026,10,21,tzinfo=timezone.utc))


@pytest.mark.parametrize("c,expected",[(120,2.3717829024660286),(140,1.7832957445009588)])
def test_workbook_and_domain_equality_full_precision(c,expected):
    result=calculate(request(c=c)); domain=result.domain_result
    assert domain.total_pressure_loss_bar==pytest.approx(expected,rel=1e-13)
    assert domain.pressure_loss_per_m_bar==pytest.approx(expected/150,rel=1e-13)
    assert domain==calculate_hazen_williams(domain.input)
    assert [s.result_value for s in result.formula_steps]==[domain.pressure_loss_per_m_bar,domain.total_pressure_loss_bar]
    assert result.primary_result_key=="total_pressure_loss_bar"
    assert result.workflow_version=="fire.hazen_williams.workflow.v1"
    assert result.snapshot_payload["rule_ids"]==["FIRE.HW.EQUATION"]


def test_zero_length_and_manual_identity():
    result=calculate(request(length=0))
    assert result.domain_result.total_pressure_loss_bar==0
    assert result.domain_result.pressure_loss_per_m_bar>0
    assert result.formula_steps[1].result_value==0
    assert result.pipe_mode is PipeInputMode.MANUAL
    assert result.pipe_input is None
    capture=result.snapshot_payload["pipe_selection"]
    assert capture["source_selection_id"] is None and capture["source_revision"] is None
    assert capture["values"] is None and capture["inside_diameter_used_mm"]==105


def test_linked_actual_diameter_source_revision_and_manual_equality():
    state=linked()
    result=calculate(request(q=m3h_to_lpm(120),pipe_input=state,inside_diameter_mm=None))
    assert result.domain_result.input.inside_diameter_mm==105  # neither 114-8 nor theoretical75
    assert result.domain_result.total_pressure_loss_bar==calculate(request(q=m3h_to_lpm(120))).domain_result.total_pressure_loss_bar
    assert result.pipe_input is state and result.pipe_mode is PipeInputMode.LINKED
    capture=result.snapshot_payload["pipe_selection"]
    assert capture["source_revision"]==3 and capture["source_selection_id"]==str(UUID(int=3))
    assert capture["values"]["pipe_id"]==str(UUID(int=2))
    assert capture["values"]["dimension_source"]["revision"]=="D3"
    di=next(v for v in result.formula_steps[0].variables if v.symbol=="Di")
    assert di.source_revision==3 and di.source_selection_id==UUID(int=3)
    assert di.source.document=="Dimension source"
    assert result.input_provenance[1].source_status is FireSourceStatus.SOURCE_REQUIRED


def test_stale_kept_values_and_observed_revision_never_refreshed():
    original=selection()
    other_pipe=replace(original.selected_pipe,inside_diameter_mm=110)
    revised=revise_selection(original,replace(original,selected_pipe=other_pipe,flow_rate_m3_h=180))
    stale=linked().keep_current(revised)
    result=calculate(request(q=m3h_to_lpm(120),pipe_input=stale,inside_diameter_mm=None))
    assert result.domain_result.input.inside_diameter_mm==105
    assert result.domain_result.input.flow_lpm==m3h_to_lpm(120)
    assert result.domain_result.total_pressure_loss_bar==calculate(request(q=m3h_to_lpm(120))).domain_result.total_pressure_loss_bar
    capture=result.snapshot_payload["pipe_selection"]
    assert capture["status"]=="LINKED_STALE" and capture["kept_current"] is True
    assert capture["source_revision"]==3 and capture["observed_revision"]==4
    assert any(m.message_key=="fire.hw.pipe_review" for m in result.warnings)
    assert stale.snapshot.source_revision==3


@pytest.mark.parametrize("field,value",[("flow_lpm",1999),("inside_diameter_mm",104)])
def test_linked_mismatched_numeric_evidence_rejected(field,value):
    with pytest.raises(ValidationError):
        calculate(request(pipe_input=linked(),**{field:parameter(field,value)}))


@pytest.mark.parametrize("status",list(FireSourceStatus))
def test_c_provenance_never_upgraded(status):
    item=parameter("hazen_williams_c",120,status=status)
    result=calculate(request(hazen_williams_c=item))
    assert result.domain_result.total_pressure_loss_bar==calculate().domain_result.total_pressure_loss_bar
    assert result.input_provenance[3] is item
    p=result.snapshot_payload["provenance"][3]
    assert p["source_status"]==status.value
    assert p["engineering_value"]["source"]["verification_status"]=="USER_SUPPLIED"
    if status not in (FireSourceStatus.SOURCE_VERIFIED,FireSourceStatus.DERIVED_FROM_VERIFIED_RULE):
        assert any(m.field_name=="hazen_williams_c" and m.source_status is status for m in result.warnings)
    assert result.snapshot_payload["calculation_validity"]=="VALID"
    assert "REGULATORY_COMPLIANT" not in result.to_json()


def test_readiness_and_override_preserved():
    inp=request()
    inp=replace(inp,**{n:replace(getattr(inp,n),source_status=FireSourceStatus.SOURCE_VERIFIED) for n in UNITS})
    assert calculate(inp).status is HWWorkflowStatus.CALCULATED
    assert calculate(inp).source_readiness is SourceReadiness.READY
    item=replace(inp.hazen_williams_c,source_status=FireSourceStatus.SOURCE_VERIFIED_CONTEXT_DEPENDENT,
        engineering_value=replace(inp.hazen_williams_c.engineering_value,override_policy=OverridePolicy.SUGGESTED,
            recommended_value=140,override_reason="Explicit project selection"))
    result=calculate(replace(inp,hazen_williams_c=item))
    assert result.source_readiness is SourceReadiness.CONTEXT_REQUIRED
    used=result.formula_steps[0].used_values[1]
    assert used.used_value==120 and used.recommended_value==140
    assert used.override_reason=="Explicit project selection"


@pytest.mark.parametrize("field",list(UNITS))
def test_missing_input_no_default(field):
    with pytest.raises(ValidationError) as error:
        calculate(replace(request(),**{field:None}))
    assert error.value.issue.code=="required" and error.value.issue.field_key==field


@pytest.mark.parametrize("field,value",[("flow_lpm",0),("flow_lpm",-1),
    ("inside_diameter_mm",0),("inside_diameter_mm",-1),("pipe_length_m",-1),
    ("hazen_williams_c",0),("hazen_williams_c",-1)])
def test_domain_validation_forwarded(field,value):
    with pytest.raises(ValidationError) as error:
        calculate(replace(request(),**{field:parameter(field,value)}))
    assert error.value.issue.field_key==field


@pytest.mark.parametrize("value",[float('nan'),float('inf'),float('-inf'),True,"120",None])
def test_nonfinite_or_non_numeric_evidence_rejected(value):
    with pytest.raises((ValueError,TypeError,ValidationError)):
        calculate(request(hazen_williams_c=parameter("hazen_williams_c",value)))


@pytest.mark.parametrize("service,applicability",[
    (HWService.SEAWATER,HWApplicability.SEAWATER_SOURCE_REQUIRED),
    (HWService.FUEL,HWApplicability.OTHER_FLUID_SOURCE_REQUIRED),
    (HWService.UNKNOWN,HWApplicability.NOT_CONFIGURED),
    (HWService.SEAWATER,HWApplicability.WATER_ONLY),
    (HWService.FUEL,HWApplicability.WATER_ONLY),
    (HWService.UNKNOWN,HWApplicability.WATER_ONLY),
    (HWService.WATER,HWApplicability.SEAWATER_SOURCE_REQUIRED),
])
def test_blocked_before_domain_call(service,applicability,monkeypatch):
    monkeypatch.setattr("services.fire_hazen_williams_service.calculate_hazen_williams",
        lambda *_:pytest.fail("Blocked fluid reached domain calculator"))
    with pytest.raises(HWApplicabilityBlocked) as error:
        calculate(request(service=service,applicability=applicability))
    assert error.value.workflow_status=="BLOCKED_APPLICABILITY"
    assert error.value.status is FireSourceStatus.SOURCE_REQUIRED
    assert error.value.calculation_validity=="NOT_CALCULATED"


def test_formula_content_sources_and_stable_order():
    result=calculate(); steps=result.formula_steps
    assert [s.step_id for s in steps]==["fire.hw.unit_loss","fire.hw.total_loss"]
    assert [s.display_order for s in steps]==[0,1]
    assert [s.step_id for s in calculate(request(c=140)).formula_steps]==[s.step_id for s in steps]
    assert [s.formula_text for s in steps]==[
        "rHW = 605000 × Q^1.85 / (CHW^1.85 × Di^4.87)","ΔpHW = rHW × L"]
    assert [[v.symbol for v in s.variables] for s in steps]==[["Q","CHW","Di","rHW"],["rHW","L","ΔpHW"]]
    assert [[v.unit for v in s.variables] for s in steps]==[["L/min","1","mm","bar/m"],["bar/m","m","bar"]]
    for step in steps:
        assert step.substitution and repr(step.result_value) in step.substitution
        assert step.classification is CalculationClassification.ENGINEERING_CALCULATION
        assert step.sources[0].document=="ZF Inductor"
        assert step.sources[0].formula=="FIRE.HW.EQUATION"
        assert step.check is None
        assert all(v.source.document.startswith("Explicit ") for v in step.used_values)
    assert len({v.source.document for v in steps[0].used_values})==3
    assert "roughness" not in result.to_json() and "Colebrook" not in result.to_json()


@pytest.mark.parametrize("language",["tr","en"])
def test_existing_renderer_compatibility(language):
    from i18n.translator import Translator
    from i18n.messages_tr import MESSAGES as TR
    from i18n.messages_en import MESSAGES as EN
    from ui.widgets.formula_steps import step_sections
    result=calculate()
    for step in result.formula_steps:
        assert step.title_key in TR and step.title_key in EN
        assert all(v.terminology_key in TR and v.terminology_key in EN for v in step.variables)
        sections=step_sections(step,Translator(language).translate)
        assert {s.key for s in sections}>={"formula","variables","used_values","source","substitution","result"}
    assert TR["fire.hw.unit_loss"]=="Birim Uzunluk Başına Basınç Kaybı"
    assert TR["fire.hw.total_loss"]=="Toplam Basınç Kaybı"
    assert all(m.message_key in TR and m.message_key in EN for m in result.warnings)


def test_payload_canonical_detached_roundtrip_and_raw_units():
    inp=request(q=m3h_to_lpm(120),pipe_input=linked(),inside_diameter_mm=None,case_id=UUID(int=9),revision=4,
        raw_inputs=(FoamRawInput(field_name="flow_lpm",value=120,unit="m³/h"),))
    result=calculate(inp); payload=result.snapshot_payload
    assert result.to_json()==calculate(inp).to_json()==canonical(payload)
    assert json.loads(json.dumps(payload,allow_nan=False))==payload
    assert payload["input_mode"]=="LINKED" and payload["case_id"]==str(UUID(int=9))
    assert payload["revision"]==4
    assert payload["raw_inputs"]["flow_lpm"]["value"]==120
    assert payload["normalized_inputs"]["flow_lpm"]==m3h_to_lpm(120)
    assert [decode(FormulaStep,s) for s in payload["formula_steps"]]==list(result.formula_steps)
    payload["pipe_selection"]["values"]["actual_internal_diameter_mm"]=-1
    payload["results"]["total_pressure_loss_bar"]["value"]=-1
    assert result.snapshot_payload["pipe_selection"]["values"]["actual_internal_diameter_mm"]==105
    assert result.domain_result.total_pressure_loss_bar>0
    with pytest.raises(FrozenInstanceError): result.pipe_mode=PipeInputMode.MANUAL
    with pytest.raises(FrozenInstanceError): inp.revision=0


@pytest.mark.parametrize("observations",[
    (FoamRawInput(field_name="flow_lpm",value=1,unit="L/min"),),
    (FoamRawInput(field_name="flow_lpm",value=2000,unit="mm"),),
    (FoamRawInput(field_name="unknown",value=1,unit="1"),),
    (FoamRawInput(field_name="flow_lpm",value=2000,unit="L/min"),)*2,
])
def test_bad_raw_observations(observations):
    with pytest.raises(ValidationError): calculate(request(raw_inputs=observations))


def test_wrong_units_binding_and_mutable_contracts():
    with pytest.raises(ValidationError): calculate(request(hazen_williams_c=parameter("hazen_williams_c",120,"mm")))
    with pytest.raises(ValidationError): calculate(request(hazen_williams_c=parameter("flow_lpm",120)))
    with pytest.raises(TypeError): request(raw_inputs=[])
    with pytest.raises(TypeError): request(assumptions=[])
    with pytest.raises(ValueError): request(revision=0)


def test_domain_called_once_and_output_never_recomputed(monkeypatch):
    calls=[]
    def engine(value):
        calls.append(value)
        return replace(calculate_hazen_williams(value),pressure_loss_per_m_bar=123,total_pressure_loss_bar=456)
    monkeypatch.setattr("services.fire_hazen_williams_service.calculate_hazen_williams",engine)
    result=calculate()
    assert len(calls)==1
    assert [s.result_value for s in result.formula_steps]==[123,456]
    assert result.snapshot_payload["results"]["total_pressure_loss_bar"]["value"]==456


def test_nozzle_remains_blocked_and_foam_unchanged():
    from services.fire_foam_service import FoamCalculationService
    from engineering.fire.foam_workflow import FoamWorkflowInput
    from engineering.fire.enums import FoamMixtureBasis
    foam=FoamCalculationService().calculate(FoamWorkflowInput(
        protected_area_m2=parameter("protected_area_m2",210,"m²"),
        application_density_lpm_m2=parameter("application_density_lpm_m2",5,"L/(min·m²)"),
        application_duration_min=parameter("application_duration_min",30,"min"),
        foam_fraction=parameter("foam_fraction",.03,"1"),
        mixture_basis=FoamMixtureBasis.CONCENTRATE_VOLUME_PER_SOLUTION_VOLUME))
    assert (foam.domain_result.solution_flow_lpm,foam.domain_result.foam_concentrate_volume_l)==(1050,945)
    with pytest.raises(FireCalculationBlocked) as error: calculate_nozzle(NozzleRequest())
    assert error.value.status is FireSourceStatus.SOURCE_REQUIRED


def test_runtime_import_headless():
    env=dict(os.environ,PYTHONPATH=str(Path(__file__).resolve().parents[1]))
    code="""
import sys
from services.fire_hazen_williams_service import HazenWilliamsCalculationService
blocked=('tkinter','matplotlib','sqlite3','database','repositories','ui','openpyxl','requests','urllib.request')
assert not any(name==root or name.startswith(root+'.') for name in sys.modules for root in blocked)
"""
    subprocess.run([sys.executable,"-c",code],check=True,env=env,capture_output=True,text=True)


def test_no_calculation_io(monkeypatch):
    inp=request(); service=HazenWilliamsCalculationService()
    def forbidden(*args,**kwargs): pytest.fail("Runtime I/O")
    with monkeypatch.context() as guard:
        guard.setattr("builtins.open",forbidden)
        guard.setattr("io.open",forbidden)
        guard.setattr("socket.create_connection",forbidden)
        result=service.calculate(inp)
    assert result.domain_result.total_pressure_loss_bar>0
