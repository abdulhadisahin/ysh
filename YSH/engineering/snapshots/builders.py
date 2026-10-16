"""Snapshot adapters consume successful results; no engineering arithmetic or live lookups."""
from __future__ import annotations

from dataclasses import fields, replace
from uuid import UUID

from engineering.module_registry import ModuleCode
from engineering.system_context import SystemContext
from engineering.snapshots.models import CalculationSnapshot
from engineering.snapshots.serialization import canonical
from engineering.formula.pipe import legacy_pipe_steps, pipe_steps, selection_geometry_steps
from engineering.formula.discharge import hydraulic_steps
from engineering.formula.suction import suction_steps
from engineering.formula.transfer import design_steps, empirical_steps
from engineering.provenance import SourceReference, SourceType
from engineering.pipe_design.models import PipeDesignCalculationResult
from engineering.pipe_design.v2_models import PipeSelection, PipeDesignV2Input
from engineering.head_loss.v2_models import DischargeV2Result
from engineering.suction_npsh.v2_models import SuctionV2Result, SuctionV2LossResult
from engineering.transfer_pump.v2_models import TransferPumpDesignResult, TransferPumpEmpiricalResult
from engineering.warning_rules import SOURCE_REGISTRY, EngineeringFinding


def result_fields(result: object) -> dict[str, object]:
    """Capture outputs/audit once; input and staged hydraulics are recorded separately."""
    data={f.name:getattr(result,f.name) for f in fields(result) if f.name not in ('input','hydraulic')}
    if 'metadata' in data:
        data['metadata']={k:v for k,v in data['metadata'].items() if k!='head_loss'}
    return data


def _material_source(steps: tuple, metadata: dict) -> tuple:
    material=metadata.get('used_material')
    if not material: return steps
    source=SourceReference(source_type=SourceType.MATERIAL_STANDARD,
                           document=material.get('standard') or None,notes=material.get('source') or None)
    return tuple(replace(step,
        variables=tuple(replace(v,source=source) if v.symbol=='k' else v for v in step.variables),
        used_values=tuple(replace(v,source=source) if v.symbol=='k' else v for v in step.used_values)) for step in steps)


def _pipe(stage: str, result: object, selection: PipeSelection | None) -> tuple:
    if not isinstance(result,PipeDesignCalculationResult) or not result.is_successful:
        raise ValueError('A successful pipe result is required')
    key='diameter' if stage=='diameter' else 'wall' if stage=='wall' else None
    if key is None or f'{key}_input' not in result.trace:
        raise ValueError('Missing actually used pipe inputs')
    if key=='diameter' and result.diameter is None or key=='wall' and result.wall_thickness is None:
        raise ValueError('Incomplete pipe stage')
    steps=legacy_pipe_steps(result)
    material=result.trace.get('material')
    if material:
        source=SourceReference(source_type=SourceType.MATERIAL_STANDARD,
                               document=material.get('standard') or None,notes=material.get('source') or None)
        steps=tuple(replace(step,sources=step.sources+(source,)) if step.step_id=='pipe.stress' else step for step in steps)
    if selection is not None:
        steps=tuple(s for s in steps if s.step_id!='pipe.Di')+selection_geometry_steps(selection)
    return ({'calculation':result,'published_selection':selection},steps,'PIPE_LEGACY_1')


def _discharge(stage: str, result: object, selection: object) -> tuple:
    if stage!='hydraulics' or not isinstance(result,DischargeV2Result):
        raise ValueError('A complete discharge result is required')
    facts={'input':result.input,'outputs':result_fields(result)}
    return facts,_material_source(hydraulic_steps(result),result.metadata),'HYDRAULIC_COEFFICIENTS_1'


def _suction(stage: str, result: object, selection: object) -> tuple:
    if stage=='hydraulics' and isinstance(result,SuctionV2LossResult):
        return ({'input':result.input,'outputs':result_fields(result)},
                _material_source(hydraulic_steps(result),result.metadata),'SUCTION_HYDRAULICS_1')
    if stage=='enpy' and isinstance(result,SuctionV2Result):
        facts={'input':result.input,'outputs':result_fields(result),
               'hydraulic_input':result.hydraulic.input,'hydraulic_outputs':result_fields(result.hydraulic)}
        return facts,_material_source(suction_steps(result),result.hydraulic.metadata),'ENPY_SINGLE_SOURCE_1'
    raise ValueError('A complete suction/ENPY stage is required')


def _transfer(stage: str, result: object, selection: object) -> tuple:
    if stage=='design' and isinstance(result,TransferPumpDesignResult):
        return {'calculation':result},design_steps(result),'TRANSFER_VOLUME_TIME_1'
    if stage=='empirical' and isinstance(result,TransferPumpEmpiricalResult):
        if not result.estimate.is_successful or result.estimate.regression_model is None:
            raise ValueError('A successful regression result is required')
        return {'calculation':result},empirical_steps(result),'TRANSFER_OLS_VESSEL_REFERENCE_1'
    raise ValueError('A complete active transfer mode is required')


def build_snapshot(module: ModuleCode, stage: str, result: object, *,
                   context: SystemContext, project_id: UUID | None = None,
                   selection: PipeSelection | None = None,
                   findings: tuple[EngineeringFinding, ...] = ()) -> CalculationSnapshot:
    """Freeze the result and explanatory steps at the success event, not at project save."""
    builder={ModuleCode.PIPE_DESIGN:_pipe,ModuleCode.DISCHARGE:_discharge,
             ModuleCode.SUCTION_NPSH:_suction,ModuleCode.TRANSFER_PUMP:_transfer}[module]
    facts,steps,version=builder(stage,result,selection)
    if not steps: raise ValueError('Incomplete calculation has no historical steps')
    return _snapshot(module,stage,version,facts,steps,context,project_id,findings)


def build_pipe_v2_snapshot(result: PipeSelection, used_input: PipeDesignV2Input, *,
                           context: SystemContext, project_id: UUID | None = None) -> CalculationSnapshot:
    """Capture configured V2 output and scalar inputs, never serialize rule callbacks."""
    if result.selected_pipe is None or result.wall is None or result.allowable_stress is None or result.allowable_stress.value is None:
        raise ValueError('Incomplete pipe selection')
    inputs={f.name:getattr(used_input,f.name) for f in fields(used_input)
            if f.name not in ('stress_rule','tolerance_rule','minimum_wall_rule')}
    inputs['stress_mode']=used_input.stress_rule.mode
    inputs['applied_stress_terms']=used_input.stress_rule.limits
    inputs['applied_stress_table_point']=tuple(point for point in used_input.stress_rule.table
                                             if point.temperature_c==used_input.design_temperature_c)
    if result.manufacturing_tolerance and result.manufacturing_tolerance.value is not None:
        inputs['applied_negative_tolerance_percent']=used_input.tolerance_rule.negative_tolerance_percent
    return _snapshot(ModuleCode.PIPE_DESIGN,'selection','PIPE_V2_CONFIGURED_1',
                     {'input':inputs,'selection':result},pipe_steps(result,used_input),context,project_id,())


def _snapshot(module,stage,version,facts,steps,context,project_id,findings) -> CalculationSnapshot:
    sources=tuple(SOURCE_REGISTRY[f.source_id] for f in findings if f.source_id in SOURCE_REGISTRY)
    summary=tuple({'symbol':step.result_symbol,'value':step.result_value,'unit':step.result_unit}
                  for step in steps if step.result_symbol in ('D','Di','s','Hs','he','ENPYm','Qgerekli','Qpump','ttransfer'))
    for symbol in ('Q','Di'):
        if not any(value['symbol']==symbol for value in summary):
            variable=next((v for step in steps for v in step.variables if v.symbol==symbol),None)
            if variable is not None:
                summary+=({'symbol':symbol,'value':variable.value,'unit':variable.unit},)
    evidence={'facts':facts,'steps':steps,'context':context,'summary':summary,
              'findings':findings,'finding_sources':sources}
    return CalculationSnapshot(module_code=module,stage=stage,model_version=version,
                               project_id=project_id,evidence_json=canonical(evidence))
