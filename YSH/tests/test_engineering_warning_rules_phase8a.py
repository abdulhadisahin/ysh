"""Phase 8A source-backed engineering-warning domain contracts."""

from __future__ import annotations

from engineering.validation import ValidationIssue
from engineering.warning_rules import (
    FUTURE_MATERIAL_VELOCITY_RULES,
    HYDRAULIC_INSTITUTE_SOURCE_ID,
    MAN_EVERLLENCE_SOURCE_ID,
    SOURCE_REGISTRY,
    WarningSeverity,
    evaluate_npsh,
    evaluate_velocity,
    validation_finding,
)


def _single_velocity(system: str, role: str, value: float):
    findings = evaluate_velocity(system, role, value)
    assert len(findings) == 1
    return findings[0]


def test_initial_man_everllence_velocity_matrix_is_source_backed_and_non_blocking() -> None:
    low = _single_velocity("DIESEL_FUEL", "SUCTION", 0.32)
    high = _single_velocity("DIESEL_FUEL", "SUCTION", 1.20)
    assert low.severity is WarningSeverity.ENGINEERING_WARNING
    assert high.severity is WarningSeverity.ENGINEERING_WARNING
    assert low.source_id == MAN_EVERLLENCE_SOURCE_ID
    assert low.blocks_calculation is False
    assert low.lower_bound == 0.5 and low.upper_bound == 1.0


def test_velocity_values_inside_initial_recommended_ranges_return_no_warning() -> None:
    assert evaluate_velocity("DIESEL_FUEL", "SUCTION", 0.75) == ()
    assert evaluate_velocity("DIESEL_FUEL", "DELIVERY", 1.75) == ()
    assert evaluate_velocity("SEA_WATER", "DELIVERY", 2.00) == ()


def test_other_initial_velocity_ranges_warn_only_when_outside_recommendation() -> None:
    assert _single_velocity("LUBE_OIL", "DELIVERY", 2.80).severity is WarningSeverity.ENGINEERING_WARNING
    assert _single_velocity("SEA_WATER", "SUCTION", 0.80).severity is WarningSeverity.ENGINEERING_WARNING


def test_npsh_availability_not_above_required_is_critical_but_non_blocking() -> None:
    finding = evaluate_npsh(3.0, 4.0)[0]
    assert finding.severity is WarningSeverity.CRITICAL_WARNING
    assert finding.source_id == HYDRAULIC_INSTITUTE_SOURCE_ID
    assert finding.blocks_calculation is False
    assert finding.actual_value == 3.0 and finding.lower_bound == 4.0
    assert evaluate_npsh(5.0, 4.0) == ()


def test_existing_validation_errors_stay_distinct_from_engineering_warnings() -> None:
    error = validation_finding(ValidationIssue("greater_than_zero", "field.flow_rate"))
    warning = _single_velocity("DIESEL_FUEL", "SUCTION", 0.32)
    assert error.severity is WarningSeverity.ERROR
    assert error.blocks_calculation is True
    assert warning.severity is WarningSeverity.ENGINEERING_WARNING
    assert warning.blocks_calculation is False


def test_future_material_specific_rules_and_source_are_present_but_inactive() -> None:
    assert SOURCE_REGISTRY[MAN_EVERLLENCE_SOURCE_ID].active is True
    assert SOURCE_REGISTRY[HYDRAULIC_INSTITUTE_SOURCE_ID].active is True
    assert all(rule.active is False for rule in FUTURE_MATERIAL_VELOCITY_RULES)
    assert all(rule.material_condition for rule in FUTURE_MATERIAL_VELOCITY_RULES)
