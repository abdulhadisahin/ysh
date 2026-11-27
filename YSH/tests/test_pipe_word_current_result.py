"""Pipe-design Word export stays enabled when the stress step carries a library material source."""
from engineering.formula.pipe import legacy_pipe_steps
from engineering.pipe_design.models import PipeDiameterInput, WallThicknessInput
from engineering.snapshots.builders import _pipe, pipe_material_source_steps
from services.pipe_design_service import PipeDesignService


def test_wall_snapshot_steps_match_page_formula_steps(material_service, pipe_size_service, engineering_constant_service):
    service = PipeDesignService(material_service, pipe_size_service, engineering_constant_service)
    diameter = service.calculate(diameter=PipeDiameterInput(34, 2.0), standard_code="EN 10220")
    material = material_service.get_all_materials()[0]
    wall = service.calculate(wall=WallThicknessInput(26.9, 10, None, 1.5, 1, 0, False, None), material_id=material.id)
    _, snapshot_steps, _ = _pipe("wall", wall, None)
    page_steps = legacy_pipe_steps(diameter) + pipe_material_source_steps(legacy_pipe_steps(wall), wall)
    assert all(step in page_steps for step in snapshot_steps)
    assert any(step.step_id == "pipe.stress" and len(step.sources) > 0 for step in snapshot_steps)
