"""Tests for the pipe-size model, repository, and service."""
from __future__ import annotations
import pytest
from core.pipe_size import PipeSize
from services.pipe_size_service import PipeSizeConflictError, PipeSizeService, PipeSizeValidationError
def test_pipe_size_serialization() -> None:
    """Pipe-size data round trips through a dictionary."""
    item=PipeSize("DN50",60.3,3.2,53.9,"EN")
    assert PipeSize.from_dict(item.to_dict()).to_dict()==item.to_dict()
def test_pipe_library_starts_empty(pipe_size_service:PipeSizeService)->None:
    """No unverified DN data is inserted."""
    assert pipe_size_service.get_all_pipe_sizes()==()
def test_pipe_size_crud(pipe_size_service:PipeSizeService)->None:
    """Pipe sizes persist and can be updated/deleted."""
    item=pipe_size_service.create_pipe_size(nominal_diameter="DN50",outside_diameter_mm=60.3,wall_thickness_mm=3.2,inside_diameter_mm=53.9,standard="EN")
    item.description="verified";pipe_size_service.update_pipe_size(item);assert pipe_size_service.get_pipe_size(item.id).description=="verified";pipe_size_service.delete_pipe_size(item.id)
def test_pipe_size_duplicate_and_geometry(pipe_size_service:PipeSizeService)->None:
    """Natural key and dimensional relationship are enforced."""
    pipe_size_service.create_pipe_size(nominal_diameter="DN50",outside_diameter_mm=60.3,wall_thickness_mm=3.2,inside_diameter_mm=53.9,standard="EN")
    with pytest.raises(PipeSizeConflictError):pipe_size_service.create_pipe_size(nominal_diameter="dn50",outside_diameter_mm=60.3,wall_thickness_mm=3.2,inside_diameter_mm=53.9,standard="en")
    with pytest.raises(PipeSizeValidationError):pipe_size_service.create_pipe_size(nominal_diameter="DN1",outside_diameter_mm=10,wall_thickness_mm=2,inside_diameter_mm=7,standard="X")
@pytest.mark.parametrize("outer,wall,inner",[(0,1,1),(10,1,10),(10,0,10)])
def test_pipe_dimensions_must_be_positive_and_consistent(pipe_size_service:PipeSizeService,outer:float,wall:float,inner:float)->None:
    """Invalid dimensions are rejected."""
    with pytest.raises(PipeSizeValidationError):pipe_size_service.create_pipe_size(nominal_diameter=f"DN{outer}{wall}",outside_diameter_mm=outer,wall_thickness_mm=wall,inside_diameter_mm=inner)
