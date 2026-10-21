"""Consume existing applied PipeSelection geometry, never recompute OD minus wall."""
from engineering.fire.enums import HWApplicability
from engineering.fire.models import HazenWilliamsInput
from engineering.fire.provenance import ParameterProvenance
from engineering.fire.units import m3h_to_lpm
from engineering.pipe_design.transfer import PipeInputState
from engineering.system_context import SystemContext


def hazen_williams_from_pipe(
    pipe_input: PipeInputState, *, pipe_length_m: float, hazen_williams_c: float,
    applicability: HWApplicability, provenance: tuple[ParameterProvenance, ...] = (),
    context: SystemContext | None = None,
) -> HazenWilliamsInput:
    """Use applied/manual Q/Di with frozen link metadata; CHW stays independent.

    Link/update/keep-current decisions belong to existing PipeInputState methods.
    This adapter neither observes live sources nor upgrades fluid applicability.
    """
    if not isinstance(pipe_input, PipeInputState):
        raise TypeError("pipe_input requires PipeInputState")
    diameter, flow_m3h = pipe_input.used_values.hydraulic_values()
    return HazenWilliamsInput(flow_lpm=m3h_to_lpm(flow_m3h), inside_diameter_mm=diameter,
        pipe_length_m=pipe_length_m, hazen_williams_c=hazen_williams_c,
        applicability=applicability, provenance=provenance,
        context=context if context is not None else SystemContext(), pipe_input=pipe_input)
