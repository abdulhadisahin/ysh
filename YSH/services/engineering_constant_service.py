"""Service layer for editable engineering constants."""
from __future__ import annotations
from collections.abc import Sequence
from uuid import UUID
from core.engineering_constant import EngineeringConstant
from engineering.validation import ValidationError, ValidationIssue
from repositories.engineering_constant_repository import EngineeringConstantRepository, EngineeringConstantRepositoryConflictError
class EngineeringConstantValidationError(ValidationError): """Raised when constant data is invalid."""
class EngineeringConstantConflictError(ValidationError): """Raised for duplicate constant keys."""
class EngineeringConstantNotFoundError(ValidationError, LookupError): """Raised for absent constants."""
class EngineeringConstantService:
    """Validates and provides editable engineering constants."""
    _DEFAULTS=(("safety_factor","Safety Factor",1.8,"","YSH Version 1 default"),("design_pressure_bar","Design Pressure",16.0,"bar","YSH Version 1 default"),("weld_factor","Weld Factor",1.0,"","YSH Version 1 default"),("corrosion_allowance_mm","Corrosion Allowance",1.0,"mm","YSH Version 1 default"),("display_decimal_places","Display Decimal Places",6.0,"digits","YSH Version 1 default"))
    def __init__(self,repository:EngineeringConstantRepository)->None:
        """Create the service and seed defaults only for an empty table."""
        self._repository=repository
        if not repository.get_all():
            for key,name,value,unit,source in self._DEFAULTS:repository.create(EngineeringConstant(key=key,display_name=name,value=value,unit=unit,source=source,is_system=True))
    def create_constant(self,**values:object)->EngineeringConstant:
        """Validate and persist a constant."""
        item=EngineeringConstant(**values)  # type: ignore[arg-type]
        self._normalise(item);self._validate(item);self._available(item)
        try:return self._repository.create(item)
        except EngineeringConstantRepositoryConflictError as error:raise EngineeringConstantConflictError(ValidationIssue("constant_duplicate")) from error
    def update_constant(self,item:EngineeringConstant)->EngineeringConstant:
        """Validate and update a constant."""
        self._normalise(item);self._validate(item);self._available(item);item.touch()
        try:return self._repository.update(item)
        except KeyError as error:raise EngineeringConstantNotFoundError(ValidationIssue("constant_not_found")) from error
        except EngineeringConstantRepositoryConflictError as error:raise EngineeringConstantConflictError(ValidationIssue("constant_duplicate")) from error
    def delete_constant(self,item_id:UUID)->None:
        """Delete a constant."""
        try:self._repository.delete(item_id)
        except KeyError as error:raise EngineeringConstantNotFoundError(ValidationIssue("constant_not_found")) from error
    def get_constant(self,key:str)->EngineeringConstant:
        """Retrieve a constant by key."""
        item=self._repository.get_by_key(key)
        if item is None:raise EngineeringConstantNotFoundError(ValidationIssue("constant_not_found"))
        return item
    def get_all_constants(self)->Sequence[EngineeringConstant]:
        """List all editable constants."""
        return self._repository.get_all()
    @staticmethod
    def _normalise(item:EngineeringConstant)->None: item.key=item.key.strip();item.display_name=item.display_name.strip();item.unit=item.unit.strip();item.description=item.description.strip();item.source=item.source.strip() or "User"
    def _validate(self,item:EngineeringConstant)->None:
        if not item.key:raise EngineeringConstantValidationError(ValidationIssue("required", "field.constant_key"))
        if not item.display_name:raise EngineeringConstantValidationError(ValidationIssue("required", "field.constant_display_name"))
        if item.key in {"safety_factor","design_pressure_bar","weld_factor"} and item.value<=0:raise EngineeringConstantValidationError(ValidationIssue("greater_than_zero", "field.constant_value"))
        if item.key=="corrosion_allowance_mm" and item.value<0:raise EngineeringConstantValidationError(ValidationIssue("zero_or_greater", "field.constant_value"))
        if item.key=="display_decimal_places" and (not item.value.is_integer() or not 0<=item.value<=12):raise EngineeringConstantValidationError(ValidationIssue("constant_value_invalid", "field.constant_value"))
    def _available(self,item:EngineeringConstant)->None:
        if self._repository.exists_key(item.key,item.id):raise EngineeringConstantConflictError(ValidationIssue("constant_duplicate"))
