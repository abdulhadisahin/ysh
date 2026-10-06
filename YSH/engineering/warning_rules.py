"""Immutable, source-backed engineering warning definitions for D243.

This module deliberately evaluates recommendations separately from calculation
and validation.  Consumers can present findings beside an otherwise valid
result without altering formula outputs.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import math

from engineering.validation import ValidationIssue


class WarningSeverity(StrEnum):
    """Severity policy shared by future engineering-warning presentations."""

    ERROR = "ERROR"
    ENGINEERING_WARNING = "ENGINEERING_WARNING"
    CRITICAL_WARNING = "CRITICAL_WARNING"


@dataclass(frozen=True, slots=True)
class EngineeringSource:
    """Central source metadata; UI must not embed source labels or links."""

    identifier: str
    title: str
    note: str
    active: bool = True


@dataclass(frozen=True, slots=True)
class WarningRule:
    """One recommended-range rule with optional future material specificity."""

    code: str
    parameter: str
    system: str | None
    line_role: str | None
    lower_bound: float | None
    upper_bound: float | None
    unit: str
    severity: WarningSeverity
    message_key: str
    source_id: str
    source_note: str
    material_condition: str | None = None
    active: bool = True


@dataclass(frozen=True, slots=True)
class EngineeringFinding:
    """A structured result that leaves a valid calculation result untouched."""

    code: str
    severity: WarningSeverity
    message_key: str
    actual_value: float | None
    lower_bound: float | None
    upper_bound: float | None
    unit: str | None
    source_id: str | None
    context: dict[str, str]

    @property
    def blocks_calculation(self) -> bool:
        return self.severity is WarningSeverity.ERROR


MAN_EVERLLENCE_SOURCE_ID = "MAN_EVERLLENCE_MARINE_PROJECT_GUIDE"
HYDRAULIC_INSTITUTE_SOURCE_ID = "HYDRAULIC_INSTITUTE_ANSI_HI_9_6_1"
WARTSILA_SOURCE_ID = "WARTSILA_MATERIAL_FLOW_GUIDANCE"

SOURCE_REGISTRY: dict[str, EngineeringSource] = {
    MAN_EVERLLENCE_SOURCE_ID: EngineeringSource(
        MAN_EVERLLENCE_SOURCE_ID,
        "MAN / Everllence proje kılavuzu",
        "Recommended flow-rate guidance; not a hard mathematical validity limit.",
    ),
    HYDRAULIC_INSTITUTE_SOURCE_ID: EngineeringSource(
        HYDRAULIC_INSTITUTE_SOURCE_ID,
        "ANSI/HI 9.6.1 NPSH ilkesi",
        "Available NPSH must exceed pump-required NPSH when NPSHr is supplied.",
    ),
    WARTSILA_SOURCE_ID: EngineeringSource(
        WARTSILA_SOURCE_ID,
        "Wärtsilä material-specific flow guidance",
        "Future material-specific seawater guidance; inactive until material identity is unambiguous.",
        active=False,
    ),
}


def _velocity_rule(system: str, line_role: str, lower: float, upper: float) -> WarningRule:
    return WarningRule(
        code=f"velocity.{system.casefold()}.{line_role.casefold()}.outside_recommended_range",
        parameter="flow_velocity",
        system=system,
        line_role=line_role,
        lower_bound=lower,
        upper_bound=upper,
        unit="m/s",
        severity=WarningSeverity.ENGINEERING_WARNING,
        message_key="warning.velocity.outside_recommended_range",
        source_id=MAN_EVERLLENCE_SOURCE_ID,
        source_note="Recommended range only; calculation remains valid.",
    )


VELOCITY_RULES: tuple[WarningRule, ...] = (
    _velocity_rule("DIESEL_FUEL", "SUCTION", 0.5, 1.0),
    _velocity_rule("DIESEL_FUEL", "DELIVERY", 1.5, 2.0),
    _velocity_rule("LUBE_OIL", "SUCTION", 0.5, 1.0),
    _velocity_rule("LUBE_OIL", "DELIVERY", 1.5, 2.5),
    _velocity_rule("SEA_WATER", "SUCTION", 1.0, 1.5),
    _velocity_rule("SEA_WATER", "DELIVERY", 1.5, 2.5),
)

# Kept source-modelled but intentionally inactive: current material selection
# cannot reliably identify galvanized steel versus CuNi alloy grade.
FUTURE_MATERIAL_VELOCITY_RULES: tuple[WarningRule, ...] = (
    WarningRule("velocity.sea_water.delivery.galvanized_steel.maximum", "flow_velocity", "SEA_WATER", "DELIVERY", None, 2.5, "m/s", WarningSeverity.ENGINEERING_WARNING, "warning.velocity.material_maximum", WARTSILA_SOURCE_ID, "Future-only material-specific maximum.", "GALVANIZED_STEEL", False),
    WarningRule("velocity.sea_water.delivery.10_90_cunife.maximum", "flow_velocity", "SEA_WATER", "DELIVERY", None, 3.0, "m/s", WarningSeverity.ENGINEERING_WARNING, "warning.velocity.material_maximum", WARTSILA_SOURCE_ID, "Future-only material-specific maximum.", "10_90_CUNIFE", False),
    WarningRule("velocity.sea_water.delivery.70_30_cuni.maximum", "flow_velocity", "SEA_WATER", "DELIVERY", None, 4.5, "m/s", WarningSeverity.ENGINEERING_WARNING, "warning.velocity.material_maximum", WARTSILA_SOURCE_ID, "Future-only material-specific maximum.", "70_30_CUNI", False),
)


def evaluate_velocity(system: str, line_role: str, velocity_m_s: float, material: str | None = None) -> tuple[EngineeringFinding, ...]:
    """Return recommended-range findings for an explicitly supplied context."""
    del material  # reserved for future inactive material-specific rules
    matches = tuple(
        rule for rule in VELOCITY_RULES
        if rule.active and rule.system == system and rule.line_role == line_role
    )
    if not matches:
        return ()
    if isinstance(velocity_m_s, bool) or not isinstance(velocity_m_s, (int, float)) or not math.isfinite(velocity_m_s):
        return (validation_finding(ValidationIssue("valid_number", "field.design_velocity")),)
    findings: list[EngineeringFinding] = []
    for rule in matches:
        below = rule.lower_bound is not None and velocity_m_s < rule.lower_bound
        above = rule.upper_bound is not None and velocity_m_s > rule.upper_bound
        if below or above:
            findings.append(_finding(rule, float(velocity_m_s), {"system": system, "line_role": line_role}))
    return tuple(findings)


def evaluate_npsh(enpym_available_m: float, npsh_required_m: float | None) -> tuple[EngineeringFinding, ...]:
    """Flag NPSHA/ENPYm not exceeding supplied NPSHr without blocking a result."""
    if npsh_required_m is None:
        return ()
    if any(isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) for value in (enpym_available_m, npsh_required_m)):
        return (validation_finding(ValidationIssue("valid_number", "field.npsh_required")),)
    if enpym_available_m > npsh_required_m:
        return ()
    return (EngineeringFinding(
        code="npsh.available_not_above_required",
        severity=WarningSeverity.CRITICAL_WARNING,
        message_key="warning.npsh.available_not_above_required",
        actual_value=float(enpym_available_m),
        lower_bound=float(npsh_required_m),
        upper_bound=None,
        unit="m",
        source_id=HYDRAULIC_INSTITUTE_SOURCE_ID,
        context={"available": "ENPYm", "required": "NPSHr"},
    ),)


def validation_finding(issue: ValidationIssue) -> EngineeringFinding:
    """Adapt existing semantic validation into the common ERROR taxonomy."""
    return EngineeringFinding(
        code=issue.code,
        severity=WarningSeverity.ERROR,
        message_key=f"validation.{issue.code}",
        actual_value=None,
        lower_bound=None,
        upper_bound=None,
        unit=None,
        source_id=None,
        context={} if issue.field_key is None else {"field_key": issue.field_key},
    )


def _finding(rule: WarningRule, actual_value: float, context: dict[str, str]) -> EngineeringFinding:
    return EngineeringFinding(
        code=rule.code,
        severity=rule.severity,
        message_key=rule.message_key,
        actual_value=actual_value,
        lower_bound=rule.lower_bound,
        upper_bound=rule.upper_bound,
        unit=rule.unit,
        source_id=rule.source_id,
        context=context,
    )
