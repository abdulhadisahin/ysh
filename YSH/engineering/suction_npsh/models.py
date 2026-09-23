"""Models for suction loss and NPSH available."""
from __future__ import annotations
from dataclasses import dataclass,field
from core.local_loss_item import LocalLossItem
from engineering.validation import ValidationIssue
@dataclass(slots=True)
class SuctionNPSHInput:
    """Inputs for validated suction losses and ENPY."""
    inside_diameter_mm:float;flow_rate_m3h:float;kinematic_viscosity_m2s:float;pipe_length_m:float;roughness_mm:float;local_loss_items:list[LocalLossItem];suction_pressure_pa:float;vapour_pressure_pa:float;density_kg_m3:float;static_suction_height_m:float;npsh_required_m:float|None=None
@dataclass(slots=True)
class SuctionNPSHResult:
    """Suction-line results, ENPY available, and semantic warnings."""
    suction_line_loss_m:float;suction_pressure_head_m:float;vapour_pressure_head_m:float;enpym_available_m:float;npsh_margin_m:float|None;messages:list[str]=field(default_factory=list);warnings:list[ValidationIssue]=field(default_factory=list);metadata:dict[str,object]=field(default_factory=dict)
