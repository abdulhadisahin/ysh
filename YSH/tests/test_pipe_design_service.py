"""Tests for service-backed current-calculation defaults."""
from __future__ import annotations
from services.pipe_design_service import PipeDesignService
from engineering.pipe_design.models import PipeDiameterInput, WallThicknessInput

def test_current_constants_are_loaded_without_mutation(
    material_service: object,
    pipe_size_service: object,
    engineering_constant_service: object,
) -> None:
    """Saved constants are available for UI defaults and remain unchanged."""
    service = PipeDesignService(
        material_service,
        pipe_size_service,
        engineering_constant_service,
    )
    values = service.get_current_constants()
    assert values == {
        "safety_factor": 1.8,
        "design_pressure_bar": 16.0,
        "weld_factor": 1.0,
        "corrosion_allowance_mm": 1.0,
        "display_decimal_places": 6.0,
    }
    assert engineering_constant_service.get_constant("safety_factor").value == 1.8


def test_pipe_stages_calculate_independently(
    material_service: object,
    pipe_size_service: object,
    engineering_constant_service: object,
) -> None:
    """Allow diameter and wall calculations without unrelated stage inputs."""
    service = PipeDesignService(material_service, pipe_size_service, engineering_constant_service)

    diameter = service.calculate(diameter=PipeDiameterInput(100.0, 2.0))
    wall = service.calculate(
        wall=WallThicknessInput(273.05, 16.0, 190.0, 1.8, 1.0, 1.0)
    )

    assert diameter.is_successful and diameter.diameter is not None
    assert diameter.wall_thickness is None
    assert wall.is_successful and wall.wall_thickness is not None
    assert wall.diameter is None
