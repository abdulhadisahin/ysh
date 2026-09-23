"""Pure canonical SI Darcy-Weisbach discharge-loss calculations."""
from __future__ import annotations
import math
from engineering.head_loss.friction_factor import turbulent_friction_factor
from engineering.head_loss.models import DischargeHeadLossInput,DischargeHeadLossResult
from engineering.validation import ValidationError, ValidationIssue
class DischargeHeadLossCalculator:
    """Calculates velocity, Darcy friction, losses, and system head."""
    def calculate(self,value:DischargeHeadLossInput)->DischargeHeadLossResult:
        """Perform SI unit conversion and canonical Darcy-Weisbach equations."""
        self._validate_input(value)
        d=value.inside_diameter_mm/1000;q=value.flow_rate_m3h/3600;k=value.roughness_mm/1000;area=math.pi*d*d/4;velocity=q/area;reynolds=velocity*d/value.kinematic_viscosity_m2s;relative=k/d;warnings=[]
        if reynolds<2300:factor=64/reynolds;regime="Laminar"
        else:
            try:turbulent=turbulent_friction_factor(reynolds,relative)
            except ValueError as error:raise ValidationError(ValidationIssue("friction_factor_unavailable")) from error
            if reynolds<4000:
                laminar=64/reynolds;factor=laminar+(turbulent-laminar)*((reynolds-2300)/1700);regime="Transitional";warnings.append(ValidationIssue("transitional_flow_regime"))
            else:factor=turbulent;regime="Turbulent"
        dynamic=velocity*velocity/(2*9.80665);total_k=sum(item.subtotal_k for item in value.local_loss_items);pipe=6.4e6*factor*value.pipe_length_m*value.flow_rate_m3h**2/value.inside_diameter_mm**5;local=6400*total_k*value.flow_rate_m3h**2/value.inside_diameter_mm**4;total=pipe+local
        legacy_pipe=6.4e6*factor*value.pipe_length_m*value.flow_rate_m3h**2/value.inside_diameter_mm**5
        derived_local=6377.707*total_k*value.flow_rate_m3h**2/value.inside_diameter_mm**4
        recorded_local=6400*total_k*value.flow_rate_m3h**2/value.inside_diameter_mm**5
        warnings.append(ValidationIssue("excel_local_loss_unresolved"))
        return DischargeHeadLossResult(velocity,reynolds,relative,regime,factor,pipe,total_k,local,total,value.geodetic_head_m+total,[],warnings,{"formula":"YSH coefficient forms","audit":{"si_dynamic_pipe_m":factor*(value.pipe_length_m/d)*dynamic,"coefficient_pipe_m":pipe,"coefficient_d4_local_m":local,"derived_d4_local_m":derived_local,"recorded_d5_local_m":recorded_local}})

    @staticmethod
    def _validate_input(value:DischargeHeadLossInput)->None:
        """Raise stable field-specific issues before any hydraulic formula runs."""
        checks=((value.inside_diameter_mm,"field.pipe_inside_diameter",True),(value.flow_rate_m3h,"field.flow_rate",True),(value.kinematic_viscosity_m2s,"field.kinematic_viscosity",True),(value.pipe_length_m,"field.pipe_length",False),(value.roughness_mm,"field.roughness",False),(value.geodetic_head_m,"field.geodetic_head",None))
        for number,field_key,positive in checks:
            if isinstance(number,bool) or not isinstance(number,(int,float)) or not math.isfinite(number):raise ValidationError(ValidationIssue("valid_number",field_key))
            if positive is True and number<=0:raise ValidationError(ValidationIssue("greater_than_zero",field_key))
            if positive is False and number<0:raise ValidationError(ValidationIssue("zero_or_greater",field_key))
