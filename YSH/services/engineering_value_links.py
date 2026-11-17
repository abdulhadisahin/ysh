"""Applied reference/used-value state. Project defaults never change implicitly."""
from dataclasses import dataclass,replace,asdict
from copy import deepcopy
import math

@dataclass(frozen=True)
class EngineeringValueLink:
    reference:dict
    used_value:float|None
    pending:dict|None=None
    kept_current:bool=False
    source_missing:bool=False
    def __post_init__(self):
        if self.used_value is not None and (isinstance(self.used_value,bool) or not math.isfinite(self.used_value)):
            raise ValueError('Invalid used engineering value')
        object.__setattr__(self,'reference',deepcopy(self.reference))
        object.__setattr__(self,'pending',deepcopy(self.pending))
    @property
    def overridden(self):
        default=self.reference.get('default_value')
        return default is not None and self.used_value is not None and self.used_value!=default
    @property
    def stale(self):return self.pending is not None or self.source_missing
    @property
    def status(self):
        if self.stale:return 'STALE'
        if self.reference.get('default_value') is None:return 'SOURCE_REQUIRED'
        return 'OVERRIDE' if self.overridden else 'LINKED'
    def observe(self,reference):
        return replace(self,pending=reference if reference is not None and reference!=self.reference else None,
                       source_missing=reference is None,kept_current=False)
    def edit(self,value):return replace(self,used_value=value)
    def update(self):
        if self.pending is None:return self
        reference=self.pending
        used=self.used_value if self.overridden or reference.get('default_value') is None else reference['default_value']
        return EngineeringValueLink(reference,used)
    def keep(self):return replace(self,kept_current=True)
    def use_reference(self):
        if self.source_missing:raise ValueError('Reference no longer available')
        row=self.pending or self.reference
        if row.get('default_value') is None:raise ValueError('Source required')
        return EngineeringValueLink(row,row['default_value'])
    def payload(self):return deepcopy(asdict(self))
    @classmethod
    def from_payload(cls,payload):return cls(**deepcopy(payload))

def bind(reference,existing=None):
    return EngineeringValueLink(reference,reference.get('default_value') if existing is None else existing)
