"""Service workflow for the Version 1 pipe-design module."""
from __future__ import annotations
from uuid import UUID
from collections.abc import Sequence
from core.material import Material
from engineering.pipe_design.calculator import PipeDesignCalculator
from engineering.pipe_design.models import PipeDesignCalculationResult, PipeDiameterInput, WallThicknessInput
from services.engineering_constant_service import EngineeringConstantService
from services.material_service import MaterialService
from services.pipe_size_service import PipeSizeService
from engineering.validation import ValidationError
class PipeDesignService:
    """Coordinates library values with pure pipe calculations."""
    def __init__(self, materials: MaterialService, pipe_sizes: PipeSizeService, constants: EngineeringConstantService) -> None:
        """Configure dependencies without accessing SQL or Tkinter."""
        self._materials=materials;self._pipe_sizes=pipe_sizes;self._constants=constants;self._calculator=PipeDesignCalculator()
    def get_current_constants(self) -> dict[str, float]:
        """Return required saved constants for a new calculation page."""
        required = (
            "safety_factor",
            "design_pressure_bar",
            "weld_factor",
            "corrosion_allowance_mm",
            "display_decimal_places",
        )
        values: dict[str, float] = {}
        for key in required:
            try:
                values[key] = self._constants.get_constant(key).value
            except LookupError as error:
                raise ValueError(
                    f"Required engineering constant '{key}' is missing."
                ) from error
        return values
    def get_all_materials(self) -> Sequence[Material]:
        """Return library materials for the wall-thickness source selector."""
        return self._materials.get_all_materials()
    def get_material(self, material_id: UUID) -> Material:
        """Return a full material record for current-calculation use."""
        return self._materials.get_material(material_id)
    def calculate(self, diameter: PipeDiameterInput|None=None, wall: WallThicknessInput|None=None, material_id: UUID|None=None, manual_input: bool=True) -> PipeDesignCalculationResult:
        """Calculate provided sections while retaining errors and traceability."""
        result=PipeDesignCalculationResult(trace={"module_identifier":"pipe_design","module_version":"1","manual_input":manual_input,"constants":self.get_current_constants()})
        try:
            if material_id is not None and wall is not None:
                material=self._materials.get_material(material_id);self._materials.validate_required_properties(material,"yield_strength_mpa");wall.yield_strength_mpa=material.yield_strength_mpa;result.trace["material"]={"id":str(material.id),"designation":material.designation}
            if diameter is not None:
                result.diameter=self._calculator.recommend_dn(self._calculator.calculate_diameter(diameter),self._pipe_sizes.get_all_pipe_sizes());result.warnings.extend(result.diameter.warnings)
            if wall is not None:result.wall_thickness=self._calculator.calculate_wall_thickness(wall)
        except ValidationError:
            raise
        except (ValueError, LookupError):
            result.errors.append("unexpected_error")
        return result
