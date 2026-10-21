"""Freeze successful Fire workflow evidence without calculators or live resolvers."""
from uuid import UUID

from engineering.fire.enums import HWApplicability
from engineering.fire.foam_workflow import FoamWorkflowResult
from engineering.fire.hazen_williams_workflow import HazenWilliamsWorkflowResult, HWService
from engineering.module_registry import ModuleCode
from engineering.snapshots.models import CalculationSnapshot
from engineering.snapshots.serialization import canonical


def build_fire_snapshot(result: FoamWorkflowResult | HazenWilliamsWorkflowResult, *,
                        project_id: UUID | None = None) -> CalculationSnapshot:
    """Store already computed steps and complete detached workflow payload, schema 1."""
    if isinstance(result, FoamWorkflowResult):
        module = ModuleCode.FIRE_FOAM_SYSTEM
    elif isinstance(result, HazenWilliamsWorkflowResult):
        if result.service is not HWService.WATER or result.applicability is not HWApplicability.WATER_ONLY:
            raise ValueError("Only supported water HW results can become snapshots")
        module = ModuleCode.FIRE_HAZEN_WILLIAMS
    else:
        raise TypeError("A successful Foam or water HW workflow result is required")
    payload = result.snapshot_payload
    if payload.get('calculation_validity') != 'VALID' or payload.get('calculation_type') != module.value:
        raise ValueError("Successful matching Fire evidence is required")
    # Payload is authoritative; never rebuild steps using today's formula builders.
    evidence = {'facts': {'fire': payload}, 'steps': payload['formula_steps'],
                'context': payload['context'], 'summary': payload['summary'],
                'findings': [], 'finding_sources': []}
    return CalculationSnapshot(module_code=module, stage='workflow',
        model_version=payload['workflow_version'], project_id=project_id,
        evidence_json=canonical(evidence))
