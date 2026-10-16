"""Phase 5 shared hydraulic and single-source ENPY regression contracts."""
from dataclasses import replace
from pathlib import Path
import ast

import pytest

from core.local_loss_item import LocalLossItem
from engineering.head_loss.calculator import DischargeHeadLossCalculator
from engineering.head_loss.friction_factor import turbulent_friction_factor
from engineering.head_loss.models import DischargeHeadLossInput
from engineering.suction_npsh.calculator import SuctionNPSHCalculator
from engineering.suction_npsh.models import ENPYInput, SuctionNPSHInput, SuctionNPSHResult
from engineering.units import convert_pressure, convert_kinematic_viscosity
from engineering.validation import ValidationError, ValidationIssue
from services.discharge_head_loss_service import DischargeHeadLossService
from services.suction_npsh_service import SuctionNPSHService

HYDRAULIC_FIELDS = (
    "flow_velocity_m_s", "reynolds_number", "relative_roughness", "flow_regime",
    "friction_factor", "pipe_friction_loss_m", "local_loss_coefficient_total",
    "local_loss_m", "total_hydraulic_loss_m",
)


def _items():
    return [LocalLossItem("Synthetic fitting", 2, 1.5)]


def _hydraulics(nu=2e-6, diameter=100, length=20):
    return DischargeHeadLossInput(diameter, 20, nu, length, .015, 0, _items())


@pytest.mark.parametrize("nu", [1e-4, 2.5e-5, 2e-6])
def test_all_paths_call_the_same_velocity_reynolds_friction_and_loss_implementation(monkeypatch, nu):
    original = DischargeHeadLossCalculator.calculate
    calls = []
    def tracked(self, value):
        result = original(self, value)
        calls.append((value, result))
        return result
    monkeypatch.setattr(DischargeHeadLossCalculator, "calculate", tracked)
    direct = DischargeHeadLossCalculator().calculate(_hydraulics(nu))
    discharge = DischargeHeadLossService(object()).calculate(100, 20, nu, 20, .015, 7, _items())
    suction = SuctionNPSHCalculator().calculate(SuctionNPSHInput(100, 20, nu, 20, .015, _items(), 120000, 3000, 850, 2))
    staged = SuctionNPSHService(object()).calculate_suction_loss(100, 20, nu, "m²/s", 20, .015, _items())
    assert len(calls) == 4
    assert discharge is calls[1][1]
    assert suction.metadata["head_loss"] is calls[2][1]
    assert staged is calls[3][1]
    for result in (discharge, suction.metadata["head_loss"], staged):
        assert tuple(getattr(result, field) for field in HYDRAULIC_FIELDS) == tuple(getattr(direct, field) for field in HYDRAULIC_FIELDS)
    assert discharge.system_head_m == 7 + direct.total_hydraulic_loss_m
    assert suction.suction_line_loss_m == direct.total_hydraulic_loss_m


@pytest.mark.parametrize("diameter", [50, 100, 200, 254])
def test_practical_pipe_d5_and_local_d4_coefficients_are_explicitly_frozen(diameter):
    value = _hydraulics(diameter=diameter)
    result = DischargeHeadLossCalculator().calculate(value)
    assert result.local_loss_coefficient_total == 3.0
    assert result.local_loss_m == 6400 * 3.0 * 20**2 / diameter**4
    assert result.local_loss_m != pytest.approx(6400 * 3.0 * 20**2 / diameter**5)
    assert result.pipe_friction_loss_m == 6.4e6 * result.friction_factor * 20 * 20**2 / diameter**5
    assert result.total_hydraulic_loss_m == result.pipe_friction_loss_m + result.local_loss_m
    # Historical D5 audit metadata stays present, separate from the active result.
    assert result.metadata["audit"]["recorded_d5_local_m"] == 6400 * 3.0 * 20**2 / diameter**5


def test_doubling_diameter_scales_local_loss_by_sixteen():
    small = DischargeHeadLossCalculator().calculate(_hydraulics(diameter=100))
    large = DischargeHeadLossCalculator().calculate(_hydraulics(diameter=200))
    assert small.local_loss_m == large.local_loss_m * 16


def test_laminar_and_colebrook_paths_remain_unchanged():
    laminar = DischargeHeadLossCalculator().calculate(_hydraulics(nu=1e-4))
    assert laminar.flow_regime == "Laminar"
    assert laminar.friction_factor == 64 / laminar.reynolds_number
    turbulent = DischargeHeadLossCalculator().calculate(_hydraulics())
    assert turbulent.flow_regime == "Turbulent"
    assert turbulent.friction_factor == turbulent_friction_factor(turbulent.reynolds_number, turbulent.relative_roughness)
    transition = DischargeHeadLossCalculator().calculate(_hydraulics(nu=2.5e-5))
    assert transition.flow_regime == "Transitional"
    assert transition.warnings == [ValidationIssue("transitional_flow_regime"), ValidationIssue("excel_local_loss_unresolved")]


@pytest.mark.parametrize("pe_unit,pe_factor", [("Pa", 1), ("kPa", 1000), ("bar", 100000)])
@pytest.mark.parametrize("pb_unit,pb_factor", [("Pa", 1), ("kPa", 1000), ("bar", 100000)])
@pytest.mark.parametrize("height", [-2, 0, 2, 30])
def test_service_combined_and_staged_enpy_equal_authoritative_calculator(pe_unit, pe_factor, pb_unit, pb_factor, height):
    service = SuctionNPSHService(object())
    loss = service.calculate_suction_loss(100, 20, 2, "cSt", 20, .015, _items())
    expected = SuctionNPSHCalculator().calculate_enpy(ENPYInput(loss.total_hydraulic_loss_m, 120000, 3000, 850, height, 15))
    staged = service.calculate_enpy(loss.total_hydraulic_loss_m, 120000 / pe_factor, pe_unit, 3000 / pb_factor, pb_unit, 850, height, 15)
    combined = service.calculate(100, 20, 2, "cSt", 20, .015, _items(), 120000 / pe_factor, pe_unit, 3000 / pb_factor, pb_unit, 850, height, 15)
    for name in ("suction_line_loss_m", "suction_pressure_head_m", "vapour_pressure_head_m", "enpym_available_m", "npsh_margin_m"):
        assert getattr(expected, name) == getattr(staged, name) == getattr(combined, name)
    assert staged.warnings == expected.warnings
    assert combined.warnings == loss.warnings + expected.warnings
    assert staged.metadata["suction_pressure_pa"] == 120000
    assert staged.metadata["vapour_pressure_pa"] == 3000


@pytest.mark.parametrize("field,delta,expected_delta", [
    ("suction_pressure_pa", 1000, 1000 / (850 * 9.80665)),
    ("vapour_pressure_pa", 1000, -1000 / (850 * 9.80665)),
    ("static_suction_height_m", 3, -3),
    ("suction_line_loss_m", 3, -3),
])
def test_individual_enpy_contributions_and_height_sign(field, delta, expected_delta):
    calculator = SuctionNPSHCalculator()
    value = ENPYInput(1, 120000, 3000, 850, 2)
    baseline = calculator.calculate_enpy(value)
    changed = calculator.calculate_enpy(replace(value, **{field: getattr(value, field) + delta}))
    assert changed.enpym_available_m - baseline.enpym_available_m == pytest.approx(expected_delta)
    assert baseline.suction_pressure_head_m == 120000 / (850 * 9.80665)
    assert baseline.vapour_pressure_head_m == 3000 / (850 * 9.80665)


def test_required_npsh_is_external_optional_and_has_no_automatic_margin():
    calculator = SuctionNPSHCalculator()
    value = ENPYInput(1, 120000, 3000, 850, 2)
    available = calculator.calculate_enpy(value)
    assert available.npsh_margin_m is None
    equal = calculator.calculate_enpy(replace(value, npsh_required_m=available.enpym_available_m))
    assert equal.npsh_margin_m == 0
    assert equal.warnings == []
    below = calculator.calculate_enpy(replace(value, npsh_required_m=available.enpym_available_m + .25))
    assert below.enpym_available_m == available.enpym_available_m
    assert below.npsh_margin_m == -.25
    assert below.warnings == [ValidationIssue("npsh_below_required")]


def test_staged_service_delegates_enpy_and_never_recalculates_hydraulics(monkeypatch):
    service = SuctionNPSHService(object())
    received = []
    sentinel = SuctionNPSHResult(7, 111, 222, 333, 444)
    def enpy(value):
        received.append(value)
        return sentinel
    def unexpected(*args, **kwargs):
        raise AssertionError("Staged ENPY must not recalculate hydraulics")
    monkeypatch.setattr(service._calculator, "calculate_enpy", enpy)
    monkeypatch.setattr(DischargeHeadLossCalculator, "calculate", unexpected)
    result = service.calculate_enpy(7, 1.2, "bar", 3, "kPa", 850, -2, 5)
    assert received == [ENPYInput(7, 120000, 3000, 850, -2, 5)]
    assert result is sentinel and result.enpym_available_m == 333 and result.npsh_margin_m == 444


def test_combined_calculator_uses_the_same_enpy_method(monkeypatch):
    calculator = SuctionNPSHCalculator()
    received = []
    sentinel = SuctionNPSHResult(7, 111, 222, 333, 444)
    def enpy(value):
        received.append(value)
        return sentinel
    monkeypatch.setattr(calculator, "calculate_enpy", enpy)
    result = calculator.calculate(SuctionNPSHInput(100, 20, 2e-6, 20, .015, _items(), 120000, 3000, 850, 2))
    assert result is sentinel
    assert len(received) == 1
    assert received[0].suction_line_loss_m == result.metadata["head_loss"].total_hydraulic_loss_m
    assert result.enpym_available_m == 333


@pytest.mark.parametrize("unit,factor", [("Pa", 1), ("kPa", 1000), ("bar", 100000)])
def test_shared_pressure_factors_match_existing_service_units(unit, factor):
    assert convert_pressure(1, unit, "Pa") == factor
    assert SuctionNPSHService._pressures_pa(1.2, unit, .03, unit) == (1.2 * factor, .03 * factor)


def test_viscosity_conversion_preserves_existing_case_sensitive_passthrough():
    assert convert_kinematic_viscosity(2, "cSt", "m²/s") == 2e-6
    assert SuctionNPSHService._viscosity_m2s(2, "cSt") == 2e-6
    assert SuctionNPSHService._viscosity_m2s(2e-6, "m²/s") == 2e-6
    assert SuctionNPSHService._viscosity_m2s(2, "cst") == 2


@pytest.mark.parametrize("unit", ["MPa", "pa", "BAR", "unsupported"])
def test_pressure_unit_set_is_not_expanded_by_shared_unit_helpers(unit):
    service = SuctionNPSHService(object())
    with pytest.raises(ValidationError) as caught:
        service.calculate_enpy(1, 1, unit, 1, "Pa", 850, 2)
    assert caught.value.issue == ValidationIssue("unsupported_pressure_unit")


@pytest.mark.parametrize("pe,pb,density,height,required,issue", [
    (-1, 0, 850, 2, None, ValidationIssue("zero_or_greater", "field.suction_pressure")),
    (1, -1, 850, 2, None, ValidationIssue("zero_or_greater", "field.vapour_pressure")),
    (1, 0, 0, 2, None, ValidationIssue("greater_than_zero", "field.fluid_density")),
    (1, 0, 850, float("nan"), None, ValidationIssue("valid_number", "field.static_suction_height")),
    (1, 0, 850, 2, float("nan"), ValidationIssue("valid_number", "field.npsh_required")),
])
def test_existing_staged_validation_contract_is_preserved(pe, pb, density, height, required, issue):
    with pytest.raises(ValidationError) as caught:
        SuctionNPSHService(object()).calculate_enpy(1, pe, "Pa", pb, "Pa", density, height, required)
    assert caught.value.issue == issue


def test_legacy_staged_conversion_overflow_semantics_are_not_silently_changed():
    # The staged API historically validated before conversion. This phase does
    # not add a new post-conversion rejection or change that boundary contract.
    result = SuctionNPSHService(object()).calculate_enpy(1, 1e308, "bar", 0, "Pa", 850, 2)
    assert result.enpym_available_m == float("inf")


def test_enpy_arithmetic_is_only_in_the_engineering_calculator():
    root = Path(__file__).resolve().parents[1]
    service = ast.parse((root / "services/suction_npsh_service.py").read_text(encoding="utf-8"))
    assert not any(isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div) for node in ast.walk(service))
    calculator = ast.parse((root / "engineering/suction_npsh/calculator.py").read_text(encoding="utf-8-sig"))
    assignments = [node for node in ast.walk(calculator) if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "enpy" for t in node.targets)]
    assert len(assignments) == 1
    imports = {node.module or "" for node in ast.walk(calculator) if isinstance(node, ast.ImportFrom)}
    assert not any(name.startswith(("repositories", "database", "ui", "i18n", "tkinter", "matplotlib", "PIL")) for name in imports)


# Captured at 1e667b7 before Phase 5 edits; exact float equality is intentional.
FROZEN_RESULTS = {0.0001: {'discharge': {'flow_velocity_m_s': 0.7073553026306459,
                        'reynolds_number': 707.355302630646,
                        'relative_roughness': 0.00015,
                        'flow_regime': 'Laminar',
                        'friction_factor': 0.09047786842338604,
                        'pipe_friction_loss_m': 0.4632466863277366,
                        'local_loss_coefficient_total': 3.0,
                        'local_loss_m': 0.0768,
                        'total_hydraulic_loss_m': 0.5400466863277366,
                        'system_head_m': 7.540046686327736},
          'suction_hydraulics': {'flow_velocity_m_s': 0.7073553026306459,
                                 'reynolds_number': 707.3553026306461,
                                 'relative_roughness': 0.00015,
                                 'flow_regime': 'Laminar',
                                 'friction_factor': 0.09047786842338602,
                                 'pipe_friction_loss_m': 0.46324668632773647,
                                 'local_loss_coefficient_total': 3.0,
                                 'local_loss_m': 0.0768,
                                 'total_hydraulic_loss_m': 0.5400466863277364},
          'enpy': {'suction_line_loss_m': 0.5400466863277364,
                   'suction_pressure_head_m': 14.395993594982516,
                   'vapour_pressure_head_m': 0.3598998398745629,
                   'enpym_available_m': 11.496047068780216,
                   'npsh_margin_m': -3.503952931219784}},
 2.5e-05: {'discharge': {'flow_velocity_m_s': 0.7073553026306459,
                         'reynolds_number': 2829.421210522584,
                         'relative_roughness': 0.00015,
                         'flow_regime': 'Transitional',
                         'friction_factor': 0.029415698734643274,
                         'pipe_friction_loss_m': 0.15060837752137357,
                         'local_loss_coefficient_total': 3.0,
                         'local_loss_m': 0.0768,
                         'total_hydraulic_loss_m': 0.22740837752137355,
                         'system_head_m': 7.227408377521374},
           'suction_hydraulics': {'flow_velocity_m_s': 0.7073553026306459,
                                  'reynolds_number': 2829.4212105225843,
                                  'relative_roughness': 0.00015,
                                  'flow_regime': 'Transitional',
                                  'friction_factor': 0.02941569873464328,
                                  'pipe_friction_loss_m': 0.15060837752137357,
                                  'local_loss_coefficient_total': 3.0,
                                  'local_loss_m': 0.0768,
                                  'total_hydraulic_loss_m': 0.22740837752137355},
           'enpy': {'suction_line_loss_m': 0.22740837752137355,
                    'suction_pressure_head_m': 14.395993594982516,
                    'vapour_pressure_head_m': 0.3598998398745629,
                    'enpym_available_m': 11.80868537758658,
                    'npsh_margin_m': -3.1913146224134206}},
 2e-06: {'discharge': {'flow_velocity_m_s': 0.7073553026306459,
                       'reynolds_number': 35367.7651315323,
                       'relative_roughness': 0.00015,
                       'flow_regime': 'Turbulent',
                       'friction_factor': 0.023039718042146776,
                       'pipe_friction_loss_m': 0.1179633563757915,
                       'local_loss_coefficient_total': 3.0,
                       'local_loss_m': 0.0768,
                       'total_hydraulic_loss_m': 0.1947633563757915,
                       'system_head_m': 7.194763356375791},
         'suction_hydraulics': {'flow_velocity_m_s': 0.7073553026306459,
                                'reynolds_number': 35367.7651315323,
                                'relative_roughness': 0.00015,
                                'flow_regime': 'Turbulent',
                                'friction_factor': 0.023039718042146776,
                                'pipe_friction_loss_m': 0.1179633563757915,
                                'local_loss_coefficient_total': 3.0,
                                'local_loss_m': 0.0768,
                                'total_hydraulic_loss_m': 0.1947633563757915},
         'enpy': {'suction_line_loss_m': 0.1947633563757915,
                  'suction_pressure_head_m': 14.395993594982516,
                  'vapour_pressure_head_m': 0.3598998398745629,
                  'enpym_available_m': 11.841330398732161,
                  'npsh_margin_m': -3.158669601267839}}}


@pytest.mark.parametrize("nu", tuple(FROZEN_RESULTS))
def test_hydraulic_and_enpy_values_match_pre_phase_snapshot_exactly(nu):
    expected = FROZEN_RESULTS[nu]
    discharge = DischargeHeadLossService(object()).calculate(100, 20, nu, 20, .015, 7, _items())
    service = SuctionNPSHService(object())
    loss = service.calculate_suction_loss(100, 20, nu * 1e6, "cSt", 20, .015, _items())
    result = service.calculate(100, 20, nu * 1e6, "cSt", 20, .015, _items(), 1.2, "bar", .03, "bar", 850, 2, 15)
    for name, number in expected["discharge"].items():
        assert getattr(discharge, name) == number
    for name, number in expected["enpy"].items():
        assert getattr(result, name) == number
    # The pre-existing cSt multiplication can round nu by one ULP. Freeze each
    # path against its own baseline instead of comparing different binary inputs.
    for name, number in expected["suction_hydraulics"].items():
        assert getattr(loss, name) == number
        assert getattr(result.metadata["head_loss"], name) == number
