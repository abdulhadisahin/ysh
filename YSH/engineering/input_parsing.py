"""Locale-tolerant parsing for user-entered engineering numbers."""

from __future__ import annotations

import math
import re

from engineering.exceptions import EngineeringValidationError
from engineering.validation import ValidationError, ValidationIssue


_NUMBER = re.compile(r"[+-]?(?:\d+(?:[.,]\d*)?|[.,]\d+)(?:[eE][+-]?\d+)?$")
_INTEGER = re.compile(r"[+-]?\d+$")


def _normalise(value: object, field_name: str, allow_empty: bool, field_key: str | None) -> str | None:
    """Validate text input and normalize an accepted decimal separator."""
    if isinstance(value, bool) or not isinstance(value, str):
        _raise_number_issue(field_name, field_key, "valid_number")
    text = value.strip()
    if not text:
        if allow_empty:
            return None
        _raise_number_issue(field_name, field_key, "required")
    if "," in text and "." in text:
        _raise_number_issue(field_name, field_key, "valid_number")
    if not _NUMBER.fullmatch(text):
        _raise_number_issue(field_name, field_key, "valid_number")
    return text.replace(",", ".")


def parse_engineering_float(
    value: object,
    *,
    field_name: str,
    allow_empty: bool = False,
    field_key: str | None = None,
) -> float | None:
    """Parse a finite float accepting either a decimal point or decimal comma."""
    normalized = _normalise(value, field_name, allow_empty, field_key)
    if normalized is None:
        return None
    parsed = float(normalized)
    if not math.isfinite(parsed):
        _raise_number_issue(field_name, field_key, "valid_number")
    return parsed


def parse_engineering_integer(
    value: object,
    *,
    field_name: str,
    allow_empty: bool = False,
    field_key: str | None = None,
) -> int | None:
    """Parse an integer while rejecting decimal and non-finite input."""
    if isinstance(value, bool) or not isinstance(value, str):
        _raise_number_issue(field_name, field_key, "whole_number")
    text = value.strip()
    if not text:
        if allow_empty:
            return None
        _raise_number_issue(field_name, field_key, "required")
    if not _INTEGER.fullmatch(text):
        _raise_number_issue(field_name, field_key, "whole_number")
    return int(text)


def _raise_number_issue(field_name: str, field_key: str | None, code: str) -> None:
    """Raise a semantic issue when a caller supplies a stable field key."""
    if field_key is not None:
        raise ValidationError(ValidationIssue(code, field_key))
    if code == "required":
        raise EngineeringValidationError(f"{field_name} is required.")
    raise EngineeringValidationError(f"{field_name} must be a valid number.")
