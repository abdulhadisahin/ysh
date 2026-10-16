"""Service layer for suction loss and ENPY calculations."""
from __future__ import annotations
from uuid import UUID
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from engineering.pipe_design.transfer import PipeInputState
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
