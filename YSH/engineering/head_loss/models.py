"""Input and result models for SI Darcy-Weisbach head loss."""
from __future__ import annotations
from dataclasses import dataclass,field
from core.local_loss_item import LocalLossItem
from engineering.validation import ValidationIssue
@dataclass(slots=True)
class DischargeHeadLossInput:
    """Pipe, fluid, elevation, and local-loss input values."""
    inside_diameter_mm:float;flow_rate_m3h:float;kinematic_viscosity_m2s:float;pipe_length_m:float;roughness_mm:float;geodetic_head_m:float;local_loss_items:list[LocalLossItem]=field(default_factory=list)
@dataclass(slots=True)
class DischargeHeadLossResult:
    """Full-precision outputs with semantic warnings for presentation clients."""
    flow_velocity_m_s:float;reynolds_number:float;relative_roughness:float;flow_regime:str;friction_factor:float;pipe_friction_loss_m:float;local_loss_coefficient_total:float;local_loss_m:float;total_hydraulic_loss_m:float;system_head_m:float;messages:list[str]=field(default_factory=list);warnings:list[ValidationIssue]=field(default_factory=list);metadata:dict[str,object]=field(default_factory=dict)
