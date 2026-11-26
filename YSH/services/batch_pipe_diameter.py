"""Independent row validation; all engineering and DN selection stay shared."""
from dataclasses import dataclass

from engineering.input_parsing import parse_engineering_float
from engineering.pipe_design.models import PipeDiameterInput
from engineering.validation import ValidationError, ValidationIssue


@dataclass(frozen=True)
class BatchDiameterResult:
    diameter_mm: float | None = None
    dn: str | None = None
    issue: ValidationIssue | None = None


def calculate_rows(service, rows, standard_code):
    results=[]
    for name,flow,velocity in rows:
        if not any(text.strip() for text in (name,flow,velocity)):
            results.append(BatchDiameterResult())
            continue
        try:
            q=parse_engineering_float(flow,field_name='Flow',field_key='batch.flow')
            v=parse_engineering_float(velocity,field_name='Velocity',field_key='batch.velocity')
            if not standard_code:raise ValidationError(ValidationIssue('pipe_standard_required'))
            result=service.calculate_batch_diameter(PipeDiameterInput(q,v),standard_code)
            results.append(BatchDiameterResult(result.diameter_mm,result.recommended_dn))
        except ValidationError as error:
            results.append(BatchDiameterResult(issue=error.issue))
        except (LookupError,ValueError):
            results.append(BatchDiameterResult(issue=ValidationIssue('pipe_standard_not_found')))
    return results
