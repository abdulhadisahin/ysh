"""Typed display data; no calculators, persistence or localized engineering text."""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from engineering.provenance import EngineeringValue, SourceReference


class CalculationClassification(StrEnum):
    """Ownership is explicit, never inferred from a module name."""
    ENGINEERING_CALCULATION = "ENGINEERING_CALCULATION"
    TL_RULE_CALCULATION = "TL_RULE_CALCULATION"
    ENGINEERING_WITH_TL_CHECK = "ENGINEERING_WITH_TL_CHECK"
    D243_DESIGN_CRITERION = "D243_DESIGN_CRITERION"
    EMPIRICAL_REFERENCE_ESTIMATE = "EMPIRICAL_REFERENCE_ESTIMATE"


class SelectionReason(StrEnum):
    """Stable reasons translated by the presentation layer."""
    USER_INPUT = "USER_INPUT"
    PIPE_STANDARD = "PIPE_STANDARD"
    LINKED_PIPE_SELECTION = "LINKED_PIPE_SELECTION"
    D243_CRITERION = "D243_CRITERION"
    MATERIAL_LIBRARY = "MATERIAL_LIBRARY"
    REFERENCE_VESSEL_DATA = "REFERENCE_VESSEL_DATA"
    CALCULATED = "CALCULATED"
    CONFIGURED = "CONFIGURED"


class CheckStatus(StrEnum):
    """A check outcome is separate from a successful arithmetic operation."""
    PASS = "PASS"
    WARNING = "WARNING"
    FAIL = "FAIL"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    NOT_CONFIGURED = "NOT_CONFIGURED"


@dataclass(frozen=True, slots=True, kw_only=True)
class FormulaVariable:
    """A raw input or intermediate, with optional upstream snapshot identity."""
    symbol: str
    terminology_key: str
    value: float
    unit: str
    source: SourceReference | None = None
    reason: SelectionReason | None = None
    source_selection_id: UUID | None = None
    source_revision: int | None = None
    context: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class FormulaCheck:
    """Suitability under an existing criterion, without a new safety margin."""
    status: CheckStatus
    actual_value: float | None = None
    reference_value: float | None = None
    operator: str | None = None
    reason_key: str | None = None
    source: SourceReference | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class FormulaStep:
    """One precomputed explanation; raw numeric precision is retained."""
    step_id: str
    title_key: str
    formula_text: str
    result_value: float
    result_unit: str
    result_symbol: str
    display_order: int
    variables: tuple[FormulaVariable, ...] = ()
    reference_variables: tuple[FormulaVariable, ...] = ()
    used_values: tuple[EngineeringValue, ...] = ()
    selection_reason: SelectionReason | None = None
    sources: tuple[SourceReference, ...] = ()
    substitution: str | None = None
    check: FormulaCheck | None = None
    classification: CalculationClassification = CalculationClassification.ENGINEERING_CALCULATION


def ordered_steps(steps: tuple[FormulaStep, ...]) -> tuple[FormulaStep, ...]:
    """Use stable identifiers to break display-order ties deterministically."""
    return tuple(sorted(steps, key=lambda step: (step.display_order, step.step_id)))
