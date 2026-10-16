"""Configured pipe-design rules; no production classification data or coefficients."""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Callable

from engineering.pipe_design.validation import _positive, _non_negative
from engineering.provenance import EngineeringValue, OverridePolicy, SourceReference, SourceType, VerificationStatus
from engineering.validation import ValidationError, ValidationIssue


class DesignStatus(StrEnum):
    """Normal selection/configuration outcomes, distinct from invalid input."""

    SUCCESS = "SUCCESS"
    NO_PIPE_CANDIDATE = "NO_PIPE_CANDIDATE"
    NO_STANDARD_WALL_MATCH = "NO_STANDARD_WALL_MATCH"
    SOURCE_REQUIRED = "SOURCE_REQUIRED"
    RULE_NOT_CONFIGURED = "RULE_NOT_CONFIGURED"


class StressMode(StrEnum):
    """Explicit material rule family; direct-table mode never falls back to steel."""

    LEGACY_RP02 = "LEGACY_RP02"
    FACTOR_BASED_STEEL_RULE = "FACTOR_BASED_STEEL_RULE"
    DIRECT_TABLE_RULE = "DIRECT_TABLE_RULE"
    USER_PROVIDED_RULE = "USER_PROVIDED_RULE"


@dataclass(frozen=True, slots=True)
class RuleValue:
    """A value is absent when a rule cannot be applied; absence is not zero."""

    value: float | None
    status: DesignStatus
    source: SourceReference | None = None
    detail: str | None = None


def _source_ready(source: SourceReference | None) -> bool:
    return bool(source and source.verification_status is VerificationStatus.VERIFIED
                and source.document and source.document.strip())


@dataclass(frozen=True, slots=True)
class StrengthLimit:
    """One explicitly applicable, caller-configured strength/factor term in MPa."""

    name: str
    strength_mpa: float
    factor: float

    def __post_init__(self) -> None:
        _positive(self.strength_mpa, "strength_mpa")
        _positive(self.factor, "strength_factor")


@dataclass(frozen=True, slots=True)
class StressPoint:
    """A configured exact-temperature allowable-stress table row, in °C and MPa."""

    temperature_c: float
    allowable_stress_mpa: float

    def __post_init__(self) -> None:
        _finite_temperature(self.temperature_c)
        _positive(self.allowable_stress_mpa, "result.allowable_stress")


def _finite_temperature(value: float) -> None:
    import math
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValidationError(ValidationIssue("valid_number", "design_temperature_c"))


@dataclass(frozen=True, slots=True)
class AllowableStressRule:
    """Rule capability only: all steel terms and table rows must be supplied."""

    mode: StressMode = StressMode.LEGACY_RP02
    source: SourceReference | None = None
    limits: tuple[StrengthLimit, ...] = ()
    table: tuple[StressPoint, ...] = ()
    user_value_mpa: float | None = None

    def evaluate(
        self, *, yield_strength_mpa: float | None = None,
        safety_factor: float | None = None, design_temperature_c: float | None = None,
    ) -> RuleValue:
        """Evaluate configured terms or exact table rows without guessed defaults."""
        if not isinstance(self.mode, StressMode):
            raise ValidationError(ValidationIssue("valid_number", "allowable_stress_rule"))
        if design_temperature_c is not None:
            _finite_temperature(design_temperature_c)
        if self.mode is StressMode.LEGACY_RP02:
            if yield_strength_mpa is None or safety_factor is None:
                return RuleValue(None, DesignStatus.RULE_NOT_CONFIGURED, detail="LEGACY_MATERIAL_DATA_REQUIRED")
            _positive(yield_strength_mpa, "field.yield_strength")
            _positive(safety_factor, "field.safety_factor")
            source = SourceReference(
                source_type=SourceType.ENGINEERING_REFERENCE,
                verification_status=VerificationStatus.UNVERIFIED,
                notes="Existing Rp0.2 / B compatibility calculation; not a verified current TL rule.",
            )
            return RuleValue(yield_strength_mpa / safety_factor, DesignStatus.SUCCESS, source, "LEGACY_COMPATIBILITY")
        if self.mode is StressMode.USER_PROVIDED_RULE:
            if self.user_value_mpa is None:
                return RuleValue(None, DesignStatus.RULE_NOT_CONFIGURED, self.source, "USER_STRESS_REQUIRED")
            _positive(self.user_value_mpa, "result.allowable_stress")
            source = self.source or SourceReference(source_type=SourceType.USER_INPUT, verification_status=VerificationStatus.USER_SUPPLIED)
            return RuleValue(self.user_value_mpa, DesignStatus.SUCCESS, source, "USER_PROVIDED")
        if self.mode is StressMode.FACTOR_BASED_STEEL_RULE:
            if not self.limits:
                return RuleValue(None, DesignStatus.RULE_NOT_CONFIGURED, self.source, "STRENGTH_TERMS_NOT_CONFIGURED")
            if not _source_ready(self.source):
                return RuleValue(None, DesignStatus.SOURCE_REQUIRED, self.source, "STRENGTH_RULE_SOURCE_REQUIRED")
            return RuleValue(min(term.strength_mpa / term.factor for term in self.limits), DesignStatus.SUCCESS, self.source)
        if not self.table:
            return RuleValue(None, DesignStatus.RULE_NOT_CONFIGURED, self.source, "STRESS_TABLE_NOT_CONFIGURED")
        if design_temperature_c is None:
            return RuleValue(None, DesignStatus.RULE_NOT_CONFIGURED, self.source, "DESIGN_TEMPERATURE_REQUIRED")
        if not _source_ready(self.source):
            return RuleValue(None, DesignStatus.SOURCE_REQUIRED, self.source, "STRESS_TABLE_SOURCE_REQUIRED")
        if len({row.temperature_c for row in self.table}) != len(self.table):
            raise ValidationError(ValidationIssue("valid_number", "allowable_stress_table"))
        match = next((row for row in self.table if row.temperature_c == design_temperature_c), None)
        if match is None:
            return RuleValue(None, DesignStatus.RULE_NOT_CONFIGURED, self.source, "TABLE_TEMPERATURE_NOT_CONFIGURED")
        return RuleValue(match.allowable_stress_mpa, DesignStatus.SUCCESS, self.source)


@dataclass(frozen=True, slots=True)
class ManufacturingToleranceRule:
    """Caller-supplied verified formula; no built-in EN/ASME tolerance formula."""

    negative_tolerance_percent: float | None = None
    allowance_formula: Callable[[float, float], float] | None = None
    source: SourceReference | None = None

    def evaluate(self, base_wall_mm: float) -> RuleValue:
        """Call a configured formula only after its source is explicitly verified."""
        _non_negative(base_wall_mm, "result.base_wall_thickness")
        if self.negative_tolerance_percent is None or self.allowance_formula is None:
            return RuleValue(None, DesignStatus.RULE_NOT_CONFIGURED, self.source, "TOLERANCE_RULE_NOT_CONFIGURED")
        _non_negative(self.negative_tolerance_percent, "negative_tolerance_percent")
        if self.negative_tolerance_percent >= 100:
            raise ValidationError(ValidationIssue("valid_number", "negative_tolerance_percent"))
        if not _source_ready(self.source):
            return RuleValue(None, DesignStatus.SOURCE_REQUIRED, self.source, "TOLERANCE_SOURCE_REQUIRED")
        result = self.allowance_formula(base_wall_mm, self.negative_tolerance_percent)
        _non_negative(result, "manufacturing_allowance_mm")
        return RuleValue(result, DesignStatus.SUCCESS, self.source)


@dataclass(frozen=True, slots=True)
class MinimumWallRule:
    """An explicitly configured minimum for the caller's applicable context."""

    minimum_wall_mm: float | None = None
    source: SourceReference | None = None

    def evaluate(self) -> RuleValue:
        """Do not turn an unavailable minimum into a zero-valued rule."""
        if self.minimum_wall_mm is None:
            return RuleValue(None, DesignStatus.RULE_NOT_CONFIGURED, self.source, "MINIMUM_WALL_NOT_CONFIGURED")
        _non_negative(self.minimum_wall_mm, "minimum_wall_mm")
        if not _source_ready(self.source):
            return RuleValue(None, DesignStatus.SOURCE_REQUIRED, self.source, "MINIMUM_WALL_SOURCE_REQUIRED")
        return RuleValue(self.minimum_wall_mm, DesignStatus.SUCCESS, self.source)


def fuel_velocity_criterion() -> EngineeringValue:
    """Return the user-approved D243 maximum; it is not a TL requirement."""
    return EngineeringValue(
        used_value=7.0, recommended_value=7.0, unit="m/s",
        source=SourceReference(source_type=SourceType.D243_CRITERION, verification_status=VerificationStatus.USER_SUPPLIED,
                               notes="D243 V2 project fuel design maximum; not a TL rule."),
        override_policy=OverridePolicy.LOCKED, symbol="V", terminology_key="engineering.V",
    )
