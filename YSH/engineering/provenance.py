"""Immutable engineering values and provenance, independent of UI and storage.

Only ``used_value`` is the effective value. ``value`` is a read-only alias;
``recommended_value`` preserves the original recommendation, if one is known.
An override is a difference from that recommendation, never a separate flag.
Terminology keys are opaque references to i18n (for example ``engineering.v``).
No source or verification facts are inferred from the current application.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, datetime
from enum import StrEnum
import math


class SourceType(StrEnum):
    """Semantically distinct origins of engineering information."""

    USER_INPUT = "USER_INPUT"
    PROJECT_CRITERION = "PROJECT_CRITERION"
    D243_CRITERION = "D243_CRITERION"
    TL_RULE = "TL_RULE"
    MATERIAL_STANDARD = "MATERIAL_STANDARD"
    PIPE_STANDARD = "PIPE_STANDARD"
    FLUID_LIBRARY = "FLUID_LIBRARY"
    ENGINEERING_REFERENCE = "ENGINEERING_REFERENCE"
    MANUFACTURER_DATA = "MANUFACTURER_DATA"
    CALCULATED = "CALCULATED"
    REFERENCE_VESSEL_DATA = "REFERENCE_VESSEL_DATA"


class VerificationStatus(StrEnum):
    """Explicit source verification, independent of source availability."""

    VERIFIED = "VERIFIED"
    PARTIALLY_VERIFIED = "PARTIALLY_VERIFIED"
    USER_SUPPLIED = "USER_SUPPLIED"
    UNVERIFIED = "UNVERIFIED"
    DEPRECATED = "DEPRECATED"


class OverridePolicy(StrEnum):
    """Locked recommendation, editable suggestion, or direct user entry."""

    LOCKED = "LOCKED"
    SUGGESTED = "SUGGESTED"
    USER_INPUT = "USER_INPUT"


def _optional_text(name: str, value: str | None) -> None:
    if value is not None and not isinstance(value, str):
        raise TypeError(f"{name} must be a string or None")


def _number(name: str, value: float | int) -> None:
    if isinstance(value, bool) or not isinstance(value, (float, int)):
        raise TypeError(f"{name} must be a real number")
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")


@dataclass(frozen=True, slots=True, kw_only=True)
class SourceReference:
    """Known source facts only; unknown dates and verification remain unset."""

    source_type: SourceType
    source_organization: str | None = None
    document: str | None = None
    part: str | None = None
    section: str | None = None
    article: str | None = None
    table: str | None = None
    formula: str | None = None
    revision: str | None = None
    effective_date: date | None = None
    verification_date: date | None = None
    verification_status: VerificationStatus | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.source_type, SourceType):
            raise TypeError("source_type must be a SourceType")
        if self.verification_status is not None and not isinstance(
            self.verification_status, VerificationStatus
        ):
            raise TypeError("verification_status must be a VerificationStatus or None")
        for name in ("effective_date", "verification_date"):
            value = getattr(self, name)
            if value is not None and (not isinstance(value, date) or isinstance(value, datetime)):
                raise TypeError(f"{name} must be a date or None")
        for name in (
            "source_organization", "document", "part", "section", "article",
            "table", "formula", "revision", "notes",
        ):
            _optional_text(name, getattr(self, name))


@dataclass(frozen=True, slots=True, kw_only=True)
class EngineeringValue:
    """One effective numeric value with an optional preserved recommendation.

    LOCKED and SUGGESTED require a recommendation. LOCKED requires equality.
    USER_INPUT has no recommendation: edits are direct input, not overrides.
    SUGGESTED may differ only with a nonempty override reason. Returning to the
    recommendation clears the override and its reason. Constructing or replacing
    the dataclass enforces the same rules as ``with_used_value``.
    """

    used_value: float | int
    unit: str
    source: SourceReference
    override_policy: OverridePolicy
    symbol: str | None = None
    terminology_key: str | None = None
    selection_reason: str | None = None
    recommended_value: float | int | None = None
    override_reason: str | None = None

    def __post_init__(self) -> None:
        _number("used_value", self.used_value)
        if not isinstance(self.unit, str):
            raise TypeError("unit must be a string")
        if not isinstance(self.source, SourceReference):
            raise TypeError("source must be a SourceReference")
        if not isinstance(self.override_policy, OverridePolicy):
            raise TypeError("override_policy must be an OverridePolicy")
        for name in ("symbol", "terminology_key", "selection_reason", "override_reason"):
            _optional_text(name, getattr(self, name))
        if self.recommended_value is not None:
            _number("recommended_value", self.recommended_value)
        if self.override_policy is OverridePolicy.USER_INPUT:
            if self.recommended_value is not None:
                raise ValueError("USER_INPUT has no recommendation; use SUGGESTED instead")
        elif self.recommended_value is None:
            raise ValueError("LOCKED and SUGGESTED require a recommended_value")
        if self.is_overridden:
            if not self.override_allowed:
                raise ValueError("A locked value cannot be overridden")
            if not self.override_reason or not self.override_reason.strip():
                raise ValueError("An override requires a nonempty override_reason")
        elif self.override_reason is not None:
            raise ValueError("override_reason requires an actual override")

    @property
    def value(self) -> float | int:
        """Read-only alias for the effective used value, never a second field."""
        return self.used_value

    @property
    def override_allowed(self) -> bool:
        """Only an editable recommendation can be overridden."""
        return self.override_policy is OverridePolicy.SUGGESTED

    @property
    def is_overridden(self) -> bool:
        return self.recommended_value is not None and self.used_value != self.recommended_value

    def with_used_value(
        self, used_value: float | int, *, override_reason: str | None = None
    ) -> EngineeringValue:
        """Return a validated copy; preserve the original recommendation/source."""
        return replace(self, used_value=used_value, override_reason=override_reason)
