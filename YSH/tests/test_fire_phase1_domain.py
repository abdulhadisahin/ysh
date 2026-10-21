"""Fire Phase 1 contracts; workbook numbers are regression fixtures, not defaults."""
from dataclasses import FrozenInstanceError, replace
import os
from pathlib import Path
import subprocess
import sys
from uuid import UUID

import pytest

from engineering.fire.calculators import (
    FireCalculationBlocked, calculate_foam_system, calculate_hazen_williams, calculate_nozzle,
)
from engineering.fire.enums import FireCalculationType, FireRuleId, FireSourceStatus, FoamMixtureBasis, HWApplicability, SYMBOLS
from engineering.fire.models import FoamSystemInput, HazenWilliamsInput, NozzleRequest
from engineering.fire.pipe_adapter import hazen_williams_from_pipe
from engineering.fire.provenance import ParameterProvenance
from engineering.fire.units import (
    percent_to_fraction, fraction_to_percent, lpm_to_m3h, m3h_to_lpm,
    litres_to_m3, m3_to_litres, bar_to_pa, pa_to_bar,
)
from engineering.pipe_design.rules import DesignStatus
from engineering.pipe_design.transfer import PipeInputState, PipeValues, PipeLinkStatus, revise_selection
from engineering.pipe_design.v2_models import PipeCandidate, PipeSelection
from engineering.provenance import EngineeringValue, OverridePolicy, SourceReference, SourceType, VerificationStatus
from engineering.validation import ValidationError


def foam(**changes):
    return FoamSystemInput(**(dict(protected_area_m2=210, application_density_lpm_m2=5,
        application_duration_min=30, foam_fraction=.03,
        mixture_basis=FoamMixtureBasis.CONCENTRATE_VOLUME_PER_SOLUTION_VOLUME) | changes))


def hw(**changes):
    return HazenWilliamsInput(**(dict(flow_lpm=2000, inside_diameter_mm=105,
        pipe_length_m=150, hazen_williams_c=120, applicability=HWApplicability.WATER_ONLY) | changes))


def evidence(name, used, *, unit="1", status=FireSourceStatus.WORKBOOK_REFERENCE_ONLY,
             recommended=None, reason=None):
    source = SourceReference(source_type=SourceType.ENGINEERING_REFERENCE,
        document="Synthetic test evidence", verification_status=VerificationStatus.UNVERIFIED)
    value = EngineeringValue(used_value=used, unit=unit, source=source,
        override_policy=OverridePolicy.SUGGESTED if recommended is not None else OverridePolicy.USER_INPUT,
        recommended_value=recommended, override_reason=reason)
    return ParameterProvenance(field_name=name, engineering_value=value, source_status=status)


def test_workbook_foam_volume_and_water_balance():
    result = calculate_foam_system(foam())
    assert result.solution_flow_lpm == 1050
    assert result.foam_concentrate_flow_lpm == 31.5
    assert result.water_flow_lpm == 1018.5
    assert result.foam_concentrate_volume_l == 945
    assert result.foam_concentrate_flow_lpm + result.water_flow_lpm == result.solution_flow_lpm


@pytest.mark.parametrize("area,volume", [(230,1035),(223,1003.5),(96,432),(190,855),(358,1611)])
def test_other_workbook_volumes(area, volume):
    assert calculate_foam_system(foam(protected_area_m2=area)).foam_concentrate_volume_l == pytest.approx(volume,rel=1e-13)


def test_pump_flows_have_no_selection_margin_and_duration_only_changes_volume():
    value = foam(protected_area_m2=1660)
    result = calculate_foam_system(value)
    assert result.solution_flow_lpm == 8300
    assert result.foam_concentrate_flow_lpm == 249
    assert lpm_to_m3h(result.foam_concentrate_flow_lpm) == pytest.approx(14.94)
    assert lpm_to_m3h(result.foam_concentrate_flow_lpm) != 15
    assert result.water_flow_lpm == 8051
    assert lpm_to_m3h(result.water_flow_lpm) == pytest.approx(483.06)
    other = calculate_foam_system(replace(value, application_duration_min=60))
    assert other.foam_concentrate_flow_lpm == result.foam_concentrate_flow_lpm
    assert other.foam_concentrate_volume_l == result.foam_concentrate_volume_l * 2


@pytest.mark.parametrize("c,expected", [(120,2.3717829024660286),(140,1.7832957445009588)])
def test_workbook_hw_cases(c, expected):
    result = calculate_hazen_williams(hw(hazen_williams_c=c))
    assert result.total_pressure_loss_bar == pytest.approx(expected, rel=1e-13)
    assert result.pressure_loss_per_m_bar == pytest.approx(expected / 150, rel=1e-13)


def test_hw_published_example_and_zero_length():
    result = calculate_hazen_williams(hw(flow_lpm=600, inside_diameter_mm=55.501,
        hazen_williams_c=100, pipe_length_m=30))
    assert result.total_pressure_loss_bar == pytest.approx(1.5984958266542856, rel=1e-13)
    zero = calculate_hazen_williams(hw(pipe_length_m=0))
    assert zero.total_pressure_loss_bar == 0
    assert zero.pressure_loss_per_m_bar > 0


@pytest.mark.parametrize("field,bad", [
    ("protected_area_m2",-1),("protected_area_m2",0),
    ("application_density_lpm_m2",0),("application_density_lpm_m2",-1),
    ("application_duration_min",0),("application_duration_min",-1),
    ("foam_fraction",0),("foam_fraction",-1),("foam_fraction",1),("foam_fraction",3),
])
def test_invalid_foam_inputs_have_field_specific_errors(field, bad):
    with pytest.raises(ValidationError) as error:
        foam(**{field:bad})
    assert error.value.issue.field_key == field


@pytest.mark.parametrize("field,bad", [
    ("flow_lpm",0),("flow_lpm",-1),("inside_diameter_mm",0),
    ("inside_diameter_mm",-1),("pipe_length_m",-1),
    ("hazen_williams_c",0),("hazen_williams_c",-1),
])
def test_invalid_hw_inputs(field, bad):
    with pytest.raises(ValidationError) as error:
        hw(**{field:bad})
    assert error.value.issue.field_key == field


@pytest.mark.parametrize("factory,field", [(foam,"protected_area_m2"),(foam,"foam_fraction"),
    (hw,"flow_lpm"),(hw,"hazen_williams_c")])
@pytest.mark.parametrize("bad", [True,False,None,"3",float("nan"),float("inf"),float("-inf")])
def test_non_finite_and_non_numeric_inputs(factory, field, bad):
    with pytest.raises(ValidationError) as error:
        factory(**{field:bad})
    assert error.value.issue.code == "valid_number"


@pytest.mark.parametrize("scope,status", [
    (HWApplicability.SEAWATER_SOURCE_REQUIRED, FireSourceStatus.SOURCE_REQUIRED),
    (HWApplicability.OTHER_FLUID_SOURCE_REQUIRED, FireSourceStatus.SOURCE_REQUIRED),
    (HWApplicability.NOT_CONFIGURED, FireSourceStatus.NOT_CONFIGURED),
])
def test_unsupported_hw_is_blocked_even_with_zero_length(scope, status):
    with pytest.raises(FireCalculationBlocked) as error:
        calculate_hazen_williams(hw(applicability=scope, pipe_length_m=0))
    assert error.value.status is status
    assert error.value.issue_id == "FIRE-HW-UNITS-001"


@pytest.mark.parametrize("draft", [NozzleRequest(),NozzleRequest(device_id="supplied", pressure_bar=4)])
def test_nozzle_always_blocked(draft):
    with pytest.raises(FireCalculationBlocked) as error:
        calculate_nozzle(draft)
    assert error.value.status is FireSourceStatus.SOURCE_REQUIRED
    assert error.value.issue_id == "FIRE-NOZZLE-FORMULA-001"


def test_nozzle_even_with_supplied_k_stays_blocked():
    request = NozzleRequest(nozzle_k=evidence("nozzle_k",80,unit="(L/min)/√bar"),pressure_bar=1)
    with pytest.raises(FireCalculationBlocked):
        calculate_nozzle(request)


@pytest.mark.parametrize("status", list(FireSourceStatus))
def test_provenance_status_and_override_survive_without_upgrade(status):
    item = evidence("foam_fraction",.03,status=status,recommended=.06,reason="Explicit project choice")
    result = calculate_foam_system(foam(provenance=(item,)))
    captured = result.input.provenance[0]
    assert captured is item
    assert captured.source_status is status
    assert captured.engineering_value.used_value == .03
    assert captured.engineering_value.recommended_value == .06
    assert captured.engineering_value.override_reason == "Explicit project choice"
    assert captured.engineering_value.source.verification_status is VerificationStatus.UNVERIFIED


@pytest.mark.parametrize("items", [
    (evidence("foam_fraction",.06),),
    (evidence("foam_fraction",.03,unit="%"),),
    (evidence("not_a_field",.03),),
    (evidence("foam_fraction",.03),evidence("foam_fraction",.03)),
])
def test_contradictory_provenance_rejected(items):
    with pytest.raises(ValidationError):
        foam(provenance=items)


def test_missing_metadata_is_not_fabricated_and_mutable_metadata_rejected():
    assert calculate_foam_system(foam()).input.provenance == ()
    with pytest.raises(TypeError):
        foam(provenance=[])
    with pytest.raises(ValueError):
        evidence("foam_fraction",.03,recommended=.06)


@pytest.mark.parametrize("forward,back,value,expected", [
    (percent_to_fraction,fraction_to_percent,3,.03),
    (lpm_to_m3h,m3h_to_lpm,249,14.94),
    (litres_to_m3,m3_to_litres,945,.945),
    (bar_to_pa,pa_to_bar,2.5,250000),
])
def test_explicit_unit_boundaries_round_trip(forward, back, value, expected):
    converted = forward(value)
    assert converted == pytest.approx(expected)
    assert back(converted) == pytest.approx(value)


def test_fraction_helpers_allow_endpoints_but_calculator_does_not():
    assert percent_to_fraction(0) == 0
    assert percent_to_fraction(100) == 1
    assert percent_to_fraction(.03) == .0003  # no heuristic: .03 percent is not 3 percent
    with pytest.raises(ValidationError):
        percent_to_fraction(101)
    with pytest.raises(ValidationError):
        fraction_to_percent(3)


def test_pipe_adapter_uses_actual_applied_geometry_and_preserves_stale_evidence():
    pipe = PipeCandidate(id=UUID(int=2),standard_id=UUID(int=1),outside_diameter_mm=110,
        wall_thickness_mm=4,inside_diameter_mm=101,nominal_diameter="TEST")
    source = PipeSelection(status=DesignStatus.RULE_NOT_CONFIGURED,
        theoretical_internal_diameter_mm=75,design_velocity_m_s=2,flow_rate_m3_h=20,
        selected_standard_id=pipe.standard_id,selected_standard_code="TEST",candidate=pipe,selected_pipe=pipe)
    applied = PipeInputState().link_to(source)
    revised = revise_selection(source,replace(source,flow_rate_m3_h=30))
    stale = applied.observe(revised).keep_current(revised)
    value = hazen_williams_from_pipe(stale,pipe_length_m=150,hazen_williams_c=120,
        applicability=HWApplicability.WATER_ONLY)
    assert value.inside_diameter_mm == 101  # not theoretical75 or OD-2t=102
    assert value.flow_lpm == pytest.approx(20*1000/60)
    assert value.pipe_input is stale
    assert value.pipe_input.status is PipeLinkStatus.LINKED_STALE
    assert value.pipe_input.snapshot.source_revision == 1
    assert value.pipe_input.observed_revision == 2
    assert value.pipe_input.kept_current
    assert value.pipe_input.snapshot.values.pipe_id == pipe.id
    assert calculate_hazen_williams(value).input.pipe_input is stale
    updated = hazen_williams_from_pipe(stale.update(revised),pipe_length_m=150,
        hazen_williams_c=120,applicability=HWApplicability.WATER_ONLY)
    assert updated.flow_lpm == pytest.approx(500)


def test_manual_adapter_does_not_guess_c_or_applicability():
    state=PipeInputState(manual_values=PipeValues(flow_rate_m3_h=120,actual_internal_diameter_mm=105))
    value=hazen_williams_from_pipe(state,pipe_length_m=150,hazen_williams_c=140,
        applicability=HWApplicability.SEAWATER_SOURCE_REQUIRED)
    assert value.flow_lpm == pytest.approx(2000)
    assert value.hazen_williams_c == 140
    with pytest.raises(FireCalculationBlocked):
        calculate_hazen_williams(value)
    with pytest.raises(ValueError):
        replace(value, inside_diameter_mm=106)
    with pytest.raises(ValueError):
        hazen_williams_from_pipe(PipeInputState(),pipe_length_m=1,hazen_williams_c=1,
            applicability=HWApplicability.WATER_ONLY)


def test_models_require_explicit_basis_scope_and_inputs():
    with pytest.raises(TypeError):
        FoamSystemInput()
    with pytest.raises(TypeError):
        foam(mixture_basis="mass_fraction")
    with pytest.raises(TypeError):
        hw(applicability="WATER_ONLY")


@pytest.mark.parametrize("value,field", [
    (foam(),"foam_fraction"),(hw(),"hazen_williams_c"),
    (calculate_foam_system(foam()),"solution_flow_lpm"),
    (calculate_hazen_williams(hw()),"total_pressure_loss_bar"),
    (evidence("foam_fraction",.03),"source_status"),
])
def test_immutable_contracts(value,field):
    with pytest.raises(FrozenInstanceError):
        setattr(value,field,999)


def test_rule_and_symbol_contracts_do_not_register_visible_modules():
    from engineering.module_registry import MODULES
    assert len(MODULES)==4
    assert FireCalculationType.FIRE_HAZEN_WILLIAMS.value == "fire_hazen_williams"
    assert FireRuleId.HW_EQUATION.value == "FIRE.HW.EQUATION"
    assert SYMBOLS["foam_fraction"] != SYMBOLS["hazen_williams_c"]
    assert "roughness_mm" not in SYMBOLS


def test_fresh_domain_import_does_not_load_ui_db_plotting_or_network():
    env=dict(os.environ,PYTHONPATH=str(Path(__file__).resolve().parents[1]))
    code="""
import sys
from engineering.fire.calculators import calculate_foam_system
from engineering.fire.pipe_adapter import hazen_williams_from_pipe
blocked=('tkinter','matplotlib','sqlite3','database','repositories','ui','requests','urllib.request')
assert not any(name == root or name.startswith(root+'.') for name in sys.modules for root in blocked)
"""
    subprocess.run([sys.executable,"-c",code],env=env,check=True,capture_output=True,text=True)


def test_extreme_hw_inputs_fail_structurally_instead_of_returning_inf():
    with pytest.raises(ValidationError):
        calculate_hazen_williams(hw(flow_lpm=1e300))
    with pytest.raises(ValidationError):
        calculate_hazen_williams(hw(inside_diameter_mm=1e-300))


def test_water_fraction_is_derived_for_each_case():
    result=calculate_foam_system(foam(protected_area_m2=1660,foam_fraction=.06))
    assert result.water_flow_lpm == 7802
    assert result.foam_concentrate_flow_lpm == 498
    assert result.water_flow_lpm+result.foam_concentrate_flow_lpm == 8300


@pytest.mark.parametrize("convert", [percent_to_fraction,fraction_to_percent,lpm_to_m3h,
    m3h_to_lpm,litres_to_m3,m3_to_litres,bar_to_pa,pa_to_bar])
@pytest.mark.parametrize("bad", [True,float("nan")])
def test_unit_boundaries_reject_non_numeric_or_non_finite(convert,bad):
    with pytest.raises(ValidationError):
        convert(bad)


def test_overflow_never_leaks_successful_inf_outputs():
    with pytest.raises(ValidationError):
        calculate_foam_system(foam(protected_area_m2=1e308))
    with pytest.raises(ValidationError):
        calculate_foam_system(foam(protected_area_m2=10**200,application_density_lpm_m2=10**200))
    with pytest.raises(ValidationError):
        m3_to_litres(1e308)
