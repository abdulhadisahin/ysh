"""Service layer for material-library workflows."""
from __future__ import annotations
from collections.abc import Sequence
from uuid import UUID
from core.material import Material
from repositories.material_repository import MaterialRepository, MaterialRepositoryConflictError

class MaterialValidationError(ValueError):
    """Raised when material data is unsuitable for storage or use."""
class MaterialConflictError(ValueError):
    """Raised when a material designation duplicates another record."""
class MaterialNotFoundError(LookupError):
    """Raised when a requested material is not available."""
class MaterialService:
    """Validates and coordinates material-library operations."""
    def __init__(self, repository: MaterialRepository) -> None:
        """Create the service and seed only an empty library."""
        self._repository = repository
        if not repository.get_all(): self._seed()
    def create_material(self, **values: object) -> Material:
        """Validate and persist a new material."""
        item = Material(**values)  # type: ignore[arg-type]
        self._normalise(item); self._validate(item); self._available(item)
        try: return self._repository.create(item)
        except MaterialRepositoryConflictError as error: raise MaterialConflictError("A material with this designation already exists.") from error
    def update_material(self, item: Material) -> Material:
        """Validate and persist a changed material."""
        self._normalise(item); self._validate(item); self._available(item); item.touch()
        try: return self._repository.update(item)
        except KeyError as error: raise MaterialNotFoundError(str(error)) from error
        except MaterialRepositoryConflictError as error: raise MaterialConflictError("A material with this designation already exists.") from error
    def delete_material(self, item_id: UUID) -> None:
        """Delete a material."""
        try: self._repository.delete(item_id)
        except KeyError as error: raise MaterialNotFoundError(str(error)) from error
    def get_material(self, item_id: UUID) -> Material:
        """Return a complete material record."""
        item = self._repository.get(item_id)
        if item is None: raise MaterialNotFoundError(f"Material '{item_id}' was not found.")
        return item
    def get_all_materials(self) -> Sequence[Material]:
        """Return all available materials."""
        return self._repository.get_all()
    def validate_required_properties(self, material: Material, *properties: str) -> None:
        """Ensure named material properties contain verified values."""
        missing = [name for name in properties if getattr(material, name, None) is None]
        if missing: raise MaterialValidationError("Required material value must be entered or verified: " + ", ".join(missing))
    def validate_manual_values(self, yield_strength_mpa: float | None, roughness_mm: float) -> None:
        """Validate independently entered material values."""
        self._validate(Material(name="Manual", designation="Manual", yield_strength_mpa=yield_strength_mpa, roughness_mm=roughness_mm))
    def _seed(self) -> None:
        for name, strength, roughness in (("AISI 304L",190.0,0.015),("AISI 316L",195.0,0.015),("ST37",None,0.045),("ST52",None,0.045)):
            self._repository.create(Material(name=name, designation=name, yield_strength_mpa=strength, roughness_mm=roughness, source="YSH Version 1 default", is_system=True))
    @staticmethod
    def _normalise(item: Material) -> None:
        item.name=item.name.strip(); item.designation=item.designation.strip(); item.standard=item.standard.strip(); item.description=item.description.strip(); item.source=item.source.strip() or "User"
    @staticmethod
    def _validate(item: Material) -> None:
        if not item.name: raise MaterialValidationError("Material name is required.")
        if not item.designation: raise MaterialValidationError("Material designation is required.")
        if item.yield_strength_mpa is not None and item.yield_strength_mpa <= 0: raise MaterialValidationError("Yield strength must be positive.")
        if item.roughness_mm < 0: raise MaterialValidationError("Roughness must be non-negative.")
    def _available(self,item:Material)->None:
        if self._repository.exists_designation(item.designation,item.id): raise MaterialConflictError("A material with this designation already exists.")
