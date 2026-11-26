"""Excel pressure equivalent of total head; not absolute or gauge pressure."""
import math
from engineering.validation import ValidationError, ValidationIssue


def pressure_equivalent_bar(density_kg_m3, system_head_m):
    for value,field in ((density_kg_m3,'discharge.pressure.density'),(system_head_m,'result.pump_discharge_head')):
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
            raise ValidationError(ValidationIssue('valid_number',field))
    if density_kg_m3<=0:
        raise ValidationError(ValidationIssue('greater_than_zero','discharge.pressure.density'))
    result=density_kg_m3 * 9.81 * system_head_m / 100_000
    if not math.isfinite(result):
        raise ValidationError(ValidationIssue('valid_number','discharge.pressure.title'))
    return result
