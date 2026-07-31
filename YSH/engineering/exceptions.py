"""Exception hierarchy for YSH engineering infrastructure."""

from __future__ import annotations


class EngineeringError(Exception):
    """Base exception for user-relevant engineering processing failures."""


class EngineeringValidationError(EngineeringError, ValueError):
    """Raised when an engineering input fails reusable validation rules."""


class UnitConversionError(EngineeringError, ValueError):
    """Raised when a requested engineering unit conversion cannot be completed."""


class UnsupportedUnitError(UnitConversionError):
    """Raised when a unit is outside the explicit YSH Version 1 unit set."""
