"""Service layer for suction loss and ENPY calculations."""
from __future__ import annotations
from uuid import UUID
from core.local_loss_item import LocalLossItem
from engineering.suction_npsh.calculator import SuctionNPSHCalculator
from engineering.suction_npsh.models import SuctionNPSHInput,SuctionNPSHResult
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
        nu=viscosity*1e-6 if viscosity_unit=="cSt" else viscosity
        result=DischargeHeadLossCalculator().calculate(DischargeHeadLossInput(d,q,nu,length,roughness,0,items))
        result.metadata["viscosity_m2s"]=nu
        return result
    def calculate_enpy(self,suction_loss_m:float,pe:float,pe_unit:str,pb:float,pb_unit:str,density:float,height:float,required:float|None=None)->SuctionNPSHResult:
        """Calculate ENPY from an already-valid suction-line loss result."""
        factors={"Pa":1,"kPa":1000,"bar":100000}
        if pe_unit not in factors or pb_unit not in factors:raise ValidationError(ValidationIssue("unsupported_pressure_unit"))
        self._validate_enpy_values(pe,pb,density,height,required)
        g=9.80665;pe_pa=pe*factors[pe_unit];pb_pa=pb*factors[pb_unit];pe_head=pe_pa/(density*g);pb_head=pb_pa/(density*g);enpy=pe_head-pb_head-height-suction_loss_m;margin=None if required is None else enpy-required;warnings=[]
        if enpy<0:warnings.append(ValidationIssue("negative_available_npsh"))
        if margin is not None and margin<0:warnings.append(ValidationIssue("npsh_below_required"))
        return SuctionNPSHResult(suction_loss_m,pe_head,pb_head,enpy,margin,[],warnings,{"formula":"ENPYm = PE/(rho*g) - Pb/(rho*g) - HEgeo - he","suction_pressure_pa":pe_pa,"vapour_pressure_pa":pb_pa})
    def calculate(self,d:float,q:float,viscosity:float,viscosity_unit:str,length:float,roughness:float|None,items:list[LocalLossItem],pe:float,pe_unit:str,pb:float,pb_unit:str,density:float,height:float,required:float|None=None,material_id:UUID|None=None)->SuctionNPSHResult:
        """Convert cSt/pressure values once and calculate ENPY."""
        if material_id is not None:
            material=self._materials.get_material(material_id);roughness=material.roughness_mm
            if roughness is None:raise ValidationError(ValidationIssue("material_roughness_missing"))
        if roughness is None:raise ValidationError(ValidationIssue("required","field.roughness"))
        nu=viscosity*1e-6 if viscosity_unit=="cSt" else viscosity
        factors={"Pa":1,"kPa":1000,"bar":100000}
        if pe_unit not in factors or pb_unit not in factors:raise ValidationError(ValidationIssue("unsupported_pressure_unit"))
        result=self._calculator.calculate(SuctionNPSHInput(d,q,nu,length,roughness,items,pe*factors[pe_unit],pb*factors[pb_unit],density,height,required));result.metadata.update({"viscosity_m2s":nu,"suction_pressure_pa":pe*factors[pe_unit],"vapour_pressure_pa":pb*factors[pb_unit]});return result

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
