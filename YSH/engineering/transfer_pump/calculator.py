"""Pure standard-library ordinary least-squares pump calculator."""
from __future__ import annotations
import math
from engineering.transfer_pump.models import LinearRegressionModel,TransferPumpInput,TransferPumpResult
from engineering.validation import ValidationIssue
class TransferPumpCalculator:
    """Calculates a linear pump-capacity estimate from reference ships."""
    def calculate(self,value:TransferPumpInput)->TransferPumpResult:
        """Fit y=a*x+b and estimate capacity and tank emptying time."""
        refs=value.reference_records
        if len(refs)<2:return TransferPumpResult(errors=[ValidationIssue("insufficient_reference_ships")])
        x=[item.fuel_capacity_m3 for item in refs];y=[item.pump_capacity_m3h for item in refs]
        if not isinstance(value.new_ship_fuel_capacity_m3, (int, float)) or isinstance(value.new_ship_fuel_capacity_m3, bool) or not math.isfinite(value.new_ship_fuel_capacity_m3):return TransferPumpResult(errors=[ValidationIssue("valid_number", "field.fuel_capacity")])
        if value.new_ship_fuel_capacity_m3<=0:return TransferPumpResult(errors=[ValidationIssue("greater_than_zero", "field.fuel_capacity")])
        if not all(isinstance(n, (int, float)) and not isinstance(n, bool) and math.isfinite(n) and n>0 for n in [*x,*y]):return TransferPumpResult(errors=[ValidationIssue("invalid_reference_ship_data")])
        xm=sum(x)/len(x);ym=sum(y)/len(y);den=sum((n-xm)**2 for n in x)
        if den==0:return TransferPumpResult(errors=[ValidationIssue("identical_reference_capacities")])
        slope=sum((a-xm)*(b-ym) for a,b in zip(x,y))/den;intercept=ym-slope*xm;predicted=slope*value.new_ship_fuel_capacity_m3+intercept
        if predicted<=0:return TransferPumpResult(errors=[ValidationIssue("non_positive_predicted_pump_capacity")])
        fitted=[slope*n+intercept for n in x];ss_res=sum((actual-fit)**2 for actual,fit in zip(y,fitted));ss_tot=sum((actual-ym)**2 for actual in y);r2=1.0 if ss_tot==0 and ss_res==0 else 1-(ss_res/ss_tot)
        model=LinearRegressionModel(slope,intercept,r2,len(refs),min(x),max(x));warnings=[]
        if not model.minimum_reference_capacity_m3<=value.new_ship_fuel_capacity_m3<=model.maximum_reference_capacity_m3:warnings.append(ValidationIssue("estimate_extrapolation"))
        hours=value.new_ship_fuel_capacity_m3/predicted
        return TransferPumpResult(predicted,hours,hours*60,model,[],warnings,{"module_identifier":"transfer_pump","reference_count":len(refs),"formulas":"y = a*x + b; t = fuel_capacity / pump_capacity"})
