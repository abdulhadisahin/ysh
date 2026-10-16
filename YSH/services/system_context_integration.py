"""Copy project identity into new results without modifying engineering values."""
from dataclasses import replace

from engineering.system_context import SystemContext
from engineering.pipe_design.v2_models import PipeSelection
from engineering.pipe_design.transfer import engineering_signature
from engineering.transfer_pump.v2_models import PumpIntegrationContext


def contextualize_selection(result: PipeSelection, context: SystemContext,
                            previous: PipeSelection | None = None) -> PipeSelection:
    """Revise the final publication once, after all context metadata is applied."""
    result = replace(result, system_id=context.system_id,
                     circuit_id=context.circuit_id, fluid_id=context.fluid_id)
    if previous is not None:
        changed = engineering_signature(previous) != engineering_signature(result)
        result = replace(result, selection_id=previous.selection_id,
                         revision=previous.revision + int(changed))
    return result


def pump_context(current: PumpIntegrationContext, project: SystemContext | None) -> PumpIntegrationContext:
    """Only identity metadata changes; external head/NPSH facts remain unchanged."""
    if project is None:
        return current
    return replace(current, system_id=project.system_id,
                   circuit_id=project.circuit_id, fluid_id=project.fluid_id)
