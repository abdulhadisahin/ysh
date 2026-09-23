"""Calculation-first service for pump discharge head loss."""
from __future__ import annotations
from uuid import UUID
from core.local_loss_item import LocalLossItem
from engineering.head_loss.calculator import DischargeHeadLossCalculator
from engineering.head_loss.models import DischargeHeadLossInput,DischargeHeadLossResult
from engineering.validation import ValidationError, ValidationIssue
class DischargeHeadLossService:
    """Coordinates material roughness with the pure Darcy calculator."""
    def __init__(self,materials:object,calculator:DischargeHeadLossCalculator|None=None)->None:self._materials=materials;self._calculator=calculator or DischargeHeadLossCalculator()
    def calculate(self,inside_diameter_mm:float,flow_rate_m3h:float,kinematic_viscosity_m2s:float,pipe_length_m:float,roughness_mm:float|None,geodetic_head_m:float,local_loss_items:list[LocalLossItem],material_id:UUID|None=None)->DischargeHeadLossResult:
        """Calculate with manual roughness or a selected library material."""
        if material_id is not None:
            material=self._materials.get_material(material_id)
            if material.roughness_mm is None:raise ValidationError(ValidationIssue("material_roughness_missing"))
            roughness_mm=material.roughness_mm
        if roughness_mm is None:raise ValidationError(ValidationIssue("required","field.roughness"))
        result=self._calculator.calculate(DischargeHeadLossInput(inside_diameter_mm,flow_rate_m3h,kinematic_viscosity_m2s,pipe_length_m,roughness_mm,geodetic_head_m,local_loss_items));result.metadata["roughness_source"]="material" if material_id else "manual";return result
