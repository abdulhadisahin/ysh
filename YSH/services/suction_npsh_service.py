"""Service layer for suction loss and ENPY calculations."""
from __future__ import annotations
from uuid import UUID
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from engineering.pipe_design.transfer import PipeInputState
    from engineering.suction_npsh.v2_models import ENPYV2Input, SuctionV2Input, SuctionV2LossResult, SuctionV2Result
from core.local_loss_item import LocalLossItem
from engineering.suction_npsh.calculator import SuctionNPSHCalculator
from engineering.suction_npsh.models import ENPYInput,SuctionNPSHInput,SuctionNPSHResult
from engineering.units import convert_pressure, convert_kinematic_viscosity
from engineering.head_loss.calculator import DischargeHeadLossCalculator
from engineering.head_loss.models import DischargeHeadLossInput,DischargeHeadLossResult
from engineering.validation import ValidationError, ValidationIssue
class SuctionNPSHService:
    """Converts user units and delegates to the pure suction calculator."""
    def __init__(self,materials:object)->None:self._materials=materials;self._calculator=SuctionNPSHCalculator()
    def calculate_suction_loss(self,d:float,q:float,viscosity:float,viscosity_unit:str,length:float,roughness:float|None,items:list[LocalLossItem],material_id:UUID|None=None)->DischargeHeadLossResult:
        """Calculate only suction-line hydraulics without ENPY inputs."""
        if material_id is not None:
            roughness=self._materials.get_material(material_id).roughness_mm
            if roughness is None:raise ValidationError(ValidationIssue("material_roughness_missing"))
        if roughness is None:raise ValidationError(ValidationIssue("required","field.roughness"))
        nu=self._viscosity_m2s(viscosity,viscosity_unit)
        result=DischargeHeadLossCalculator().calculate(DischargeHeadLossInput(d,q,nu,length,roughness,0,items))
        result.metadata["viscosity_m2s"]=nu
        return result
    def calculate_enpy(self,suction_loss_m:float,pe:float,pe_unit:str,pb:float,pb_unit:str,density:float,height:float,required:float|None=None)->SuctionNPSHResult:
        """Calculate ENPY from an already-valid suction-line loss result."""
        self._validate_pressure_units(pe_unit,pb_unit)
        self._validate_enpy_values(pe,pb,density,height,required)
        pe_pa,pb_pa=self._pressures_pa(pe,pe_unit,pb,pb_unit)
        result=self._calculator.calculate_enpy(ENPYInput(suction_loss_m,pe_pa,pb_pa,density,height,required))
        result.metadata.update({"suction_pressure_pa":pe_pa,"vapour_pressure_pa":pb_pa})
        return result
    def calculate(self,d:float,q:float,viscosity:float,viscosity_unit:str,length:float,roughness:float|None,items:list[LocalLossItem],pe:float,pe_unit:str,pb:float,pb_unit:str,density:float,height:float,required:float|None=None,material_id:UUID|None=None)->SuctionNPSHResult:
        """Convert cSt/pressure values once and calculate ENPY."""
        if material_id is not None:
            material=self._materials.get_material(material_id);roughness=material.roughness_mm
            if roughness is None:raise ValidationError(ValidationIssue("material_roughness_missing"))
        if roughness is None:raise ValidationError(ValidationIssue("required","field.roughness"))
        nu=self._viscosity_m2s(viscosity,viscosity_unit)
        pe_pa,pb_pa=self._pressures_pa(pe,pe_unit,pb,pb_unit)
        result=self._calculator.calculate(SuctionNPSHInput(d,q,nu,length,roughness,items,pe_pa,pb_pa,density,height,required));result.metadata.update({"viscosity_m2s":nu,"suction_pressure_pa":pe_pa,"vapour_pressure_pa":pb_pa});return result

    @staticmethod
    def _viscosity_m2s(viscosity:float,unit:str)->float:
        """Reuse the shared factor while preserving legacy unit/validation behavior."""
        return viscosity*convert_kinematic_viscosity(1.0,"cSt","m²/s") if unit=="cSt" else viscosity

    @staticmethod
    def _validate_pressure_units(pe_unit:str,pb_unit:str)->None:
        # Keep the existing exact service unit set; do not enable new modes/aliases.
        if pe_unit not in ("Pa","kPa","bar") or pb_unit not in ("Pa","kPa","bar"):
            raise ValidationError(ValidationIssue("unsupported_pressure_unit"))

    @classmethod
    def _pressures_pa(cls,pe:float,pe_unit:str,pb:float,pb_unit:str)->tuple[float,float]:
        """Use shared unit factors, retaining the original multiplication order.

        Converting the factors rather than raw values retains field-specific
        validation and error order at the established service/calculator boundary.
        """
        cls._validate_pressure_units(pe_unit,pb_unit)
        return pe*int(convert_pressure(1.0,pe_unit,"Pa")),pb*int(convert_pressure(1.0,pb_unit,"Pa"))

    @staticmethod
    def _validate_enpy_values(pe:float,pb:float,density:float,height:float,required:float|None)->None:
        """Validate service-level ENPY values with stable field keys."""
        import math
        checks=((pe,"field.suction_pressure",False),(pb,"field.vapour_pressure",False),(density,"field.fluid_density",True),(height,"field.static_suction_height",None))
        for number,field_key,positive in checks:
            if isinstance(number,bool) or not isinstance(number,(int,float)) or not math.isfinite(number):raise ValidationError(ValidationIssue("valid_number",field_key))
            if positive and number<=0:raise ValidationError(ValidationIssue("greater_than_zero",field_key))
            if positive is False and number<0:raise ValidationError(ValidationIssue("zero_or_greater",field_key))
        if required is not None and (isinstance(required,bool) or not isinstance(required,(int,float)) or not math.isfinite(required)):raise ValidationError(ValidationIssue("valid_number","field.npsh_required"))

    def calculate_suction_loss_with_pipe(
        self, pipe_input: PipeInputState, *, viscosity: float, viscosity_unit: str,
        length: float, roughness: float | None, items: list[LocalLossItem],
        material_id: UUID | None = None,
    ) -> DischargeHeadLossResult:
        """Calculate suction hydraulics from applied values without reading a source."""
        diameter, flow = pipe_input.used_values.hydraulic_values()
        result = self.calculate_suction_loss(diameter, flow, viscosity, viscosity_unit,
                                            length, roughness, items, material_id)
        result.metadata["pipe_transfer"] = pipe_input.trace()
        return result

    def calculate_with_pipe(
        self, pipe_input: PipeInputState, *, viscosity: float, viscosity_unit: str,
        length: float, roughness: float | None, items: list[LocalLossItem],
        pe: float, pe_unit: str, pb: float, pb_unit: str, density: float,
        height: float, required: float | None = None, material_id: UUID | None = None,
    ) -> SuctionNPSHResult:
        """Consume the applied snapshot while retaining existing ENPY mathematics."""
        diameter, flow = pipe_input.used_values.hydraulic_values()
        result = self.calculate(diameter, flow, viscosity, viscosity_unit, length,
            roughness, items, pe, pe_unit, pb, pb_unit, density, height, required, material_id)
        result.metadata["pipe_transfer"] = pipe_input.trace()
        return result

    def calculate_suction_loss_v2(self, value: SuctionV2Input) -> SuctionV2LossResult:
        """Validate and delegate actual applied Q/Di to the shared hydraulic service."""
        from dataclasses import fields, replace
        from engineering.suction_npsh.v2_models import SuctionV2LossResult
        roughness = value.roughness_mm
        used_material = None
        if value.material_id is not None:
            material = self._materials.get_material(value.material_id)
            roughness = material.roughness_mm
            used_material = {"id":str(value.material_id),"designation":getattr(material,"designation",None),
                             "standard":getattr(material,"standard",None),"source":getattr(material,"source",None),"roughness_mm":roughness}
            if roughness is None:
                raise ValidationError(ValidationIssue("material_roughness_missing"))
        result = self.calculate_suction_loss_with_pipe(
            value.pipe_input, viscosity=value.viscosity, viscosity_unit=value.viscosity_unit,
            length=value.pipe_length_m, roughness=roughness,
            items=[item.to_item() for item in value.local_losses],
        )
        result.metadata["roughness_source"] = "material" if value.material_id else "manual"
        if used_material is not None:
            result.metadata["used_material"] = used_material
        diameter, flow = value.pipe_input.used_values.hydraulic_values()
        return SuctionV2LossResult(
            **{field.name: getattr(result, field.name) for field in fields(result)},
            input=replace(value, roughness_mm=roughness),
            actual_internal_diameter_mm=diameter, flow_rate_m3_h=flow,
        )

    def calculate_enpy_v2(self, loss: SuctionV2LossResult, value: ENPYV2Input) -> SuctionV2Result:
        """Reuse the sole ENPY arithmetic implementation without recalculating hydraulics."""
        from dataclasses import fields
        from engineering.suction_npsh.v2_models import SuctionV2Result
        result = self.calculate_enpy(
            loss.total_hydraulic_loss_m, value.suction_pressure, value.suction_pressure_unit,
            value.vapour_pressure, value.vapour_pressure_unit, value.density_kg_m3,
            value.static_suction_height_m, value.npsh_required_m,
        )
        result.metadata["head_loss"] = loss
        result.metadata["pipe_transfer"] = loss.input.pipe_input.trace()
        return SuctionV2Result(
            **{field.name: getattr(result, field.name) for field in fields(result)},
            hydraulic=loss, input=value,
        )

    def calculate_v2(self, pipe: SuctionV2Input, enpy: ENPYV2Input) -> SuctionV2Result:
        """Compose the two explicit stages; no duplicated hydraulic or ENPY equations."""
        loss = self.calculate_suction_loss_v2(pipe)
        result = self.calculate_enpy_v2(loss, enpy)
        result.warnings[:0] = loss.warnings
        return result
