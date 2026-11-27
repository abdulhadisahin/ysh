from uuid import UUID
from engineering.formula.discharge import hydraulic_steps
from engineering.head_loss.v2_models import DischargeLocalLoss, DischargeV2Input
from engineering.module_registry import ModuleCode
from engineering.pipe_design.transfer import PipeInputState, PipeValues
from engineering.snapshots.builders import build_snapshot, material_source_steps
from engineering.system_context import ContextReference, SystemContext
from services.discharge_head_loss_service import DischargeHeadLossService


def test_displayed_steps_match_frozen_steps_when_a_library_material_is_used():
    """The Word button compares frozen steps with the displayed ones; the material source must be in both."""
    value = DischargeV2Input(pipe_input=PipeInputState(manual_values=PipeValues(actual_internal_diameter_mm=101, flow_rate_m3_h=20)),
        kinematic_viscosity_m2s=2e-6, pipe_length_m=20, roughness_mm=.015, geodetic_head_m=2,
        local_losses=(DischargeLocalLoss('TEST bend', 2, .5),))
    result = DischargeHeadLossService(object()).calculate_v2(value)
    result.metadata['used_material'] = {'standard': 'TS EN 10216-1', 'source': 'Library'}
    context = SystemContext(system=ContextReference(id=UUID(int=1), code='T', name_tr='Örnek'))
    snapshot = build_snapshot(ModuleCode.DISCHARGE, 'hydraulics', result, context=context)
    shown = material_source_steps(hydraulic_steps(result), result.metadata)
    assert snapshot.formula_steps and all(step in shown for step in snapshot.formula_steps)
    assert not all(step in hydraulic_steps(result) for step in snapshot.formula_steps)
