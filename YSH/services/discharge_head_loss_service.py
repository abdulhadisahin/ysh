"""Calculation-first service for pump discharge head loss."""
from __future__ import annotations
from uuid import UUID
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from engineering.pipe_design.transfer import PipeInputState
    from engineering.head_loss.v2_models import DischargeV2Input, DischargeV2Result
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

    def calculate_with_pipe(
        self, pipe_input: PipeInputState, *, kinematic_viscosity_m2s: float,
        pipe_length_m: float, roughness_mm: float | None, geodetic_head_m: float,
        local_loss_items: list[LocalLossItem], material_id: UUID | None = None,
    ) -> DischargeHeadLossResult:
        """Consume applied/manual Di and Q only; material roughness stays explicit."""
        diameter, flow = pipe_input.used_values.hydraulic_values()
        result = self.calculate(diameter, flow, kinematic_viscosity_m2s, pipe_length_m,
                                roughness_mm, geodetic_head_m, local_loss_items, material_id)
        result.metadata["pipe_transfer"] = pipe_input.trace()
        return result

    def calculate_v2(self, value: DischargeV2Input) -> DischargeV2Result:
        """Validate/calculate applied inputs through the authoritative shared path."""
        from dataclasses import fields, replace
        from engineering.head_loss.v2_models import DischargeV2Result
        roughness = value.roughness_mm
        if value.material_id is not None:
            roughness = self._materials.get_material(value.material_id).roughness_mm
            if roughness is None:
                raise ValidationError(ValidationIssue("material_roughness_missing"))
        result = self.calculate_with_pipe(
            value.pipe_input, kinematic_viscosity_m2s=value.kinematic_viscosity_m2s,
            pipe_length_m=value.pipe_length_m, roughness_mm=roughness,
            geodetic_head_m=value.geodetic_head_m,
            local_loss_items=[item.to_item() for item in value.local_losses],
            material_id=None,
        )
        used = replace(value, roughness_mm=roughness)
        result.metadata["roughness_source"] = "material" if value.material_id else "manual"
        diameter, flow = value.pipe_input.used_values.hydraulic_values()
        return DischargeV2Result(
            **{field.name: getattr(result, field.name) for field in fields(result)},
            input=used, flow_rate_m3_h=flow, actual_internal_diameter_mm=diameter,
            geodetic_head_m=value.geodetic_head_m,
        )
