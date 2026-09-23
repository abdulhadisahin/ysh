"""Pure approved calculations for pipe diameter and wall thickness."""
from __future__ import annotations
import math
from collections.abc import Sequence
from core.pipe_size import PipeSize
from engineering.pipe_design.models import PipeDiameterInput,PipeDiameterResult,WallThicknessInput,WallThicknessResult
from engineering.pipe_design.validation import validate_diameter_input,validate_wall_input
class PipeDesignCalculator:
    """Executes formulas without database, service, or UI dependencies."""
    def calculate_diameter(self,value:PipeDiameterInput)->PipeDiameterResult:
        """Calculate D = sqrt(4Q/(V*pi)) using SI flow rate."""
        validate_diameter_input(value);flow_m3s=value.flow_rate_m3h/3600;diameter=math.sqrt((4*flow_m3s)/(value.design_velocity_mps*math.pi));return PipeDiameterResult(diameter,diameter*1000)
    def recommend_dn(self,result:PipeDiameterResult,pipe_sizes:Sequence[PipeSize])->PipeDiameterResult:
        """Recommend the first suitable distinct nominal DN.

        A DN can have many EN 10220 wall-thickness rows.  The row with the
        largest inside diameter represents the nominal size for this selection;
        actual wall selection remains a separate engineering decision.
        """
        representatives: dict[str, PipeSize] = {}
        for item in pipe_sizes:
            existing = representatives.get(item.nominal_diameter.casefold())
            if existing is None or item.inside_diameter_mm > existing.inside_diameter_mm:
                representatives[item.nominal_diameter.casefold()] = item
        ordered=sorted(representatives.values(),key=lambda item:item.outside_diameter_mm)
        if not ordered:
            result.warnings.append("pipe_size_library_empty")
            return result
        matching=[item for item in ordered if item.inside_diameter_mm>=result.diameter_mm]
        if not matching:
            result.warnings.append("no_suitable_dn")
            return result
        recommended=matching[0]
        result.minimum_matching_dn=recommended.nominal_diameter;result.recommended_dn=recommended.nominal_diameter;result.recommended_inside_diameter_mm=recommended.inside_diameter_mm;result.recommended_outside_diameter_mm=recommended.outside_diameter_mm;result.recommended_wall_thickness_mm=recommended.wall_thickness_mm
        return result
    def calculate_wall_thickness(self,value:WallThicknessInput)->WallThicknessResult:
        """Calculate approved allowable stress, base thickness, bend, and final thickness."""
        validate_wall_input(value);sigma=value.yield_strength_mpa/value.safety_factor;s0=(value.outside_diameter_mm*value.design_pressure_bar)/((20*sigma*value.weld_factor)+value.design_pressure_bar);bend=0.0 if not value.bend_allowance_enabled else .4*(value.outside_diameter_mm/value.bend_radius_mm)*s0
        return WallThicknessResult(sigma,s0,bend,value.corrosion_allowance_mm,s0+value.corrosion_allowance_mm+bend)
