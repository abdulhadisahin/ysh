"""Engineering data contracts. No SQL, Tk, or hydraulic calculation dependencies."""
from dataclasses import dataclass,field,asdict
from datetime import datetime,timezone
from uuid import UUID,uuid4
import math

METHODS=('SOURCE_NOMINAL','SOURCE_RECOMMENDED','DERIVED_MIDPOINT','ENGINEERING_DEFAULT','USER_DEFINED','SOURCE_REQUIRED')
VERIFICATIONS=('VERIFIED','LIMITED_APPLICABILITY','RECOMMENDATION','SOURCE_REQUIRED')
NATURES=('RECOMMENDED_RANGE','RECOMMENDED_MAX','HARD_LIMIT','D243_CRITERION','SOURCE_REQUIRED')

def now(): return datetime.now(timezone.utc)
def numeric(*values):
    if any(v is not None and (isinstance(v,bool) or not isinstance(v,(float,int)) or not math.isfinite(v)) for v in values):
        raise ValueError('Engineering data must be finite')

@dataclass(frozen=True,kw_only=True)
class FluidSpecification:
    code:str
    fluid_id:UUID
    name:str
    fluid_group:str
    property_name:str
    unit:str
    source_min:float|None=None
    source_max:float|None=None
    source_nominal:float|None=None
    default_value:float|None=None
    default_method:str='SOURCE_REQUIRED'
    reference_temperature_c:float|None=None
    reference_salinity_g_kg:float|None=None
    source_authority:str=''
    source_document:str=''
    source_edition:str=''
    source_note:str=''
    verification:str='SOURCE_REQUIRED'
    is_factory:bool=False
    is_active:bool=True
    id:UUID=field(default_factory=uuid4)
    created_at:datetime=field(default_factory=now)
    modified_at:datetime=field(default_factory=now)
    def __post_init__(self):
        numeric(self.source_min,self.source_max,self.source_nominal,self.default_value,self.reference_temperature_c,self.reference_salinity_g_kg)
        if self.reference_salinity_g_kg is not None and self.reference_salinity_g_kg < 0:raise ValueError('Invalid salinity')
        if self.property_name in ('density','kinematic_viscosity') and any(v is not None and v<=0 for v in (self.source_min,self.source_max,self.source_nominal,self.default_value)):
            raise ValueError('Positive physical property required')
        if self.default_method not in METHODS or self.verification not in VERIFICATIONS: raise ValueError('Invalid property policy')
        if self.source_min is not None and self.source_max is not None and self.source_min>self.source_max:raise ValueError('Invalid range')
        if self.default_method=='DERIVED_MIDPOINT':
            if self.source_min is None or self.source_max is None or self.default_value is None or not math.isclose(self.default_value,(self.source_min+self.source_max)/2):
                raise ValueError('Midpoint requires both meaningful bounds and their midpoint')
        if self.default_method=='SOURCE_REQUIRED' and self.default_value is not None:raise ValueError('Unresolved property cannot provide a default')
        if self.default_method=='SOURCE_NOMINAL' and (self.default_value is None or self.source_nominal is None or self.default_value!=self.source_nominal):raise ValueError('Nominal default must match source')
    @property
    def value(self): return self.default_value
    @property
    def catalog_summary(self):
        return f'{self.name} / {self.property_name}: {self.default_value if self.default_value is not None else "SOURCE_REQUIRED"} {self.unit} @ {self.reference_temperature_c} °C'

@dataclass(frozen=True,kw_only=True)
class MaterialSurface:
    code:str
    name:str
    material_name:str
    surface_condition:str
    roughness_mm:float|None=None
    material_id:UUID|None=None
    source_authority:str=''
    source_document:str=''
    source_note:str=''
    verification:str='SOURCE_REQUIRED'
    is_factory:bool=False
    is_active:bool=True
    id:UUID=field(default_factory=uuid4)
    created_at:datetime=field(default_factory=now)
    modified_at:datetime=field(default_factory=now)
    def __post_init__(self):
        numeric(self.roughness_mm)
        if self.roughness_mm is not None and self.roughness_mm<0:raise ValueError('Negative absolute roughness')
        if self.verification not in VERIFICATIONS:raise ValueError('Invalid verification')
    @property
    def catalog_summary(self): return f'{self.name}: ε = {self.roughness_mm if self.roughness_mm is not None else "SOURCE_REQUIRED"} mm'

@dataclass(frozen=True,kw_only=True)
class EngineeringRule:
    code:str
    name:str
    profile_id:UUID
    system_family:str=''
    service:str=''
    fluid_group:str=''
    line_type:str=''
    material:str=''
    parameter:str='flow_velocity'
    rule_nature:str='SOURCE_REQUIRED'
    recommended_min:float|None=None
    recommended_max:float|None=None
    hard_min:float|None=None
    hard_max:float|None=None
    unit:str='m/s'
    yellow_fraction:float=.1
    critical_multiplier:float=5.
    source_authority:str=''
    source_document:str=''
    source_edition:str=''
    source_clause:str=''
    applicability:str=''
    verification:str='SOURCE_REQUIRED'
    notes:str=''
    is_factory:bool=False
    is_active:bool=True
    id:UUID=field(default_factory=uuid4)
    created_at:datetime=field(default_factory=now)
    modified_at:datetime=field(default_factory=now)
    def __post_init__(self):
        numeric(self.recommended_min,self.recommended_max,self.hard_min,self.hard_max,self.yellow_fraction,self.critical_multiplier)
        if self.rule_nature not in NATURES or self.verification not in VERIFICATIONS:raise ValueError('Invalid rule nature/verification')
        if not 0<=self.yellow_fraction<=1 or self.critical_multiplier<=1:raise ValueError('Invalid deviation policy')
        for lo,hi in ((self.recommended_min,self.recommended_max),(self.hard_min,self.hard_max)):
            if lo is not None and hi is not None and lo>hi:raise ValueError('Invalid rule bounds')
        limits=(self.hard_min,self.hard_max) if self.rule_nature=='HARD_LIMIT' else (self.recommended_min,self.recommended_max)
        if self.rule_nature!='SOURCE_REQUIRED' and all(v is None for v in limits):raise ValueError('Configured rule requires explicit bounds')
        if self.rule_nature=='RECOMMENDED_RANGE' and any(v is None for v in limits):raise ValueError('Recommended range needs both bounds')
        if self.rule_nature=='SOURCE_REQUIRED' and any(v is not None for v in (self.recommended_min,self.recommended_max,self.hard_min,self.hard_max)):
            raise ValueError('Source-required rule cannot invent numerical limits')
    @property
    def catalog_summary(self):
        bounds=(self.hard_min,self.hard_max) if self.rule_nature=='HARD_LIMIT' else (self.recommended_min,self.recommended_max)
        return f'{self.name}: {bounds[0]} … {bounds[1]} {self.unit} / {self.source_authority} / {self.applicability}'
