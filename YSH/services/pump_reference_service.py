"""Validation service for fuel transfer pump reference ships."""
from __future__ import annotations
import math
from uuid import UUID
from core.pump_reference import PumpReference
from engineering.validation import ValidationError, ValidationIssue
from repositories.pump_reference_repository import PumpReferenceRepository
class PumpReferenceService:
    """Validates and coordinates saved pump-reference records."""
    def __init__(self,repository:PumpReferenceRepository)->None:self._repository=repository
    def create_reference(self,ship_name:str,fuel_capacity_m3:float,pump_capacity_m3h:float,description:str="",source:str="User")->PumpReference:
        """Validate and persist one reference ship."""
        item=PumpReference(ship_name.strip(),fuel_capacity_m3,pump_capacity_m3h,description.strip(),source.strip() or "User");self._validate(item);return self._repository.create(item)
    def get_all_references(self)->tuple[PumpReference,...]:
        """Return all saved references."""
        return self._repository.get_all()
    def delete_reference(self,item_id:UUID)->None:
        """Delete a saved reference ship."""
        self._repository.delete(item_id)
    def get_reference(self,item_id:UUID)->PumpReference:
        """Return a saved reference or raise a clear lookup error."""
        item=self._repository.get_by_id(item_id)
        if item is None:raise LookupError("Reference ship was not found.")
        return item
    def update_reference(self,item:PumpReference)->PumpReference:
        """Validate and persist an edited reference ship."""
        item.ship_name=item.ship_name.strip();item.description=item.description.strip();item.source=item.source.strip() or "User";self._validate(item);item.modified_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc);return self._repository.update(item)
    def _validate(self,item:PumpReference)->None:
        if not item.ship_name:raise ValidationError(ValidationIssue("required","field.ship_name"))
        if self._repository.ship_name_exists(item.ship_name,item.id):raise ValidationError(ValidationIssue("duplicate_ship_name"))
        for name,value in (("Fuel capacity",item.fuel_capacity_m3),("Pump capacity",item.pump_capacity_m3h)):
            if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):raise ValidationError(ValidationIssue("valid_number","field.fuel_capacity" if name=="Fuel capacity" else "field.pump_capacity"))
            if value<=0:raise ValidationError(ValidationIssue("greater_than_zero","field.fuel_capacity" if name=="Fuel capacity" else "field.pump_capacity"))
