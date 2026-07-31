"""Tests for materials across model, repository, and service layers."""
from __future__ import annotations
import pytest
from core.material import Material
from services.material_service import MaterialConflictError, MaterialValidationError, MaterialService

def test_material_serialization_round_trip() -> None:
    """A material serializes without losing nullable values."""
    item=Material(name="ST37",designation="ST37",yield_strength_mpa=None,roughness_mm=.045)
    assert Material.from_dict(item.to_dict()).to_dict()==item.to_dict()
def test_materials_seed_only_empty_library(material_service:MaterialService)->None:
    """Initial materials are seeded once and not duplicated."""
    assert len(material_service.get_all_materials())==4
def test_material_crud(material_service:MaterialService)->None:
    """A user material can be stored, updated, and deleted."""
    item=material_service.create_material(name="Carbon Steel",designation="CS",yield_strength_mpa=250,roughness_mm=.045)
    item.name="Updated";material_service.update_material(item);assert material_service.get_material(item.id).name=="Updated";material_service.delete_material(item.id)
    with pytest.raises(LookupError):material_service.get_material(item.id)
def test_duplicate_designation_is_case_insensitive(material_service:MaterialService)->None:
    """Case variants of a designation conflict."""
    with pytest.raises(MaterialConflictError):material_service.create_material(name="Another",designation="aisi 304l",yield_strength_mpa=200,roughness_mm=.01)
@pytest.mark.parametrize(("strength","roughness"),[(0,.01),(-1,.01),(200,-.01)])
def test_material_numeric_validation(material_service:MaterialService,strength:float,roughness:float)->None:
    """Invalid material numeric values are rejected."""
    with pytest.raises(MaterialValidationError):material_service.create_material(name="X",designation=f"X{strength}{roughness}",yield_strength_mpa=strength,roughness_mm=roughness)
def test_material_missing_property_detection(material_service:MaterialService)->None:
    """Materials without verified values cannot satisfy required-property use."""
    with pytest.raises(MaterialValidationError,match="verified"):material_service.validate_required_properties(material_service.get_all_materials()[2],"yield_strength_mpa")
