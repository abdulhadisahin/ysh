"""Deterministic JSON for explicitly allowed calculation facts and FormulaSteps."""
from __future__ import annotations

from dataclasses import fields, is_dataclass
from datetime import date, datetime
from enum import Enum
import json
import math
from types import UnionType
from typing import get_args, get_origin, get_type_hints
from uuid import UUID

from engineering.formula.models import FormulaStep, FormulaVariable, FormulaCheck
from engineering.provenance import EngineeringValue, SourceReference
from engineering.system_context import SystemContext, ContextReference

_FACT_MODULES = {
    'engineering.pipe_design.models','engineering.pipe_design.v2_models',
    'engineering.pipe_design.rules','engineering.pipe_design.transfer',
    'engineering.head_loss.models','engineering.head_loss.v2_models',
    'engineering.suction_npsh.models','engineering.suction_npsh.v2_models',
    'engineering.transfer_pump.models','engineering.transfer_pump.v2_models',
    'engineering.transfer_pump.capacity_basis','engineering.warning_rules',
    'engineering.validation','core.local_loss_item',
}
_TYPED = {FormulaStep,FormulaVariable,FormulaCheck,EngineeringValue,SourceReference,SystemContext,ContextReference}


def primitive(value: object) -> object:
    """Copy only calculation-domain facts; widgets, services and callbacks are rejected."""
    if isinstance(value,Enum):
        return value.value
    if isinstance(value,UUID):
        return str(value)
    if isinstance(value,(date,datetime)):
        if isinstance(value,datetime) and value.utcoffset() is None:
            raise ValueError('Snapshot timestamps require timezone')
        return value.isoformat()
    if is_dataclass(value) and not isinstance(value,type):
        module=type(value).__module__.removeprefix('YSH.')
        if type(value) not in _TYPED and module not in _FACT_MODULES:
            raise ValueError('Object is not a supported calculation fact')
        return {f.name:primitive(getattr(value,f.name)) for f in fields(value)}
    if isinstance(value,dict):
        if not all(type(key) is str for key in value):
            raise ValueError('Snapshot keys must be strings')
        return {key:primitive(item) for key,item in value.items()}
    if isinstance(value,(list,tuple)):
        return [primitive(item) for item in value]
    if value is None or type(value) in (str,int,bool):
        return value
    if type(value) is float and math.isfinite(value):
        return value
    raise ValueError('Unsupported/nonfinite snapshot value')


def canonical(value: object) -> str:
    """Keep raw JSON numbers, neutral units and stable key ordering."""
    return json.dumps(primitive(value),ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)


def decode(target: object, value: object) -> object:
    """Restore only the small typed explanation/context graph, never import payload types."""
    origin,args=get_origin(target),get_args(target)
    if origin is UnionType:
        if value is None and type(None) in args: return None
        for option in args:
            if option is type(None): continue
            try: return decode(option,value)
            except (ValueError,TypeError): pass
        raise ValueError('Invalid snapshot union')
    if origin is tuple:
        if not isinstance(value,list): raise ValueError('Expected snapshot array')
        return tuple(decode(args[0],item) for item in value)
    if target is UUID:
        return UUID(value)
    if target in (date,datetime):
        result=target.fromisoformat(value)
        if target is datetime and result.utcoffset() is None: raise ValueError('Naive snapshot timestamp')
        return result
    if isinstance(target,type) and issubclass(target,Enum): return target(value)
    if target in _TYPED:
        if not isinstance(value,dict): raise ValueError('Expected snapshot object')
        hints=get_type_hints(target)
        if set(value)-{f.name for f in fields(target)}: raise ValueError('Unknown versioned snapshot field')
        return target(**{f.name:decode(hints[f.name],value[f.name]) for f in fields(target) if f.name in value})
    if target is float and type(value) in (float,int) and math.isfinite(value): return value
    if type(value) is target: return value
    raise ValueError('Invalid snapshot primitive')
