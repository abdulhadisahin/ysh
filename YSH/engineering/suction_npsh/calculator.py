"""ENPY calculator composed with the validated head-loss engine."""
from __future__ import annotations
from engineering.head_loss.calculator import DischargeHeadLossCalculator
from engineering.head_loss.models import DischargeHeadLossInput
from engineering.suction_npsh.models import SuctionNPSHInput,SuctionNPSHResult
from engineering.validation import ValidationError, ValidationIssue
class SuctionNPSHCalculator:
    """Reuses canonical YSH losses then evaluates approved ENPY formula."""
    def calculate(self,value:SuctionNPSHInput)->SuctionNPSHResult:
        """Calculate ENPYm = PE/rho/g - Pb/rho/g - HEgeo - he."""
        self._validate_input(value)
        loss=DischargeHeadLossCalculator().calculate(DischargeHeadLossInput(value.inside_diameter_mm,value.flow_rate_m3h,value.kinematic_viscosity_m2s,value.pipe_length_m,value.roughness_mm,0,value.local_loss_items));g=9.80665;pe=value.suction_pressure_pa/(value.density_kg_m3*g);pb=value.vapour_pressure_pa/(value.density_kg_m3*g);enpy=pe-pb-value.static_suction_height_m-loss.total_hydraulic_loss_m;margin=None if value.npsh_required_m is None else enpy-value.npsh_required_m;warnings=list(loss.warnings)
        if enpy<0:warnings.append(ValidationIssue("negative_available_npsh"))
        if margin is not None and margin<0:warnings.append(ValidationIssue("npsh_below_required"))
        return SuctionNPSHResult(loss.total_hydraulic_loss_m,pe,pb,enpy,margin,[],warnings,{"formula":"ENPYm = PE/(rho*g) - Pb/(rho*g) - HEgeo - he","head_loss":loss})

    @staticmethod
    def _validate_input(value:SuctionNPSHInput)->None:
        """Validate ENPY-specific values without embedded presentation text."""
        import math
        checks=((value.suction_pressure_pa,"field.suction_pressure",False),(value.vapour_pressure_pa,"field.vapour_pressure",False),(value.density_kg_m3,"field.fluid_density",True),(value.static_suction_height_m,"field.static_suction_height",None))
        for number,field_key,positive in checks:
            if isinstance(number,bool) or not isinstance(number,(int,float)) or not math.isfinite(number):raise ValidationError(ValidationIssue("valid_number",field_key))
            if positive and number<=0:raise ValidationError(ValidationIssue("greater_than_zero",field_key))
            if positive is False and number<0:raise ValidationError(ValidationIssue("zero_or_greater",field_key))
        if value.npsh_required_m is not None and (isinstance(value.npsh_required_m,bool) or not isinstance(value.npsh_required_m,(int,float)) or not math.isfinite(value.npsh_required_m)):raise ValidationError(ValidationIssue("valid_number","field.npsh_required"))
