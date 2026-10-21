"""Field-specific semantic errors, with no regulatory bounds or display text."""
import math

from engineering.validation import ValidationError, ValidationIssue


def finite(value: object, field: str) -> float:
    try:
        valid = (not isinstance(value, bool) and isinstance(value, (int, float))
                 and math.isfinite(value))
    except OverflowError:
        valid = False
    if not valid:
        raise ValidationError(ValidationIssue("valid_number", field))
    return float(value)


def positive(value: object, field: str, *, zero_allowed: bool = False) -> float:
    number = finite(value, field)
    if number < 0 or (number == 0 and not zero_allowed):
        code = "zero_or_greater" if zero_allowed else "greater_than_zero"
        raise ValidationError(ValidationIssue(code, field))
    return number


def fraction(value: object, field: str, *, endpoints: bool = False) -> float:
    number = finite(value, field)
    if not (0 <= number <= 1 if endpoints else 0 < number < 1):
        raise ValidationError(ValidationIssue("fire.fraction_range", field))
    return number
