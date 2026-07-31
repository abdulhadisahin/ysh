"""Tests for engineering constants across the library layers."""
from __future__ import annotations
import pytest
from core.engineering_constant import EngineeringConstant
from services.engineering_constant_service import EngineeringConstantConflictError, EngineeringConstantService, EngineeringConstantValidationError
def test_constant_serialization() -> None:
    """Constants retain values after serialization."""
    item=EngineeringConstant("factor","Factor",1.25)
    assert EngineeringConstant.from_dict(item.to_dict()).to_dict()==item.to_dict()
def test_constants_seed(engineering_constant_service:EngineeringConstantService)->None:
    """All verified Version 1 defaults are created once."""
    assert len(engineering_constant_service.get_all_constants())==5
def test_constants_are_editable(engineering_constant_service:EngineeringConstantService)->None:
    """Seeded constants can be changed and persist."""
    item=engineering_constant_service.get_constant("safety_factor");item.value=2.0;engineering_constant_service.update_constant(item);assert engineering_constant_service.get_constant("safety_factor").value==2.0
def test_constant_crud_and_unique_key(engineering_constant_service:EngineeringConstantService)->None:
    """User constants support CRUD and case-insensitive uniqueness."""
    item=engineering_constant_service.create_constant(key="custom",display_name="Custom",value=4)
    with pytest.raises(EngineeringConstantConflictError):engineering_constant_service.create_constant(key="CUSTOM",display_name="Duplicate",value=2)
    engineering_constant_service.delete_constant(item.id)
@pytest.mark.parametrize(("key","value"),[("safety_factor",0),("design_pressure_bar",0),("weld_factor",0),("corrosion_allowance_mm",-.1),("display_decimal_places",2.5),("display_decimal_places",13)])
def test_per_key_constant_validation(engineering_constant_service:EngineeringConstantService,key:str,value:float)->None:
    """Known constant meanings apply their required validation."""
    with pytest.raises(EngineeringConstantValidationError):engineering_constant_service.create_constant(key=key,display_name="Test",value=value)
