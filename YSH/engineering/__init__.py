"""Shared engineering infrastructure for YSH calculation modules."""

import sys

sys.modules.setdefault("engineering", sys.modules[__name__])

from .exceptions import (
    EngineeringError,
    EngineeringValidationError,
    UnitConversionError,
    UnsupportedUnitError,
)
from .result import EngineeringMessage, EngineeringResult

__all__ = [
    "EngineeringError",
    "EngineeringMessage",
    "EngineeringResult",
    "EngineeringValidationError",
    "UnitConversionError",
    "UnsupportedUnitError",
]
