"""Application evidence tests; sample criteria are explicit fixtures, not default rules."""
from dataclasses import FrozenInstanceError, replace
from datetime import date
import json
import os
from pathlib import Path
import subprocess
import sys
from uuid import UUID

import pytest

from engineering.fire.calculators import calculate_foam_system, calculate_hazen_williams, calculate_nozzle, FireCalculationBlocked
from engineering.fire.enums import FireSourceStatus, FoamMixtureBasis, HWApplicability
from engineering.fire.foam_workflow import (FoamWorkflowInput, FoamRawInput, FoamWorkflowStatus,
    SourceReadiness, SourceMessageCategory)
from engineering.fire.models import HazenWilliamsInput, NozzleRequest
from engineering.fire.provenance import ParameterProvenance
from engineering.formula.models import CalculationClassification, FormulaStep
from engineering.provenance import EngineeringValue, SourceReference, SourceType, VerificationStatus, OverridePolicy
from engineering.snapshots.serialization import decode
from engineering.system_context import SystemContext, ContextReference
from engineering.validation import ValidationError
from services.fire_foam_service import FoamCalculationService


def parameter(name,value,unit,*,status=FireSourceStatus.USER_PROJECT_ASSUMPTION,recommended=None,reason=None):
    return ParameterProvenance(field_name=name,source_status=status,
        engineering_value=EngineeringValue(used_value=value,unit=unit,
            source=SourceReference(source_type=SourceType.USER_INPUT,document="Explicit test criteria",
                revision="test-revision",verification_date=date(2026,10,21),
                verification_status=VerificationStatus.USER_SUPPLIED),
            override_policy=OverridePolicy.USER_INPUT if recommended is None else OverridePolicy.SUGGESTED,
            recommended_value=recommended,override_reason=reason))


def request(area=210,q=5,t=30,c=.03,**changes):
    return FoamWorkflowInput(**(dict(
        protected_area_m2=parameter("protected_area_m2",area,"m²"),
        application_density_lpm_m2=parameter("application_density_lpm_m2",q,"L/(min·m²)"),
        application_duration_min=parameter("application_duration_min",t,"min"),
        foam_fraction=parameter("foam_fraction",c,"1"),
        mixture_basis=FoamMixtureBasis.CONCENTRATE_VOLUME_PER_SOLUTION_VOLUME) | changes))


def calculate(value=None):
    return FoamCalculationService().calculate(value if value is not None else request())


def test_workbook_workflow_steps_summary_and_direct_domain_match():
    result=calculate()
    domain=result.domain_result
    assert domain==calculate_foam_system(domain.input)
    assert (domain.solution_flow_lpm,domain.foam_concentrate_flow_lpm,domain.water_flow_lpm,
            domain.foam_concentrate_volume_l)==(1050,31.5,1018.5,945)
    assert [s.step_id for s in result.formula_steps]==[
        "fire.foam.solution_flow","fire.foam.concentrate_flow","fire.foam.water_flow","fire.foam.concentrate_volume"]
    assert [s.display_order for s in result.formula_steps]==[0,1,2,3]
    assert [s.result_value for s in result.formula_steps]==[1050,31.5,1018.5,945]
    assert [s.result_unit for s in result.formula_steps]==["L/min","L/min","L/min","L"]
    assert [s.result_symbol for s in result.formula_steps]==["Qsolution","Qfoam","Qwater","Vfoam"]
    assert [[v.symbol for v in s.variables] for s in result.formula_steps]==[
        ["A","q","Qsolution"],["Cfoam","Qsolution","Qfoam"],
        ["Cfoam","Qsolution","Qwater"],["Qfoam","t","Vfoam"]]
    assert result.formula_steps[2].substitution=="Qwater = (1 - 0.03) × 1050 = 1018.5 L/min"
    assert result.formula_steps[3].substitution=="Vfoam = 31.5 × 30 = 945.0 L"
    assert result.primary_result_key=="foam_concentrate_volume_l"
    assert len(result.summary)==4
    assert result.workflow_version=="fire.foam.workflow.v1"


def test_workbook_flow_and_output_conversions_no_equipment_rounding():
    result=calculate(request(area=1660))
    d=result.domain_result
    assert (d.solution_flow_lpm,d.foam_concentrate_flow_lpm,d.water_flow_lpm)==(8300,249,8051)
    values=result.snapshot_payload["converted_results"]
    assert values["foam_concentrate_flow_m3h"]["value"]==pytest.approx(14.94)
    assert values["water_flow_m3h"]["value"]==pytest.approx(483.06)
    assert calculate().snapshot_payload["converted_results"]["foam_concentrate_volume_m3"]["value"]==pytest.approx(.945)
    assert "selected_capacity" not in result.snapshot_payload


def test_override_uses_six_percent_and_preserves_original_recommendation():
    item=parameter("foam_fraction",.06,"1",recommended=.03,
        reason="Project-selected approved concentrate",
        status=FireSourceStatus.SOURCE_VERIFIED_CONTEXT_DEPENDENT)
    result=calculate(request(foam_fraction=item))
    assert result.domain_result.foam_concentrate_flow_lpm==63
    assert result.domain_result.foam_concentrate_volume_l==1890
    assert result.domain_result.water_flow_lpm==987
    captured=result.input_provenance[3]
    assert captured is item
    assert captured.engineering_value.recommended_value==.03
    assert captured.engineering_value.used_value==.06
    assert captured.engineering_value.override_reason=="Project-selected approved concentrate"
    used=result.formula_steps[1].used_values[0]
    assert used.recommended_value==.03 and used.used_value==.06
    assert used.override_reason==item.engineering_value.override_reason
    assert result.formula_steps[2].substitution.startswith("Qwater = (1 - 0.06)")
    raw=result.snapshot_payload["provenance"][3]
    assert raw["source_status"]=="SOURCE_VERIFIED_CONTEXT_DEPENDENT"
    assert raw["engineering_value"]["override_reason"]==used.override_reason


def test_no_recommendation_is_not_synthesized():
    result=calculate(request(q=4.5,t=17,c=.04))
    assert all(v.engineering_value.recommended_value is None for v in result.input_provenance)
    assert all(v.recommended_value is None for s in result.formula_steps for v in s.used_values)
    assert result.domain_result==calculate_foam_system(result.domain_result.input)
    assert all(w.category is SourceMessageCategory.INFO for w in result.warnings)


@pytest.mark.parametrize("status",list(FireSourceStatus))
def test_every_source_status_is_preserved_and_mathematics_stays_independent(status):
    item=parameter("application_density_lpm_m2",4.5,"L/(min·m²)",status=status)
    result=calculate(request(application_density_lpm_m2=item))
    assert result.domain_result.solution_flow_lpm==945
    assert result.input_provenance[1].source_status is status
    payload=result.snapshot_payload
    assert payload["provenance"][1]["source_status"]==status.value
    assert payload["calculation_validity"]=="VALID"
    assert payload["provenance"][1]["engineering_value"]["source"]["verification_status"]=="USER_SUPPLIED"
    if status not in (FireSourceStatus.SOURCE_VERIFIED,FireSourceStatus.DERIVED_FROM_VERIFIED_RULE):
        assert any(w.field_name==item.field_name and w.source_status is status for w in result.warnings)
        assert result.status is FoamWorkflowStatus.CALCULATED_WITH_SOURCE_WARNING


def test_readiness_is_not_regulatory_compliance():
    original=request()
    fields=("protected_area_m2","application_density_lpm_m2","application_duration_min","foam_fraction")
    verified=replace(original,**{name:replace(getattr(original,name),source_status=FireSourceStatus.SOURCE_VERIFIED) for name in fields})
    result=calculate(verified)
    assert result.status is FoamWorkflowStatus.CALCULATED
    assert result.source_readiness is SourceReadiness.READY
    assert result.warnings==()
    contextual=replace(verified,foam_fraction=replace(verified.foam_fraction,source_status=FireSourceStatus.SOURCE_VERIFIED_CONTEXT_DEPENDENT))
    assert calculate(contextual).source_readiness is SourceReadiness.CONTEXT_REQUIRED
    required=replace(verified,application_density_lpm_m2=replace(verified.application_density_lpm_m2,source_status=FireSourceStatus.SOURCE_REQUIRED))
    result=calculate(required)
    assert result.source_readiness is SourceReadiness.REVIEW_REQUIRED
    assert result.warnings[0].category is SourceMessageCategory.SOURCE_REQUIRED
    assert "REGULATORY_COMPLIANT" not in result.to_json()


@pytest.mark.parametrize("name",["protected_area_m2","application_density_lpm_m2","application_duration_min","foam_fraction","mixture_basis"])
def test_omitted_required_input_is_validation_failure(name):
    with pytest.raises(ValidationError) as error:
        calculate(replace(request(),**{name:None}))
    assert error.value.issue.code=="required"
    assert error.value.issue.field_key==name


@pytest.mark.parametrize("kwargs,field",[({"area":-1},"protected_area_m2"),({"q":0},"application_density_lpm_m2"),
    ({"t":0},"application_duration_min"),({"c":1},"foam_fraction")])
def test_domain_validation_forwarded_without_partial_result(kwargs,field):
    with pytest.raises(ValidationError) as error:
        calculate(request(**kwargs))
    assert error.value.issue.field_key==field


def test_payload_is_canonical_detached_and_roundtrips_existing_source_and_steps():
    ctx=SystemContext(system=ContextReference(id=UUID(int=2),code="TEST_FIRE",name_tr="Test Yangın"))
    inp=request(context=ctx,case_id=UUID(int=1),revision=3,assumptions=("Explicit protected area basis",),
        raw_inputs=(FoamRawInput(field_name="foam_fraction",value=3,unit="%"),))
    first=calculate(inp); second=calculate(inp)
    assert first.to_json()==second.to_json()
    payload=json.loads(first.to_json())
    assert json.loads(json.dumps(payload,allow_nan=False))==payload
    assert payload["raw_inputs"]["foam_fraction"]["value"]==3
    assert payload["raw_inputs"]["foam_fraction"]["unit"]=="%"
    assert payload["normalized_inputs"]["foam_fraction"]==.03
    assert payload["raw_inputs"]["protected_area_m2"]["representation"]=="normalized_input"
    assert payload["context"]["system"]["id"]==str(UUID(int=2))
    assert payload["case_id"]==str(UUID(int=1)) and payload["revision"]==3
    assert payload["assumptions"]==["Explicit protected area basis"]
    assert [decode(FormulaStep,s) for s in payload["formula_steps"]]==list(first.formula_steps)
    src=payload["provenance"][0]["engineering_value"]["source"]
    assert decode(SourceReference,src)==inp.protected_area_m2.engineering_value.source
    payload["results"]["solution_flow_lpm"]["value"]=-999
    assert first.snapshot_payload["results"]["solution_flow_lpm"]["value"]==1050
    assert first.domain_result.solution_flow_lpm==1050


@pytest.mark.parametrize("raw",[
    (FoamRawInput(field_name="foam_fraction",value=6,unit="%"),),
    (FoamRawInput(field_name="protected_area_m2",value=210,unit="mm"),),
    (FoamRawInput(field_name="unknown",value=1,unit="1"),),
    (FoamRawInput(field_name="foam_fraction",value=3,unit="%"),)*2,
])
def test_conflicting_original_observations_rejected(raw):
    with pytest.raises(ValidationError):
        calculate(request(raw_inputs=raw))


def test_wrong_binding_and_units_are_rejected():
    with pytest.raises(ValidationError):
        calculate(request(foam_fraction=parameter("application_duration_min",.03,"1")))
    with pytest.raises(ValidationError):
        calculate(request(foam_fraction=parameter("foam_fraction",.03,"%")))


def test_formula_sources_and_input_sources_remain_separate():
    result=calculate()
    for step in result.formula_steps:
        assert step.classification is CalculationClassification.ENGINEERING_CALCULATION
        assert step.sources[0].source_type is SourceType.CALCULATED
        assert step.sources[0].formula.startswith("FIRE.FOAM.")
        for value in step.used_values:
            assert value.source.source_type is SourceType.USER_INPUT
            assert value.source.document=="Explicit test criteria"
        assert step.check is None


@pytest.mark.parametrize("language",["tr","en"])
def test_existing_formula_sections_render_headlessly_without_recalculation(language,monkeypatch):
    from i18n.translator import Translator
    from ui.widgets.formula_steps import step_sections
    from i18n.messages_en import MESSAGES as EN
    from i18n.messages_tr import MESSAGES as TR
    result=calculate()
    monkeypatch.setattr("services.fire_foam_service.calculate_foam_system",lambda value:pytest.fail("Renderer recalculated"))
    tr=Translator(language).translate
    for step in result.formula_steps:
        assert step.title_key in EN and step.title_key in TR
        assert all(v.terminology_key in EN and v.terminology_key in TR for v in step.variables)
        sections=step_sections(step,tr)
        assert {s.key for s in sections}>={"formula","variables","used_values","source","substitution","result"}
        assert next(s for s in sections if s.key=="substitution").text==step.substitution
    for warning in result.warnings:
        assert warning.message_key in EN and warning.message_key in TR


def test_service_calls_existing_engine_once_and_uses_returned_results(monkeypatch):
    import services.fire_foam_service as service
    calls=[]
    def calculate_domain(value):
        calls.append(value)
        return replace(calculate_foam_system(value),solution_flow_lpm=1234)
    monkeypatch.setattr(service,"calculate_foam_system",calculate_domain)
    result=calculate()
    assert len(calls)==1
    assert result.formula_steps[0].result_value==1234
    assert result.snapshot_payload["results"]["solution_flow_lpm"]["value"]==1234


def test_result_and_request_are_immutable():
    result=calculate()
    with pytest.raises(FrozenInstanceError): result.status="bad"
    with pytest.raises(FrozenInstanceError): result.summary[0].value=0
    with pytest.raises(TypeError): request(assumptions=[])
    with pytest.raises(TypeError): request(raw_inputs=[])
    with pytest.raises(ValueError): request(revision=0)


def test_phase1_hw_and_nozzle_unchanged():
    for c,expected in [(120,2.3717829024660286),(140,1.7832957445009588)]:
        value=HazenWilliamsInput(flow_lpm=2000,inside_diameter_mm=105,pipe_length_m=150,
            hazen_williams_c=c,applicability=HWApplicability.WATER_ONLY)
        assert calculate_hazen_williams(value).total_pressure_loss_bar==pytest.approx(expected,rel=1e-13)
        with pytest.raises(FireCalculationBlocked):
            calculate_hazen_williams(replace(value,applicability=HWApplicability.SEAWATER_SOURCE_REQUIRED))
    with pytest.raises(FireCalculationBlocked): calculate_nozzle(NozzleRequest())


def test_runtime_service_is_headless_and_reference_free():
    env=dict(os.environ,PYTHONPATH=str(Path(__file__).resolve().parents[1]))
    code="""
import sys
from services.fire_foam_service import FoamCalculationService
blocked=('tkinter','matplotlib','sqlite3','database','repositories','ui','openpyxl','requests','urllib.request')
assert not any(name==root or name.startswith(root+'.') for name in sys.modules for root in blocked)
"""
    subprocess.run([sys.executable,"-c",code],check=True,env=env,capture_output=True,text=True)


def test_calculation_never_reads_files_or_connects_to_network(monkeypatch):
    service=FoamCalculationService()
    inp=request()
    def forbidden(*args,**kwargs):
        pytest.fail("Workflow attempted runtime I/O")
    with monkeypatch.context() as guard:
        guard.setattr("builtins.open",forbidden)
        guard.setattr("io.open",forbidden)
        guard.setattr("socket.create_connection",forbidden)
        result=service.calculate(inp)
    assert result.domain_result.foam_concentrate_volume_l==945
