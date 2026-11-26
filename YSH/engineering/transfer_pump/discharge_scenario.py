"""User-defined constant-flow 115 percent scenario, separate from pump sizing."""
from dataclasses import dataclass
import math
from engineering.validation import ValidationError, ValidationIssue


@dataclass(frozen=True)
class Discharge115Result:
    scenario_flow_m3_h: float
    duration_h: float


def calculate_discharge_115(volume_m3, nominal_flow_m3_h):
    for value,key in ((volume_m3,'transfer.scenario115.volume'),(nominal_flow_m3_h,'transfer.scenario115.nominal')):
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
            raise ValidationError(ValidationIssue('valid_number',key))
        if value<=0:raise ValidationError(ValidationIssue('greater_than_zero',key))
    scenario_flow=1.15 * nominal_flow_m3_h
    duration=volume_m3 / scenario_flow
    if not math.isfinite(scenario_flow) or not math.isfinite(duration) or duration<=0:
        raise ValidationError(ValidationIssue('valid_number','transfer.scenario115.nominal'))
    return Discharge115Result(scenario_flow,duration)
